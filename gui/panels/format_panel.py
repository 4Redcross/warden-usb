import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.formatter import FILESYSTEMS_LINUX, FILESYSTEMS_WINDOWS, Formatter
from core.models import DriveInfo, FormatJob
from gui import icons
from workers.format_worker import FormatWorker


class FormatPanel(QWidget):
    def __init__(self, formatter: Formatter, parent=None):
        super().__init__(parent)
        self._formatter = formatter
        self._current_drive: DriveInfo | None = None
        self._worker: FormatWorker | None = None
        self._fs_buttons: list[QPushButton] = []
        self._selected_fs: str = "exFAT"
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        root.addWidget(self._build_drive_card())
        root.addWidget(self._build_options_card())
        root.addWidget(self._build_warning_banner())

        # Progress (hidden until formatting)
        self._progress_label = QLabel()
        self._progress_label.setObjectName("caption")
        self._progress_label.setVisible(False)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        root.addWidget(self._progress_label)
        root.addWidget(self._progress)

        root.addLayout(self._build_footer())
        root.addStretch()

    # ── Drive info card ───────────────────────────────────────────────────────

    def _build_drive_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(16)

        # Icon box
        icon_box = QFrame()
        icon_box.setObjectName("icon_box")
        icon_box.setFixedSize(42, 42)
        ibl = QVBoxLayout(icon_box)
        ibl.setContentsMargins(11, 11, 11, 11)
        drive_ico = QLabel()
        drive_ico.setPixmap(icons.pixmap("drive", 20, "#7C3AED"))
        ibl.addWidget(drive_ico)
        cl.addWidget(icon_box)

        # Metadata
        meta = QVBoxLayout()
        meta.setSpacing(3)
        self._lbl_drive_name = QLabel("No drive selected")
        self._lbl_drive_name.setStyleSheet("font-weight: 600; font-size: 14px;")
        meta.addWidget(self._lbl_drive_name)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(0)
        self._lbl_meta = QLabel("—")
        self._lbl_meta.setObjectName("caption")
        meta_row.addWidget(self._lbl_meta)
        meta_row.addStretch()
        meta.addLayout(meta_row)
        cl.addLayout(meta, 1)

        # Erase badge
        erase_badge = QLabel()
        erase_badge.setObjectName("badge_erase")
        ico_lbl = QLabel()
        ico_lbl.setPixmap(icons.pixmap("alert", 11, "#F59E0B"))
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(0, 0, 0, 0)
        badge_row.setSpacing(5)
        badge_row.addWidget(ico_lbl)
        badge_row.addWidget(QLabel("Will erase all data"))
        erase_badge.setLayout(badge_row)
        cl.addWidget(erase_badge)

        self._drive_card = card
        return card

    # ── Options card ─────────────────────────────────────────────────────────

    def _build_options_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Head
        head = QFrame()
        head.setObjectName("card_head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(14, 10, 14, 10)
        hl.setSpacing(8)
        disk_ico = QLabel()
        disk_ico.setPixmap(icons.pixmap("disk", 14, "#B0B3BC"))
        hl.addWidget(disk_ico)
        title = QLabel("Format options")
        title.setObjectName("h3")
        hl.addWidget(title)
        sub = QLabel("Choose a filesystem and label for the drive")
        sub.setObjectName("sub")
        hl.addWidget(sub)
        hl.addStretch()
        vbox.addWidget(head)

        # Body
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(14, 14, 14, 14)
        bl.setSpacing(14)

        # Row 1: filesystem toggles + label + allocation unit
        row1 = QHBoxLayout()
        row1.setSpacing(14)

        fs_col = QVBoxLayout()
        fs_lbl = QLabel("Filesystem")
        fs_lbl.setObjectName("h3")
        fs_col.addWidget(fs_lbl)
        fs_btn_row = QHBoxLayout()
        fs_btn_row.setSpacing(6)
        fs_list = FILESYSTEMS_WINDOWS if sys.platform == "win32" else FILESYSTEMS_LINUX
        for fs in fs_list[:3]:  # show max 3 toggle buttons
            btn = QPushButton(fs)
            btn.setCheckable(True)
            btn.setChecked(fs == self._selected_fs)
            btn.setObjectName("fs_active" if fs == self._selected_fs else "fs_btn")
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda checked, f=fs: self._select_fs(f))
            self._fs_buttons.append(btn)
            fs_btn_row.addWidget(btn)
        fs_col.addLayout(fs_btn_row)
        row1.addLayout(fs_col, 2)

        label_col = QVBoxLayout()
        label_lbl = QLabel("Volume label")
        label_lbl.setObjectName("h3")
        label_col.addWidget(label_lbl)
        self._input_label = QLineEdit()
        self._input_label.setPlaceholderText("WARDEN-SECURE")
        label_col.addWidget(self._input_label)
        row1.addLayout(label_col, 2)

        alloc_col = QVBoxLayout()
        alloc_lbl = QLabel("Allocation unit")
        alloc_lbl.setObjectName("h3")
        alloc_col.addWidget(alloc_lbl)
        self._combo_alloc = QComboBox()
        self._combo_alloc.addItems(["Default", "4 KB", "8 KB", "16 KB", "32 KB", "64 KB", "128 KB"])
        alloc_col.addWidget(self._combo_alloc)
        row1.addLayout(alloc_col, 2)

        bl.addLayout(row1)

        # Checkboxes
        chk_row = QHBoxLayout()
        chk_row.setSpacing(24)
        self._chk_quick = QCheckBox("Quick format")
        self._chk_quick.setChecked(True)
        self._chk_verify = QCheckBox("Verify after format")
        self._chk_recovery = QCheckBox("Write Warden recovery key to drive")
        chk_row.addWidget(self._chk_quick)
        chk_row.addWidget(self._chk_verify)
        chk_row.addWidget(self._chk_recovery)
        chk_row.addStretch()
        bl.addLayout(chk_row)

        vbox.addWidget(body)
        return card

    # ── Warning banner ────────────────────────────────────────────────────────

    def _build_warning_banner(self) -> QFrame:
        banner = QFrame()
        banner.setObjectName("banner_warn")
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(14, 12, 14, 12)
        bl.setSpacing(12)

        # ! icon
        icon_lbl = QLabel("!")
        icon_lbl.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #F59E0B; "
            "background: #F59E0B22; border: 1px solid #F59E0B44; "
            "border-radius: 5px; padding: 3px 8px; min-width: 22px;"
        )
        icon_lbl.setAlignment(Qt.AlignCenter)
        bl.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        self._warn_title = QLabel("This will permanently erase everything on the selected drive")
        self._warn_title.setStyleSheet("font-weight: 600; font-size: 12.5px;")
        self._warn_title.setWordWrap(True)
        text_col.addWidget(self._warn_title)
        self._warn_body = QLabel(
            "All data on the drive will be wiped. Quick format does not securely wipe blocks; "
            "disable it above for a forensic wipe. This action cannot be undone."
        )
        self._warn_body.setObjectName("caption")
        self._warn_body.setWordWrap(True)
        text_col.addWidget(self._warn_body)
        bl.addLayout(text_col, 1)

        self._chk_understand = QCheckBox("I understand")
        self._chk_understand.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._chk_understand.stateChanged.connect(self._on_understand_toggled)
        bl.addWidget(self._chk_understand)

        self._warn_banner = banner
        return banner

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        self._lbl_est_time = QLabel()
        self._lbl_est_time.setObjectName("caption")
        row.addWidget(self._lbl_est_time)

        row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("ghost")
        btn_cancel.clicked.connect(self._cancel_format)
        row.addWidget(btn_cancel)

        self._btn_format = QPushButton()
        self._btn_format.setObjectName("danger")
        self._btn_format.setIcon(icons.icon("alert", 14, "#FFFFFF"))
        self._btn_format.setText("Format Drive")
        self._btn_format.setEnabled(False)
        self._btn_format.clicked.connect(self._confirm_format)
        row.addWidget(self._btn_format)

        return row

    # ── Drive selection ───────────────────────────────────────────────────────

    def set_drive(self, drive: DriveInfo | None) -> None:
        self._current_drive = drive
        self._chk_understand.setChecked(False)

        if drive:
            self._lbl_drive_name.setText(drive.display_name())
            parts = [drive.filesystem, drive.size_str(), drive.free_str() + " free"]
            if drive.device_id:
                parts.append(f"ID {drive.device_id}")
            self._lbl_meta.setText("  ·  ".join(parts))
            self._input_label.setPlaceholderText(drive.label or "WARDEN-SECURE")
            used_gb = (drive.total_bytes - drive.free_bytes) / 1e9 if drive.total_bytes else 0
            secs = int(used_gb * 0.5) if not self._chk_quick.isChecked() else 30
            self._lbl_est_time.setText(
                f"Estimated time: <b>~{secs} seconds</b> with quick format {'enabled' if self._chk_quick.isChecked() else 'disabled'}"
            )
            self._warn_title.setText(
                f"This will permanently erase everything on {drive.path.rstrip('/\\')}:"
            )
        else:
            self._lbl_drive_name.setText("No drive selected")
            self._lbl_meta.setText("—")
            self._lbl_est_time.setText("")
            self._input_label.setPlaceholderText("WARDEN-SECURE")
            self._warn_title.setText("This will permanently erase everything on the selected drive")

    # ── Filesystem toggle ─────────────────────────────────────────────────────

    def _select_fs(self, fs: str) -> None:
        self._selected_fs = fs
        for btn in self._fs_buttons:
            active = btn.text() == fs
            btn.setObjectName("fs_active" if active else "fs_btn")
            btn.setChecked(active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ── Format flow ───────────────────────────────────────────────────────────

    def _on_understand_toggled(self, state: int) -> None:
        self._btn_format.setEnabled(state == Qt.Checked and self._current_drive is not None)

    def _confirm_format(self) -> None:
        if not self._current_drive:
            return

        label = self._input_label.text().strip() or self._current_drive.label or "USB Drive"
        filesystem = self._selected_fs

        dlg = _ConfirmDialog(self._current_drive, filesystem, label, self)
        if dlg.exec() != QDialog.Accepted:
            return

        job = FormatJob(
            drive=self._current_drive,
            filesystem=filesystem,
            label=label,
            quick_format=self._chk_quick.isChecked(),
            confirmed=True,
        )

        self._btn_format.setEnabled(False)
        self._chk_understand.setChecked(False)
        self._progress_label.setText(f"Formatting as {filesystem}…")
        self._progress_label.setVisible(True)
        self._progress.setVisible(True)

        self._worker = FormatWorker(self._formatter, job)
        self._worker.status.connect(self._progress_label.setText)
        self._worker.finished.connect(self._on_format_done)
        self._worker.error.connect(self._on_format_error)
        self._worker.start()

    def _cancel_format(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
        self._chk_understand.setChecked(False)
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)

    def _on_format_done(self) -> None:
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)
        QMessageBox.information(self, "Format Complete", "Drive formatted successfully.")

    def _on_format_error(self, msg: str) -> None:
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)
        QMessageBox.critical(self, "Format Failed", msg)


# ── Confirm dialog ────────────────────────────────────────────────────────────

class _ConfirmDialog(QDialog):
    def __init__(self, drive: DriveInfo, filesystem: str, label: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Format")
        self.setMinimumWidth(420)

        lay = QVBoxLayout(self)
        lay.setSpacing(12)

        warn = QLabel("⚠  This will permanently erase all data on the drive.")
        warn.setStyleSheet("font-weight: 600; font-size: 14px;")
        lay.addWidget(warn)

        details = QLabel(
            f"Drive:       {drive.display_name()}\n"
            f"Size:        {drive.size_str()}\n"
            f"Filesystem:  {filesystem}\n"
            f"New label:   {label}"
        )
        details.setStyleSheet(
            "font-family: 'Cascadia Code', Consolas, monospace; font-size: 13px;"
        )
        lay.addWidget(details)

        if ":" in drive.path:
            expected = drive.path.rstrip("\\/").split(":")[0]
        else:
            expected = drive.path.strip("/").split("/")[-1]

        confirm_lbl = QLabel(f"Type  <b>{expected}</b>  to confirm:")
        confirm_lbl.setTextFormat(Qt.RichText)
        lay.addWidget(confirm_lbl)

        self._input = QLineEdit()
        self._input.setPlaceholderText(expected)
        lay.addWidget(self._input)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._check_confirm)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        self._expected = expected.upper()

    def _check_confirm(self) -> None:
        if self._input.text().strip().upper() == self._expected:
            self.accept()
        else:
            QMessageBox.warning(self, "Mismatch", "Input did not match. Format cancelled.")
