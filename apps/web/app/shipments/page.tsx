"use client";

import Link from "next/link";
import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { RouteLine } from "@/components/RouteLine";
import { StatusBadge } from "@/components/StatusBadge";
import { api, type Shipment } from "@/lib/api";
import { clock, SHIPMENT_STATUS_LABEL, shipmentStatus, shipmentStatusLabel, stamp } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";

export default function ShipmentsPage() {
  const shipments = usePoll(() => api<Shipment[]>("/shipments"), 10000);
  const [status, setStatus] = useState<string | null>(null);
  const statuses = Array.from(new Set((shipments.data ?? []).map((s) => s.status)));
  const selected = status !== null && statuses.includes(status) ? status : null;
  const list = (shipments.data ?? []).filter((s) => selected === null || s.status === selected);
  return <AppShell>
    <div className="page-head"><div><h1>Pengiriman</h1><p className="sub">Pantau rute, status, dan riwayat suhu setiap pengiriman.</p></div>
      {shipments.updatedAt && <span className="updated">Diperbarui {clock(shipments.updatedAt)}</span>}
    </div>
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
        <div><div className="row-title">{s.product_name}</div><div className="row-sub">{s.device_label}</div><RouteLine origin={s.origin} destination={s.destination} className="shipment-route" /></div>
        <div>{shipmentStatusLabel(s)}</div><div className="muted">{stamp(s.started_at)}</div>
      </Link>)}</div>
    </div>
  </AppShell>;
}
