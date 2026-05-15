import json
import os
import shutil
import stat
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.models import QuarantineEntry, ThreatLevel


class QuarantineManager:
    def __init__(self, quarantine_dir: Path):
        self.quarantine_dir = quarantine_dir
        self._meta = quarantine_dir / "metadata.jsonl"
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self._lock_dir(self.quarantine_dir)

    def _lock_dir(self, path: Path) -> None:
        try:
            mode = os.stat(path).st_mode
            os.chmod(path, mode & ~(stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
        except OSError:
            pass

    # ------------------------------------------------------------------ #
    # Quarantine a file
    # ------------------------------------------------------------------ #

    def quarantine(
        self,
        source: Path,
        threat_name: str,
        detected_by: str,
        sha256: str,
        threat_level: ThreatLevel,
    ) -> QuarantineEntry:
        entry_id = str(uuid.uuid4())
        dest = self.quarantine_dir / f"{entry_id}_{source.name}"

        shutil.move(str(source), str(dest))
        try:
            os.chmod(dest, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

        entry = QuarantineEntry(
            id=entry_id,
            original_path=source,
            quarantine_path=dest,
            threat_name=threat_name,
            detected_by=detected_by,
            sha256=sha256,
            quarantined_at=datetime.now(timezone.utc),
            threat_level=threat_level,
        )
        self._append_meta(entry)
        return entry

    # ------------------------------------------------------------------ #
    # List
    # ------------------------------------------------------------------ #

    def get_entry(self, entry_id: str) -> Optional[QuarantineEntry]:
        return next((e for e in self.list_entries() if e.id == entry_id), None)

    def list_entries(self) -> list[QuarantineEntry]:
        if not self._meta.exists():
            return []
        entries = []
        with open(self._meta, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    entry = QuarantineEntry(
                        id=r["id"],
                        original_path=Path(r["original_path"]),
                        quarantine_path=Path(r["quarantine_path"]),
                        threat_name=r["threat_name"],
                        detected_by=r["detected_by"],
                        sha256=r["sha256"],
                        quarantined_at=datetime.fromisoformat(r["quarantined_at"]),
                        threat_level=ThreatLevel(r["threat_level"]),
                        vt_hash_result=r.get("vt_hash_result"),
                        vt_full_result=r.get("vt_full_result"),
                    )
                    if entry.quarantine_path.exists():
                        entries.append(entry)
                except (KeyError, ValueError):
                    continue
        return entries

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def restore(self, entry: QuarantineEntry, dest_dir: Path) -> Path:
        dest = dest_dir / entry.original_path.name
        shutil.move(str(entry.quarantine_path), str(dest))
        self._remove_meta(entry.id)
        return dest

    def delete(self, entry: QuarantineEntry) -> None:
        try:
            entry.quarantine_path.unlink(missing_ok=True)
        except OSError:
            pass
        self._remove_meta(entry.id)

    def update_vt_results(
        self,
        entry_id: str,
        hash_result: Optional[dict] = None,
        full_result: Optional[dict] = None,
    ) -> None:
        if not self._meta.exists():
            return
        lines = []
        with open(self._meta, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    if rec.get("id") == entry_id:
                        if hash_result is not None:
                            rec["vt_hash_result"] = hash_result
                        if full_result is not None:
                            rec["vt_full_result"] = full_result
                        lines.append(json.dumps(rec) + "\n")
                    else:
                        lines.append(line)
                except json.JSONDecodeError:
                    lines.append(line)
        with open(self._meta, "w", encoding="utf-8") as f:
            f.writelines(lines)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _append_meta(self, entry: QuarantineEntry) -> None:
        record = {
            "id": entry.id,
            "original_path": str(entry.original_path),
            "quarantine_path": str(entry.quarantine_path),
            "threat_name": entry.threat_name,
            "detected_by": entry.detected_by,
            "sha256": entry.sha256,
            "quarantined_at": entry.quarantined_at.isoformat(),
            "threat_level": entry.threat_level.value,
        }
        with open(self._meta, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def _remove_meta(self, entry_id: str) -> None:
        if not self._meta.exists():
            return
        lines = []
        with open(self._meta, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    if json.loads(line.strip()).get("id") != entry_id:
                        lines.append(line)
                except json.JSONDecodeError:
                    lines.append(line)
        with open(self._meta, "w", encoding="utf-8") as f:
            f.writelines(lines)
