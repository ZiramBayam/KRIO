// MOCK — tunggu backend #41 (@scientivan). Ganti ke api() asli saat endpoint tersedia.
import { useSyncExternalStore } from "react";
import { session, type Device, type Shipment } from "./api";
import type { Product } from "./mockProducts";

export type ShipmentOverlay = { changes: Record<string, Partial<Shipment>>; added: Shipment[] };
export const emptyShipmentOverlay: ShipmentOverlay = { changes: {}, added: [] };

export function overlayShipments(server: Shipment[], local: ShipmentOverlay): Shipment[] {
  return [...server, ...local.added].map(s => local.changes[s.id] ? { ...s, ...local.changes[s.id] } : s);
}

export function isActiveShipment(s: Shipment) {
  return ["active", "in_transit", "ongoing", "running"].includes(s.status.toLowerCase());
}

export function startShipment(local: ShipmentOverlay, server: Shipment[], device: Device, product: Product, origin: string, destination: string): ShipmentOverlay {
  if (!origin.trim() || !destination.trim()) throw new Error("Isi asal dan tujuan pengiriman.");
  if (overlayShipments(server, local).some(s => s.device_id === device.id && isActiveShipment(s))) {
    throw new Error("Perangkat sudah memiliki pengiriman aktif.");
  }
  const shipment: Shipment = { id: `mock-${crypto.randomUUID()}`, device_id: device.id, device_label: device.label,
    product_id: product.id, product_name: product.name, temp_min_c: product.min, temp_max_c: product.max,
    origin: origin.trim(), destination: destination.trim(), status: "active", started_at: new Date().toISOString(), ended_at: null };
  return { ...local, added: [...local.added, shipment] };
}

export function finishShipment(local: ShipmentOverlay, shipment: Shipment, status: "completed" | "aborted"): ShipmentOverlay {
  const current = overlayShipments([shipment], { ...local, added: [] })[0];
  if (!isActiveShipment(current)) throw new Error("Hanya pengiriman aktif yang dapat diselesaikan atau dibatalkan.");
  return { ...local, changes: { ...local.changes, [shipment.id]: { status, ended_at: new Date().toISOString() } } };
}

// Overlay hanya di memori, dibagi antara daftar/detail; muat ulang menghapusnya.
// Pisahkan per sesi autentikasi agar perubahan akun lain tidak ikut ditampilkan.
const overlays = new Map<string, ShipmentOverlay>();
const listeners = new Set<() => void>();
function subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; }
export function useShipmentOverlay() {
  const key = session()?.token ?? "";
  const local = useSyncExternalStore(subscribe, () => overlays.get(key) ?? emptyShipmentOverlay, () => emptyShipmentOverlay);
  function update(change: (previous: ShipmentOverlay) => ShipmentOverlay) {
    overlays.set(key, change(overlays.get(key) ?? emptyShipmentOverlay));
    listeners.forEach(listener => listener());
  }
  return [local, update] as const;
}
