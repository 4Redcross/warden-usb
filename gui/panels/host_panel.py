import secrets
import string
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.audit import AuditLog
from core.fileserver import FileServer
from core.models import DriveInfo
from gui import icons
from workers.server_worker import ServerWorker


# ── Toggle switch ─────────────────────────────────────────────────────────────

class _ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = True, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(38, 22)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, v: bool) -> None:
        self._checked = v
        self.update()

    def mousePressEvent(self, _):
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#7C3AED") if self._checked else QColor("#2A2D38"))
        p.drawRoundedRect(0, 4, 38, 14, 7, 7)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(20 if self._checked else 2, 1, 20, 20)
        p.end()


# ── Host panel ────────────────────────────────────────────────────────────────

class HostPanel(QWidget):
    def __init__(self, file_server: FileServer, audit: AuditLog, parent=None):
        super().__init__(parent)
        self._server = file_server
        self._audit = audit
        self._current_drive: DriveInfo | None = None
        self._worker: ServerWorker | None = None
        self._server_url: str = ""
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

        if not self._server.is_available():
            warn = QFrame()
            warn.setObjectName("banner_warn")
            wl = QHBoxLayout(warn)
            wl.setContentsMargins(12, 10, 12, 10)
            wl.addWidget(QLabel("⚠  wsgidav / cheroot not installed. Run: pip install wsgidav cheroot"))
            root.addWidget(warn)
            root.addStretch()
            return

        root.addWidget(self._build_config_card())
        root.addWidget(self._build_connected_card())
        root.addLayout(self._build_info_row())
        root.addStretch()

        self._card_connected.setVisible(False)

        # Signals
        self._btn_start.clicked.connect(self._start_server)
        self._btn_stop.clicked.connect(self._stop_server)
        self._btn_copy.clicked.connect(self._copy_url)
        self._btn_show_pass.clicked.connect(self._toggle_password_visibility)
        self._generate_password()

    # ── Config card ───────────────────────────────────────────────────────────

    def _build_config_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        self._card_config = card
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Head
        head = QFrame()
        head.setObjectName("card_head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(14, 10, 14, 10)
        hl.setSpacing(8)
        ico = QLabel()
        ico.setPixmap(icons.pixmap("server", 14, "#B0B3BC"))
        hl.addWidget(ico)
        title = QLabel("WebDAV Server")
        title.setObjectName("h3")
        hl.addWidget(title)
        sub = QLabel("Share the selected drive read-only or read-write over your local network")
        sub.setObjectName("sub")
        hl.addWidget(sub)
        hl.addStretch()
        stopped_badge = QLabel("  ● Stopped")
        stopped_badge.setObjectName("badge_stopped")
        hl.addWidget(stopped_badge)
        vbox.addWidget(head)

        # Body
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(14, 14, 14, 14)
        bl.setSpacing(12)

        # Row 1: bind address + mode
        row1 = QHBoxLayout()
        row1.setSpacing(14)

        bind_col = QVBoxLayout()
        bind_lbl = QLabel("Bind address")
        bind_lbl.setObjectName("h3")
        bind_col.addWidget(bind_lbl)
        bind_inner = QHBoxLayout()
        bind_inner.setSpacing(0)
        self._combo_host = QComboBox()
        self._combo_host.addItems(["0.0.0.0", "127.0.0.1"])
        self._combo_host.setMinimumWidth(110)
        bind_inner.addWidget(self._combo_host)
        colon = QLabel(":")
        colon.setStyleSheet("color: #6B6E7A; padding: 0 4px;")
        bind_inner.addWidget(colon)
        self._spin_port = QSpinBox()
        self._spin_port.setRange(1024, 65535)
        self._spin_port.setValue(8443)
        self._spin_port.setMinimumWidth(80)
        bind_inner.addWidget(self._spin_port)
        bind_col.addLayout(bind_inner)
        row1.addLayout(bind_col)

        mode_col = QVBoxLayout()
        mode_lbl = QLabel("Mode")
        mode_lbl.setObjectName("h3")
        mode_col.addWidget(mode_lbl)
        self._combo_mode = QComboBox()
        self._combo_mode.addItems(["Read-only · safer", "Read-write"])
        mode_col.addWidget(self._combo_mode)
        row1.addLayout(mode_col)

        row1.addStretch()
        bl.addLayout(row1)

        # Row 2: username + password
        row2 = QHBoxLayout()
        row2.setSpacing(14)

        user_col = QVBoxLayout()
        user_lbl = QLabel("Username")
        user_lbl.setObjectName("h3")
        user_col.addWidget(user_lbl)
        self._input_user = QLineEdit("warden")
        user_col.addWidget(self._input_user)
        row2.addLayout(user_col)

        pass_col = QVBoxLayout()
        pass_lbl = QLabel("Password")
        pass_lbl.setObjectName("h3")
        pass_col.addWidget(pass_lbl)
        pass_inner = QHBoxLayout()
        pass_inner.setSpacing(0)
        self._input_pass = QLineEdit()
        self._input_pass.setEchoMode(QLineEdit.Password)
        self._input_pass.setPlaceholderText("auto-generated")
        pass_inner.addWidget(self._input_pass, 1)
        btn_gen = QPushButton()
        btn_gen.setObjectName("sm_icon")
        btn_gen.setIcon(icons.icon("key", 12, "#B0B3BC"))
        btn_gen.setText("Generate")
        btn_gen.clicked.connect(self._generate_password)
        pass_inner.addWidget(btn_gen)
        pass_col.addLayout(pass_inner)
        row2.addLayout(pass_col)

        row2.addStretch()
        bl.addLayout(row2)

        # Row 3: checkboxes + HTTPS toggle
        row3 = QHBoxLayout()
        row3.setSpacing(24)
        self._chk_localhost = QCheckBox("Localhost only (127.0.0.1)")
        self._chk_allow_write = QCheckBox("Allow write access")
        row3.addWidget(self._chk_localhost)
        row3.addWidget(self._chk_allow_write)
        row3.addStretch()

        https_row = QHBoxLayout()
        https_row.setSpacing(8)
        https_lbl = QLabel("HTTPS")
        https_lbl.setStyleSheet("font-size: 12.5px;")
        https_row.addWidget(https_lbl)
        self._toggle_https = _ToggleSwitch(checked=True)
        https_row.addWidget(self._toggle_https)
        cert_lbl = QLabel("self-signed cert")
        cert_lbl.setObjectName("caption")
        https_row.addWidget(cert_lbl)
        row3.addLayout(https_row)
        bl.addLayout(row3)

        vbox.addWidget(body)

        # Footer
        foot = QFrame()
        foot.setObjectName("card_foot")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(14, 10, 14, 10)
        fl.setSpacing(8)
        lock_ico = QLabel()
        lock_ico.setPixmap(icons.pixmap("lock", 11, "#6B6E7A"))
        fl.addWidget(lock_ico)
        note = QLabel("Server runs only while Warden is open. Credentials are session-scoped.")
        note.setObjectName("caption")
        fl.addWidget(note)
        fl.addStretch()
        self._btn_start = QPushButton()
        self._btn_start.setIcon(icons.icon("server", 13, "#FFFFFF"))
        self._btn_start.setText("Start Server")
        self._btn_start.setEnabled(False)
        fl.addWidget(self._btn_start)
        vbox.addWidget(foot)

        return card

    # ── Connected card ────────────────────────────────────────────────────────

    def _build_connected_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        self._card_connected = card
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Head
        head = QFrame()
        head.setObjectName("card_head")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(14, 10, 14, 10)
        hl.setSpacing(8)
        ico = QLabel()
        ico.setPixmap(icons.pixmap("server", 14, "#3B82F6"))
        hl.addWidget(ico)
        title = QLabel("WebDAV Server")
        title.setObjectName("h3")
        hl.addWidget(title)
        self._lbl_sharing = QLabel()
        self._lbl_sharing.setObjectName("sub")
        hl.addWidget(self._lbl_sharing)
        hl.addStretch()
        running_badge = QLabel("  ● Running")
        running_badge.setObjectName("badge_running")
        hl.addWidget(running_badge)
        vbox.addWidget(head)

        # Body
        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(14, 14, 14, 14)
        bl.setSpacing(18)

        # Left column: URL + credentials
        left = QVBoxLayout()
        left.setSpacing(10)

        url_lbl = QLabel("WebDAV URL")
        url_lbl.setObjectName("h3")
        left.addWidget(url_lbl)

        url_row = QHBoxLayout()
        url_row.setSpacing(0)
        self._lbl_url = QLabel("—")
        self._lbl_url.setObjectName("url")
        self._lbl_url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._lbl_url.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        url_row.addWidget(self._lbl_url, 1)
        self._btn_copy = QPushButton()
        self._btn_copy.setObjectName("sm_icon")
        self._btn_copy.setIcon(icons.icon("copy", 12, "#B0B3BC"))
        self._btn_copy.setText("Copy")
        url_row.addWidget(self._btn_copy)
        left.addLayout(url_row)

        cred_row = QHBoxLayout()
        cred_row.setSpacing(10)

        user_col = QVBoxLayout()
        ul = QLabel("Username")
        ul.setObjectName("h3")
        user_col.addWidget(ul)
        self._lbl_conn_user = QLabel()
        self._lbl_conn_user.setObjectName("mono")
        user_col.addWidget(self._lbl_conn_user)
        cred_row.addLayout(user_col)

        pass_col = QVBoxLayout()
        pl = QLabel("Password")
        pl.setObjectName("h3")
        pass_col.addWidget(pl)
        pass_inner = QHBoxLayout()
        pass_inner.setSpacing(0)
        self._lbl_conn_pass = QLabel("•••••••••••••••")
        self._lbl_conn_pass.setObjectName("mono")
        pass_inner.addWidget(self._lbl_conn_pass)
        self._btn_show_pass = QPushButton()
        self._btn_show_pass.setObjectName("sm_icon")
        self._btn_show_pass.setIcon(icons.icon("eye", 12, "#B0B3BC"))
        self._btn_show_pass.setCheckable(True)
        pass_inner.addWidget(self._btn_show_pass)
        pass_col.addLayout(pass_inner)
        cred_row.addLayout(pass_col)

        cred_row.addStretch()
        left.addLayout(cred_row)
        left.addStretch()
        bl.addLayout(left, 1)

        # Right column: QR code
        right = QVBoxLayout()
        right.setSpacing(6)
        right.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self._lbl_qr = QLabel()
        self._lbl_qr.setAlignment(Qt.AlignCenter)
        self._lbl_qr.setFixedSize(140, 140)
        self._lbl_qr.setStyleSheet(
            "background: #FFFFFF; border-radius: 6px; border: 1px solid #2A2D38;"
        )
        right.addWidget(self._lbl_qr)
        scan_lbl = QLabel("Scan with phone")
        scan_lbl.setObjectName("caption")
        scan_lbl.setAlignment(Qt.AlignCenter)
        right.addWidget(scan_lbl)
        bl.addLayout(right)

        vbox.addWidget(body)

        # How to connect
        how_section = QWidget()
        hs_lay = QVBoxLayout(how_section)
        hs_lay.setContentsMargins(14, 0, 14, 14)
        hs_lay.setSpacing(10)

        how_lbl = QLabel("HOW TO CONNECT")
        how_lbl.setObjectName("caption")
        how_lbl.setStyleSheet("letter-spacing: 0.08em; font-size: 11px;")
        hs_lay.addWidget(how_lbl)

        platform_row = QHBoxLayout()
        platform_row.setSpacing(10)

        platforms = [
            ("win", "Windows",
             "Open File Explorer → right-click This PC → Map network drive… → paste the URL above."),
            ("apple", "macOS",
             "In Finder, press ⌘K and enter the URL. macOS will prompt for the credentials."),
            ("android", "Android",
             "Use a WebDAV client such as Solid Explorer. Scan the QR code, accept the cert, and you're in."),
        ]
        for icon_name, name, body_text in platforms:
            platform_row.addWidget(self._platform_card(icon_name, name, body_text))

        hs_lay.addLayout(platform_row)
        vbox.addWidget(how_section)

        # Sep
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        vbox.addWidget(sep)

        # Footer
        foot = QFrame()
        foot.setObjectName("card_foot")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(14, 10, 14, 10)
        fl.setSpacing(14)

        dot = QLabel("●")
        dot.setStyleSheet("font-size: 7px; color: #10B981;")
        fl.addWidget(dot)
        self._lbl_clients = QLabel("Server running")
        self._lbl_clients.setStyleSheet("font-size: 12px;")
        fl.addWidget(self._lbl_clients)

        fl.addStretch()

        btn_log = QPushButton("Show access log")
        btn_log.setObjectName("ghost")
        btn_log.clicked.connect(self._show_access_log)
        fl.addWidget(btn_log)

        self._btn_stop = QPushButton("Stop Server")
        self._btn_stop.setObjectName("danger")
        fl.addWidget(self._btn_stop)

        vbox.addWidget(foot)
        return card

    def _platform_card(self, icon_name: str, name: str, body: str) -> QFrame:
        card = QFrame()
        card.setObjectName("platform_card")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(11, 11, 11, 11)
        cl.setSpacing(10)

        # Icon box
        icon_box = QFrame()
        icon_box.setObjectName("icon_box")
        icon_box.setFixedSize(28, 28)
        ibl = QVBoxLayout(icon_box)
        ibl.setContentsMargins(7, 7, 7, 7)
        ico = QLabel()
        if icon_name in ("win", "apple", "android"):
            # Use text glyphs for OS icons
            glyph = {"win": "⊞", "apple": "", "android": "🤖"}.get(icon_name, "?")
            ico.setText(glyph)
            ico.setStyleSheet("font-size: 12px; color: #B0B3BC;")
        else:
            ico.setPixmap(icons.pixmap(icon_name, 14, "#B0B3BC"))
        ibl.addWidget(ico)
        cl.addWidget(icon_box)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-weight: 600; font-size: 12.5px;")
        text_col.addWidget(name_lbl)
        body_lbl = QLabel(body)
        body_lbl.setObjectName("caption")
        body_lbl.setWordWrap(True)
        text_col.addWidget(body_lbl)
        cl.addLayout(text_col, 1)

        return card

    # ── Info row ──────────────────────────────────────────────────────────────

    def _build_info_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        # Why read-only card
        card1 = QFrame()
        card1.setObjectName("card")
        c1l = QHBoxLayout(card1)
        c1l.setContentsMargins(12, 12, 12, 12)
        c1l.setSpacing(10)
        ico1 = QLabel()
        ico1.setPixmap(icons.pixmap("shield", 16, "#7C3AED"))
        c1l.addWidget(ico1)
        txt1 = QVBoxLayout()
        txt1.setSpacing(2)
        t1h = QLabel("Why share read-only?")
        t1h.setStyleSheet("font-weight: 600; font-size: 12px;")
        txt1.addWidget(t1h)
        t1b = QLabel("Prevents remote clients from writing back ransomware or altering the drive.")
        t1b.setObjectName("caption")
        t1b.setWordWrap(True)
        txt1.addWidget(t1b)
        c1l.addLayout(txt1, 1)
        row.addWidget(card1, 1)

        # TLS fingerprint card
        card2 = QFrame()
        card2.setObjectName("card")
        c2l = QHBoxLayout(card2)
        c2l.setContentsMargins(12, 12, 12, 12)
        c2l.setSpacing(10)
        ico2 = QLabel()
        ico2.setPixmap(icons.pixmap("lock", 16, "#3B82F6"))
        c2l.addWidget(ico2)
        txt2 = QVBoxLayout()
        txt2.setSpacing(2)
        t2h = QLabel("TLS fingerprint")
        t2h.setStyleSheet("font-weight: 600; font-size: 12px;")
        txt2.addWidget(t2h)
        self._lbl_fingerprint = QLabel("SHA-256 · —")
        self._lbl_fingerprint.setObjectName("caption")
        self._lbl_fingerprint.setWordWrap(True)
        txt2.addWidget(self._lbl_fingerprint)
        c2l.addLayout(txt2, 1)
        row.addWidget(card2, 1)

        self._load_fingerprint()
        return row

    # ── Drive selection ───────────────────────────────────────────────────────

    def set_drive(self, drive: DriveInfo | None) -> None:
        self._current_drive = drive
        if drive and not self._server.is_running():
            self._btn_start.setEnabled(True)
        elif not drive:
            self._btn_start.setEnabled(False)

    # ── Server lifecycle ──────────────────────────────────────────────────────

    def _start_server(self) -> None:
        if not self._current_drive:
            return

        password = self._input_pass.text().strip()
        if not password:
            self._generate_password()
            password = self._input_pass.text()

        host = self._combo_host.currentText()
        port = self._spin_port.value()
        username = self._input_user.text().strip() or "warden"
        use_ssl = self._toggle_https.isChecked()
        read_only = "Read-only" in self._combo_mode.currentText()

        self._worker = ServerWorker(
            server=self._server,
            audit=self._audit,
            root_path=Path(self._current_drive.path),
            host=host,
            port=port,
            username=username,
            password=password,
            use_ssl=use_ssl,
        )
        self._worker.started.connect(self._on_server_started)
        self._worker.error.connect(self._on_server_error)
        self._worker.start()

        self._btn_start.setEnabled(False)
        self._btn_start.setText("Starting…")

    def _stop_server(self) -> None:
        if self._worker:
            self._worker.stop_server()
        self._card_connected.setVisible(False)
        self._card_config.setVisible(True)
        self._btn_start.setText("Start Server")
        self._btn_start.setEnabled(self._current_drive is not None)

    def _on_server_started(self, url: str) -> None:
        self._server_url = url
        self._card_config.setVisible(False)
        self._card_connected.setVisible(True)

        drive = self._current_drive
        mode = "read-only" if "Read-only" in self._combo_mode.currentText() else "read-write"
        label = drive.display_name() if drive else "drive"
        self._lbl_sharing.setText(f"Sharing <b>{label}</b> {mode}")

        self._lbl_url.setText(url)
        user = self._input_user.text().strip() or "warden"
        self._lbl_conn_user.setText(user)
        self._lbl_conn_pass.setText("•••••••••••••••")
        self._btn_show_pass.setChecked(False)
        self._btn_show_pass.setIcon(icons.icon("eye", 12, "#B0B3BC"))

        self._load_fingerprint()
        self._try_generate_qr(url)

    def _on_server_error(self, msg: str) -> None:
        self._btn_start.setEnabled(True)
        self._btn_start.setText("Start Server")
        QMessageBox.critical(self, "Server Error", msg)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _generate_password(self) -> None:
        alphabet = string.ascii_letters + string.digits
        pwd = "".join(secrets.choice(alphabet) for _ in range(16))
        self._input_pass.setText(pwd)

    def _copy_url(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._lbl_url.text())

    def _toggle_password_visibility(self) -> None:
        visible = self._btn_show_pass.isChecked()
        if visible:
            self._lbl_conn_pass.setText(self._input_pass.text())
            self._btn_show_pass.setIcon(icons.icon("eye_off", 12, "#B0B3BC"))
        else:
            self._lbl_conn_pass.setText("•••••••••••••••")
            self._btn_show_pass.setIcon(icons.icon("eye", 12, "#B0B3BC"))

    def _show_access_log(self) -> None:
        from PySide6.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("Access Log")
        dlg.resize(600, 400)
        lay = QVBoxLayout(dlg)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(self._audit.recent_text() if hasattr(self._audit, "recent_text") else "No log available.")
        lay.addWidget(txt)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        bb.rejected.connect(dlg.reject)
        lay.addWidget(bb)
        dlg.exec()

    def _try_generate_qr(self, url: str) -> None:
        try:
            import io
            import qrcode
            from PySide6.QtGui import QImage, QPixmap

            qr = qrcode.make(url)
            buf = io.BytesIO()
            qr.save(buf, format="PNG")
            buf.seek(0)
            img = QImage.fromData(buf.read())
            pix = QPixmap.fromImage(img).scaled(
                130, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self._lbl_qr.setPixmap(pix)
        except ImportError:
            self._lbl_qr.setText("Install qrcode\nfor QR code")
            self._lbl_qr.setStyleSheet(
                "background: #1C1E26; border-radius: 6px; color: #6B6E7A; font-size: 11px;"
            )

    def _load_fingerprint(self) -> None:
        try:
            import hashlib
            import ssl as _ssl
            cert_path = self._server._cert_path if hasattr(self._server, "_cert_path") else None
            if cert_path and Path(cert_path).exists():
                der = _ssl.PEM_cert_to_DER_cert(Path(cert_path).read_text())
                fp = hashlib.sha256(der).hexdigest().upper()
                pairs = ":".join(fp[i:i+2] for i in range(0, 16, 2))
                self._lbl_fingerprint.setText(f"SHA-256 · {pairs}…")
            else:
                self._lbl_fingerprint.setText("SHA-256 · start server to generate cert")
        except Exception:
            self._lbl_fingerprint.setText("SHA-256 · —")
