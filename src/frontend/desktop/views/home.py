"""
HomeView — entry screen for creating or opening an exam.

Section A: Create New Exam form with inline validation.
Section B: Scrollable list of existing exams with refresh and lock badge.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

import flet as ft

from frontend.desktop.api_client import APIClient, APIError
from frontend.desktop.i18n import t
from frontend.desktop.theme import ThemeConfig


class HomeView:
    """Entry screen: create a new exam or open an existing one.

    This class follows the ``build()`` pattern used by the other views in
    this project.  ``build()`` returns a plain ``ft.Control`` tree that the
    caller adds to the page.

    Parameters
    ----------
    api:
        Async HTTP client used to call ``list_exams`` and ``create_exam``.
    theme:
        Active ``ThemeConfig`` for colour styling.
    on_exam_ready:
        Callback invoked with the ``exam_id`` (int) once an exam is selected
        or created.  The main app uses this to replace ``HomeView`` with the
        exam workspace.
    """

    def __init__(
        self,
        api: APIClient,
        theme: ThemeConfig,
        on_exam_ready: Callable[[int], None],
    ) -> None:
        self.api = api
        self.theme = theme
        self.on_exam_ready = on_exam_ready

        # --- Section A: form fields (populated in build()) ---
        self._name_field: Optional[ft.TextField] = None
        self._questions_field: Optional[ft.TextField] = None
        self._note_field: Optional[ft.TextField] = None
        self._weight_mode_group: Optional[ft.RadioGroup] = None
        self._custom_weights_field: Optional[ft.TextField] = None
        self._custom_weights_row: Optional[ft.Container] = None
        self._create_button: Optional[ft.ElevatedButton] = None

        # --- Section B: exam list (populated in build() / load()) ---
        self._exam_list_column: Optional[ft.Column] = None
        self._exams: list[dict] = []

        # Reference to the Flet page (set by the caller after build())
        self._page: Optional[ft.Page] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def load(self) -> None:
        """Fetch existing exams and refresh the list column.

        Called once after the view is mounted and again when the user
        clicks the refresh button.

        Requirement 4.1
        """
        try:
            self._exams = await self.api.list_exams()
        except APIError:
            self._exams = []

        self._rebuild_exam_list()

        if self._exam_list_column is not None and self._page is not None:
            try:
                self._exam_list_column.update()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, page: Optional[ft.Page] = None) -> ft.Control:
        """Return the full Flet control tree for this view.

        Parameters
        ----------
        page:
            The Flet ``Page`` instance.  Required for async task dispatch
            (``page.run_task``) and snackbar display.  If omitted the caller
            must set ``view._page`` before any user interaction occurs.
        """
        if page is not None:
            self._page = page

        # ---- Section A ------------------------------------------------
        self._name_field = ft.TextField(
            label=t("exam_name"),
            expand=True,
        )
        self._questions_field = ft.TextField(
            label=t("questions_count"),
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self._note_field = ft.TextField(
            label=t("symbolic_note"),
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self._create_button = ft.ElevatedButton(
            content=ft.Text(t("create_and_open")),
            on_click=self._on_create_clicked_sync,
            bgcolor=self.theme.primary,
            color=self.theme.on_primary,
        )

        # ---- Weight mode selector ------------------------------------
        def on_weight_mode_change(e: ft.ControlEvent) -> None:
            if self._custom_weights_row is not None:
                self._custom_weights_row.visible = (e.control.value == "custom")
                if self._page is not None:
                    try:
                        self._page.update()
                    except Exception:
                        pass

        self._weight_mode_group = ft.RadioGroup(
            value="default",
            on_change=on_weight_mode_change,
            content=ft.Column(
                controls=[
                    ft.Radio(value="default",        label=t("weight_default")),
                    ft.Radio(value="even_questions",  label=t("weight_even_questions")),
                    ft.Radio(value="odd_questions",   label=t("weight_odd_questions")),
                    ft.Radio(value="custom",          label=t("weight_custom")),
                ],
                spacing=4,
            ),
        )

        self._custom_weights_field = ft.TextField(
            label=t("weight_custom_hint"),
            hint_text='ex: 1, 5, 10-15',
            expand=True,
        )
        self._custom_weights_row = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        t("weight_custom_desc"),
                        size=11,
                        color=self.theme.on_background,
                        opacity=0.6,
                        italic=True,
                    ),
                    self._custom_weights_field,
                ],
                spacing=4,
            ),
            visible=False,
        )

        section_a = ft.Container(
            expand=True,
            bgcolor=self.theme.surface,
            border_radius=8,
            padding=24,
            content=ft.Column(
                spacing=16,
                controls=[
                    ft.Text(
                        t("create_exam"),
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=self.theme.on_background,
                    ),
                    self._name_field,
                    self._questions_field,
                    self._note_field,
                    ft.Text(
                        t("weight_mode"),
                        size=13,
                        color=self.theme.on_background,
                        opacity=0.8,
                    ),
                    self._weight_mode_group,
                    self._custom_weights_row,
                    ft.Row(
                        controls=[self._create_button],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
            ),
        )

        # ---- Section B ------------------------------------------------
        self._exam_list_column = ft.Column(
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        self._rebuild_exam_list()

        refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip=t("refresh"),
            on_click=self._on_refresh_clicked,
            icon_color=self.theme.secondary,
        )

        section_b = ft.Container(
            expand=True,
            bgcolor=self.theme.surface,
            border_radius=8,
            padding=24,
            content=ft.Column(
                spacing=16,
                expand=True,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(
                                t("open_exam"),
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color=self.theme.on_background,
                            ),
                            refresh_button,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self._exam_list_column,
                ],
            ),
        )

        # ---- Layout ---------------------------------------------------
        return ft.Container(
            expand=True,
            bgcolor=self.theme.background,
            padding=32,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.Text(
                        "Enem da Read",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=self.theme.primary,
                    ),
                    ft.ResponsiveRow(
                        expand=True,
                        controls=[
                            ft.Column(
                                col={"sm": 12, "md": 6},
                                controls=[section_a],
                                expand=True,
                            ),
                            ft.Column(
                                col={"sm": 12, "md": 6},
                                controls=[section_b],
                                expand=True,
                            ),
                        ],
                    ),
                ],
                spacing=24,
            ),
        )

    # ------------------------------------------------------------------
    # Private helpers — exam list
    # ------------------------------------------------------------------

    def _rebuild_exam_list(self) -> None:
        """Repopulate ``_exam_list_column`` from ``self._exams``.

        Requirements: 4.1, 4.2, 4.6
        """
        if self._exam_list_column is None:
            return

        self._exam_list_column.controls.clear()

        if not self._exams:
            # Requirement 4.2 — empty state message
            self._exam_list_column.controls.append(
                ft.Text(
                    t("no_exams"),
                    color=self.theme.on_background,
                    opacity=0.6,
                    italic=True,
                )
            )
            return

        for exam in self._exams:
            exam_id: int = exam.get("exam_id") or exam.get("id", 0)
            name: str = (
                exam.get("exam_name")
                or exam.get("name")
                or str(exam_id)
            )
            status: str = exam.get("status", "")
            questions: int = (
                exam.get("questions_numbers")
                or exam.get("questions_count")
                or 0
            )
            created_at: str = exam.get("created_at") or ""
            is_completed = status == "completed"

            # Build the row controls
            row_controls: list[ft.Control] = []

            if is_completed:
                # Requirement 4.6 — lock icon
                row_controls.append(ft.Text("🔒", size=16))

            row_controls.append(
                ft.Text(
                    name,
                    expand=True,
                    weight=ft.FontWeight.W_500,
                    color=self.theme.on_background,
                )
            )

            if is_completed:
                # Requirement 4.6 — completed status badge
                row_controls.append(
                    ft.Container(
                        content=ft.Text(
                            t("exam_completed"),
                            size=11,
                            color=self.theme.on_primary,
                        ),
                        bgcolor=self.theme.secondary,
                        border_radius=4,
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    )
                )

            if questions:
                row_controls.append(
                    ft.Text(
                        f"{questions}q",
                        size=12,
                        color=self.theme.on_background,
                        opacity=0.6,
                    )
                )

            if created_at:
                date_str = (
                    created_at[:10] if len(created_at) >= 10 else created_at
                )
                row_controls.append(
                    ft.Text(
                        date_str,
                        size=12,
                        color=self.theme.on_background,
                        opacity=0.5,
                    )
                )

            row = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Row(
                                controls=row_controls,
                                spacing=8,
                                alignment=ft.MainAxisAlignment.START,
                                expand=True,
                            ),
                            expand=True,
                            on_click=self._make_open_handler(exam_id),
                            ink=True,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color="#EF5350",
                            tooltip=t("delete_exam"),
                            on_click=self._make_delete_exam_handler(exam_id, name),
                        ),
                    ],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.padding.symmetric(horizontal=4, vertical=4),
                border_radius=6,
                bgcolor=self.theme.background,
            )

            self._exam_list_column.controls.append(row)

    def _make_open_handler(self, exam_id: int) -> Callable:
        """Return a click handler that calls ``on_exam_ready(exam_id)``.

        Requirement 4.5
        """

        def handler(e: ft.ControlEvent) -> None:
            self.on_exam_ready(exam_id)

        return handler

    def _make_delete_exam_handler(self, exam_id: int, name: str) -> Callable:
        """Return a click handler that confirms and deletes an exam."""

        def handler(e: ft.ControlEvent) -> None:
            if self._page is not None:
                self._page.run_task(self._confirm_delete_exam, exam_id, name)

        return handler

    async def _confirm_delete_exam(self, exam_id: int, name: str) -> None:
        """Show a confirmation dialog then delete the exam."""
        if self._page is None:
            return

        confirmed: asyncio.Future[bool] = asyncio.get_event_loop().create_future()

        def on_confirm(_: ft.ControlEvent) -> None:
            dialog.open = False
            self._page.update()
            if not confirmed.done():
                confirmed.set_result(True)

        def on_cancel(_: ft.ControlEvent) -> None:
            dialog.open = False
            self._page.update()
            if not confirmed.done():
                confirmed.set_result(False)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(t("delete_exam")),
            content=ft.Text(f'"{name}" — {t("delete_confirm")}'),
            actions=[
                ft.TextButton(text=t("cancel"), on_click=on_cancel),
                ft.TextButton(
                    text=t("delete"),
                    style=ft.ButtonStyle(color="#EF5350"),
                    on_click=on_confirm,
                ),
            ],
        )
        self._page.dialog = dialog
        dialog.open = True
        self._page.update()

        if not await confirmed:
            return

        try:
            await self.api.delete_exam(exam_id)
            await self.load()
        except APIError as err:
            if self._page is not None:
                self._page.snack_bar = ft.SnackBar(
                    content=ft.Text(err.message), open=True
                )
                self._page.update()

    # ------------------------------------------------------------------
    # Private helpers — form
    # ------------------------------------------------------------------

    def _validate_form(self) -> bool:
        """Validate Section A fields inline.

        Sets ``error`` on offending fields and returns ``True`` only when all
        fields are valid.  Makes no API call.

        Requirement 4.3
        """
        valid = True

        # Exam name — must not be blank
        name_val = (self._name_field.value or "").strip()
        if not name_val:
            self._name_field.error = ft.Text(t("error_required"))
            valid = False
        else:
            self._name_field.error = None

        # Questions count — must be a positive integer
        questions_val = (self._questions_field.value or "").strip()
        if not _is_positive_int(questions_val):
            self._questions_field.error = ft.Text(t("error_positive_int"))
            valid = False
        else:
            self._questions_field.error = None

        # Symbolic note — must be a positive integer
        note_val = (self._note_field.value or "").strip()
        if not _is_positive_int(note_val):
            self._note_field.error = ft.Text(t("error_positive_int"))
            valid = False
        else:
            self._note_field.error = None

        # Flush field error state to the UI
        if self._page is not None:
            try:
                self._page.update()
            except Exception:
                pass

        return valid

    def _on_refresh_clicked(self, e: ft.ControlEvent) -> None:
        """Dispatch the async ``load()`` call from a sync click handler."""
        if self._page is not None:
            self._page.run_task(self.load)

    def _on_create_clicked_sync(self, e: ft.ControlEvent) -> None:
        """Dispatch the async create flow from a sync click handler."""
        if self._page is not None:
            self._page.run_task(self._on_create_clicked)

    async def _on_create_clicked(self) -> None:
        """Validate the form and, if valid, call ``create_exam``.

        Requirements: 4.3, 4.4
        """
        if not self._validate_form():
            return

        name = (self._name_field.value or "").strip()
        questions = int((self._questions_field.value or "").strip())
        note = int((self._note_field.value or "").strip())

        # Parse weight mode
        weight_mode = "default"
        heavy_questions: list[int] | None = None
        if self._weight_mode_group is not None:
            weight_mode = self._weight_mode_group.value or "default"
        if weight_mode == "custom" and self._custom_weights_field is not None:
            raw = (self._custom_weights_field.value or "").strip()
            heavy_questions = _parse_question_numbers(raw, questions)
            if not heavy_questions:
                weight_mode = "default"

        # Disable button while the request is in flight
        if self._create_button is not None:
            self._create_button.disabled = True
            if self._page is not None:
                try:
                    self._page.update()
                except Exception:
                    pass

        try:
            new_exam = await self.api.create_exam(
                name=name,
                questions_numbers=questions,
                symbolic_note=note,
                weight_mode=weight_mode,
                heavy_questions=heavy_questions,
            )
            exam_id: int = new_exam.get("exam_id") or new_exam.get("id", 0)
            self.on_exam_ready(exam_id)
        except APIError as err:
            if self._page is not None:
                self._page.snack_bar = ft.SnackBar(
                    content=ft.Text(err.message), open=True
                )
                try:
                    self._page.update()
                except Exception:
                    pass
        finally:
            if self._create_button is not None:
                self._create_button.disabled = False
            if self._page is not None:
                try:
                    self._page.update()
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _is_positive_int(value: str) -> bool:
    """Return ``True`` if *value* represents a positive integer (> 0)."""
    try:
        return int(value) > 0
    except (ValueError, TypeError):
        return False


def _parse_question_numbers(raw: str, max_q: int) -> list[int]:
    """
    Parse a string like "1, 5, 10-15" into a sorted list of question numbers.

    Supports:
      - Single numbers: "1, 5, 10"
      - Ranges:         "10-15"  → [10, 11, 12, 13, 14, 15]
      - Mixed:          "1, 5, 10-15"

    Numbers outside [1, max_q] are silently ignored.
    Returns an empty list if nothing valid is found.
    """
    result: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            # Range like "10-15"
            bounds = part.split("-", 1)
            try:
                lo, hi = int(bounds[0].strip()), int(bounds[1].strip())
                for n in range(lo, hi + 1):
                    if 1 <= n <= max_q:
                        result.add(n)
            except (ValueError, IndexError):
                pass
        else:
            try:
                n = int(part)
                if 1 <= n <= max_q:
                    result.add(n)
            except ValueError:
                pass
    return sorted(result)
