"""Colours + Qt stylesheet (matches the CrowPanel: black, outline, Spotify green)."""

GREEN = "#1DB954"
BG = "#0B0C0E"
CARD = "#15171B"
BORDER = "#3A3D44"
TEXT = "#E8E8E8"
MUTED = "#A0A4AB"
WARN = "#E5A50A"
ERROR = "#E5534B"

STYLE = f"""
* {{ font-family: "Segoe UI", "Segoe UI Emoji", sans-serif; color: {TEXT}; }}
QWidget#Root {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 12px; }}
QWidget {{ background: transparent; }}
QLabel#Title {{ font-size: 15px; font-weight: 600; }}
QLabel#Muted, QLabel[muted="true"] {{ color: {MUTED}; }}
QLabel#Status[level="ok"] {{ color: {GREEN}; }}
QLabel#Status[level="warn"] {{ color: {WARN}; }}
QLabel#Status[level="error"] {{ color: {ERROR}; }}

QTabBar::tab {{ background: transparent; color: {MUTED}; padding: 6px 12px;
               border: none; border-bottom: 2px solid transparent; font-size: 13px; }}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {GREEN}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

QFrame#Tile {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#Tile:hover {{ border-color: #6A6E77; }}
QFrame#Tile[on="true"] {{ background: {GREEN}; border-color: {GREEN}; }}
QFrame#Tile[on="true"] QLabel {{ color: #000; }}
QFrame#Tile[avail="false"] {{ border-style: dashed; }}
QFrame#Tile[avail="false"] QLabel {{ color: #5A5E66; }}

QPushButton {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px;
               padding: 6px 10px; }}
QPushButton:hover {{ border-color: #6A6E77; }}
QPushButton:checked, QPushButton#Primary {{ background: {GREEN}; border-color: {GREEN}; color: #000; }}
QPushButton:disabled {{ color: #5A5E66; }}
QToolButton {{ border: none; padding: 4px; border-radius: 6px; }}
QToolButton:hover {{ background: {CARD}; }}

QComboBox, QLineEdit, QSpinBox {{ background: {CARD}; border: 1px solid {BORDER};
               border-radius: 8px; padding: 5px 8px; }}
QComboBox QAbstractItemView {{ background: {CARD}; border: 1px solid {BORDER};
               selection-background-color: {GREEN}; selection-color: #000; }}
QListWidget {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px; }}
QListWidget::item {{ padding: 6px; }}
QListWidget::item:selected {{ background: {GREEN}; color: #000; }}

QSlider::groove:horizontal {{ height: 4px; background: {BORDER}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {GREEN}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: #fff; width: 12px; margin: -5px 0; border-radius: 6px; }}

QScrollArea {{ border: none; }}
QScrollBar:vertical {{ width: 8px; background: transparent; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

QDialog {{ background: {BG}; }}
QMenu {{ background: {CARD}; border: 1px solid {BORDER}; }}
QMenu::item:selected {{ background: {GREEN}; color: #000; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 2px solid #6A6E77; border-radius: 4px;
                        background: {CARD}; }}
QCheckBox::indicator:hover {{ border-color: {GREEN}; }}
QCheckBox::indicator:checked {{ background: {GREEN}; border-color: {GREEN}; }}
"""

DOMAIN_ICON = {
    "light": "💡", "switch": "🔌", "fan": "🌀", "input_boolean": "⏻", "climate": "🌡",
    "scene": "🎬", "script": "▶", "automation": "⚙", "sensor": "📈", "binary_sensor": "◉",
    "lock": "🔒", "cover": "🪟", "media_player": "🎵", "button": "⏺", "input_button": "⏺",
    "vacuum": "🧹", "camera": "📷", "humidifier": "💧", "water_heater": "🔥",
}
