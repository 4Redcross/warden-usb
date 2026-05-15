import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from core.models import DriveInfo, ScanResult, ThreatInfo, ThreatLevel
from core.audit import AuditLog
from core.quarantine import QuarantineManager
from core.virustotal import VirusTotalClient, sha256_of_file
from core.yara_engine import YaraEngine

try:
    import clamd as _clamd
    _CLAMD = True
except ImportError:
    _CLAMD = False


class Scanner:
    def __init__(
        self,
        yara_engine: YaraEngine,
        quarantine: QuarantineManager,
        audit: AuditLog,
        vt_client: Optional[VirusTotalClient] = None,
        use_clamav: bool = True,
        use_yara: bool = True,
        use_vt_hash: bool = False,
        auto_quarantine: bool = True,
    ):
        self.yara_engine = yara_engine
        self.quarantine = quarantine
        self.audit = audit
        self.vt_client = vt_client
        self.use_clamav = use_clamav
        self.use_yara = use_yara
        self.use_vt_hash = use_vt_hash
        self.auto_quarantine = auto_quarantine
        self._clam = self._init_clam()

    def _init_clam(self) -> object:
        if not _CLAMD or not self.use_clamav:
            return None
        cd = None
        try:
            cd = (
                _clamd.ClamdUnixSocket()
                if os.name != "nt"
                else _clamd.ClamdNetworkSocket()
            )
            cd.ping()
            return cd
        except Exception:
            if cd is not None and hasattr(cd, "clamd_socket"):
                try:
                    cd.clamd_socket.close()
                except Exception:
                    pass
            return "subprocess"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def scan_drive(
        self,
        drive: DriveInfo,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> ScanResult:
        result = ScanResult(
            drive_path=drive.path,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            files_scanned=0,
        )

        if self.use_yara:
            self.yara_engine.load_rules()

        files: list[Path] = []
        for root, _, filenames in os.walk(drive.path):
            for fname in filenames:
                files.append(Path(root) / fname)

        total = len(files)
        for i, fp in enumerate(files):
            if cancel_check and cancel_check():
                break

            if progress_callback:
                progress_callback(int((i / max(total, 1)) * 100), str(fp))

            threats = self._scan_file(fp)
            for threat in threats:
                result.threats.append(threat)
                if self.auto_quarantine:
                    try:
                        self.quarantine.quarantine(
                            fp,
                            threat.threat_name,
                            threat.detected_by,
                            threat.sha256,
                            threat.threat_level,
                        )
                        self.audit.log_quarantine(str(fp), threat.sha256, threat.threat_name)
                    except Exception as e:
                        result.errors.append(f"Quarantine failed for {fp.name}: {e}")

            result.files_scanned += 1

        result.completed_at = datetime.now(timezone.utc)

        engines = []
        if self.use_clamav:
            engines.append("clamav")
        if self.use_yara:
            engines.append("yara")
        if self.use_vt_hash:
            engines.append("vt_hash")

        self.audit.log_scan(drive.path, result.files_scanned, result.threat_count, ",".join(engines))
        return result

    # ------------------------------------------------------------------ #
    # Per-file scanning
    # ------------------------------------------------------------------ #

    def _scan_file(self, fp: Path) -> list[ThreatInfo]:
        threats: list[ThreatInfo] = []
        sha256 = ""

        if self.use_clamav and self._clam:
            name = self._clam_scan(fp)
            if name:
                sha256 = sha256 or sha256_of_file(fp)
                threats.append(ThreatInfo(
                    file_path=fp,
                    threat_name=name,
                    detected_by="clamav",
                    threat_level=ThreatLevel.MALICIOUS,
                    sha256=sha256,
                ))

        if self.use_yara and self.yara_engine.is_available():
            for rule in self.yara_engine.scan_file(fp):
                sha256 = sha256 or sha256_of_file(fp)
                threats.append(ThreatInfo(
                    file_path=fp,
                    threat_name=rule,
                    detected_by="yara",
                    threat_level=ThreatLevel.SUSPICIOUS,
                    sha256=sha256,
                ))

        if self.use_vt_hash and not threats and self.vt_client and self.vt_client.is_configured():
            sha256 = sha256 or sha256_of_file(fp)
            vt = self.vt_client.hash_lookup(sha256)
            if vt and vt.get("found") and vt.get("malicious", 0) > 0:
                threats.append(ThreatInfo(
                    file_path=fp,
                    threat_name=vt.get("name", "Unknown"),
                    detected_by="virustotal",
                    threat_level=ThreatLevel.MALICIOUS,
                    sha256=sha256,
                    vt_result=vt,
                ))

        return threats

    def _clam_scan(self, fp: Path) -> Optional[str]:
        if self._clam == "subprocess":
            return self._clamscan_subprocess(fp)
        try:
            result = self._clam.scan(str(fp))
            status, name = result.get(str(fp), ("OK", None))
            return name if status == "FOUND" else None
        except Exception:
            return self._clamscan_subprocess(fp)

    def _clamscan_subprocess(self, fp: Path) -> Optional[str]:
        try:
            r = subprocess.run(
                ["clamscan", "--no-summary", str(fp)],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode == 1:
                for line in r.stdout.splitlines():
                    if "FOUND" in line:
                        return line.split(":")[-1].strip().replace(" FOUND", "")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None
