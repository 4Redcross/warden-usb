from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from backends.base import DriveBackend
from config.settings import Settings
from core.audit import AuditLog
from core.fileserver import FileServer
from core.formatter import Formatter
from core.models import DriveInfo
from core.monitor import DriveMonitor
from core.quarantine import QuarantineManager
from core.scanner import Scanner
from core.virustotal import VirusTotalClient
from core.yara_engine import YaraEngine
from gui import icons
from gui import theme as _theme
from gui.panels.format_panel import FormatPanel
from gui.panels.host_panel import HostPanel
from gui.panels.scan_panel import ScanPanel
from workers.monitor_worker import MonitorWorker


# ── Badge tab bar ────────────────────────────────────────────────────────────

class _BadgeTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._badges: dict[int, int] = {}

    def set_badge(self, index: int, count: int) -> None:
        self._badges[index] = count
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not any(v > 0 for v in self._badges.values()):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for idx, count in self._badges.items():
            if count <= 0:
                continue
            rect = self.tabRect(idx)
            fm = self.fontMetrics()
            label = self.tabText(idx)
            text_w = fm.horizontalAdvance(label)
            # Position badge just right of the tab label centre
            cx = rect.x() + rect.width() // 2 + text_w // 2 + 10
            cy = rect.y() + 10
            r = 8
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#EF4444"))
            p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            p.setPen(QColor("#FFFFFF"))
            f = QFont("Segoe UI", 7)
            f.setBold(True)
            p.setFont(f)
            p.drawText(cx - r, cy - r, r * 2, r * 2, Qt.AlignCenter, str(min(count, 99)))
        p.end()


class _BadgeTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bar = _BadgeTabBar(self)
        self.setTabBar(self._bar)

    def set_badge(self, index: int, count: int) -> None:
        self._bar.set_badge(index, count)


# ── Main window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: Settings,
        scanner: Scanner,
        formatter: Formatter,
        file_server: FileServer,
        drive_monitor: DriveMonitor,
        backend: DriveBackend,
        audit: AuditLog,
        yara_engine: YaraEngine,
        quarantine: QuarantineManager,
        vt_client: VirusTotalClient | None,
    ):
        super().__init__()
        self._settings = settings
        self._scanner = scanner
        self._backend = backend
        self._audit = audit
        self._yara = yara_engine
        self._vt = vt_client

        self._current_drive: DriveInfo | None = None
        self._drives: list[DriveInfo] = []
        self._last_scan_time: str = ""

        self.setWindowTitle("Warden — USB Security")
        self.setMinimumSize(920, 680)
        self.resize(1100, 760)

        self._build_ui(scanner, formatter, file_server, drive_monitor, audit, quarantine, vt_client)
        self._start_monitor(drive_monitor)
        self._refresh_drives()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_drives)
        self._refresh_timer.start(5000)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self, scanner, formatter, file_server, drive_monitor, audit, quarantine, vt_client) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())
        root.addWidget(self._make_banner())

        # ── Tabs ──
        self._scan_panel = ScanPanel(scanner, quarantine, vt_client)
        self._format_panel = FormatPanel(formatter)
        self._host_panel = HostPanel(file_server, audit)

        self._scan_panel.scan_completed.connect(self._on_scan_completed)

        self._tabs = _BadgeTabWidget()
        self._tabs.addTab(self._scan_panel,   icons.icon("scan",   14, "#B0B3BC"), "Scan")
        self._tabs.addTab(self._host_panel,   icons.icon("server", 14, "#B0B3BC"), "Host")
        self._tabs.addTab(self._format_panel, icons.icon("disk",   14, "#B0B3BC"), "Format")

        tab_wrap = QWidget()
        tw_lay = QVBoxLayout(tab_wrap)
        tw_lay.setContentsMargins(14, 10, 14, 10)
        tw_lay.addWidget(self._tabs)
        root.addWidget(tab_wrap, 1)

        self._build_status_bar()

    def _make_header(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(54)
        header.setStyleSheet(
            f"QFrame {{ border-bottom: 1px solid {_theme.DARK.border}; background-color: {_theme.DARK.surface}; }}"
        )
        lay = QHBoxLayout(header)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(10)

        # Logo
        logo_frame = QFrame()
        logo_frame.setFixedSize(34, 34)
        logo_frame.setStyleSheet(
            "QFrame { background-color: #7C3AED; border-radius: 8px; border: none; }"
        )
        logo_lay = QVBoxLayout(logo_frame)
        logo_lay.setContentsMargins(7, 7, 7, 7)
        logo_icon = QLabel()
        logo_icon.setPixmap(icons.pixmap("shield", 20, "#FFFFFF"))
        logo_lay.addWidget(logo_icon)
        lay.addWidget(logo_frame)

        # App name + version
        name_lbl = QLabel("Warden")
        name_lbl.setObjectName("h1")
        lay.addWidget(name_lbl)
        ver_lbl = QLabel("v0.1")
        ver_lbl.setStyleSheet("font-size: 11px; color: #6B6E7A; margin-top: 4px;")
        lay.addWidget(ver_lbl)
        lay.addStretch()
        
        self._drive_dot = QLabel("●")
        self._drive_dot.setStyleSheet("font-size: 8px; color: #6B6E7A;")
        lay.addWidget(self._drive_dot)

        # Drive selector
        self._combo_drive = QComboBox()
        self._combo_drive.setMinimumWidth(260)
        self._combo_drive.setMaximumWidth(360)
        self._combo_drive.setPlaceholderText("No USB connected")
        lay.addWidget(self._combo_drive)

        # Refresh
        btn_refresh = QPushButton()
        btn_refresh.setObjectName("icon_btn")
        btn_refresh.setIcon(icons.icon("refresh", 14, "#6B6E7A"))
        btn_refresh.setToolTip("Refresh drives")
        btn_refresh.setFixedSize(30, 30)
        btn_refresh.clicked.connect(self._refresh_drives)
        lay.addWidget(btn_refresh)

        lay.addSpacing(4)

        # Theme toggle
        self._btn_theme = QPushButton()
        self._btn_theme.setObjectName("icon_btn")
        self._btn_theme.setFixedSize(30, 30)
        self._btn_theme.clicked.connect(self._toggle_theme)
        self._update_theme_btn()
        lay.addWidget(self._btn_theme)

        lay.addSpacing(4)

        # Update Rules
        btn_rules = QPushButton()
        btn_rules.setObjectName("secondary")
        btn_rules.setIcon(icons.icon("download", 13, "#B0B3BC"))
        btn_rules.setText("Update Rules")
        btn_rules.setToolTip("Download latest YARA rules from Neo23x0/signature-base")
        btn_rules.clicked.connect(self._update_rules)
        lay.addWidget(btn_rules)

        self._combo_drive.currentIndexChanged.connect(self._on_drive_selected)
        return header

    def _make_banner(self) -> QWidget:
        self._banner = QFrame()
        self._banner.setObjectName("banner_info")
        b_lay = QHBoxLayout(self._banner)
        b_lay.setContentsMargins(14, 7, 14, 7)
        self._banner_label = QLabel()
        b_lay.addWidget(self._banner_label)
        b_lay.addStretch()
        btn_dismiss = QPushButton("✕")
        btn_dismiss.setObjectName("icon_btn")
        btn_dismiss.setFixedSize(22, 22)
        btn_dismiss.clicked.connect(lambda: self._banner.setVisible(False))
        b_lay.addWidget(btn_dismiss)
        self._banner.setVisible(False)

        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(14, 6, 14, 0)
        wl.addWidget(self._banner)
        return wrap

    def _build_status_bar(self) -> None:
        bar = QStatusBar()
        self.setStatusBar(bar)
        bar.setSizeGripEnabled(False)

        self._sb_drive = QLabel()
        self._sb_fs = QLabel()
        self._sb_cap = QLabel()

        sep1 = QLabel("·")
        sep1.setStyleSheet("color: #2A2D38; margin: 0 4px;")
        sep2 = QLabel("·")
        sep2.setStyleSheet("color: #2A2D38; margin: 0 4px;")

        bar.addWidget(QLabel("  "))
        bar.addWidget(self._sb_drive)
        bar.addWidget(sep1)
        bar.addWidget(self._sb_fs)
        bar.addWidget(sep2)
        bar.addWidget(self._sb_cap)

        # Right side
        right = QWidget()
        rl = QHBoxLayout(right)
        rl.setContentsMargins(0, 0, 8, 0)
        rl.setSpacing(6)

        self._sb_last_scan = QLabel()
        rl.addWidget(self._sb_last_scan)

        sep3 = QLabel("·")
        sep3.setStyleSheet("color: #2A2D38; margin: 0 4px;")
        rl.addWidget(sep3)

        dot = QLabel("●")
        dot.setStyleSheet("font-size: 7px; color: #10B981;")
        rl.addWidget(dot)
        rl.addWidget(QLabel("Engines ready"))

        bar.addPermanentWidget(right)
        self._update_status_bar()

    # ── Drive management ──────────────────────────────────────────────────────

    def _refresh_drives(self) -> None:
        current_path = (
            self._drives[self._combo_drive.currentIndex()].path
            if self._combo_drive.currentIndex() >= 0 and self._drives
            else None
        )
        self._drives = self._backend.list_removable_drives()
        self._combo_drive.blockSignals(True)
        self._combo_drive.clear()
        for d in self._drives:
            self._combo_drive.addItem(d.display_name())
        self._combo_drive.blockSignals(False)

        if self._drives:
            idx = next((i for i, d in enumerate(self._drives) if d.path == current_path), 0)
            self._combo_drive.setCurrentIndex(idx)
            self._on_drive_selected(idx)
        else:
            self._set_active_drive(None)

    @Slot(int)
    def _on_drive_selected(self, index: int) -> None:
        if 0 <= index < len(self._drives):
            self._set_active_drive(self._drives[index])
        else:
            self._set_active_drive(None)

    def _set_active_drive(self, drive: DriveInfo | None) -> None:
        self._current_drive = drive
        self._scan_panel.set_drive(drive)
        self._format_panel.set_drive(drive)
        self._host_panel.set_drive(drive)
        connected = drive is not None
        self._drive_dot.setStyleSheet(
            f"font-size: 8px; color: {'#10B981' if connected else '#6B6E7A'};"
        )
        self._update_status_bar(drive)

    def _update_status_bar(self, drive: DriveInfo | None = None) -> None:
        if drive:
            self._sb_drive.setText(f"<b>Drive:</b> {drive.path.rstrip('/\\')} ({drive.label})")
            self._sb_fs.setText(f"<b>Filesystem:</b> {drive.filesystem}")
            self._sb_cap.setText(f"<b>Capacity:</b> {drive.free_str()} free of {drive.size_str()}")
        else:
            self._sb_drive.setText("No drive connected")
            self._sb_fs.setText("")
            self._sb_cap.setText("")
        if self._last_scan_time:
            self._sb_last_scan.setText(f"Last scan: <b>{self._last_scan_time}</b>")
        else:
            self._sb_last_scan.setText("")

    # ── Hot-plug monitor ──────────────────────────────────────────────────────

    def _start_monitor(self, monitor: DriveMonitor) -> None:
        self._monitor_worker = MonitorWorker(monitor)
        self._monitor_worker.drive_connected.connect(self._on_drive_connected)
        self._monitor_worker.drive_disconnected.connect(self._on_drive_disconnected)
        self._monitor_worker.start()

    @Slot(object)
    def _on_drive_connected(self, drive: DriveInfo) -> None:
        self._show_banner(f"USB connected: {drive.display_name()}")
        self._refresh_drives()
        for i, d in enumerate(self._drives):
            if d.path == drive.path:
                self._combo_drive.setCurrentIndex(i)
                break

    @Slot(str)
    def _on_drive_disconnected(self, path: str) -> None:
        self._show_banner(f"USB removed: {path}")
        self._refresh_drives()

    def _show_banner(self, msg: str) -> None:
        self._banner_label.setText(msg)
        self._banner.setVisible(True)
        QTimer.singleShot(8000, lambda: self._banner.setVisible(False))

    # ── Scan badge ────────────────────────────────────────────────────────────

    @Slot(int, str)
    def _on_scan_completed(self, threat_count: int, timestamp: str) -> None:
        self._tabs.set_badge(0, threat_count)
        self._last_scan_time = timestamp
        self._update_status_bar(self._current_drive)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _toggle_theme(self) -> None:
        new_theme = "light" if self._settings.theme == "dark" else "dark"
        self._settings.theme = new_theme
        palette = _theme.DARK if new_theme == "dark" else _theme.LIGHT
        QApplication.instance().setStyleSheet(_theme.stylesheet(palette))
        self._update_theme_btn()

    def _update_theme_btn(self) -> None:
        is_dark = self._settings.theme == "dark"
        self._btn_theme.setIcon(
            icons.icon("sun" if is_dark else "moon", 14, "#B0B3BC")
        )

    # ── YARA rules update ─────────────────────────────────────────────────────

    def _update_rules(self) -> None:
        from PySide6.QtWidgets import QMessageBox, QProgressDialog
        dlg = QProgressDialog("Downloading YARA rules from Neo23x0/signature-base…", "Cancel", 0, 100, self)
        dlg.setWindowTitle("Update Rules")
        dlg.setWindowModality(Qt.WindowModal)
        dlg.show()

        success = self._yara.download_rules(
            progress_cb=lambda p: (dlg.setValue(p), QApplication.processEvents())
        )
        dlg.close()

        if success:
            QMessageBox.information(self, "Rules Updated", "YARA rules downloaded and ready.")
        else:
            QMessageBox.warning(self, "Update Failed", "Could not download rules. Check your internet connection.")

    def closeEvent(self, event) -> None:
        if hasattr(self, "_monitor_worker"):
            self._monitor_worker.stop()
        if hasattr(self, "_refresh_timer"):
            self._refresh_timer.stop()
        super().closeEvent(event)
