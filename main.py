import sys
from pathlib import Path

import webview

from backends.base import DriveBackend
from config.settings import Settings
from core.audit import AuditLog
from core.fileserver import FileServer
from core.formatter import Formatter
from core.monitor import DriveMonitor
from core.quarantine import QuarantineManager
from core.scanner import Scanner
from core.virustotal import VirusTotalClient
from core.yara_engine import YaraEngine
from webapi import WardenApi


def _get_backend() -> DriveBackend:
    if sys.platform == "win32":
        from backends.windows import WindowsBackend
        return WindowsBackend()
    else:
        from backends.linux import LinuxBackend
        return LinuxBackend()


def _check_vendor() -> None:
    vendor = Path("web/vendor")
    if not (vendor / "react.production.min.js").exists():
        print("ERROR: vendor JS files missing. Run:  python setup_web.py")
        sys.exit(1)


def main() -> None:
    _check_vendor()

    settings  = Settings()
    audit     = AuditLog(settings.audit_log_path)
    yara      = YaraEngine(settings.rules_dir)
    quarantine = QuarantineManager(settings.quarantine_dir)

    vt_key    = settings.get_vt_api_key()
    vt_client = VirusTotalClient(vt_key) if vt_key else None

    scanner = Scanner(
        yara_engine=yara,
        quarantine=quarantine,
        audit=audit,
        vt_client=vt_client,
        use_clamav=settings.get("scan.use_clamav", True),
        use_yara=settings.get("scan.use_yara", True),
        use_vt_hash=settings.get("scan.use_vt_hash", False),
        auto_quarantine=settings.get("scan.auto_quarantine", True),
    )

    backend      = _get_backend()
    formatter    = Formatter(backend, audit)
    file_server  = FileServer(settings.cert_dir)
    drive_monitor = DriveMonitor(backend)

    warden_api = WardenApi(
        scanner=scanner,
        formatter=formatter,
        file_server=file_server,
        drive_monitor=drive_monitor,
        backend=backend,
        audit=audit,
        yara_engine=yara,
        quarantine=quarantine,
        vt_client=vt_client,
        settings=settings,
    )

    window = webview.create_window(
        title="Warden — USB Security",
        url=str(Path("web/index.html").resolve()),
        js_api=warden_api,
        width=1100,
        height=820,
        min_size=(920, 700),
        background_color="#0F1117",
    )

    def on_loaded():
        warden_api.set_window(window)

    webview.start(on_loaded, http_server=True, debug="--debug" in sys.argv)


if __name__ == "__main__":
    main()
