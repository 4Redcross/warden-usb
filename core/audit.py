import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLog:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, event_type: str, data: dict[str, Any]) -> None:
        entry = {"ts": datetime.now(timezone.utc).isoformat(), "event": event_type, **data}
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_scan(self, drive_path: str, files_scanned: int, threat_count: int, engines: str) -> None:
        self._write("scan", {
            "drive": drive_path,
            "files_scanned": files_scanned,
            "threats": threat_count,
            "engines": engines,
        })

    def log_quarantine(self, original_path: str, sha256: str, threat_name: str) -> None:
        self._write("quarantine", {
            "original_path": original_path,
            "sha256": sha256,
            "threat": threat_name,
        })

    def log_format(self, drive_path: str, filesystem: str, label: str) -> None:
        self._write("format", {"drive": drive_path, "filesystem": filesystem, "label": label})

    def log_server(self, action: str, drive_path: str, port: int) -> None:
        self._write("server", {"action": action, "drive": drive_path, "port": port})

    def log_vt_upload(self, sha256: str, filename: str) -> None:
        self._write("vt_upload", {"sha256": sha256, "filename": filename})

    def read_all(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries
