"""
Python API exposed to the JS frontend via window.pywebview.api.*

All public methods return JSON-serialisable values (dicts / lists / primitives).
Long-running operations start a background thread and push progress events
back to the JS side via window.__dispatch(event).
"""
from __future__ import annotations

import json
import secrets
import string
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from backends.base import DriveBackend
from core.audit import AuditLog
from core.fileserver import FileServer
from core.formatter import Formatter
from core.models import DriveInfo, FormatJob
from core.quarantine import QuarantineManager
from core.scanner import Scanner
from core.virustotal import VirusTotalClient
from core.yara_engine import YaraEngine
from workers.format_worker import FormatWorker
from workers.scan_worker import ScanWorker
from workers.server_worker import ServerWorker


class WardenApi:
    def __init__(
        self,
        scanner: Scanner,
        formatter: Formatter,
        file_server: FileServer,
        backend: DriveBackend,
        audit: AuditLog,
        yara_engine: YaraEngine,
        quarantine: QuarantineManager,
        vt_client: VirusTotalClient | None,
        settings,
    ):
        self._scanner = scanner
        self._formatter = formatter
        self._file_server = file_server
        self._backend = backend
        self._audit = audit
        self._yara = yara_engine
        self._quarantine = quarantine
        self._vt = vt_client
        self._settings = settings

        self._window = None
        self._scan_worker: ScanWorker | None = None
        self._server_worker: ServerWorker | None = None
        self._format_worker: FormatWorker | None = None
        self._drives: list[DriveInfo] = []

    # ── Window reference (set after webview.create_window) ────────────────────

    def set_window(self, window) -> None:
        self._window = window
        self._start_monitor()
        self._start_drive_refresh()

    # ── Event push ────────────────────────────────────────────────────────────

    def _push(self, event_type: str, data: Any = None) -> None:
        if not self._window:
            return
        payload = json.dumps({"type": event_type, "data": data if data is not None else {}})
        try:
            self._window.evaluate_js(f"window.__dispatch && window.__dispatch({payload})")
        except Exception:
            pass

    # ── Drive management ──────────────────────────────────────────────────────

    def list_drives(self) -> list[dict]:
        self._drives = self._backend.list_removable_drives()
        return [self._drive_dict(d) for d in self._drives]

    def _drive_dict(self, d: DriveInfo) -> dict:
        return {
            "path": d.path,
            "label": d.label,
            "filesystem": d.filesystem,
            "total_bytes": d.total_bytes,
            "free_bytes": d.free_bytes,
            "device_id": d.device_id,
            "display_name": d.display_name(),
            "size_str": d.size_str(),
            "free_str": d.free_str(),
        }

    def _start_drive_refresh(self) -> None:
        def _poll():
            import time
            while True:
                time.sleep(5)
                drives = self._backend.list_removable_drives()
                self._push("drives:changed", [self._drive_dict(d) for d in drives])
                self._drives = drives

        t = threading.Thread(target=_poll, daemon=True)
        t.start()

    # ── Hot-plug monitor ──────────────────────────────────────────────────────

    def _start_monitor(self) -> None:
        try:
            self._backend.start_monitoring(
                on_connect=lambda d: self._push("drive:connected", self._drive_dict(d)),
                on_disconnect=lambda p: self._push("drive:disconnected", {"path": p}),
            )
        except Exception:
            pass

    # ── Scanning ──────────────────────────────────────────────────────────────

    def start_scan(self, drive_path: str, options: dict) -> dict:
        drive = self._find_drive(drive_path)
        if not drive:
            return {"ok": False, "error": "Drive not found"}
        if self._scan_worker and self._scan_worker.is_alive():
            return {"ok": False, "error": "Scan already running"}

        self._scan_worker = ScanWorker(
            scanner=self._scanner,
            drive=drive,
            on_progress=self._on_scan_progress,
            on_result=self._on_scan_result,
            on_error=self._on_scan_error,
        )
        self._scan_worker.start()
        return {"ok": True}

    def cancel_scan(self) -> None:
        if self._scan_worker:
            self._scan_worker.cancel()

    def _on_scan_progress(self, pct: int, file_path: str) -> None:
        self._push("scan:progress", {"pct": pct, "file": file_path})

    def _on_scan_result(self, result) -> None:
        threats = []
        for t in result.threats:
            threats.append({
                "file": Path(t.file_path).name,
                "path": str(t.file_path),
                "threat": t.threat_name,
                "engine": t.detected_by,
                "sev": self._threat_sev(t.threat_level.value),
                "sha256": t.sha256,
            })
        self._push("scan:complete", {
            "files_scanned": result.files_scanned,
            "threat_count": result.threat_count,
            "threats": threats,
            "duration": result.duration_str(),
            "timestamp": datetime.now().strftime("%b %d, %H:%M"),
        })

    def _on_scan_error(self, msg: str) -> None:
        self._push("scan:error", {"message": msg})

    def _threat_sev(self, level: str) -> str:
        return {"malicious": "crit", "suspicious": "high", "unknown": "med", "clean": "low"}.get(level, "med")

    # ── Quarantine actions ────────────────────────────────────────────────────

    def get_quarantine(self) -> list[dict]:
        entries = self._quarantine.list_entries()
        return [self._quarantine_dict(e) for e in entries]

    def quarantine_file(
        self, file_path: str, threat_name: str, engine: str, sha256: str = ""
    ) -> dict:
        try:
            from core.models import ThreatLevel
            from core.virustotal import sha256_of_file
            src = Path(file_path)
            if not sha256:
                try:
                    sha256 = sha256_of_file(src)
                except OSError:
                    sha256 = ""
            self._quarantine.quarantine(
                src,
                threat_name,
                engine,
                sha256,
                ThreatLevel.MALICIOUS,
            )
            self._audit.log_quarantine(file_path, sha256, threat_name)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def quarantine_all(self, threats: list[dict]) -> dict:
        ok, failed = 0, 0
        for t in threats:
            r = self.quarantine_file(
                t["path"], t["threat"], t["engine"], t.get("sha256", "")
            )
            if r.get("ok"):
                ok += 1
            else:
                failed += 1
        return {"ok": True, "quarantined": ok, "failed": failed}

    def restore_quarantine(self, entry_id: str) -> dict:
        try:
            entry = self._quarantine.get_entry(entry_id)
            if not entry:
                return {"ok": False, "error": "Entry not found"}
            dest_dir = entry.original_path.parent
            if not dest_dir.exists():
                dest_dir = Path.home() / "Downloads"
                dest_dir.mkdir(parents=True, exist_ok=True)
            restored = self._quarantine.restore(entry, dest_dir)
            return {"ok": True, "path": str(restored)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def delete_quarantine(self, entry_id: str) -> dict:
        try:
            entry = self._quarantine.get_entry(entry_id)
            if not entry:
                return {"ok": False, "error": "Entry not found"}
            self._quarantine.delete(entry)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def vt_hash_check(self, entry_id: str) -> dict:
        if not self._vt:
            return {"ok": False, "error": "No VirusTotal API key configured"}
        try:
            entry = self._quarantine.get_entry(entry_id)
            if not entry:
                return {"ok": False, "error": "Entry not found"}
            result = self._vt.hash_lookup(entry.sha256)
            self._quarantine.update_vt_results(entry_id, hash_result=result)
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def vt_upload(self, entry_id: str) -> dict:
        if not self._vt:
            return {"ok": False, "error": "No VirusTotal API key configured"}
        try:
            entry = self._quarantine.get_entry(entry_id)
            if not entry:
                return {"ok": False, "error": "Entry not found"}
            result = self._vt.upload_file(entry.quarantine_path)
            self._quarantine.update_vt_results(entry_id, full_result=result)
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _quarantine_dict(self, e) -> dict:
        return {
            "id": e.id,
            "file": e.original_path.name,
            "path": str(e.original_path),
            "threat": e.threat_name,
            "engine": e.detected_by,
            "size": self._file_size(e.quarantine_path),
            "when": self._relative_time(e.quarantined_at),
            "sev": self._threat_sev(e.threat_level.value),
            "sha256": e.sha256,
        }

    # ── Firewall helpers (Windows only) ───────────────────────────────────────

    _FW_RULE      = "Warden WebDAV"
    _FW_RULE_CA   = "Warden CA Download"

    def _fw_open(self, port: int, rule_name: str | None = None) -> None:
        if sys.platform != "win32":
            return
        subprocess.run(
            [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={rule_name or self._FW_RULE}",
                "dir=in", "action=allow", "protocol=TCP",
                f"localport={port}",
            ],
            capture_output=True,
        )

    def _fw_close(self) -> None:
        if sys.platform != "win32":
            return
        for rule in (self._FW_RULE, self._FW_RULE_CA):
            subprocess.run(
                [
                    "netsh", "advfirewall", "firewall", "delete", "rule",
                    f"name={rule}",
                ],
                capture_output=True,
            )

    # ── WebDAV server ─────────────────────────────────────────────────────────

    def start_server(self, config: dict) -> dict:
        if self._server_worker and self._server_worker.is_alive():
            return {"ok": False, "error": "Server already running"}

        drive = self._find_drive(config.get("drive_path", ""))
        if not drive:
            return {"ok": False, "error": "No drive selected"}

        password = config.get("password") or self._gen_password()
        port = int(config.get("port", 8443))
        self._server_worker = ServerWorker(
            server=self._file_server,
            audit=self._audit,
            root_path=Path(drive.path),
            host=config.get("host", "0.0.0.0"),
            port=port,
            username=config.get("username", "warden"),
            password=password,
            use_ssl=config.get("use_ssl", True),
            on_started=lambda url: self._push("server:started", {
                "url": url,
                "password": password,
                "ca_url": self._file_server.ca_url,
                "mdns_active": self._file_server.mdns_active,
            }),
            on_error=lambda msg: self._push("server:error", {"message": msg}),
        )
        self._fw_open(port,       self._FW_RULE)
        self._fw_open(port + 1,   self._FW_RULE_CA)
        self._server_worker.start()
        return {"ok": True}

    def get_access_log(self) -> list:
        return self._file_server.get_access_log()

    def stop_server(self) -> dict:
        if self._server_worker:
            self._server_worker.stop_server()
            self._server_worker = None
        self._fw_close()
        self._push("server:stopped", {})
        return {"ok": True}

    # ── CA / TLS info ──────────────────────────────────────────────────────────

    def get_tls_info(self) -> dict:
        try:
            import hashlib
            import ssl as _ssl
            from cryptography import x509 as _x509

            cert_path = self._settings.cert_dir / "server.crt"
            if not cert_path.exists():
                return {"fingerprint": "—", "expires": "No cert yet", "local_ip": self._local_ip()}

            pem = cert_path.read_text()
            der = _ssl.PEM_cert_to_DER_cert(pem)
            fp_hex = hashlib.sha256(der).hexdigest().upper()
            fingerprint = ":".join(fp_hex[i:i+2] for i in range(0, len(fp_hex), 2))

            cert = _x509.load_pem_x509_certificate(pem.encode())
            expires = cert.not_valid_after_utc.strftime("%Y-%m-%d")

            return {
                "fingerprint": fingerprint,
                "expires": expires,
                "local_ip": self._local_ip(),
                "mdns_host": "warden.local" if self._file_server.mdns_active else "",
            }
        except Exception as e:
            return {"fingerprint": "—", "expires": "—", "local_ip": self._local_ip(), "mdns_host": "", "error": str(e)}

    def _local_ip(self) -> str:
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "—"

    # ── Formatting ────────────────────────────────────────────────────────────

    def start_format(self, config: dict) -> dict:
        drive = self._find_drive(config.get("drive_path", ""))
        if not drive:
            return {"ok": False, "error": "No drive selected"}

        job = FormatJob(
            drive=drive,
            filesystem=config.get("filesystem", "exFAT"),
            label=config.get("label", drive.label or "USB Drive"),
            quick_format=config.get("quick_format", True),
            confirmed=True,
        )
        self._format_worker = FormatWorker(
            formatter=self._formatter,
            job=job,
            on_status=lambda s: self._push("format:status", {"message": s}),
            on_finished=lambda: self._push("format:complete", {}),
            on_error=lambda msg: self._push("format:error", {"message": msg}),
        )
        self._format_worker.start()
        return {"ok": True}

    # ── YARA rules ────────────────────────────────────────────────────────────

    def update_rules(self) -> dict:
        def _run():
            ok = self._yara.download_rules(
                progress_cb=lambda p: self._push("rules:progress", {"pct": p})
            )
            if ok:
                self._settings.set("rules_last_updated", datetime.now().isoformat())
            self._push("rules:done", {"ok": ok})

        threading.Thread(target=_run, daemon=True).start()
        return {"ok": True}

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_settings(self) -> dict:
        from core.formatter import FILESYSTEMS_WINDOWS, FILESYSTEMS_LINUX
        filesystems = FILESYSTEMS_LINUX if sys.platform != "win32" else FILESYSTEMS_WINDOWS
        return {
            "theme": self._settings.theme,
            "use_clamav": self._settings.get("scan.use_clamav", True),
            "use_yara": self._settings.get("scan.use_yara", True),
            "use_vt_hash": self._settings.get("scan.use_vt_hash", False),
            "has_vt_key": bool(self._settings.get_vt_api_key()),
            "has_yara_rules": self._yara.has_rules(),
            "keyring_available": self._settings.keyring_available,
            "rules_last_updated": self._settings.get("rules_last_updated"),
            "server_available": self._file_server.is_available(),
            "platform": sys.platform,
            "filesystems": filesystems,
        }

    def set_theme(self, theme: str) -> None:
        self._settings.theme = theme

    # ── VirusTotal API key ────────────────────────────────────────────────────

    def set_vt_key(self, key: str) -> dict:
        """Verify a VirusTotal API key, then persist it to the OS credential
        vault and inject a fresh client at runtime. The key is never logged."""
        key = (key or "").strip()
        if not key:
            return {"ok": False, "error": "API key is empty"}
        client = VirusTotalClient(key)
        check = client.verify()
        if not check.get("ok"):
            return {"ok": False, "error": check.get("error", "Verification failed")}
        self._settings.set_vt_api_key(key)
        self._vt = client
        self._scanner.vt_client = client
        return {"ok": True}

    def clear_vt_key(self) -> dict:
        try:
            self._settings.delete_vt_api_key()
        except Exception as e:
            return {"ok": False, "error": str(e)}
        self._vt = None
        self._scanner.vt_client = None
        return {"ok": True}

    def get_audit_log(self) -> str:
        try:
            entries = self._audit.read_all()
        except Exception:
            return ""
        lines = []
        for e in entries[-200:]:
            ts = str(e.get("ts", "")).replace("T", " ")
            ts = ts.split(".")[0].split("+")[0]
            event = str(e.get("event", "")).upper()
            fields = " ".join(
                f"{k}={v}" for k, v in e.items() if k not in ("ts", "event")
            )
            lines.append(f"{ts}  {event:<10} {fields}".rstrip())
        lines.reverse()  # newest first
        return "\n".join(lines)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_drive(self, path: str) -> DriveInfo | None:
        for d in self._drives:
            if d.path == path:
                return d
        if path:
            self._drives = self._backend.list_removable_drives()
            for d in self._drives:
                if d.path == path:
                    return d
        return None

    def _gen_password(self) -> str:
        return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

    def _file_size(self, path: Path) -> str:
        try:
            b = path.stat().st_size
            for unit in ("B", "KB", "MB", "GB"):
                if b < 1024:
                    return f"{b:.0f} {unit}"
                b /= 1024
            return f"{b:.1f} GB"
        except Exception:
            return "—"

    def _relative_time(self, dt: datetime) -> str:
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        delta = now - dt
        s = int(delta.total_seconds())
        if s < 60:
            return f"{s}s ago"
        if s < 3600:
            return f"{s // 60}m ago"
        if s < 86400:
            return f"{s // 3600}h ago"
        return f"{s // 86400}d ago"
