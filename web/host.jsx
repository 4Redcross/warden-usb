// Host tab — WebDAV server config & connected state

function QRCodeImg({ url, size = 140 }) {
  const divRef = React.useRef(null);
  React.useEffect(() => {
    if (!divRef.current || !url || !window.QRCode) return;
    divRef.current.innerHTML = "";
    new window.QRCode(divRef.current, {
      text: url,
      width: size,
      height: size,
      colorDark: "#000000",
      colorLight: "#ffffff",
      correctLevel: window.QRCode.CorrectLevel.M,
    });
  }, [url, size]);
  return (
    <div
      style={{
        background: "#fff",
        padding: 8,
        borderRadius: 6,
        lineHeight: 0,
        boxShadow: "0 2px 10px rgba(0,0,0,0.35)",
      }}
    >
      <div ref={divRef} style={{ borderRadius: 2, overflow: "hidden" }} />
    </div>
  );
}

function HostConfig({ drive, config, setConfig, onStart }) {
  const toggle = (field) => setConfig((c) => ({ ...c, [field]: !c[field] }));
  const [showPass, setShowPass] = React.useState(false);

  return (
    <div className="card">
      <div className="card-head">
        <Icon.server style={{ width: 14, height: 14, color: "var(--text-dim)" }} />
        <h3>WebDAV Server</h3>
        <span className="sub">Share the selected drive over your local network</span>
        <span className="badge muted" style={{ marginLeft: "auto" }}>
          <span className="dot" />
          Stopped
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, padding: 14 }}>
        {/* Port */}
        <div className="field">
          <label>Port</label>
          <input
            type="number"
            value={config.port}
            min={1024}
            max={65535}
            onChange={(e) => setConfig((c) => ({ ...c, port: parseInt(e.target.value) || 8443 }))}
          />
        </div>

        {/* Mode */}
        <div className="field">
          <label>Mode</label>
          <select
            value={config.read_only ? "ro" : "rw"}
            onChange={(e) => setConfig((c) => ({ ...c, read_only: e.target.value === "ro" }))}
          >
            <option value="ro">Read-only · (safer)</option>
            <option value="rw">Read-write</option>
          </select>
        </div>

        {/* Username */}
        <div className="field">
          <label>Username</label>
          <input
            type="text"
            value={config.username}
            onChange={(e) => setConfig((c) => ({ ...c, username: e.target.value }))}
          />
        </div>

        {/* Password */}
        <div className="field">
          <label>Password</label>
          <div style={{ display: "flex", gap: 6 }}>
            <input
              type={showPass ? "text" : "password"}
              value={config.password}
              placeholder="auto-generated"
              onChange={(e) => setConfig((c) => ({ ...c, password: e.target.value }))}
              style={{ flex: 1 }}
            />
            {config.password && (
              <button
                className="btn sm ghost"
                onClick={() => setShowPass((s) => !s)}
                title={showPass ? "Hide" : "Show"}
              >
                <Icon.eye style={{ width: 12, height: 12 }} />
              </button>
            )}
            <button
              className="btn sm"
              onClick={() => {
                const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$";
                const pwd = Array.from(
                  { length: 16 },
                  () => chars[Math.floor(Math.random() * chars.length)],
                ).join("");
                setConfig((c) => ({ ...c, password: pwd }));
                setShowPass(true);
              }}
            >
              <Icon.key style={{ width: 12, height: 12 }} />
              Generate
            </button>
          </div>
        </div>

        {/* Full-width row: checkboxes + HTTPS toggle */}
        <div style={{ gridColumn: "1 / -1", display: "flex", alignItems: "center", gap: 24, paddingTop: 4 }}>
          <span
            className={`check ${!config.read_only ? "on" : ""}`}
            onClick={() => setConfig((c) => ({ ...c, read_only: !c.read_only }))}
          >
            <span className="box" />
            Allow write access
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: "auto" }}>
            <span style={{ fontSize: 12.5 }}>HTTPS</span>
            <span className={`toggle ${config.use_ssl ? "on" : ""}`} onClick={() => toggle("use_ssl")} />
            <span className="sub">
              {config.use_ssl ? "warden.local · one-time cert install per device" : "unencrypted"}
            </span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: "10px 14px",
          borderTop: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          gap: 10,
          background: "var(--surface-deep)",
          borderRadius: "0 0 8px 8px",
        }}
      >
        <Icon.lock style={{ width: 11, height: 11, color: "var(--text-muted)" }} />
        <span className="sub">Server runs only while Warden is open. Credentials are session-scoped.</span>
        <button className="btn primary lg" style={{ marginLeft: "auto" }} disabled={!drive} onClick={onStart}>
          <Icon.server style={{ width: 13, height: 13 }} />
          Start Server
        </button>
      </div>
    </div>
  );
}

function AccessLogModal({ onClose }) {
  const [lines, setLines] = React.useState([]);
  const bottomRef = React.useRef(null);

  React.useEffect(() => {
    const load = async () => {
      const log = (await window.pywebview?.api?.get_access_log?.()) || [];
      setLines(log);
    };
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, []);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        background: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 10,
          width: 640,
          maxHeight: 420,
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            padding: "10px 14px",
            borderBottom: "1px solid var(--border)",
            gap: 8,
          }}
        >
          <Icon.server style={{ width: 14, height: 14, color: "var(--text-dim)" }} />
          <span style={{ fontWeight: 600, fontSize: 13 }}>Access Log</span>
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 4 }}>
            live · last 200 requests
          </span>
          <button className="btn sm ghost" style={{ marginLeft: "auto" }} onClick={onClose}>
            ✕
          </button>
        </div>
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "10px 14px",
            fontFamily: "monospace",
            fontSize: 11.5,
          }}
        >
          {lines.length === 0 ? (
            <span style={{ color: "var(--text-muted)" }}>No requests yet.</span>
          ) : (
            lines.map((l, i) => (
              <div
                key={i}
                style={{
                  padding: "2px 0",
                  color: "var(--text-dim)",
                  borderBottom: "1px solid var(--border)",
                  whiteSpace: "pre",
                }}
              >
                {l}
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}

function PlatformCard({ icon, name, body, iconSize = 13 }) {
  return (
    <div
      style={{
        background: "var(--surface-2)",
        border: "1px solid var(--border)",
        borderRadius: 7,
        overflow: "hidden",
      }}
    >
      {/* Header row: icon pinned left, name centered across full width */}
      <div
        style={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          padding: "8px 11px",
          height: 34,
        }}
      >
        <div
          style={{
            width: iconSize + 8,
            height: iconSize + 8,
            borderRadius: 4,
            background: "var(--surface-3)",
            color: "var(--text-dim)",
            display: "grid",
            placeItems: "center",
            flexShrink: 0,
            zIndex: 1,
          }}
        >
          {React.cloneElement(icon, { style: { width: iconSize, height: iconSize } })}
        </div>
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 600,
            fontSize: 12.5,
            pointerEvents: "none",
          }}
        >
          {name}
        </div>
      </div>
      {/* Separator */}
      <div style={{ height: 1, background: "var(--border)" }} />
      {/* Body — full width */}
      <div style={{ padding: "9px 11px", fontSize: 11.5, color: "var(--text-dim)", lineHeight: 1.6 }}>
        {body}
      </div>
    </div>
  );
}

function HostConnected({ drive, serverState, config, onStop, onToast }) {
  const [activeTab, setActiveTab] = React.useState("cert");
  const [showPass, setShowPass] = React.useState(false);
  const [showLog, setShowLog] = React.useState(false);
  const url = serverState.url || "";
  const caUrl = serverState.ca_url || "";
  const mdnsActive = serverState.mdns_active || false;

  const copyUrl = () => {
    navigator.clipboard?.writeText(url);
    onToast?.("URL copied.", "info");
  };
  const copyCaUrl = () => {
    navigator.clipboard?.writeText(caUrl);
    onToast?.("Setup guide URL copied.", "info");
  };

  const tabs = caUrl
    ? [
        { id: "cert", label: "Setup Guide" },
        { id: "server", label: "Server" },
      ]
    : [{ id: "server", label: "Server" }];

  // Default to "server" tab if no CA URL available
  React.useEffect(() => {
    if (!caUrl) setActiveTab("server");
  }, [caUrl]);

  const Step = ({ children }) => (
    <div style={{ display: "flex", gap: 5, alignItems: "flex-start", padding: "2px 0" }}>
      <span style={{ color: "var(--accent)", flexShrink: 0, marginTop: 1 }}>›</span>
      <span>{children}</span>
    </div>
  );

  const caSteps = [
    {
      icon: <Icon.win />,
      name: "Windows",
      body: (
        <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <Step>Open the link above — it shows a full setup guide with copy-able commands</Step>
          <Step>
            Download the cert and run the <b>certutil</b> command as admin
          </Step>
          <Step>
            Restart <b>WebClient</b> service, then map the drive
          </Step>
        </div>
      ),
    },
    {
      icon: <Icon.apple />,
      name: "macOS / iPhone",
      body: (
        <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <Step>
            Open the link above in <b>Safari</b> and download the cert
          </Step>
          <Step>
            macOS: <b>System Settings → Privacy &amp; Security → Certificates</b> → trust it
          </Step>
          <Step>
            iPhone: follow the <b>profile install</b> prompt after download
          </Step>
        </div>
      ),
    },
    {
      icon: <Icon.android />,
      name: "Android / Linux",
      body: (
        <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <Step>Scan the QR code or open the link above</Step>
          <Step>
            Android: <b>Settings → Security → Install a certificate → CA certificate</b>
          </Step>
          <Step>
            Linux:{" "}
            <span className="mono" style={{ fontSize: 10 }}>
              sudo cp warden-ca.crt /usr/local/share/ca-certificates/ &amp;&amp; sudo update-ca-certificates
            </span>
          </Step>
        </div>
      ),
    },
  ];

  const serverSteps = [
    {
      icon: <Icon.win />,
      name: "Windows",
      body: (
        <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <Step>
            Open <b>File Explorer</b>
          </Step>
          <Step>
            Right-click <b>This PC</b> → <b>Map network drive…</b>
          </Step>
          <Step>
            Paste the <b>warden.local</b> URL — resolves automatically on your LAN
          </Step>
          <Step>Enter your username and password</Step>
        </div>
      ),
    },
    {
      icon: <Icon.apple />,
      name: "macOS",
      body: (
        <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <Step>
            In Finder press <span className="mono">⌘K</span>
          </Step>
          <Step>
            Paste the <b>warden.local</b> URL
          </Step>
          <Step>Enter your username and password</Step>
        </div>
      ),
    },
    {
      icon: <Icon.android />,
      name: "Android",
      body: (
        <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <Step>
            Install <b>Solid Explorer</b> or a WebDAV client
          </Step>
          <Step>Scan the QR code or enter the URL manually</Step>
          <Step>Enter your username and password</Step>
        </div>
      ),
    },
  ];

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
      {/* ── Card header ── */}
      <div className="card-head">
        <Icon.server style={{ width: 14, height: 14, color: "var(--highlight)" }} />
        <h3>WebDAV Server</h3>
        <span className="sub">
          Sharing <b style={{ color: "var(--text)" }}>{drive?.display_name || "drive"}</b> ·{" "}
          {config.read_only ? "read-only" : "read-write"}
        </span>
        <div style={{ display: "flex", gap: 6, marginLeft: "auto", alignItems: "center" }}>
          {mdnsActive && (
            <span
              className="badge"
              style={{
                background: "rgba(99,102,241,.15)",
                color: "var(--accent)",
                border: "1px solid rgba(99,102,241,.3)",
                fontSize: 11,
              }}
            >
              warden.local
            </span>
          )}
          <span className="badge clean">
            <span className="dot" />
            Running
          </span>
        </div>
      </div>

      {/* ── Inner tab bar ── */}
      {tabs.length > 1 && (
        <div
          style={{
            display: "flex",
            borderBottom: "1px solid var(--border)",
            background: "var(--surface-deep)",
            padding: "0 14px",
            gap: 2,
          }}
        >
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              style={{
                background: "none",
                border: "none",
                borderBottom: activeTab === t.id ? "2px solid var(--accent)" : "2px solid transparent",
                color: activeTab === t.id ? "var(--text)" : "var(--text-muted)",
                cursor: "pointer",
                padding: "9px 14px 8px",
                fontSize: 12.5,
                fontWeight: activeTab === t.id ? 600 : 400,
                marginBottom: -1,
                transition: "color .15s",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
      )}

      {/* ── Scrollable body ── */}
      <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
        {/* ── Install Cert tab ── */}
        {activeTab === "cert" && caUrl && (
          <div style={{ padding: "16px 14px 14px" }}>
            {/* CA URL pill */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                padding: "6px 10px",
                fontSize: 12,
                marginBottom: 14,
              }}
            >
              <Icon.lock style={{ width: 11, height: 11, color: "var(--accent)", flexShrink: 0 }} />
              <span
                className="mono"
                style={{
                  flex: 1,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  color: "var(--highlight)",
                }}
              >
                {caUrl}
              </span>
              <button
                className="btn sm ghost"
                style={{ flexShrink: 0, padding: "2px 7px" }}
                onClick={copyCaUrl}
              >
                <Icon.copy style={{ width: 11, height: 11 }} />
              </button>
            </div>

            {/* Platform cards + QR side by side */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 16, alignItems: "start" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                {caSteps.map((p) => (
                  <PlatformCard key={p.name} icon={p.icon} name={p.name} body={p.body} />
                ))}
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                <QRCodeImg url={caUrl} />
                <span className="sub" style={{ textAlign: "center" }}>
                  Scan to open guide
                </span>
              </div>
            </div>
          </div>
        )}

        {/* ── Server tab ── */}
        {activeTab === "server" && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 120px", gap: 18, padding: 16 }}>
              {/* Left: URL + credentials */}
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div className="field">
                  <label>WebDAV URL</label>
                  <div
                    className="input mono"
                    style={{ height: 42, fontSize: 13.5, color: "var(--highlight)" }}
                  >
                    <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>{url}</span>
                    <button className="btn sm ghost" onClick={copyUrl} style={{ marginLeft: "auto" }}>
                      <Icon.copy style={{ width: 12, height: 12 }} />
                      Copy
                    </button>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 10 }}>
                  <div className="field" style={{ flex: 1 }}>
                    <label>Username</label>
                    <div className="input mono" style={{ height: 34 }}>
                      {config.username}
                    </div>
                  </div>
                  <div className="field" style={{ flex: 1 }}>
                    <label>Password</label>
                    <div className="input mono" style={{ height: 34, paddingRight: 4 }}>
                      <span style={{ flex: 1 }}>
                        {showPass ? serverState.password || config.password : "•".repeat(16)}
                      </span>
                      <button
                        className="btn sm"
                        style={{ marginLeft: "auto" }}
                        onClick={() => setShowPass((s) => !s)}
                      >
                        <Icon.eye style={{ width: 12, height: 12 }} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right: QR for WebDAV URL */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                <QRCodeImg url={url} size={110} />
                <span className="sub">Scan with phone</span>
              </div>
            </div>

            {/* How to connect */}
            <div style={{ borderTop: "1px solid var(--border)", padding: "14px 14px 10px" }}>
              <div
                style={{
                  fontSize: 11,
                  letterSpacing: ".08em",
                  textTransform: "uppercase",
                  color: "var(--text-muted)",
                  marginBottom: 10,
                }}
              >
                How to connect
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                {serverSteps.map((p) => (
                  <PlatformCard key={p.name} icon={p.icon} name={p.name} body={p.body} />
                ))}
              </div>
            </div>
          </>
        )}
      </div>
      {/* end scrollable body */}

      {/* Footer — always visible */}
      <div
        style={{
          padding: "10px 14px",
          borderTop: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          gap: 14,
          background: "var(--surface-deep)",
          borderRadius: "0 0 8px 8px",
          flexShrink: 0,
        }}
      >
        <button className="btn ghost" style={{ marginLeft: "auto" }} onClick={() => setShowLog(true)}>
          Show access log
        </button>
        <button className="btn danger" onClick={onStop}>
          Stop Server
        </button>
      </div>
      {showLog && <AccessLogModal onClose={() => setShowLog(false)} />}
    </div>
  );
}

function HostTab({ drive, serverState, config, setConfig, onStart, onStop, tlsInfo, onToast }) {
  const connected = serverState?.status === "running";
  const fp = tlsInfo?.fingerprint || "—";
  const expires = tlsInfo?.expires || "—";
  const localIp = tlsInfo?.local_ip || "—";
  const mdnsHost = tlsInfo?.mdns_host || "";

  const copyFp = () => {
    navigator.clipboard?.writeText(fp);
    onToast?.("SHA-256 fingerprint copied.", "info");
  };

  const fpShort = fp !== "—" ? fp.slice(0, 23) + "…" : "—";

  return (
    <div className="content">
      {connected ? (
        <HostConnected
          drive={drive}
          serverState={serverState}
          config={config}
          onStop={onStop}
          onToast={onToast}
        />
      ) : (
        <HostConfig drive={drive} config={config} setConfig={setConfig} onStart={onStart} />
      )}
      <div style={{ display: "flex", gap: 12 }}>
        <div
          className="card"
          style={{ flex: 1, padding: "12px 14px", display: "flex", alignItems: "flex-start", gap: 10 }}
        >
          <Icon.shield
            style={{ width: 24, height: 24, color: "var(--accent)", flex: "0 0 auto", marginTop: 4 }}
          />
          <div style={{ fontSize: 12, flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>Hosting notes</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 5, color: "var(--text-muted)" }}>
              <div>
                <span style={{ color: "var(--text-dim)", fontWeight: 600 }}>Network access: </span>
                the server is visible to all devices on your local network. Only share the password with
                people you trust.
              </div>
              <div>
                <span style={{ color: "var(--text-dim)", fontWeight: 600 }}>Read-only mode: </span>
                recommended as it prevents clients from writing ransomware or overwriting files on the USB
                drive.
              </div>
            </div>
          </div>
        </div>
        <div
          className="card"
          style={{ flex: 1, padding: "12px 14px", display: "flex", alignItems: "flex-start", gap: 10 }}
        >
          <Icon.lock
            style={{ width: 24, height: 24, color: "var(--green)", flex: "0 0 auto", marginTop: 4 }}
          />
          <div style={{ fontSize: 12, flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>TLS certificate</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <div style={{ display: "flex", gap: 6 }}>
                <span style={{ color: "var(--text-muted)", width: 52, flexShrink: 0 }}>Local IP</span>
                <span className="mono" style={{ color: "var(--highlight)" }}>
                  {localIp}
                </span>
              </div>
              {mdnsHost && (
                <div style={{ display: "flex", gap: 6 }}>
                  <span style={{ color: "var(--text-muted)", width: 52, flexShrink: 0 }}>mDNS</span>
                  <span className="mono" style={{ color: "var(--accent)" }}>
                    {mdnsHost}
                  </span>
                </div>
              )}
              <div style={{ display: "flex", gap: 6 }}>
                <span style={{ color: "var(--text-muted)", width: 52, flexShrink: 0 }}>Expires</span>
                <span className="mono">{expires}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ color: "var(--text-muted)", flexShrink: 0 }}>SHA-256</span>
                <span
                  className="mono"
                  style={{
                    fontSize: 11,
                    color: "var(--text-dim)",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    flex: 1,
                  }}
                >
                  {fpShort}
                </span>
                {fp !== "—" && (
                  <button
                    className="btn sm ghost"
                    style={{ flexShrink: 0, padding: "1px 6px" }}
                    onClick={copyFp}
                    title="Copy full fingerprint"
                  >
                    <Icon.copy style={{ width: 11, height: 11 }} />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

window.HostTab = HostTab;
