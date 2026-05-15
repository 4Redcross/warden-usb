// Warden — Host tab.
// Single card morphs from config (mode === "config") to connected (mode === "connected").

function QRMock() {
  // Deterministic, simple QR-ish bitmap (21×21) — three locator squares + body noise.
  const cells = Array.from({length: 21*21}, (_, i) => {
    const x = i % 21, y = Math.floor(i / 21);
    // Corner finders
    const inFinder = (cx, cy) => Math.abs(x - cx) <= 3 && Math.abs(y - cy) <= 3 &&
                                 !(Math.abs(x - cx) === 2 && Math.abs(y - cy) <= 2 && Math.abs(y - cy) >= 0 && (Math.abs(x - cx) === 2 || Math.abs(y - cy) === 2)) ||
                                 ((Math.abs(x - cx) === 3 || Math.abs(y - cy) === 3) && Math.abs(x - cx) <= 3 && Math.abs(y - cy) <= 3) ||
                                 (Math.abs(x - cx) <= 1 && Math.abs(y - cy) <= 1);
    if (inFinder(3,3) || inFinder(17,3) || inFinder(3,17)) {
      const dx = x <= 6 ? x - 3 : x >= 14 ? x - 17 : null;
      const dy = y <= 6 ? y - 3 : y >= 14 ? y - 17 : null;
      if (dx === null || dy === null) {} else {
        const a = Math.abs(dx), b = Math.abs(dy);
        if (a === 3 || b === 3) return true;
        if (a <= 1 && b <= 1) return true;
        return false;
      }
    }
    // Pseudo-random body
    return ((x * 7 + y * 13 + x*y) % 5) < 2;
  });
  return (
    <div className="qr">
      {cells.map((on, i) => <i key={i} className={on ? "" : "off"}/>)}
    </div>
  );
}

function HostConfig() {
  return (
    <div className="card">
      <div className="card-head">
        <Icon.server style={{width:14,height:14,color:"var(--text-dim)"}}/>
        <h3>WebDAV Server</h3>
        <span className="sub">Share the selected drive read-only or read-write over your local network</span>
        <span className="badge muted" style={{marginLeft:"auto"}}><span className="dot" style={{background:"var(--text-muted)"}}/>Stopped</span>
      </div>
      <div className="card-body" style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:18}}>
        <div className="field">
          <label>Bind address</label>
          <div className="input">
            <span className="mono" style={{color:"var(--text-dim)"}}>0.0.0.0</span>
            <span className="mono" style={{color:"var(--text-muted)"}}>:</span>
            <span className="mono">8443</span>
            <Icon.caret style={{width:12,height:12,color:"var(--text-muted)",marginLeft:"auto"}}/>
          </div>
        </div>
        <div className="field">
          <label>Mode</label>
          <div className="input">
            <span>Read-only · safer</span>
            <Icon.caret style={{width:12,height:12,color:"var(--text-muted)",marginLeft:"auto"}}/>
          </div>
        </div>
        <div className="field">
          <label>Username</label>
          <div className="input focused"><span>warden</span></div>
        </div>
        <div className="field">
          <label>Password</label>
          <div className="input" style={{paddingRight:4}}>
            <span className="mono">•••••••••••••••</span>
            <button className="btn sm" style={{marginLeft:"auto"}}><Icon.key style={{width:12,height:12}}/>Generate</button>
          </div>
        </div>

        <div style={{gridColumn:"1 / -1",display:"flex",alignItems:"center",gap:24,paddingTop:6}}>
          <label className="check on"><span className="box"/>Localhost only (127.0.0.1)</label>
          <label className="check"><span className="box"/>Allow write access</label>
          <div style={{display:"flex",alignItems:"center",gap:8,marginLeft:"auto"}}>
            <span style={{fontSize:12.5,color:"var(--text)"}}>HTTPS</span>
            <span className="toggle on"/>
            <span style={{fontSize:11.5,color:"var(--text-muted)"}}>self-signed cert</span>
          </div>
        </div>
      </div>
      <div style={{padding:"12px 16px",borderTop:"1px solid var(--border)",display:"flex",alignItems:"center",gap:10}}>
        <span style={{fontSize:11.5,color:"var(--text-muted)"}}>
          <Icon.lock style={{width:11,height:11,verticalAlign:"-1px",marginRight:4}}/>
          Server runs only while Warden is open. Credentials are session-scoped.
        </span>
        <button className="btn primary lg" style={{marginLeft:"auto"}}>
          <Icon.server style={{width:13,height:13}}/>
          Start Server
        </button>
      </div>
    </div>
  );
}

function HostConnected() {
  const url = "https://192.168.1.42:8443/warden/D";
  return (
    <div className="card">
      <div className="card-head">
        <Icon.server style={{width:14,height:14,color:"var(--highlight)"}}/>
        <h3>WebDAV Server</h3>
        <span className="sub">Sharing <b style={{color:"var(--text)"}}>SanDisk Cruzer (D:)</b> read-only · 2m 14s uptime</span>
        <span className="badge clean" style={{marginLeft:"auto"}}><span className="dot"/>Running</span>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 160px",gap:18,padding:"16px"}}>
        <div style={{display:"flex",flexDirection:"column",gap:10}}>
          <div className="field">
            <label>WebDAV URL</label>
            <div className="input mono" style={{height:42,fontSize:13.5,color:"var(--highlight)"}}>
              {url}
              <button className="btn sm ghost" style={{marginLeft:"auto"}}><Icon.copy style={{width:12,height:12}}/>Copy</button>
            </div>
          </div>
          <div style={{display:"flex",gap:10}}>
            <div className="field" style={{flex:1}}>
              <label>Username</label>
              <div className="input mono">warden</div>
            </div>
            <div className="field" style={{flex:1}}>
              <label>Password</label>
              <div className="input mono" style={{paddingRight:4}}>
                <span>•••••••••••••••</span>
                <button className="btn sm" style={{marginLeft:"auto"}}><Icon.eye style={{width:12,height:12}}/></button>
              </div>
            </div>
          </div>
        </div>
        <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:8}}>
          <QRMock/>
          <span style={{fontSize:11,color:"var(--text-muted)"}}>Scan with phone</span>
        </div>
      </div>

      <div style={{borderTop:"1px solid var(--border)",padding:"14px 16px"}}>
        <div style={{fontSize:11,letterSpacing:".08em",textTransform:"uppercase",color:"var(--text-muted)",marginBottom:10}}>How to connect</div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12}}>
          {[
            {ico:<Icon.win/>, name:"Windows", body:<>Open File Explorer → right-click <b>This PC</b> → <b>Map network drive…</b> → paste the URL above.</>},
            {ico:<Icon.apple/>, name:"macOS",   body:<>In Finder, press <span className="mono">⌘K</span> and enter the URL. macOS will prompt for the credentials.</>},
            {ico:<Icon.android/>, name:"Android", body:<>Use a WebDAV client such as Solid Explorer or Cx. Scan the QR code, accept the cert, and you're in.</>},
          ].map(p => (
            <div key={p.name} style={{background:"var(--surface-2)",border:"1px solid var(--border)",borderRadius:7,padding:"11px 12px",display:"flex",gap:10,alignItems:"flex-start"}}>
              <div style={{width:24,height:24,borderRadius:5,background:"var(--surface-3)",color:"var(--text-dim)",display:"grid",placeItems:"center",flex:"0 0 auto"}}>
                {React.cloneElement(p.ico, {style:{width:14,height:14}})}
              </div>
              <div>
                <div style={{fontWeight:600,fontSize:12.5,marginBottom:3}}>{p.name}</div>
                <div style={{fontSize:11.5,color:"var(--text-dim)",lineHeight:1.55}}>{p.body}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{padding:"12px 16px",borderTop:"1px solid var(--border)",display:"flex",alignItems:"center",gap:14}}>
        <div style={{display:"flex",alignItems:"center",gap:8}}>
          <span style={{width:7,height:7,borderRadius:"50%",background:"var(--success)",boxShadow:"0 0 8px var(--success)"}}/>
          <span style={{fontSize:12}}><b>2 clients connected</b> · 14.3 MB transferred</span>
        </div>
        <button className="btn ghost" style={{marginLeft:"auto"}}>Show access log</button>
        <button className="btn danger">Stop Server</button>
      </div>
    </div>
  );
}

function HostTab({ mode }) {
  return (
    <div className="content">
      {mode === "connected" ? <HostConnected/> : <HostConfig/>}
      <div style={{display:"flex",gap:12}}>
        <div className="card" style={{flex:1,padding:"12px 14px",display:"flex",alignItems:"center",gap:10}}>
          <Icon.shield style={{width:16,height:16,color:"var(--accent)"}}/>
          <div style={{fontSize:12}}>
            <div style={{fontWeight:600}}>Why share read-only?</div>
            <div style={{color:"var(--text-muted)",marginTop:2}}>Prevents remote clients from writing back ransomware or altering the drive.</div>
          </div>
        </div>
        <div className="card" style={{flex:1,padding:"12px 14px",display:"flex",alignItems:"center",gap:10}}>
          <Icon.lock style={{width:16,height:16,color:"var(--highlight)"}}/>
          <div style={{fontSize:12}}>
            <div style={{fontWeight:600}}>TLS fingerprint</div>
            <div style={{color:"var(--text-muted)",marginTop:2}} className="mono">SHA-256 · 7A:9B:43:08:FE:21:…</div>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { HostTab });
