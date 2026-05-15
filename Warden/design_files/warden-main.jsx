// Warden — assembled app shell + design canvas of variants.

const DRIVE = {
  label: "SanDisk Cruzer",
  mount: "D:\\",
  fs: "FAT32",
  size: "64.0 GB",
  used: "38.2 GB",
};

function Warden({ tab = "scan", hostMode = "config", theme = "dark" }) {
  return (
    <div className={"warden" + (theme === "light" ? " light" : "")}>
      <TitleBar/>
      <Header drive={DRIVE} theme={theme}/>
      <Tabs active={tab} threatCount={7}/>
      {tab === "scan"   && <ScanTab/>}
      {tab === "host"   && <HostTab mode={hostMode}/>}
      {tab === "format" && <FormatTab/>}
      <StatusBar drive={DRIVE} lastScan="May 13, 14:22"/>
    </div>
  );
}

function App() {
  const W = 1100, H = 760;
  return (
    <DesignCanvas>
      <DCSection
        id="scan"
        title="Scan tab"
        subtitle="Primary surface — drive scanning, threat triage, quarantine. Table layout (dark & light)."
      >
        <DCArtboard id="scan-dark" label="Dark · default" width={W} height={H}>
          <Warden tab="scan" theme="dark"/>
        </DCArtboard>
        <DCArtboard id="scan-light" label="Light · same palette" width={W} height={H}>
          <Warden tab="scan" theme="light"/>
        </DCArtboard>
      </DCSection>

      <DCSection
        id="host"
        title="Host tab"
        subtitle="Single card morphs from configuration to connected state."
      >
        <DCArtboard id="host-config-dark"      label="Dark · config"     width={W} height={H}>
          <Warden tab="host" hostMode="config" theme="dark"/>
        </DCArtboard>
        <DCArtboard id="host-config-light"     label="Light · config"    width={W} height={H}>
          <Warden tab="host" hostMode="config" theme="light"/>
        </DCArtboard>
        <DCArtboard id="host-connected-dark"   label="Dark · running"    width={W} height={H}>
          <Warden tab="host" hostMode="connected" theme="dark"/>
        </DCArtboard>
        <DCArtboard id="host-connected-light"  label="Light · running"   width={W} height={H}>
          <Warden tab="host" hostMode="connected" theme="light"/>
        </DCArtboard>
      </DCSection>

      <DCSection
        id="format"
        title="Format tab"
        subtitle="Destructive action — gated by checkbox confirmation and an amber warning banner."
      >
        <DCArtboard id="format-dark"  label="Dark"  width={W} height={H}>
          <Warden tab="format" theme="dark"/>
        </DCArtboard>
        <DCArtboard id="format-light" label="Light" width={W} height={H}>
          <Warden tab="format" theme="light"/>
        </DCArtboard>
      </DCSection>
    </DesignCanvas>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
