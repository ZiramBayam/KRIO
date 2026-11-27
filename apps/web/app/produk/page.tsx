"use client";

import { useState, type FormEvent } from "react";
import { AppShell } from "@/components/AppShell";
import { AdminEditor } from "@/components/AdminEditor";
import { BackendPendingNotice } from "@/components/BackendPendingNotice";
import { Icon } from "@/components/Icon";
import { seedProducts, saveProduct, deleteProduct, type Product } from "@/lib/mockProducts";

export default function Produk() {
  const [rows, setRows] = useState(seedProducts);
  const [editor, setEditor] = useState<Product | "new" | null>(null);
  const [failure, setFailure] = useState("");
  const [message, setMessage] = useState("");
  const editing = editor && editor !== "new" ? editor : null;
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name")).trim();
    const min = Number(form.get("min"));
    const max = Number(form.get("max"));
    const shelfHours = Number(form.get("shelfHours"));
    if (!name || ![min, max, shelfHours].every(Number.isFinite) || min > max || shelfHours <= 0) {
      setFailure("Isi nama, suhu minimum ≤ maksimum, dan umur simpan lebih dari 0 jam."); return;
    }
    setRows(p => saveProduct(p, { name, min, max, shelfHours }, editing?.id));
    setEditor(null); setMessage("Perubahan produk diterapkan sementara. Belum tersimpan ke server.");
  }
  return <AppShell>
    <BackendPendingNotice issues={["#40"]} owner="scientivan" />
    <div className="page-head"><div><h1>Manajemen produk</h1><p className="sub">{rows.length} produk sementara · Katalog contoh untuk mencoba pengaturan</p></div>
      <button className="btn btn-primary" onClick={() => { setFailure(""); setEditor("new"); }}>Tambah produk</button></div>
    <div className="note note-info"><span className="icon-chip icon-chip-info"><Icon name="box" /></span><p>Seluruh data produk adalah data sementara. Suhu dan umur simpan pada contoh bukan acuan keamanan pangan.</p></div>
    {message && <p className="note" role="status">{message}</p>}
    <section className="card admin-table-wrap" aria-label="Daftar produk sementara"><table className="admin-table">
      <thead><tr>{["Nama produk", "Rentang suhu", "Referensi umur simpan", "Tindakan"].map(t => <th key={t} scope="col">{t}</th>)}</tr></thead>
      <tbody>{rows.map(p => <tr key={p.id}><th scope="row">{p.name}<div><span className="chip">Belum tersimpan ke server</span></div></th><td className="num">{p.min}–{p.max} °C</td><td className="num">{p.shelfHours} jam</td>
        <td><div className="admin-actions"><button className="btn btn-ghost btn-sm" aria-label={`Edit ${p.name}`} onClick={() => { setFailure(""); setEditor(p); }}><Icon name="edit" />Edit</button>
          <button className="btn btn-ghost btn-sm" aria-label={`Hapus ${p.name}`} onClick={() => { if (window.confirm(`Hapus ${p.name} dari daftar sementara?`)) { setRows(r => deleteProduct(r, p.id)); setMessage("Produk dihapus dari daftar sementara."); } }}><Icon name="trash" />Hapus</button></div></td></tr>)}</tbody>
    </table>{rows.length === 0 && <p className="panel">Belum ada produk. Tambahkan produk untuk mengisi katalog sementara.</p>}</section>
    {editor && <AdminEditor title={editing ? "Edit produk" : "Tambah produk"} onClose={() => setEditor(null)}>
      <form className="admin-form" onSubmit={submit}>
        <label className="field">Nama produk<input autoFocus className="input" name="name" required maxLength={120} defaultValue={editing?.name} /></label>
        <label className="field">Suhu minimum (°C)<input className="input num" name="min" type="number" step="any" required defaultValue={editing?.min} /></label>
        <label className="field">Suhu maksimum (°C)<input className="input num" name="max" type="number" step="any" required defaultValue={editing?.max} /></label>
        <label className="field">Referensi umur simpan (jam)<input className="input num" name="shelfHours" type="number" min="0.01" step="any" required defaultValue={editing?.shelfHours} /></label>
        {failure && <p className="note note-error" role="alert">{failure}</p>}
        <button className="btn btn-primary" type="submit">Terapkan sementara</button>
      </form></AdminEditor>}
  </AppShell>;
}
