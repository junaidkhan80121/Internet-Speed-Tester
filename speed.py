"""
VELOCITY — Internet Speed Tester
A premium, clean PyQt5 speed testing application inspired by modern dashboard design.
Features: Animated gauge, Ping/Download/Upload cards, test history, server info, progress bar.
"""

import sys
import os
import math
import json
import datetime
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, pyqtProperty, QRectF, QPointF, QSize
)
from PyQt5.QtGui import (
    QFont, QFontDatabase, QColor, QPainter, QPen, QBrush,
    QLinearGradient, QRadialGradient, QConicalGradient,
    QPainterPath, QIcon, QPalette, QPixmap
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGridLayout, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy, QMessageBox, QFileDialog, QScrollArea, QProgressBar,
    QSpacerItem, QStackedWidget, QToolButton
)

import speedtest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "images")
HISTORY_FILE = os.path.join(BASE_DIR, "speed_history.json")


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  COLOUR PALETTE                                                        ║
# ╚═════════════════════════════════════════════════════════════════════════╝
C = {
    "bg":            "#f5f6fa",
    "white":         "#ffffff",
    "card_bg":       "#ffffff",
    "border":        "#e8ecf1",
    "border_light":  "#f0f2f5",
    "primary":       "#2563eb",
    "primary_hover": "#1d4ed8",
    "primary_light": "#dbeafe",
    "accent_green":  "#10b981",
    "accent_orange": "#f59e0b",
    "accent_red":    "#ef4444",
    "accent_purple": "#8b5cf6",
    "text_dark":     "#0f172a",
    "text":          "#334155",
    "text_secondary":"#64748b",
    "text_muted":    "#94a3b8",
    "gauge_track":   "#e2e8f0",
    "gauge_active":  "#2563eb",
    "shadow":        "rgba(15, 23, 42, 0.06)",
    "divider":       "#f1f5f9",
    "dark_section":  "#0f172a",
    "ping_border":   "#ef4444",
    "dl_border":     "#2563eb",
    "ul_border":     "#f59e0b",
}


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  ANIMATED CIRCULAR GAUGE                                              ║
# ╚═════════════════════════════════════════════════════════════════════════╝
class SpeedGauge(QWidget):
    """Large circular speed gauge, clean design with thick blue arc."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._max_value = 1000.0
        self._phase = "DOWNLOAD"
        self._stable = False
        self.setMinimumSize(300, 300)
        self.setMaximumSize(360, 360)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def get_value(self):
        return self._value

    def set_value(self, v):
        self._value = v
        self.update()

    value = pyqtProperty(float, get_value, set_value)

    def set_max(self, m):
        self._max_value = max(m, 1)
        self.update()

    def set_phase(self, phase):
        self._phase = phase
        self.update()

    def set_stable(self, s):
        self._stable = s
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h)
        cx, cy = w / 2, h / 2
        radius = side * 0.42
        thickness = 14

        # === Background circle (track) ===
        pen_track = QPen(QColor(C["gauge_track"]), thickness, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_track)
        arc_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.drawArc(arc_rect, 0, 360 * 16)

        # === Value arc ===
        ratio = min(self._value / self._max_value, 1.0) if self._max_value else 0
        span_angle = 360 * ratio
        pen_val = QPen(QColor(C["gauge_active"]), thickness, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen_val)
        # Draw from top (90°), going clockwise (negative span)
        painter.drawArc(arc_rect, 90 * 16, int(-span_angle * 16))

        # === Phase label + stable badge ===
        badge_y = cy - 30
        painter.setPen(QColor(C["text_secondary"]))
        phase_font = QFont("Segoe UI", 9, QFont.DemiBold)
        phase_font.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        painter.setFont(phase_font)

        phase_text = self._phase.upper()
        fm = painter.fontMetrics()
        pw = fm.horizontalAdvance(phase_text)

        total_w = pw
        if self._stable:
            total_w += 90  # space for badge

        start_x = cx - total_w / 2

        painter.drawText(QPointF(start_x, badge_y), phase_text)

        if self._stable:
            badge_x = start_x + pw + 8
            badge_rect = QRectF(badge_x, badge_y - 14, 82, 18)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#dbeafe"))
            painter.drawRoundedRect(badge_rect, 9, 9)
            painter.setPen(QColor(C["primary"]))
            painter.setFont(QFont("Segoe UI", 7, QFont.Bold))
            painter.drawText(badge_rect, Qt.AlignCenter, "✓ Stable Connection")

        # === Center value ===
        painter.setPen(QColor(C["text_dark"]))
        val_font = QFont("Segoe UI", int(side * 0.14), QFont.Bold)
        painter.setFont(val_font)
        val_text = f"{self._value:.0f}" if self._value >= 10 else f"{self._value:.1f}"
        painter.drawText(QRectF(cx - radius, cy - 20, radius * 2, radius * 0.55),
                         Qt.AlignCenter, val_text)

        # === "Mbps" unit ===
        painter.setPen(QColor(C["primary"]))
        unit_font = QFont("Segoe UI", 13, QFont.DemiBold)
        painter.setFont(unit_font)
        painter.drawText(QRectF(cx - radius, cy + radius * 0.28, radius * 2, 30),
                         Qt.AlignCenter, "Mbps")

        painter.end()


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  METRIC CARD (Ping / Download / Upload)                               ║
# ╚═════════════════════════════════════════════════════════════════════════╝
class MetricCard(QFrame):
    """A card with a coloured left border showing a metric result."""

    def __init__(self, title, icon_char, border_color, parent=None):
        super().__init__(parent)
        self.border_color = border_color
        self.setFixedHeight(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(f"""
            MetricCard {{
                background: {C['white']};
                border: 1px solid {C['border']};
                border-left: 4px solid {border_color};
                border-radius: 10px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 18))
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 14, 10)
        layout.setSpacing(0)

        # Left content
        left = QVBoxLayout()
        left.setSpacing(2)

        header = QLabel(title.upper())
        header.setFont(QFont("Segoe UI", 8, QFont.DemiBold))
        header.setStyleSheet(f"color: {C['text_muted']}; border: none; letter-spacing: 1px;")
        left.addWidget(header)

        val_row = QHBoxLayout()
        val_row.setSpacing(4)
        self.value_label = QLabel("—")
        self.value_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {C['text_dark']}; border: none;")
        val_row.addWidget(self.value_label)

        self.unit_label = QLabel("")
        self.unit_label.setFont(QFont("Segoe UI", 11))
        self.unit_label.setStyleSheet(f"color: {C['text_muted']}; border: none;")
        self.unit_label.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        val_row.addWidget(self.unit_label)
        val_row.addStretch()

        left.addLayout(val_row)
        layout.addLayout(left, 1)

        # Right icon
        icon_lbl = QLabel(icon_char)
        icon_lbl.setFont(QFont("Segoe UI", 16))
        icon_lbl.setStyleSheet(f"color: {border_color}; border: none;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_lbl)

    def set_value(self, value, unit):
        self.value_label.setText(value)
        self.unit_label.setText(unit)

    def reset(self):
        self.value_label.setText("—")
        self.unit_label.setText("")


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  INFO BOX (Server / Provider)                                         ║
# ╚═════════════════════════════════════════════════════════════════════════╝
class InfoBox(QFrame):
    """Small box showing server or provider information."""

    def __init__(self, icon_char, title, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            InfoBox {{
                background: {C['white']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
        """)
        self.setFixedHeight(70)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(2)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)
        icon_lbl = QLabel(icon_char)
        icon_lbl.setFont(QFont("Segoe UI", 10))
        icon_lbl.setStyleSheet(f"color: {C['text_muted']}; border: none;")
        header_row.addWidget(icon_lbl)
        title_lbl = QLabel(title.upper())
        title_lbl.setFont(QFont("Segoe UI", 7, QFont.DemiBold))
        title_lbl.setStyleSheet(f"color: {C['text_muted']}; border: none; letter-spacing: 1.5px;")
        header_row.addWidget(title_lbl)
        header_row.addStretch()
        layout.addLayout(header_row)

        self.main_label = QLabel("—")
        self.main_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.main_label.setStyleSheet(f"color: {C['text_dark']}; border: none;")
        layout.addWidget(self.main_label)

        self.sub_label = QLabel("")
        self.sub_label.setFont(QFont("Segoe UI", 8))
        self.sub_label.setStyleSheet(f"color: {C['text_muted']}; border: none;")
        layout.addWidget(self.sub_label)

    def set_info(self, main, sub=""):
        self.main_label.setText(main)
        self.sub_label.setText(sub)


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  HISTORY ROW                                                           ║
# ╚═════════════════════════════════════════════════════════════════════════╝
class HistoryRow(QFrame):
    """Single row showing a past speed test result."""

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            HistoryRow {{
                background: {C['white']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
            HistoryRow:hover {{
                border-color: {C['primary']};
                background: {C['primary_light']};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(24)

        # Date
        date_box = QVBoxLayout()
        date_box.setSpacing(0)
        date_str = data.get("date", "")
        parts = date_str.split(" ")
        d_label = QLabel(parts[0] if parts else "")
        d_label.setFont(QFont("Segoe UI", 8, QFont.Bold))
        d_label.setStyleSheet(f"color: {C['text_secondary']}; border: none;")
        date_box.addWidget(d_label)
        t_label = QLabel(parts[1] if len(parts) > 1 else "")
        t_label.setFont(QFont("Segoe UI", 8))
        t_label.setStyleSheet(f"color: {C['text_muted']}; border: none;")
        date_box.addWidget(t_label)
        layout.addLayout(date_box)

        # Download
        dl_box = QVBoxLayout()
        dl_box.setSpacing(0)
        dl_header = QLabel("DOWNLOAD")
        dl_header.setFont(QFont("Segoe UI", 7))
        dl_header.setStyleSheet(f"color: {C['text_muted']}; border: none; letter-spacing: 0.5px;")
        dl_box.addWidget(dl_header)
        dl_val = QLabel(f"{data.get('download', 0):.1f} Mbps")
        dl_val.setFont(QFont("Segoe UI", 11, QFont.Bold))
        dl_val.setStyleSheet(f"color: {C['text_dark']}; border: none;")
        dl_box.addWidget(dl_val)
        layout.addLayout(dl_box)

        # Upload
        ul_box = QVBoxLayout()
        ul_box.setSpacing(0)
        ul_header = QLabel("UPLOAD")
        ul_header.setFont(QFont("Segoe UI", 7))
        ul_header.setStyleSheet(f"color: {C['text_muted']}; border: none; letter-spacing: 0.5px;")
        ul_box.addWidget(ul_header)
        ul_val = QLabel(f"{data.get('upload', 0):.1f} Mbps")
        ul_val.setFont(QFont("Segoe UI", 11, QFont.Bold))
        ul_val.setStyleSheet(f"color: {C['text_dark']}; border: none;")
        ul_box.addWidget(ul_val)
        layout.addLayout(ul_box)

        # Ping
        ping_box = QVBoxLayout()
        ping_box.setSpacing(0)
        ping_header = QLabel("PING")
        ping_header.setFont(QFont("Segoe UI", 7))
        ping_header.setStyleSheet(f"color: {C['text_muted']}; border: none; letter-spacing: 0.5px;")
        ping_box.addWidget(ping_header)
        ping_val = QLabel(f"{data.get('ping', 0):.0f} ms")
        ping_val.setFont(QFont("Segoe UI", 11, QFont.Bold))
        ping_val.setStyleSheet(f"color: {C['text_dark']}; border: none;")
        ping_box.addWidget(ping_val)
        layout.addLayout(ping_box)

        layout.addStretch()

        # Eye icon
        eye = QLabel("👁")
        eye.setFont(QFont("Segoe UI", 12))
        eye.setStyleSheet(f"color: {C['text_muted']}; border: none;")
        layout.addWidget(eye)


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  GLOBAL NETWORK SECTION                                               ║
# ╚═════════════════════════════════════════════════════════════════════════╝
class GlobalNetworkSection(QFrame):
    """Dark section showing network info with a world map graphic."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(200)
        self.setStyleSheet(f"""
            GlobalNetworkSection {{
                background: {C['dark_section']};
                border-radius: 14px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 30, 0)
        layout.setSpacing(20)

        # Left: World map visualization (custom painted)
        self.map_widget = WorldMapWidget()
        self.map_widget.setFixedWidth(380)
        layout.addWidget(self.map_widget)

        # Right: Info text
        right = QVBoxLayout()
        right.setSpacing(8)
        right.addStretch()

        title = QLabel("Global Network")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #ffffff; border: none;")
        right.addWidget(title)

        desc = QLabel(
            "VELOCITY leverages a premium tier-1 global\n"
            "network infrastructure to ensure your speed\n"
            "tests are accurate to within 0.1ms of precision."
        )
        desc.setFont(QFont("Segoe UI", 9))
        desc.setStyleSheet("color: #94a3b8; border: none; line-height: 1.6;")
        right.addWidget(desc)

        right.addSpacing(6)

        bullets = [
            ("●", "4,500+ Global Servers"),
            ("●", "Real-time Geo-IP Mapping"),
            ("●", "Jitter & Loss Analytics"),
        ]
        for dot, text in bullets:
            row = QHBoxLayout()
            row.setSpacing(8)
            dot_lbl = QLabel(dot)
            dot_lbl.setFont(QFont("Segoe UI", 7))
            dot_lbl.setStyleSheet(f"color: {C['primary']}; border: none;")
            dot_lbl.setFixedWidth(12)
            row.addWidget(dot_lbl)
            txt_lbl = QLabel(text)
            txt_lbl.setFont(QFont("Segoe UI", 9))
            txt_lbl.setStyleSheet("color: #cbd5e1; border: none;")
            row.addWidget(txt_lbl)
            row.addStretch()
            right.addLayout(row)

        right.addStretch()
        layout.addLayout(right, 1)


class WorldMapWidget(QWidget):
    """Custom-painted abstract world map dots for the dark section."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Draw scattered dots to represent a world map
        import random
        random.seed(42)  # deterministic

        # Continent-ish clusters
        clusters = [
            (0.20, 0.35, 0.12, 0.15, 40),   # North America
            (0.22, 0.60, 0.08, 0.10, 20),   # South America
            (0.48, 0.30, 0.10, 0.12, 45),   # Europe
            (0.47, 0.50, 0.12, 0.15, 35),   # Africa
            (0.65, 0.35, 0.15, 0.15, 50),   # Asia
            (0.78, 0.60, 0.08, 0.10, 25),   # Oceania
        ]

        for cx_f, cy_f, rw, rh, count in clusters:
            for _ in range(count):
                dx = random.gauss(0, rw) * w
                dy = random.gauss(0, rh) * h
                x = cx_f * w + dx
                y = cy_f * h + dy
                if 0 <= x < w and 0 <= y < h:
                    brightness = random.randint(40, 120)
                    size = random.uniform(1.0, 2.5)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(brightness, brightness + 20, brightness + 40, 160))
                    painter.drawEllipse(QPointF(x, y), size, size)

        # Highlight dots (servers)
        highlights = [
            (0.18, 0.33), (0.25, 0.40), (0.50, 0.28),
            (0.52, 0.35), (0.68, 0.30), (0.72, 0.38),
            (0.80, 0.58),
        ]
        for fx, fy in highlights:
            px, py = fx * w, fy * h
            # Glow
            glow = QRadialGradient(px, py, 12)
            glow.setColorAt(0, QColor(37, 99, 235, 120))
            glow.setColorAt(1, QColor(37, 99, 235, 0))
            painter.setBrush(glow)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(px, py), 12, 12)
            # Core dot
            painter.setBrush(QColor(C["primary"]))
            painter.drawEllipse(QPointF(px, py), 3, 3)

        painter.end()


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  NAVIGATION BAR                                                        ║
# ╚═════════════════════════════════════════════════════════════════════════╝
class NavBar(QFrame):
    """Top navigation bar with VELOCITY logo and tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setStyleSheet(f"""
            NavBar {{
                background: {C['white']};
                border-bottom: 1px solid {C['border']};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(0)

        # Logo
        logo = QLabel("VELOCITY")
        logo.setFont(QFont("Segoe UI", 14, QFont.Bold))
        logo.setStyleSheet(f"color: {C['primary']}; border: none;")
        layout.addWidget(logo)

        layout.addSpacing(40)

        # Nav tabs
        tabs = ["Dashboard", "History", "Servers", "Settings"]
        self.tab_buttons = []
        for i, name in enumerate(tabs):
            btn = QPushButton(name)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(52)
            active = (i == 0)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {C['primary'] if active else C['text_secondary']};
                    border: none;
                    border-bottom: {'2px solid ' + C['primary'] if active else '2px solid transparent'};
                    padding: 0 12px;
                    font-weight: {'bold' if active else 'normal'};
                }}
                QPushButton:hover {{
                    color: {C['primary']};
                }}
            """)
            layout.addWidget(btn)
            self.tab_buttons.append(btn)

        layout.addStretch()

        # Right icons
        bell = QPushButton("🔔")
        bell.setFont(QFont("Segoe UI", 13))
        bell.setStyleSheet("border: none; background: transparent;")
        bell.setFixedSize(36, 36)
        bell.setCursor(Qt.PointingHandCursor)
        layout.addWidget(bell)

        avatar = QLabel("👤")
        avatar.setFont(QFont("Segoe UI", 13))
        avatar.setStyleSheet(f"""
            border: 2px solid {C['border']};
            border-radius: 16px;
            padding: 2px;
        """)
        avatar.setFixedSize(34, 34)
        avatar.setAlignment(Qt.AlignCenter)
        layout.addWidget(avatar)


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  FOOTER                                                               ║
# ╚═════════════════════════════════════════════════════════════════════════╝
class Footer(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            Footer {{
                background: {C['white']};
                border-top: 1px solid {C['border']};
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)

        left = QLabel(f"© {datetime.datetime.now().year} VELOCITY Precision Telemetry")
        left.setFont(QFont("Segoe UI", 8))
        left.setStyleSheet(f"color: {C['text_muted']}; border: none;")
        layout.addWidget(left)

        layout.addStretch()

        for text in ["Support", "Legal", "Privacy Policy"]:
            lnk = QLabel(text)
            lnk.setFont(QFont("Segoe UI", 8))
            is_last = text == "Privacy Policy"
            lnk.setStyleSheet(
                f"color: {C['primary'] if is_last else C['text_muted']}; border: none; "
                f"{'text-decoration: underline;' if is_last else ''}"
            )
            layout.addWidget(lnk)
            if not is_last:
                layout.addSpacing(16)


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  WORKER THREAD                                                         ║
# ╚═════════════════════════════════════════════════════════════════════════╝
class SpeedTestWorker(QThread):
    phase_changed = pyqtSignal(str)
    ping_result = pyqtSignal(float)
    download_result = pyqtSignal(float)
    upload_result = pyqtSignal(float)
    server_info = pyqtSignal(dict)
    progress_update = pyqtSignal(int)
    error = pyqtSignal(str)
    finished_all = pyqtSignal()

    def run(self):
        try:
            self.phase_changed.emit("connecting")
            self.progress_update.emit(5)
            st = speedtest.Speedtest()

            self.phase_changed.emit("ping")
            self.progress_update.emit(15)
            best = st.get_best_server()
            self.ping_result.emit(best["latency"])
            self.server_info.emit({
                "host": best.get("host", ""),
                "name": best.get("name", ""),
                "country": best.get("country", ""),
                "sponsor": best.get("sponsor", ""),
                "latency": best.get("latency", 0),
            })
            self.progress_update.emit(25)

            self.phase_changed.emit("download")
            dl = st.download() / 1e6
            self.download_result.emit(dl)
            self.progress_update.emit(60)

            self.phase_changed.emit("upload")
            ul = st.upload() / 1e6
            self.upload_result.emit(ul)
            self.progress_update.emit(95)

            self.phase_changed.emit("done")
            self.progress_update.emit(100)
            self.finished_all.emit()

        except Exception as e:
            self.error.emit(str(e))


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  MAIN WINDOW                                                           ║
# ╚═════════════════════════════════════════════════════════════════════════╝
class VelocityWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VELOCITY — Internet Speed Tester")
        self.setMinimumSize(920, 740)
        self.resize(960, 820)
        self.setStyleSheet(f"QMainWindow {{ background: {C['bg']}; }} QLabel {{ background: transparent; }}")

        self._ping = 0.0
        self._download = 0.0
        self._upload = 0.0
        self._server = {}
        self._testing = False
        self._history = self._load_history()

        self._build_ui()
        self._populate_history()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── NAV BAR ───────────────────────────────────────────
        self.navbar = NavBar()
        root.addWidget(self.navbar)

        # ── Scroll Area ───────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: {C['bg']}; border: none; }}
            QScrollBar:vertical {{
                background: {C['bg']};
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['border']};
                border-radius: 3px;
                min-height: 40px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        container = QWidget()
        container.setStyleSheet(f"background: {C['bg']};")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(36, 28, 36, 28)
        main_layout.setSpacing(24)

        # ═══════════════════════════════════════════════════════
        #  TOP SECTION: Gauge left, Cards right
        # ═══════════════════════════════════════════════════════
        top_section = QHBoxLayout()
        top_section.setSpacing(28)

        # Left: Gauge
        gauge_wrapper = QVBoxLayout()
        gauge_wrapper.setAlignment(Qt.AlignCenter)
        self.gauge = SpeedGauge()
        gauge_wrapper.addWidget(self.gauge, alignment=Qt.AlignCenter)

        # Progress bar
        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)
        progress_label = QLabel("Test Progress")
        progress_label.setFont(QFont("Segoe UI", 9))
        progress_label.setStyleSheet(f"color: {C['text_secondary']};")
        progress_row.addWidget(progress_label)
        progress_row.addStretch()
        self.progress_pct = QLabel("0%")
        self.progress_pct.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.progress_pct.setStyleSheet(f"color: {C['primary']};")
        progress_row.addWidget(self.progress_pct)
        gauge_wrapper.addLayout(progress_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {C['gauge_track']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {C['primary']};
                border-radius: 3px;
            }}
        """)
        gauge_wrapper.addWidget(self.progress_bar)

        gauge_wrapper.addSpacing(10)

        # Start / Restart button
        self.start_btn = QPushButton("▶   START TEST")
        self.start_btn.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setFixedHeight(50)
        self.start_btn.setMinimumWidth(300)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['primary']};
                color: #ffffff;
                border: none;
                border-radius: 25px;
                padding: 0 32px;
            }}
            QPushButton:hover {{
                background: {C['primary_hover']};
            }}
            QPushButton:pressed {{
                background: #1e40af;
            }}
            QPushButton:disabled {{
                background: {C['gauge_track']};
                color: {C['text_muted']};
            }}
        """)
        shadow_btn = QGraphicsDropShadowEffect(self.start_btn)
        shadow_btn.setBlurRadius(28)
        shadow_btn.setOffset(0, 6)
        shadow_btn.setColor(QColor(37, 99, 235, 70))
        self.start_btn.setGraphicsEffect(shadow_btn)
        self.start_btn.clicked.connect(self._start_test)
        gauge_wrapper.addWidget(self.start_btn, alignment=Qt.AlignCenter)

        top_section.addLayout(gauge_wrapper, 1)

        # Right: Metric cards + server info
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        self.ping_card = MetricCard("Ping", "🏓", C["ping_border"])
        self.dl_card = MetricCard("Peak Download", "⬇", C["dl_border"])
        self.ul_card = MetricCard("Upload", "⬆", C["ul_border"])
        right_col.addWidget(self.ping_card)
        right_col.addWidget(self.dl_card)
        right_col.addWidget(self.ul_card)

        # Server / Provider info
        info_row = QHBoxLayout()
        info_row.setSpacing(10)
        self.server_box = InfoBox("🖥", "Active Server")
        self.provider_box = InfoBox("📡", "Provider")
        info_row.addWidget(self.server_box)
        info_row.addWidget(self.provider_box)
        right_col.addLayout(info_row)

        right_col.addStretch()
        top_section.addLayout(right_col, 1)

        main_layout.addLayout(top_section)

        # ═══════════════════════════════════════════════════════
        #  HISTORY SECTION
        # ═══════════════════════════════════════════════════════
        main_layout.addSpacing(8)
        history_header = QHBoxLayout()
        history_title = QLabel("Recent Tests")
        history_title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        history_title.setStyleSheet(f"color: {C['text_dark']};")
        history_header.addWidget(history_title)
        history_header.addStretch()

        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setFont(QFont("Segoe UI", 9))
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C['text_muted']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                color: {C['accent_red']};
                border-color: {C['accent_red']};
            }}
        """)
        self.clear_btn.clicked.connect(self._clear_history)
        history_header.addWidget(self.clear_btn)

        export_btn = QPushButton("Export ↗")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.setFont(QFont("Segoe UI", 9))
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C['primary']};
                border: 1px solid {C['primary']};
                border-radius: 6px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background: {C['primary_light']};
            }}
        """)
        export_btn.clicked.connect(self._export_results)
        history_header.addWidget(export_btn)

        main_layout.addLayout(history_header)

        self.history_container = QVBoxLayout()
        self.history_container.setSpacing(8)
        main_layout.addLayout(self.history_container)

        self.no_history_label = QLabel("No test results yet. Click START TEST to begin.")
        self.no_history_label.setFont(QFont("Segoe UI", 10))
        self.no_history_label.setStyleSheet(f"color: {C['text_muted']};")
        self.no_history_label.setAlignment(Qt.AlignCenter)
        self.history_container.addWidget(self.no_history_label)

        # ═══════════════════════════════════════════════════════
        #  GLOBAL NETWORK SECTION
        # ═══════════════════════════════════════════════════════
        main_layout.addSpacing(8)
        self.network_section = GlobalNetworkSection()
        main_layout.addWidget(self.network_section)

        main_layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        # ── FOOTER ────────────────────────────────────────────
        self.footer = Footer()
        root.addWidget(self.footer)

    # ── Speed Test Control ────────────────────────────────────────────
    def _start_test(self):
        if self._testing:
            return
        self._testing = True
        self.start_btn.setEnabled(False)
        self.start_btn.setText("⏳   TESTING…")

        self.ping_card.reset()
        self.dl_card.reset()
        self.ul_card.reset()
        self.server_box.set_info("Connecting…", "")
        self.provider_box.set_info("—", "")
        self.gauge.set_value(0)
        self.gauge.set_phase("CONNECTING")
        self.gauge.set_stable(False)
        self.progress_bar.setValue(0)
        self.progress_pct.setText("0%")

        self.worker = SpeedTestWorker()
        self.worker.phase_changed.connect(self._on_phase)
        self.worker.ping_result.connect(self._on_ping)
        self.worker.download_result.connect(self._on_download)
        self.worker.upload_result.connect(self._on_upload)
        self.worker.server_info.connect(self._on_server_info)
        self.worker.progress_update.connect(self._on_progress)
        self.worker.error.connect(self._on_error)
        self.worker.finished_all.connect(self._on_done)
        self.worker.start()

    def _on_phase(self, phase):
        label_map = {
            "connecting": "CONNECTING",
            "ping": "PING",
            "download": "DOWNLOAD",
            "upload": "UPLOAD",
            "done": "COMPLETE",
        }
        self.gauge.set_phase(label_map.get(phase, phase.upper()))

    def _on_progress(self, pct):
        self.progress_bar.setValue(pct)
        self.progress_pct.setText(f"{pct}%")

    def _on_ping(self, ms):
        self._ping = ms
        self.ping_card.set_value(f"{ms:.0f}", "ms")
        self._animate_gauge(ms, 200)

    def _on_download(self, mbps):
        self._download = mbps
        self.dl_card.set_value(f"{mbps:.1f}", "Mbps")
        max_val = max(mbps * 1.2, 100)
        self.gauge.set_max(max_val)
        self._animate_gauge(mbps, max_val)
        self.gauge.set_stable(True)

    def _on_upload(self, mbps):
        self._upload = mbps
        self.ul_card.set_value(f"{mbps:.1f}", "Mbps")
        max_val = max(self._download * 1.2, mbps * 1.2, 100)
        self.gauge.set_max(max_val)
        self._animate_gauge(mbps, max_val)

    def _on_server_info(self, info):
        self._server = info
        name = info.get("name", "Unknown")
        country = info.get("country", "")
        sponsor = info.get("sponsor", "")
        host = info.get("host", "")
        self.server_box.set_info(f"{name}, {country}", "Status: Optimal")
        self.provider_box.set_info(sponsor if sponsor else host, "Connection Active")

    def _on_error(self, msg):
        self._testing = False
        self.start_btn.setEnabled(True)
        self.start_btn.setText("▶   RESTART TEST")
        self.gauge.set_phase("ERROR")
        self.gauge.set_stable(False)
        QMessageBox.warning(self, "Speed Test Error",
                            f"Could not complete the speed test.\n\n{msg}")

    def _on_done(self):
        self._testing = False
        self.start_btn.setEnabled(True)
        self.start_btn.setText("↻   RESTART TEST")
        self.gauge.set_stable(True)
        self._save_result()
        self._populate_history()

    def _animate_gauge(self, target, max_val):
        self.gauge.set_max(max_val)
        anim = QPropertyAnimation(self.gauge, b"value")
        anim.setDuration(900)
        anim.setStartValue(self.gauge.get_value())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
        self._gauge_anim = anim

    # ── History ───────────────────────────────────────────────────────
    def _load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_result(self):
        entry = {
            "date": datetime.datetime.now().strftime("%b %d %H:%M"),
            "ping": round(self._ping, 1),
            "download": round(self._download, 2),
            "upload": round(self._upload, 2),
            "server": self._server.get("sponsor", ""),
        }
        self._history.append(entry)
        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump(self._history, f, indent=2)
        except Exception:
            pass

    def _populate_history(self):
        # Clear existing
        while self.history_container.count():
            item = self.history_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._history:
            self.no_history_label = QLabel("No test results yet. Click START TEST to begin.")
            self.no_history_label.setFont(QFont("Segoe UI", 10))
            self.no_history_label.setStyleSheet(f"color: {C['text_muted']};")
            self.no_history_label.setAlignment(Qt.AlignCenter)
            self.history_container.addWidget(self.no_history_label)
            return

        # Show last 5
        for entry in reversed(self._history[-5:]):
            row = HistoryRow(entry)
            self.history_container.addWidget(row)

    def _clear_history(self):
        self._history = []
        try:
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
        except Exception:
            pass
        self._populate_history()

    # ── Export ────────────────────────────────────────────────────────
    def _export_results(self):
        if not self._history:
            QMessageBox.information(self, "Export", "No results to export. Run a test first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Speed Test Results", "velocity_results.json",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return

        if path.endswith(".json"):
            with open(path, "w") as f:
                json.dump(self._history, f, indent=2)
        else:
            lines = [
                "═══════════════════════════════════════════════════════",
                "           VELOCITY — Speed Test History               ",
                "═══════════════════════════════════════════════════════",
            ]
            for entry in self._history:
                lines.append(
                    f"  {entry['date']}  |  "
                    f"Ping: {entry['ping']}ms  |  "
                    f"DL: {entry['download']} Mbps  |  "
                    f"UL: {entry['upload']} Mbps  |  "
                    f"Server: {entry.get('server', 'N/A')}"
                )
            lines.append("═══════════════════════════════════════════════════════")
            with open(path, "w") as f:
                f.write("\n".join(lines))


# ╔═════════════════════════════════════════════════════════════════════════╗
# ║  ENTRY POINT                                                           ║
# ╚═════════════════════════════════════════════════════════════════════════╝
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Light palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(C["bg"]))
    palette.setColor(QPalette.WindowText, QColor(C["text"]))
    palette.setColor(QPalette.Base, QColor(C["white"]))
    palette.setColor(QPalette.AlternateBase, QColor(C["bg"]))
    palette.setColor(QPalette.Text, QColor(C["text"]))
    palette.setColor(QPalette.Button, QColor(C["white"]))
    palette.setColor(QPalette.ButtonText, QColor(C["text"]))
    palette.setColor(QPalette.Highlight, QColor(C["primary"]))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = VelocityWindow()
    window.show()
    sys.exit(app.exec_())
