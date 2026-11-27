"use client";

import { useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Icon } from "@/components/Icon";
import { StatusBadge } from "@/components/StatusBadge";
import { api, session, type Alert, type Device } from "@/lib/api";
import { alertStatus, clock, KIND_LABEL, stamp } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";

const STATUS_FILTER = { active: "Aktif", resolved: "Selesai", all: "Semua" } as const;
const SEVERITY_FILTER = { all: "Semua tingkat", critical: "Kritis", warning: "Waspada" } as const;

function alertIcon(kind: string): string {
  if (kind === "DEVICE_OFFLINE") return "signal";
  if (kind === "KEGAGALAN_PENDINGIN") return "thermo";
  return "bell";
}

export default function Alerts() {
  const [status, setStatus] = useState<keyof typeof STATUS_FILTER>("active");
  const [severity, setSeverity] = useState<keyof typeof SEVERITY_FILTER>("all");
  const [failure, setFailure] = useState<string | null>(null);
  const seen = useRef<Set<string> | null>(null);
  const alerts = usePoll(() => api<Alert[]>(`/alerts?status=${status}`), 10000, [status]);
  const devices = usePoll(() => api<Device[]>("/devices"), 30000);
  const labels = new Map((devices.data ?? []).map((d) => [d.id, d.label]));
  const canAck = session()?.user.role !== "viewer";

  const list = (alerts.data ?? []).filter((a) => severity === "all" || a.severity === severity);

  // Pengelompokan visual per perangkat (mempertahankan urutan kejadian terbaru)
  const groupedList: { alert: Alert; groupIndex: number; groupTotal: number }[] = [];
  const deviceGroups = new Map<string, Alert[]>();
  for (const a of list) {
    const existing = deviceGroups.get(a.device_id);
    if (existing) {
      existing.push(a);
    } else {
      deviceGroups.set(a.device_id, [a]);
    }
  }
  for (const group of deviceGroups.values()) {
    group.forEach((alert, idx) => {
      groupedList.push({ alert, groupIndex: idx, groupTotal: group.length });
    });
  }

  const fresh = new Set<string>();
  if (alerts.data) {
    if (seen.current) for (const a of alerts.data) if (!seen.current.has(a.id)) fresh.add(a.id);
    seen.current = new Set(alerts.data.map((a) => a.id));
  }
  const critical = (alerts.data ?? []).filter((a) => a.severity === "critical" && !a.resolved_at).length;

  async function acknowledge(alert: Alert) {
    setFailure(null);
    const previous = alerts.data;
    alerts.setData((rows) => (rows ?? []).filter((a) => status !== "active" || a.id !== alert.id)
      .map((a) => (a.id === alert.id ? { ...a, resolved_at: new Date().toISOString() } : a)));
    try {
      await api(`/alerts/${alert.id}/ack`, { method: "POST" });
      alerts.refresh();
    } catch (err) {
      alerts.setData(previous);
      setFailure(err instanceof Error ? err.message : "Peringatan gagal ditandai.");
    }
  }

  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Peringatan</h1>
          <p className="sub">Tandai peringatan yang sudah ditangani supaya tim tahu kondisinya sedang diurus.</p>
        </div>
        {alerts.updatedAt && <span className="updated"><span className="live-dot" />Diperbarui {clock(alerts.updatedAt)}</span>}
      </div>
      <div className="grid-3">
        <div className="card"><div className="panel"><div className="fact-label">Kritis dan aktif</div>
          <div className="device-temp num">{critical}</div></div>
          <div className="card-body"><h3>Perlu ditangani sekarang</h3><p className="muted">Suhu jauh di luar rentang produk.</p></div></div>
        <div className="card"><div className="panel"><div className="fact-label">Ditampilkan</div>
          <div className="device-temp num">{list.length}</div></div>
          <div className="card-body"><h3>Sesuai filter</h3><p className="muted">{STATUS_FILTER[status]}, {SEVERITY_FILTER[severity].toLowerCase()}.</p></div></div>
        <div className="card"><div className="panel"><div className="fact-label">Pemeriksaan otomatis</div>
          <div className="device-temp num">30 dtk</div></div>
          <div className="card-body"><h3>Jadwal pemindaian</h3><p className="muted">Server memeriksa suhu dan perangkat diam setiap 30 detik.</p></div></div>
      </div>
      <div className="card">
        <div className="card-head" style={{ flexWrap: "wrap" }}>
          <div className="segmented" role="group" aria-label="Status peringatan">
            {(Object.keys(STATUS_FILTER) as (keyof typeof STATUS_FILTER)[]).map((k) => (
              <button key={k} aria-pressed={status === k} onClick={() => setStatus(k)}>{STATUS_FILTER[k]}</button>
            ))}
          </div>
          <div className="segmented" role="group" aria-label="Tingkat peringatan">
            {(Object.keys(SEVERITY_FILTER) as (keyof typeof SEVERITY_FILTER)[]).map((k) => (
              <button key={k} aria-pressed={severity === k} onClick={() => setSeverity(k)}>{SEVERITY_FILTER[k]}</button>
            ))}
          </div>
        </div>
        <div className="panel" style={{ background: "var(--color-surface)", padding: 0 }}>
          {failure && <div className="note note-error" role="alert">{failure}</div>}
          {alerts.error && <div className="note note-error" role="alert"><div><b>Peringatan belum bisa dimuat</b>{alerts.error}</div></div>}
          {!alerts.data && !alerts.error && <div className="skeleton" />}
          {alerts.data && list.length === 0 && (
            <div className="note" style={{ border: 0 }}><div><b>Tidak ada peringatan</b>Semua perangkat sedang dalam kondisi yang tidak memicu peringatan.</div></div>
          )}
          <div className="rows">
            {groupedList.map(({ alert: a, groupIndex, groupTotal }) => (
              <div
                className={`row${fresh.has(a.id) ? " row-enter" : ""}${groupTotal > 1 && groupIndex > 0 ? " row-device-repeat" : ""}`}
                key={a.id}
              >
                <StatusBadge status={alertStatus(a)} />
                <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  <span className={`icon-chip icon-chip-${a.severity}`} aria-hidden="true">
                    <Icon name={alertIcon(a.kind)} size={16} />
                  </span>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div className="row-title" style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <span>{KIND_LABEL[a.kind] ?? a.kind} di {labels.get(a.device_id) ?? "perangkat"}</span>
                      {groupTotal > 1 && groupIndex === 0 && (
                        <span className="chip" style={{ fontSize: 11, fontWeight: 700, height: 20, padding: "0 8px", color: "var(--color-critical)" }}>
                          {groupTotal} peringatan
                        </span>
                      )}
                      {groupTotal > 1 && groupIndex > 0 && (
                        <span className="chip" style={{ fontSize: 11, fontWeight: 600, height: 20, padding: "0 8px" }}>
                          #{groupIndex + 1}
                        </span>
                      )}
                    </div>
                    <div className="row-sub">{a.message}</div>
                  </div>
                </div>
                <div className="muted">{stamp(a.raised_at)}</div>
                <div>
                  {a.resolved_at ? (
                    <span className="chip"><Icon name="check" size={14} />&nbsp;{a.acked_by ? "Sudah ditangani" : "Pulih otomatis"}</span>
                  ) : (
                    <button className="btn btn-ghost btn-sm" onClick={() => acknowledge(a)} disabled={!canAck}
                      title={canAck ? undefined : "Akun hanya-lihat tidak bisa menandai peringatan"}>
                      <Icon name="check" size={15} />Tandai ditangani
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
