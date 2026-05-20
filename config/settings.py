import json
import os
from pathlib import Path
from typing import Any

try:
    import keyring
    _KEYRING = True
except ImportError:
    _KEYRING = False

_SERVICE = "warden-app"
_VT_KEY_NAME = "vt_api_key"


def _probe_keyring() -> bool:
    """Return True only when keyring has a real, working backend.

    On Linux `import keyring` succeeds even with no Secret Service provider
    running (headless servers, minimal installs) — the failure only surfaces
    when a backend operation actually runs. A harmless read of a non-existent
    entry exercises the backend without writing anything: it returns None on a
    working vault and raises on the fallback "fail" backend.
    """
    if not _KEYRING:
        return False
    try:
        keyring.get_password(_SERVICE, "__warden_probe__")
        return True
    except Exception:
        return False


# Probed once at import. Distinguishes "keyring importable" from
# "keyring actually usable" — the two differ on headless Linux.
_KEYRING_OK = _probe_keyring()


def _app_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "Warden"


def _defaults() -> dict:
    d = _app_data_dir()
    return {
        "theme": "dark",
        "scan": {
            "use_clamav": True,
            "use_yara": True,
            "use_vt_hash": False,
            "use_vt_upload": False,
            "auto_quarantine": True,
        },
        "server": {
            "port": 8443,
            "bind_localhost_only": False,
            "username": "warden",
        },
        "rules_last_updated": None,
        "quarantine_dir": str(d / "quarantine"),
        "audit_log": str(d / "audit.jsonl"),
    }


class Settings:
    def __init__(self):
        self._path = _app_data_dir() / "config.json"
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        defaults = _defaults()
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data = {**defaults, **saved}
                self._data["scan"] = {**defaults["scan"], **saved.get("scan", {})}
                self._data["server"] = {**defaults["server"], **saved.get("server", {})}
            except (json.JSONDecodeError, OSError):
                self._data = defaults
        else:
            self._data = defaults

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self._data
        for k in keys:
            if not isinstance(val, dict):
                return default
            val = val.get(k, default)
        return val

    def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        self.save()

    def get_vt_api_key(self) -> str:
        if _KEYRING_OK:
            try:
                key = keyring.get_password(_SERVICE, _VT_KEY_NAME)
                if key:
                    return key
            except Exception:
                pass  # backend became unavailable — fall through to plaintext
        return self._data.get("_vt_key", "")

    def set_vt_api_key(self, key: str) -> None:
        if _KEYRING_OK:
            try:
                keyring.set_password(_SERVICE, _VT_KEY_NAME, key)
                # Drop any stale plaintext copy so the key lives in one place.
                if self._data.pop("_vt_key", None) is not None:
                    self.save()
                return
            except Exception:
                pass  # write failed at runtime — fall back to plaintext
        self._data["_vt_key"] = key
        self.save()

    def delete_vt_api_key(self) -> None:
        if _KEYRING_OK:
            try:
                keyring.delete_password(_SERVICE, _VT_KEY_NAME)
            except Exception:
                pass  # not set / backend has no delete — nothing to do
        # Always clear the plaintext copy too, wherever the key happened to live.
        if self._data.pop("_vt_key", None) is not None:
            self.save()

    @property
    def keyring_available(self) -> bool:
        """True when the OS credential vault has a usable backend.

        Windows (Credential Manager) and macOS (Keychain) are always usable.
        On Linux this is False on headless / minimal systems with no Secret
        Service provider (GNOME Keyring / KWallet) running — in that case the
        key falls back to plaintext config and the UI warns the user.
        """
        return _KEYRING_OK

    @property
    def app_data_dir(self) -> Path:
        return _app_data_dir()

    @property
    def quarantine_dir(self) -> Path:
        return Path(self.get("quarantine_dir"))

    @property
    def audit_log_path(self) -> Path:
        return Path(self.get("audit_log"))

    @property
    def rules_dir(self) -> Path:
        return Path(__file__).parent.parent / "rules"

    @property
    def cert_dir(self) -> Path:
        return self.app_data_dir / "certs"

    @property
    def theme(self) -> str:
        return self.get("theme", "dark")

    @theme.setter
    def theme(self, value: str) -> None:
        self.set("theme", value)
