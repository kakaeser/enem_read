"""
DashboardView — ranked participant table and aggregate statistics.

Displays a ft.DataTable with Rank, Name, Score, Accuracy % columns,
aggregate stats (avg/highest/lowest) above the table, and a refresh button.
Clicking a participant row opens ParticipantDetailView.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft

from frontend.desktop.api_client import APIClient, APIError
from frontend.desktop.i18n import t
from frontend.desktop.theme import ThemeConfig


class DashboardView:
    """Ranked participant table with aggregate statistics.

    Parameters
    ----------
    api:
        Async HTTP client used to call ``get_exam_results`` and
        ``get_exam_statistics``.
    exam_id:
        The exam whose results are displayed.
    theme:
        Active ``ThemeConfig`` for colour styling.
    read_only:
        When ``True`` the view is in read-only mode.  Row clicks still open
        ``ParticipantDetailView`` (Requirement 5.5).
    on_participant_click:
        Optional callback invoked with ``(participant_id, exam_id)`` when a
        row is clicked.  If omitted the view performs a lazy import of
        ``ParticipantDetailView`` and opens it directly via ``page.overlay``.
    """

    def __init__(
        self,
        api: APIClient,
        exam_id: int,
        theme: ThemeConfig,
        read_only: bool = False,
        on_participant_click: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        self.api = api
        self.exam_id = exam_id
        self.theme = theme
        self.read_only = read_only
        self.on_participant_click = on_participant_click

        # Data
        self._results: list[dict] = []
        self._statistics: dict = {}

        # Controls (populated in build())
        self._stats_row: Optional[ft.Row] = None
        self._data_table: Optional[ft.DataTable] = None
        self._table_container: Optional[ft.Column] = None
        self._page: Optional[ft.Page] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def load(self) -> None:
        """Fetch results and statistics, then rebuild the table.

        Requirements: 5.1, 5.2, 5.3
        """
        try:
            self._results = await self.api.get_exam_results(self.exam_id)
        except APIError:
            self._results = []

        try:
            self._statistics = await self.api.get_exam_statistics(self.exam_id)
        except APIError:
            self._statistics = {}

        self._rebuild_stats()
        self._rebuild_table()

        if self._table_container is not None and self._page is not None:
            try:
                self._table_container.update()
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
            and overlay management.  If omitted the caller must set
            ``view._page`` before any user interaction occurs.
        """
        if page is not None:
            self._page = page

        # ---- Stats row ------------------------------------------------
        self._stats_row = ft.Row(
            controls=self._build_stat_chips(),
            spacing=16,
            wrap=True,
        )

        # ---- DataTable ------------------------------------------------
        self._data_table = ft.DataTable(
            columns=self._build_columns(),
            rows=[],
            border=ft.border.all(1, self.theme.surface),
            border_radius=8,
            heading_row_color=self.theme.surface,
            heading_row_height=48,
            data_row_min_height=44,
            column_spacing=24,
            expand=True,
        )

        # ---- Refresh button -------------------------------------------
        refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip=t("refresh"),
            on_click=self._on_refresh_clicked,
            icon_color=self.theme.secondary,
        )

        # ---- Header row -----------------------------------------------
        header_row = ft.Row(
            controls=[
                ft.Text(
                    t("dashboard"),
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=self.theme.on_background,
                ),
                refresh_button,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # ---- Scrollable table wrapper ---------------------------------
        table_scroll = ft.Row(
            controls=[self._data_table],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        # ---- Assemble -------------------------------------------------
        self._table_container = ft.Column(
            controls=[
                header_row,
                self._stats_row,
                ft.Divider(color=self.theme.surface, height=1),
                table_scroll,
            ],
            spacing=16,
            expand=True,
        )

        return ft.Container(
            expand=True,
            bgcolor=self.theme.background,
            padding=24,
            content=self._table_container,
        )

    # ------------------------------------------------------------------
    # Private helpers — columns
    # ------------------------------------------------------------------

    def _build_columns(self) -> list[ft.DataColumn]:
        """Build the four DataTable columns.

        Requirement 5.1
        """
        return [
            ft.DataColumn(
                ft.Text(
                    t("rank"),
                    weight=ft.FontWeight.BOLD,
                    color=self.theme.on_background,
                )
            ),
            ft.DataColumn(
                ft.Text(
                    t("name"),
                    weight=ft.FontWeight.BOLD,
                    color=self.theme.on_background,
                )
            ),
            ft.DataColumn(
                ft.Text(
                    t("score"),
                    weight=ft.FontWeight.BOLD,
                    color=self.theme.on_background,
                ),
                numeric=True,
            ),
            ft.DataColumn(
                ft.Text(
                    t("accuracy"),
                    weight=ft.FontWeight.BOLD,
                    color=self.theme.on_background,
                ),
                numeric=True,
            ),
        ]

    # ------------------------------------------------------------------
    # Private helpers — stats
    # ------------------------------------------------------------------

    def _build_stat_chips(self) -> list[ft.Control]:
        """Build stat chip controls from ``self._statistics``.

        Requirement 5.2
        """
        avg = self._statistics.get("average_score")
        highest = self._statistics.get("highest_score")
        lowest = self._statistics.get("lowest_score")

        def _chip(label: str, value: object) -> ft.Container:
            display = f"{value:.2f}" if isinstance(value, float) else (str(value) if value is not None else "—")
            return ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(label, size=11, color=self.theme.on_background, opacity=0.7),
                        ft.Text(display, size=16, weight=ft.FontWeight.BOLD, color=self.theme.secondary),
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=self.theme.surface,
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
            )

        return [
            _chip("Ø " + t("score"), avg),
            _chip("▲ " + t("score"), highest),
            _chip("▼ " + t("score"), lowest),
        ]

    def _rebuild_stats(self) -> None:
        """Refresh the stats row controls in-place."""
        if self._stats_row is None:
            return
        self._stats_row.controls = self._build_stat_chips()

    # ------------------------------------------------------------------
    # Private helpers — table rows
    # ------------------------------------------------------------------

    def _rebuild_table(self) -> None:
        """Repopulate ``_data_table.rows`` from ``self._results``.

        Requirements: 5.1, 5.4, 5.5
        """
        if self._data_table is None:
            return

        self._data_table.rows.clear()

        # Sort by score descending to assign rank
        sorted_results = sorted(
            self._results,
            key=lambda r: r.get("final_score") or r.get("score") or 0,
            reverse=True,
        )

        for rank, entry in enumerate(sorted_results, start=1):
            participant_id: int = entry.get("participant_id") or entry.get("id") or 0
            name: str = entry.get("participant_name") or entry.get("nome") or str(participant_id)
            score = entry.get("final_score") or entry.get("score") or 0
            accuracy = entry.get("accuracy_percent") or entry.get("accuracy") or 0

            score_str = f"{score:.2f}" if isinstance(score, float) else str(score)
            accuracy_str = f"{accuracy:.1f}%" if isinstance(accuracy, (int, float)) else str(accuracy)

            row = ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(rank), color=self.theme.on_background)),
                    ft.DataCell(ft.Text(name, color=self.theme.on_background)),
                    ft.DataCell(ft.Text(score_str, color=self.theme.on_background)),
                    ft.DataCell(ft.Text(accuracy_str, color=self.theme.on_background)),
                ],
                on_select_change=self._make_row_click_handler(
                    participant_id=participant_id,
                    rank_position=rank,
                ),
            )
            self._data_table.rows.append(row)

    def _make_row_click_handler(
        self, participant_id: int, rank_position: int
    ) -> Callable:
        """Return a click handler for a participant row.

        Requirements: 5.4, 5.5
        """

        def handler(e: ft.ControlEvent) -> None:
            if self.on_participant_click is not None:
                # Caller-supplied callback (avoids circular import entirely)
                self.on_participant_click(participant_id, self.exam_id)
            else:
                # Lazy import to avoid circular dependency
                if self._page is not None:
                    self._page.run_task(
                        self._open_participant_detail,
                        participant_id,
                        rank_position,
                    )

        return handler

    async def _open_participant_detail(
        self, participant_id: int, rank_position: int
    ) -> None:
        """Lazily import and open ParticipantDetailView as a page overlay.

        Requirements: 5.4, 5.5
        """
        if self._page is None:
            return

        # Lazy import prevents circular dependency at module load time
        from frontend.desktop.views.participant_detail import ParticipantDetailView  # noqa: PLC0415

        def on_close() -> None:
            if overlay_container in self._page.overlay:
                self._page.overlay.remove(overlay_container)
            try:
                self._page.update()
            except Exception:
                pass

        detail_view = ParticipantDetailView(
            api=self.api,
            participant_id=participant_id,
            exam_id=self.exam_id,
            rank_position=rank_position,
            theme=self.theme,
            on_close=on_close,
            read_only=self.read_only,
        )

        overlay_container = ft.Container(
            expand=True,
            bgcolor=ft.colors.with_opacity(0.6, "#000000"),
            content=ft.Row(
                controls=[
                    ft.Container(expand=True),  # left spacer
                    ft.Container(
                        width=600,
                        expand=False,
                        bgcolor=self.theme.background,
                        border_radius=ft.border_radius.only(top_left=12, bottom_left=12),
                        content=detail_view.build(page=self._page),
                    ),
                ],
                expand=True,
            ),
        )

        self._page.overlay.append(overlay_container)
        self._page.update()

        await detail_view.load()

    # ------------------------------------------------------------------
    # Private helpers — event handlers
    # ------------------------------------------------------------------

    def _on_refresh_clicked(self, e: ft.ControlEvent) -> None:
        """Dispatch the async ``load()`` call from a sync click handler.

        Requirement 5.3
        """
        if self._page is not None:
            self._page.run_task(self.load)
