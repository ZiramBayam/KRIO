"use client";

import { useState, type FormEvent } from "react";
import { Icon } from "@/components/Icon";
import { signIn } from "@/lib/api";

export default function Login() {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      await signIn(String(form.get("email")), String(form.get("password")));
      window.location.assign("/dashboard/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal masuk.");
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <div className="card">
        <div className="card-head" style={{ justifyContent: "flex-start" }}>
          <span className="brand-mark"><Icon name="thermo" /></span>
          <div>
            <h1 style={{ fontSize: 20 }}>Masuk ke KRIO</h1>
            <p className="muted" style={{ marginTop: 2 }}>Pantau suhu boks ikan dari gudang sampai tujuan.</p>
          </div>
        </div>
        <form onSubmit={submit}>
          <label className="field">Email
            <input className="input" name="email" type="email" autoComplete="username" required defaultValue="admin@demo.com" />
          </label>
          <label className="field">Kata sandi
            <input className="input" name="password" type="password" autoComplete="current-password" required />
          </label>
          {error && <div className="note note-error" role="alert">{error}</div>}
          <button className="btn btn-primary" disabled={busy}>{busy ? "Memproses..." : "Masuk"}</button>
        </form>
      </div>
    </div>
  );
}
