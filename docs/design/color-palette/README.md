# Color Palette KRIO

Token warna antarmuka KRIO untuk light mode dan dark mode.

| Berkas | Isi |
|---|---|
| `tokens.css` | Token warna sebagai CSS custom properties, dipilih lewat `data-theme="light"` atau `data-theme="dark"` |
| `index.html` | Halaman preview: swatch, contoh komponen, dan tabel rasio kontras yang dihitung dari `tokens.css` |

Buka `index.html` langsung di browser untuk melihat preview.

## Aturan pemakaian

- **Kontras.** Seluruh 29 pasangan warna per mode memenuhi WCAG 2.2 AA: minimal 4.5:1 untuk teks, minimal 3:1 untuk komponen UI, ikon, dan garis grafik.
- **Status tidak dibedakan warna saja.** Badge dan kartu status selalu memuat ikon dan label teks: `● Aman`, `▲ Waspada`, `✕ Kritis`, `○ Offline`.
- **Status solid vs badge.** Token `--color-<status>` dipakai untuk ikon, border, dan garis grafik. Teks status di dalam badge memakai pasangan `--color-<status>-fg` di atas `--color-<status>-bg`.

| Status | Arti |
|---|---|
| Aman | Suhu di dalam rentang produk |
| Waspada | Suhu diprediksi melewati ambang (peringatan dini) |
| Kritis | Suhu sudah melewati ambang atau pendingin gagal |
| Offline | Perangkat tidak mengirim data |
