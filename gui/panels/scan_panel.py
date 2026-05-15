from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.models import DriveInfo, QuarantineEntry, ScanResult, ThreatInfo, ThreatLevel
from core.quarantine import QuarantineManager
from core.scanner import Scanner
from core.virustotal import VirusTotalClient
from gui import icons
from workers.scan_worker import ScanWorker


# ── Severity pip ─────────────────────────────────────────────────────────────

_SEV_CFG = {
    ThreatLevel.MALICIOUS:  ("#EF4444", "████", "Critical"),
    ThreatLevel.SUSPICIOUS: ("#F97316", "███",  "High"),
}


def _sev_label(level: ThreatLevel) -> QLabel:
    color, bars, text = _SEV_CFG.get(level, ("#F59E0B", "██", "Medium"))
    lbl = QLabel(f'<span style="color:{color};font-weight:600;font-size:11px;letter-spacing:1px;">'
                 f'{bars}</span>'
                 f'<span style="color:{color};font-weight:600;font-size:11.5px;"> {text}</span>')
    lbl.setTextFormat(Qt.RichText)
    lbl.setContentsMargins(0, 0, 0, 0)
    return lbl


# ── Two-line file cell ────────────────────────────────────────────────────────

def _file_cell(filename: str, path: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(6, 4, 6, 4)
    lay.setSpacing(1)
    name = QLabel(filename)
    name.setStyleSheet("font-weight: 600; font-size: 12.5px;")
    p = QLabel(path)
    p.setStyleSheet("font-size: 10.5px; color: #6B6E7A;")
    lay.addWidget(name)
    lay.addWidget(p)
    return w


# ── Card header helper ────────────────────────────────────────────────────────

def _card_head(icon_name: str, icon_color: str, title: str, subtitle: str = "") -> tuple[QFrame, QHBoxLayout]:
    head = QFrame()
    head.setObjectName("card_head")
    lay = QHBoxLayout(head)
    lay.setContentsMargins(14, 10, 14, 10)
    lay.setSpacing(8)

    ico = QLabel()
    ico.setPixmap(icons.pixmap(icon_name, 14, icon_color))
    lay.addWidget(ico)

    title_lbl = QLabel(title)
    title_lbl.setObjectName("h2")
    lay.addWidget(title_lbl)

    if subtitle:
        sub = QLabel(subtitle)
        sub.setObjectName("sub")
        lay.addWidget(sub)

    return head, lay


# ── Scan panel ────────────────────────────────────────────────────────────────

class ScanPanel(QWidget):
    scan_completed = Signal(int, str)   # (threat_count, timestamp)
    request_vt_upload = Signal(object)  # QuarantineEntry

    def __init__(
        self,
        scanner: Scanner,
        quarantine: QuarantineManager,
        vt_client: VirusTotalClient | None,
        parent=None,
    ):
        super().__init__(parent)
        self._scanner = scanner
        self._quarantine = quarantine
        self._vt = vt_client
        self._worker: ScanWorker | None = None
        self._current_drive: DriveInfo | None = None
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        root.addWidget(self._build_controls_card())
        root.addWidget(self._build_threats_card(), 1)
        root.addWidget(self._build_quarantine_card())

    # ── Controls card ─────────────────────────────────────────────────────────

    def _build_controls_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Top row: drive info | checkboxes | buttons
        top = QWidget()
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(14, 12, 14, 12)
        top_lay.setSpacing(0)

        # Drive icon + name
        icon_box = QFrame()
        icon_box.setObjectName("icon_box")
        icon_box.setFixedSize(38, 38)
        ib_lay = QVBoxLayout(icon_box)
        ib_lay.setContentsMargins(9, 9, 9, 9)
        drive_ico = QLabel()
        drive_ico.setPixmap(icons.pixmap("drive", 20, "#7C3AED"))
        ib_lay.addWidget(drive_ico)
        top_lay.addWidget(icon_box)
        top_lay.addSpacing(10)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        self._drive_label = QLabel("No drive selected")
        self._drive_label.setObjectName("h2")
        self._drive_meta = QLabel("")
        self._drive_meta.setObjectName("sub")
        name_col.addWidget(self._drive_label)
        name_col.addWidget(self._drive_meta)
        top_lay.addLayout(name_col)

        # Vertical divider
        div = QFrame()
        div.setFrameShape(QFrame.VLine)
        div.setStyleSheet("color: #2A2D38; min-width: 1px; max-width: 1px; margin: 4px 16px;")
        top_lay.addWidget(div)

        # Checkboxes
        self._chk_clam = QCheckBox("ClamAV")
        self._chk_clam.setChecked(True)
        self._chk_yara = QCheckBox("YARA rules")
        self._chk_yara.setChecked(True)
        self._chk_vt = QCheckBox("VirusTotal hash lookup")
        self._chk_vt.setToolTip("Sends SHA-256 hash only — no file upload")
        top_lay.addWidget(self._chk_clam)
        top_lay.addSpacing(12)
        top_lay.addWidget(self._chk_yara)
        top_lay.addSpacing(12)
        top_lay.addWidget(self._chk_vt)

        top_lay.addStretch()

        self._btn_scan = QPushButton()
        self._btn_scan.setIcon(icons.icon("scan", 14, "#FFFFFF"))
        self._btn_scan.setText("Scan Drive")
        self._btn_scan.setEnabled(False)
        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setObjectName("ghost")
        self._btn_cancel.setVisible(False)
        top_lay.addWidget(self._btn_cancel)
        top_lay.addSpacing(8)
        top_lay.addWidget(self._btn_scan)

        lay.addWidget(top)

        # Stats row (darker bg, border-top)
        self._stats_row = QFrame()
        self._stats_row.setObjectName("card_foot")
        sr_lay = QHBoxLayout(self._stats_row)
        sr_lay.setContentsMargins(14, 10, 14, 10)
        sr_lay.setSpacing(0)

        self._lbl_files = self._kv_block(sr_lay, "FILES SCANNED", "—")
        self._vdiv(sr_lay)
        self._lbl_threats = self._kv_block(sr_lay, "THREATS", "—", danger=False)
        self._vdiv(sr_lay)
        self._lbl_quarantined = self._kv_block(sr_lay, "QUARANTINED", "—")
        self._vdiv(sr_lay)
        self._lbl_duration = self._kv_block(sr_lay, "DURATION", "—")

        sr_lay.addStretch()

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setVisible(False)
        self._progress.setFixedWidth(140)
        sr_lay.addWidget(self._progress)

        self._badge_result = QLabel()
        self._badge_result.setObjectName("badge_threat")
        self._badge_result.setVisible(False)
        sr_lay.addSpacing(8)
        sr_lay.addWidget(self._badge_result)

        self._lbl_scan_time = QLabel()
        self._lbl_scan_time.setObjectName("sub")
        self._lbl_scan_time.setVisible(False)
        sr_lay.addSpacing(8)
        sr_lay.addWidget(self._lbl_scan_time)

        lay.addWidget(self._stats_row)

        self._btn_scan.clicked.connect(self._start_scan)
        self._btn_cancel.clicked.connect(self._cancel_scan)
        return card

    def _kv_block(self, layout: QHBoxLayout, key: str, value: str, danger: bool = False) -> QLabel:
        col = QVBoxLayout()
        col.setSpacing(2)
        k = QLabel(key)
        k.setStyleSheet("font-size: 10px; font-weight: 600; color: #6B6E7A; letter-spacing: 0.08em;")
        v = QLabel(value)
        v.setStyleSheet("font-size: 15px; font-weight: 600;")
        col.addWidget(k)
        col.addWidget(v)
        layout.addLayout(col)
        layout.addSpacing(20)
        return v

    def _vdiv(self, layout: QHBoxLayout) -> None:
        d = QFrame()
        d.setFrameShape(QFrame.VLine)
        d.setStyleSheet("color: #2A2D38; min-width: 1px; max-width: 1px; margin: 2px 16px 2px 4px;")
        layout.addWidget(d)

    # ── Threats card ──────────────────────────────────────────────────────────

    def _build_threats_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        head, h_lay = _card_head("alert", "#EF4444", "Detected Threats")
        self._threats_sub = QLabel("No scan run yet")
        self._threats_sub.setObjectName("sub")
        h_lay.addWidget(self._threats_sub)
        h_lay.addStretch()

        self._btn_quarantine_all = QPushButton("Quarantine all")
        self._btn_quarantine_all.setObjectName("sm")
        self._btn_quarantine_all.setEnabled(False)
        h_lay.addWidget(self._btn_quarantine_all)

        self._btn_export = QPushButton("Export report")
        self._btn_export.setObjectName("sm")
        self._btn_export.setEnabled(False)
        h_lay.addWidget(self._btn_export)

        lay.addWidget(head)

        self._threats_table = QTableWidget(0, 5)
        self._threats_table.setHorizontalHeaderLabels(["File", "Threat", "Engine", "Severity", "Action"])
        self._threats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._threats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._threats_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._threats_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._threats_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._threats_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._threats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._threats_table.setAlternatingRowColors(True)
        self._threats_table.verticalHeader().setVisible(False)
        self._threats_table.setShowGrid(False)
        lay.addWidget(self._threats_table, 1)

        return card

    # ── Quarantine card ───────────────────────────────────────────────────────

    def _build_quarantine_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        head, h_lay = _card_head("lock", "#B0B3BC", "Quarantine")
        self._q_sub = QLabel("0 files isolated · encrypted at-rest")
        self._q_sub.setObjectName("sub")
        h_lay.addWidget(self._q_sub)
        h_lay.addStretch()

        self._btn_vault = QPushButton("Open vault")
        self._btn_vault.setObjectName("sm")
        h_lay.addWidget(self._btn_vault)

        lay.addWidget(head)

        self._q_table = QTableWidget(0, 5)
        self._q_table.setHorizontalHeaderLabels(["File", "Original Threat", "Size", "Quarantined", "Actions"])
        self._q_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._q_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._q_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._q_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._q_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._q_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._q_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._q_table.setAlternatingRowColors(True)
        self._q_table.verticalHeader().setVisible(False)
        self._q_table.setShowGrid(False)
        self._q_table.setMaximumHeight(160)
        lay.addWidget(self._q_table)

        # Footer with "N more" info
        self._q_footer = QFrame()
        self._q_footer.setObjectName("card_foot")
        qf_lay = QHBoxLayout(self._q_footer)
        qf_lay.setContentsMargins(14, 7, 14, 7)
        self._q_more_lbl = QLabel()
        self._q_more_lbl.setObjectName("sub")
        qf_lay.addWidget(self._q_more_lbl)
        qf_lay.addStretch()
        btn_view_all = QPushButton("View all")
        btn_view_all.setObjectName("sm")
        btn_view_all.clicked.connect(self._show_full_quarantine)
        qf_lay.addWidget(btn_view_all)
        self._q_footer.setVisible(False)
        lay.addWidget(self._q_footer)

        self._btn_vault.clicked.connect(self._show_full_quarantine)
        self._load_quarantine()
        return card

    # ── Drive selection ───────────────────────────────────────────────────────

    def set_drive(self, drive: DriveInfo | None) -> None:
        self._current_drive = drive
        if drive:
            self._drive_label.setText(drive.display_name())
            self._drive_meta.setText(f"{drive.filesystem} · {drive.size_str()} · {drive.free_str()} used")
            self._btn_scan.setEnabled(True)
        else:
            self._drive_label.setText("No drive selected")
            self._drive_meta.setText("")
            self._btn_scan.setEnabled(False)

    # ── Scan lifecycle ────────────────────────────────────────────────────────

    def _start_scan(self) -> None:
        if not self._current_drive:
            return

        self._scanner.use_clamav = self._chk_clam.isChecked()
        self._scanner.use_yara = self._chk_yara.isChecked()
        self._scanner.use_vt_hash = self._chk_vt.isChecked()

        self._threats_table.setRowCount(0)
        self._badge_result.setVisible(False)
        self._lbl_scan_time.setVisible(False)
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._btn_scan.setVisible(False)
        self._btn_cancel.setVisible(True)

        self._worker = ScanWorker(self._scanner, self._current_drive)
        self._worker.progress.connect(self._on_progress)
        self._worker.result.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _cancel_scan(self) -> None:
        if self._worker:
            self._worker.cancel()
        self._reset_controls()

    @Slot(int, str)
    def _on_progress(self, pct: int, filepath: str) -> None:
        self._progress.setValue(pct)
        name = Path(filepath).name
        self._threats_sub.setText(f"Scanning: {name}")

    @Slot(object)
    def _on_result(self, result: ScanResult) -> None:
        self._reset_controls()
        self._show_summary(result)
        self._populate_threats(result)
        self._load_quarantine()
        ts = datetime.now().strftime("%b %-d, %H:%M") if hasattr(datetime.now(), 'strftime') else ""
        try:
            ts = datetime.now().strftime("%b %d, %H:%M").lstrip("0")
        except Exception:
            ts = ""
        self.scan_completed.emit(result.threat_count, ts)

    @Slot(str)
    def _on_error(self, msg: str) -> None:
        self._reset_controls()
        QMessageBox.critical(self, "Scan Error", msg)

    def _reset_controls(self) -> None:
        self._progress.setVisible(False)
        self._btn_scan.setVisible(True)
        self._btn_cancel.setVisible(False)

    # ── Result display ────────────────────────────────────────────────────────

    def _show_summary(self, result: ScanResult) -> None:
        self._lbl_files.setText(f"{result.files_scanned:,}")
        self._lbl_quarantined.setText(str(result.threat_count))
        self._lbl_duration.setText(result.duration_str())

        if result.is_clean:
            self._lbl_threats.setText("0")
            self._lbl_threats.setStyleSheet("font-size: 15px; font-weight: 600;")
            self._badge_result.setText("  Clean  ")
            self._badge_result.setObjectName("badge_clean")
        else:
            self._lbl_threats.setText(str(result.threat_count))
            self._lbl_threats.setStyleSheet(f"font-size: 15px; font-weight: 600; color: #EF4444;")
            self._badge_result.setText(f"  {result.threat_count} Threat(s) Detected  ")
            self._badge_result.setObjectName("badge_threat")

        self._badge_result.style().unpolish(self._badge_result)
        self._badge_result.style().polish(self._badge_result)
        self._badge_result.setVisible(True)

        self._threats_sub.setText(
            f"{result.threat_count} item{'s' if result.threat_count != 1 else ''} · grouped by severity"
        )
        self._btn_quarantine_all.setEnabled(result.threat_count > 0)
        self._btn_export.setEnabled(True)

    def _populate_threats(self, result: ScanResult) -> None:
        self._threats_table.setRowCount(0)
        self._threats_table.setRowCount(len(result.threats))
        for row, threat in enumerate(result.threats):
            self._threats_table.setRowHeight(row, 48)

            file_w = _file_cell(threat.file_path.name, str(threat.file_path))
            self._threats_table.setCellWidget(row, 0, file_w)

            self._threats_table.setItem(row, 1, QTableWidgetItem(threat.threat_name))
            self._threats_table.setItem(row, 2, QTableWidgetItem(threat.detected_by))

            sev_w = QWidget()
            sl = QHBoxLayout(sev_w)
            sl.setContentsMargins(6, 0, 6, 0)
            sl.addWidget(_sev_label(threat.threat_level))
            sl.addStretch()
            self._threats_table.setCellWidget(row, 3, sev_w)

            act_w = QWidget()
            al = QHBoxLayout(act_w)
            al.setContentsMargins(4, 4, 4, 4)
            btn_q = QPushButton("Quarantine")
            btn_q.setObjectName("sm")
            al.addWidget(btn_q)
            self._threats_table.setCellWidget(row, 4, act_w)

    # ── Quarantine ────────────────────────────────────────────────────────────

    def _load_quarantine(self) -> None:
        entries = self._quarantine.list_entries()
        count = len(entries)

        self._q_sub.setText(f"{count} file{'s' if count != 1 else ''} isolated · encrypted at-rest")

        # Show only first row in compact view
        shown = entries[:1]
        self._q_table.setRowCount(0)
        self._q_table.setRowCount(len(shown))
        for row, entry in enumerate(shown):
            self._q_table.setRowHeight(row, 46)

            file_w = _file_cell(entry.original_path.name, str(entry.original_path))
            self._q_table.setCellWidget(row, 0, file_w)

            self._q_table.setItem(row, 1, QTableWidgetItem(entry.threat_name))

            try:
                size = entry.quarantine_path.stat().st_size
                size_str = f"{size // 1024} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
            except Exception:
                size_str = "—"
            self._q_table.setItem(row, 2, QTableWidgetItem(size_str))
            self._q_table.setItem(row, 3, QTableWidgetItem("Recently"))

            act_w = self._make_q_actions(entry)
            self._q_table.setCellWidget(row, 4, act_w)

        extra = count - len(shown)
        if extra > 0:
            self._q_more_lbl.setText(f"+{extra} more in quarantine")
            self._q_footer.setVisible(True)
        else:
            self._q_footer.setVisible(False)

    def _make_q_actions(self, entry: QuarantineEntry) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        vt_enabled = self._vt is not None and self._vt.is_configured()

        btn_hash = QPushButton()
        btn_hash.setObjectName("sm_icon")
        btn_hash.setIcon(icons.icon("hash", 12, "#B0B3BC"))
        btn_hash.setText("VT Hash")
        btn_hash.setEnabled(vt_enabled)
        btn_hash.clicked.connect(lambda: self._vt_hash_lookup(entry))

        btn_upload = QPushButton()
        btn_upload.setObjectName("sm_icon")
        btn_upload.setIcon(icons.icon("upload", 12, "#B0B3BC"))
        btn_upload.setText("VT Upload")
        btn_upload.setEnabled(vt_enabled)
        btn_upload.clicked.connect(lambda: self._confirm_vt_upload(entry))

        btn_restore = QPushButton()
        btn_restore.setObjectName("sm_icon")
        btn_restore.setIcon(icons.icon("restore", 12, "#B0B3BC"))
        btn_restore.setText("Restore")
        btn_restore.clicked.connect(lambda: self._restore(entry))

        btn_del = QPushButton()
        btn_del.setObjectName("sm_icon")
        btn_del.setIcon(icons.icon("trash", 12, "#EF4444"))
        btn_del.setStyleSheet("QPushButton { color: #EF4444; } QPushButton:hover { border-color: #EF4444; }")
        btn_del.clicked.connect(lambda: self._delete_entry(entry))

        lay.addWidget(btn_hash)
        lay.addWidget(btn_upload)
        lay.addWidget(btn_restore)
        lay.addWidget(btn_del)
        lay.addStretch()
        return w

    def _show_full_quarantine(self) -> None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Quarantine Vault")
        dlg.resize(820, 480)
        lay = QVBoxLayout(dlg)
        tbl = QTableWidget(0, 5)
        tbl.setHorizontalHeaderLabels(["File", "Original Threat", "Size", "Quarantined", "Actions"])
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        lay.addWidget(tbl)
        entries = self._quarantine.list_entries()
        tbl.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            tbl.setRowHeight(row, 46)
            tbl.setCellWidget(row, 0, _file_cell(entry.original_path.name, str(entry.original_path)))
            tbl.setItem(row, 1, QTableWidgetItem(entry.threat_name))
            tbl.setItem(row, 2, QTableWidgetItem("—"))
            tbl.setItem(row, 3, QTableWidgetItem("—"))
            tbl.setCellWidget(row, 4, self._make_q_actions(entry))
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)
        dlg.exec()

    def _vt_hash_lookup(self, entry: QuarantineEntry) -> None:
        if not self._vt:
            return
        result = self._vt.hash_lookup(entry.sha256)
        if result is None:
            QMessageBox.warning(self, "VT Lookup", "Request failed. Check your API key and connection.")
        elif not result.get("found"):
            QMessageBox.information(self, "VT Lookup", "Hash not found in VirusTotal database.")
        else:
            mal = result.get("malicious", 0)
            total = result.get("total", 0)
            name = result.get("name", "Unknown")
            QMessageBox.information(self, "VT Hash Result",
                f"Name: {name}\nDetections: {mal}/{total} engines flagged this file.")
        self._quarantine.update_vt_results(entry.id, hash_result=result)

    def _confirm_vt_upload(self, entry: QuarantineEntry) -> None:
        reply = QMessageBox.warning(
            self, "VirusTotal Upload",
            "This file will be uploaded to VirusTotal's servers and may be shared with security researchers.\n\n"
            "Do NOT proceed if the file contains confidential or sensitive data.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.request_vt_upload.emit(entry)

    def _restore(self, entry: QuarantineEntry) -> None:
        if not self._current_drive:
            QMessageBox.warning(self, "Restore", "Select a drive to restore the file to.")
            return
        restored = self._quarantine.restore(entry, Path(self._current_drive.path))
        QMessageBox.information(self, "Restored", f"File restored to:\n{restored}")
        self._load_quarantine()

    def _delete_entry(self, entry: QuarantineEntry) -> None:
        reply = QMessageBox.question(
            self, "Delete",
            f"Permanently delete '{entry.original_path.name}'?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._quarantine.delete(entry)
            self._load_quarantine()
