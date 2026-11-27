import Link from "next/link";
import type { Device } from "@/lib/api";
import { ago, deviceStatus, link, temp } from "@/lib/format";
import { Icon } from "./Icon";
import { StatusBadge } from "./StatusBadge";

export function DeviceCard({ device, now }: { device: Device; now: number }) {
  return (
    <Link href={`/devices/?id=${device.id}`} className="card device-card">
      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
          <StatusBadge status={deviceStatus(device)} />
          <span className="chip">{device.device_id}</span>
        </div>
        <div className="device-temp num" style={{ marginTop: 14 }}>{temp(device.temp_c)}</div>
        <div className="device-range">
          {device.temp_min_c != null ? `Rentang produk ${device.temp_min_c} sampai ${device.temp_max_c} °C` : "Belum ada pengiriman aktif"}
        </div>
        <div className="facts">
          <div className="fact"><div className="fact-label"><Icon name="clock" size={14} />Terakhir</div>
            <div className="fact-value">{ago(device.last_seen_at, now)}</div></div>
          <div className="fact"><div className="fact-label"><Icon name="battery" size={14} />Baterai</div>
            <div className="fact-value num">{device.batt_v != null ? `${device.batt_v.toFixed(2)} V` : "Tidak ada"}</div></div>
          <div className="fact"><div className="fact-label"><Icon name="signal" size={14} />Jaringan</div>
            <div className="fact-value">{link(device.link_type)}</div></div>
        </div>
      </div>
      <div className="card-body">
        <h2>{device.label}</h2>
        <p className="muted">Buka grafik suhu dan riwayat peringatan perangkat ini.</p>
      </div>
    </Link>
  );
}
