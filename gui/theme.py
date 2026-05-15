from dataclasses import dataclass


@dataclass
class Palette:
    bg: str           # 60% — primary background
    surface: str      # 30% — cards, panels
    surface2: str     # stats rows, table footers (slightly darker)
    accent: str       # purple — primary CTA, logo
    accent_soft: str  # translucent purple bg (icon boxes)
    accent_line: str  # translucent purple border
    highlight: str    # blue — URLs, running status, focus rings
    text: str
    text_dim: str     # slightly dimmer body text
    text_muted: str   # captions, placeholders
    danger: str
    success: str
    warning: str
    border: str


DARK = Palette(
    bg="#0F1117",
    surface="#1C1E26",
    surface2="#13151C",
    accent="#7C3AED",
    accent_soft="#7C3AED1A",
    accent_line="#7C3AED40",
    highlight="#3B82F6",
    text="#E8E9ED",
    text_dim="#B0B3BC",
    text_muted="#6B6E7A",
    danger="#EF4444",
    success="#10B981",
    warning="#F59E0B",
    border="#2A2D38",
)

LIGHT = Palette(
    bg="#F7F8FA",
    surface="#EAECF0",
    surface2="#DFE1E7",
    accent="#7C3AED",
    accent_soft="#7C3AED12",
    accent_line="#7C3AED30",
    highlight="#2563EB",
    text="#111318",
    text_dim="#3D4049",
    text_muted="#757880",
    danger="#DC2626",
    success="#059669",
    warning="#D97706",
    border="#D4D6DC",
)


def stylesheet(p: Palette) -> str:
    return f"""
/* ── Base ── */
* {{
    font-family: "Segoe UI", system-ui, sans-serif;
    font-size: 13px;
    color: {p.text};
    outline: none;
}}
QMainWindow, QDialog, QWidget {{
    background-color: {p.bg};
}}

/* ── Labels ── */
QLabel {{
    background-color: transparent;
}}
QLabel#h1 {{ font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }}
QLabel#h2 {{ font-size: 13px; font-weight: 600; }}
QLabel#h3 {{ font-size: 12px; font-weight: 600; color: {p.text_dim}; }}
QLabel#sub {{
    font-size: 11.5px;
    color: {p.text_muted};
}}
QLabel#caption {{
    font-size: 11px;
    color: {p.text_muted};
}}
QLabel#mono {{
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12.5px;
    color: {p.highlight};
}}
QLabel#url {{
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 13px;
    color: {p.highlight};
    background-color: {p.surface2};
    border: 1px solid {p.border};
    border-radius: 6px;
    padding: 8px 12px;
}}

/* ── Badges ── */
QLabel#badge_clean {{
    background-color: {p.success}22;
    color: {p.success};
    border-radius: 4px;
    padding: 2px 10px;
    font-weight: 600;
    font-size: 11.5px;
}}
QLabel#badge_threat {{
    background-color: {p.danger}22;
    color: {p.danger};
    border-radius: 4px;
    padding: 2px 10px;
    font-weight: 600;
    font-size: 11.5px;
}}
QLabel#badge_warn {{
    background-color: {p.warning}22;
    color: {p.warning};
    border-radius: 4px;
    padding: 2px 10px;
    font-weight: 600;
    font-size: 11.5px;
}}
QLabel#badge_muted {{
    background-color: {p.border};
    color: {p.text_dim};
    border-radius: 4px;
    padding: 2px 10px;
    font-weight: 500;
    font-size: 11.5px;
}}
QLabel#badge_running {{
    background-color: {p.success}22;
    color: {p.success};
    border-radius: 4px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: 11.5px;
}}
QLabel#badge_stopped {{
    background-color: {p.border};
    color: {p.text_muted};
    border-radius: 4px;
    padding: 3px 10px;
    font-weight: 500;
    font-size: 11.5px;
}}
QLabel#badge_erase {{
    background-color: {p.warning}18;
    color: {p.warning};
    border: 1px solid {p.warning}40;
    border-radius: 4px;
    padding: 3px 10px;
    font-weight: 500;
    font-size: 11.5px;
}}

/* ── Cards ── */
QFrame#card {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    border-radius: 8px;
}}
QFrame#card_head {{
    background-color: transparent;
    border: none;
    border-bottom: 1px solid {p.border};
}}
QFrame#card_foot {{
    background-color: {p.surface2};
    border: none;
    border-top: 1px solid {p.border};
    border-bottom-left-radius: 8px;
    border-bottom-right-radius: 8px;
}}
QFrame#surface2 {{
    background-color: {p.surface2};
    border: none;
}}
QFrame#icon_box {{
    background-color: {p.accent_soft};
    border: 1px solid {p.accent_line};
    border-radius: 8px;
}}
QFrame#platform_card {{
    background-color: {p.surface2};
    border: 1px solid {p.border};
    border-radius: 7px;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {p.accent};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 12.5px;
    min-height: 30px;
}}
QPushButton:hover   {{ background-color: {_lighten(p.accent, 18)}; }}
QPushButton:pressed {{ background-color: {_darken(p.accent, 15)}; }}
QPushButton:disabled {{
    background-color: {p.border};
    color: {p.text_muted};
}}
QPushButton#secondary {{
    background-color: transparent;
    color: {p.text_dim};
    border: 1px solid {p.border};
}}
QPushButton#secondary:hover {{
    border-color: {p.accent};
    color: {p.accent};
}}
QPushButton#ghost {{
    background-color: transparent;
    color: {p.text_dim};
    border: none;
    padding: 5px 12px;
}}
QPushButton#ghost:hover {{
    background-color: {p.border};
    color: {p.text};
}}
QPushButton#sm {{
    background-color: transparent;
    color: {p.text_dim};
    border: 1px solid {p.border};
    padding: 3px 10px;
    font-size: 11.5px;
    font-weight: 500;
    min-height: 24px;
    border-radius: 5px;
}}
QPushButton#sm:hover {{
    border-color: {p.accent};
    color: {p.accent};
}}
QPushButton#sm_icon {{
    background-color: transparent;
    color: {p.text_dim};
    border: 1px solid {p.border};
    padding: 3px 8px;
    font-size: 11.5px;
    min-height: 24px;
    border-radius: 5px;
}}
QPushButton#sm_icon:hover {{
    border-color: {p.accent};
    color: {p.accent};
}}
QPushButton#danger {{
    background-color: {p.danger};
    color: #ffffff;
}}
QPushButton#danger:hover  {{ background-color: {_lighten(p.danger, 15)}; }}
QPushButton#danger:disabled {{
    background-color: {p.border};
    color: {p.text_muted};
    opacity: 0.6;
}}
QPushButton#icon_btn {{
    background-color: transparent;
    border: none;
    padding: 4px 8px;
    color: {p.text_muted};
    min-height: 24px;
    min-width: 24px;
}}
QPushButton#icon_btn:hover {{ color: {p.text}; background-color: {p.border}; border-radius: 5px; }}

/* Filesystem toggle buttons */
QPushButton#fs_btn {{
    background-color: {p.surface2};
    color: {p.text_dim};
    border: 1px solid {p.border};
    border-radius: 7px;
    font-size: 12.5px;
    font-weight: 500;
    padding: 6px 0;
    min-height: 36px;
}}
QPushButton#fs_btn:hover {{
    border-color: {p.accent};
    color: {p.text};
}}
QPushButton#fs_active {{
    background-color: {p.accent_soft};
    color: {p.text};
    border: 1px solid {p.accent};
    border-radius: 7px;
    font-size: 12.5px;
    font-weight: 600;
    padding: 6px 0;
    min-height: 36px;
}}

/* ── Inputs ── */
QComboBox, QLineEdit, QSpinBox {{
    background-color: {p.surface2};
    border: 1px solid {p.border};
    border-radius: 6px;
    padding: 6px 10px;
    color: {p.text};
    min-height: 32px;
}}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus {{
    border-color: {p.accent};
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background-color: {p.surface};
    border: 1px solid {p.border};
    selection-background-color: {p.accent};
    color: {p.text};
    border-radius: 6px;
}}

/* ── Progress bar ── */
QProgressBar {{
    background-color: {p.surface2};
    border: 1px solid {p.border};
    border-radius: 4px;
    text-align: center;
    height: 6px;
    font-size: 11px;
    color: {p.text_muted};
}}
QProgressBar::chunk {{
    background-color: {p.accent};
    border-radius: 4px;
}}

/* ── Tables ── */
QTableWidget {{
    background-color: {p.surface};
    border: none;
    gridline-color: {p.border};
    alternate-background-color: {p.bg};
}}
QTableWidget::item {{ padding: 5px 8px; border: none; }}
QTableWidget::item:selected {{
    background-color: {p.accent}22;
    color: {p.text};
}}
QHeaderView::section {{
    background-color: {p.surface2};
    border: none;
    border-bottom: 1px solid {p.border};
    padding: 5px 8px;
    font-weight: 600;
    font-size: 11px;
    color: {p.text_muted};
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
QTableCornerButton::section {{ background-color: {p.surface2}; }}

/* ── Checkboxes ── */
QCheckBox {{
    background-color: transparent;
    spacing: 8px;
    font-size: 12.5px;
}}
QCheckBox::indicator {{
    width: 15px; height: 15px;
    border: 1.5px solid {p.border};
    border-radius: 4px;
    background-color: {p.surface2};
}}
QCheckBox::indicator:checked {{
    background-color: {p.accent};
    border-color: {p.accent};
    image: url(none);
}}
QCheckBox::indicator:hover {{ border-color: {p.accent}; }}

/* ── Tabs ── */
QTabWidget::pane {{
    border: 1px solid {p.border};
    border-radius: 0 8px 8px 8px;
    background-color: {p.surface};
    top: -1px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {p.text_muted};
    padding: 9px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 500;
    font-size: 13px;
}}
QTabBar::tab:selected {{
    color: {p.accent};
    border-bottom: 2px solid {p.accent};
}}
QTabBar::tab:hover:!selected {{ color: {p.text}; }}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {p.border};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
}}
QScrollBar::handle:horizontal {{
    background: {p.border};
    border-radius: 3px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Text areas ── */
QTextEdit {{
    background-color: {p.surface2};
    border: 1px solid {p.border};
    border-radius: 6px;
    padding: 8px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 11.5px;
    color: {p.text_dim};
}}

/* ── Status bar ── */
QStatusBar {{
    background-color: {p.surface2};
    border-top: 1px solid {p.border};
    color: {p.text_muted};
    font-size: 11.5px;
    padding: 0;
}}
QStatusBar QLabel {{ background-color: transparent; color: {p.text_muted}; font-size: 11.5px; }}

/* ── Tooltips ── */
QToolTip {{
    background-color: {p.surface};
    color: {p.text};
    border: 1px solid {p.border};
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 12px;
}}

/* ── Banners ── */
QFrame#banner_info {{
    background-color: {p.accent}18;
    border: 1px solid {p.accent}44;
    border-radius: 6px;
}}
QFrame#banner_warn {{
    background-color: {p.warning}18;
    border: 1px solid {p.warning}44;
    border-radius: 8px;
}}

/* ── Separators ── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {{
    color: {p.border};
    background-color: {p.border};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}
"""


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        max(0, min(255, r)),
        max(0, min(255, g)),
        max(0, min(255, b)),
    )


def _lighten(h: str, amt: int) -> str:
    r, g, b = _hex_to_rgb(h)
    return _rgb_to_hex(r + amt, g + amt, b + amt)


def _darken(h: str, amt: int) -> str:
    r, g, b = _hex_to_rgb(h)
    return _rgb_to_hex(r - amt, g - amt, b - amt)
