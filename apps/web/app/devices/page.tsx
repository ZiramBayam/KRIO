"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Icon } from "@/components/Icon";
import { StatusBadge } from "@/components/StatusBadge";
import { TempChart } from "@/components/TempChart";
import { api, type Alert, type Device, type Reading } from "@/lib/api";
import { ago, alertStatus, clock, deviceStatus, KIND_LABEL, link, stamp, temp } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";

const RANGES = { "1h": { hours: 1, bucket: "1m" }, "24h": { hours: 24, bucket: "5m" } } as const;

function Detail() {
  const id = useSearchParams().get("id") ?? "";
  const [range, setRange] = useState<keyof typeof RANGES>("1h");
  const device = usePoll(() => api<Device>(`/devices/${id}`), 10000, [id]);
  const readings = usePoll(() => {
    const end = new Date();
    const start = new Date(end.getTime() - RANGES[range].hours * 3600_000);
    const q = new URLSearchParams({ device_id: id, from: start.toISOString(), to: end.toISOString(), bucket: RANGES[range].bucket });
    return api<Reading[]>(`/readings?${q}`);
  }, 10000, [id, range]);
  const alerts = usePoll(() => api<Alert[]>("/alerts?status=all"), 10000);

  const d = device.data;
  const points = (readings.data ?? []).map((r) => ({ x: new Date(r.ts).getTime(), temp_c: r.temp_c }));
  const mine = (alerts.data ?? []).filter((a) => a.device_id === id).slice(0, 8);

  return (
    <>
      <div className="page-head">
        <div>
          <Link href="/dashboard/" className="btn btn-ghost btn-sm" style={{ marginBottom: 12 }}><Icon name="back" size={16} />Semua perangkat</Link>
          <h1>{d?.label ?? "Memuat perangkat"}</h1>
          <p className="sub">{d ? `${d.device_id} lewat jaringan ${link(d.link_type)}. Data terakhir ${ago(d.last_seen_at)}.` : "Mengambil data perangkat."}</p>
        </div>
        {d && <StatusBadge status={deviceStatus(d)} />}
      </div>
      {device.error && <div className="note note-error" role="alert"><div><b>Perangkat tidak ditemukan</b>{device.error}</div></div>}
      <div className="card">
        <div className="card-head">
          <div>
            <h2>Grafik suhu</h2>
            <p className="muted" style={{ marginTop: 2 }}>Area hijau adalah rentang aman produk. Garis putus-putus menandai batasnya.</p>
          </div>
          <div className="segmented" role="group" aria-label="Rentang waktu">
            {(Object.keys(RANGES) as (keyof typeof RANGES)[]).map((key) => (
              <button key={key} aria-pressed={range === key} onClick={() => setRange(key)}>{key === "1h" ? "1 jam" : "24 jam"}</button>
            ))}
          </div>
        </div>
        <div className="panel" style={{ background: "var(--color-surface)" }}>
          {readings.error && <div className="note note-error">{readings.error}</div>}
          {!readings.data && !readings.error && <div className="skeleton" />}
          {readings.data && points.length === 0 && (
            <div className="note"><div><b>Belum ada data di rentang ini</b>Pilih 24 jam atau jalankan simulasi untuk mengirim data baru.</div></div>
          )}
          {points.length > 0 && <TempChart points={points} min={d?.temp_min_c ?? null} max={d?.temp_max_c ?? null}
            xLabel="jam" formatX={(x) => (range === "1h" ? clock(new Date(x)).slice(0, 5) : stamp(new Date(x)))} />}
        </div>
      </div>
      <div className="grid-3">
        <div className="card"><div className="panel"><div className="fact-label">Suhu terakhir</div>
          <div className="device-temp num">{temp(d?.temp_c ?? null)}</div></div>
          <div className="card-body"><h3>Pembacaan sensor</h3><p className="muted">Diukur {d?.reading_at ? clock(d.reading_at) : "belum ada"}.</p></div></div>
        <div className="card"><div className="panel"><div className="fact-label">Baterai</div>
          <div className="device-temp num">{d?.batt_v != null ? `${d.batt_v.toFixed(2)} V` : "Tidak ada"}</div></div>
          <div className="card-body"><h3>Daya perangkat</h3><p className="muted">Di bawah 3,4 V perangkat perlu diisi ulang.</p></div></div>
        <div className="card"><div className="panel"><div className="fact-label">Kelembapan</div>
          <div className="device-temp num">{d?.rh_pct != null ? `${Math.round(d.rh_pct)}%` : "Tidak ada"}</div></div>
          <div className="card-body"><h3>Udara di dalam boks</h3><p className="muted">Dibaca bersama suhu pada setiap pengiriman.</p></div></div>
      </div>
      <div className="card">
        <div className="card-head"><h2>Peringatan perangkat ini</h2><Link href="/alerts/" className="btn btn-ghost btn-sm">Buka semua peringatan</Link></div>
        <div className="panel" style={{ background: "var(--color-surface)", padding: 0 }}>
          {mine.length === 0 && <div className="note" style={{ border: 0 }}><div><b>Belum ada peringatan</b>Perangkat ini belum pernah memicu peringatan.</div></div>}
          <div className="rows">
            {mine.map((a) => (
              <div className="row" key={a.id}>
                <StatusBadge status={alertStatus(a)} />
                <div><div className="row-title">{KIND_LABEL[a.kind] ?? a.kind}</div><div className="row-sub">{a.message}</div></div>
                <div className="muted">{stamp(a.raised_at)}</div>
                <div className="muted">{a.resolved_at ? "Selesai" : "Aktif"}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

export default function DevicePage() {
  return (
    <AppShell>
      <Suspense fallback={<div className="skeleton" />}><Detail /></Suspense>
    </AppShell>
  );
}
