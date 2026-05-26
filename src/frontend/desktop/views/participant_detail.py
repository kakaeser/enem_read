"""
ParticipantDetailView — per-participant score and answer breakdown overlay.

Displays the participant's name, rank badge, final score, score breakdown row,
and a per-question DataTable.  Supports editing essay points with validation.

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

import flet as ft

from frontend.desktop.api_client import APIClient, APIError
from frontend.desktop.i18n import t
from frontend.desktop.theme import ThemeConfig


class ParticipantDetailView:
    """Per-participant score and answer breakdown panel.

    Parameters
    ----------
    api:
        Async HTTP client used to call ``get_participant_score``,
        ``get_participant_responses``, and ``update_participant``.
    participant_id:
        The participant whose detail is shown.
    exam_id:
        The exam the participant belongs to.
    rank_position:
        The participant's rank in the sorted results list (1-based).
    theme:
        Active ``ThemeConfig`` for colour styling.
    on_close:
        Callback invoked when the close button is clicked.
    read_only:
        When ``True`` the essay points field is read-only and the save
        button is hidden (Requirement 7.5).
    """

    def __init__(
        self,
        api: APIClient,
        participant_id: int,
        exam_id: int,
        rank_position: int,
        theme: ThemeConfig,
        on_close: Callable[[], None],
        read_only: bool = False,
    ) -> None:
        self.api = api
        self.participant_id = participant_id
        self.exam_id = exam_id
        self.rank_position = rank_position
        self.theme = theme
        self.on_close = on_close
        self.read_only = read_only

        # Data (populated in load())
        self._score: dict = {}
        self._responses: list[dict] = []

        # Controls (populated in build())
        self._header_row: Optional[ft.Row] = None
        self._breakdown_row: Optional[ft.Row] = None
        self._essay_field: Optional[ft.TextField] = None
        self._save_button: Optional[ft.ElevatedButton] = None
        self._question_table: Optional[ft.DataTable] = None
        self._content_column: Optional[ft.Column] = None
        self._page: Optional[ft.Page] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def load(self) -> None:
        """Fetch score and responses in parallel, then rebuild the UI.

        Uses ``asyncio.gather`` for parallel API calls.

        Requirement 7.1
        """
        try:
            self._score, self._responses = await asyncio.gather(
                self.api.get_participant_score(self.exam_id, self.participant_id),
                self.api.get_participant_responses(self.exam_id, self.participant_id),
            )
        except APIError:
            self._score = {}
            self._responses = []

        self._rebuild_header()
        self._rebuild_breakdown()
        self._rebuild_question_table()

        if self._content_column is not None and self._page is not None:
            try:
                self._content_column.update()
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
            and snackbar display.  If omitted the caller must set
            ``view._page`` before any user interaction occurs.
        """
        if page is not None:
            self._page = page

        # ---- Header row (name, rank badge, score) --------------------
        self._header_row = ft.Row(
            controls=self._build_header_controls(),
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # ---- Score breakdown row -------------------------------------
        self._breakdown_row = ft.Row(
            controls=self._build_breakdown_controls(),
            spacing=16,
            wrap=True,
        )

        # ---- Essay points field + save button ------------------------
        self._essay_field = ft.TextField(
            label=t("essay_points"),
            value=str(self._score.get("essay_points") or ""),
            read_only=self.read_only,  # Requirement 7.5
            keyboard_type=ft.KeyboardType.NUMBER,
            width=180,
            color=self.theme.on_background,
            border_color=self.theme.secondary,
            focused_border_color=self.theme.primary,
            label_style=ft.TextStyle(color=self.theme.on_background),
        )

        self._save_button = ft.ElevatedButton(
            text=t("save"),
            icon=ft.Icons.SAVE,
            on_click=self._on_save_clicked,
            bgcolor=self.theme.primary,
            color=self.theme.on_primary,
            visible=not self.read_only,  # Requirement 7.5
        )

        essay_row = ft.Row(
            controls=[self._essay_field, self._save_button],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # ---- Per-question DataTable ----------------------------------
        self._question_table = ft.DataTable(
            columns=self._build_table_columns(),
            rows=self._build_table_rows(),
            border=ft.border.all(1, self.theme.surface),
            border_radius=8,
            heading_row_color=self.theme.surface,
            heading_row_height=44,
            data_row_min_height=40,
            column_spacing=20,
            expand=True,
        )

        table_scroll = ft.Row(
            controls=[self._question_table],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        # ---- Close button -------------------------------------------
        close_button = ft.TextButton(
            text=t("close"),
            icon=ft.Icons.CLOSE,
            on_click=self._on_close_clicked,
            style=ft.ButtonStyle(color=self.theme.secondary),
        )

        # ---- Assemble -----------------------------------------------
        self._content_column = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            t("dashboard"),
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=self.theme.on_background,
                        ),
                        ft.Container(expand=True),
                        close_button,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(color=self.theme.surface, height=1),
                self._header_row,
                ft.Divider(color=self.theme.surface, height=1),
                self._breakdown_row,
                essay_row,
                ft.Divider(color=self.theme.surface, height=1),
                table_scroll,
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )

        return ft.Container(
            expand=True,
            bgcolor=self.theme.background,
            padding=24,
            content=self._content_column,
        )

    # ------------------------------------------------------------------
    # Private helpers — header
    # ------------------------------------------------------------------

    def _build_header_controls(self) -> list[ft.Control]:
        """Build name, rank badge, and final score controls.

        Requirement 7.1
        """
        name: str = (
            self._score.get("participant_name")
            or self._score.get("nome")
            or f"#{self.participant_id}"
        )
        final_score = self._score.get("final_score") or self._score.get("score") or 0
        score_str = f"{final_score:.2f}" if isinstance(final_score, float) else str(final_score)

        rank_badge = ft.Container(
            content=ft.Text(
                f"#{self.rank_position}",
                size=14,
                weight=ft.FontWeight.BOLD,
                color=self.theme.on_primary,
            ),
            bgcolor=self.theme.primary,
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=12, vertical=4),
        )

        return [
            ft.Row(
                controls=[
                    rank_badge,
                    ft.Text(
                        name,
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=self.theme.on_background,
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Text(
                score_str,
                size=24,
                weight=ft.FontWeight.BOLD,
                color=self.theme.secondary,
            ),
        ]

    def _rebuild_header(self) -> None:
        """Refresh the header row controls in-place."""
        if self._header_row is None:
            return
        self._header_row.controls = self._build_header_controls()

    # ------------------------------------------------------------------
    # Private helpers — breakdown row
    # ------------------------------------------------------------------

    def _build_breakdown_controls(self) -> list[ft.Control]:
        """Build score breakdown chip controls.

        Requirement 7.1
        """
        normalized = self._score.get("normalized_score") or self._score.get("final_score") or 0
        essay_pts = self._score.get("essay_points") or 0
        correct = self._score.get("correct_count") or self._score.get("correct_answers") or 0
        total = self._score.get("total_questions") or len(self._responses) or 0
        accuracy = self._score.get("accuracy_percent") or self._score.get("accuracy") or 0

        def _chip(label: str, value: str) -> ft.Container:
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            label,
                            size=11,
                            color=self.theme.on_background,
                            opacity=0.7,
                        ),
                        ft.Text(
                            value,
                            size=15,
                            weight=ft.FontWeight.BOLD,
                            color=self.theme.secondary,
                        ),
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=self.theme.surface,
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=14, vertical=8),
            )

        norm_str = f"{normalized:.2f}" if isinstance(normalized, float) else str(normalized)
        essay_str = str(essay_pts) if essay_pts is not None else "—"
        correct_str = f"{correct}/{total}"
        accuracy_str = f"{accuracy:.1f}%" if isinstance(accuracy, (int, float)) else str(accuracy)

        return [
            _chip(t("score"), norm_str),
            _chip(t("essay_points"), essay_str),
            _chip(t("accuracy"), accuracy_str),
            _chip("✓/Total", correct_str),
        ]

    def _rebuild_breakdown(self) -> None:
        """Refresh the breakdown row controls in-place."""
        if self._breakdown_row is None:
            return
        self._breakdown_row.controls = self._build_breakdown_controls()

        # Also sync the essay field value
        if self._essay_field is not None:
            essay_pts = self._score.get("essay_points")
            self._essay_field.value = str(essay_pts) if essay_pts is not None else ""

    # ------------------------------------------------------------------
    # Private helpers — question table
    # ------------------------------------------------------------------

    def _build_table_columns(self) -> list[ft.DataColumn]:
        """Build the five DataTable columns.

        Requirement 7.2
        """
        def _col(label: str, numeric: bool = False) -> ft.DataColumn:
            return ft.DataColumn(
                ft.Text(
                    label,
                    weight=ft.FontWeight.BOLD,
                    color=self.theme.on_background,
                ),
                numeric=numeric,
            )

        return [
            _col("Q#", numeric=True),
            _col(t("correct_answer")),
            _col(t("marked_answer")),
            _col(t("result")),
            _col(t("weight"), numeric=True),
        ]

    def _build_table_rows(self) -> list[ft.DataRow]:
        """Build DataRow list from ``self._responses``.

        Requirement 7.2
        """
        rows: list[ft.DataRow] = []

        for resp in self._responses:
            q_num = resp.get("question_number") or resp.get("numero") or "?"
            correct_ans = resp.get("correct_answer") or "—"
            marked_ans = resp.get("marked_answer") or "—"
            is_correct = resp.get("correct")
            weight = resp.get("peso") or resp.get("weight") or 1

            # Result symbol: ✓ correct, ✗ wrong, — unknown/null
            if is_correct is None:
                result_symbol = "—"
                result_color = self.theme.on_background
            elif is_correct:
                result_symbol = "✓"
                result_color = "#4CAF50"  # green
            else:
                result_symbol = "✗"
                result_color = "#F44336"  # red

            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(
                            ft.Text(str(q_num), color=self.theme.on_background)
                        ),
                        ft.DataCell(
                            ft.Text(str(correct_ans), color=self.theme.on_background)
                        ),
                        ft.DataCell(
                            ft.Text(str(marked_ans), color=self.theme.on_background)
                        ),
                        ft.DataCell(
                            ft.Text(
                                result_symbol,
                                color=result_color,
                                weight=ft.FontWeight.BOLD,
                            )
                        ),
                        ft.DataCell(
                            ft.Text(str(weight), color=self.theme.on_background)
                        ),
                    ]
                )
            )

        return rows

    def _rebuild_question_table(self) -> None:
        """Repopulate ``_question_table.rows`` from ``self._responses``."""
        if self._question_table is None:
            return
        self._question_table.rows = self._build_table_rows()

    # ------------------------------------------------------------------
    # Private helpers — event handlers
    # ------------------------------------------------------------------

    def _on_close_clicked(self, e: ft.ControlEvent) -> None:
        """Invoke the on_close callback.

        Requirement 7.6
        """
        self.on_close()

    def _on_save_clicked(self, e: ft.ControlEvent) -> None:
        """Dispatch the async save flow from a sync click handler."""
        if self._page is not None:
            self._page.run_task(self._save_essay_points)

    async def _save_essay_points(self) -> None:
        """Validate and save essay points via the API.

        Requirements: 7.3, 7.4
        """
        raw_value = (self._essay_field.value or "").strip()

        # Requirement 7.4 — validate: must be a non-negative number
        try:
            value = float(raw_value)
            if value < 0:
                raise ValueError("negative")
        except (ValueError, TypeError):
            self._show_snackbar(t("error_essay_points"))
            return

        # Disable save button while request is in flight
        if self._save_button is not None:
            self._save_button.disabled = True
            try:
                self._save_button.update()
            except Exception:
                pass

        try:
            # Requirement 7.3 — call update_participant with essay_points
            await self.api.update_participant(
                self.participant_id, {"essay_points": value}
            )
            self._show_snackbar(t("saved"))
        except APIError as err:
            self._show_snackbar(err.message)
        finally:
            if self._save_button is not None:
                self._save_button.disabled = False
                try:
                    self._save_button.update()
                except Exception:
                    pass

    def _show_snackbar(self, message: str) -> None:
        """Display a snackbar on the page."""
        if self._page is not None:
            self._page.snack_bar = ft.SnackBar(
                content=ft.Text(message), open=True
            )
            try:
                self._page.update()
            except Exception:
                pass
