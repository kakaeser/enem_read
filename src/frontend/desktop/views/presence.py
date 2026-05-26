"""
PresenceView — attendance management view.

Renders each participant as a row with a name (clickable) and a presence
toggle (ft.Switch).  Supports optimistic UI: the switch is flipped
immediately and reverted if the API call fails.

When read_only=True all switches are disabled and the "Import Participants"
button is hidden; clicking a participant name still opens
ParticipantDetailView.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

import flet as ft

from frontend.desktop.api_client import APIClient, APIError
from frontend.desktop.i18n import t
from frontend.desktop.theme import ThemeConfig


class PresenceView:
    """Attendance management view with per-participant presence toggles.

    Parameters
    ----------
    api:
        Async HTTP client used to call ``list_participants`` and
        ``update_participant``.
    exam_id:
        The exam whose participants are displayed.
    theme:
        Active ``ThemeConfig`` for colour styling.
    read_only:
        When ``True`` all toggles are disabled and the import button is
        hidden.  Clicking a participant name still opens
        ``ParticipantDetailView`` (Requirement 6.4, 6.5).
    """

    def __init__(
        self,
        api: APIClient,
        exam_id: int,
        theme: ThemeConfig,
        read_only: bool = False,
    ) -> None:
        self.api = api
        self.exam_id = exam_id
        self.theme = theme
        self.read_only = read_only

        # Data
        self._participants: list[dict] = []

        # Controls (populated in build())
        self._list_column: Optional[ft.Column] = None
        self._import_button: Optional[ft.ElevatedButton] = None
        self._add_button: Optional[ft.ElevatedButton] = None
        self._add_name_field: Optional[ft.TextField] = None
        self._add_row: Optional[ft.Row] = None
        self._file_picker: Optional[ft.FilePicker] = None
        self._page: Optional[ft.Page] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def load(self) -> None:
        """Fetch participants and rebuild the list.

        Requirement 6.1
        """
        try:
            self._participants = await self.api.list_participants(self.exam_id)
        except APIError:
            self._participants = []

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

        # ---- FilePicker (registered on the page overlay) --------------
        self._file_picker = ft.FilePicker(on_result=self._on_file_picked)
        if self._page is not None:
            self._page.overlay.append(self._file_picker)

        # ---- Import button (hidden in read_only mode) -----------------
        self._import_button = ft.ElevatedButton(
            text=t("import_participants"),
            icon=ft.Icons.UPLOAD_FILE,
            on_click=self._on_import_clicked,
            bgcolor=self.theme.primary,
            color=self.theme.on_primary,
            visible=not self.read_only,  # Requirement 6.4
        )

        # ---- Add participant manually (hidden in read_only mode) ------
        self._add_name_field = ft.TextField(
            hint_text=t("name"),
            expand=True,
            dense=True,
            visible=not self.read_only,
        )
        self._add_button = ft.ElevatedButton(
            text=t("add_participant"),
            icon=ft.Icons.PERSON_ADD,
            on_click=self._on_add_participant_clicked,
            bgcolor=self.theme.primary,
            color=self.theme.on_primary,
            visible=not self.read_only,
        )
        self._add_row = ft.Row(
            controls=[self._add_name_field, self._add_button],
            spacing=8,
            visible=not self.read_only,
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
                    t("presence"),
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=self.theme.on_background,
                ),
                ft.Row(
                    controls=[self._import_button, refresh_button],
                    spacing=8,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # ---- Participant list -----------------------------------------
        self._list_column = ft.Column(
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        self._rebuild_list()

        # ---- Assemble -------------------------------------------------
        return ft.Container(
            expand=True,
            bgcolor=self.theme.background,
            padding=24,
            content=ft.Column(
                controls=[
                    header_row,
                    self._add_row,
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
        """Repopulate ``_list_column`` from ``self._participants``.

        Requirement 6.1
        """
        if self._list_column is None:
            return

        self._list_column.controls.clear()

        if not self._participants:
            self._list_column.controls.append(
                ft.Text(
                    t("no_exams"),  # generic empty-state fallback
                    color=self.theme.on_background,
                    opacity=0.6,
                    italic=True,
                )
            )
            return

        for participant in self._participants:
            row = self._build_participant_row(participant)
            self._list_column.controls.append(row)

    def _build_participant_row(self, participant: dict) -> ft.Control:
        """Build a single participant row: name (clickable) + Switch.

        Requirements: 6.1, 6.2, 6.4, 6.5
        """
        participant_id: int = participant.get("id", 0)
        name: str = participant.get("nome") or participant.get("name") or str(participant_id)
        presente: bool = bool(participant.get("presente", False))

        # ---- Presence switch -----------------------------------------
        switch = ft.Switch(
            value=presente,
            active_color=self.theme.primary,
            disabled=self.read_only,  # Requirement 6.4
            on_change=self._make_toggle_handler(participant_id, switch_ref=None),
        )
        # Re-assign on_change with the actual switch reference so the
        # handler can revert it on error (Requirement 6.3)
        switch.on_change = self._make_toggle_handler(participant_id, switch_ref=switch)

        # ---- Name label (clickable) ----------------------------------
        name_label = ft.TextButton(
            text=name,
            style=ft.ButtonStyle(
                color=self.theme.on_background,
                overlay_color=ft.colors.with_opacity(0.08, self.theme.primary),
            ),
            on_click=self._make_name_click_handler(participant_id),
        )

        # ---- Row container -------------------------------------------
        return ft.Container(
            content=ft.Row(
                controls=[
                    name_label,
                    ft.Container(expand=True),  # spacer
                    ft.Text(
                        t("present"),
                        size=12,
                        color=self.theme.on_background,
                        opacity=0.7,
                    ),
                    switch,
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color="#EF5350",
                        tooltip=t("delete_participant"),
                        visible=not self.read_only,
                        on_click=self._make_delete_handler(participant_id, name),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=self.theme.surface,
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
        )

    # ------------------------------------------------------------------
    # Private helpers — event handlers
    # ------------------------------------------------------------------

    def _make_toggle_handler(
        self, participant_id: int, switch_ref: Optional[ft.Switch]
    ) -> Callable:
        """Return an on_change handler for a participant's Switch.

        Implements optimistic UI (Requirements 6.2, 6.3).
        """

        def handler(e: ft.ControlEvent) -> None:
            if self._page is not None:
                self._page.run_task(
                    self._toggle_presence,
                    participant_id,
                    e.control,
                    e.control.value,
                )

        return handler

    async def _toggle_presence(
        self,
        participant_id: int,
        switch: ft.Switch,
        new_value: bool,
    ) -> None:
        """Call update_participant; revert switch on error.

        Requirements: 6.2, 6.3
        """
        # Optimistic UI: switch is already flipped by Flet before this runs.
        # Record the previous value for potential revert.
        previous_value = not new_value

        try:
            await self.api.update_participant(
                participant_id, {"presente": new_value}
            )
            # Update local cache so a rebuild reflects the new state
            for p in self._participants:
                if p.get("id") == participant_id:
                    p["presente"] = new_value
                    break
        except APIError as err:
            # Requirement 6.3 — revert the switch
            switch.value = previous_value
            if self._page is not None:
                self._page.snack_bar = ft.SnackBar(
                    content=ft.Text(err.message), open=True
                )
            try:
                switch.update()
            except Exception:
                pass
            if self._page is not None:
                try:
                    self._page.update()
                except Exception:
                    pass

    def _make_name_click_handler(self, participant_id: int) -> Callable:
        """Return a click handler that opens ParticipantDetailView.

        Requirement 6.5
        """

        def handler(e: ft.ControlEvent) -> None:
            if self._page is not None:
                self._page.run_task(
                    self._open_participant_detail, participant_id
                )

        return handler

    async def _open_participant_detail(self, participant_id: int) -> None:
        """Lazily import and open ParticipantDetailView as a page overlay.

        Uses a local import to avoid circular dependencies since
        participant_detail.py may not exist yet (Requirement 6.5).
        """
        if self._page is None:
            return

        # Determine rank position from results (best-effort; 0 if unavailable)
        rank_position = 0
        try:
            results = await self.api.get_exam_results(self.exam_id)
            sorted_results = sorted(
                results,
                key=lambda r: r.get("final_score") or r.get("score") or 0,
                reverse=True,
            )
            for idx, entry in enumerate(sorted_results, start=1):
                if (
                    entry.get("participant_id") == participant_id
                    or entry.get("id") == participant_id
                ):
                    rank_position = idx
                    break
        except APIError:
            pass

        # Lazy import to avoid circular dependency at module load time
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
                        border_radius=ft.border_radius.only(
                            top_left=12, bottom_left=12
                        ),
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
    # Private helpers — delete participant
    # ------------------------------------------------------------------

    def _make_delete_handler(self, participant_id: int, name: str) -> Callable:
        """Return a click handler that confirms and deletes a participant."""

        def handler(e: ft.ControlEvent) -> None:
            if self._page is not None:
                self._page.run_task(self._confirm_delete_participant, participant_id, name)

        return handler

    async def _confirm_delete_participant(self, participant_id: int, name: str) -> None:
        """Show a confirmation dialog then delete the participant."""
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
            title=ft.Text(t("delete_participant")),
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
            await self.api.delete_participant(participant_id)
            await self.load()
        except APIError as err:
            if self._page is not None:
                self._page.snack_bar = ft.SnackBar(
                    content=ft.Text(err.message), open=True
                )
                self._page.update()

    # ------------------------------------------------------------------
    # Private helpers — add participant manually
    # ------------------------------------------------------------------

    def _on_add_participant_clicked(self, e: ft.ControlEvent) -> None:
        """Dispatch the async add participant call from a sync click handler."""
        if self._page is not None:
            self._page.run_task(self._add_participant_manually)

    async def _add_participant_manually(self) -> None:
        """Call api.add_participant with the name from the text field."""
        if self._add_name_field is None:
            return

        name = (self._add_name_field.value or "").strip()
        if not name:
            if self._page is not None:
                self._page.snack_bar = ft.SnackBar(
                    content=ft.Text(t("error_required")), open=True
                )
                self._page.update()
            return

        if self._add_button is not None:
            self._add_button.disabled = True
            try:
                self._add_button.update()
            except Exception:
                pass

        try:
            await self.api.add_participant(self.exam_id, name)
            self._add_name_field.value = ""
            try:
                self._add_name_field.update()
            except Exception:
                pass
            # Reload the list to show the new participant
            await self.load()
        except APIError as err:
            if self._page is not None:
                self._page.snack_bar = ft.SnackBar(
                    content=ft.Text(err.message), open=True
                )
                self._page.update()
        finally:
            if self._add_button is not None:
                self._add_button.disabled = False
                try:
                    self._add_button.update()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Private helpers — import
    # ------------------------------------------------------------------

    def _on_import_clicked(self, e: ft.ControlEvent) -> None:
        """Open the FilePicker to select a CSV / Excel file."""
        if self._file_picker is not None:
            self._file_picker.pick_files(
                dialog_title=t("import_participants"),
                allowed_extensions=["csv", "xlsx", "xls"],
                allow_multiple=False,
            )

    def _on_file_picked(self, e: ft.FilePickerResultEvent) -> None:
        """Dispatch the async import after the user selects a file."""
        if e.files and len(e.files) > 0:
            file_path = e.files[0].path
            if file_path and self._page is not None:
                self._page.run_task(self._import_participants, file_path)

    async def _import_participants(self, file_path: str) -> None:
        """Call api.import_participants and show a summary snackbar."""
        if self._import_button is not None:
            self._import_button.disabled = True
            try:
                self._import_button.update()
            except Exception:
                pass

        try:
            result = await self.api.import_participants(self.exam_id, file_path)
            imported: int = result.get("imported", 0)
            skipped: int = result.get("skipped", 0)
            errors: list = result.get("errors", [])

            summary = f"{imported} {t('import_participants')} ✓"
            if skipped:
                summary += f", {skipped} skipped"
            if errors:
                summary += f", {len(errors)} errors"

            if self._page is not None:
                self._page.snack_bar = ft.SnackBar(
                    content=ft.Text(summary), open=True
                )

            # Reload the participant list to reflect any new entries
            await self.load()

        except APIError as err:
            if self._page is not None:
                self._page.snack_bar = ft.SnackBar(
                    content=ft.Text(err.message), open=True
                )
            if self._page is not None:
                try:
                    self._page.update()
                except Exception:
                    pass
        finally:
            if self._import_button is not None:
                self._import_button.disabled = False
                try:
                    self._import_button.update()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Private helpers — refresh
    # ------------------------------------------------------------------

    def _on_refresh_clicked(self, e: ft.ControlEvent) -> None:
        """Dispatch the async ``load()`` call from a sync click handler."""
        if self._page is not None:
            self._page.run_task(self.load)
