import hashlib
import time
from pathlib import Path
from typing import Optional

import requests

_BASE = "https://www.virustotal.com/api/v3"


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class VirusTotalClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({"x-apikey": api_key})

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def hash_lookup(self, sha256: str) -> Optional[dict]:
        """Query VT by SHA-256 hash — no file upload."""
        if not self.is_configured():
            return None
        try:
            resp = self._session.get(f"{_BASE}/files/{sha256}", timeout=15)
            if resp.status_code == 404:
                return {"found": False, "sha256": sha256}
            resp.raise_for_status()
            attrs = resp.json().get("data", {}).get("attributes", {})
            stats = attrs.get("last_analysis_stats", {})
            return {
                "found": True,
                "sha256": sha256,
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "undetected": stats.get("undetected", 0),
                "total": sum(stats.values()),
                "name": attrs.get("meaningful_name", ""),
            }
        except requests.RequestException:
            return None

    def verify(self) -> dict:
        """Check whether the API key is accepted by VirusTotal.

        Makes one lightweight authenticated request. Returns
        {"ok": bool, "error": str}. The key itself is never logged or returned.
        """
        if not self.is_configured():
            return {"ok": False, "error": "No API key provided"}
        # EICAR test-file SHA-256 — a well-known sample always present on VT.
        eicar = "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"
        try:
            resp = self._session.get(f"{_BASE}/files/{eicar}", timeout=15)
        except requests.RequestException as exc:
            return {"ok": False, "error": f"Could not reach VirusTotal: {exc}"}
        if resp.status_code in (200, 404, 429):
            # 200/404 = key works; 429 = rate-limited but key is valid.
            return {"ok": True, "error": ""}
        if resp.status_code in (401, 403):
            return {"ok": False, "error": "VirusTotal rejected the API key"}
        return {"ok": False, "error": f"Unexpected response from VirusTotal (HTTP {resp.status_code})"}

    def upload_file(self, file_path: Path) -> Optional[dict]:
        """Upload file to VT for full multi-engine analysis."""
        if not self.is_configured():
            return None
        try:
            with open(file_path, "rb") as f:
                resp = self._session.post(
                    f"{_BASE}/files",
                    files={"file": (file_path.name, f)},
                    timeout=120,
                )
            resp.raise_for_status()
            analysis_id = resp.json().get("data", {}).get("id")
            if not analysis_id:
                return None

            for _ in range(12):
                time.sleep(5)
                poll = self._session.get(f"{_BASE}/analyses/{analysis_id}", timeout=15)
                poll.raise_for_status()
                data = poll.json().get("data", {}).get("attributes", {})
                if data.get("status") == "completed":
                    stats = data.get("stats", {})
                    return {
                        "sha256": sha256_of_file(file_path),
                        "malicious": stats.get("malicious", 0),
                        "suspicious": stats.get("suspicious", 0),
                        "undetected": stats.get("undetected", 0),
                        "total": sum(stats.values()),
                        "analysis_id": analysis_id,
                    }
            return None
        except (requests.RequestException, OSError):
            return None
