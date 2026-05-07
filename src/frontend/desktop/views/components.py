from __future__ import annotations

import base64
import io
from datetime import datetime
from typing import Callable, Optional

import flet as ft
import qrcode

from frontend.desktop.api_client import APIClient, APIError
from frontend.desktop.i18n import LANGUAGES, get_language, t
from frontend.desktop.theme import ThemeConfig


class SharePanel(ft.UserControl):
    """Displays a QR code, a read-only URL field, and a copy-link button.

    Requirements: 3.1, 3.2
    """

    def __init__(self, url: str, theme: ThemeConfig) -> None:
        super().__init__()
        self.url = url
        self.theme = theme

    def build(self) -> ft.Control:
        # Generate QR code and encode as base64
        qr_image = qrcode.make(self.url)
        buffer = io.BytesIO()
        qr_image.save(buffer, format="PNG")
        qr_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        def copy_link(e: ft.ControlEvent) -> None:
            self.page.set_clipboard(self.url)

        return ft.Column(
            controls=[
                ft.Image(src_base64=qr_b64, width=200, height=200),
                ft.TextField(value=self.url, read_only=True, expand=True),
                ft.ElevatedButton(
                    text=t("copy_link"),
                    on_click=copy_link,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )


class EndExamButton(ft.UserControl):
    """Button that triggers a confirmation dialog before finishing an exam.

    Requirements: 8.1, 8.2, 8.3, 8.4
    """

    def __init__(
        self,
        exam_id: int,
        api: APIClient,
        theme: ThemeConfig,
        on_exam_ended: Callable[[], None],
    ) -> None:
        super().__init__()
        self.exam_id = exam_id
        self.api = api
        self.theme = theme
        self.on_exam_ended = on_exam_ended
        self._button: Optional[ft.ElevatedButton] = None

    def build(self) -> ft.Control:
        self._button = ft.ElevatedButton(
            text=t("end_exam"),
            on_click=self._show_confirm_dialog,
        )
        return self._button

    def _show_confirm_dialog(self, e: ft.ControlEvent) -> None:
        dialog = ft.AlertDialog(
            title=ft.Text(t("end_exam_confirm")),
            content=ft.Text(t("end_exam_warning")),
            actions=[
                ft.TextButton(
                    text=t("cancel"),
                    on_click=lambda _: self._close_dialog(dialog),
                ),
                ft.TextButton(
                    text=t("end_exam"),
                    on_click=lambda _: self.page.run_task(
                        self._confirm_end_exam, dialog
                    ),
                ),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _close_dialog(self, dialog: ft.AlertDialog) -> None:
        dialog.open = False
        self.page.update()

    async def _confirm_end_exam(self, dialog: ft.AlertDialog) -> None:
        self._close_dialog(dialog)

        # Disable button while the request is in flight
        if self._button is not None:
            self._button.disabled = True
            self.update()

        try:
            await self.api.finish_exam(self.exam_id)
            self.on_exam_ended()
        except APIError as err:
            if err.status_code == 409:
                # Already completed — treat as success
                self.on_exam_ended()
            else:
                # Show error and re-enable the button
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(err.message), open=True
                )
                if self._button is not None:
                    self._button.disabled = False
                self.page.update()


class ReadOnlyBanner(ft.UserControl):
    """Amber banner shown when an exam is in read-only (completed) mode.

    Requirements: 8.5
    """

    def __init__(
        self, ended_at: Optional[datetime], theme: ThemeConfig
    ) -> None:
        super().__init__()
        self.ended_at = ended_at
        self.theme = theme

    def build(self) -> ft.Control:
        row_controls: list[ft.Control] = [
            ft.Icon(ft.icons.LOCK, color="#F57F17"),
            ft.Text(t("view_only")),
        ]

        if self.ended_at is not None:
            ended_label = (
                f'{t("exam_ended_at")}: '
                f'{self.ended_at.strftime("%d/%m/%Y %H:%M")}'
            )
            row_controls.append(ft.Text(ended_label))

        return ft.Container(
            bgcolor="#FFF8E1",
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            content=ft.Row(controls=row_controls),
        )


class LanguageSwitcher(ft.UserControl):
    """Dropdown for switching the application language.

    Calls on_change(lang_code) when the user selects a new language.
    """

    def __init__(
        self, on_change: Callable[[str], None], theme: ThemeConfig
    ) -> None:
        super().__init__()
        self.on_change = on_change
        self.theme = theme

    def build(self) -> ft.Control:
        def handle_change(e: ft.ControlEvent) -> None:
            self.on_change(e.control.value)

        return ft.Dropdown(
            value=get_language(),
            options=[
                ft.dropdown.Option(key="pt_BR", text="🇧🇷 Português"),
                ft.dropdown.Option(key="en", text="🇺🇸 English"),
            ],
            on_change=handle_change,
        )
