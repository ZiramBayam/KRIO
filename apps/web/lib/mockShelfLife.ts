// MOCK — tunggu backend/ML #66. Fungsi deterministik sederhana, BUKAN data nyata.
import type { Shipment } from "./api";

/** Referensi arbitrer 72 jam; waktu akhir dibekukan untuk pengiriman selesai. */
export function mockShelfLife(s: Shipment, now = Date.now()): number {
  const elapsed = Math.max(0, (s.ended_at ? Date.parse(s.ended_at) : now) - Date.parse(s.started_at));
  if (!Number.isFinite(elapsed)) return 0;
  return Math.max(0, Math.min(100, Math.round(100 * (1 - elapsed / (72 * 3600_000)))));
}
