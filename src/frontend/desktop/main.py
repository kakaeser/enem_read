"""
main.py — Flet desktop app entry point for Enem da Read.

Startup flow:
  1. load_config()
  2. If no language saved → show LanguageSelectView → set_language + save_config
  3. If language saved → set_language directly
  4. Show loading indicator while APILauncher.start_if_needed() runs
     → on timeout show blocking error dialog with t("api_start_error")
  5. Start MobileServerLauncher → get mobile URL
  6. Show HomeView

openExamWorkspace(exam_id):
  - Fetch exam, determine read_only = exam["status"] == "completed"
  - Build tabbed layout: DashboardView + PresenceView + SharePanel
  - If read_only: show ReadOnlyBanner, hide EndExamButton
  - If not read_only: show EndExamButton that transitions workspace to read-only on success

page.on_disconnect / window close:
  - launcher.stop() and mobile_server.stop()

Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 11.1, 11.2, 11.3
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import flet as ft

from frontend.desktop.api_client import APIClient, APIError
from frontend.desktop.api_launcher import APILauncher
from frontend.desktop.app_config import load_config, save_config
from frontend.desktop.i18n import set_language, t
from frontend.desktop.mobile_server import MobileServerLauncher
from frontend.desktop.theme import THEMES, ThemeConfig
from frontend.desktop.views.components import (
    EndExamButton,
    LanguageSwitcher,
    ReadOnlyBanner,
    SharePanel,
)
from frontend.desktop.views.dashboard import DashboardView
from frontend.desktop.views.home import HomeView
from frontend.desktop.views.language_select import LanguageSelectView
from frontend.desktop.views.presence import PresenceView


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mobile_dir() -> str:
    """Return the absolute path to src/frontend/mobile/."""
    here = Path(__file__).resolve().parent          # src/frontend/desktop/
    return str(here.parent / "mobile")              # src/frontend/mobile/


# ---------------------------------------------------------------------------
# App class
# ---------------------------------------------------------------------------

class App:
    """Wires all desktop modules together and manages the Flet page lifecycle."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page

        # Config / theme
        self._config: dict = {}
        self._theme: ThemeConfig = THEMES["dark_blue"]

        # Infrastructure
        self._launcher: Optional[APILauncher] = None
        self._mobile_server: Optional[MobileServerLauncher] = None
        self._mobile_url: str = ""

        # API client (created after launcher is ready)
        self._api: Optional[APIClient] = None

        # Current workspace state
        self._current_exam_id: Optional[int] = None
        self._workspace_read_only: bool = False

        # Workspace view references (kept for read-only transition)
        self._dashboard_view: Optional[DashboardView] = None
        self._presence_view: Optional[PresenceView] = None

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Full startup sequence."""
        self.page.title = "Enem da Read"
        self.page.padding = 0
        self.page.spacing = 0
        self.page.bgcolor = "#0D1117"

        # Register window-close / disconnect handler (Requirement 1.4, 2.4)
        self.page.on_disconnect = self._on_disconnect

        # 1. Load persisted config
        self._config = load_config()
        theme_name = self._config.get("theme", "dark_blue")
        self._theme = THEMES.get(theme_name, THEMES["dark_blue"])

        # 2. Language selection (Requirements 11.1, 11.2, 11.3)
        saved_lang = self._config.get("language")
        if not saved_lang:
            # First launch — show language picker and wait
            await self._show_language_select()
        else:
            # Language already saved — apply directly (Requirement 11.3)
            set_language(saved_lang)

        # 3. Show loading indicator while API starts (Requirements 1.1, 1.2, 1.3)
        await self._start_api()

        # 4. Start mobile server (Requirements 2.1, 2.2)
        self._start_mobile_server()

        # 5. Show HomeView
        self._show_home()

    # ------------------------------------------------------------------
    # Language selection
    # ------------------------------------------------------------------

    async def _show_language_select(self) -> None:
        """Show LanguageSelectView and wait for the user to pick a language.

        Requirements: 11.1, 11.2
        """
        lang_chosen: asyncio.Future[str] = asyncio.get_event_loop().create_future()

        def on_language_selected(lang: str) -> None:
            if not lang_chosen.done():
                lang_chosen.set_result(lang)

        lang_view = LanguageSelectView(on_language_selected=on_language_selected)

        self.page.controls.clear()
        self.page.add(lang_view.build())
        self.page.update()

        # Wait until the user picks a language
        chosen_lang = await lang_chosen

        # Persist and apply (Requirement 11.2)
        set_language(chosen_lang)
        self._config["language"] = chosen_lang
        self._config.setdefault("theme", "dark_blue")
        save_config(self._config)

    # ------------------------------------------------------------------
    # API startup
    # ------------------------------------------------------------------

    async def _start_api(self) -> None:
        """Show a loading indicator, start the API, handle timeout error.

        Requirements: 1.1, 1.2, 1.3
        """
        # Show loading indicator
        loading = ft.Container(
            expand=True,
            alignment=ft.alignment.center,
            bgcolor=self._theme.background,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=24,
                controls=[
                    ft.ProgressRing(color=self._theme.primary),
                    ft.Text(
                        t("connecting"),
                        size=16,
                        color=self._theme.on_background,
                    ),
                ],
            ),
        )
        self.page.controls.clear()
        self.page.add(loading)
        self.page.update()

        self._launcher = APILauncher()
        try:
            await self._launcher.start_if_needed()
        except RuntimeError:
            # Requirement 1.3 — blocking error dialog
            await self._show_api_error_dialog()
            return

        # API is up — create the client
        self._api = APIClient()

    async def _show_api_error_dialog(self) -> None:
        """Show a blocking error dialog when the API fails to start.

        Requirement 1.3
        """
        dialog_closed: asyncio.Future[None] = asyncio.get_event_loop().create_future()

        def on_ok(_: ft.ControlEvent) -> None:
            dialog.open = False
            self.page.update()
            if not dialog_closed.done():
                dialog_closed.set_result(None)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(t("api_start_error")),
            content=ft.Text(t("api_start_error")),
            actions=[
                ft.TextButton(text="OK", on_click=on_ok),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

        await dialog_closed

    # ------------------------------------------------------------------
    # Mobile server
    # ------------------------------------------------------------------

    def _start_mobile_server(self) -> None:
        """Start the mobile static file server and capture the URL.

        Requirements: 2.1, 2.2
        """
        mobile_dir = _mobile_dir()
        self._mobile_server = MobileServerLauncher(mobile_dir=mobile_dir, port=8080)
        try:
            self._mobile_url = self._mobile_server.start()
        except OSError:
            # All ports in use — fall back gracefully
            self._mobile_url = "http://127.0.0.1:8080/index.html"

        # Show snackbar warning if server fell back to localhost (Requirement 2.2)
        if self._mobile_url.startswith("http://127.0.0.1"):
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(t("mobile_server_warning")),
                open=True,
            )
            self.page.update()

    # ------------------------------------------------------------------
    # HomeView
    # ------------------------------------------------------------------

    def _show_home(self) -> None:
        """Replace page content with HomeView."""
        if self._api is None:
            return

        home = HomeView(
            api=self._api,
            theme=self._theme,
            on_exam_ready=self._open_exam_workspace,
        )

        self.page.controls.clear()
        self.page.add(home.build(page=self.page))
        self.page.update()

        # Load exam list asynchronously
        self.page.run_task(home.load)

    # ------------------------------------------------------------------
    # Exam workspace
    # ------------------------------------------------------------------

    def _open_exam_workspace(self, exam_id: int) -> None:
        """Sync wrapper — dispatches the async workspace builder."""
        self.page.run_task(self._build_exam_workspace, exam_id)

    async def _build_exam_workspace(self, exam_id: int) -> None:
        """Fetch exam, determine read_only, build and show the workspace.

        Requirements: 1.1, 2.1, 8.5
        """
        if self._api is None:
            return

        self._current_exam_id = exam_id

        # Fetch exam to determine read_only status
        exam: dict = {}
        try:
            exams = await self._api.list_exams()
            for e in exams:
                if e.get("id") == exam_id:
                    exam = e
                    break
        except APIError:
            pass

        read_only = exam.get("status") == "completed"
        self._workspace_read_only = read_only

        # Build views
        self._dashboard_view = DashboardView(
            api=self._api,
            exam_id=exam_id,
            theme=self._theme,
            read_only=read_only,
        )
        self._presence_view = PresenceView(
            api=self._api,
            exam_id=exam_id,
            theme=self._theme,
            read_only=read_only,
        )

        # Build the workspace layout and show it
        workspace = self._build_workspace_layout(exam, read_only)
        self.page.controls.clear()
        self.page.add(workspace)
        self.page.update()

        # Load data for both views
        await asyncio.gather(
            self._dashboard_view.load(),
            self._presence_view.load(),
        )

    def _build_workspace_layout(self, exam: dict, read_only: bool) -> ft.Control:
        """Build the full workspace layout with tabs, header, and banners.

        Returns a Flet control tree containing:
        - Top bar: app title, SharePanel, LanguageSwitcher
        - ReadOnlyBanner (if read_only) or EndExamButton (if not)
        - Tab bar: Dashboard | Presence
        """
        assert self._dashboard_view is not None
        assert self._presence_view is not None

        exam_name: str = (
            exam.get("exam_name") or exam.get("name") or f"Exam #{exam.get('id', '')}"
        )

        # ---- Tab content (built once; toggled via visibility) --------
        dashboard_content = self._dashboard_view.build(page=self.page)
        presence_content = self._presence_view.build(page=self.page)

        # Wrap each tab in a Container so we can toggle visibility
        dashboard_container = ft.Container(
            content=dashboard_content,
            expand=True,
            visible=True,
        )
        presence_container = ft.Container(
            content=presence_content,
            expand=True,
            visible=False,
        )

        # ---- Tab buttons ---------------------------------------------
        tab_dashboard = ft.TextButton(
            text=t("dashboard"),
            style=ft.ButtonStyle(color=self._theme.primary),
            on_click=lambda _: self._switch_tab(
                dashboard_container, presence_container,
                tab_dashboard, tab_presence,
            ),
        )
        tab_presence = ft.TextButton(
            text=t("presence"),
            style=ft.ButtonStyle(color=self._theme.on_background),
            on_click=lambda _: self._switch_tab(
                presence_container, dashboard_container,
                tab_presence, tab_dashboard,
            ),
        )

        tab_bar = ft.Row(
            controls=[tab_dashboard, tab_presence],
            spacing=4,
        )

        # ---- SharePanel (collapsible) --------------------------------
        share_panel = SharePanel(url=self._mobile_url, theme=self._theme)

        share_container = ft.Container(
            content=share_panel.build(page=self.page),
            visible=False,
        )

        def toggle_share(_: ft.ControlEvent) -> None:
            share_container.visible = not share_container.visible
            self.page.update()

        share_button = ft.IconButton(
            icon=ft.Icons.SHARE,
            tooltip=t("share"),
            on_click=toggle_share,
            icon_color=self._theme.secondary,
        )

        # ---- Language switcher --------------------------------------
        def on_lang_change(lang: str) -> None:
            set_language(lang)
            self._config["language"] = lang
            save_config(self._config)
            # Rebuild the workspace to apply new language strings
            self.page.run_task(
                self._build_exam_workspace, self._current_exam_id
            )

        lang_switcher = LanguageSwitcher(
            on_change=on_lang_change,
            theme=self._theme,
        )

        # ---- Back to home button ------------------------------------
        def go_home(_: ft.ControlEvent) -> None:
            self._show_home()

        back_button = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip=t("open_exam"),
            on_click=go_home,
            icon_color=self._theme.on_background,
        )

        # ---- Top bar ------------------------------------------------
        top_bar = ft.Container(
            bgcolor=self._theme.surface,
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            content=ft.Row(
                controls=[
                    back_button,
                    ft.Text(
                        exam_name,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=self._theme.on_background,
                        expand=True,
                    ),
                    tab_bar,
                    ft.Container(expand=True),
                    share_button,
                    lang_switcher.build(page=self.page),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        # ---- Status bar (ReadOnlyBanner or EndExamButton) -----------
        ended_at = exam.get("ended_at")
        if read_only:
            # Requirement 8.5 — show ReadOnlyBanner, hide EndExamButton
            from datetime import datetime

            ended_at_dt: Optional[datetime] = None
            if ended_at:
                try:
                    ended_at_dt = datetime.fromisoformat(
                        ended_at.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    ended_at_dt = None

            status_bar: ft.Control = ReadOnlyBanner(
                ended_at=ended_at_dt,
                theme=self._theme,
            ).build()
        else:
            # Requirement 8.1–8.4 — show EndExamButton
            assert self._api is not None
            status_bar = EndExamButton(
                exam_id=exam.get("id", self._current_exam_id or 0),
                api=self._api,
                theme=self._theme,
                on_exam_ended=self._on_exam_ended,
            ).build(page=self.page)

        status_bar_container = ft.Container(
            content=status_bar,
            padding=ft.padding.symmetric(horizontal=16, vertical=4),
        )

        # ---- Full layout --------------------------------------------
        return ft.Column(
            controls=[
                top_bar,
                status_bar_container,
                share_container,
                ft.Divider(height=1, color=self._theme.surface),
                ft.Container(
                    expand=True,
                    content=ft.Stack(
                        controls=[dashboard_container, presence_container],
                        expand=True,
                    ),
                ),
            ],
            spacing=0,
            expand=True,
        )

    def _switch_tab(
        self,
        show: ft.Container,
        hide: ft.Container,
        active_btn: ft.TextButton,
        inactive_btn: ft.TextButton,
    ) -> None:
        """Toggle visibility between two tab containers and update button styles."""
        show.visible = True
        hide.visible = False
        active_btn.style = ft.ButtonStyle(color=self._theme.primary)
        inactive_btn.style = ft.ButtonStyle(color=self._theme.on_background)
        self.page.update()

    # ------------------------------------------------------------------
    # End exam callback
    # ------------------------------------------------------------------

    def _on_exam_ended(self) -> None:
        """Called by EndExamButton after a successful finish_exam call.

        Transitions the entire workspace to read-only mode (Requirement 8.2).
        """
        if self._current_exam_id is not None:
            self.page.run_task(
                self._build_exam_workspace, self._current_exam_id
            )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _on_disconnect(self, e: ft.ControlEvent) -> None:
        """Stop background processes when the window closes.

        Requirements: 1.4, 2.4
        """
        if self._launcher is not None:
            self._launcher.stop()
        if self._mobile_server is not None:
            self._mobile_server.stop()


# ---------------------------------------------------------------------------
# Flet entry point
# ---------------------------------------------------------------------------

async def main(page: ft.Page) -> None:
    """Flet async main function — creates the App and runs the startup flow."""
    app = App(page)
    await app.run()


if __name__ == "__main__":
    ft.app(target=main)
