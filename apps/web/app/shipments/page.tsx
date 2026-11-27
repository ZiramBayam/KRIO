"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { AdminEditor } from "@/components/AdminEditor";
import { BackendPendingNotice } from "@/components/BackendPendingNotice";
import { seedProducts } from "@/lib/mockProducts";
import { isActiveShipment, overlayShipments, startShipment, useShipmentOverlay } from "@/lib/mockShipmentActions";
import { AppShell } from "@/components/AppShell";
import { RouteLine } from "@/components/RouteLine";
import { StatusBadge } from "@/components/StatusBadge";
import { api, type Device, type Shipment } from "@/lib/api";
import { clock, SHIPMENT_STATUS_LABEL, shipmentStatus, shipmentStatusLabel, stamp } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";

export default function ShipmentsPage() {
  const shipments = usePoll(() => api<Shipment[]>("/shipments"), 10000);
  const devices = usePoll(() => api<Device[]>("/devices"), 10000);
  const [local, setLocal] = useShipmentOverlay();
  const [editor, setEditor] = useState(false);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [failure, setFailure] = useState("");
  const [message, setMessage] = useState("");
  const rows = overlayShipments(shipments.data ?? [], local);
  const available = (devices.data ?? []).filter(d => !rows.some(s => s.device_id === d.id && isActiveShipment(s)));
  const ready = !!shipments.data && !!devices.data && !shipments.error && !devices.error;
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ready) { setFailure("Tunggu hingga data server selesai dimuat."); return; }
    const form = new FormData(event.currentTarget);
    const device = available.find(d => d.id === form.get("device"));
    const product = seedProducts.find(p => p.id === form.get("product"));
    if (!device || !product) { setFailure("Pilih perangkat yang tersedia dan produk contoh."); return; }
    try {
      setLocal(previous => startShipment(previous, shipments.data ?? [], device, product, origin, destination));
      setEditor(false); setStatus(null);
      setMessage("Pengiriman ditambahkan sementara. Belum tersimpan ke server; muat ulang menghapus perubahan.");
    } catch (error) { setFailure(error instanceof Error ? error.message : "Pengiriman belum dapat dimulai."); }
  }
  const [status, setStatus] = useState<string | null>(null);
  const statuses = Array.from(new Set(rows.map((s) => s.status)));
  const selected = status !== null && statuses.includes(status) ? status : null;
  const list = rows.filter((s) => selected === null || s.status === selected);
  return <AppShell>
    <div className="page-head"><div><h1>Pengiriman</h1><p className="sub">Pantau rute, status, dan riwayat suhu setiap pengiriman.</p></div>
      <button className="btn btn-primary" onClick={() => { setFailure(""); setOrigin(""); setDestination(""); setEditor(true); }}>Mulai pengiriman</button>
      {shipments.updatedAt && <span className="updated">Diperbarui {clock(shipments.updatedAt)}</span>}
    </div>
    {message && <p className="note note-info" role="status">{message}</p>}
    <div className="card">
      <div className="card-head"><div className="segmented shipment-filters" role="group" aria-label="Status pengiriman">
        <button aria-pressed={selected === null} onClick={() => setStatus(null)}>Semua</button>
        {statuses.map((s) => <button key={s} aria-pressed={selected === s} onClick={() => setStatus(s)}>{SHIPMENT_STATUS_LABEL[s.toLowerCase()] ?? s}</button>)}
      </div><span className="chip">{list.length} pengiriman</span></div>
      {shipments.error && <div className="note note-error" role="alert"><div><b>Pengiriman belum bisa dimuat</b>{shipments.error}</div></div>}
      {!shipments.data && !shipments.error && <div className="skeleton" aria-label="Memuat pengiriman" />}
      {shipments.data && list.length === 0 && <div className="note"><div><b>Belum ada pengiriman</b>Pengiriman yang tercatat akan muncul di sini.</div></div>}
      <div className="rows">{list.map((s) => <Link key={s.id} href={`/shipments/detail/?id=${encodeURIComponent(s.id)}`} className="row row-link">
        <StatusBadge status={shipmentStatus(s)} />
        <div><div className="row-title">{s.product_name}</div><div className="row-sub">{s.device_label}</div>{(local.changes[s.id] || local.added.some(a => a.id === s.id)) && <span className="chip">Belum tersimpan ke server</span>}<RouteLine origin={s.origin} destination={s.destination} className="shipment-route" /></div>
        <div>{shipmentStatusLabel(s)}</div><div className="muted">{stamp(s.started_at)}</div>
      </Link>)}</div>
    </div>
    {editor && <AdminEditor title="Mulai pengiriman" onClose={() => setEditor(false)}>
      <form className="admin-form" onSubmit={submit}>
        <BackendPendingNotice issues={["#41"]} owner="scientivan" />
        <p className="muted">Produk memakai katalog contoh sementara #40. Suhu produk contoh bukan acuan keamanan pangan. Muat ulang menghapus perubahan pengiriman.</p>
        {(!shipments.data || !devices.data) && !shipments.error && !devices.error && <p className="note" role="status">Memuat perangkat dan pengiriman dari server…</p>}
        {(devices.error || shipments.error) && <p className="note note-error" role="alert">Data server belum dapat dimuat. Tunggu pembaruan sebelum memulai pengiriman.</p>}
        {ready && available.length === 0 && <p className="note">Tidak ada perangkat tersedia. Semua perangkat terdaftar sedang memiliki pengiriman aktif.</p>}
        <label className="field">Perangkat<select autoFocus required name="device" className="input" defaultValue="" disabled={!ready}>
          <option value="" disabled>Pilih perangkat</option>{available.map(d => <option key={d.id} value={d.id}>{d.label} · {d.device_id}</option>)}
        </select></label>
        <label className="field">Produk contoh<select required name="product" className="input" defaultValue=""><option value="" disabled>Pilih produk contoh</option>{seedProducts.map(p => <option key={p.id} value={p.id}>{p.name} · {p.min}–{p.max} °C</option>)}</select></label>
        <label className="field">Asal<input required className="input" value={origin} maxLength={160} onChange={e => setOrigin(e.target.value)} /></label>
        <label className="field">Tujuan<input required className="input" value={destination} maxLength={160} onChange={e => setDestination(e.target.value)} /></label>
        {origin.trim() && destination.trim() && <RouteLine origin={origin.trim()} destination={destination.trim()} className="shipment-route" />}
        {failure && <p className="note note-error" role="alert">{failure}</p>}
        <button type="submit" className="btn btn-primary" disabled={!ready || available.length === 0}>Mulai sementara</button>
      </form>
    </AdminEditor>}
  </AppShell>;
}
