# Kalibrasi Residual + CUSUM — Dataset B (#62, F4)

**Kedua baseline di bawah ini adalah pengganti sementara untuk model forecast LightGBM sungguhan (issue #58 belum dikerjakan).** Ambang hasil kalibrasi ini WAJIB dikalibrasi ulang begitu #58/#60 selesai dan residual sungguhan dari `forecasts` tersedia — angka di sini adalah bukti bahwa logika deteksi di `services/alerting/residual.py` bekerja dan tahap kalibrasinya sudah disiapkan, bukan ambang final untuk produksi.

## Ringkasan perbandingan baseline

| Baseline | Sigma (°F) | k | Window tertangkap |
|---|---|---|---|
| persistence (T(t-5menit)) | 1.0463 | 0.5 | 2/4 |
| moving_average (rata-rata 1 jam) | 2.0322 | 0.5 | 4/4 |

**Temuan utama:** baseline `persistence` gagal menangkap window anomali yang berbentuk drift landai (bukan lonjakan tajam) — begitu suhu berubah, T_prediksi(t) langsung 'mengikuti' nilai baru dalam 1 langkah (5 menit), sehingga residual kembali kecil meski suhu sebenarnya masih jauh dari kondisi normal. Ini BUKAN soal tuning k (lihat grid persistence: hasil identik di semua nilai k) — baseline `moving_average` (12 langkah) mengingat kondisi lebih lama sebelum ikut bergeser, sehingga residual tetap elevated lebih lama saat drift terjadi. **Baseline yang dipakai untuk hasil akhir: `moving_average_1h`** (4/4 window tertangkap).

## Baseline: `persistence`

- Baris dipakai: 22682
- Sigma (set validasi, n=20414): **1.0463 °F** (ambang 3-sigma = 3.1389 °F)
- k terpilih: **0.5** (dari grid [0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
- Event: 36 total (3 KEGAGALAN_PENDINGIN, 33 PINTU_DIBUKA)
- **Window berlabel tertangkap (recall): 2/4**
- **Event kritis di LUAR window berlabel manapun: 1/3** — proxy kasar false-positive; sebagian bisa jadi anomali nyata yang belum dilabeli NAB (mis. siklus defrost), bukan otomatis kesalahan deteksi, tapi tetap perlu ditinjau manual sebelum dipakai ke data produksi.

| k | event kritis | event pintu-dibuka | window tertangkap |
|---|---|---|---|
| 0.5 | 3 | 33 | 2/4 ← dipilih |
| 1.0 | 3 | 33 | 2/4 |
| 1.5 | 3 | 33 | 2/4 |
| 2.0 | 3 | 33 | 2/4 |
| 2.5 | 3 | 33 | 2/4 |
| 3.0 | 3 | 33 | 2/4 |

Pencocokan per window:

- 2013-12-10 06:25:00 s/d 2013-12-12 05:35:00 — TIDAK tertangkap
- 2013-12-15 17:50:00 s/d 2013-12-17 17:00:00 — tertangkap (1 event)
- 2014-01-27 14:20:00 s/d 2014-01-29 13:30:00 — TIDAK tertangkap
- 2014-02-07 14:55:00 s/d 2014-02-09 14:05:00 — tertangkap (1 event)

Plot: `ml/reports/figures/dataset_b_calibration_persistence.png`

## Baseline: `moving_average_1h`

- Baris dipakai: 22671
- Sigma (set validasi, n=20403): **2.0322 °F** (ambang 3-sigma = 6.0966 °F)
- k terpilih: **0.5** (dari grid [0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
- Event: 64 total (26 KEGAGALAN_PENDINGIN, 38 PINTU_DIBUKA)
- **Window berlabel tertangkap (recall): 4/4**
- **Event kritis di LUAR window berlabel manapun: 21/26** — proxy kasar false-positive; sebagian bisa jadi anomali nyata yang belum dilabeli NAB (mis. siklus defrost), bukan otomatis kesalahan deteksi, tapi tetap perlu ditinjau manual sebelum dipakai ke data produksi.

| k | event kritis | event pintu-dibuka | window tertangkap |
|---|---|---|---|
| 0.5 | 26 | 38 | 4/4 ← dipilih |
| 1.0 | 26 | 38 | 4/4 |
| 1.5 | 26 | 38 | 4/4 |
| 2.0 | 26 | 38 | 4/4 |
| 2.5 | 26 | 38 | 4/4 |
| 3.0 | 26 | 38 | 4/4 |

Pencocokan per window:

- 2013-12-10 06:25:00 s/d 2013-12-12 05:35:00 — tertangkap (1 event)
- 2013-12-15 17:50:00 s/d 2013-12-17 17:00:00 — tertangkap (2 event)
- 2014-01-27 14:20:00 s/d 2014-01-29 13:30:00 — tertangkap (1 event)
- 2014-02-07 14:55:00 s/d 2014-02-09 14:05:00 — tertangkap (1 event)

Plot: `ml/reports/figures/dataset_b_calibration_moving_average_1h.png`

## Keterbatasan yang perlu ditindaklanjuti

- Kedua baseline di atas memakai nilai suhu historis itu sendiri, bukan model forecast — ambang hasil kalibrasi ini adalah titik awal, bukan hasil final. Begitu #58/#60 selesai, ulangi proses ini dengan residual dari tabel `forecasts`.
- Residual persistence bisa 'bocor' satu langkah lag ke depan dari batas window berlabel (lihat docstring `ml/calibration/dataset_b_baseline.py`); moving average punya efek serupa dengan lag lebih panjang.
- Kondisi `PREDICTED_EXCURSION` (prediksi melewati ambang) dan `DEVICE_OFFLINE` (data > 2x interval) ada di luar cakupan modul ini — `DEVICE_OFFLINE` sudah ada di `services/alerting/rules.py::evaluate_offline` (memakai ambang tetap 10 menit, bukan 2x interval per perangkat — perlu diselaraskan terpisah di issue lain), `PREDICTED_EXCURSION` milik issue #61.
- Integrasi ke `services/alerting/scanner.py` (memanggil `detect_events` dengan residual dari tabel `forecasts`) sengaja BELUM dikerjakan karena tabel itu masih kosong (menunggu #58/#60). Fungsi murni di `residual.py` sudah siap dipanggil begitu sumber prediksi tersedia — tinggal mengganti cara residual dihitung, bukan menulis ulang state machine-nya.
- Tampilan linimasa pengiriman untuk event ini adalah pekerjaan frontend, di luar scope.