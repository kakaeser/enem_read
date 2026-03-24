from dataclasses import dataclass


@dataclass
class ThemeConfig:
    name: str
    primary: str        # hex color
    secondary: str
    background: str
    surface: str
    on_primary: str
    on_background: str


THEMES: dict[str, ThemeConfig] = {
    "dark_blue": ThemeConfig(
        name="dark_blue",
        primary="#1565C0",
        secondary="#42A5F5",
        background="#0D1117",
        surface="#161B22",
        on_primary="#FFFFFF",
        on_background="#E6EDF3",
    ),
    "dark_green": ThemeConfig(
        name="dark_green",
        primary="#2E7D32",
        secondary="#66BB6A",
        background="#0D1117",
        surface="#161B22",
        on_primary="#FFFFFF",
        on_background="#E6EDF3",
    ),
    "light": ThemeConfig(
        name="light",
        primary="#1976D2",
        secondary="#42A5F5",
        background="#F5F5F5",
        surface="#FFFFFF",
        on_primary="#FFFFFF",
        on_background="#212121",
    ),
    "light_purple": ThemeConfig(
        name="light_purple",
        primary="#7C3AED",
        secondary="#A78BFA",
        background="#F5F3FF",
        surface="#EDE9FE",
        on_primary="#FFFFFF",
        on_background="#3B1F6E",
    ),
    "high_contrast": ThemeConfig(
        name="high_contrast",
        primary="#FFFF00",
        secondary="#00FFFF",
        background="#000000",
        surface="#1A1A1A",
        on_primary="#000000",
        on_background="#FFFFFF",
    ),
}
