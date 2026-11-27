"use client";

import { AppShell } from "@/components/AppShell";
import { DeviceCard } from "@/components/DeviceCard";
import { HeroBanner } from "@/components/HeroBanner";
import { api, type Device } from "@/lib/api";
import { clock, deviceStatus, temp } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";

export default function Dashboard() {
  const { data, error, updatedAt } = usePoll(() => api<Device[]>("/devices"), 10000);
  const now = updatedAt?.getTime() ?? Date.now();

  const highlight = (() => {
    if (!data || data.length === 0) return null;
    const critical = data.find((d) => deviceStatus(d) === "critical");
    if (critical) {
      const min = critical.temp_min_c ?? 0;
      const max = critical.temp_max_c ?? 0;
      return {
        status: "critical" as const,
        title: `${critical.label} — suhu di luar batas`,
        detail: `Suhu saat ini ${temp(critical.temp_c)} keluar dari rentang aman ${min} sampai ${max} °C. Periksa boks pendingin segera.`,
        stat: {
          label: "Suhu saat ini",
          value: temp(critical.temp_c),
        },
      };
    }
    const warning = data.find((d) => deviceStatus(d) === "warning");
    if (warning) {
      const min = warning.temp_min_c ?? 0;
      const max = warning.temp_max_c ?? 0;
      return {
        status: "warning" as const,
        title: `${warning.label} — suhu mendekati batas`,
        detail: `Suhu saat ini ${temp(warning.temp_c)} mendekati batas aman (${min} sampai ${max} °C).`,
        stat: {
          label: "Suhu saat ini",
          value: temp(warning.temp_c),
        },
      };
    }
    return null;
  })();

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
      {highlight && (
        <HeroBanner
          status={highlight.status}
          title={highlight.title}
          detail={highlight.detail}
          stat={highlight.stat}
        />
      )}
      {!data && !error && <div className="device-grid"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div>}
      {data && data.length === 0 && (
        <div className="note"><div><b>Belum ada perangkat</b>Perangkat yang terdaftar di akun ini akan muncul di sini.</div></div>
      )}
      {data && data.length > 0 && (
        <div className="device-grid">{data.map((d) => <DeviceCard key={d.id} device={d} now={now} />)}</div>
      )}
    </AppShell>
  );
}
