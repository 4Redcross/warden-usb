from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class DriveType(Enum):
    USB = "usb"
    INTERNAL = "internal"
    NETWORK = "network"
    UNKNOWN = "unknown"


class ThreatLevel(Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    UNKNOWN = "unknown"


@dataclass
class DriveInfo:
    path: str
    label: str
    filesystem: str
    total_bytes: int
    free_bytes: int
    drive_type: DriveType
    device_id: str = ""

    def size_str(self) -> str:
        gb = self.total_bytes / (1024 ** 3)
        return f"{gb:.1f} GB"

    def free_str(self) -> str:
        gb = self.free_bytes / (1024 ** 3)
        return f"{gb:.1f} GB"

    def display_name(self) -> str:
        return f"{self.label} ({self.path})"


@dataclass
class ThreatInfo:
    file_path: Path
    threat_name: str
    detected_by: str
    threat_level: ThreatLevel
    sha256: str = ""
    vt_result: Optional[dict] = None


@dataclass
class ScanResult:
    drive_path: str
    started_at: datetime
    completed_at: Optional[datetime]
    files_scanned: int
    threats: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return len(self.threats) == 0

    @property
    def threat_count(self) -> int:
        return len(self.threats)

    def duration_str(self) -> str:
        if not self.completed_at:
            return "—"
        delta = self.completed_at - self.started_at
        secs = int(delta.total_seconds())
        if secs < 60:
            return f"{secs}s"
        return f"{secs // 60}m {secs % 60}s"


@dataclass
class QuarantineEntry:
    id: str
    original_path: Path
    quarantine_path: Path
    threat_name: str
    detected_by: str
    sha256: str
    quarantined_at: datetime
    threat_level: ThreatLevel
    vt_hash_result: Optional[dict] = None
    vt_full_result: Optional[dict] = None


@dataclass
class FormatJob:
    drive: DriveInfo
    filesystem: str
    label: str
    quick_format: bool
    confirmed: bool = False
