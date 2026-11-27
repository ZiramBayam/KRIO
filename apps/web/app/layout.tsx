import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KRIO Dashboard",
  description: "Pemantauan rantai dingin ikan segar",
};

const THEME_INIT = `(function(){
  try {
    var saved = localStorage.getItem("krio.theme");
    var theme = saved === "light" || saved === "dark" ? saved
      : matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    document.documentElement.dataset.theme = theme;
  } catch (e) {}
})();`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="id" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
