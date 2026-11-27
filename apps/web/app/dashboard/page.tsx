"use client";

import { AppShell } from "@/components/AppShell";
import { DeviceCard } from "@/components/DeviceCard";
import { api, type Device } from "@/lib/api";
import { clock } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";

export default function Dashboard() {
  const { data, error, updatedAt } = usePoll(() => api<Device[]>("/devices"), 10000);
  const now = updatedAt?.getTime() ?? Date.now();
  return (
    <AppShell>
      <div className="page-head">
        <div>
          <h1>Pemantauan perangkat</h1>
          <p className="sub">Suhu terbaru setiap boks pendingin, diperbarui otomatis setiap 10 detik.</p>
        </div>
        {updatedAt && <span className="updated"><span className="live-dot" />Diperbarui {clock(updatedAt)}</span>}
      </div>
      {error && <div className="note note-error" role="alert"><div><b>Data perangkat belum bisa dimuat</b>{error}</div></div>}
      {!data && !error && <div className="grid-3"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div>}
      {data && data.length === 0 && (
        <div className="note"><div><b>Belum ada perangkat</b>Perangkat yang terdaftar di akun ini akan muncul di sini.</div></div>
      )}
      {data && data.length > 0 && (
        <div className="grid-3">{data.map((d) => <DeviceCard key={d.id} device={d} now={now} />)}</div>
      )}
    </AppShell>
  );
}
