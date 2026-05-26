"""
AnswerKeyView — view, import, and manually edit the answer key for an exam.

Renders each question as a row with its number and an editable dropdown
for the correct answer (A–E).  Header contains:
  - "Import Answer Key" button (image OCR / CSV / JSON)
  - "Save All" button to persist dropdown edits
  - Refresh button

When read_only=True all dropdowns are disabled and both action buttons are hidden.
"""

from __future__ import annotations

import csv
import json
from typing import Callable, Optional

import flet as ft
import httpx

from frontend.desktop.api_client import APIClient, APIError
from frontend.desktop.i18n import t
from frontend.desktop.theme import ThemeConfig

_VALID_ANSWERS = ["A", "B", "C", "D", "E"]


class AnswerKeyView:
    """Editable answer-key view with import support.

    Parameters
    ----------
    api:
        Async HTTP client.
    exam_id:
        The exam whose answer key is displayed.
    theme:
        Active ``ThemeConfig`` for colour styling.
    read_only:
        When ``True`` all dropdowns are disabled and action buttons are hidden.
    on_import:
        Optional async callback invoked after a successful import so that
        other views (e.g. DashboardView) can reload their data.
    """

    def __init__(
        self,
        api: APIClient,
        exam_id: int,
        theme: ThemeConfig,
        read_only: bool = False,
        on_import: Optional[Callable] = None,
    ) -> None:
        self.api = api
        self.exam_id = exam_id
        self.theme = theme
        self.read_only = read_only
        self.on_import = on_import

        self._questions: list[dict] = []
        self._dropdowns: dict[int, ft.Dropdown] = {}

        self._list_column: Optional[ft.Column] = None
        self._save_button: Optional[ft.ElevatedButton] = None
        self._import_button: Optional[ft.ElevatedButton] = None
        self._file_picker: Optional[ft.FilePicker] = None
        self._page: Optional[ft.Page] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def load(self) -> None:
        """Fetch questions and rebuild the list."""
        try:
            self._questions = await self.api.get_answer_key(self.exam_id)
        except APIError:
            self._questions = []

        self._rebuild_list()

        if self._list_column is not None and self._page is not None:
            try:
                self._list_column.update()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, page: Optional[ft.Page] = None) -> ft.Control:
        """Return the full Flet control tree for this view."""
        if page is not None:
            self._page = page

        # ---- FilePicker (registered on page overlay) -----------------
        self._file_picker = ft.FilePicker(on_result=self._on_file_picked)
        if self._page is not None:
            self._page.overlay.append(self._file_picker)

        # ---- Import button (hidden in read_only mode) ----------------
        self._import_button = ft.ElevatedButton(
            text=t("import_answer_key"),
            icon=ft.Icons.UPLOAD_FILE,
            on_click=self._on_import_clicked,
            bgcolor=self.theme.secondary,
            color=self.theme.on_primary,
            visible=not self.read_only,
        )

        # ---- Save button (hidden in read_only mode) ------------------
        self._save_button = ft.ElevatedButton(
            text=t("save_all"),
            icon=ft.Icons.SAVE,
            on_click=self._on_save_clicked,
            bgcolor=self.theme.primary,
            color=self.theme.on_primary,
            visible=not self.read_only,
        )

        # ---- Refresh button -----------------------------------------
        refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip=t("refresh"),
            on_click=self._on_refresh_clicked,
            icon_color=self.theme.secondary,
        )

        # ---- Header row ---------------------------------------------
        header_row = ft.Row(
            controls=[
                ft.Text(
                    t("answer_key_view"),
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=self.theme.on_background,
                ),
                ft.Row(
                    controls=[self._import_button, self._save_button, refresh_button],
                    spacing=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # ---- Question list ------------------------------------------
        self._list_column = ft.Column(
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        self._rebuild_list()

        return ft.Container(
            expand=True,
            bgcolor=self.theme.background,
            padding=24,
            content=ft.Column(
                controls=[
                    header_row,
                    ft.Divider(color=self.theme.surface, height=1),
                    self._list_column,
                ],
                spacing=16,
                expand=True,
            ),
        )

    # ------------------------------------------------------------------
    # Private helpers — list
    # ------------------------------------------------------------------

    def _rebuild_list(self) -> None:
        if self._list_column is None:
            return

        self._list_column.controls.clear()
        self._dropdowns.clear()

        if not self._questions:
            self._list_column.controls.append(
                ft.Text(
                    t("answer_key_empty"),
                    color=self.theme.on_background,
                    opacity=0.6,
                    italic=True,
                )
            )
            return

        COLS = 3
        sorted_qs = sorted(self._questions, key=lambda q: q.get("numero", 0))

        for i in range(0, len(sorted_qs), COLS):
            chunk = sorted_qs[i : i + COLS]
            row_controls = [self._build_question_card(q) for q in chunk]
            while len(row_controls) < COLS:
                row_controls.append(ft.Container(expand=True))
            self._list_column.controls.append(
                ft.Row(controls=row_controls, spacing=8, expand=True)
            )

    def _build_question_card(self, question: dict) -> ft.Control:
        numero: int = question.get("numero", 0)
        current_answer: str = (question.get("question_correct_answer") or "").upper()

        dropdown = ft.Dropdown(
            value=current_answer if current_answer in _VALID_ANSWERS else None,
            options=[ft.dropdown.Option(a) for a in _VALID_ANSWERS],
            width=80,
            disabled=self.read_only,
            bgcolor=self.theme.surface,
            color=self.theme.on_background,
            border_color=self.theme.secondary,
            focused_border_color=self.theme.primary,
            hint_text="—",
        )
        self._dropdowns[numero] = dropdown

        return ft.Container(
            expand=True,
            content=ft.Row(
                controls=[
                    ft.Text(
                        f"{t('question_number_short')} {numero}",
                        size=13,
                        color=self.theme.on_background,
                        width=60,
                    ),
                    dropdown,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            bgcolor=self.theme.surface,
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

    # ------------------------------------------------------------------
    # Private helpers — import
    # ------------------------------------------------------------------

    def _on_import_clicked(self, e: ft.ControlEvent) -> None:
        """Open the FilePicker — accepts images (OCR), CSV, and JSON."""
        if self._file_picker is not None:
            self._file_picker.pick_files(
                dialog_title=t("import_answer_key"),
                allowed_extensions=["jpg", "jpeg", "png", "csv", "json"],
                allow_multiple=False,
            )

    def _on_file_picked(self, e: ft.FilePickerResultEvent) -> None:
        """Route to OCR upload or file-based import based on extension."""
        if e.files and len(e.files) > 0:
            file_path = e.files[0].path
            if file_path and self._page is not None:
                ext = file_path.rsplit(".", 1)[-1].lower()
                if ext in ("csv", "json"):
                    self._page.run_task(self._import_from_file, file_path, ext)
                else:
                    self._page.run_task(self._upload_ocr_image, file_path)

    def _set_import_loading(self, loading: bool) -> None:
        if self._import_button is not None:
            self._import_button.disabled = loading
            try:
                self._import_button.update()
            except Exception:
                pass

    async def _import_from_file(self, file_path: str, ext: str) -> None:
        """Parse a CSV or JSON answer key and POST to the manual endpoint."""
        self._set_import_loading(True)
        try:
            answers: dict[str, str] = {}

            if ext == "json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    answers = {str(k): str(v).strip().upper() for k, v in data.items()}
                elif isinstance(data, list):
                    for row in data:
                        q = row.get("question") or row.get("numero") or row.get("q")
                        a = row.get("answer") or row.get("resposta") or row.get("a")
                        if q is not None and a is not None:
                            answers[str(q)] = str(a).strip().upper()

            elif ext == "csv":
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        q = (row.get("question") or row.get("numero") or
                             row.get("q") or row.get("Q") or "").strip()
                        a = (row.get("answer") or row.get("resposta") or
                             row.get("a") or row.get("A") or "").strip().upper()
                        if q and a:
                            answers[q] = a

            if not answers:
                raise ValueError(
                    "No valid pairs found. "
                    "CSV needs 'question'+'answer' columns. "
                    'JSON needs {"1": "A"} or [{"question": 1, "answer": "A"}].'
                )

            result = await self.api.set_answer_key_manual(self.exam_id, answers)
            saved = result.get("saved", len(answers))
            self._show_snack(f"{t('answer_key_imported')} ({saved} questões)")
            await self._after_import()

        except Exception as err:
            self._show_snack(str(err))
        finally:
            self._set_import_loading(False)

    async def _upload_ocr_image(self, file_path: str) -> None:
        """POST the image to the OCR endpoint."""
        self._set_import_loading(True)
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()

            filename = file_path.split("/")[-1].split("\\")[-1]

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"http://localhost:8000/api/v1/exams/{self.exam_id}/ocr/answer-key",
                    files={"file": (filename, file_content)},
                )

            if response.status_code < 200 or response.status_code >= 300:
                try:
                    detail = response.json().get("detail", "")
                except Exception:
                    detail = response.text
                raise Exception(detail or f"HTTP {response.status_code}")

            self._show_snack(t("answer_key_imported"))
            await self._after_import()

        except Exception as err:
            self._show_snack(str(err))
        finally:
            self._set_import_loading(False)

    async def _after_import(self) -> None:
        """Reload this view and notify the dashboard."""
        await self.load()
        if self.on_import is not None:
            try:
                await self.on_import()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Private helpers — save
    # ------------------------------------------------------------------

    def _on_save_clicked(self, e: ft.ControlEvent) -> None:
        if self._page is not None:
            self._page.run_task(self._save_all)

    async def _save_all(self) -> None:
        if self._save_button is not None:
            self._save_button.disabled = True
            try:
                self._save_button.update()
            except Exception:
                pass

        try:
            answers: dict[str, str] = {}
            for numero, dropdown in self._dropdowns.items():
                val = (dropdown.value or "").strip().upper()
                if val in _VALID_ANSWERS:
                    answers[str(numero)] = val

            if not answers:
                self._show_snack(t("error_required"))
                return

            await self.api.set_answer_key_manual(self.exam_id, answers)
            self._show_snack(t("answer_key_saved"))
            await self._after_import()

        except APIError as err:
            self._show_snack(err.message)
        except Exception as err:
            self._show_snack(str(err))
        finally:
            if self._save_button is not None:
                self._save_button.disabled = False
                try:
                    self._save_button.update()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Private helpers — refresh / snack
    # ------------------------------------------------------------------

    def _on_refresh_clicked(self, e: ft.ControlEvent) -> None:
        if self._page is not None:
            self._page.run_task(self.load)

    def _show_snack(self, message: str) -> None:
        if self._page is not None:
            self._page.snack_bar = ft.SnackBar(
                content=ft.Text(message), open=True
            )
            try:
                self._page.update()
            except Exception:
                pass
