from __future__ import annotations

from typing import Callable, Optional

import flet as ft


class LanguageSelectView:
    """First-launch language selection screen.

    Displays two large buttons for the user to pick their preferred language.
    Calls ``on_language_selected(lang)`` with the chosen language code.
    Does NOT call ``set_language()`` or ``save_config()`` directly — the
    caller (``main.py``) is responsible for persistence.

    Requirements: 11.1, 11.2
    """

    def __init__(
        self,
        on_language_selected: Callable[[str], None],
    ) -> None:
        self.on_language_selected = on_language_selected

    def build(self, page: Optional[ft.Page] = None) -> ft.Control:
        def select_pt(e: ft.ControlEvent) -> None:
            self.on_language_selected("pt_BR")

        def select_en(e: ft.ControlEvent) -> None:
            self.on_language_selected("en")

        return ft.Container(
            expand=True,
            alignment=ft.alignment.center,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=32,
                controls=[
                    ft.Text(
                        "Enem da Read",
                        size=36,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(
                        "Selecione o idioma / Select language",
                        size=18,
                        opacity=0.7,
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=24,
                        controls=[
                            ft.ElevatedButton(
                                text="🇧🇷 Português (BR)",
                                on_click=select_pt,
                                width=220,
                                height=64,
                                style=ft.ButtonStyle(
                                    text_style=ft.TextStyle(size=18),
                                ),
                            ),
                            ft.ElevatedButton(
                                text="🇺🇸 English",
                                on_click=select_en,
                                width=220,
                                height=64,
                                style=ft.ButtonStyle(
                                    text_style=ft.TextStyle(size=18),
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )
