// Warden — Format tab.

function FormatTab() {
  return (
    <div className="content">
      <div className="card">
        <div className="card-body" style={{display:"flex",alignItems:"center",gap:18}}>
          <div style={{width:42,height:42,borderRadius:9,background:"var(--accent-soft)",border:"1px solid var(--accent-line)",display:"grid",placeItems:"center",color:"var(--accent)"}}>
            <Icon.drive style={{width:20,height:20}}/>
          </div>
          <div style={{flex:1}}>
            <div style={{fontWeight:600,fontSize:14}}>SanDisk Cruzer (D:)</div>
            <div style={{color:"var(--text-muted)",fontSize:11.5,marginTop:2,display:"flex",gap:14}}>
              <span>FAT32</span><span>·</span>
              <span>64 GB total</span><span>·</span>
              <span>38.2 GB used</span><span>·</span>
              <span>Serial AB12-9F44</span>
            </div>
          </div>
          <span className="badge muted"><Icon.alert style={{width:11,height:11}}/> Will erase all data</span>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <Icon.disk style={{width:14,height:14,color:"var(--text-dim)"}}/>
          <h3>Format options</h3>
          <span className="sub">Choose a filesystem and label for the drive</span>
        </div>
        <div className="card-body" style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:14}}>
          <div className="field">
            <label>Filesystem</label>
            <div style={{display:"flex",gap:6}}>
              {["NTFS","FAT32","exFAT"].map((f, i) => (
                <div key={f} style={{
                  flex:1, height:38, borderRadius:7, border:"1px solid " + (i === 2 ? "var(--accent)" : "var(--border)"),
                  background: i === 2 ? "var(--accent-soft)" : "var(--surface-2)",
                  color: i === 2 ? "var(--text)" : "var(--text-dim)",
                  display:"grid", placeItems:"center", fontSize:12.5, fontWeight: i === 2 ? 600 : 500
                }}>{f}</div>
              ))}
            </div>
          </div>
          <div className="field">
            <label>Volume label</label>
            <div className="input focused"><span>WARDEN-SECURE</span></div>
          </div>
          <div className="field">
            <label>Allocation unit</label>
            <div className="input"><span>Default (128 KB)</span><Icon.caret style={{width:12,height:12,color:"var(--text-muted)",marginLeft:"auto"}}/></div>
          </div>

          <div style={{gridColumn:"1 / -1",display:"flex",gap:24,paddingTop:4}}>
            <label className="check on"><span className="box"/>Quick format</label>
            <label className="check"><span className="box"/>Verify after format</label>
            <label className="check"><span className="box"/>Write Warden recovery key to drive</label>
          </div>
        </div>
      </div>

      <div className="warning-banner">
        <div className="ico">!</div>
        <div style={{flex:1}}>
          <h4>This will permanently erase everything on D:</h4>
          <p>
            64 GB of data — including the 4 quarantined files — will be wiped. Quick format does not securely wipe blocks;
            for a forensic wipe disable the option above. This action cannot be undone.
          </p>
        </div>
        <label className="check" style={{flex:"0 0 auto",marginTop:2}}><span className="box"/>I understand</label>
      </div>

      <div style={{display:"flex",alignItems:"center",gap:10,marginTop:"auto"}}>
        <span style={{fontSize:11.5,color:"var(--text-muted)"}}>
          Estimated time: <b style={{color:"var(--text-dim)"}}>~38 seconds</b> with quick format enabled
        </span>
        <button className="btn ghost" style={{marginLeft:"auto"}}>Cancel</button>
        <button className="btn danger lg" disabled style={{opacity:.55,cursor:"not-allowed"}}>
          <Icon.alert style={{width:14,height:14}}/>
          Format Drive
        </button>
      </div>
    </div>
  );
}

Object.assign(window, { FormatTab });
