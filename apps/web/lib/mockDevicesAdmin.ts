// MOCK — tunggu backend #39 (@scientivan). Ganti ke api() asli saat endpoint tersedia.
import type { Device } from "./api";

export type DeviceDraft = Pick<Device, "label" | "device_id" | "link_type">;
export type DeviceOverlay = { changes: Record<string, DeviceDraft>; added: Device[]; deleted: string[] };
export const emptyDeviceOverlay: DeviceOverlay = { changes: {}, added: [], deleted: [] };

export function overlayDevices(server: Device[], local: DeviceOverlay) {
  return [...server, ...local.added].filter(d => !local.deleted.includes(d.id))
    .map(d => local.changes[d.id] ? { ...d, ...local.changes[d.id] } : d);
}

export function saveDevice(local: DeviceOverlay, draft: DeviceDraft, id?: string): DeviceOverlay {
  if (id) return { ...local, changes: { ...local.changes, [id]: draft } };
  const device: Device = { ...draft, id: `mock-${crypto.randomUUID()}`, status: "offline",
    last_seen_at: null, reading_at: null, temp_c: null, batt_v: null, rh_pct: null,
    rssi: null, temp_min_c: null, temp_max_c: null };
  return { ...local, added: [...local.added, device] };
}

export function deleteDevice(local: DeviceOverlay, id: string): DeviceOverlay {
  return { ...local, deleted: [...local.deleted, id] };
}
