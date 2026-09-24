# Device Emulator KRIO

Menyimulasikan armada boks pendingin yang mengirim telemetri suhu, menggantikan perangkat keras yang memang berada di luar scope proyek (PRD §8.6 dan risiko R3). Emulator memakai skema payload yang sama persis dengan firmware nyata (`krio.telemetry.v1`, PRD §9.2), sehingga perangkat fisik dapat menggantikannya tanpa mengubah backend.

> Keluaran emulator **tidak pernah** dipakai sebagai data latih maupun data uji model AI (PRD §12.4). Perannya hanya menggerakkan demo dan menguji alerting.

## Menjalankan

```bash
# tiga armada default (2 seluler, 1 LoRa), 6 jam simulasi, keluaran JSON Lines
PYTHONPATH=services python3 -m emulator --duration 6h

# menulis langsung ke PostgreSQL lokal
DATABASE_URL=postgresql://localhost/krio_dev \
  PYTHONPATH=services python3 -m emulator --sink postgres --duration 6h
```

Perangkat harus sudah terdaftar pada tabel `devices`; pesan dari `device_id` yang tidak dikenal dilewati dan dihitung sebagai pesan ditolak, meniru validasi fn_ingest (issue #34).

## Mode simulasi

| Mode | Perilaku | Dipakai menguji |
|---|---|---|
| `normal` | Suhu bertahan di sekitar setpoint, di bawah ambang 4 °C | Dashboard pemantauan (F1) |
| `excursion` | Kompresor gagal pada `--event-start`; suhu menanjak monoton, 4 °C ke 10 °C dalam ~30 menit | Peringatan dini prediktif (F2), alert `KEGAGALAN_PENDINGIN` |
| `door-open` | Lonjakan singkat sekitar +5 °C tiap 30 menit, lalu pulih ke kurva normal | Deteksi anomali (F4), alert `PINTU_DIBUKA` |
| `offline` | Perangkat berhenti mengirim selama `--offline-duration` | Alert `DEVICE_OFFLINE` (issue #49) |

```bash
PYTHONPATH=services python3 -m emulator --devices KRIO-0001:cellular --mode excursion --duration 2h
PYTHONPATH=services python3 -m emulator --mode door-open --duration 3h
PYTHONPATH=services python3 -m emulator --mode offline --offline-duration 45m --duration 3h
```

## Opsi utama

| Opsi | Arti | Default |
|---|---|---|
| `--devices` | Daftar `id:link` dipisah koma | `KRIO-0001:cellular,KRIO-0002:cellular,KRIO-0003:lora` |
| `--mode` | Skenario simulasi | `normal` |
| `--interval` | Interval kirim (detik) | 300 seluler, 600 LoRa (PRD §8.4) |
| `--duration` | Lama simulasi (`90s`, `30m`, `6h`, `1d`) | `6h` |
| `--speed` | `0` secepat mungkin, `1` real-time, `60` satu menit simulasi per detik | `0` |
| `--event-start` | Kapan kejadian mode dimulai | `10m` |
| `--sink` | `stdout` (JSON Lines) atau `postgres` | `stdout` |
| `--seed` | Seed acak agar simulasi dapat diulang | `42` |

## Model termal

Suhu boks mengikuti hukum pendinginan Newton dengan beban panas tambahan:

```
dT/dt = -k · (T - T_target) + Q(t) / C
```

Suhu udara luar mengikuti siklus harian sinusoidal (rata-rata 29 °C, amplitudo 4 °C), dan pembacaan sensor diberi derau Gaussian σ = 0,3 °C sepadan akurasi logger nyata ±1 °C.

Durasi pintu terbuka dipilih 5 menit, batas atas rentang 2–5 menit pada PRD, agar lonjakannya tetap terekam pada interval sampling 5 menit. Dengan durasi 3 menit, lonjakan sering jatuh di antara dua pembacaan sehingga tidak terlihat di basis data.

## Pengujian

```bash
PYTHONPATH=services python3 -m unittest discover -s services/emulator/tests -v
```

Uji mencakup rentang suhu tiap mode, bentuk kurva excursion dan door-open, jeda pengiriman saat offline, `seq` yang monoton naik, kontrak payload beserta batas 512 byte, dan keterulangan simulasi untuk seed yang sama.

## Batasan saat ini

- Tujuan pengiriman baru `stdout` dan `postgres`. Jalur Azure IoT Hub menyusul setelah langganan Azure aktif (issue #22 dan #23); model termal dan payload tidak perlu berubah karena lapisan pengirimannya terpisah.
- Perilaku jaringan pada PRD §8.6 (packet loss, zona tanpa sinyal, store-and-forward, batas airtime LoRa) belum diimplementasikan dan akan menjadi issue tersendiri.
