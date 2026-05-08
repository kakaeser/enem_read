"""
OCR Service for processing answer key and answer sheet images.

Implements image preprocessing pipeline:
  grayscale → orientation detection/correction → CLAHE → denoising → Otsu binarization
"""

import logging
import re
from typing import List, Optional

import cv2
import numpy as np
import pytesseract
from pytesseract import Output

from backend.entities.questao import Questao
from backend.entities.resposta import Resposta
from backend.schemas.ocr import AnswerKeyResult, AnswerSheetResult, ExtractedAnswer

logger = logging.getLogger(__name__)

# Valid answer characters (A-E, case-insensitive matching)
VALID_ANSWERS = set("ABCDE")

# Patterns to match lines like:
#   "1. A", "1) A", "1 - A", "Q1: A", "1 A", "1 : C"
#   Allows optional whitespace around any single separator character.
_ANSWER_PATTERN = re.compile(
    r"[Qq]?\s*(\d+)\s*[.)\-:]?\s*[:]?\s*([A-Ea-e])\b"
)


class OCRService:
    """Service for OCR processing of answer keys and answer sheets."""

    # ------------------------------------------------------------------ #
    # Public async API                                                     #
    # ------------------------------------------------------------------ #

    async def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Run the preprocessing pipeline on a raw image.

        For images that are already clean (high contrast, low noise — e.g.
        digital screenshots or scanned documents with white background), the
        heavy pipeline (CLAHE + denoising + Otsu) actually *hurts* OCR quality
        by introducing artifacts.  We detect this case and return a simple
        grayscale conversion instead.

        Pipeline (clean image):
          1. Grayscale conversion only

        Pipeline (noisy/low-contrast image):
          1. Grayscale conversion
          2. Orientation detection and correction
          3. Adaptive histogram equalization (CLAHE)
          4. Denoising (fastNlMeansDenoising)
          5. Binarization (Otsu's method)

        Args:
            image: Input image as a NumPy array (BGR or grayscale).

        Returns:
            Preprocessed image as a NumPy array.
        """
        gray = self._to_grayscale(image)

        if self._is_clean_image(gray):
            # Already clean — just return grayscale, no further processing
            return gray

        corrected = self._correct_orientation(gray)
        equalized = self._apply_clahe(corrected)
        denoised = self._denoise(equalized)
        binary = self._binarize(denoised)
        return binary

    def _is_clean_image(self, gray: np.ndarray) -> bool:
        """
        Return True if the image is already high-contrast and clean.

        Heuristic: if more than 85% of pixels are near-white (>200) or
        near-black (<50), the image needs no further processing.
        """
        total = gray.size
        if total == 0:
            return False
        near_white = int(np.sum(gray > 200))
        near_black = int(np.sum(gray < 50))
        ratio = (near_white + near_black) / total
        return ratio > 0.85

    async def process_answer_key(
        self,
        image_file: bytes,
        exam_id: int,
        exam_questions_numbers: int,
        question_repo,
    ) -> AnswerKeyResult:
        """
        Process an answer key image and persist extracted correct answers.

        Args:
            image_file: Raw image bytes (JPEG, PNG, etc.).
            exam_id: ID of the exam this answer key belongs to.
            exam_questions_numbers: Total number of questions in the exam.
            question_repo: Repository with get_by_exam_id, update, create_bulk methods.

        Returns:
            AnswerKeyResult with extraction summary.
        """
        try:
            # Decode bytes → numpy array
            nparr = np.frombuffer(image_file, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                return AnswerKeyResult(
                    exam_id=exam_id,
                    extracted_answers=[],
                    avg_confidence=0.0,
                    flagged_count=0,
                    success=False,
                    error_message="Failed to decode image file.",
                )

            # Preprocess
            preprocessed = await self.preprocess_image(image)

            # PSM 11: sparse text — finds words anywhere on the page without
            # assuming a single block. Works better for multi-column tables.
            # PSM 6 (uniform block) was causing column-by-column reading.
            _TESS_CONFIG = r"--oem 3 --psm 6"
            data = pytesseract.image_to_data(
                preprocessed, output_type=Output.DICT, config=_TESS_CONFIG
            )
            full_text = pytesseract.image_to_string(preprocessed, config=_TESS_CONFIG)
            print("\n\n=== TEXTO BRUTO DO TESSERACT ===")
            print(full_text)
            print("================================\n\n")

            # Build a word→confidence map (last occurrence wins for duplicates)
            word_conf: dict[str, float] = {}
            for word, conf in zip(data["text"], data["conf"]):
                word = word.strip()
                if word and conf != -1:
                    word_conf[word.upper()] = float(conf)

            # Try spatial pairing first; fall back to line-based parsing
            extracted = self._parse_answer_key_spatial(
                data, exam_questions_numbers, word_conf
            )
            if not extracted:
                extracted = self._parse_answer_key_text(
                    full_text, exam_questions_numbers, word_conf
                )

            if not extracted:
                return AnswerKeyResult(
                    exam_id=exam_id,
                    extracted_answers=[],
                    avg_confidence=0.0,
                    flagged_count=0,
                    success=False,
                    error_message="No valid question-answer pairs found in image.",
                )

            # Persist to database
            await self._save_answer_key(exam_id, extracted, question_repo)

            avg_conf = sum(e.confidence for e in extracted) / len(extracted)
            flagged = sum(1 for e in extracted if e.confidence < 80.0)

            return AnswerKeyResult(
                exam_id=exam_id,
                extracted_answers=extracted,
                avg_confidence=round(avg_conf, 2),
                flagged_count=flagged,
                success=True,
            )

        except Exception as exc:
            logger.exception("process_answer_key failed for exam_id=%s", exam_id)
            return AnswerKeyResult(
                exam_id=exam_id,
                extracted_answers=[],
                avg_confidence=0.0,
                flagged_count=0,
                success=False,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------ #
    # Private helpers for answer key processing                           #
    # ------------------------------------------------------------------ #

    def _parse_answer_key_spatial(
        self,
        data: dict,
        max_question: int,
        word_conf: dict,
    ) -> List[ExtractedAnswer]:
        """
        Pair question numbers with answer letters using bounding-box proximity.

        Handles both clean single-word tokens ("23", "B") and merged tokens
        produced when Tesseract fuses colon-separated text ("23:B", "23:48:24:").
        """
        # ---- Step 1: expand raw tokens into atomic (text, cx, cy, conf) ----
        # Tesseract sometimes merges "23:B" or "23:48:24:" into one token.
        # We split on ":" and distribute the bounding box evenly.
        _NUM_RE = re.compile(r"^[Qq]?(\d+)$")
        _ANS_RE = re.compile(r"^([A-Ea-e])$")
        # Also catch "23:B" merged tokens directly
        _MERGED_RE = re.compile(r"[Qq]?(\d+)\s*[:.]\s*([A-Ea-e])\b")

        atomic: list[tuple[str, float, float, float]] = []  # (text, cx, cy, conf)
        merged_pairs: list[tuple[int, str, float]] = []     # (q_num, answer, conf)

        n = len(data["text"])
        for i in range(n):
            raw = (data["text"][i] or "").strip()
            if not raw:
                continue
            conf = float(data["conf"][i]) if data["conf"][i] != -1 else 50.0
            x = data["left"][i]
            y = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]
            cx = float(x + w / 2)
            cy = float(y + h / 2)

            # Check for merged "23:B" pattern first
            m = _MERGED_RE.search(raw)
            if m:
                q_num = int(m.group(1))
                answer = m.group(2).upper()
                if 1 <= q_num <= max_question and answer in VALID_ANSWERS:
                    merged_pairs.append((q_num, answer, conf))
                continue

            # Split on ":" to handle "23:48:24:" column merges
            parts = [p.strip() for p in raw.split(":") if p.strip()]
            if len(parts) > 1:
                # Distribute bounding box width evenly across parts
                part_w = w / len(parts)
                for j, part in enumerate(parts):
                    part_cx = x + part_w * j + part_w / 2
                    atomic.append((part, part_cx, cy, conf))
            else:
                atomic.append((raw, cx, cy, conf))

        # If we got clean merged pairs, return them directly
        if merged_pairs:
            seen: set[int] = set()
            results: List[ExtractedAnswer] = []
            for q_num, answer, conf in sorted(merged_pairs, key=lambda t: t[0]):
                if q_num in seen:
                    continue
                seen.add(q_num)
                results.append(ExtractedAnswer(
                    question_number=q_num,
                    answer=answer,
                    confidence=conf,
                ))
            if len(results) >= max_question // 2:
                return results
            # Not enough — fall through to spatial matching

        # ---- Step 2: separate number and answer tokens ----
        heights_approx = 20.0  # fallback
        num_tokens: list[tuple[int, float, float, float]] = []
        ans_tokens: list[tuple[str, float, float, float]] = []

        for word, cx, cy, conf in atomic:
            m = _NUM_RE.match(word)
            if m:
                num_tokens.append((int(m.group(1)), cx, cy, conf))
            elif _ANS_RE.match(word):
                ans_tokens.append((word.upper(), cx, cy, conf))

        if not num_tokens or not ans_tokens:
            return []

        # Estimate row height from vertical gaps between consecutive number tokens
        sorted_nums = sorted(num_tokens, key=lambda t: t[2])
        gaps = [
            abs(sorted_nums[i+1][2] - sorted_nums[i][2])
            for i in range(len(sorted_nums) - 1)
            if abs(sorted_nums[i+1][2] - sorted_nums[i][2]) > 2
        ]
        row_h = float(sorted(gaps)[len(gaps) // 2]) if gaps else heights_approx
        band = row_h * 0.8

        # ---- Step 3: pair each number with the nearest answer in its band ----
        seen2: set[int] = set()
        results2: List[ExtractedAnswer] = []

        for q_num, nx, ny, _ in sorted(num_tokens, key=lambda t: (t[2], t[1])):
            if q_num < 1 or q_num > max_question:
                continue
            if q_num in seen2:
                continue

            candidates = [
                (a, ax, ay, ac)
                for a, ax, ay, ac in ans_tokens
                if abs(ay - ny) <= band and ax > nx
            ]
            if not candidates:
                candidates = [
                    (a, ax, ay, ac)
                    for a, ax, ay, ac in ans_tokens
                    if abs(ay - ny) <= band
                ]
            if not candidates:
                continue

            best = min(candidates, key=lambda t: abs(t[1] - nx))
            answer = best[0]
            confidence = best[3] if best[3] > 0 else word_conf.get(answer, 50.0)

            if answer not in VALID_ANSWERS:
                continue

            seen2.add(q_num)
            results2.append(ExtractedAnswer(
                question_number=q_num,
                answer=answer,
                confidence=confidence,
            ))

        return results2

    def _parse_answer_sheet_spatial(
        self,
        data: dict,
        question_map: dict,
        word_conf: dict,
    ) -> List[ExtractedAnswer]:
        """Spatial pairing for answer sheets — same algorithm, validates against question_map."""
        _NUM_RE = re.compile(r"^[Qq]?(\d+)$")
        _ANS_RE = re.compile(r"^([A-Ea-e])$")
        _MERGED_RE = re.compile(r"[Qq]?(\d+)\s*[:.]\s*([A-Ea-e])\b")

        atomic: list[tuple[str, float, float, float]] = []
        merged_pairs: list[tuple[int, str, float]] = []

        n = len(data["text"])
        for i in range(n):
            raw = (data["text"][i] or "").strip()
            if not raw:
                continue
            conf = float(data["conf"][i]) if data["conf"][i] != -1 else 50.0
            x = data["left"][i]
            y = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]
            cx = float(x + w / 2)
            cy = float(y + h / 2)

            m = _MERGED_RE.search(raw)
            if m:
                q_num = int(m.group(1))
                answer = m.group(2).upper()
                if q_num in question_map and answer in VALID_ANSWERS:
                    merged_pairs.append((q_num, answer, conf))
                continue

            parts = [p.strip() for p in raw.split(":") if p.strip()]
            if len(parts) > 1:
                part_w = w / len(parts)
                for j, part in enumerate(parts):
                    part_cx = x + part_w * j + part_w / 2
                    atomic.append((part, part_cx, cy, conf))
            else:
                atomic.append((raw, cx, cy, conf))

        if merged_pairs:
            seen: set[int] = set()
            results: List[ExtractedAnswer] = []
            for q_num, answer, conf in sorted(merged_pairs, key=lambda t: t[0]):
                if q_num in seen:
                    continue
                seen.add(q_num)
                results.append(ExtractedAnswer(
                    question_number=q_num,
                    answer=answer,
                    confidence=conf,
                ))
            if len(results) >= len(question_map) // 2:
                return results

        num_tokens: list[tuple[int, float, float, float]] = []
        ans_tokens: list[tuple[str, float, float, float]] = []

        for word, cx, cy, conf in atomic:
            m = _NUM_RE.match(word)
            if m:
                num_tokens.append((int(m.group(1)), cx, cy, conf))
            elif _ANS_RE.match(word):
                ans_tokens.append((word.upper(), cx, cy, conf))

        if not num_tokens or not ans_tokens:
            return []

        sorted_nums = sorted(num_tokens, key=lambda t: t[2])
        gaps = [
            abs(sorted_nums[i+1][2] - sorted_nums[i][2])
            for i in range(len(sorted_nums) - 1)
            if abs(sorted_nums[i+1][2] - sorted_nums[i][2]) > 2
        ]
        row_h = float(sorted(gaps)[len(gaps) // 2]) if gaps else 20.0
        band = row_h * 0.8

        seen2: set[int] = set()
        results2: List[ExtractedAnswer] = []

        for q_num, nx, ny, _ in sorted(num_tokens, key=lambda t: (t[2], t[1])):
            if q_num not in question_map:
                continue
            if q_num in seen2:
                continue

            candidates = [
                (a, ax, ay, ac)
                for a, ax, ay, ac in ans_tokens
                if abs(ay - ny) <= band and ax > nx
            ]
            if not candidates:
                candidates = [
                    (a, ax, ay, ac)
                    for a, ax, ay, ac in ans_tokens
                    if abs(ay - ny) <= band
                ]
            if not candidates:
                continue

            best = min(candidates, key=lambda t: abs(t[1] - nx))
            answer = best[0]
            confidence = best[3] if best[3] > 0 else word_conf.get(answer, 50.0)

            if answer not in VALID_ANSWERS:
                continue

            seen2.add(q_num)
            results2.append(ExtractedAnswer(
                question_number=q_num,
                answer=answer,
                confidence=confidence,
            ))

        return results2

    def _parse_answer_key_text(
        self,
        text: str,
        max_question: int,
        word_conf: dict,
    ) -> List[ExtractedAnswer]:
        """
        Parse OCR text and return validated ExtractedAnswer objects.

        Handles both clean lines ("1: C") and Tesseract column-merge artifacts
        where an entire column appears on one line ("23:48:24:C25:B...").
        """
        results: List[ExtractedAnswer] = []
        seen: set[int] = set()

        # Scan the entire text (not just per-line) for all number:letter pairs
        for match in _ANSWER_PATTERN.finditer(text):
            q_str = match.group(1)
            a_str = match.group(2)

            if not q_str or not a_str:
                continue

            q_num = int(q_str)
            answer = a_str.upper()

            if q_num < 1 or q_num > max_question:
                continue
            if answer not in VALID_ANSWERS:
                continue
            if q_num in seen:
                continue

            seen.add(q_num)
            confidence = word_conf.get(answer, 50.0)
            results.append(ExtractedAnswer(
                question_number=q_num,
                answer=answer,
                confidence=confidence,
            ))

        return results

    def _parse_answer_sheet_text(
        self,
        text: str,
        question_map: dict,
        word_conf: dict,
    ) -> List[ExtractedAnswer]:
        """
        Parse OCR text for answer sheets — validates against question_map.
        Scans full text to handle column-merge artifacts.
        """
        results: List[ExtractedAnswer] = []
        seen: set[int] = set()

        for match in _ANSWER_PATTERN.finditer(text):
            q_str = match.group(1)
            a_str = match.group(2)

            if not q_str or not a_str:
                continue

            q_num = int(q_str)
            answer = a_str.upper()

            if q_num not in question_map:
                continue
            if answer not in VALID_ANSWERS:
                continue
            if q_num in seen:
                continue

            seen.add(q_num)
            confidence = word_conf.get(answer, 50.0)
            results.append(ExtractedAnswer(
                question_number=q_num,
                answer=answer,
                confidence=confidence,
            ))

        return results

    async def _save_answer_key(
        self,
        exam_id: int,
        extracted: List[ExtractedAnswer],
        question_repo,
    ) -> None:
        """Create or update Question records with extracted correct answers."""
        existing: list[Questao] = await question_repo.get_by_exam_id(exam_id)
        existing_map: dict[int, Questao] = {q.numero: q for q in existing}

        to_create: list[Questao] = []

        for item in extracted:
            if item.question_number in existing_map:
                q = existing_map[item.question_number]
                q.question_correct_answer = item.answer
                await question_repo.update(q)
            else:
                to_create.append(
                    Questao(
                        exam_id=exam_id,
                        numero=item.question_number,
                        peso=1,
                        question_correct_answer=item.answer,
                    )
                )

        if to_create:
            await question_repo.create_bulk(to_create)

    async def process_answer_sheet(
        self,
        image_file: bytes,
        participant_id: int,
        exam_id: int,
        question_repo,
        response_repo,
    ) -> AnswerSheetResult:
        """
        Process a participant answer sheet image and persist extracted marked answers.

        Args:
            image_file: Raw image bytes (JPEG, PNG, etc.).
            participant_id: ID of the participant whose sheet is being processed.
            exam_id: ID of the exam this answer sheet belongs to.
            question_repo: Repository with get_by_exam_id method.
            response_repo: Repository with create_or_update method.

        Returns:
            AnswerSheetResult with extraction summary.
        """
        try:
            # Decode bytes → numpy array
            nparr = np.frombuffer(image_file, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                return AnswerSheetResult(
                    participant_id=participant_id,
                    exam_id=exam_id,
                    extracted_answers=[],
                    avg_confidence=0.0,
                    flagged_count=0,
                    success=False,
                    error_message="Failed to decode image file.",
                )

            # Preprocess
            preprocessed = await self.preprocess_image(image)

            # PSM 11: sparse text — finds words anywhere on the page without
            # assuming a single block. Works better for multi-column tables.
            _TESS_CONFIG = r"--oem 3 --psm 11"
            data = pytesseract.image_to_data(preprocessed, output_type=Output.DICT, config=_TESS_CONFIG)
            full_text = pytesseract.image_to_string(preprocessed, config=_TESS_CONFIG)

            # Build a word→confidence map (last occurrence wins for duplicates)
            word_conf: dict[str, float] = {}
            for word, conf in zip(data["text"], data["conf"]):
                word = word.strip()
                if word and conf != -1:
                    word_conf[word.upper()] = float(conf)

            # Fetch existing questions to validate against
            existing_questions: list[Questao] = await question_repo.get_by_exam_id(exam_id)
            question_map: dict[int, Questao] = {q.numero: q for q in existing_questions}

            if not question_map:
                return AnswerSheetResult(
                    participant_id=participant_id,
                    exam_id=exam_id,
                    extracted_answers=[],
                    avg_confidence=0.0,
                    flagged_count=0,
                    success=False,
                    error_message=f"No questions found for exam_id={exam_id}.",
                )

            # Try spatial pairing first; fall back to line-based parsing
            extracted = self._parse_answer_sheet_spatial(data, question_map, word_conf)
            if not extracted:
                extracted = self._parse_answer_sheet_text(full_text, question_map, word_conf)

            if not extracted:
                return AnswerSheetResult(
                    participant_id=participant_id,
                    exam_id=exam_id,
                    extracted_answers=[],
                    avg_confidence=0.0,
                    flagged_count=0,
                    success=False,
                    error_message="No valid question-answer pairs found in image.",
                )

            # Persist to database
            await self._save_answer_sheet(
                participant_id, exam_id, extracted, question_map, response_repo
            )

            avg_conf = sum(e.confidence for e in extracted) / len(extracted)
            flagged = sum(1 for e in extracted if e.confidence < 80.0)

            return AnswerSheetResult(
                participant_id=participant_id,
                exam_id=exam_id,
                extracted_answers=extracted,
                avg_confidence=round(avg_conf, 2),
                flagged_count=flagged,
                success=True,
            )

        except Exception as exc:
            logger.exception(
                "process_answer_sheet failed for participant_id=%s exam_id=%s",
                participant_id,
                exam_id,
            )
            return AnswerSheetResult(
                participant_id=participant_id,
                exam_id=exam_id,
                extracted_answers=[],
                avg_confidence=0.0,
                flagged_count=0,
                success=False,
                error_message=str(exc),
            )

    # ------------------------------------------------------------------ #
    # Private helpers for answer sheet processing                         #
    # ------------------------------------------------------------------ #

    async def _save_answer_sheet(
        self,
        participant_id: int,
        exam_id: int,
        extracted: List[ExtractedAnswer],
        question_map: dict,
        response_repo,
    ) -> None:
        """Create or update Response records with extracted marked answers."""
        for item in extracted:
            question = question_map.get(item.question_number)
            if question is None:
                continue

            response = Resposta(
                user_id=participant_id,
                quest_id=question.id,
                exam_id=exam_id,
                marked_answer=item.answer,
                confidence_score=item.confidence,
                manually_reviewed=False,
            )
            await response_repo.create_or_update(response)

    # ------------------------------------------------------------------ #
    # Step 1 – Grayscale conversion                                        #
    # ------------------------------------------------------------------ #

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale if it is not already."""
        if image is None:
            raise ValueError("Image cannot be None")

        if len(image.shape) == 2:
            # Already grayscale
            return image.copy()

        if len(image.shape) == 3:
            channels = image.shape[2]
            if channels == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            if channels == 4:
                return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

        raise ValueError(f"Unsupported image shape: {image.shape}")

    # ------------------------------------------------------------------ #
    # Step 2 – Orientation detection and correction                        #
    # ------------------------------------------------------------------ #

    def _correct_orientation(self, gray: np.ndarray) -> np.ndarray:
        """
        Detect image orientation and rotate to upright position.

        Uses Tesseract OSD when available; falls back to a heuristic
        based on text-line detection via Hough transform.
        """
        angle = self._detect_orientation_angle(gray)
        if abs(angle) < 0.5:
            return gray

        return self._rotate_image(gray, angle)

    def _detect_orientation_angle(self, gray: np.ndarray) -> float:
        """
        Return the skew angle (degrees) that should be applied to straighten the image.

        Tries Tesseract OSD first; falls back to a Hough-line heuristic.
        """
        try:
            return self._osd_angle(gray)
        except Exception as exc:
            logger.debug("Tesseract OSD unavailable (%s); using heuristic.", exc)
            return self._heuristic_skew_angle(gray)

    def _osd_angle(self, gray: np.ndarray) -> float:
        """Use Tesseract OSD to detect orientation angle."""
        import pytesseract  # imported lazily to avoid hard dependency at module load

        osd = pytesseract.image_to_osd(gray, output_type=pytesseract.Output.DICT)
        rotate = int(osd.get("rotate", 0))
        # Tesseract reports the angle needed to make the text upright.
        # We negate it because cv2.getRotationMatrix2D rotates counter-clockwise.
        return -float(rotate)

    def _heuristic_skew_angle(self, gray: np.ndarray) -> float:
        """
        Estimate skew angle using Hough line detection on edge-detected image.

        Returns the median angle of detected near-horizontal lines, clamped to ±15°.
        """
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

        if lines is None or len(lines) == 0:
            return 0.0

        angles = []
        for line in lines:
            rho, theta = line[0]
            # Convert to degrees; near-horizontal lines have theta ≈ 0 or ≈ π
            angle_deg = np.degrees(theta) - 90.0
            if abs(angle_deg) <= 15.0:
                angles.append(angle_deg)

        if not angles:
            return 0.0

        return float(np.median(angles))

    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by *angle* degrees around its centre, filling with white."""
        h, w = image.shape[:2]
        centre = (w / 2.0, h / 2.0)
        matrix = cv2.getRotationMatrix2D(centre, angle, 1.0)
        rotated = cv2.warpAffine(
            image,
            matrix,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=255,
        )
        return rotated

    # ------------------------------------------------------------------ #
    # Step 3 – Adaptive histogram equalization (CLAHE)                    #
    # ------------------------------------------------------------------ #

    def _apply_clahe(
        self,
        gray: np.ndarray,
        clip_limit: float = 2.0,
        tile_grid_size: tuple = (8, 8),
    ) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to
        correct uneven lighting conditions.

        Args:
            gray: Grayscale image.
            clip_limit: Threshold for contrast limiting.
            tile_grid_size: Size of grid for histogram equalization.

        Returns:
            Contrast-enhanced grayscale image.
        """
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        return clahe.apply(gray)

    # ------------------------------------------------------------------ #
    # Step 4 – Denoising                                                   #
    # ------------------------------------------------------------------ #

    def _denoise(
        self,
        gray: np.ndarray,
        h: int = 10,
        template_window_size: int = 7,
        search_window_size: int = 21,
    ) -> np.ndarray:
        """
        Remove noise using Non-Local Means Denoising.

        Args:
            gray: Grayscale image.
            h: Filter strength (higher = more denoising, less detail).
            template_window_size: Size of template patch (must be odd).
            search_window_size: Size of search window (must be odd).

        Returns:
            Denoised grayscale image.
        """
        return cv2.fastNlMeansDenoising(
            gray,
            None,
            h=h,
            templateWindowSize=template_window_size,
            searchWindowSize=search_window_size,
        )

    # ------------------------------------------------------------------ #
    # Step 5 – Binarization (Otsu's method)                               #
    # ------------------------------------------------------------------ #

    def _binarize(self, gray: np.ndarray) -> np.ndarray:
        """
        Convert grayscale image to binary using Otsu's thresholding.

        Otsu's method automatically determines the optimal threshold value
        by minimising intra-class intensity variance.

        Returns:
            Binary image (0 = black, 255 = white).
        """
        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        return binary
