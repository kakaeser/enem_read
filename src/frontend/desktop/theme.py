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
        primary="#2563EB",       
        secondary="#60A5FA",
        background="#F8FAFC",    
        surface="#FFFFFF",       
        on_primary="#FFFFFF",   
        on_background="#1E293B", 
    ),
    "light_purple": ThemeConfig(
        name="light_purple",
        primary="#6D28D9",      
        secondary="#8B5CF6",
        background="#F8FAFC",    
        surface="#FFFFFF",       
        on_primary="#FFFFFF",
        on_background="#1E293B",
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
