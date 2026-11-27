"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Icon } from "@/components/Icon";
import { RouteLine } from "@/components/RouteLine";
import { StatusBadge } from "@/components/StatusBadge";
import { TempChart } from "@/components/TempChart";
import { BackendPendingNotice } from "@/components/BackendPendingNotice";
import { mockShelfLife } from "@/lib/mockShelfLife";
import { HeroBanner } from "@/components/HeroBanner";
import { api, type Alert, type Reading, type Shipment } from "@/lib/api";
import { alertStatus, clock, KIND_LABEL, shipmentStatus, shipmentStatusLabel, stamp, temp } from "@/lib/format";
import { finishShipment, isActiveShipment, overlayShipments, useShipmentOverlay } from "@/lib/mockShipmentActions";
import { usePoll } from "@/lib/usePoll";

const RANGES = { "1h": { hours: 1, bucket: "1m" }, "24h": { hours: 24, bucket: "5m" } } as const;

function Detail() {
  const id = useSearchParams().get("id") ?? "";
  const [range, setRange] = useState<keyof typeof RANGES>("1h");
  const [local, setLocal] = useShipmentOverlay();
  const [failure, setFailure] = useState("");
  const added = local.added.find(s => s.id === id);
  const shipment = usePoll(() => id.startsWith("mock-")
    ? added ? Promise.resolve(added) : Promise.reject(new Error("Pengiriman sementara sudah tidak tersedia."))
    : id ? api<Shipment>(`/shipments/${encodeURIComponent(id)}`) : Promise.reject(new Error("ID pengiriman belum diisi.")), 10000, [id]);
  const source = added ?? (shipment.data?.id === id ? shipment.data : null);
  const s = source ? overlayShipments([source], { ...local, added: [] })[0] : null;
  function finish(status: "completed" | "aborted") {
    if (!s) return;
    try { setLocal(previous => finishShipment(previous, s, status)); setFailure(""); }
    catch (error) { setFailure(error instanceof Error ? error.message : "Perubahan belum dapat diterapkan."); }
  }
  const readings = usePoll(() => {
    if (!s || s.id !== id) return Promise.resolve<Reading[]>([]);
    const end = new Date(s.ended_at ?? Date.now());
    const start = new Date(Math.max(new Date(s.started_at).getTime(), end.getTime() - RANGES[range].hours * 3600_000));
    if (start > end) return Promise.resolve<Reading[]>([]);
    const q = new URLSearchParams({ device_id: s.device_id, from: start.toISOString(), to: end.toISOString(), bucket: RANGES[range].bucket });
    return api<Reading[]>(`/readings?${q}`);
  }, 10000, [s?.device_id, s?.started_at, s?.ended_at, range]);
  const alerts = usePoll(() => api<Alert[]>("/alerts?status=all"), 10000);
  const mine = (alerts.data ?? []).filter((a) => a.shipment_id === id).sort((a, b) => Date.parse(b.raised_at) - Date.parse(a.raised_at));
  const critical = mine.filter((a) => a.severity === "critical" && !a.resolved_at);
  const points = (readings.data ?? []).map((r) => ({ x: new Date(r.ts).getTime(), temp_c: r.temp_c }));
  const durationMinutes = s ? Math.max(0, Math.floor((new Date(s.ended_at ?? Date.now()).getTime() - Date.parse(s.started_at)) / 60000)) : 0;

  return <>
    <div className="page-head"><div>
      <Link href="/shipments/" className="btn btn-ghost btn-sm"><Icon name="back" size={16} />Semua pengiriman</Link>
      <h1>{s ? s.product_name : "Detail pengiriman"}</h1>
      {s && <><p className="sub">{s.device_label}</p><RouteLine origin={s.origin} destination={s.destination} className="shipment-route" /></>}
    </div>{s && <StatusBadge status={shipmentStatus(s)} />}</div>
    {shipment.error && !added && <div className="note note-error" role="alert"><div><b>Pengiriman tidak dapat dimuat</b>Periksa ID pengiriman atau coba lagi setelah koneksi tersedia.</div></div>}
    {!s && !shipment.error && <div className="skeleton" aria-label="Memuat detail pengiriman" />}
    {s && <>
      {(local.changes[s.id] || added) && <p className="note note-info" role="status"><span className="chip">Belum tersimpan ke server</span> Perubahan sementara; muat ulang menghapusnya.</p>}
      {isActiveShipment(s) && <div className="card"><div className="card-body">
        <h2>Tindakan pengiriman</h2>
        <BackendPendingNotice issues={["#41"]} owner="scientivan" />
        <div className="admin-actions">
          <button className="btn btn-primary" onClick={() => finish("completed")}>Selesaikan</button>
          <button className="btn btn-ghost" onClick={() => finish("aborted")}>Batalkan</button>
        </div>
      </div></div>}
      {failure && <p className="note note-error" role="alert">{failure}</p>}
      <div className="grid-3">
        <div className="card"><div className="panel"><div className="fact-label">Status pengiriman</div><div className="fact-value">{shipmentStatusLabel(s)}</div></div></div>
        <div className="card"><div className="panel"><div className="fact-label">Rentang suhu produk</div><div className="fact-value num">{temp(s.temp_min_c)} – {temp(s.temp_max_c)}</div></div></div>
        <div className="card"><div className="panel"><div className="fact-label">Mulai dan durasi</div><div className="fact-value">{stamp(s.started_at)}</div><p className="muted">{Math.floor(durationMinutes / 60)} jam {durationMinutes % 60} menit{s.ended_at ? ` · Berakhir ${stamp(s.ended_at)}` : " · Belum berakhir"}</p></div></div>
      </div>
      {shipmentStatus(s) === "warning" && critical.length > 0 && <HeroBanner status="critical" title="Peringatan kritis pada pengiriman aktif" detail={critical[0].message} stat={{ label: "Belum selesai", value: String(critical.length) }} />}
      <div className="card">
        <div className="card-head" style={{ flexWrap: "wrap" }}><div><h2>Grafik suhu</h2><p className="muted">Rentang terakhir dibatasi waktu mulai dan akhir pengiriman.</p></div>
          <div className="segmented" role="group" aria-label="Rentang waktu">{(Object.keys(RANGES) as (keyof typeof RANGES)[]).map((key) => <button key={key} aria-pressed={range === key} onClick={() => setRange(key)}>{key === "1h" ? "1 jam" : "24 jam"}</button>)}</div>
        </div>
        <div className="panel" style={{ background: "var(--color-surface)" }}>
          {readings.error && <div className="note note-error" role="alert">{readings.error}</div>}
          {!readings.data && !readings.error && <div className="skeleton" />}
          {readings.data && !readings.error && points.length === 0 && <div className="note">Belum ada pembacaan suhu dalam rentang ini.</div>}
          {points.length > 0 && <TempChart points={points} min={s.temp_min_c} max={s.temp_max_c} xLabel="jam" formatX={(x) => range === "1h" ? clock(new Date(x)).slice(0, 5) : stamp(new Date(x))} />}
        </div>
      </div>
      <div className="card"><div className="card-head"><h2>Sisa umur simpan</h2><span className="chip">Contoh sementara</span></div>
        <div className="card-body">
          <div className="fact-value num">{mockShelfLife(s)}%</div>
          <div className="progress" role="progressbar" aria-label="Contoh sisa umur simpan, bukan data nyata" aria-valuemin={0} aria-valuemax={100} aria-valuenow={mockShelfLife(s)}><span style={{ width: `${mockShelfLife(s)}%` }} /></div>
          <p className="muted">Ilustrasi berdasarkan durasi referensi arbitrer 72 jam. Bukan estimasi kelayakan atau keamanan produk.</p>
          <BackendPendingNotice issues={["#66"]} owner="AnthonyS051105" />
        </div>
      </div>
      <div className="card"><div className="card-head"><h2>Linimasa pengiriman</h2></div>
        <div className="panel" style={{ background: "var(--color-surface)", padding: 0 }}>
          {alerts.error && <div className="note note-error" role="alert">{alerts.error}</div>}
          {!alerts.data && !alerts.error && <div className="skeleton" />}
          {alerts.data && !alerts.error && mine.length === 0 && <div className="note">Belum ada peringatan terkait pengiriman ini.</div>}
          <div className="rows">{mine.map((a) => <div className="row" key={a.id}>
            <StatusBadge status={alertStatus(a)} />
            <div><div className="row-title">{KIND_LABEL[a.kind] ?? a.kind}</div><div className="row-sub">{a.message}</div></div>
            <div className="muted">{stamp(a.raised_at)}</div><div className="muted">{a.resolved_at ? "Selesai" : "Aktif"}</div>
          </div>)}</div>
        </div>
      </div>
    </>}
  </>;
}

export default function ShipmentDetailPage() {
  return <AppShell><Suspense fallback={<div className="skeleton" />}><Detail /></Suspense></AppShell>;
}
