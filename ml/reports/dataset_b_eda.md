# EDA Dataset B — NAB realKnownCause (#56)

Sumber: https://github.com/numenta/NAB — lisensi **MIT** (dicek langsung dari
`LICENSE.txt` di root repo NAB, bukan diasumsikan; catatan sebelumnya yang
menduga AGPL perlu dikoreksi — repo NAB memakai MIT).

## `machine_temperature_system_failure.csv`

- Baris: **22683** | Rentang waktu: 2013-12-02 21:15:00 s/d 2014-02-19 15:25:00
- Interval sampling (median): **5.0 menit**
- Duplikat timestamp dibuang: 12
- Urut monoton naik: True
- Gap > 1.5x interval median: **0** (gap terbesar: 0 menit)
- Nilai (°F): min 2.08, max 108.51, mean 85.92, std 13.75
- Nilai (°C, dikonversi): min -16.62, max 42.51, mean 29.96, std 7.64

### Window anomali berlabel (4)

- 2013-12-10 06:25:00 s/d 2013-12-12 05:35:00 (47.2 jam, 567 titik data) — nilai min/mean/max (°F): 48.39 / 79.05 / 102.74
- 2013-12-15 17:50:00 s/d 2013-12-17 17:00:00 (47.2 jam, 567 titik data) — nilai min/mean/max (°F): 2.08 / 72.85 / 103.62
- 2014-01-27 14:20:00 s/d 2014-01-29 13:30:00 (47.2 jam, 567 titik data) — nilai min/mean/max (°F): 51.25 / 64.69 / 80.31
- 2014-02-07 14:55:00 s/d 2014-02-09 14:05:00 (47.2 jam, 567 titik data) — nilai min/mean/max (°F): 25.89 / 39.48 / 91.33

## `ambient_temperature_system_failure.csv`

- Baris: **7267** | Rentang waktu: 2013-07-04 00:00:00 s/d 2014-05-28 15:00:00
- Interval sampling (median): **60.0 menit**
- Duplikat timestamp dibuang: 0
- Urut monoton naik: True
- Gap > 1.5x interval median: **10** (gap terbesar: 10440 menit)
- Nilai (°F): min 57.46, max 86.22, mean 71.24, std 4.25
- Nilai (°C, dikonversi): min 14.14, max 30.12, mean 21.80, std 2.36

### Window anomali berlabel (2)

- 2013-12-15 07:00:00 s/d 2013-12-30 09:00:00 (362.0 jam, 363 titik data) — nilai min/mean/max (°F): 73.71 / 77.51 / 86.22
- 2014-03-29 15:00:00 s/d 2014-04-20 22:00:00 (535.0 jam, 363 titik data) — nilai min/mean/max (°F): 57.46 / 65.86 / 72.29
