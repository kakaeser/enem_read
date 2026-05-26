"""
Async HTTP client wrapper for the Enem da Read REST API.

All methods raise APIError on non-2xx responses.
List methods return [] and dict methods return {} when the result is empty.
"""

from __future__ import annotations

import httpx


class APIError(Exception):
    """Raised when the API returns a non-2xx status code."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"APIError {status_code}: {message}")


def _extract_detail(response: httpx.Response) -> str:
    """Try to extract a human-readable message from an error response."""
    try:
        body = response.json()
        if isinstance(body, dict):
            return str(body.get("detail", body))
        return str(body)
    except Exception:
        return response.text or f"HTTP {response.status_code}"


def _raise_for_status(response: httpx.Response) -> None:
    """Raise APIError if the response status is not 2xx."""
    if response.status_code < 200 or response.status_code >= 300:
        raise APIError(response.status_code, _extract_detail(response))


class APIClient:
    """Thin async wrapper around httpx.AsyncClient for all desktop API calls."""

    def __init__(self, base_url: str = "http://localhost:8000/api/v1") -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    # ------------------------------------------------------------------
    # Exams
    # ------------------------------------------------------------------

    async def list_exams(self) -> list[dict]:
        """GET /exams — returns list of ExamResponse dicts."""
        response = await self._client.get("/exams/")
        _raise_for_status(response)
        return response.json() or []

    async def get_exam_results(self, exam_id: int) -> list[dict]:
        """GET /exams/{exam_id}/results — returns list of ScoreBreakdown dicts."""
        response = await self._client.get(f"/exams/{exam_id}/results")
        _raise_for_status(response)
        return response.json() or []

    async def get_exam_statistics(self, exam_id: int) -> dict:
        """GET /exams/{exam_id}/statistics — returns ExamStatistics dict."""
        response = await self._client.get(f"/exams/{exam_id}/statistics")
        _raise_for_status(response)
        return response.json() or {}

    async def create_exam(
        self, name: str, questions_numbers: int, symbolic_note: int,
        weight_mode: str = "default", heavy_questions: list[int] | None = None,
    ) -> dict:
        """POST /exams — creates a new exam and returns ExamResponse dict."""
        payload: dict = {
            "exam_name": name,
            "questions_numbers": questions_numbers,
            "symbolic_note": symbolic_note,
            "weight_mode": weight_mode,
        }
        if heavy_questions:
            payload["heavy_questions"] = heavy_questions
        response = await self._client.post("/exams/", json=payload)
        _raise_for_status(response)
        return response.json() or {}

    async def delete_exam(self, exam_id: int) -> None:
        """DELETE /exams/{exam_id} — deletes an exam and all associated data."""
        response = await self._client.delete(f"/exams/{exam_id}")
        _raise_for_status(response)

    async def set_answer_key_manual(
        self, exam_id: int, answers: dict[str, str], weights: dict[str, int] | None = None
    ) -> dict:
        """POST /exams/{exam_id}/answer-key/manual — set answers directly without OCR."""
        payload: dict = {"answers": answers}
        if weights:
            payload["weights"] = weights
        response = await self._client.post(f"/exams/{exam_id}/answer-key/manual", json=payload)
        _raise_for_status(response)
        return response.json() or {}

    async def get_answer_key(self, exam_id: int) -> list[dict]:
        """
        Return the answer key for an exam as a list of
        {numero, question_correct_answer, peso} dicts.

        Reuses GET /exams/{exam_id}/participants/{participant_id}/responses
        from the first available participant.  If no participant has responses
        yet, falls back to building a skeleton from the exam's questions_numbers
        field so the editor still shows all rows.
        """
        # Try to get a real participant with responses
        try:
            participants = await self.list_participants(exam_id)
            for p in participants:
                pid = p.get("id") or p.get("participant_id")
                if pid is None:
                    continue
                responses = await self.get_participant_responses(exam_id, pid)
                if responses:
                    # Responses already contain correct_answer + peso per question
                    return [
                        {
                            "numero": r.get("question_number") or r.get("numero"),
                            "question_correct_answer": r.get("correct_answer"),
                            "peso": r.get("peso") or r.get("weight") or 1,
                        }
                        for r in responses
                    ]
        except APIError:
            pass

        # No responses yet — build skeleton from exam metadata
        try:
            exams = await self.list_exams()
            exam = next(
                (e for e in exams if e.get("exam_id") == exam_id or e.get("id") == exam_id),
                None,
            )
            if exam:
                total: int = exam.get("questions_numbers") or 0
                return [
                    {"numero": n, "question_correct_answer": None, "peso": 1}
                    for n in range(1, total + 1)
                ]
        except APIError:
            pass

        return []

    async def finish_exam(self, exam_id: int) -> dict:
        """
        POST /exams/{exam_id}/finish — locks the exam.

        Returns ExamResponse dict with status='completed' and ended_at set.
        Raises APIError(404) if exam not found.
        Raises APIError(409) if already completed.
        """
        response = await self._client.post(f"/exams/{exam_id}/finish")
        _raise_for_status(response)
        return response.json() or {}

    # ------------------------------------------------------------------
    # Participants
    # ------------------------------------------------------------------

    async def list_participants(
        self, exam_id: int, presente: bool | None = None
    ) -> list[dict]:
        """
        GET /exams/{exam_id}/participants — returns list of ParticipantResponse dicts.

        Passes ?presente=true/false when the argument is provided.
        """
        params: dict = {}
        if presente is not None:
            params["presente"] = str(presente).lower()
        response = await self._client.get(
            f"/exams/{exam_id}/participants", params=params
        )
        _raise_for_status(response)
        return response.json() or []

    async def add_participant(self, exam_id: int, nome: str) -> dict:
        """POST /exams/{exam_id}/participants — adds a participant and returns ParticipantResponse dict."""
        response = await self._client.post(
            f"/exams/{exam_id}/participants", json={"nome": nome}
        )
        _raise_for_status(response)
        return response.json() or {}

    async def import_participants(self, exam_id: int, file_path: str) -> dict:
        """
        POST /exams/{exam_id}/participants/import — bulk-imports participants from a file.

        Opens the file at file_path and POSTs it as multipart/form-data.
        Returns {"imported": int, "skipped": int, "errors": list[str]}.
        """
        with open(file_path, "rb") as f:
            file_content = f.read()

        filename = file_path.split("/")[-1].split("\\")[-1]
        files = {"file": (filename, file_content)}
        response = await self._client.post(
            f"/exams/{exam_id}/participants/import", files=files
        )
        _raise_for_status(response)
        return response.json() or {}

    async def delete_participant(self, participant_id: int) -> None:
        """DELETE /participants/{participant_id} — deletes a participant."""
        response = await self._client.delete(f"/participants/{participant_id}")
        _raise_for_status(response)

    async def update_participant(self, participant_id: int, payload: dict) -> dict:
        """PATCH /participants/{participant_id} — updates participant fields and returns ParticipantResponse dict."""
        response = await self._client.patch(
            f"/participants/{participant_id}", json=payload
        )
        _raise_for_status(response)
        return response.json() or {}

    async def get_participant_score(self, exam_id: int, participant_id: int) -> dict:
        """
        Returns the ScoreBreakdown dict for a single participant.

        Calls GET /exams/{exam_id}/results and finds the entry matching participant_id.
        Returns {} if the participant is not found in the results.
        """
        results = await self.get_exam_results(exam_id)
        for entry in results:
            if entry.get("participant_id") == participant_id:
                return entry
        return {}

    async def get_participant_responses(
        self, exam_id: int, participant_id: int
    ) -> list[dict]:
        """
        GET /exams/{exam_id}/participants/{participant_id}/responses

        Returns list of QuestionResponseDetail dicts ordered by question_number.
        """
        response = await self._client.get(
            f"/exams/{exam_id}/participants/{participant_id}/responses"
        )
        _raise_for_status(response)
        return response.json() or []
