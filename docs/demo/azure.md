# Arsitektur demo dan produksi KRIO

## Demo pada satu VM

Jalankan dashboard Next.js, API FastAPI, emulator Python, pemindai alert, dan
PostgreSQL pada **satu VM yang disetujui asisten lab**. Browser penguji membuka
dashboard melalui alamat yang diizinkan lab. API mengakses PostgreSQL melalui
loopback. Jika PDF atau foto masuk cakupan demo, simpan berkas di disk persisten
VM dan sajikan lewat API. Keputusan ini mengikuti izin lab untuk menjalankan
aplikasi dan database bersama pada VM yang diperbolehkan tanpa membuat resource
Azure tambahan.

```text
Browser penguji → Dashboard → API FastAPI → PostgreSQL
                                  ↑               ↑
Panel Simulasi → Emulator → HTTP ingest    Pemindai alert
                                  ↑
                         krio.telemetry.v1
```

1. Operator memilih perangkat dan skenario dari panel Simulasi. Setelah panel
   terintegrasi, API menjalankan emulator di VM. Backend dan panel memakai acuan
   waktu yang sama saat menampilkan hasil simulasi dipercepat.
2. Emulator mengirim telemetri ke `POST /api/ingest`. API memvalidasi pesan,
   menyimpan pembacaan di PostgreSQL, dan memperbarui waktu telemetri terakhir.
3. Pemindai berkala membaca data untuk mendeteksi pelanggaran ambang dan
   perangkat offline, lalu menyimpan alert di PostgreSQL.
4. Dashboard mengambil suhu, status, grafik, dan alert melalui API. Tindakan
   *acknowledge* disimpan melalui API yang sama.

**Status:** backend dan alur emulator HTTP sudah diuji secara lokal. Dashboard
dan panel Simulasi masih mengikuti [issue frontend #103–#106](https://github.com/ZiramBayam/KRIO/issues/90)
dan [issue #110](https://github.com/ZiramBayam/KRIO/issues/110). Nama atau alamat
VM dan cara mengaksesnya belum dikonfirmasi. Jalur App Service dan PostgreSQL
Flexible Server pada issue #100–#102 perlu diperbarui agar mencerminkan
deployment satu VM. Percobaan provisioning Flexible Server sebelumnya ditolak
karena provider belum terdaftar dan tidak membuat server.

## Rancangan saat produk siap digunakan

Gunakan kontrak telemetri dan API yang sudah ada sebagai dasar. Pisahkan
komponen ketika volume data, kebutuhan berbagi berkas, kebutuhan pemulihan,
atau jumlah layanan membuat pemisahan bermanfaat. Rancangan ini mengikuti
[arah arsitektur PRD](../PRD_KRIO_v1.2.md#7-arsitektur-sistem) dan merupakan
target pengembangan.

| Komponen | Rancangan produksi | Pertimbangan |
|---|---|---|
| Perangkat dan ingest | Sensor seluler mengirim ke layanan ingest tepercaya. Sensor LoRaWAN di cold storage mengirim lewat gateway dan Network Server yang menerjemahkan payload sebelum meneruskannya. Azure IoT Hub bisa dipakai sebagai titik masuk jika disetujui. | Sensor berada di lokasi fisik pengiriman. Setiap perangkat punya identitas sendiri dan ingest tetap memvalidasi kontrak `krio.telemetry.v1`. |
| API dan dashboard | Dashboard mengakses API melalui HTTPS. API menangani autentikasi, pembatasan akses tenant, dan akses ke data. Hosting terkelola seperti App Service menjadi opsi saat diperlukan. | Akses browser dan pengiriman telemetri punya kebutuhan autentikasi berbeda. |
| Basis data | PostgreSQL menyimpan telemetri, perangkat, produk, pengiriman, alert, dan metadata berkas. Pertimbangkan PostgreSQL terkelola saat backup dan pemulihan perlu dikelola terpisah dari host aplikasi. | API dan proses terjadwal bisa berbagi data melalui koneksi privat jika tersedia, dengan autentikasi dan TLS sesuai deployment. |
| Pekerjaan terjadwal | Jalankan pemindaian alert, forecast, dan perhitungan umur simpan lewat proses terjadwal. Pisahkan proses dari API saat beban atau kebutuhan penjadwalannya meningkat. | Pemrosesan telemetri dan respons ke pengguna dapat berkembang dengan laju berbeda. |
| Berkas | Simpan PDF, foto ikan, dan artefak model di disk persisten selama satu host melayani semuanya. Gunakan object storage seperti Azure Blob Storage saat beberapa layanan perlu membaca berkas yang sama, volume tumbuh, atau berkas perlu tetap tersedia saat VM diganti. | PostgreSQL menyimpan metadata dan referensi berkas. Object storage mengelola akses dan penyimpanan berkas secara terpisah dari host aplikasi. |
| Notifikasi | Tampilkan alert di dashboard. Tambahkan layanan email seperti Azure Communication Services jika notifikasi keluar aplikasi dibutuhkan dan disetujui. | Pengiriman email mengikuti kebutuhan operasional dan izin penggunaan layanan. |

```text
Sensor seluler ──────────────────────────────┐
Sensor LoRaWAN → Gateway → Network Server ───┴→ Ingest → PostgreSQL
                                                         ↕        ↕
                                  Pemrosesan terjadwal ←─┘        API ↔ Dashboard
                                           │                      ↕
                                           └→ Notifikasi     Penyimpanan berkas
```

1. Ingest menerima pesan perangkat, memvalidasi identitas dan format, lalu
   menyimpan pembacaan dengan waktu pengukuran aslinya. Data yang dikirim ulang
   setelah koneksi pulih mengikuti aturan deduplikasi.
2. Proses terjadwal membaca telemetri dan menulis hasil forecast, perhitungan
   umur simpan, serta alert ke PostgreSQL saat fitur-fitur itu sudah terintegrasi.
   Alert yang memenuhi aturan notifikasi bisa dikirim ke layanan email.
3. API mengambil data dari PostgreSQL untuk dashboard. Saat fitur laporan atau
   foto dipakai, API menyimpan berkas di penyimpanan yang dipilih dan mencatat
   referensinya di PostgreSQL. API memeriksa akses sebelum menyajikan berkas.
4. Saat deployment berkembang, verifikasi bahwa backup PostgreSQL dan berkas
   benar-benar dapat dipulihkan, lalu pantau ingest, alert, dan uptime API.

## Langkah berikutnya

1. Konfirmasi VM yang diizinkan, akses SSH tim, dan alamat HTTPS yang bisa
   digunakan penguji. Sambil menunggu, lanjutkan integrasi frontend secara lokal.
2. Sambungkan login, grafik dan status perangkat, lalu daftar dan
   *acknowledge* alert ke [kontrak API](../openapi.yaml). Tambahkan panel Simulasi
   setelah alur dashboard inti bekerja.
3. Deploy komponen demo ke VM yang sama. Jalankan migrasi Alembic dan seed,
   lalu verifikasi health check, tiga perangkat, grafik, dan status alert.
4. Latih empat skenario dari browser. Verifikasi pemulihan perangkat offline
   dan hilangnya alert yang sudah diakui dari daftar aktif. Catat hasil demo
   dan sesuaikan issue deployment #100–#102 dengan cakupan VM yang disetujui.
