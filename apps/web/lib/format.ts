import type { Alert, Device } from "./api";

export type Status = "safe" | "warning" | "critical" | "offline";

export const STATUS: Record<Status, { icon: string; label: string; hint: string }> = {
  safe: { icon: "●", label: "Aman", hint: "Suhu berada di dalam rentang produk." },
  warning: { icon: "▲", label: "Waspada", hint: "Suhu kurang dari 0,5 °C dari batas produk." },
  critical: { icon: "✕", label: "Kritis", hint: "Suhu sudah keluar dari rentang produk." },
  offline: { icon: "○", label: "Offline", hint: "Perangkat berhenti mengirim data." },
};

export function deviceStatus(d: Device): Status {
  if (d.status === "offline") return "offline";
  if (d.temp_c == null || d.temp_min_c == null || d.temp_max_c == null) return "safe";
  if (d.temp_c > d.temp_max_c || d.temp_c < d.temp_min_c) return "critical";
  if (d.temp_c > d.temp_max_c - 0.5 || d.temp_c < d.temp_min_c + 0.5) return "warning";
  return "safe";
}

export function alertStatus(a: Alert): Status {
  if (a.kind === "DEVICE_OFFLINE") return "offline";
  return a.severity === "critical" ? "critical" : "warning";
}

export const KIND_LABEL: Record<string, string> = {
  KEGAGALAN_PENDINGIN: "Suhu keluar dari batas",
  DEVICE_OFFLINE: "Perangkat offline",
};

const time = new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const dateTime = new Intl.DateTimeFormat("id-ID", {
  day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
});

export const clock = (iso: string | Date) => time.format(new Date(iso));
export const stamp = (iso: string | Date) => dateTime.format(new Date(iso));

export function ago(iso: string | null, now = Date.now()) {
  if (!iso) return "Belum pernah mengirim";
  const s = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (s < 60) return `${s} detik lalu`;
  if (s < 3600) return `${Math.floor(s / 60)} menit lalu`;
  if (s < 86400) return `${Math.floor(s / 3600)} jam lalu`;
  return `${Math.floor(s / 86400)} hari lalu`;
}

export const temp = (v: number | null) => (v == null ? "Tidak ada" : `${v.toFixed(1)} °C`);
export const link = (l: Device["link_type"]) => (l === "lora" ? "LoRa" : "Seluler");

export function simClock(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}.${String(s).padStart(2, "0")}`;
}
