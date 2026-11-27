"use client";

// Same origin in production (nginx proxies /api). For `next dev`, set
// NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 so the browser calls the local API.
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";
const KEY = "krio.session";

export type Role = "owner" | "admin" | "viewer";
export type User = { id: string; tenant_id: string; email: string; role: Role };
export type Device = {
  id: string; device_id: string; label: string; link_type: "cellular" | "lora";
  last_seen_at: string | null; reading_at: string | null; temp_c: number | null;
  batt_v: number | null; rh_pct: number | null; rssi: number | null;
  temp_min_c: number | null; temp_max_c: number | null; status: "online" | "offline";
};
export type Shipment = {
  id: string; device_id: string; device_label: string; product_id: string; product_name: string;
  origin: string; destination: string; status: string; started_at: string; ended_at: string | null;
  temp_min_c: number; temp_max_c: number;
};
export type Reading = { ts: string; temp_c: number; count: number };
export type Alert = {
  id: string; device_id: string; shipment_id: string | null; kind: string;
  severity: "info" | "warning" | "critical"; message: string; raised_at: string;
  resolved_at: string | null; acked_by: string | null;
};
export type SimEvent = { sim_s: number; at: string; text: string };
export type Mode = "normal" | "excursion" | "door-open" | "offline";
export type Simulation = {
  id: string; device_id: string; device_code: string; device_label: string; mode: Mode;
  state: "running" | "finished" | "stopped" | "failed"; speed: number; duration_s: number;
  sim_elapsed_s: number; started_at: string; ended_at: string | null; sent: number;
  error: string | null; events: SimEvent[];
};

type Session = { token: string; user: User };

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export function session(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(KEY);
  return raw ? (JSON.parse(raw) as Session) : null;
}

export function signOut() {
  sessionStorage.removeItem(KEY);
  window.location.assign("/login/");
}

export async function signIn(email: string, password: string) {
  const res = await fetch(`${BASE}/api/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new ApiError(res.status, res.status === 401
    ? "Email atau kata sandi tidak cocok."
    : "Server belum bisa dihubungi. Coba lagi sebentar lagi.");
  const body = await res.json();
  sessionStorage.setItem(KEY, JSON.stringify({ token: body.access_token, user: body.user }));
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const current = session();
  let res: Response;
  try {
    res = await fetch(`${BASE}/api${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(current ? { Authorization: `Bearer ${current.token}` } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(0, "Koneksi ke server terputus.");
  }
  if (res.status === 401) {
    signOut();
    throw new ApiError(401, "Sesi berakhir. Silakan masuk lagi.");
  }
  if (!res.ok) {
    let detail = `Permintaan gagal (HTTP ${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch { /* keep default */ }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}
