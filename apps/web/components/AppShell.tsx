"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { api, session, signOut, type Alert, type User } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";
import { Icon } from "./Icon";
import { ThemeToggle } from "./ThemeToggle";

const NAV = [
  { href: "/dashboard/", label: "Pemantauan", icon: "grid" },
  { href: "/shipments/", label: "Pengiriman", icon: "box" },
  { href: "/alerts/", label: "Peringatan", icon: "bell" },
  { href: "/simulasi/", label: "Simulasi", icon: "play" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const s = session();
    if (!s) window.location.replace("/login/");
    else setUser(s.user);
  }, []);

  const { data: alerts } = usePoll(() => (session() ? api<Alert[]>("/alerts") : Promise.resolve([])), 10000);
  const critical = (alerts ?? []).filter((a) => a.severity === "critical").length;

  if (!user) return null;
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark"><img src="/krio.svg" alt="" width={32} height={32} /></span>
          <span>KRIO</span>
        </div>
        <nav aria-label="Menu utama">
          {NAV.map((item) => {
            const active = path.startsWith(item.href) || (item.href === "/dashboard/" && path.startsWith("/devices"));
            return (
              <Link key={item.href} href={item.href} className={`nav-item${active ? " active" : ""}`}
                aria-current={active ? "page" : undefined}>
                <Icon name={item.icon} />
                <span>{item.label}</span>
                {item.href === "/alerts/" && critical > 0 && (
                  <span className="nav-count" aria-label={`${critical} peringatan kritis`}>{critical}</span>
                )}
              </Link>
            );
          })}
        </nav>
        <div className="account">
          <ThemeToggle />
          <div className="account-mail">{user.email}</div>
          <div className="account-role">{{ owner: "Pemilik", admin: "Operator", viewer: "Hanya lihat" }[user.role]}</div>
          <button className="btn btn-ghost" onClick={signOut}><Icon name="logout" size={16} /> Keluar</button>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
