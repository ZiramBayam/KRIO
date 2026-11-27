"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Icon } from "@/components/Icon";
import { StatusBadge } from "@/components/StatusBadge";
import { TempChart } from "@/components/TempChart";
import { api, session, type Alert, type Device, type Mode, type Reading, type Simulation } from "@/lib/api";
import { alertStatus, deviceStatus, KIND_LABEL, link, simClock, temp } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";

// Expected curve for each scenario, drawn as a tiny preview (x 0..60, y 0..28).
const SCENARIOS: { mode: Mode; name: string; desc: string; shape: string }[] = [
  { mode: "normal", name: "Operasi normal", desc: "Suhu stabil di rentang produk dan data terus masuk.",
    shape: "M2 18 L12 17 L22 19 L32 18 L42 17 L52 18 L62 18" },
  { mode: "excursion", name: "Pendingin gagal", desc: "Menit ke-10 pendingin mati, suhu naik melewati batas dan memicu peringatan.",
    shape: "M2 20 L12 20 L20 16 L30 11 L40 7 L50 5 L62 4" },
  { mode: "door-open", name: "Pintu dibuka", desc: "Pintu terbuka 5 menit di menit ke-10 dan ke-40, suhu melonjak lalu turun lagi.",
    shape: "M2 20 L12 20 L15 10 L20 19 L34 20 L40 20 L43 10 L48 19 L62 20" },
  { mode: "offline", name: "Perangkat offline", desc: "Menit ke-10 sampai 35 perangkat diam, status berubah Offline lalu pulih.",
    shape: "M2 18 L12 18 M38 18 L62 18" },
];

const MODE_NAME = Object.fromEntries(SCENARIOS.map((s) => [s.mode, s.name])) as Record<Mode, string>;

function Preview({ shape, offline }: { shape: string; offline?: boolean }) {
  return (
    <svg width="64" height="40" viewBox="0 0 64 28" aria-hidden="true">
      <line x1="0" y1="9" x2="64" y2="9" stroke="var(--color-critical)" strokeDasharray="3 2" strokeWidth="1" />
      {offline && <rect x="12" y="4" width="26" height="20" fill="var(--color-offline-bg)" />}
      <path d={shape} fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function SimulationPage() {
  const sim = usePoll(() => api<Simulation | null>("/simulation"), 2000);
  const running = sim.data?.state === "running";
  const fast = running ? 3000 : 10000;
  const devices = usePoll(() => api<Device[]>("/devices"), fast, [fast]);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("excursion");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const canRun = session()?.user.role !== "viewer";

  // Follow the device of an active or last run; otherwise default to the first device.
  useEffect(() => {
    if (sim.data && (running || !deviceId)) setDeviceId(sim.data.device_id);
    else if (!deviceId && devices.data?.length) setDeviceId(devices.data[0].id);
  }, [sim.data, running, deviceId, devices.data]);

  const run = sim.data && sim.data.device_id === deviceId ? sim.data : null;
  const startedAt = run ? new Date(run.started_at).getTime() : null;
  const speed = run?.speed ?? 20;

  const readings = usePoll(() => {
    if (!deviceId) return Promise.resolve([] as Reading[]);
    const end = new Date();
    const start = startedAt ? new Date(startedAt - 5000) : new Date(end.getTime() - 3 * 60_000);
    const q = new URLSearchParams({ device_id: deviceId, from: start.toISOString(), to: end.toISOString(), bucket: "10s" });
    return api<Reading[]>(`/readings?${q}`);
  }, fast, [deviceId, startedAt, fast]);
  const alerts = usePoll(() => api<Alert[]>("/alerts?status=all"), fast, [fast]);

  const device = devices.data?.find((d) => d.id === deviceId) ?? null;
  const toSim = (iso: string) => (startedAt ? ((new Date(iso).getTime() - startedAt) / 1000) * speed : 0);
  const points = (readings.data ?? [])
    .map((r) => ({ x: startedAt ? toSim(r.ts) / 60 : new Date(r.ts).getTime(), temp_c: r.temp_c }))
    .filter((p) => !startedAt || p.x >= 0);
  const runAlerts = run ? (alerts.data ?? []).filter((a) => a.device_id === run.device_id && new Date(a.raised_at).getTime() >= startedAt! - 1000) : [];
  const timeline = run ? [
    ...run.events.map((e) => ({ key: `e${e.at}${e.text}`, sim: e.sim_s, text: e.text, kind: e.text.includes("berhenti mengirim") ? "offline" : "event" })),
    ...runAlerts.map((a) => ({ key: a.id, sim: toSim(a.raised_at), text: `Peringatan ${alertStatus(a) === "critical" ? "kritis" : "baru"}. ${a.message}`, kind: "alert" })),
  ].sort((a, b) => a.sim - b.sim) : [];
  const elapsed = run?.sim_elapsed_s ?? 0;
  const lastPoint = points.at(-1);
  const pulsing = running && readings.updatedAt && lastPoint !== undefined;

  async function start() {
    if (!deviceId) return;
    setBusy(true); setFailure(null);
    try {
      sim.setData(await api<Simulation>("/simulation", { method: "POST", body: JSON.stringify({ device_id: deviceId, mode }) }));
    } catch (err) {
      setFailure(err instanceof Error ? err.message : "Simulasi gagal dimulai.");
    } finally { setBusy(false); sim.refresh(); }
  }
  async function stop() {
    setBusy(true); setFailure(null);
    try { await api("/simulation/stop", { method: "POST" }); }
    catch (err) { setFailure(err instanceof Error ? err.message : "Simulasi gagal dihentikan."); }
    finally { setBusy(false); sim.refresh(); }
  }
  async function acknowledge(id: string) {
    try { await api(`/alerts/${id}/ack`, { method: "POST" }); alerts.refresh(); }
    catch (err) { setFailure(err instanceof Error ? err.message : "Peringatan gagal ditandai."); }
  }

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Simulasi skenario</h1>
          <p className="sub">Pilih boks dan kejadian, lalu lihat bagaimana KRIO merespons. Satu jam simulasi selesai dalam sekitar 3 menit.</p>
        </div>
        <span className="updated"><Icon name="clock" size={15} />1 detik nyata sama dengan {speed} detik simulasi</span>
      </div>
      {failure && <div className="note note-error" role="alert"><div><b>Ada kendala</b>{failure}</div></div>}
      <div className="split">
        <div className="card">
          <div className="card-head"><h2>1. Pilih boks pendingin</h2></div>
          <div className="device-pick" style={{ padding: "0 4px 4px" }}>
            {(devices.data ?? []).map((d) => (
              <button key={d.id} aria-pressed={d.id === deviceId} disabled={running} onClick={() => setDeviceId(d.id)}>
                <span style={{ fontWeight: 700 }}>{d.label}</span>
                <span className="muted" style={{ fontSize: 12 }}>{d.device_id}, {link(d.link_type)}</span>
                <StatusBadge status={deviceStatus(d)} />
              </button>
            ))}
          </div>
          <div className="card-head" style={{ marginTop: 8 }}><h2>2. Pilih kejadian</h2></div>
          <div className="scenario-list" style={{ padding: "0 4px 4px" }}>
            {SCENARIOS.map((s) => (
              <button key={s.mode} className="scenario" aria-pressed={mode === s.mode} disabled={running} onClick={() => setMode(s.mode)}>
                <Preview shape={s.shape} offline={s.mode === "offline"} />
                <span><span className="scenario-name">{s.name}</span><span className="scenario-desc" style={{ display: "block" }}>{s.desc}</span></span>
              </button>
            ))}
          </div>
          <div style={{ padding: "12px 4px 4px", display: "grid", gap: 8 }}>
            {running ? (
              <button className="btn btn-danger" onClick={stop} disabled={busy || !canRun}><Icon name="stop" size={16} />Hentikan simulasi</button>
            ) : (
              <button className="btn btn-primary" onClick={start} disabled={busy || !deviceId || !canRun}><Icon name="play" size={16} />Jalankan simulasi</button>
            )}
            {!canRun && <div className="note note-info">Akun hanya-lihat bisa memantau simulasi tetapi tidak bisa menjalankannya.</div>}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>
          <div className="card">
            <div className="card-head">
              <div>
                <h2>{run ? `${MODE_NAME[run.mode]} di ${run.device_label}` : "Belum ada simulasi untuk boks ini"}</h2>
                <p className="muted" style={{ marginTop: 2 }}>
                  {run ? { running: "Simulasi sedang berjalan dan data dikirim lewat API ingest.", finished: "Simulasi selesai. Hasilnya tetap tersimpan di grafik dan daftar peringatan.", stopped: "Simulasi dihentikan sebelum selesai.", failed: `Simulasi gagal. ${run.error ?? ""}` }[run.state]
                    : "Tekan Jalankan simulasi untuk mulai mengirim data dari boks ini."}
                </p>
              </div>
              {device && <StatusBadge status={deviceStatus(device)} />}
            </div>
            <div className="panel">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
                <div className="sim-clock num">{simClock(elapsed)}</div>
                <div className="muted" style={{ fontWeight: 600 }}>menit simulasi dari {simClock(run?.duration_s ?? 3600)}</div>
              </div>
              <div className="progress" style={{ marginTop: 8 }} role="progressbar" aria-valuemin={0} aria-valuemax={100}
                aria-valuenow={Math.round((elapsed / (run?.duration_s ?? 3600)) * 100)} aria-label="Kemajuan simulasi">
                <span style={{ width: `${Math.min(100, (elapsed / (run?.duration_s ?? 3600)) * 100)}%` }} />
              </div>
              <div className="stat-row" style={{ marginTop: 12 }}>
                <div className="fact"><div className="fact-label"><Icon name="thermo" size={14} />Suhu sekarang</div>
                  <div className="fact-value num">{temp(device?.temp_c ?? null)}</div></div>
                <div className="fact"><div className="fact-label">
                  <span className={`live-dot ping${pulsing ? " on" : ""}`} />Data terkirim</div>
                  <div className="fact-value num">{run?.sent ?? 0} pesan</div></div>
                <div className="fact"><div className="fact-label"><Icon name="bell" size={14} />Peringatan baru</div>
                  <div className="fact-value num">{runAlerts.length}</div></div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-head">
              <div><h2>Grafik suhu</h2><p className="muted" style={{ marginTop: 2 }}>Sumbu bawah memakai menit simulasi, sama dengan jam di atas.</p></div>
              {device && <Link className="btn btn-ghost btn-sm" href={`/devices/?id=${device.id}`}>Detail perangkat</Link>}
            </div>
            <div className="panel" style={{ background: "var(--color-surface)" }}>
              {points.length === 0 ? (
                <div className="note"><div><b>Grafik masih kosong</b>Data pertama muncul beberapa detik setelah simulasi berjalan.</div></div>
              ) : (
                <TempChart points={points} min={device?.temp_min_c ?? null} max={device?.temp_max_c ?? null} height={260}
                  xLabel="menit simulasi" domainX={startedAt ? [0, 60] : undefined}
                  formatX={(x) => (startedAt ? `${Math.round(x)} mnt` : new Date(x).toLocaleTimeString("id-ID").slice(0, 5))} />
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-head"><div><h2>Linimasa kejadian</h2><p className="muted" style={{ marginTop: 2 }}>Kejadian skenario dan respons KRIO diurutkan menurut menit simulasi.</p></div></div>
            <div className="panel" style={{ background: "var(--color-surface)" }}>
              {timeline.length === 0 ? (
                <div className="note"><div><b>Belum ada kejadian</b>Linimasa terisi begitu simulasi dimulai.</div></div>
              ) : (
                <ol className="timeline">
                  {timeline.map((item) => (
                    <li key={item.key}>
                      <span className="t">{simClock(Math.max(0, item.sim))}</span>
                      <span className={`dot ${item.kind}`} />
                      <span style={{ fontWeight: item.kind === "alert" ? 700 : 600 }}>{item.text}</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>

          {runAlerts.some((a) => !a.resolved_at) && (
            <div className="card">
              <div className="card-head"><h2>Peringatan yang perlu ditangani</h2></div>
              <div className="panel" style={{ background: "var(--color-surface)", padding: 0 }}>
                <div className="rows">
                  {runAlerts.filter((a) => !a.resolved_at).map((a) => (
                    <div className="row row-enter" key={a.id} style={{ gridTemplateColumns: "120px minmax(0,1fr) 170px" }}>
                      <StatusBadge status={alertStatus(a)} />
                      <div><div className="row-title">{KIND_LABEL[a.kind] ?? a.kind}</div><div className="row-sub">{a.message}</div></div>
                      <button className="btn btn-ghost btn-sm" onClick={() => acknowledge(a.id)} disabled={!canRun}><Icon name="check" size={15} />Tandai ditangani</button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
