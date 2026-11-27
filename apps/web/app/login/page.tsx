"use client";

import { useState, type FormEvent } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Icon } from "@/components/Icon";
import { signIn } from "@/lib/api";

export default function Login() {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

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
    <main className="login-page">
      <section className="login-main" aria-labelledby="login-heading">
        <header className="login-header">
          <div className="login-brand">
            <span className="brand-mark"><img src="/krio.svg" alt="" /></span>
            <span>KRIO</span>
          </div>
          <ThemeToggle />
        </header>
        <div className="login-body">
          <p className="login-eyebrow">Pemantauan rantai dingin</p>
          <h1 id="login-heading">Masuk ke KRIO</h1>
          <p className="login-intro">Pantau suhu boks ikan dan dapatkan peringatan sebelum produk rusak.</p>
          <form className="login-form" onSubmit={submit} aria-busy={busy}>
            <label className="field">Email
              <input className="input" name="email" type="email" autoComplete="username" required defaultValue="admin@demo.com" />
            </label>
            <label className="field">Kata sandi
              <span className="login-password">
                <input className="input" id="login-password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" required />
                <button className="login-password-toggle" type="button"
                  aria-label={showPassword ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
                  aria-controls="login-password" aria-pressed={showPassword}
                  onClick={() => setShowPassword(!showPassword)}>
                  <Icon name={showPassword ? "eye-off" : "eye"} size={20} />
                </button>
              </span>
            </label>
            {error && <div className="note note-error" role="alert">{error}</div>}
            <button className="btn btn-primary login-submit" type="submit" disabled={busy}>{busy ? "Memproses..." : "Masuk"}</button>
          </form>
        </div>
        <footer className="login-footer">Dari gudang sampai tujuan, suhu tetap terpantau.</footer>
      </section>
      <aside className="login-hero" aria-label="Rantai dingin ikan segar">
        <div className="login-hero-copy">
          <p className="login-eyebrow">Untuk usaha distribusi ikan</p>
          <h2>Ikan segar.<br />Perjalanan terjaga.</h2>
          <p>Pantau suhu sepanjang pengiriman, agar Anda tahu kapan perlu bertindak.</p>
        </div>
      </aside>
    </main>
  );
}
