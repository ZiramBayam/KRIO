# Lapisan Peringatan KRIO

Menerbitkan peringatan dari data `readings` yang sudah masuk basis data:

| Issue | Jenis peringatan | Pemicu |
|---|---|---|
| #48 | `KEGAGALAN_PENDINGIN` (ambang) | Suhu terukur keluar dari rentang `products.temp_min_c`–`temp_max_c` |
| #49 | `DEVICE_OFFLINE` | Perangkat dengan pengiriman aktif diam lebih dari 10 menit |
| #62 | `PINTU_DIBUKA` / `KEGAGALAN_PENDINGIN` (residual) | Residual r(t) = T_terukur - T_prediksi melebihi 3σ; durasi < 15 menit & kembali normal → `PINTU_DIBUKA` (info), durasi ≥ 20 menit & CUSUM naik → `KEGAGALAN_PENDINGIN` (critical) |

Keparahan peringatan suhu ambang (#48): simpangan sampai 5 °C dari batas produk `warning`, di atas 5 °C `critical`.

Peredaman: maksimal satu peringatan per perangkat per jenis dalam 30 menit (suhu) dan 1 jam (offline). Peringatan `DEVICE_OFFLINE` ditutup otomatis (`resolved_at`) begitu perangkat kembali mengirim.

**Catatan #48 vs #62:** keduanya menghasilkan `kind=KEGAGALAN_PENDINGIN` tapi lewat jalur berbeda — `evaluate_threshold` (ambang statis per produk) dan `residual.detect_events` (statistik residual + CUSUM, baru bisa membedakan pintu dibuka dari kegagalan sungguhan). Belum digabung dalam satu `scan()`; lihat `residual.py` dan `ml/calibration/` untuk status #62.

## Struktur

| Berkas | Isi |
|---|---|
| `rules.py` | Keputusan murni: ambang, keparahan, peredaman, konstanta `kind`. Tanpa basis data |
| `residual.py` | Deteksi anomali residual + CUSUM (#62): `PINTU_DIBUKA` vs `KEGAGALAN_PENDINGIN`. Murni, belum dipanggil dari `scanner.py` |
| `repository.py` | Kueri baca/tulis `alerts`, `readings`, `devices`, `products` |
| `scanner.py` | Satu pemindaian lengkap (ambang #48 + offline #49); nanti menjadi isi `fn_alerting` |
| `__main__.py` | CLI `python -m alerting` |

## Menjalankan

```bash
DATABASE_URL=postgresql://localhost/krio_dev PYTHONPATH=services python3 -m alerting

# tanpa menulis apa pun
PYTHONPATH=services python3 -m alerting --dsn postgresql://localhost/krio_dev --dry-run

# waktu acuan khusus untuk pemeriksaan offline (dipakai saat menguji data simulasi)
PYTHONPATH=services python3 -m alerting --now 2026-10-02T14:19:50+00:00
```

Keluaran berupa JSON ringkasan: jumlah perangkat diperiksa, peringatan suhu, peringatan offline, dan peringatan offline yang ditutup.

## Pengujian

```bash
PYTHONPATH=services python3 -m unittest discover -s services/alerting/tests -v
```

Uji mencakup perhitungan simpangan, pemetaan keparahan, pelanggaran batas atas dan batas bawah, jendela peredaman 30 menit dan 1 jam, perangkat yang belum pernah mengirim, serta deteksi residual + CUSUM (`PINTU_DIBUKA`/`KEGAGALAN_PENDINGIN`, zona abu-abu 15-20 menit, event tidak diulang dalam satu episode).

Kalibrasi ambang `residual.py` pada Dataset B (NAB realKnownCause) ada di `ml/calibration/` — lihat `ml/reports/dataset_b_calibration.md` untuk hasil dan perbandingan baseline.

### Uji ujung ke ujung dengan emulator

```bash
createdb krio_alert
psql -X -d krio_alert -f services/ingest/db/migrations/0001_init.sql
# isi tenant, produk, perangkat, dan pengiriman aktif, lalu:
DATABASE_URL=postgresql://localhost/krio_alert PYTHONPATH=services \
  python3 -m emulator --devices KRIO-0001:cellular --mode excursion --duration 2h --sink postgres
DATABASE_URL=postgresql://localhost/krio_alert PYTHONPATH=services python3 -m alerting
```

Emulator menuliskan stempel waktu simulasi yang berjalan lebih cepat daripada waktu nyata. Untuk memeriksa `DEVICE_OFFLINE` pada data simulasi, jalankan pemindai dengan `--now` beberapa menit setelah pembacaan terakhir.

## Batasan saat ini

- Pemindaian dijalankan manual lewat CLI. Pemicu waktu Azure Functions menyusul setelah Function App aktif (issue #26); logikanya tidak perlu berubah karena `scan()` sudah terpisah dari cara pemanggilan.
- `residual.py` (#62) sudah ada dan teruji, tapi **belum dipanggil dari `scanner.py`** — `scan_thresholds`/`scan_offline` saat ini tidak menyertakan deteksi residual. Alasannya: `detect_events` butuh T_prediksi(t) dari tabel `forecasts`, yang masih kosong karena model forecast (#58) dan `fn_forecast` (#60) belum selesai. Begitu keduanya ada, tambahkan `scan_residual(repo, result, now)` yang mengambil pasangan (reading, forecast terdekat) per perangkat dan memanggil `residual.detect_events`.
- Ambang kalibrasi `residual.py` saat ini (lihat `ml/reports/dataset_b_calibration.md`) dihasilkan dari baseline persistence/moving-average sebagai pengganti sementara model forecast — WAJIB dikalibrasi ulang begitu residual sungguhan tersedia.
- Jenis `PREDICTED_EXCURSION` milik peringatan dini prediktif (issue #61), bukan lapisan ini.
