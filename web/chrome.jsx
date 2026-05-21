// App chrome: Header, Tabs, StatusBar

// Small red notification dot — positioned at the top-right of its (relative) parent.
// `ring` is the colour of the gap around the dot; set it to the background it sits on.
function NotifDot({ ring = "var(--surface)" }) {
  return (
    <span
      style={{
        position: "absolute",
        top: 3,
        right: 3,
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: "var(--danger)",
        border: `2px solid ${ring}`,
      }}
    />
  );
}

function Header({ drives, selectedDrive, onDriveChange, theme, onThemeToggle, onRefresh, onOpenSettings, rulesMissing }) {
  const connected = !!selectedDrive;
  return (
    <div className="header">
      <div className="brand">
        <div className="logo">
          <Icon.shield style={{ width: 20, height: 20 }} />
        </div>
        <div className="name">
          Warden <small>v1.0.1</small>
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
        <button
          className="iconbtn"
          title={rulesMissing ? "Settings — YARA rules not installed" : "Settings"}
          onClick={onOpenSettings}
          style={{ position: "relative" }}
        >
          <Icon.gear style={{ width: 15, height: 15 }} />
          {rulesMissing && <NotifDot />}
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

function StatusBar({ drive, lastScan }) {
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
          <span>
            Last scan: <b>{lastScan}</b>
          </span>
        )}
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

function AuditLogModal({ onClose }) {
  const [text, setText] = React.useState(null);

  const load = React.useCallback(async () => {
    const log = await window.pywebview?.api?.get_audit_log?.();
    setText(typeof log === "string" ? log : "");
  }, []);

  React.useEffect(() => {
    let active = true;
    (async () => {
      const log = await window.pywebview?.api?.get_audit_log?.();
      if (active) setText(typeof log === "string" ? log : "");
    })();
    return () => { active = false; };
  }, []);

  const lines = (text || "").split("\n").filter(Boolean);

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
          width: 680,
          maxHeight: 460,
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
          <Icon.file style={{ width: 14, height: 14, color: "var(--text-dim)" }} />
          <span style={{ fontWeight: 600, fontSize: 13 }}>Audit Log</span>
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 4 }}>
            last 200 events · newest first
          </span>
          <button className="btn sm ghost" style={{ marginLeft: "auto" }} onClick={load}>
            <Icon.refresh style={{ width: 12, height: 12 }} />
            Refresh
          </button>
          <button className="btn sm ghost" onClick={onClose}>
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
          {text === null ? (
            <span style={{ color: "var(--text-muted)" }}>Loading…</span>
          ) : lines.length === 0 ? (
            <span style={{ color: "var(--text-muted)" }}>No audit events recorded yet.</span>
          ) : (
            lines.map((l, i) => (
              <div
                key={i}
                style={{
                  padding: "2px 0",
                  color: "var(--text-dim)",
                  borderBottom: "1px solid var(--border)",
                  whiteSpace: "pre-wrap",
                }}
              >
                {l}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function SettingsModal({ settings, onClose, onUpdateRules, onOpenAuditLog, onToast, onSettingsChanged }) {
  const [vtKey, setVtKey] = React.useState("");
  const [showKey, setShowKey] = React.useState(false);
  const [saving, setSaving] = React.useState(false);

  const hasKey = !!(settings && settings.has_vt_key);
  const keyringOk = !settings || settings.keyring_available !== false;
  const lastUpd = settings && settings.rules_last_updated;
  const rulesMissing = !!settings && settings.has_yara_rules === false;

  const saveKey = async () => {
    const key = vtKey.trim();
    if (!key) {
      onToast && onToast("Enter an API key first.", "warn");
      return;
    }
    setSaving(true);
    const r = await window.pywebview?.api?.set_vt_key?.(key);
    setSaving(false);
    if (r && r.ok) {
      setVtKey("");
      setShowKey(false);
      onToast && onToast("VirusTotal API key verified and saved.", "info");
      onSettingsChanged && onSettingsChanged();
    } else {
      onToast && onToast(`Key not saved: ${(r && r.error) || "unknown error"}`, "error");
    }
  };

  const removeKey = async () => {
    if (!confirm("Remove the saved VirusTotal API key?")) return;
    const r = await window.pywebview?.api?.clear_vt_key?.();
    if (r && r.ok) {
      onToast && onToast("VirusTotal API key removed.", "info");
      onSettingsChanged && onSettingsChanged();
    } else {
      onToast && onToast(`Could not remove key: ${(r && r.error) || "unknown error"}`, "error");
    }
  };

  const sectionStyle = {
    background: "var(--surface-2)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    padding: "12px 14px",
  };
  const titleStyle = { fontSize: 12.5, fontWeight: 600, color: "var(--text)", marginBottom: 3 };
  const descStyle = { fontSize: 11.5, color: "var(--text-muted)", lineHeight: 1.5, marginBottom: 10 };

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
          width: 520,
          maxHeight: 560,
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
          <Icon.gear style={{ width: 14, height: 14, color: "var(--text-dim)" }} />
          <span style={{ fontWeight: 600, fontSize: 13 }}>Settings</span>
          <button className="btn sm ghost" style={{ marginLeft: "auto" }} onClick={onClose}>
            ✕
          </button>
        </div>

        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: 14,
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          {/* 1 — Update YARA rules */}
          <div style={sectionStyle}>
            <div style={titleStyle}>Update YARA Rules</div>
            <div style={descStyle}>
              Malware signature rules from the Neo23x0/signature-base project.
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 11.5, color: "var(--text-muted)", flex: 1 }}>
                Last updated:{" "}
                <b style={{ color: "var(--text-dim)" }}>
                  {lastUpd ? new Date(lastUpd).toLocaleString() : "Never"}
                </b>
              </span>
              <button
                className="btn sm"
                onClick={onUpdateRules}
                style={{ position: "relative" }}
              >
                <Icon.download style={{ width: 12, height: 12 }} />
                Update Rules
                {rulesMissing && <NotifDot ring="var(--surface-2)" />}
              </button>
            </div>
          </div>

          {/* 2 — VirusTotal API key */}
          <div style={sectionStyle}>
            <div style={titleStyle}>VirusTotal API Key</div>
            <div style={descStyle}>
              Enables hash lookups and file uploads. Stored in your operating system's
              credential vault — never written to plaintext config.
            </div>
            {!keyringOk && (
              <div
                style={{
                  fontSize: 11,
                  color: "var(--warning)",
                  background: "rgba(245,158,11,0.1)",
                  border: "1px solid rgba(245,158,11,0.3)",
                  borderRadius: 5,
                  padding: "5px 8px",
                  marginBottom: 8,
                }}
              >
                Secure storage unavailable — the key would be saved in plaintext config.
              </div>
            )}
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
              <Icon.lock
                style={{
                  width: 12,
                  height: 12,
                  color: hasKey ? "var(--success)" : "var(--text-muted)",
                }}
              />
              <span
                style={{
                  fontSize: 11.5,
                  color: hasKey ? "var(--success)" : "var(--text-muted)",
                }}
              >
                {hasKey ? "A key is currently saved." : "No key configured."}
              </span>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <div style={{ position: "relative", flex: 1 }}>
                <input
                  type={showKey ? "text" : "password"}
                  value={vtKey}
                  onChange={(e) => setVtKey(e.target.value)}
                  placeholder={hasKey ? "Enter a new key to replace" : "Paste your VirusTotal API key"}
                  style={{ paddingRight: 32 }}
                  autoComplete="off"
                  spellCheck={false}
                />
                <button
                  className="iconbtn"
                  onClick={() => setShowKey((s) => !s)}
                  title={showKey ? "Hide key" : "Show key"}
                  style={{ position: "absolute", right: 3, top: 3, width: 28, height: 28 }}
                >
                  <Icon.eye style={{ width: 13, height: 13 }} />
                </button>
              </div>
              <button className="btn sm" onClick={saveKey} disabled={saving}>
                {saving ? "Verifying…" : "Save"}
              </button>
              {hasKey && (
                <button className="btn sm" onClick={removeKey} style={{ color: "var(--danger)" }}>
                  Remove
                </button>
              )}
            </div>
          </div>

          {/* 3 — View audit logs */}
          <div style={sectionStyle}>
            <div style={titleStyle}>View Audit Logs</div>
            <div style={descStyle}>
              History of scans, quarantines, formats and file-server activity.
            </div>
            <button className="btn sm" onClick={onOpenAuditLog}>
              <Icon.file style={{ width: 12, height: 12 }} />
              Open Audit Log
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Header, Tabs, StatusBar, Banner, AuditLogModal, SettingsModal });
