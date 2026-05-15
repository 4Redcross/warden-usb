// Scan tab

function SevPip({ level }) {
  const labels = { crit: "Critical", high: "High", med: "Medium", low: "Low" };
  return (
    <span className={`sev ${level}`}>
      <span className="pip">
        <i />
        <i />
        <i />
        <i />
      </span>
      {labels[level] || level}
    </span>
  );
}

function ScanControls({ drive, scanState, settings, onScan, onCancel }) {
  const { status, files_scanned, threat_count, quarantine_count, duration, timestamp, pct, current_file } =
    scanState;
  const scanning = status === "scanning";
  const done = status === "done";

  const [useClamav, setUseClamav] = React.useState(settings?.use_clamav ?? true);
  const [useYara, setUseYara] = React.useState(settings?.use_yara ?? true);
  const [useVt, setUseVt] = React.useState(settings?.use_vt_hash ?? false);

  const toggle = (val, set) => () => set(!val);

  return (
    <div className="card">
      <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "12px 14px" }}>
        {/* Drive info */}
        <div style={{ display: "flex", alignItems: "center", gap: 11, minWidth: 220 }}>
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: 8,
              background: "var(--accent-soft)",
              border: "1px solid var(--accent-line)",
              display: "grid",
              placeItems: "center",
              color: "var(--accent)",
              flex: "0 0 auto",
            }}
          >
            <Icon.drive style={{ width: 18, height: 18 }} />
          </div>
          <div>
            {drive ? (
              <>
                <div style={{ fontWeight: 600, fontSize: 13.5 }}>{drive.display_name}</div>
                <div style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 1 }}>
                  {drive.filesystem} · {drive.size_str} · {drive.free_str} free
                </div>
              </>
            ) : (
              <div style={{ color: "var(--text-muted)" }}>No drive selected</div>
            )}
          </div>
        </div>

        <div className="v-divider" />

        {/* Engine toggles */}
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
          <span className={`check ${useClamav ? "on" : ""}`} onClick={toggle(useClamav, setUseClamav)}>
            <span className="box" />
            ClamAV
          </span>
          <span className={`check ${useYara ? "on" : ""}`} onClick={toggle(useYara, setUseYara)}>
            <span className="box" />
            YARA rules
          </span>
          <span className={`check ${useVt ? "on" : ""}`} onClick={toggle(useVt, setUseVt)}>
            <span className="box" />
            VirusTotal hash lookup
          </span>
        </div>

        {/* Action buttons */}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
          {scanning ? (
            <button className="btn ghost" onClick={onCancel}>
              Cancel
            </button>
          ) : (
            <button
              className="btn ghost"
              onClick={() => onScan({ useClamav, useYara, useVt, quick: true })}
              disabled={!drive}
            >
              Quick scan
            </button>
          )}
          <button
            className="btn primary lg"
            disabled={!drive || scanning}
            onClick={() => onScan({ useClamav, useYara, useVt, quick: false })}
          >
            <Icon.scan style={{ width: 14, height: 14 }} />
            {scanning ? "Scanning…" : "Scan Drive"}
          </button>
        </div>
      </div>

      {/* Progress bar (visible while scanning) */}
      {scanning && (
        <div style={{ padding: "0 14px 8px" }}>
          <div
            style={{
              height: 4,
              background: "var(--surface-2)",
              borderRadius: 2,
              overflow: "hidden",
              marginBottom: 5,
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${pct || 0}%`,
                background: "var(--accent)",
                borderRadius: 2,
                transition: "width .3s",
              }}
            />
          </div>
          <div
            style={{
              fontSize: 11,
              color: "var(--text-muted)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {current_file || "Preparing…"}
          </div>
        </div>
      )}

      {/* Stats footer */}
      <div
        style={{
          borderTop: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          gap: 50,
          padding: "10px 14px",
          background: "var(--surface-deep)",
          borderRadius: "0 0 8px 8px",
        }}
      >
        <div className="kv">
          <span className="k">Files scanned</span>
          <span className="v">{(files_scanned || 0).toLocaleString()}</span>
        </div>
        {/* <div className="v-divider"/> */}
        <div className="kv">
          <span className="k">Threats</span>
          <span className="v" style={{ color: threat_count > 0 ? "var(--danger)" : undefined }}>
            {threat_count || 0}
          </span>
        </div>
        {/* <div className="v-divider"/> */}
        <div className="kv">
          <span className="k">Quarantined</span>
          <span className="v">{quarantine_count || 0}</span>
        </div>
        <div className="v-divider" style={{ margin: "0 -20px" }} />
        <div className="kv">
          <span className="k">Duration</span>
          <span className="v">{duration || "—"}</span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
          {done && threat_count > 0 && (
            <span className="badge threat">
              <span className="dot" />
              {threat_count} Threat{threat_count !== 1 ? "s" : ""} Detected
            </span>
          )}
          {done && threat_count === 0 && (
            <span className="badge clean">
              <span className="dot" />
              Clean
            </span>
          )}
          {timestamp && (
            <span style={{ color: "var(--text-muted)", fontSize: 11 }}>
              {done ? "completed" : "scanning"} {timestamp}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function ThreatsTable({ threats, onQuarantine, onQuarantineAll }) {
  if (!threats || threats.length === 0) return null;
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", minHeight: 0, flex: "1 1 0" }}>
      <div className="card-head">
        <Icon.alert style={{ width: 14, height: 14, color: "var(--danger)" }} />
        <h3>Detected Threats</h3>
        <span className="sub">
          {threats.length} item{threats.length !== 1 ? "s" : ""} · grouped by severity
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          <button className="btn sm" onClick={onQuarantineAll}>
            Quarantine all
          </button>
          <button className="btn sm ghost">Export report</button>
        </div>
      </div>
      <div style={{ overflow: "auto", flex: "1 1 0", minHeight: 0 }}>
        <table className="warden-tbl">
          <thead>
            <tr>
              <th style={{ width: "34%" }}>File</th>
              <th style={{ width: "26%" }}>Threat</th>
              <th style={{ width: "14%" }}>Engine</th>
              <th style={{ width: "16%" }}>Severity</th>
              <th style={{ width: "10%", textAlign: "right" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {threats.map((t, i) => (
              <tr key={i}>
                <td>
                  <div className="file">
                    <Icon.file />
                    <div>
                      <div>{t.file}</div>
                      <div className="path">{t.path}</div>
                    </div>
                  </div>
                </td>
                <td className="threat">{t.threat}</td>
                <td className="engine">{t.engine}</td>
                <td>
                  <SevPip level={t.sev} />
                </td>
                <td>
                  <div className="row-actions">
                    <button className="btn sm" onClick={() => onQuarantine(t)}>
                      Quarantine
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function QuarantineTable({ entries, onRestore, onDelete, onVtHash, onVtUpload }) {
  if (!entries || entries.length === 0) return null;
  const visible = entries.slice(0, 2);
  const extra = entries.length - visible.length;

  return (
    <div className="card">
      <div className="card-head">
        <Icon.lock style={{ width: 14, height: 14, color: "var(--text-dim)" }} />
        <h3>Quarantine</h3>
        <span className="sub">
          {entries.length} file{entries.length !== 1 ? "s" : ""} isolated on this machine · encrypted at-rest
        </span>
        <div style={{ marginLeft: "auto" }}>
          <button className="btn sm ghost">Open vault</button>
        </div>
      </div>
      <div>
        <table className="warden-tbl">
          <thead>
            <tr>
              <th style={{ width: "34%" }}>File</th>
              <th>Original threat</th>
              <th style={{ width: 70 }}>Size</th>
              <th style={{ width: 100 }}>Quarantined</th>
              <th style={{ width: 260, textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((q) => (
              <tr key={q.id}>
                <td>
                  <div className="file">
                    <Icon.file />
                    <div>
                      <div>{q.file}</div>
                      <div className="path">{q.path}</div>
                    </div>
                  </div>
                </td>
                <td style={{ color: "var(--text-dim)", fontSize: 12.5 }}>{q.threat}</td>
                <td className="engine">{q.size}</td>
                <td className="engine">{q.when}</td>
                <td>
                  <div className="row-actions">
                    <button className="btn sm" title="VirusTotal hash check" onClick={() => onVtHash(q.id)}>
                      <Icon.hash style={{ width: 12, height: 12 }} />
                      VT Hash
                    </button>
                    <button className="btn sm" title="VirusTotal upload" onClick={() => onVtUpload(q.id)}>
                      <Icon.upload style={{ width: 12, height: 12 }} />
                      VT Upload
                    </button>
                    <button className="btn sm" title="Restore" onClick={() => onRestore(q.id)}>
                      <Icon.restore style={{ width: 12, height: 12 }} />
                      Restore
                    </button>
                    <button
                      className="btn sm"
                      title="Delete permanently"
                      style={{ color: "var(--danger)" }}
                      onClick={() => onDelete(q.id)}
                    >
                      <Icon.trash style={{ width: 12, height: 12 }} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {extra > 0 && (
          <div
            style={{
              padding: "8px 14px",
              borderTop: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 11.5,
              color: "var(--text-muted)",
              background: "var(--surface-deep)",
              borderRadius: "0 0 8px 8px",
            }}
          >
            +{extra} more in quarantine
            <button className="btn sm ghost" style={{ marginLeft: "auto" }}>
              View all
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function ScanTab({
  drive,
  scanState,
  settings,
  quarantine,
  onScan,
  onCancel,
  onQuarantine,
  onQuarantineAll,
  onRestore,
  onDelete,
  onVtHash,
  onVtUpload,
}) {
  return (
    <div className="content">
      <ScanControls
        drive={drive}
        scanState={scanState}
        settings={settings}
        onScan={onScan}
        onCancel={onCancel}
      />
      <ThreatsTable
        threats={scanState.threats}
        onQuarantine={onQuarantine}
        onQuarantineAll={onQuarantineAll}
      />
      <QuarantineTable
        entries={quarantine}
        onRestore={onRestore}
        onDelete={onDelete}
        onVtHash={onVtHash}
        onVtUpload={onVtUpload}
      />
    </div>
  );
}

window.ScanTab = ScanTab;
