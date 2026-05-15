// App chrome: Header, Tabs, StatusBar

function Header({ drives, selectedDrive, onDriveChange, theme, onThemeToggle, onRefresh, onUpdateRules }) {
  const connected = !!selectedDrive;
  return (
    <div className="header">
      <div className="brand">
        <div className="logo">
          <Icon.shield style={{ width: 20, height: 20 }} />
        </div>
        <div className="name">
          Warden <small>v2.4.1</small>
        </div>
      </div>

      <div className="drive-selector">
        <span className={`dot ${connected ? "connected" : ""}`} />
        <Icon.drive style={{ width: 16, height: 16, color: "var(--text-dim)" }} />
        {connected ? (
          <div className="description">
            <span style={{ fontWeight: "600" }}>{selectedDrive.label}</span>
            <span className="meta">
              {selectedDrive.path} · {selectedDrive.filesystem} · {selectedDrive.size_str}
            </span>
          </div>
        ) : (
          <span style={{ color: "var(--text-muted)" }}>No USB connected</span>
        )}
        <Icon.caret className="caret" style={{ width: 14, height: 14, marginLeft: "auto" }} />
        <select
          value={selectedDrive?.path || ""}
          onChange={(e) => onDriveChange(e.target.value)}
          style={{ position: "absolute", inset: 0, opacity: 0, cursor: "pointer", width: "100%" }}
        >
          <option value="">No drive</option>
          {drives.map((d) => (
            <option key={d.path} value={d.path}>
              {d.display_name}
            </option>
          ))}
        </select>
      </div>

      <div className="actions">
        <button className="iconbtn" title="Refresh drives" onClick={onRefresh}>
          <Icon.refresh style={{ width: 14, height: 14 }} />
        </button>
        <button className="iconbtn" title="Toggle theme" onClick={onThemeToggle}>
          {theme === "dark" ? (
            <Icon.sun style={{ width: 14, height: 14 }} />
          ) : (
            <Icon.moon style={{ width: 14, height: 14 }} />
          )}
        </button>
        <button className="btn" style={{ fontSize: 12.5 }} onClick={onUpdateRules}>
          <Icon.download style={{ width: 13, height: 13 }} />
          Update Rules
        </button>
      </div>
    </div>
  );
}

function Tabs({ active, onChange, threatCount }) {
  const tabs = [
    { id: "scan", label: "Scan", icon: <Icon.scan style={{ width: 14, height: 14 }} /> },
    { id: "host", label: "Host", icon: <Icon.server style={{ width: 14, height: 14 }} /> },
    { id: "format", label: "Format", icon: <Icon.disk style={{ width: 14, height: 14 }} /> },
  ];
  return (
    <div className="tabs">
      {tabs.map((t) => (
        <div key={t.id} className={`tab ${active === t.id ? "active" : ""}`} onClick={() => onChange(t.id)}>
          {t.icon}
          <span>{t.label}</span>
          {t.id === "scan" && threatCount > 0 && <span className="count">{Math.min(threatCount, 99)}</span>}
        </div>
      ))}
    </div>
  );
}

function StatusBar({ drive, lastScan, enginesReady }) {
  return (
    <div className="statusbar">
      {drive ? (
        <>
          <span>
            <b>Drive:</b> {drive.path} ({drive.label})
          </span>
          <span className="sep" />
          <span>
            <b>Filesystem:</b> {drive.filesystem}
          </span>
          <span className="sep" />
          <span>
            <b>Capacity:</b> {drive.free_str} free of {drive.size_str}
          </span>
        </>
      ) : (
        <span>No drive connected</span>
      )}
      <div className="right">
        {lastScan && (
          <>
            <span>
              Last scan: <b>{lastScan}</b>
            </span>
            <span className="sep" />
          </>
        )}
        <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: enginesReady ? "var(--success)" : "var(--text-muted)",
              display: "inline-block",
            }}
          />
          {enginesReady ? "Engines ready" : "Engines loading…"}
        </span>
      </div>
    </div>
  );
}

function Banner({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div
      style={{
        padding: "7px 14px",
        background: "rgba(124,58,237,.10)",
        border: "1px solid rgba(124,58,237,.25)",
        borderRadius: 6,
        margin: "8px 14px 0",
        display: "flex",
        alignItems: "center",
        gap: 10,
        fontSize: 12.5,
      }}
    >
      <span style={{ flex: 1 }}>{message}</span>
      <button className="btn ghost" style={{ padding: "2px 8px", fontSize: 12 }} onClick={onDismiss}>
        ✕
      </button>
    </div>
  );
}

Object.assign(window, { Header, Tabs, StatusBar, Banner });
