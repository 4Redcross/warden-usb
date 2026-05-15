// Format tab

function FormatTab({ drive, formatState, settings, onFormat, onCancel }) {
  const fsList = settings?.filesystems || ["NTFS", "FAT32", "exFAT"];
  const [fs, setFs] = React.useState(fsList[0]);
  const [label, setLabel] = React.useState("");
  const [alloc, setAlloc] = React.useState("Default");
  const [quick, setQuick] = React.useState(true);
  const [verify, setVerify] = React.useState(false);
  const [understood, setUnderstood] = React.useState(false);

  const formatting = formatState?.status === "formatting";
  const allocList = ["Default", "4 KB", "8 KB", "16 KB", "32 KB", "64 KB", "128 KB"];

  // Reset understood when drive changes
  React.useEffect(() => {
    setUnderstood(false);
  }, [drive?.path]);

  const canFormat = drive && understood && !formatting;

  const handleFormat = () => {
    if (!canFormat) return;
    onFormat({
      drive_path: drive.path,
      filesystem: fs,
      label: label || drive.label || "USB Drive",
      alloc_unit: alloc,
      quick_format: quick,
      verify_after: verify,
    });
  };

  return (
    <div className="content">
      {/* Drive info card */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "12px 14px" }}>
          <div
            style={{
              width: 42,
              height: 42,
              borderRadius: 9,
              background: "var(--accent-soft)",
              border: "1px solid var(--accent-line)",
              display: "grid",
              placeItems: "center",
              color: "var(--accent)",
              flex: "0 0 auto",
            }}
          >
            <Icon.drive style={{ width: 20, height: 20 }} />
          </div>
          <div style={{ flex: 1 }}>
            {drive ? (
              <>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{drive.display_name}</div>
                <div
                  style={{
                    color: "var(--text-muted)",
                    fontSize: 11.5,
                    marginTop: 2,
                    display: "flex",
                    gap: 10,
                    flexWrap: "wrap",
                  }}
                >
                  <span>{drive.filesystem}</span>
                  <span>·</span>
                  <span>{drive.size_str} total</span>
                  <span>·</span>
                  <span>{drive.free_str} free</span>
                </div>
              </>
            ) : (
              <div style={{ color: "var(--text-muted)" }}>No drive selected</div>
            )}
          </div>
          {drive && (
            <span className="badge warn">
              <Icon.alert style={{ width: 11, height: 11 }} />
              Will erase all data
            </span>
          )}
        </div>
      </div>

      {/* Format options card */}
      <div className="card">
        <div className="card-head">
          <Icon.disk style={{ width: 14, height: 14, color: "var(--text-dim)" }} />
          <h3>Format options</h3>
          <span className="sub">Choose a filesystem and label for the drive</span>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, padding: 14 }}>
          {/* Filesystem toggles */}
          <div className="field">
            <label>Filesystem</label>
            <div style={{ display: "flex", gap: 6 }}>
              {fsList.map((f) => (
                <button
                  key={f}
                  onClick={() => setFs(f)}
                  style={{
                    flex: 1,
                    height: 38,
                    borderRadius: 7,
                    border: `1px solid ${f === fs ? "var(--accent)" : "var(--border)"}`,
                    background: f === fs ? "var(--accent-soft)" : "var(--surface-2)",
                    color: f === fs ? "var(--text)" : "var(--text-dim)",
                    fontSize: 12.5,
                    fontWeight: f === fs ? 600 : 500,
                    cursor: "pointer",
                    transition: "all .15s",
                  }}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Volume label */}
          <div className="field">
            <label>Volume label</label>
            <input
              type="text"
              value={label}
              placeholder={drive?.label || "WARDEN-SECURE"}
              maxLength={32}
              onChange={(e) => setLabel(e.target.value.toUpperCase())}
            />
          </div>

          {/* Allocation unit */}
          <div className="field">
            <label>Allocation unit</label>
            <select value={alloc} onChange={(e) => setAlloc(e.target.value)}>
              {allocList.map((a) => (
                <option key={a}>{a}</option>
              ))}
            </select>
          </div>

          {/* Checkboxes row */}
          <div style={{ gridColumn: "1 / -1", display: "flex", gap: 24, paddingTop: 4, flexWrap: "wrap" }}>
            <span className={`check ${quick ? "on" : ""}`} onClick={() => setQuick((q) => !q)}>
              <span className="box" />
              Quick format
            </span>
            <span className={`check ${verify ? "on" : ""}`} onClick={() => setVerify((v) => !v)}>
              <span className="box" />
              Verify after format
            </span>
          </div>
        </div>
      </div>

      {/* Warning banner */}
      <div className="warning-banner">
        <div className="ico">!</div>
        <div style={{ flex: 1 }}>
          <h4 style={{ color: "var(--warning)" }}>
            {drive
              ? `This will permanently erase everything on ${drive.path.replace(/[\\/]+$/, "")}`
              : "This will permanently erase everything on the selected drive"}
          </h4>
          <p>
            {drive ? `${drive.size_str} of data` : "All data"} will be wiped. Quick format does not securely
            wipe blocks; disable it above for a forensic wipe. This action cannot be undone.
          </p>
        </div>
        <span
          className={`check ${understood ? "on" : ""}`}
          style={{ flex: "0 0 auto", marginTop: 2 }}
          onClick={() => setUnderstood((u) => !u)}
        >
          <span className="box" />I understand
        </span>
      </div>

      {/* Progress (during format) */}
      {formatting && (
        <div>
          <div
            style={{
              height: 4,
              background: "var(--surface-2)",
              borderRadius: 2,
              overflow: "hidden",
              marginBottom: 6,
            }}
          >
            <div
              style={{
                height: "100%",
                width: "100%",
                background: "var(--accent)",
                borderRadius: 2,
                animation: "indeterminate 1.5s infinite",
              }}
            />
          </div>
          <div style={{ fontSize: 11.5, color: "var(--text-muted)" }}>
            {formatState.message || "Formatting…"}
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: "auto", paddingTop: 4 }}>
        <span className="sub">
          Estimated time:{" "}
          <b style={{ color: "var(--text-dim)" }}>
            ~{quick ? "30" : Math.max(30, Math.round(((drive?.total_bytes || 0) / 1e9) * 10))} seconds
          </b>{" "}
          with quick format {quick ? "enabled" : "disabled"}
        </span>
        <button
          className="btn ghost"
          style={{ marginLeft: "auto" }}
          onClick={onCancel}
          disabled={!formatting}
        >
          Cancel
        </button>
        <button className="btn danger lg" disabled={!canFormat} onClick={handleFormat}>
          <Icon.alert style={{ width: 14, height: 14 }} />
          Format Drive
        </button>
      </div>
    </div>
  );
}

window.FormatTab = FormatTab;
