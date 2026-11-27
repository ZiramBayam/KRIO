"use client";

import { useEffect, useState } from "react";
import { Icon } from "./Icon";

type Theme = "light" | "dark";
const KEY = "krio.theme";

function apply(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem(KEY, theme);
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    setTheme((document.documentElement.dataset.theme as Theme) ?? "light");
  }, []);

  if (!theme) return null;

  return (
    <div className="theme-toggle" role="group" aria-label="Mode tampilan">
      <span>{theme === "dark" ? "Gelap" : "Terang"}</span>
      <div style={{ display: "flex", gap: 2 }}>
        <button type="button" aria-pressed={theme === "light"} aria-label="Mode terang"
          onClick={() => { apply("light"); setTheme("light"); }}>
          <Icon name="sun" size={16} />
        </button>
        <button type="button" aria-pressed={theme === "dark"} aria-label="Mode gelap"
          onClick={() => { apply("dark"); setTheme("dark"); }}>
          <Icon name="moon" size={16} />
        </button>
      </div>
    </div>
  );
}
