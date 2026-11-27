"use client";

import { useState, type FormEvent } from "react";
import { AppShell } from "@/components/AppShell";
import { AdminEditor } from "@/components/AdminEditor";
import { BackendPendingNotice } from "@/components/BackendPendingNotice";
import { Icon } from "@/components/Icon";
import { SignalBars } from "@/components/SignalBars";
import { StatusBadge } from "@/components/StatusBadge";
import { api, type Device } from "@/lib/api";
import { ago, deviceStatus, link } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";
import { emptyDeviceOverlay, overlayDevices, saveDevice, deleteDevice } from "@/lib/mockDevicesAdmin";

export default function Perangkat() {
  const { data, error, refresh } = usePoll(() => api<Device[]>("/devices"), 10000);
  const [local, setLocal] = useState(emptyDeviceOverlay);
  const [editor, setEditor] = useState<Device | "new" | null>(null);
  const [failure, setFailure] = useState("");
  const [message, setMessage] = useState("");
  const rows = overlayDevices(data ?? [], local);
  const editing = editor && editor !== "new" ? editor : null;
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const label = String(form.get("label")).trim();
    const device_id = String(form.get("device_id")).trim();
    if (!label || !device_id) { setFailure("Label dan ID perangkat wajib diisi."); return; }
    if (rows.some(d => d.device_id.toLowerCase() === device_id.toLowerCase() && d.id !== editing?.id)) {
      setFailure("ID perangkat sudah digunakan."); return;
    }
    setLocal(previous => saveDevice(previous, { label, device_id, link_type: form.get("link_type") === "lora" ? "lora" : "cellular" }, editing?.id));
    setEditor(null); setMessage("Perubahan perangkat diterapkan sementara. Belum tersimpan ke server.");
  }
  return <AppShell>
    <BackendPendingNotice issues={["#39"]} owner="scientivan" />
    <div className="page-head"><div><h1>Manajemen perangkat</h1><p className="sub">Daftar server diperbarui setiap 10 detik · {rows.length} perangkat ditampilkan</p></div>
      <button className="btn btn-primary" onClick={() => { setFailure(""); setEditor("new"); }}>Tambah perangkat</button></div>
    {message && <p className="note note-info" role="status">{message}</p>}
    {error && <div className="note note-error" role="alert">{error}<button className="btn btn-ghost btn-sm" onClick={refresh}>Coba lagi</button></div>}
    {!data && !error && <p className="note" role="status">Memuat daftar perangkat dari server…</p>}
    <section className="card admin-table-wrap" aria-label="Daftar perangkat"><table className="admin-table">
      <thead><tr>{["Label", "ID perangkat", "Koneksi", "Status pemantauan", "Sinyal", "Terakhir terlihat", "Tindakan"].map(t => <th key={t} scope="col">{t}</th>)}</tr></thead>
      <tbody>{rows.map(d => <tr key={d.id}><th scope="row">{d.label}{(local.changes[d.id] || local.added.some(a => a.id === d.id)) && <div><span className="chip">Belum tersimpan ke server</span></div>}</th>
        <td className="num">{d.device_id}</td><td>{link(d.link_type)}</td><td><StatusBadge status={deviceStatus(d)} /></td><td><SignalBars rssi={d.rssi} /></td><td>{ago(d.last_seen_at)}</td>
        <td><div className="admin-actions"><button className="btn btn-ghost btn-sm" aria-label={`Edit ${d.label}`} onClick={() => { setFailure(""); setEditor(d); }}><Icon name="edit" />Edit</button>
          <button className="btn btn-ghost btn-sm" aria-label={`Hapus ${d.label}`} onClick={() => { if (window.confirm(`Hapus ${d.label} dari daftar sementara? Data server tetap tersedia setelah muat ulang.`)) { setLocal(p => deleteDevice(p, d.id)); setMessage("Perangkat dihapus dari daftar sementara."); } }}><Icon name="trash" />Hapus</button></div></td></tr>)}</tbody>
    </table>{data && rows.length === 0 && <p className="panel">Belum ada perangkat. Tambahkan perangkat untuk mencoba formulir sementara.</p>}</section>
    {editor && <AdminEditor title={editing ? "Edit perangkat" : "Tambah perangkat"} onClose={() => setEditor(null)}>
      <form className="admin-form" onSubmit={submit}>
        <label className="field">Label<input autoFocus required name="label" className="input" defaultValue={editing?.label} maxLength={120} /></label>
        <label className="field">ID perangkat<input required name="device_id" className="input num" defaultValue={editing?.device_id} maxLength={100} /></label>
        <label className="field">Jenis koneksi<select name="link_type" className="input" defaultValue={editing?.link_type ?? "cellular"}><option value="cellular">Seluler</option><option value="lora">LoRa</option></select></label>
        {failure && <p className="note note-error" role="alert">{failure}</p>}
        <button className="btn btn-primary" type="submit">Terapkan sementara</button>
      </form></AdminEditor>}
  </AppShell>;
}
