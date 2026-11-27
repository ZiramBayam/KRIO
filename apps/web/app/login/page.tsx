"use client";

import { useState, type FormEvent } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Icon } from "@/components/Icon";
import { BackendPendingNotice } from "@/components/BackendPendingNotice";
import { signIn } from "@/lib/api";
import { mockRegister } from "@/lib/mockAuth";

interface SideProps {
  onSwitchSide: () => void;
}

export function RegisterSide({ onSwitchSide }: SideProps) {
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    const email = String(form.get("email") ?? "").trim();
    const company = String(form.get("company") ?? "").trim();
    const password = String(form.get("password") ?? "");
    const passwordConfirm = String(form.get("password_confirm") ?? "");

    setError(null);
    setSuccess(null);

    if (password !== passwordConfirm) {
      setError("Konfirmasi kata sandi tidak cocok.");
      return;
    }

    setBusy(true);
    try {
      await mockRegister({ name, email, company, password });
      setSuccess("Pendaftaran berhasil! Mengalihkan ke halaman masuk...");
      setTimeout(() => {
        onSwitchSide();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal mendaftar.");
      setBusy(false);
    }
  }

  return (
    <div className="login-page auth-face-register">
      <aside className="login-hero login-hero-register" aria-label="Rantai dingin ikan segar">
        <div className="login-hero-copy">
          <p className="login-eyebrow">Untuk usaha distribusi ikan</p>
          <h2>Gabung dan mulai pantau suhu pengiriman Anda.</h2>
          <p>Pantau kualitas dan suhu boks ikan segar secara langsung dari gudang hingga ke tangan pelanggan.</p>
          <div className="login-switch-action">
            <span>Sudah punya akun?</span>{" "}
            <button type="button" className="login-switch-link" onClick={onSwitchSide}>
              Masuk
            </button>
          </div>
        </div>
      </aside>
      <section className="login-main" aria-labelledby="register-heading">
        <header className="login-header">
          <div className="login-brand">
            <span className="brand-mark"><img src="/krio.svg" alt="" /></span>
            <span>KRIO</span>
          </div>
          <ThemeToggle />
        </header>
        <div className="login-body">
          <BackendPendingNotice issues={["#36"]} owner="scientivan" />
          <p className="login-eyebrow" style={{ marginTop: 16 }}>Pendaftaran akun baru</p>
          <h1 id="register-heading">Daftar ke KRIO</h1>
          <p className="login-intro">Buat akun untuk memantau pengiriman rantai dingin Anda.</p>
          <form className="login-form" onSubmit={handleRegister} aria-busy={busy}>
            <label className="field">Nama lengkap
              <input className="input" name="name" type="text" autoComplete="name" required placeholder="Budi Santoso" />
            </label>
            <label className="field">Email
              <input className="input" name="email" type="email" autoComplete="email" required placeholder="budi@perusahaan.com" />
            </label>
            <label className="field">Nama perusahaan
              <input className="input" name="company" type="text" autoComplete="organization" required placeholder="PT Samudra Jaya" />
            </label>
            <label className="field">Kata sandi
              <span className="login-password">
                <input className="input" id="register-password" name="password" type={showPassword ? "text" : "password"} autoComplete="new-password" required minLength={8} />
                <button className="login-password-toggle" type="button"
                  aria-label={showPassword ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
                  aria-controls="register-password" aria-pressed={showPassword}
                  onClick={() => setShowPassword(!showPassword)}>
                  <Icon name={showPassword ? "eye-off" : "eye"} size={20} />
                </button>
              </span>
            </label>
            <label className="field">Konfirmasi kata sandi
              <span className="login-password">
                <input className="input" id="register-password-confirm" name="password_confirm" type={showPassword ? "text" : "password"} autoComplete="new-password" required minLength={8} />
              </span>
            </label>
            {error && <div className="note note-error" role="alert">{error}</div>}
            {success && <div className="note note-info" role="status">{success}</div>}
            <button className="btn btn-primary login-submit" type="submit" disabled={busy}>
              {busy ? "Memproses..." : "Daftar"}
            </button>
          </form>
        </div>
        <footer className="login-footer">Dari gudang sampai tujuan, suhu tetap terpantau.</footer>
      </section>
    </div>
  );
}

export function LoginSide({ onSwitchSide }: SideProps) {
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
    <div className="login-page auth-face-login">
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
            <button className="btn btn-primary login-submit" type="submit" disabled={busy}>
              {busy ? "Memproses..." : "Masuk"}
            </button>
          </form>
        </div>
        <footer className="login-footer">Dari gudang sampai tujuan, suhu tetap terpantau.</footer>
      </section>
      <aside className="login-hero" aria-label="Rantai dingin ikan segar">
        <div className="login-hero-copy">
          <p className="login-eyebrow">Untuk usaha distribusi ikan</p>
          <h2>Ikan segar.<br />Perjalanan terjaga.</h2>
          <p>Pantau suhu sepanjang pengiriman, agar Anda tahu kapan perlu bertindak.</p>
          <div className="login-switch-action">
            <span>Belum punya akun?</span>{" "}
            <button type="button" className="login-switch-link" onClick={onSwitchSide}>
              Daftar
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}

export default function LoginPage() {
  const [side, setSide] = useState<"register" | "login">("register");

  return (
    <main>
      {side === "register" ? (
        <RegisterSide onSwitchSide={() => setSide("login")} />
      ) : (
        <LoginSide onSwitchSide={() => setSide("register")} />
      )}
    </main>
  );
}
