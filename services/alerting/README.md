# Lapisan Peringatan KRIO

Menerbitkan peringatan dari data `readings` yang sudah masuk basis data:

| Issue | Jenis peringatan | Pemicu |
|---|---|---|
| #48 | `KEGAGALAN_PENDINGIN` | Suhu terukur keluar dari rentang `products.temp_min_c`–`temp_max_c` |
| #49 | `DEVICE_OFFLINE` | Perangkat dengan pengiriman aktif diam lebih dari 10 menit |

Keparahan peringatan suhu: simpangan sampai 5 °C dari batas produk `warning`, di atas 5 °C `critical`.

Peredaman: maksimal satu peringatan per perangkat per jenis dalam 30 menit (suhu) dan 1 jam (offline). Peringatan `DEVICE_OFFLINE` ditutup otomatis (`resolved_at`) begitu perangkat kembali mengirim.

## Struktur

| Berkas | Isi |
|---|---|
| `rules.py` | Keputusan murni: ambang, keparahan, peredaman. Tanpa basis data |
| `repository.py` | Kueri baca/tulis `alerts`, `readings`, `devices`, `products` |
| `scanner.py` | Satu pemindaian lengkap; nanti menjadi isi `fn_alerting` |
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

Uji mencakup perhitungan simpangan, pemetaan keparahan, pelanggaran batas atas dan batas bawah, jendela peredaman 30 menit dan 1 jam, serta perangkat yang belum pernah mengirim.

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
- Jenis `PINTU_DIBUKA` belum dibuat; pembedaan pintu dibuka dari kegagalan pendingin memerlukan deteksi anomali residual (issue F4).
- Jenis `PREDICTED_EXCURSION` milik peringatan dini prediktif (issue #61), bukan lapisan ini.
