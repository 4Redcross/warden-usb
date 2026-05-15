// Warden — Scan tab.
// Two layout variants: "table" (default — dense, sysadmin-style) and "cards"
// (threat-first stack, easier scanning).

const THREATS = [
  { file: "autorun.inf",                      path: "/D:/autorun.inf",                       threat: "Trojan.LNK.Agent.Gen", engine: "ClamAV",       sev: "crit" },
  { file: "setup-tool.exe",                   path: "/D:/installers/setup-tool.exe",         threat: "Win32.Stealer.RedLine", engine: "VirusTotal",  sev: "crit" },
  { file: "invoice_april.pdf.exe",            path: "/D:/Documents/invoice_april.pdf.exe",   threat: "MSIL.Backdoor.Quasar",  engine: "YARA",         sev: "high" },
  { file: "macro_template.xlsm",              path: "/D:/Work/macro_template.xlsm",          threat: "X97M.Downloader.AGT",   engine: "ClamAV",       sev: "high" },
  { file: "keyboard_helper.dll",              path: "/D:/tools/keyboard_helper.dll",         threat: "Generic.Keylogger.b",   engine: "YARA",         sev: "med"  },
  { file: "screensaver.scr",                  path: "/D:/themes/screensaver.scr",            threat: "PUA.Win.Adware.Bundler", engine: "ClamAV",      sev: "med"  },
  { file: "cracked_keygen.zip",               path: "/D:/_old/cracked_keygen.zip",           threat: "HEUR.RiskTool.KeyGen",  engine: "Heuristic",    sev: "low"  },
];

const QUARANTINE = [
  { file: "ransom-note.html",       path: "/D:/Desktop/ransom-note.html",      orig: "Crypto.Locker.Gen",       size: "12 KB",   when: "2 min ago",   sev: "crit" },
  { file: "wsh-loader.js",          path: "/D:/scripts/wsh-loader.js",         orig: "JS.Loader.Emotet",        size: "44 KB",   when: "2 min ago",   sev: "high" },
  { file: "fake-driver.sys",        path: "/D:/drivers/fake-driver.sys",       orig: "Win64.Rootkit.Necurs",    size: "1.4 MB",  when: "Yesterday",   sev: "crit" },
  { file: "browser_helper.exe",     path: "/D:/utils/browser_helper.exe",      orig: "Adware.Win32.Ginyas",     size: "780 KB",  when: "Yesterday",   sev: "med"  },
];

function ScanControls() {
  return (
    <div className="card">
      <div style={{display:"flex",alignItems:"center",gap:16,padding:"12px 14px"}}>
        <div style={{display:"flex",alignItems:"center",gap:11,minWidth:220}}>
          <div style={{width:38,height:38,borderRadius:8,background:"var(--accent-soft)",border:"1px solid var(--accent-line)",display:"grid",placeItems:"center",color:"var(--accent)",flex:"0 0 auto"}}>
            <Icon.drive style={{width:18,height:18}}/>
          </div>
          <div>
            <div style={{fontWeight:600,fontSize:13.5}}>SanDisk Cruzer (D:)</div>
            <div style={{color:"var(--text-muted)",fontSize:11,marginTop:1}}>FAT32 · 64 GB · 38.2 GB used</div>
          </div>
        </div>

        <div className="v-divider"/>

        <div style={{display:"flex",gap:14,flexWrap:"wrap"}}>
          <span className="check on"><span className="box"/>ClamAV</span>
          <span className="check on"><span className="box"/>YARA rules</span>
          <span className="check on"><span className="box"/>VirusTotal hash lookup</span>
        </div>

        <div style={{marginLeft:"auto",display:"flex",alignItems:"center",gap:10}}>
          <button className="btn ghost">Quick scan</button>
          <button className="btn primary lg">
            <Icon.scan style={{width:14,height:14}}/>
            Scan Drive
          </button>
        </div>
      </div>
      <div style={{borderTop:"1px solid var(--border)",display:"flex",alignItems:"center",gap:24,padding:"10px 14px",background:"var(--surface-deep)",borderRadius:"0 0 8px 8px"}}>
        <div className="kv"><span className="k">Files scanned</span><span className="v" style={{fontSize:15}}>12,847</span></div>
        <div className="v-divider"/>
        <div className="kv"><span className="k">Threats</span><span className="v" style={{fontSize:15,color:"var(--danger)"}}>7</span></div>
        <div className="v-divider"/>
        <div className="kv"><span className="k">Quarantined</span><span className="v" style={{fontSize:15}}>4</span></div>
        <div className="v-divider"/>
        <div className="kv"><span className="k">Duration</span><span className="v" style={{fontSize:15}}>02:14<small>min</small></span></div>
        <div style={{marginLeft:"auto",display:"flex",alignItems:"center",gap:10}}>
          <span className="badge threat"><span className="dot"/>7 Threats Detected</span>
          <span style={{color:"var(--text-muted)",fontSize:11}}>completed 2 min ago</span>
        </div>
      </div>
    </div>
  );
}

function SevPip({ level }) {
  return (
    <span className={`sev ${level}`}>
      <span className="pip"><i/><i/><i/><i/></span>
      {{crit:"Critical",high:"High",med:"Medium",low:"Low"}[level]}
    </span>
  );
}

function ThreatsTable() {
  return (
    <div className="card" style={{display:"flex",flexDirection:"column",minHeight:0,flex:"1 1 0"}}>
      <div className="card-head">
        <Icon.alert style={{width:14,height:14,color:"var(--danger)"}}/>
        <h3>Detected Threats</h3>
        <span className="sub">7 items · grouped by severity</span>
        <div style={{marginLeft:"auto",display:"flex",gap:6}}>
          <button className="btn sm">Quarantine all</button>
          <button className="btn sm ghost">Export report</button>
        </div>
      </div>
      <div style={{overflow:"auto",flex:"1 1 0",minHeight:0}}>
        <table className="warden-tbl">
          <thead>
            <tr>
              <th style={{width:"34%"}}>File</th>
              <th style={{width:"26%"}}>Threat</th>
              <th style={{width:"14%"}}>Engine</th>
              <th style={{width:"16%"}}>Severity</th>
              <th style={{width:"10%",textAlign:"right"}}>Action</th>
            </tr>
          </thead>
          <tbody>
            {THREATS.map(t => (
              <tr key={t.file}>
                <td>
                  <div className="file">
                    <Icon.file/>
                    <div>
                      <div>{t.file}</div>
                      <div className="path">{t.path}</div>
                    </div>
                  </div>
                </td>
                <td className="threat">{t.threat}</td>
                <td className="engine">{t.engine}</td>
                <td><SevPip level={t.sev}/></td>
                <td>
                  <div className="row-actions">
                    <button className="btn sm">Quarantine</button>
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

function ThreatsCards() {
  return (
    <div className="card" style={{display:"flex",flexDirection:"column",minHeight:0,flex:"1 1 0"}}>
      <div className="card-head">
        <Icon.alert style={{width:14,height:14,color:"var(--danger)"}}/>
        <h3>Detected Threats</h3>
        <span className="sub">Sorted by severity · 7 items</span>
        <div style={{marginLeft:"auto",display:"flex",gap:6}}>
          <button className="btn sm">Quarantine all</button>
        </div>
      </div>
      <div style={{padding:"12px 14px",display:"flex",flexDirection:"column",gap:8,overflow:"auto",flex:"1 1 0",minHeight:0}}>
        {THREATS.map(t => (
          <div key={t.file} className={`threat-card ${t.sev}`}>
            <div className="icon-wrap"><Icon.bug style={{width:18,height:18}}/></div>
            <div className="main">
              <div className="top">
                <span className="threat-name">{t.threat}</span>
                <SevPip level={t.sev}/>
                <span className="badge muted" style={{fontWeight:500}}>{t.engine}</span>
              </div>
              <div className="path">{t.path}</div>
            </div>
            <div style={{display:"flex",gap:6}}>
              <button className="btn sm">Quarantine</button>
              <button className="btn sm ghost">Details</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function QuarantineTable({ compact }) {
  return (
    <div className="card">
      <div className="card-head">
        <Icon.lock style={{width:14,height:14,color:"var(--text-dim)"}}/>
        <h3>Quarantine</h3>
        <span className="sub">{QUARANTINE.length} files isolated · encrypted at-rest</span>
        <div style={{marginLeft:"auto"}}>
          <button className="btn sm ghost">Open vault</button>
        </div>
      </div>
      <div>
        <table className="warden-tbl">
          <thead>
            <tr>
              <th style={{width:"36%"}}>File</th>
              <th>Original threat</th>
              <th style={{width:80}}>Size</th>
              <th style={{width:110}}>Quarantined</th>
              <th style={{width:280,textAlign:"right"}}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {(compact ? QUARANTINE.slice(0,1) : QUARANTINE).map(q => (
              <tr key={q.file}>
                <td>
                  <div className="file">
                    <Icon.file/>
                    <div>
                      <div>{q.file}</div>
                      <div className="path">{q.path}</div>
                    </div>
                  </div>
                </td>
                <td className="threat" style={{color:"var(--text-dim)",fontWeight:400}}>{q.orig}</td>
                <td className="engine">{q.size}</td>
                <td className="engine">{q.when}</td>
                <td>
                  <div className="row-actions">
                    <button className="btn sm" title="VirusTotal hash check"><Icon.hash style={{width:12,height:12}}/>VT Hash</button>
                    <button className="btn sm" title="VirusTotal upload"><Icon.upload style={{width:12,height:12}}/>VT Upload</button>
                    <button className="btn sm" title="Restore"><Icon.restore style={{width:12,height:12}}/>Restore</button>
                    <button className="btn sm" title="Delete" style={{color:"var(--danger)"}}><Icon.trash style={{width:12,height:12}}/></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {compact && QUARANTINE.length > 1 && (
          <div style={{padding:"8px 14px",borderTop:"1px solid var(--border)",display:"flex",alignItems:"center",gap:6,fontSize:11.5,color:"var(--text-muted)",background:"var(--surface-deep)",borderRadius:"0 0 8px 8px"}}>
            +{QUARANTINE.length - 1} more in quarantine
            <button className="btn sm ghost" style={{marginLeft:"auto"}}>View all</button>
          </div>
        )}
      </div>
    </div>
  );
}

function ScanTab() {
  return (
    <div className="content">
      <ScanControls/>
      <ThreatsTable/>
      <QuarantineTable compact={true}/>
    </div>
  );
}

Object.assign(window, { ScanTab });
