import datetime
import logging
import queue
import secrets
import socket
import threading
from collections import deque
from pathlib import Path
from typing import Optional

try:
    from wsgidav.wsgidav_app import WsgiDAVApp
    from cheroot import wsgi as cheroot_wsgi
    from cheroot.ssl.builtin import BuiltinSSLAdapter
    import wsgidav.util as _wsgidav_util

    # FAT32 drives can have zero/invalid mtimes that crash wsgidav's RFC 1123
    # formatter on Windows. Patch it to return a safe fallback instead.
    _SAFE_SECS = 86400.0  # 1970-01-02 00:00:00 UTC — always valid on Windows

    _orig_rfc1123 = _wsgidav_util.get_rfc1123_time
    _orig_rfc3339 = _wsgidav_util.get_rfc3339_time

    def _safe_rfc1123(secs=None):
        try:
            return _orig_rfc1123(secs)
        except (OSError, ValueError, OverflowError):
            return _orig_rfc1123(_SAFE_SECS)

    def _safe_rfc3339(secs=None):
        try:
            return _orig_rfc3339(secs)
        except (OSError, ValueError, OverflowError):
            return _orig_rfc3339(_SAFE_SECS)

    _wsgidav_util.get_rfc1123_time = _safe_rfc1123
    _wsgidav_util.get_rfc3339_time = _safe_rfc3339

    _WSGIDAV = True
except ImportError:
    _WSGIDAV = False

try:
    from zeroconf import Zeroconf, ServiceInfo as _ZcServiceInfo
    _ZEROCONF = True
except ImportError:
    _ZEROCONF = False

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    _CRYPTO = True
except ImportError:
    _CRYPTO = False

_MDNS_HOST = "warden.local"


class _AccessLogHandler(logging.Handler):
    """Captures wsgidav request log lines into a fixed-size ring buffer."""
    def __init__(self, buf: deque):
        super().__init__()
        self._buf = buf

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        # wsgidav logs requests as "GET /path HTTP/1.1 → 200"
        if any(m in msg for m in ("GET ", "PUT ", "DELETE ", "PROPFIND", "OPTIONS", "HEAD ")):
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self._buf.append(f"{ts}  {msg}")


class FileServer:
    def __init__(self, cert_dir: Path):
        self.cert_dir = cert_dir
        self._server = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.token: str = ""
        self._access_log: deque = deque(maxlen=200)
        self._log_handler: Optional[_AccessLogHandler] = None
        self._ca_http_server = None
        self._ca_http_thread: Optional[threading.Thread] = None
        self.ca_url: str = ""
        self._zeroconf: Optional[object] = None
        self._zeroconf_info: Optional[object] = None
        self.mdns_active: bool = False
        self._fw_tcp_ports: list = []   # TCP ports we opened in the firewall

    def is_available(self) -> bool:
        return _WSGIDAV

    @property
    def ca_cert_path(self) -> Path:
        return self.cert_dir / "warden-ca.crt"

    def _ensure_ca(self) -> tuple[Path, Path]:
        """Generate the local CA key + cert once. CA=True so it can sign server certs."""
        if not _CRYPTO:
            raise RuntimeError("cryptography package required. Install: pip install cryptography")

        self.cert_dir.mkdir(parents=True, exist_ok=True)
        ca_key_path  = self.cert_dir / "warden-ca.key"
        ca_cert_path = self.cert_dir / "warden-ca.crt"

        if ca_key_path.exists() and ca_cert_path.exists():
            return ca_cert_path, ca_key_path

        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME,         "Warden Local CA"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME,   "Warden USB Security"),
        ])
        ca_cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.KeyUsage(
                digital_signature=True, key_cert_sign=True, crl_sign=True,
                content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False,
                encipher_only=False, decipher_only=False,
            ), critical=True)
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
                critical=False,
            )
            .sign(ca_key, hashes.SHA256())
        )
        ca_cert_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
        ca_key_path.write_bytes(ca_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
        return ca_cert_path, ca_key_path

    def _ensure_cert(self, cdp_url: str = "") -> tuple[str, str]:
        """Generate (or regenerate) a server cert signed by the local CA.

        *cdp_url* — if non-empty, a CRL Distribution Point URL is embedded so
        that WinHTTP / WebClient can fetch the revocation list and complete the
        TLS handshake without dropping the connection.
        """
        import ipaddress
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        if not _CRYPTO:
            raise RuntimeError("cryptography package required. Install: pip install cryptography")

        self.cert_dir.mkdir(parents=True, exist_ok=True)
        cert_path = self.cert_dir / "server.crt"
        key_path  = self.cert_dir / "server.key"

        ca_cert_path, ca_key_path = self._ensure_ca()
        ca_cert = x509.load_pem_x509_certificate(ca_cert_path.read_bytes())
        ca_key  = load_pem_private_key(ca_key_path.read_bytes(), password=None)

        # SANs — always include localhost + LAN IP
        san_ips = {ipaddress.IPv4Address("127.0.0.1")}
        try:
            lan = self._local_ip()
            if lan not in ("—", "localhost"):
                san_ips.add(ipaddress.IPv4Address(lan))
        except Exception:
            pass

        # Regenerate if cert is missing, LAN IP changed, or CDP URL changed
        if cert_path.exists() and key_path.exists():
            try:
                existing = x509.load_pem_x509_certificate(cert_path.read_bytes())
                san_ext  = existing.extensions.get_extension_for_class(x509.SubjectAlternativeName)
                existing_ips = {v.value for v in san_ext.value if isinstance(v, x509.IPAddress)}
                if san_ips == existing_ips:
                    # Also check that the embedded CDP matches what we want
                    try:
                        cdp_ext = existing.extensions.get_extension_for_class(
                            x509.CRLDistributionPoints
                        )
                        existing_cdp = next(iter(cdp_ext.value)).full_name[0].value
                    except Exception:
                        existing_cdp = ""
                    if existing_cdp == cdp_url:
                        return str(cert_path), str(key_path)
            except Exception:
                pass

        server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        san = x509.SubjectAlternativeName(
            [x509.DNSName("localhost"), x509.DNSName(_MDNS_HOST)]
            + [x509.IPAddress(ip) for ip in sorted(san_ips, key=str)]
        )
        builder = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "warden-server")]))
            .issuer_name(ca_cert.subject)
            .public_key(server_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            # 825-day limit (Apple / Chrome enforce this for TLS certs)
            .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=825))
            .add_extension(san, critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(
                digital_signature=True, key_encipherment=True,
                content_commitment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ), critical=True)
            .add_extension(
                x509.ExtendedKeyUsage([x509.ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
            # RFC 5280 — AKI links this cert to the CA key; SKI identifies our key.
            # Schannel uses both for chain building and path validation.
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()),
                critical=False,
            )
        )
        # Embed CRL Distribution Point so WinHTTP can verify revocation status
        if cdp_url:
            builder = builder.add_extension(
                x509.CRLDistributionPoints([
                    x509.DistributionPoint(
                        full_name=[x509.UniformResourceIdentifier(cdp_url)],
                        relative_name=None,
                        reasons=None,
                        crl_issuer=None,
                    )
                ]),
                critical=False,
            )
        server_cert = builder.sign(ca_key, hashes.SHA256())
        cert_path.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
        return str(cert_path), str(key_path)

    def _ensure_crl(self) -> Path:
        """Generate (or overwrite) an empty CRL signed by the local CA (DER format).

        WinHTTP fetches this when it checks revocation. An empty CRL is valid —
        it simply means no certificates have been revoked yet.
        """
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        crl_path = self.cert_dir / "warden-ca.crl"
        ca_cert_path, ca_key_path = self._ensure_ca()
        ca_cert = x509.load_pem_x509_certificate(ca_cert_path.read_bytes())
        ca_key  = load_pem_private_key(ca_key_path.read_bytes(), password=None)

        now = datetime.datetime.now(datetime.timezone.utc)
        crl = (
            x509.CertificateRevocationListBuilder()
            .issuer_name(ca_cert.subject)
            .last_update(now)
            .next_update(now + datetime.timedelta(days=3650))
            # RFC 5280 §5.2.1 — CRL issuers MUST include AKI so that Schannel
            # can match the CRL to the CA key that signed it.
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
                critical=False,
            )
            .sign(ca_key, hashes.SHA256())
        )
        crl_path.write_bytes(crl.public_bytes(serialization.Encoding.DER))
        return crl_path

    # ── Plain-HTTP CA cert download server ────────────────────────────────────

    def _start_ca_server(
        self,
        port: int,
        webdav_port: int = 8443,
        lan_ip: str = "",
        username: str = "warden",
    ) -> str:
        """Start a plain-HTTP server on *port*.

        Serves:
          /               — HTML setup guide with copy-able commands
          /warden-ca.crt  — CA certificate download
          /warden-ca.crl  — CRL download (for WinHTTP revocation check)

        Must stay plain HTTP so clients can reach it before they have installed
        the CA cert (bootstrapping trust requires an unencrypted channel).

        Returns the CA cert download URL (shown in the Warden UI).
        """
        import http.server

        cert_dir = self.cert_dir
        ca_path  = self.ca_cert_path

        # Map URL path → (file path, MIME type, download filename)
        _FILE_ROUTES = {
            "/warden-ca.crt": (ca_path,                        "application/x-pem-file", "warden-ca.crt"),
            "/warden-ca.crl": (cert_dir / "warden-ca.crl",    "application/pkix-crl",   "warden-ca.crl"),
        }

        _display_ip = lan_ip or self._local_ip()
        _webdav_url = f"https://{_MDNS_HOST}:{webdav_port}"
        _webdav_ip_url = f"https://{_display_ip}:{webdav_port}"
        _username = username

        _SETUP_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Warden — Device Setup</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#0f1117;color:#e8e9ed;font-family:system-ui,-apple-system,sans-serif;
       padding:36px 20px 48px;min-height:100vh}}
  .wrap{{max-width:640px;margin:0 auto}}
  h1{{font-size:22px;font-weight:700;color:#7c3aed;margin-bottom:4px}}
  .sub{{color:#6b7280;font-size:13px;margin-bottom:20px;line-height:1.5}}
  .ptabs{{display:flex;gap:0;margin-bottom:24px;border:1px solid #2a2d3e;
          border-radius:8px;overflow:hidden;background:#13151c}}
  .ptab{{flex:1;padding:9px 6px;font-size:13px;font-weight:500;color:#6b7280;
         background:none;border:none;cursor:pointer;transition:all .15s;
         display:flex;align-items:center;justify-content:center;gap:5px}}
  .ptab:not(:last-child){{border-right:1px solid #2a2d3e}}
  .ptab.active{{background:#1a1d2e;color:#e8e9ed;font-weight:600}}
  .ptab .os-icon{{font-size:14px;line-height:1}}
  .panel{{display:none}}
  .panel.active{{display:block}}
  .step{{background:#1a1d2e;border:1px solid #2a2d3e;border-radius:10px;
         padding:18px 20px;margin-bottom:12px}}
  .num{{color:#7c3aed;font-size:10px;font-weight:700;text-transform:uppercase;
        letter-spacing:.08em;margin-bottom:5px}}
  .title{{font-size:14.5px;font-weight:600;margin-bottom:7px}}
  .desc{{color:#9ca3af;font-size:12.5px;margin-bottom:11px;line-height:1.55}}
  .cmd{{background:#0a0c14;border:1px solid #2a2d3e;border-radius:6px;
        padding:9px 11px;display:flex;align-items:center;gap:10px;margin-bottom:5px}}
  .cmd code{{flex:1;font-family:'Cascadia Code',Consolas,monospace;font-size:12.5px;
             color:#a5b4fc;word-break:break-all;white-space:pre-wrap}}
  .copy{{background:#2a2d3e;border:none;color:#9ca3af;padding:4px 10px;
         border-radius:4px;cursor:pointer;font-size:12px;white-space:nowrap;
         flex-shrink:0;transition:all .15s}}
  .copy:hover{{background:#3a3d4e;color:#e8e9ed}}
  .copy.ok{{background:#14532d;color:#4ade80}}
  .dl{{display:inline-block;background:#7c3aed;color:#fff;padding:9px 20px;
       border-radius:7px;text-decoration:none;font-size:13.5px;font-weight:600;
       transition:background .15s}}
  .dl:hover{{background:#6d28d9}}
  .note{{color:#6b7280;font-size:12px;margin-top:7px;line-height:1.5}}
  .url{{color:#34d399;font-family:monospace}}
  .hl{{color:#e8e9ed;font-weight:600}}
  .badge{{display:inline-block;background:rgba(52,211,153,.12);color:#34d399;
          border:1px solid rgba(52,211,153,.3);border-radius:4px;
          font-size:11px;padding:1px 7px;margin-left:6px;vertical-align:middle}}
  .warn{{background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.25);
         border-radius:6px;padding:8px 12px;font-size:12px;color:#d97706;margin-top:8px}}
</style>
</head>
<body>
<div class="wrap">
  <h1>Warden <span class="badge">Device Setup</span></h1>
  <p class="sub">One-time setup to access the encrypted file share from this device.</p>

  <div class="ptabs">
    <button class="ptab active" onclick="show('win',this)">
      <span class="os-icon">&#x1FA9F;</span> Windows
    </button>
    <button class="ptab" onclick="show('mac',this)">
      <span class="os-icon">&#xF8FF;</span> macOS
    </button>
    <button class="ptab" onclick="show('ios',this)">
      <span class="os-icon">&#x1F4F1;</span> iPhone/iPad
    </button>
    <button class="ptab" onclick="show('and',this)">
      <span class="os-icon">&#x1F916;</span> Android
    </button>
    <button class="ptab" onclick="show('lnx',this)">
      <span class="os-icon">&#x1F427;</span> Linux
    </button>
  </div>

  <!-- Windows -->
  <div id="win" class="panel active">
    <div class="step">
      <div class="num">Step 1 — Windows</div>
      <div class="title">Download the CA certificate</div>
      <div class="desc">Lets Windows verify the Warden server's identity.</div>
      <a class="dl" href="/warden-ca.crt" download>&#8659;&nbsp; Download warden-ca.crt</a>
    </div>
    <div class="step">
      <div class="num">Step 2 — Windows</div>
      <div class="title">Install into the <span class="hl">Local Machine</span> trust store</div>
      <div class="desc">Open an <span class="hl">admin Command Prompt</span> (not PowerShell) and run:</div>
      <div class="cmd">
        <code id="w2">certutil -addstore Root "%USERPROFILE%\\Downloads\\warden-ca.crt"</code>
        <button class="copy" onclick="cp('w2',this)">Copy</button>
      </div>
      <p class="note">Must be run as admin — otherwise it silently installs to the wrong (Current User) store and WebClient won't see it.</p>
    </div>
    <div class="step">
      <div class="num">Step 3 — Windows</div>
      <div class="title">Restart the <span class="hl">WebClient</span> service</div>
      <div class="desc">In the same admin Command Prompt:</div>
      <div class="cmd">
        <code id="w3">net stop webclient &amp;&amp; net start webclient</code>
        <button class="copy" onclick="cp('w3',this)">Copy</button>
      </div>
    </div>
    <div class="step">
      <div class="num">Step 4 — Windows</div>
      <div class="title">Map the network drive</div>
      <div class="desc">File Explorer &#8594; <span class="hl">This PC</span> &#8594; <span class="hl">Map network drive…</span> &#8594; paste this URL:</div>
      <div class="cmd">
        <code id="w4">{_webdav_url}</code>
        <button class="copy" onclick="cp('w4',this)">Copy</button>
      </div>
      <p class="note">Username: <span class="url">{_username}</span> &nbsp;·&nbsp; Password: shown in Warden app<br>
      If <span class="url">warden.local</span> doesn't resolve, try: <span class="url">{_webdav_ip_url}</span></p>
      <div class="warn">&#9888; Don't test from the same PC running Warden — Windows blocks WebDAV loopback connections over HTTPS.</div>
    </div>
  </div>

  <!-- macOS -->
  <div id="mac" class="panel">
    <div class="step">
      <div class="num">Step 1 — macOS</div>
      <div class="title">Download the CA certificate</div>
      <a class="dl" href="/warden-ca.crt" download>&#8659;&nbsp; Download warden-ca.crt</a>
    </div>
    <div class="step">
      <div class="num">Step 2 — macOS</div>
      <div class="title">Trust it in Keychain</div>
      <div class="desc">Double-click the downloaded file &#8594; Keychain Access opens &#8594; find <span class="hl">Warden Local CA</span> &#8594; double-click &#8594; <span class="hl">Trust</span> &#8594; set <span class="hl">When using this certificate</span> to <span class="hl">Always Trust</span>.</div>
    </div>
    <div class="step">
      <div class="num">Step 3 — macOS</div>
      <div class="title">Connect in Finder</div>
      <div class="desc">Press <span class="hl">&#8984;K</span> in Finder and paste:</div>
      <div class="cmd">
        <code id="m3">{_webdav_url}</code>
        <button class="copy" onclick="cp('m3',this)">Copy</button>
      </div>
      <p class="note">Username: <span class="url">{_username}</span> &nbsp;·&nbsp; Password: shown in Warden app</p>
    </div>
  </div>

  <!-- iPhone / iPad -->
  <div id="ios" class="panel">
    <div class="step">
      <div class="num">Step 1 — iOS</div>
      <div class="title">Download the certificate profile</div>
      <div class="desc">Open this page in <span class="hl">Safari</span> (not Chrome) and tap the download button — iOS will prompt you to install a profile.</div>
      <a class="dl" href="/warden-ca.crt">&#8659;&nbsp; Download warden-ca.crt</a>
    </div>
    <div class="step">
      <div class="num">Step 2 — iOS</div>
      <div class="title">Install the profile</div>
      <div class="desc"><span class="hl">Settings &#8594; General &#8594; VPN &amp; Device Management</span> &#8594; tap the Warden profile &#8594; <span class="hl">Install</span>.</div>
    </div>
    <div class="step">
      <div class="num">Step 3 — iOS</div>
      <div class="title">Enable full trust</div>
      <div class="desc"><span class="hl">Settings &#8594; General &#8594; About &#8594; Certificate Trust Settings</span> &#8594; toggle on <span class="hl">Warden Local CA</span>.</div>
    </div>
    <div class="step">
      <div class="num">Step 4 — iOS</div>
      <div class="title">Connect with a WebDAV app</div>
      <div class="desc">Use <span class="hl">Documents by Readdle</span> or similar. Add a WebDAV server:</div>
      <div class="cmd">
        <code id="i4">{_webdav_url}</code>
        <button class="copy" onclick="cp('i4',this)">Copy</button>
      </div>
      <p class="note">Username: <span class="url">{_username}</span> &nbsp;·&nbsp; Password: shown in Warden app</p>
    </div>
  </div>

  <!-- Android -->
  <div id="and" class="panel">
    <div class="step">
      <div class="num">Step 1 — Android</div>
      <div class="title">Download the CA certificate</div>
      <a class="dl" href="/warden-ca.crt" download>&#8659;&nbsp; Download warden-ca.crt</a>
    </div>
    <div class="step">
      <div class="num">Step 2 — Android</div>
      <div class="title">Install as CA certificate</div>
      <div class="desc"><span class="hl">Settings &#8594; Security &#8594; Encryption &amp; credentials &#8594; Install a certificate &#8594; CA certificate</span> &#8594; pick the downloaded file.</div>
      <p class="note">Path varies by manufacturer — search "CA certificate" in Settings if needed.</p>
    </div>
    <div class="step">
      <div class="num">Step 3 — Android</div>
      <div class="title">Connect with a WebDAV app</div>
      <div class="desc">Use <span class="hl">Solid Explorer</span> or <span class="hl">FX File Explorer</span>. Add a WebDAV connection:</div>
      <div class="cmd">
        <code id="a3">{_webdav_url}</code>
        <button class="copy" onclick="cp('a3',this)">Copy</button>
      </div>
      <p class="note">Username: <span class="url">{_username}</span> &nbsp;·&nbsp; Password: shown in Warden app</p>
    </div>
  </div>

  <!-- Linux -->
  <div id="lnx" class="panel">
    <div class="step">
      <div class="num">Step 1 — Linux</div>
      <div class="title">Download &amp; trust the CA certificate</div>
      <div class="cmd">
        <code id="l1">curl -o /tmp/warden-ca.crt http://{_display_ip}:{port}/warden-ca.crt &amp;&amp; sudo cp /tmp/warden-ca.crt /usr/local/share/ca-certificates/ &amp;&amp; sudo update-ca-certificates</code>
        <button class="copy" onclick="cp('l1',this)">Copy</button>
      </div>
    </div>
    <div class="step">
      <div class="num">Step 2 — Linux</div>
      <div class="title">Mount the WebDAV share</div>
      <div class="desc">Using <span class="hl">davfs2</span>:</div>
      <div class="cmd">
        <code id="l2">sudo mount -t davfs {_webdav_url} /mnt/warden</code>
        <button class="copy" onclick="cp('l2',this)">Copy</button>
      </div>
      <p class="note">Username: <span class="url">{_username}</span> &nbsp;·&nbsp; Password: shown in Warden app</p>
    </div>
  </div>

</div>
<script>
function show(id,btn){{
  document.querySelectorAll('.panel').forEach(function(p){{p.classList.remove('active')}});
  document.querySelectorAll('.ptab').forEach(function(b){{b.classList.remove('active')}});
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}}
function cp(id,btn){{
  var el=document.getElementById(id);
  var text=el.textContent.trim().replace(/&&/g,'&&');
  if(window.navigator&&navigator.clipboard){{
    navigator.clipboard.writeText(text).then(function(){{ok(btn)}}).catch(function(){{fallback(text,btn)}});
  }}else{{
    fallback(text,btn);
  }}
}}
function fallback(text,btn){{
  var ta=document.createElement('textarea');
  ta.value=text;ta.style.cssText='position:fixed;opacity:0;top:0;left:0';
  document.body.appendChild(ta);ta.focus();ta.select();
  try{{document.execCommand('copy');ok(btn);}}catch(e){{}}
  document.body.removeChild(ta);
}}
function ok(btn){{
  btn.textContent='Copied!';btn.classList.add('ok');
  setTimeout(function(){{btn.textContent='Copy';btn.classList.remove('ok')}},1600);
}}
</script>
</body>
</html>""".encode()

        access_log = self._access_log  # capture for closure

        class _Handler(http.server.BaseHTTPRequestHandler):
            def _serve(self_, method: str) -> None:
                status = 200
                if self_.path in _FILE_ROUTES:
                    file_path, mime, fname = _FILE_ROUTES[self_.path]
                    try:
                        data = file_path.read_bytes()
                        self_.send_response(200)
                        self_.send_header("Content-Type", mime)
                        self_.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                        self_.send_header("Content-Length", str(len(data)))
                        self_.end_headers()
                        if method == "GET":
                            self_.wfile.write(data)
                    except Exception:
                        self_.send_response(500)
                        self_.end_headers()
                        status = 500
                elif self_.path == "/":
                    self_.send_response(200)
                    self_.send_header("Content-Type", "text/html; charset=utf-8")
                    self_.send_header("Content-Length", str(len(_SETUP_HTML)))
                    self_.end_headers()
                    if method == "GET":
                        self_.wfile.write(_SETUP_HTML)
                else:
                    self_.send_response(404)
                    self_.end_headers()
                    status = 404
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                client = self_.client_address[0]
                access_log.append(f"{ts}  CA-HTTP  {method} {self_.path} → {status}  [{client}]")

            def do_GET(self_):
                self_._serve("GET")

            def do_HEAD(self_):
                self_._serve("HEAD")

            def log_message(self_, *args):
                pass  # suppress console noise; we write to access_log above

        self._ca_http_server = http.server.HTTPServer(("0.0.0.0", port), _Handler)
        self._ca_http_thread = threading.Thread(
            target=self._ca_http_server.serve_forever,
            daemon=True,
        )
        self._ca_http_thread.start()

        display_ip = lan_ip or self._local_ip()
        return f"http://{display_ip}:{port}/"

    def _stop_ca_server(self) -> None:
        if self._ca_http_server:
            try:
                self._ca_http_server.shutdown()   # signals serve_forever() to exit
                self._ca_http_server.server_close()  # releases the socket immediately
            except Exception:
                pass
            self._ca_http_server = None
            self._ca_http_thread = None
        self.ca_url = ""

    # ── mDNS (warden.local) ───────────────────────────────────────────────────

    def _start_mdns(self, lan_ip: str, port: int) -> bool:
        """Advertise warden.local via mDNS so clients resolve the hostname
        automatically without any DNS server or registry changes.

        Returns True if mDNS was registered successfully.
        """
        if not _ZEROCONF:
            logging.getLogger("warden").warning(
                "zeroconf not installed — warden.local unavailable. "
                "Install: pip install zeroconf"
            )
            return False
        import socket as _socket
        try:
            self._zeroconf = Zeroconf()
            self._zeroconf_info = _ZcServiceInfo(
                type_="_http._tcp.local.",
                name="Warden._http._tcp.local.",
                addresses=[_socket.inet_aton(lan_ip)],
                port=port,
                server=f"{_MDNS_HOST}.",
            )
            self._zeroconf.register_service(self._zeroconf_info)
            logging.getLogger("warden").info(
                "mDNS: %s → %s (port %d)", _MDNS_HOST, lan_ip, port
            )
            return True
        except Exception as exc:
            logging.getLogger("warden").warning("mDNS registration failed: %s", exc)
            self._stop_mdns()
            return False

    def _stop_mdns(self) -> None:
        if self._zeroconf:
            try:
                if self._zeroconf_info:
                    self._zeroconf.unregister_service(self._zeroconf_info)
                self._zeroconf.close()
            except Exception:
                pass
            self._zeroconf = None
            self._zeroconf_info = None
        self.mdns_active = False

    # ── Windows Firewall management ───────────────────────────────────────────

    def _apply_firewall_rules(self, tcp_ports: list) -> None:
        """Add inbound Windows Firewall rules for WebDAV/CA ports + UDP 5353 (mDNS).

        Runs silently — failures are logged at DEBUG level only so the app never
        crashes just because firewall changes couldn't be applied (e.g. no admin).
        """
        import sys, subprocess
        if sys.platform != "win32":
            return
        rules = [("Warden-mDNS-5353", "UDP", 5353)] + \
                [(f"Warden-TCP-{p}", "TCP", p) for p in tcp_ports]
        for name, proto, port in rules:
            try:
                subprocess.run(
                    ["netsh", "advfirewall", "firewall", "add", "rule",
                     f"name={name}", "dir=in", "action=allow",
                     f"protocol={proto}", f"localport={port}"],
                    check=False, capture_output=True, timeout=5,
                )
            except Exception as exc:
                logging.getLogger("warden").debug("Firewall rule %s skipped: %s", name, exc)
        self._fw_tcp_ports = list(tcp_ports)

    def _remove_firewall_rules(self) -> None:
        """Remove the inbound firewall rules that were added by _apply_firewall_rules."""
        import sys, subprocess
        if sys.platform != "win32":
            return
        names = ["Warden-mDNS-5353"] + [f"Warden-TCP-{p}" for p in self._fw_tcp_ports]
        for name in names:
            try:
                subprocess.run(
                    ["netsh", "advfirewall", "firewall", "delete", "rule",
                     f"name={name}"],
                    check=False, capture_output=True, timeout=5,
                )
            except Exception as exc:
                logging.getLogger("warden").debug("Firewall rule %s removal skipped: %s", name, exc)
        self._fw_tcp_ports = []

    def start(
        self,
        root_path: Path,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool = True,
    ) -> str:
        if not _WSGIDAV:
            raise RuntimeError(
                "wsgidav and cheroot required.\n"
                "Install: pip install wsgidav cheroot"
            )

        self.token = secrets.token_urlsafe(16)

        config = {
            "host": host,
            "port": port,
            "root": str(root_path),
            "provider_mapping": {"/": str(root_path)},
            "simple_dc": {
                "user_mapping": {"*": {username: {"password": password}}}
            },
            "http_authenticator": {
                "domain_controller": None,
                "accept_basic": True,
                "accept_digest": True,
                "default_to_digest": True,  # Windows WebClient prefers Digest over Basic
            },
            "verbose": 0,
            "logging": {"enable_loggers": []},
        }

        app = WsgiDAVApp(config)

        lan_ip = self._local_ip()   # needed for mDNS and CDP URL regardless of SSL

        server = cheroot_wsgi.Server((host, port), app)
        if use_ssl:
            import ssl as _ssl
            ca_port = port + 1
            self._ensure_ca()   # generate CA key+cert if missing
            self._ensure_crl()  # generate empty CRL so WinHTTP revocation check succeeds

            # CDP URL baked into the server cert so WinHTTP knows where to fetch the CRL
            cdp_url = f"http://{lan_ip}:{ca_port}/warden-ca.crl" if lan_ip not in ("—", "localhost") else ""

            # Force-regenerate the server cert on every start so the CDP URL and
            # SANs are always current.  Stale certs (wrong CDP, wrong IP) cause
            # WinHTTP to drop the TLS handshake with EOF (error 6) because it
            # cannot fetch the CRL from the embedded distribution point.
            for _stale in ("server.crt", "server.key", "server-chain.pem"):
                (self.cert_dir / _stale).unlink(missing_ok=True)

            cert_path, key_path = self._ensure_cert(cdp_url=cdp_url)

            # Full-chain PEM (server cert + CA cert) — clients get the whole chain
            chain_path = self.cert_dir / "server-chain.pem"
            chain_path.write_bytes(
                Path(cert_path).read_bytes() + self.ca_cert_path.read_bytes()
            )

            adapter = BuiltinSSLAdapter(str(chain_path), key_path)
            ctx = _ssl.SSLContext(_ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(str(chain_path), key_path)
            ctx.minimum_version = _ssl.TLSVersion.TLSv1_2
            if hasattr(_ssl, "OP_IGNORE_UNEXPECTED_EOF"):
                ctx.options |= _ssl.OP_IGNORE_UNEXPECTED_EOF
            adapter.context = ctx
            server.ssl_adapter = adapter
            # Start plain-HTTP mini server on port+1 so other network devices can
            # download the CA cert and CRL without needing to trust TLS first.
            try:
                self.ca_url = self._start_ca_server(
                    ca_port, webdav_port=port, lan_ip=lan_ip, username=username
                )
            except Exception as _ca_err:
                import logging as _log
                _log.getLogger("warden").warning("CA/CRL server failed to start on port %d: %s", ca_port, _ca_err)
                self.ca_url = ""

        # Attach access-log handler to the wsgidav logger
        self._access_log.clear()
        self._log_handler = _AccessLogHandler(self._access_log)
        logging.getLogger("wsgidav").addHandler(self._log_handler)

        self._server = server
        self._running = True

        # Run the blocking server.start() in a daemon thread.
        # Use a queue to surface any immediate bind/SSL errors back to the caller.
        error_q: queue.Queue = queue.Queue()

        def _run() -> None:
            try:
                server.start()
            except Exception as exc:
                error_q.put(exc)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

        # Wait up to 1.5 s for a startup failure; if the queue is still empty
        # by then the server is listening successfully.
        try:
            raise error_q.get(timeout=1.5)
        except queue.Empty:
            pass  # server is up

        self._running = True

        # Open firewall ports so other LAN devices can reach this machine.
        # TCP: WebDAV port + CA HTTP port (cert/CRL download). UDP 5353: mDNS.
        # Rules are removed again in stop() to keep the firewall clean.
        _tcp_fw = [port]
        if use_ssl:
            _tcp_fw.append(port + 1)   # CA HTTP port
        self._apply_firewall_rules(_tcp_fw)

        # Start mDNS after the server is confirmed running so clients can reach
        # it via warden.local instead of a raw IP address.  warden.local is
        # automatically in Windows' Intranet zone, which bypasses the WebClient
        # zone restrictions that block HTTPS WebDAV on non-standard ports.
        self.mdns_active = self._start_mdns(lan_ip, port)

        scheme = "https" if use_ssl else "http"
        if self.mdns_active:
            url_host = _MDNS_HOST
        elif host == "0.0.0.0":
            url_host = lan_ip
        else:
            url_host = host
        return f"{scheme}://{url_host}:{port}"

    def stop(self) -> None:
        if self._server and self._running:
            try:
                self._server.stop()
            except Exception:
                pass
            self._running = False
        if self._log_handler:
            logging.getLogger("wsgidav").removeHandler(self._log_handler)
            self._log_handler = None
        self._stop_ca_server()
        self._stop_mdns()
        self._remove_firewall_rules()

    def get_access_log(self) -> list[str]:
        return list(self._access_log)

    def is_running(self) -> bool:
        return self._running

    def _local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"
