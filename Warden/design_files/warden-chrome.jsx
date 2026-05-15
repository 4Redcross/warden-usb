// Warden app chrome — title bar, header, tabs, status bar.
// `activeTab` is controlled from the outside so artboards can preset a tab.

function TitleBar() {
  return (
    <div className="titlebar">
      <div className="dots"><i/><i/><i/></div>
      <div className="title">Warden — USB Security</div>
      <div className="win">— ☐ ✕</div>
    </div>
  );
}

function Header({ drive, theme }) {
  return (
    <div className="header">
      <div className="brand">
        <div className="logo"><Icon.shield/></div>
        <div className="name">Warden <small>v2.4.1</small></div>
      </div>
      <div className="drive-selector">
        <span className="dot"/>
        <Icon.drive style={{width:14,height:14,color:"var(--text-dim)"}}/>
        <span>{drive.label}</span>
        <span className="meta">{drive.mount} · {drive.fs} · {drive.size}</span>
        <Icon.caret className="caret" style={{width:14,height:14}}/>
      </div>
      <div className="actions">
        <button className="iconbtn" title="Refresh"><Icon.refresh style={{width:14,height:14}}/></button>
        <button className="iconbtn" title="Toggle theme">
          {theme === "light"
            ? <Icon.sun style={{width:14,height:14}}/>
            : <Icon.moon style={{width:14,height:14}}/>}
        </button>
        <button className="btn" title="Update Rules">
          <Icon.download style={{width:13,height:13}}/>
          Update Rules
        </button>
      </div>
    </div>
  );
}

function Tabs({ active, onChange, threatCount }) {
  const tabs = [
    { id: "scan",   label: "Scan",   icon: <Icon.scan/> },
    { id: "host",   label: "Host",   icon: <Icon.server/> },
    { id: "format", label: "Format", icon: <Icon.disk/> },
  ];
  return (
    <div className="tabs">
      {tabs.map(t => (
        <div key={t.id} className={`tab ${active === t.id ? "active" : ""}`} onClick={() => onChange && onChange(t.id)}>
          {t.icon}
          <span>{t.label}</span>
          {t.id === "scan" && threatCount > 0 && <span className="count">{threatCount}</span>}
        </div>
      ))}
    </div>
  );
}

function StatusBar({ drive, lastScan }) {
  return (
    <div className="statusbar">
      <span><b>Drive:</b> {drive.mount} ({drive.label})</span>
      <span className="sep"/>
      <span><b>Filesystem:</b> {drive.fs}</span>
      <span className="sep"/>
      <span><b>Capacity:</b> {drive.used} / {drive.size}</span>
      <div className="right">
        {lastScan && <span>Last scan: <b>{lastScan}</b></span>}
        <span className="sep"/>
        <span style={{display:"inline-flex",alignItems:"center",gap:6}}>
          <span style={{width:6,height:6,borderRadius:"50%",background:"var(--highlight)"}}/>
          Engines ready
        </span>
      </div>
    </div>
  );
}

Object.assign(window, { TitleBar, Header, Tabs, StatusBar });
