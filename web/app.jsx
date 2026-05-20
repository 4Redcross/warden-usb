// Main app — state management and API wiring

const { useState, useEffect, useCallback, useRef } = React;

// ── Toast ────────────────────────────────────────────────────────────────────
function Toaster({ toasts }) {
  return (
    <div style={{
      position: "fixed", bottom: 20, right: 20, zIndex: 9999,
      display: "flex", flexDirection: "column", gap: 8, pointerEvents: "none",
    }}>
      {toasts.map(t => (
        <div key={t.id} style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "10px 16px", borderRadius: 8, fontSize: 13,
          background: t.type === "error" ? "var(--danger)" : t.type === "warn" ? "var(--warning)" : "#1e2330",
          color: "#fff",
          border: `1px solid ${t.type === "error" ? "rgba(239,68,68,.4)" : t.type === "warn" ? "rgba(245,158,11,.4)" : "var(--border)"}`,
          boxShadow: "0 4px 16px rgba(0,0,0,.4)",
          animation: "toastIn .2s ease",
          pointerEvents: "auto",
          minWidth: 220, maxWidth: 380,
        }}>
          <span style={{ flex: 1 }}>{t.message}</span>
        </div>
      ))}
    </div>
  );
}

function useToast() {
  const [toasts, setToasts] = useState([]);
  const counter = useRef(0);
  const toast = useCallback((message, type = "info", duration = 3500) => {
    const id = ++counter.current;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), duration);
  }, []);
  return { toasts, toast };
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  componentDidCatch(error, info) {
    console.error("Warden render error:", error, info.componentStack);
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{
          padding: 32, fontFamily: "monospace", background: "#0f1117",
          color: "#ef4444", height: "100vh", overflow: "auto"
        }}>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>
            Warden crashed — render error
          </div>
          <pre style={{ fontSize: 12, whiteSpace: "pre-wrap", color: "#e8e9ed" }}>
            {String(this.state.error)}
          </pre>
          <button
            onClick={() => this.setState({ error: null })}
            style={{ marginTop: 16, padding: "6px 16px", background: "#7c3aed",
              color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const api = () => window.pywebview?.api;

const DEFAULT_SERVER_CONFIG = {
  host: "0.0.0.0",
  port: 8443,
  username: "warden",
  password: "",
  use_ssl: true,
  read_only: true,
};

function App() {
  // ── Toast ───────────────────────────────────────────────────────────────
  const { toasts, toast } = useToast();

  // ── Core state ──────────────────────────────────────────────────────────
  const [theme,    setTheme]    = useState("dark");
  const [activeTab, setActiveTab] = useState("scan");
  const [drives,   setDrives]   = useState([]);
  const [drive,    setDrive]    = useState(null);
  const [settings, setSettings] = useState({});
  const [banner,   setBanner]   = useState("");
  const [auditOpen, setAuditOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // ── Scan state ──────────────────────────────────────────────────────────
  const [scanState,  setScanState]  = useState({ status: "idle", threats: [], files_scanned: 0, threat_count: 0, quarantine_count: 0 });
  const [quarantine, setQuarantine] = useState([]);

  // ── Server state ────────────────────────────────────────────────────────
  const [serverConfig, setServerConfig] = useState(DEFAULT_SERVER_CONFIG);
  const [serverState,  setServerState]  = useState({ status: "stopped" });
  const [tlsInfo, setTlsInfo] = useState({ fingerprint: "—", expires: "—", local_ip: "—" });

  // ── Format state ────────────────────────────────────────────────────────
  const [formatState, setFormatState] = useState({ status: "idle" });

  // ── Event dispatch (Python → JS) ────────────────────────────────────────
  useEffect(() => {
    window.__dispatch = (event) => {
      const { type, data } = event;
      switch (type) {
        case "drives:changed":
          setDrives(data);
          // If the selected drive is no longer in the list, deselect it
          setDrive(d => d && !data.find(x => x.path === d.path) ? null : d);
          break;
        case "drive:connected":
          setDrives(d => [...d.filter(x => x.path !== data.path), data]);
          setBanner(`USB connected: ${data.display_name}`);
          setTimeout(() => setBanner(""), 8000);
          break;
        case "drive:disconnected":
          setDrives(d => d.filter(x => x.path !== data.path));
          setDrive(d => d?.path === data.path ? null : d);
          setBanner(`USB removed: ${data.path}`);
          setTimeout(() => setBanner(""), 8000);
          break;
        case "scan:progress":
          setScanState(s => ({ ...s, status: "scanning", pct: data.pct, current_file: data.file }));
          break;
        case "scan:complete":
          setScanState(s => ({ ...s, status: "done", ...data }));
          loadQuarantine();
          break;
        case "scan:error":
          setScanState(s => ({ ...s, status: "error" }));
          alert(`Scan error: ${data.message}`);
          break;
        case "server:started":
          setServerState({ status: "running", url: data.url, password: data.password, ca_url: data.ca_url || "", mdns_active: !!data.mdns_active });
          break;
        case "server:stopped":
          setServerState({ status: "stopped" });
          break;
        case "server:error":
          setServerState({ status: "stopped" });
          alert(`Server error: ${data.message}`);
          break;
        case "format:status":
          setFormatState({ status: "formatting", message: data.message });
          break;
        case "format:complete":
          setFormatState({ status: "done" });
          setBanner("Drive formatted successfully.");
          setTimeout(() => setBanner(""), 8000);
          break;
        case "format:error":
          setFormatState({ status: "error" });
          alert(`Format error: ${data.message}`);
          break;
        case "rules:done":
          setBanner(data.ok ? "YARA rules updated." : "Rules update failed.");
          setTimeout(() => setBanner(""), 8000);
          break;
        default:
          break;
      }
    };
    return () => { window.__dispatch = null; };
  }, []);

  // ── Initial load ────────────────────────────────────────────────────────
  useEffect(() => {
    const init = async () => {
      try {
        const [s, d] = await Promise.all([
          api().get_settings(),
          api().list_drives(),
        ]);
        setSettings(s);
        setTheme(s.theme || "dark");
        setDrives(d);
        if (d.length) setDrive(d[0]);

        const q = await api().get_quarantine();
        setQuarantine(q);

        const tls = await api().get_tls_info();
        setTlsInfo(tls);
      } catch (err) {
        console.error("Warden init error:", err);
      }
    };

    if (api()) {
      init();
    } else {
      window.addEventListener("pywebviewready", init, { once: true });
    }

    return () => window.removeEventListener("pywebviewready", init);
  }, []);

  // ── Reset state when drive is removed ──────────────────────────────────
  useEffect(() => {
    if (!drive) {
      setScanState({ status: "idle", threats: [], files_scanned: 0, threat_count: 0, quarantine_count: 0 });
      setFormatState({ status: "idle" });
    }
  }, [drive]);

  // ── Drive selection ─────────────────────────────────────────────────────
  const handleDriveChange = useCallback((path) => {
    const d = drives.find(x => x.path === path) || null;
    setDrive(d);
  }, [drives]);

  const refreshDrives = useCallback(async () => {
    if (!api()) return;
    const d = await api().list_drives();
    setDrives(d);
    if (d.length && !drive) setDrive(d[0]);
  }, [drive]);

  // ── Theme ───────────────────────────────────────────────────────────────
  const toggleTheme = useCallback(() => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    api()?.set_theme(next);
  }, [theme]);

  // ── Scan ────────────────────────────────────────────────────────────────
  const startScan = useCallback(async (options) => {
    if (!drive || !api()) return;
    setScanState({ status: "scanning", threats: [], files_scanned: 0, threat_count: 0, quarantine_count: 0, pct: 0 });
    await api().start_scan(drive.path, options);
  }, [drive]);

  const cancelScan = useCallback(async () => {
    await api()?.cancel_scan();
    setScanState(s => ({ ...s, status: "idle" }));
  }, []);

  const loadQuarantine = useCallback(async () => {
    if (!api()) return;
    const q = await api().get_quarantine();
    setQuarantine(q);
  }, []);

  const quarantineFile = useCallback(async (threat) => {
    await api()?.quarantine_file(threat.path, threat.threat, threat.engine);
    setScanState(s => ({ ...s, threats: s.threats.filter(t => t.path !== threat.path) }));
    await loadQuarantine();
  }, [loadQuarantine]);

  const quarantineAll = useCallback(async () => {
    if (!api()) return;
    await api().quarantine_all(scanState.threats);
    setScanState(s => ({ ...s, threats: [] }));
    await loadQuarantine();
  }, [scanState.threats, loadQuarantine]);

  const restoreQuarantine = useCallback(async (id) => {
    const r = await api()?.restore_quarantine(id);
    if (r?.ok) {
      toast(`File restored to ${r.path}`, "info");
      await loadQuarantine();
    } else {
      toast(`Restore failed: ${r?.error}`, "error");
    }
  }, [loadQuarantine, toast]);

  const deleteQuarantine = useCallback(async (id) => {
    if (!confirm("Permanently delete this file from quarantine?")) return;
    const r = await api()?.delete_quarantine(id);
    if (r?.ok) {
      toast("File permanently deleted from quarantine.", "info");
      await loadQuarantine();
    } else {
      toast(`Delete failed: ${r?.error}`, "error");
    }
  }, [loadQuarantine, toast]);

  const vtHashCheck = useCallback(async (id) => {
    const r = await api()?.vt_hash_check(id);
    if (r?.ok) toast(`VT: ${JSON.stringify(r.result)}`, "info", 6000);
    else toast(`VT check failed: ${r?.error}`, "error");
  }, [toast]);

  const vtUpload = useCallback(async (id) => {
    const r = await api()?.vt_upload(id);
    if (r?.ok) toast("VT upload complete.", "info");
    else toast(`VT upload failed: ${r?.error}`, "error");
  }, [toast]);

  // ── Server ──────────────────────────────────────────────────────────────
  const startServer = useCallback(async () => {
    if (!drive || !api()) return;
    await api().start_server({ ...serverConfig, drive_path: drive.path });
  }, [drive, serverConfig]);

  const stopServer = useCallback(async () => {
    await api()?.stop_server();
  }, []);

  // ── Format ──────────────────────────────────────────────────────────────
  const startFormat = useCallback(async (config) => {
    if (!drive || !api()) return;
    const driveLetter = drive.path.replace(/[:\\/]/g, "").toUpperCase();
    const input = window.prompt(
      `You are about to FORMAT ${drive.path}\n\nFilesystem: ${config.filesystem}  ·  Label: ${config.label}\n\nThis will erase ALL data on the drive. Type the drive letter "${driveLetter}" to confirm:`
    );
    if (input?.trim().toUpperCase() !== driveLetter) return;
    setFormatState({ status: "formatting", message: "Starting…" });
    await api().start_format({ ...config, drive_path: drive.path });
  }, [drive]);

  const cancelFormat = useCallback(async () => {
    setFormatState({ status: "idle" });
  }, []);

  // ── Rules ───────────────────────────────────────────────────────────────
  const updateRules = useCallback(async () => {
    await api()?.update_rules();
    setBanner("Downloading YARA rules…");
  }, []);

  // ── Settings ────────────────────────────────────────────────────────────
  const refreshSettings = useCallback(async () => {
    if (!api()) return;
    const s = await api().get_settings();
    setSettings(s);
  }, []);

  const openSettings = useCallback(async () => {
    await refreshSettings();
    setSettingsOpen(true);
  }, [refreshSettings]);

  // ── Render ──────────────────────────────────────────────────────────────
  return (
    <div className={`warden ${theme === "light" ? "light" : ""}`}>
      <Header
        drives={drives}
        selectedDrive={drive}
        onDriveChange={handleDriveChange}
        theme={theme}
        onThemeToggle={toggleTheme}
        onRefresh={refreshDrives}
        onOpenSettings={openSettings}
      />
      <Tabs active={activeTab} onChange={setActiveTab} threatCount={scanState.threats.length}/>
      <Banner message={banner} onDismiss={() => setBanner("")}/>

      {activeTab === "scan" && (
        <ScanTab
          drive={drive}
          scanState={scanState}
          settings={settings}
          quarantine={quarantine}
          onScan={startScan}
          onCancel={cancelScan}
          onQuarantine={quarantineFile}
          onQuarantineAll={quarantineAll}
          onRestore={restoreQuarantine}
          onDelete={deleteQuarantine}
          onVtHash={vtHashCheck}
          onVtUpload={vtUpload}
        />
      )}
      {activeTab === "host" && (
        <HostTab
          drive={drive}
          serverState={serverState}
          config={serverConfig}
          setConfig={setServerConfig}
          onStart={startServer}
          onStop={stopServer}
          tlsInfo={tlsInfo}
          onToast={toast}
        />
      )}
      {activeTab === "format" && (
        <FormatTab
          drive={drive}
          formatState={formatState}
          settings={settings}
          onFormat={startFormat}
          onCancel={cancelFormat}
        />
      )}

      <StatusBar
        drive={drive}
        lastScan={scanState.timestamp}
      />
      {settingsOpen && (
        <SettingsModal
          settings={settings}
          onClose={() => setSettingsOpen(false)}
          onUpdateRules={updateRules}
          onOpenAuditLog={() => { setSettingsOpen(false); setAuditOpen(true); }}
          onToast={toast}
          onSettingsChanged={refreshSettings}
        />
      )}
      {auditOpen && <AuditLogModal onClose={() => setAuditOpen(false)} />}
      <Toaster toasts={toasts} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <ErrorBoundary>
    <App/>
  </ErrorBoundary>
);
