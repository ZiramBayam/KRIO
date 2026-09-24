# KRIO — Product Requirements Document

**Sistem Pemantauan Rantai Dingin Prediktif untuk pelaku bisnis Distributor Hasil Laut**

| | |
|---|---|
| **Kelompok** | Manut |
| **Mata Kuliah** | Senior Project (Jaringan Komputer, Komputasi Awan, dan AI) |
| **Institusi** | Laboratorium Jaringan Komputer dan Aplikasi Terdistribusi |
| **Versi Dokumen** | 1.2 — F8 disempurnakan: foto `after` dipindah dari dashboard ke link sekali pakai untuk sopir/kurir, menyelesaikan kontradiksi dengan Persona 2 |
| **Tanggal** | 28 Agustus 2026 |
| **Status** | Draf untuk direview tim |

---

## 1. Ringkasan Eksekutif

KRIO adalah aplikasi web pemantauan rantai dingin yang memberi peringatan **sebelum** produk rusak, bukan sesudahnya.

Perbedaannya dengan produk sejenis terletak pada satu hal: KRIO memprediksi suhu 30–60 menit ke depan dan menerjemahkannya menjadi estimasi sisa umur simpan produk. Data logger konvensional hanya menjelaskan mengapa produk rusak setelah kejadian. Platform enterprise seperti Controlant dan Tive memang memantau secara langsung, tetapi harganya di luar jangkauan pelaku bisnis Indonesia dan analitiknya berorientasi pelaporan kejadian.

**Segmen MVP:** pelaku bisnis distributor ikan segar dan hasil laut, rantai dingin 0–4 °C.

**Tiga keputusan arsitektur yang membedakan dokumen ini dari proposal awal:**

1. **Konektivitas hybrid, bukan LoRaWAN murni.** LoRaWAN untuk titik statis (cold storage), seluler NB-IoT/GSM untuk boks yang bergerak. Alasan lengkap di §8.
2. **Device Emulator sebagai komponen tetap arsitektur**, bukan penambal sementara karena ketiadaan hardware. Kontrak payload-nya identik dengan firmware nyata, sehingga perangkat fisik bisa masuk tanpa mengubah backend.
3. **Model AI dilatih dan diuji sepenuhnya pada dataset publik nyata.** Emulator tidak pernah digunakan sebagai data latih maupun data uji — hanya menggerakkan demo dashboard. Ini menutup celah sirkularitas yang akan ditanyakan penguji.

**Status hardware:** tim tidak memiliki perangkat fisik. Firmware ESP32 dinyatakan **di luar scope** implementasi, tetapi kontrak antarmukanya dispesifikasikan penuh di §9 agar jalur ke perangkat nyata tetap terbuka.

---

## 2. Latar Belakang dan Masalah

### 2.1 Skala kerugian

Kajian *Food Loss and Waste* Kementerian PPN/Bappenas (2021) mencatat Indonesia menghasilkan **23–48 juta ton** kehilangan dan sampah pangan per tahun sepanjang periode 2000–2019, setara **115–184 kg per kapita per tahun**. Potensi kerugian ekonominya mencapai **Rp213–551 triliun per tahun**, atau **4–5% dari Produk Domestik Bruto** nasional.

Sebagian kehilangan itu terjadi pada tahap distribusi dan penyimpanan — tahap yang secara langsung bergantung pada kualitas infrastruktur rantai dingin.

### 2.2 Kerentanan hasil laut

Ikan segar termasuk komoditas paling rentan. Umur simpannya hanya **2–10 hari** tergantung spesies, beban bakteri awal, metode pengemasan, dan kondisi suhu. Laju pembusukannya sangat sensitif terhadap suhu: energi aktivasi degradasi mutu berada pada rentang **49–84 kJ/mol**, dan untuk mikroflora pembusuk **75–85 kJ/mol**. Secara praktis, menaikkan suhu penyimpanan dari 0 °C ke 10 °C memangkas umur simpan menjadi kurang dari setengahnya (§13.2).

### 2.3 Celah yang belum terisi

pelaku bisnis yang menjadi tulang punggung distribusi pangan umumnya masih memeriksa suhu secara manual dan berkala. Metode ini meninggalkan jeda panjang yang tidak terpantau — terutama pada malam hari dan selama kendaraan dalam perjalanan. Solusi otomatis yang tersedia di pasar dirancang untuk korporasi dengan biaya berlangganan yang tidak terjangkau pelaku usaha kecil.

### 2.4 Rumusan masalah

1. Bagaimana merancang sistem pemantauan rantai dingin yang bekerja terus-menerus selama distribusi, **termasuk di wilayah dengan kualitas jaringan terbatas**, tanpa membuat klaim konektivitas yang tidak dapat dipenuhi di lapangan?
2. Bagaimana memanfaatkan kecerdasan buatan untuk **memprediksi** pelanggaran ambang suhu dan mengestimasi sisa umur simpan, sehingga tindakan pencegahan dapat dilakukan sebelum kerusakan terjadi?
3. Bagaimana menyajikan hasil pemantauan dalam aplikasi web yang **terjangkau secara terukur** dan dapat dioperasikan pelaku pelaku bisnis tanpa keahlian teknis khusus?

---

## 3. Target Pengguna

### Persona 1 — Bu Sari, pelaku bisnis (pengguna utama)

Pemilik usaha distribusi ikan segar di Yogyakarta dengan tiga armada pikap berpendingin. Melayani restoran dan pasar swalayan kecil. Melek ponsel, tidak melek teknis. Kerugiannya saat ini tidak terukur — ia hanya tahu ada keluhan pelanggan dan barang retur.

**Yang ia butuhkan:** tahu ada masalah selagi masih bisa ditindaklanjuti, dan bukti tertulis bahwa suhu terjaga ketika pelanggan komplain.

### Persona 2 — Pak Joko, Sopir/Kurir

Membawa satu armada, tiga sampai lima titik antar per hari. Tidak akan membuka dashboard.

**Yang ia butuhkan:** diberi tahu lewat telepon dari Bu Sari kalau ada yang salah. Sistem tidak boleh mengandalkan dia untuk berinteraksi dengan aplikasi. Satu pengecualian sempit: menerima link sekali pakai lewat pesan singkat saat serah-terima di titik tujuan, untuk mengunggah foto kesegaran ikan (`after`, F8) — tanpa login, tanpa melihat dashboard, tanpa data pengiriman lain selain yang terkait link tersebut.

### Persona 3 — Rina, Admin Gudang

Mencatat pengiriman, mendaftarkan boks, menyiapkan laporan bulanan.

**Yang ia butuhkan:** registrasi perangkat yang sederhana, pencatatan pengiriman, dan laporan yang bisa diunduh tanpa mengolah data manual.

---

## 4. Tujuan dan Metrik Keberhasilan

### 4.1 Metrik produk

| Metrik | Target |
|---|---|
| Lead time peringatan sebelum ambang terlampaui | ≥ 30 menit pada ≥ 70% kejadian |
| Alarm palsu | ≤ 1 per perangkat per minggu |
| Waktu dari registrasi sampai data pertama tampil | < 15 menit |
| Ketersediaan dashboard | ≥ 99% selama periode demo |

### 4.2 Metrik model AI

| Metrik | Target | Catatan |
|---|---|---|
| MAE prediksi suhu, horizon 30 menit | ≤ 0,5 °C | Pada shipment uji yang belum pernah dilihat model |
| MAE prediksi suhu, horizon 60 menit | ≤ 1,0 °C | |
| MAE pada segmen excursion saja | Dilaporkan terpisah | Segmen inilah yang penting; rata-rata global menyesatkan |
| Kemenangan atas baseline | **Wajib** mengalahkan *persistence* dan *Newton cooling* | Jika tidak, model tidak dipakai |
| Recall deteksi kegagalan | ≥ 0,9 | Diuji pada NAB (§12.1) |
| Precision deteksi kegagalan | ≥ 0,8 | |

Aturan main: **jika model tidak mengalahkan baseline sederhana, PRD ini mengharuskan tim melaporkannya apa adanya dan memakai baseline.** Dataset yang tersedia berukuran kecil, sehingga kemungkinan ini nyata dan bukan aib.

---

## 5. Scope MVP dan Non-Scope

### 5.1 Di dalam scope

- Aplikasi web dashboard multi-pengguna dengan autentikasi
- Ingest telemetri via Azure IoT Hub dari Device Emulator
- Device Emulator 3 armada dengan model termal fisik dan simulasi perilaku jaringan
- Prediksi suhu horizon 30 dan 60 menit
- Deteksi anomali berbasis residual (bedakan pintu dibuka vs kegagalan pendingin)
- Estimasi sisa umur simpan berbasis Arrhenius/TTI untuk ikan segar
- Deteksi kualitas visual ikan dari foto (mata, insang, tekstur) via kamera ponsel, sebelum dan sesudah pengiriman
- Notifikasi dashboard dan email
- Laporan compliance PDF dengan Mean Kinetic Temperature
- Manajemen perangkat, produk, dan pengiriman

### 5.2 Di luar scope — dinyatakan eksplisit

| Tidak dibangun | Alasan |
|---|---|
| Firmware ESP32 dan perangkat fisik | Tidak ada hardware. Kontrak antarmuka tetap dispesifikasikan (§9) |
| Gateway dan Network Server LoRaWAN | Konsekuensi dari poin di atas; desainnya tetap didokumentasikan (§8) |
| Notifikasi WhatsApp | WhatsApp Business API berbayar dan butuh verifikasi bisnis |
| Aplikasi mobile native | Dashboard web responsif sudah memadai untuk persona |
| Penagihan dan langganan otomatis | Model bisnis didokumentasikan (§14), implementasinya tidak |
| Produk selain ikan segar | Parameter kinetika spesifik per produk; satu segmen dulu |
| Integrasi TMS/ERP pihak ketiga | Pasca-MVP |
| GPS pada jalur LoRa | Keterbatasan payload dan daya (§8.3) |

---

## 6. Fitur dan User Stories

### F1 — Pemantauan Suhu Real-time

> Sebagai pelaku bisnis, saya ingin melihat suhu setiap boks saat ini agar tahu kondisi barang saya tanpa menelepon sopir.

**Acceptance criteria**

- Dashboard menampilkan suhu, kelembapan, tegangan baterai, dan status koneksi tiap perangkat
- Grafik deret waktu dapat di-zoom pada rentang waktu pilihan pengguna
- Lokasi ditampilkan di peta **hanya untuk perangkat jalur seluler**; perangkat jalur LoRa menampilkan lokasi statis terdaftar
- Data yang lebih lama dari 2× interval sampling ditandai "koneksi terputus"
- Latensi dari perangkat mengirim sampai tampil di dashboard < 30 detik

### F2 — Peringatan Dini Prediktif

> Sebagai pelaku bisnis, saya ingin diperingatkan sebelum suhu melewati batas aman agar masih sempat menelepon sopir.

**Acceptance criteria**

- Sistem memprediksi suhu 30 dan 60 menit ke depan, diperbarui tiap 5 menit
- Peringatan terbit ketika suhu **prediksi** melewati ambang produk, bukan suhu terukur
- Peringatan memuat: perangkat, pengiriman, suhu saat ini, suhu prediksi, perkiraan waktu pelanggaran
- Notifikasi dikirim ke dashboard dan email
- Peringatan yang sama tidak diulang dalam 30 menit (peredaman)
- Pengguna dapat menandai peringatan sebagai sudah ditangani

### F3 — Estimasi Sisa Umur Simpan

> Sebagai pelaku bisnis, saya ingin tahu berapa sisa umur ikan saya agar bisa memutuskan mana yang harus dijual duluan.

**Acceptance criteria**

- Menampilkan persentase sisa umur simpan yang terus berjalan per pengiriman
- Perhitungan memakai akumulasi paparan suhu (Arrhenius/TTI, §13)
- Menampilkan pula **proyeksi** sisa umur 60 menit ke depan memakai suhu hasil prediksi
- Parameter kinetika dapat diatur per jenis produk
- Antarmuka menyatakan terbuka bahwa angka ini adalah estimasi berbasis parameter literatur yang belum dikalibrasi lokal

### F4 — Deteksi Anomali Berbasis Residual

> Sebagai pelaku bisnis, saya ingin sistem membedakan pintu boks yang dibuka sebentar dari kompresor yang rusak, supaya saya tidak mengabaikan notifikasi karena terlalu sering salah.

**Acceptance criteria**

- Sistem menghitung residual antara suhu terukur dan suhu prediksi
- Lonjakan singkat yang kembali ke kurva prediksi diklasifikasi **PINTU_DIBUKA** — dicatat sebagai info, tidak memicu alarm
- Residual positif persisten dengan CUSUM menaik diklasifikasi **KEGAGALAN_PENDINGIN** — memicu alarm kritis
- Kedua jenis kejadian tampil di linimasa pengiriman
- Ambang deteksi dapat dikonfigurasi dan nilai awalnya diturunkan dari data validasi

> **Catatan desain penting.** Worksheet awal merancang fitur ini sebagai klasifikasi tersupervisi. Itu tidak dapat dijalankan: tidak tersedia dataset rantai dingin publik yang memiliki anotasi "pintu dibuka" versus "kompresor rusak". Pendekatan residual memakai ulang model prediksi F2 untuk melayani fungsi kedua ini tanpa memerlukan data berlabel, dan divalidasi pada dataset NAB yang memang memuat label kegagalan nyata (§12.1).

### F5 — Laporan Compliance Otomatis

> Sebagai admin gudang, saya ingin mengunduh bukti riwayat suhu satu pengiriman ketika pelanggan komplain.

**Acceptance criteria**

- Menghasilkan PDF per pengiriman: grafik suhu, tabel ringkasan, daftar pelanggaran, nilai **Mean Kinetic Temperature**
- MKT dihitung sesuai rumus USP General Chapter 1079.2 (§13.3)
- Laporan memuat identitas perangkat, penanggung jawab, asal, tujuan, dan stempel waktu
- PDF disimpan di Blob Storage dan dapat diunduh ulang

### F6 — Store-and-Forward dan Sinkronisasi

> Sebagai pelaku bisnis, saya ingin riwayat suhu tetap utuh meski armada melewati daerah tanpa sinyal.

**Acceptance criteria**

- Perangkat menyimpan pembacaan secara lokal saat koneksi terputus
- Saat koneksi pulih, data tertunda dikirim dengan penanda `buffered: true`
- Backend menyisipkan data tertunda pada posisi kronologis yang benar berdasarkan `ts`, bukan waktu terima
- Nomor urut `seq` per perangkat memungkinkan deteksi paket hilang
- Dashboard menampilkan indikator "data tersinkronisasi" pada segmen terkait
- Laju pengiriman backlog dibatasi agar tidak melanggar batas airtime (§8.4)

### F7 — Manajemen Perangkat, Produk, dan Pengiriman

> Sebagai admin gudang, saya ingin mendaftarkan boks baru dan mencatat pengiriman tanpa bantuan teknisi.

**Acceptance criteria**

- Registrasi perangkat: label, jenis jalur (LoRa/seluler), lokasi statis jika berlaku
- Definisi produk: nama, ambang suhu minimum dan maksimum, parameter kinetika
- Pencatatan pengiriman: perangkat, produk, asal, tujuan, penanggung jawab, waktu mulai dan selesai
- Data setiap tenant terisolasi dari tenant lain

### F8 — Deteksi Kualitas Visual Ikan (Computer Vision)

> Sebagai pelaku bisnis, saya ingin memotret kondisi ikan sebelum dan sesudah pengiriman agar punya bukti visual, bukan hanya angka suhu, ketika pelanggan mempertanyakan mutu barang.

**Acceptance criteria**

- Foto `before` diunggah lewat kamera ponsel pada dashboard web oleh pelaku bisnis atau admin gudang, saat pengiriman dimulai
- Foto `after` diunggah lewat **link sekali pakai** yang dikirim ke ponsel sopir/kurir (Persona 2, Pak Joko) via pesan singkat saat serah-terima di titik tujuan — tanpa login, tanpa akses dashboard, hanya kamera dan tombol unggah untuk pengiriman terkait
- Link sekali pakai terikat pada satu `shipment_id`, kedaluwarsa otomatis setelah dipakai satu kali atau setelah jangka waktu tertentu (mis. 24 jam), mana yang lebih dulu
- Sistem mengklasifikasikan kesegaran dari foto mata, insang, atau tekstur daging ke tiga kelas: **Sangat Segar**, **Segar**, **Tidak Segar**, disertai skor keyakinan
- Hasil klasifikasi `before` dan `after` ditampilkan berdampingan pada linimasa pengiriman sebagai validasi silang terhadap estimasi umur simpan berbasis suhu (F3)
- Jika klasifikasi visual dan estimasi berbasis suhu berbeda signifikan (mis. visual "Tidak Segar" padahal suhu terjaga), dashboard menampilkan catatan diskrepansi — bukan menimpa salah satu angka
- Foto dan hasil klasifikasi tersimpan permanen di Blob Storage sebagai bagian dari laporan compliance (F5)
- Antarmuka menyatakan terbuka bahwa model dilatih pada dataset publik spesies ikan yang berbeda dari kondisi lokal, sehingga hasil adalah indikasi, bukan kepastian mutlak (lihat §12.5 dan R11)

> **Kenapa lewat kamera ponsel, bukan kamera pada perangkat sensor.** Tim tidak memiliki hardware (§1, §8.6) dan firmware ESP32 dinyatakan di luar scope. Modul kamera pada boks pendingin juga menambah beban payload dan daya yang tidak sepadan untuk sekadar dua pemotretan per pengiriman. Menaruh fitur ini di lapisan aplikasi web — difoto oleh pelaku bisnis atau admin gudang memakai ponsel yang mereka sudah punya (§3, Persona 1 dan 3) — konsisten dengan batasan hardware yang sama yang mendorong keputusan Device Emulator (§8.6).

> **Kenapa foto `after` lewat link sekali pakai, bukan dashboard biasa.** Titik pengambilan foto `after` adalah lokasi tujuan pengiriman — tempat yang secara realistis hanya didatangi Pak Joko (Persona 2), bukan Bu Sari atau Rina. Persona 2 secara sengaja didefinisikan sebagai bukan pengguna aplikasi (§3): sistem tidak boleh bergantung padanya untuk berinteraksi dengan dashboard. Link sekali pakai menyelesaikan kontradiksi ini tanpa melanggar prinsip tersebut — cakupannya sempit (satu aksi, satu pengiriman, tanpa sesi login), berbeda dari "membuka dashboard". Dua alternatif lain dipertimbangkan dan ditolak: (a) menjadikan pihak penerima/pembeli sebagai pengambil foto berisiko bias insentif — pembeli yang ingin negosiasi harga bisa memotret dari sudut yang membuat ikan tampak kurang segar, merusak validitas foto sebagai bukti compliance; (b) menjadikan foto `after` opsional/best-effort melemahkan nilai inti fitur, karena perbandingan `before`/`after` adalah yang membedakan F8 dari sekadar cek suhu.

---

## 7. Arsitektur Sistem

```
┌─ SUMBER DATA ────────────────────────────────────────────────────────┐
│                                                                      │
│  [Boks statis — cold storage]                                        │
│   ESP32 + DS18B20 + SHT31 + RFM95 (LoRa)                             │
│        │ LoRaWAN AS923                                               │
│        ▼                                                             │
│   LoRaWAN Gateway ──> Network Server (ChirpStack / TTN)              │
│                              │ decode payload biner ──> JSON v1      │
│                              │                                       │
│  [Boks bergerak — armada]    │                                       │
│   ESP32 + sensor + SIM7020 (NB-IoT) + GPS                            │
│        │ MQTT over TLS                                               │
│        ├──────────────────────┤                                      │
│                               │                                      │
│  [Device Emulator (Python)] ──┤  ← kontrak payload identik           │
│   model termal + event +      │                                      │
│   simulasi perilaku jaringan  │                                      │
└───────────────────────────────┼──────────────────────────────────────┘
                                ▼
                    ┌───────────────────────┐
                    │  Azure IoT Hub (F1)   │  MQTT/TLS, device identity
                    └───────────┬───────────┘
                                │ built-in Event Hub endpoint
                                ▼
                    ┌───────────────────────────────────┐
                    │  Azure Functions (Python)         │
                    │  ├ fn_ingest    (Event Hub trig.) │
                    │  ├ fn_forecast  (Timer, 5 menit)  │
                    │  ├ fn_shelflife (Timer, 15 menit) │
                    │  ├ fn_alert     (dipanggil)       │
                    │  └ fn_report    (HTTP trig.)      │
                    └───┬───────────┬───────────────┬───┘
                        │           │               │
            ┌───────────▼──┐  ┌─────▼────────┐  ┌───▼──────────────┐
            │ PostgreSQL   │  │ Blob Storage │  │ Azure Comm.      │
            │ Flexible Srv │  │ model + PDF  │  │ Services (Email) │
            └───────┬──────┘  └──────────────┘  └──────────────────┘
                    │
            ┌───────▼────────────────────┐
            │ Next.js di Azure App Service│ ──> Browser (Bu Sari, Rina)
            └─────────────────────────────┘
```

> **Komponen yang hilang di worksheet awal:** Azure IoT Hub **tidak menerima LoRaWAN secara langsung**. Diperlukan LoRaWAN Network Server (ChirpStack atau The Things Network) yang menerjemahkan uplink biner menjadi JSON dan meneruskannya ke IoT Hub. Komponen ini kini eksplisit dalam diagram.

### 7.1 Pilihan teknologi

| Lapisan | Pilihan | Alasan |
|---|---|---|
| Web + BFF | Next.js (TypeScript) di Azure App Service | App Service sudah ditetapkan; satu artefak deployment |
| Ingest | Azure IoT Hub tier F1 | Gratis, mencukupi skala demo (§8.5) |
| Pemrosesan | Azure Functions, Python 3.11, Consumption plan | Serverless; satu bahasa dengan lapisan ML |
| Basis data | Azure Database for PostgreSQL Flexible Server, B1ms | Cukup untuk skala demo; menghindari kompleksitas TimescaleDB |
| Penyimpanan objek | Azure Blob Storage | Artefak model dan berkas PDF laporan |
| Email | Azure Communication Services Email | Azure-native, tidak menambah vendor |
| ML | LightGBM pada fitur lag, Python | Dataset kecil — gradient boosting umumnya mengungguli deep learning di regime ini |
| Autentikasi | NextAuth (kredensial) + PostgreSQL | Friksi terendah; Entra External ID sebagai alternatif |

### 7.2 Struktur repositori

```
apps/web/          Next.js — dashboard dan API BFF
services/ingest/   Azure Functions (Python) — fn_ingest, fn_forecast, dst.
services/emulator/ Device Emulator — model termal + klien MQTT
ml/                Notebook eksplorasi, skrip latih, evaluasi, artefak model
firmware/          Sketsa referensi ESP32 + dokumen kontrak payload (tidak dibangun)
infra/             Bicep/Terraform untuk provisioning Azure
docs/              Worksheet, ADR, laporan
```

---

## 8. Desain Jaringan

### 8.1 Mengapa bukan LoRaWAN murni

Proposal awal memakai LoRaWAN untuk seluruh kasus, termasuk armada bergerak, dengan alasan LoRa bekerja di wilayah bersinyal seluler lemah. Argumen ini tidak bertahan saat diperiksa:

**LoRaWAN tetap membutuhkan gateway dalam jangkauan.** Kendaraan yang bergerak lintas kota berada di luar jangkauan gateway mana pun kecuali tersedia jaringan LoRaWAN publik di sepanjang rute. Cakupan LoRaWAN publik di Indonesia jauh lebih tipis daripada cakupan seluler. Untuk kasus bergerak, LoRa bukan memperbaiki masalah cakupan — ia memperburuknya.

Bukti pendukung dari lapangan: studi rantai dingin strawberry yang didanai USDA (yang datasetnya justru kami pakai untuk melatih model, §12.1) menginstrumentasi pengiriman lintas benua Amerika Serikat dan memilih **radio seluler GSM** untuk mengirim data dari kendaraan yang bergerak.

### 8.2 Keputusan: hybrid berdasarkan mobilitas

| | **Jalur LoRa** | **Jalur Seluler** |
|---|---|---|
| Kasus pakai | Cold storage, gudang, titik statis | Boks pada armada bergerak |
| Radio | RFM95 (LoRaWAN AS923) | SIM7020 (NB-IoT) atau SIM800L (GSM) |
| Interval sampling | 10 menit | 5 menit |
| Payload | Biner ≤ 12 byte, di-decode Network Server | JSON langsung |
| GPS | Tidak tersedia | Tersedia |
| Biaya berulang | Nol setelah gateway terpasang | Kartu data IoT per perangkat |
| Konsumsi daya | Sangat rendah, tahan berbulan-bulan | Lebih tinggi, perlu isi ulang berkala |
| Ketergantungan | Gateway milik sendiri di lokasi | Cakupan operator seluler |

Prinsipnya sederhana: **perangkat yang diam memakai jaringan yang mensyaratkan gateway diam; perangkat yang bergerak memakai jaringan yang cakupannya mengikuti jalan raya.** Masing-masing dipakai di tempat yang memang menjadi kekuatannya.

### 8.3 Mengapa GPS hanya di jalur seluler

Payload LoRaWAN sangat terbatas dan setiap byte menambah airtime. Koordinat GPS memerlukan sekitar 8 byte tambahan, ditambah modul GPS yang konsumsi dayanya jauh melampaui anggaran daya perangkat LoRa bertenaga baterai. Karena perangkat jalur LoRa memang statis, lokasinya cukup dicatat sekali saat registrasi.

Fitur peta pada dashboard karenanya hanya menampilkan posisi bergerak untuk perangkat jalur seluler. Worksheet awal menjanjikan lokasi armada tanpa menyediakan perangkat GPS di daftar sensornya — inkonsistensi itu diselesaikan di sini.

### 8.4 Interval sampling dan batas airtime

Interval 1 menit dari worksheet awal diturunkan menjadi **5 menit (seluler)** dan **10 menit (LoRa)**. Tiga alasan:

1. **Batas airtime LoRaWAN.** Regulasi dwell-time dan kebijakan penggunaan wajar jaringan publik membatasi total airtime uplink per perangkat per hari. Interval 1 menit melampaui anggaran itu pada faktor penyebaran yang realistis.
2. **Kesesuaian dengan data latih.** Dataset rantai dingin nyata yang dipakai melatih model mencatat pada interval 5–10 menit. Menyamakan interval operasional dengan interval data latih menghilangkan ketidaksesuaian domain yang tidak perlu.
3. **Fisika termal boks bersifat lambat.** Massa termal boks pendingin membuat perubahan suhu berarti berlangsung dalam hitungan puluhan menit. Sampling 1 menit sebagian besar hanya merekam derau sensor.

**Konsekuensi untuk F6 (store-and-forward).** Worksheet awal menjanjikan sinkronisasi otomatis seluruh backlog saat koneksi pulih. Pada jalur LoRa hal itu justru melanggar batas airtime — burst backlog persis yang dibatasi. Karena itu:

- Jalur seluler: backlog dikirim penuh, dibatasi laju maksimum 10 pesan per menit
- Jalur LoRa: backlog dikirim dengan **penurunan resolusi** — rata-rata per 30 menit untuk data tertunda, bukan setiap pembacaan

Riwayat tetap utuh secara bermakna tanpa melanggar batasan radio.

### 8.5 Anggaran kuota Azure IoT Hub

Tier gratis F1 memberi **8.000 pesan per hari** dengan ukuran hitung 0,5 KB per pesan, dan satu hub gratis per langganan.

| | Perhitungan | Hasil |
|---|---|---|
| Pesan per perangkat seluler per hari | 24 jam × 60 menit ÷ 5 menit | 288 |
| Skala demo (3 armada) | 3 × 288 | **864 pesan/hari** |
| Pemakaian kuota F1 | 864 ÷ 8.000 | **10,8%** |
| Kapasitas maksimum di F1 | 8.000 ÷ 288 | ~27 perangkat |

Skala demo dibatasi 3 armada bukan semata karena keterbatasan sumber daya, melainkan sebagai keputusan sadar agar seluruh sistem berjalan di tier gratis dan kredit Azure student tetap aman. Payload dirancang di bawah 512 byte agar satu pesan tetap dihitung satu kuota.

### 8.6 Device Emulator

Emulator adalah komponen tetap arsitektur, bukan penambal sementara. Ia mensimulasikan armada boks dan mengirim ke IoT Hub melalui **topic dan skema payload yang persis sama** dengan firmware nyata (§9), sehingga perangkat fisik dapat menggantikannya tanpa satu baris pun perubahan di backend.

**Model termal** mengikuti hukum pendinginan Newton:

```
dT/dt = -k · (T - T_target)  +  Q_beban(t) / C
```

dengan `k` konstanta perpindahan panas boks, `T_target` setpoint pendingin, dan `Q_beban(t)` beban panas dari lingkungan dan kejadian.

**Kejadian yang disimulasikan**

| Kejadian | Perilaku |
|---|---|
| Pintu dibuka | `Q_beban` melonjak 2–5 menit, lalu suhu pulih ke kurva normal |
| Kegagalan kompresor | `T_target` naik permanen; suhu menanjak monoton |
| Suhu ambien harian | Fungsi sinusoidal mengikuti siklus siang-malam |
| Derau sensor | Gaussian, σ = 0,3 °C, sepadan akurasi logger nyata ±1 °C |

**Perilaku jaringan yang disimulasikan** — inilah yang membuat dimensi jaringan komputer dapat diukur, bukan sekadar diklaim:

| Perilaku | Implementasi |
|---|---|
| Packet loss | Probabilitas drop yang dapat dikonfigurasi per jalur |
| Zona tanpa sinyal | Jendela waktu terjadwal tanpa konektivitas |
| Store-and-forward | Antrean lokal, dikirim ulang saat pulih dengan `buffered: true` |
| Batas airtime LoRa | Penegakan anggaran airtime; pelanggaran dicatat, tidak dikirim |
| Nomor urut | `seq` monoton agar paket hilang dapat dihitung di backend |

**Aturan yang mengikat:** keluaran emulator **tidak pernah** dipakai sebagai data latih maupun data uji model AI. Perannya terbatas pada menggerakkan demo dashboard. Alasan lengkap di §12.4.

---

## 9. Kontrak Perangkat

Kontrak ini berlaku sama untuk Device Emulator dan firmware ESP32 masa depan.

### 9.1 Topic MQTT

Mengikuti konvensi Azure IoT Hub:

```
devices/{device_id}/messages/events/
```

Autentikasi memakai identitas per perangkat pada IoT Hub (SAS token atau sertifikat X.509). Transport MQTT over TLS 1.2.

### 9.2 Skema payload — `krio.telemetry.v1`

```json
{
  "schema": "krio.telemetry.v1",
  "device_id": "KRIO-0001",
  "ts": "2026-08-28T09:15:00Z",
  "link": "cellular",
  "seq": 10432,
  "temp_c": 2.4,
  "rh_pct": 78.1,
  "batt_v": 3.91,
  "rssi": -87,
  "gps": { "lat": -7.7956, "lon": 110.3695 },
  "buffered": false
}
```

| Field | Tipe | Wajib | Keterangan |
|---|---|---|---|
| `schema` | string | ya | Versi kontrak; backend menolak versi tak dikenal |
| `device_id` | string | ya | Sama dengan identitas perangkat di IoT Hub |
| `ts` | ISO 8601 UTC | ya | **Waktu pengukuran**, bukan waktu pengiriman |
| `link` | enum | ya | `lora` atau `cellular` |
| `seq` | integer | ya | Monoton naik per perangkat; dipakai mendeteksi paket hilang |
| `temp_c` | float | ya | Derajat Celsius, presisi 0,01 |
| `rh_pct` | float | tidak | Kelembapan relatif |
| `batt_v` | float | tidak | Tegangan baterai |
| `rssi` | integer | tidak | Kekuatan sinyal, dBm |
| `gps` | object\|null | tidak | **Selalu `null` pada `link: "lora"`** |
| `buffered` | boolean | ya | `true` jika hasil sinkronisasi tertunda |

**Aturan wajib**

- Ukuran payload harus < 512 byte agar dihitung satu kuota pesan IoT Hub
- `ts` menentukan urutan kronologis di basis data — data `buffered` disisipkan sesuai `ts`, bukan waktu terima
- Backend menolak dan mencatat payload yang gagal validasi skema; ia tidak boleh menggagalkan pemrosesan pesan lain

### 9.3 Payload biner jalur LoRa

Uplink LoRaWAN memakai bentuk padat, di-decode oleh Network Server menjadi JSON di atas:

| Offset | Ukuran | Field | Penyandian |
|---|---|---|---|
| 0 | 2 byte | `temp_c` | int16, satuan 0,01 °C |
| 2 | 1 byte | `rh_pct` | uint8, persen bulat |
| 3 | 1 byte | `batt_v` | uint8, satuan 0,02 V |
| 4 | 2 byte | `seq` | uint16, berputar |
| 6 | 1 byte | flags | bit 0 = `buffered`, bit 1–7 cadangan |

Total **7 byte** — jauh di bawah batas payload AS923 pada faktor penyebaran manapun. Network Server mengisi `device_id`, `ts`, `link`, dan `gps: null`.

---

## 10. Skema Data

PostgreSQL. Nama tabel dan kolom dalam bahasa Inggris mengikuti konvensi umum; isi domainnya dalam bahasa Indonesia.

```sql
tenants (
  id            uuid PRIMARY KEY,
  name          text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
)

users (
  id            uuid PRIMARY KEY,
  tenant_id     uuid NOT NULL REFERENCES tenants(id),
  email         citext NOT NULL UNIQUE,
  password_hash text NOT NULL,
  role          text NOT NULL,           -- 'owner' | 'admin' | 'viewer'
  created_at    timestamptz NOT NULL DEFAULT now()
)

products (
  id                uuid PRIMARY KEY,
  tenant_id         uuid NOT NULL REFERENCES tenants(id),
  name              text NOT NULL,       -- 'Ikan segar (utuh, dalam es)'
  temp_min_c        real NOT NULL,       -- 0.0
  temp_max_c        real NOT NULL,       -- 4.0
  ea_j_per_mol      real NOT NULL,       -- 60000
  t_ref_k           real NOT NULL,       -- 273.15
  shelf_life_ref_h  real NOT NULL        -- 240 (10 hari pada T_ref)
)

devices (
  id            uuid PRIMARY KEY,
  tenant_id     uuid NOT NULL REFERENCES tenants(id),
  device_id     text NOT NULL UNIQUE,    -- 'KRIO-0001', sama dengan IoT Hub
  label         text NOT NULL,
  link_type     text NOT NULL,           -- 'lora' | 'cellular'
  static_lat    double precision,        -- hanya untuk link_type='lora'
  static_lon    double precision,
  registered_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at  timestamptz
)

shipments (
  id             uuid PRIMARY KEY,
  tenant_id      uuid NOT NULL REFERENCES tenants(id),
  device_id      uuid NOT NULL REFERENCES devices(id),
  product_id     uuid NOT NULL REFERENCES products(id),
  origin         text NOT NULL,
  destination    text NOT NULL,
  handler_name   text,
  started_at     timestamptz NOT NULL,
  ended_at       timestamptz,
  status         text NOT NULL           -- 'active' | 'completed' | 'aborted'
)

readings (
  device_id  uuid NOT NULL REFERENCES devices(id),
  ts         timestamptz NOT NULL,
  seq        bigint NOT NULL,
  temp_c     real NOT NULL,
  rh_pct     real,
  batt_v     real,
  rssi       smallint,
  lat        double precision,
  lon        double precision,
  buffered   boolean NOT NULL DEFAULT false,
  PRIMARY KEY (device_id, ts)
) PARTITION BY RANGE (ts);
-- Partisi bulanan. Indeks: (device_id, ts DESC)

forecasts (
  id             bigserial PRIMARY KEY,
  device_id      uuid NOT NULL REFERENCES devices(id),
  issued_at      timestamptz NOT NULL,   -- kapan prediksi dibuat
  horizon_min    smallint NOT NULL,      -- 30 | 60
  target_ts      timestamptz NOT NULL,   -- issued_at + horizon
  predicted_c    real NOT NULL,
  model_version  text NOT NULL
)

alerts (
  id             uuid PRIMARY KEY,
  tenant_id      uuid NOT NULL REFERENCES tenants(id),
  shipment_id    uuid REFERENCES shipments(id),
  device_id      uuid NOT NULL REFERENCES devices(id),
  kind           text NOT NULL,          -- 'PREDICTED_EXCURSION'
                                         -- | 'KEGAGALAN_PENDINGIN'
                                         -- | 'PINTU_DIBUKA'
                                         -- | 'DEVICE_OFFLINE'
  severity       text NOT NULL,          -- 'info' | 'warning' | 'critical'
  raised_at      timestamptz NOT NULL,
  predicted_for  timestamptz,            -- kapan pelanggaran diperkirakan terjadi
  resolved_at    timestamptz,
  acked_by       uuid REFERENCES users(id),
  message        text NOT NULL
)

shelf_life_state (
  shipment_id       uuid PRIMARY KEY REFERENCES shipments(id),
  updated_at        timestamptz NOT NULL,
  accumulated_decay real NOT NULL,       -- D, tak berdimensi; 1.0 = habis
  remaining_pct     real NOT NULL,
  projected_pct_60m real,
  mkt_c             real
)

fish_quality_checks (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES tenants(id),
  shipment_id     uuid NOT NULL REFERENCES shipments(id),
  stage           text NOT NULL,          -- 'before' | 'after'
  photo_url       text NOT NULL,          -- path di Blob Storage
  freshness_class text NOT NULL,          -- 'sangat_segar' | 'segar' | 'tidak_segar'
  confidence      real NOT NULL,          -- 0.0–1.0
  model_version   text NOT NULL,
  upload_channel  text NOT NULL,          -- 'dashboard' | 'one_time_link'
  uploaded_by     uuid REFERENCES users(id),  -- NULL jika via one_time_link (Pak Joko bukan users)
  link_id         uuid REFERENCES shipment_photo_links(id),  -- NULL jika via dashboard
  created_at      timestamptz NOT NULL DEFAULT now()
)

shipment_photo_links (
  id            uuid PRIMARY KEY,
  tenant_id     uuid NOT NULL REFERENCES tenants(id),
  shipment_id   uuid NOT NULL REFERENCES shipments(id),
  stage         text NOT NULL,          -- 'after' (saat ini hanya dipakai untuk tahap after)
  token         text NOT NULL UNIQUE,   -- dikirim via SMS/WhatsApp ke sopir
  expires_at    timestamptz NOT NULL,   -- created_at + 24 jam
  used_at       timestamptz,            -- NULL sampai dipakai; sekali dipakai, token mati
  created_by    uuid NOT NULL REFERENCES users(id),
  created_at    timestamptz NOT NULL DEFAULT now()
)
```

**Catatan implementasi**

- Seluruh kueri dashboard **wajib** difilter `tenant_id`; isolasi tenant ditegakkan di lapisan kueri
- `readings` dipartisi bulanan agar pemangkasan retensi berupa `DROP PARTITION`, bukan `DELETE` massal
- Retensi mengikuti tier langganan (§14.2); pemangkasan dijalankan oleh Function terjadwal

---

## 11. Spesifikasi API

Seluruh endpoint di bawah `/api`, memerlukan sesi terautentikasi, dan tercakup `tenant_id` dari sesi — **kecuali endpoint di bawah `/api/public`**, yang disengaja tanpa autentikasi sesi karena dipakai oleh Pak Joko (Persona 2) lewat link sekali pakai, tanpa login (lihat F8).

| Metode | Endpoint | Keterangan |
|---|---|---|
| `GET` | `/api/devices` | Daftar perangkat beserta pembacaan terakhir dan status koneksi |
| `POST` | `/api/devices` | Registrasi perangkat baru |
| `PATCH` | `/api/devices/:id` | Ubah label atau lokasi statis |
| `GET` | `/api/products` | Daftar produk beserta ambang dan parameter kinetika |
| `POST` | `/api/products` | Buat definisi produk |
| `GET` | `/api/shipments` | Daftar pengiriman, dapat difilter status |
| `POST` | `/api/shipments` | Mulai pengiriman baru |
| `PATCH` | `/api/shipments/:id` | Akhiri atau batalkan pengiriman |
| `GET` | `/api/shipments/:id/readings?from=&to=&bucket=` | Deret waktu; `bucket` melakukan agregasi sisi server |
| `GET` | `/api/shipments/:id/forecast` | Prediksi horizon 30 dan 60 menit terkini |
| `GET` | `/api/shipments/:id/shelf-life` | Sisa umur simpan saat ini dan proyeksinya |
| `POST` | `/api/shipments/:id/quality-checks` | Unggah foto `stage: before` dari dashboard; backend menjalankan klasifikasi dan menyimpan hasil |
| `GET` | `/api/shipments/:id/quality-checks` | Daftar hasil klasifikasi visual `before`/`after` untuk pengiriman ini |
| `POST` | `/api/shipments/:id/photo-links` | Admin/owner membuat link sekali pakai untuk foto `after`; mengembalikan URL + token, dikirim manual ke sopir via SMS/WhatsApp |
| `GET` | `/api/public/photo-links/:token` | **Tanpa sesi.** Validasi token (belum kedaluwarsa, belum dipakai) sebelum menampilkan form unggah ke sopir |
| `POST` | `/api/public/photo-links/:token/upload` | **Tanpa sesi.** Unggah foto `after` via token; backend menjalankan klasifikasi, menyimpan hasil dengan `upload_channel: one_time_link`, lalu menandai token sebagai terpakai |
| `GET` | `/api/shipments/:id/report` | Menghasilkan atau mengambil PDF compliance |
| `GET` | `/api/alerts?status=` | Daftar peringatan |
| `POST` | `/api/alerts/:id/ack` | Tandai peringatan sudah ditangani |

**Konvensi**

- Seluruh stempel waktu ISO 8601 UTC
- Deret waktu dipaginasi dengan kursor; `bucket` (`1m`/`5m`/`1h`) mengagregasi di sisi server agar payload dashboard tetap ringan
- Galat mengembalikan `{ "error": { "code": string, "message": string } }` dengan kode status HTTP yang sesuai
---

## 12. Desain Kecerdasan Buatan

### 12.1 Sumber data

Model dilatih dan diuji **sepenuhnya pada dataset publik nyata**. Dua dataset dipakai untuk dua tujuan berbeda.

**Dataset A — dinamika termal rantai dingin nyata**

*A Time-Temperature Dataset for the Strawberry Cold Chain Across Multiple Shipments and Locations* (Abdella, Brecht, Uysal — University of South Florida & University of Florida; didanai USDA dan FDACS).

| | |
|---|---|
| Cakupan | 6 pengiriman nyata lintas benua Amerika Serikat |
| Instrumentasi | 3 palet per pengiriman × 3 logger vertikal = 9 titik ukur; total 54 titik |
| Perangkat | DeltaTrak Reusable Real-Time Logger Mini, akurasi ±1 °C |
| Interval | 5 menit (pengiriman 1), 10 menit (pengiriman 2–6) |
| Durasi | 2 hari 1 jam sampai 6 hari 14 jam per pengiriman |
| Cakupan tahap | Panen, prapendinginan ke 0 °C, dan transportasi |
| Rute | Plant City (Florida) dan Salinas (California) menuju MD, PA, VA, SC, NC, GA, TX |
| Transmisi | Radio seluler GSM secara real-time dari lapangan |
| Lisensi | CC BY 4.0 |

**Mengapa data strawberry sah dipakai untuk produk ikan.** Ini pertanyaan yang hampir pasti diajukan penguji, dan jawabannya terletak pada pemisahan lapisan:

> Model deret waktu memprediksi **suhu di dalam boks**. Itu adalah fisika perpindahan panas wadah berpendingin — massa termal, insulasi, siklus kompresor, beban ambien — dan sama sekali tidak bergantung pada biologi produk di dalamnya. Setpoint prapendinginan strawberry (0 °C) berimpit dengan rentang rantai dingin ikan segar (0–4 °C), sehingga rezim termalnya sebanding.
>
> Sifat spesifik ikan tidak masuk ke model AI sama sekali. Ia masuk **satu lapisan di atasnya**, pada perhitungan Arrhenius (§13), lewat parameter kinetika ikan dari literatur.

Pemisahan ini disengaja: lapisan yang bergantung pada produk dibuat eksplisit, berparameter, dan dapat diganti tanpa melatih ulang model.

**Dataset B — kegagalan sistem berlabel**

Numenta Anomaly Benchmark, kategori `realKnownCause`:

| Berkas | Isi |
|---|---|
| `machine_temperature_system_failure.csv` | 22.695 observasi suhu komponen internal mesin industri, interval 5 menit, dengan **3 anomali berlabel oleh insinyur mesinnya**: shutdown terencana, awal mula gangguan, dan kegagalan katastrofik |
| `ambient_temperature_system_failure.csv` | Suhu ambien dengan kegagalan sistem berlabel |

Dataset ini menutup lubang yang tidak dapat ditutup Dataset A: **anotasi kegagalan nyata**. Struktur kejadiannya — kenaikan suhu lambat dan persisten yang berujung kegagalan, didahului fase "awal mula gangguan" yang halus — persis pola yang harus dideteksi F4 pada kegagalan kompresor. Detektor residual/CUSUM divalidasi di sini.

### 12.2 Model prediksi suhu

**Pembagian data.** Pembagian dilakukan **per pengiriman**, bukan acak per baris. Pembagian acak pada deret waktu membocorkan informasi masa depan ke dalam data latih dan menghasilkan metrik yang menyesatkan.

| Bagian | Pengiriman |
|---|---|
| Latih | 4 pengiriman |
| Validasi | 1 pengiriman |
| Uji | 1 pengiriman, tidak pernah disentuh sampai evaluasi akhir |

**Rekayasa fitur**

- Lag suhu pada t−5, t−10, t−15, t−30, t−45, t−60 menit
- Rata-rata dan simpangan baku bergerak pada jendela 15, 30, dan 60 menit
- Laju perubahan `dT/dt` pada jendela pendek dan panjang
- Waktu sejak pengiriman dimulai
- Jam dalam hari (penyandian siklik sin/cos) untuk menangkap siklus ambien harian
- Posisi sensor jika tersedia (depan/tengah/belakang, atas/tengah/bawah)

**Model.** LightGBM, satu model per horizon (30 dan 60 menit). Alasan memilih gradient boosting alih-alih LSTM/Transformer: dataset hanya berisi enam pengiriman. Pada regime data sekecil ini, model dengan kapasitas besar cenderung menghafal dan kalah dari gradient boosting pada fitur lag yang dirancang baik. Deep learning dicatat sebagai eksplorasi opsional, bukan jalur utama.

**Baseline pembanding — wajib dilaporkan**

1. *Persistence* — prediksi = suhu terakhir yang terukur. Sulit dikalahkan pada horizon pendek.
2. *Newton cooling* — fit eksponensial pada jendela terakhir, diekstrapolasi ke depan. Pembanding berbasis fisika.

Model hanya dipakai bila mengalahkan keduanya pada set uji. Jika tidak, tim melaporkannya apa adanya dan memakai baseline terbaik.

**Evaluasi.** MAE dan RMSE per horizon, dilaporkan untuk keseluruhan data **dan secara terpisah untuk segmen excursion**. Rata-rata global didominasi periode stabil yang mudah diprediksi; kinerja pada segmen excursion adalah yang benar-benar menentukan kegunaan produk.

### 12.3 Deteksi anomali berbasis residual

Satu model melayani dua fungsi. Residual dihitung sebagai:

```
r(t) = T_terukur(t) − T_prediksi(t)
```

σ diestimasi dari sebaran residual pada set validasi.

| Pola residual | Klasifikasi | Tindakan |
|---|---|---|
| `\|r\| > 3σ` selama < 15 menit, lalu kembali ke kurva prediksi | **PINTU_DIBUKA** | Dicatat sebagai info; tidak memicu alarm |
| `r > 3σ` bertahan ≥ 20 menit **dan** CUSUM menaik monoton | **KEGAGALAN_PENDINGIN** | Alarm kritis |
| Suhu prediksi melewati ambang produk | **PREDICTED_EXCURSION** | Peringatan dini |
| Tidak ada data melebihi 2× interval sampling | **DEVICE_OFFLINE** | Peringatan |

Statistik CUSUM mengakumulasi simpangan positif:

```
S(t) = max(0, S(t−1) + r(t) − k)
```

dengan `k` parameter kelonggaran. CUSUM sengaja dipilih karena peka terhadap pergeseran kecil yang persisten — persis tanda kegagalan kompresor yang baru dimulai — sementara lonjakan besar sesaat tidak membuatnya menanjak berkelanjutan.

Ambang `3σ`, `15 menit`, `20 menit`, dan `k` adalah nilai awal yang harus dikalibrasi terhadap Dataset B dan dicatat hasil kalibrasinya.

### 12.4 Strategi anti-sirkularitas

Aturan berikut mengikat dan harus dinyatakan terbuka dalam laporan akhir:

> **Keluaran Device Emulator tidak pernah digunakan sebagai data latih maupun data uji untuk model apa pun.** Emulator hanya menggerakkan demo dashboard secara langsung.

Alasannya: emulator menghasilkan suhu dari hukum pendinginan Newton. Melatih model pada keluarannya lalu mengujinya pada keluaran yang sama hanya membuktikan model mampu menghafal ulang rumus generatornya sendiri — bukan bahwa ia mempelajari sesuatu tentang rantai dingin nyata. Angka akurasinya akan tinggi dan tidak berarti apa-apa.

Karena itu pembagian tanggung jawab dibuat tegas:

| Komponen | Sumber data |
|---|---|
| Pelatihan dan evaluasi model prediksi | Dataset A (strawberry cold chain) |
| Kalibrasi dan evaluasi detektor anomali | Dataset B (NAB, berlabel) |
| Pelatihan dan evaluasi model computer vision | Dataset C dan D (§12.5) |
| Demo dashboard langsung, uji beban, uji integrasi | Device Emulator |

---

### 12.5 Model Computer Vision Kesegaran Ikan

**Sumber data.** Dua dataset publik dipakai untuk tujuan yang berbeda, mengikuti pola pemisahan yang sama dengan §12.1.

**Dataset C — kesegaran mata ikan**

*The Freshness of the Fish Eyes Dataset* (Prasetyo, Adityo, Suciati, & Fatichah, 2022; Mendeley Data, doi:10.17632/xzyx7pbr3w.1). Berisi citra mata dari 8 spesies ikan, berlabel 3 kelas kesegaran berbasis rentang hari penyimpanan (Sangat Segar: 1–2 hari, Segar: 3–4 hari, Tidak Segar: 5–6 hari).

**Dataset D — kesegaran multi-indikator**

*DaFiF: A Complete Dataset for Fish's Freshness Problems* (Prasetyo, Suciati, Sutramiani, Adiananda, & Dewi, 2024; Data in Brief, doi:10.1016/j.dib.2024.111016). Mencakup citra mata, insang, dan tekstur pada spesies kembung, nila, dan tuna, dengan label kesegaran yang diverifikasi lewat uji organoleptik mengikuti standar **SNI 2729:2013**.

> **Mengapa data dari spesies lain sah dipakai untuk MVP.** Sama seperti argumen Dataset A pada §12.1: pola degradasi visual (kejernihan mata, warna insang, kekusaman kulit) bersifat umum lintas spesies ikan bersirip, meski laju kemunculannya berbeda per spesies. Dataset D secara khusus sudah mencakup spesies yang lazim didistribusikan di Indonesia (kembung, nila), yang memperkecil kesenjangan domain dibanding jika hanya memakai Dataset C.

**Pembagian data.** Per gambar sumber (bukan augmentasi turunannya) dipisah ke latih/validasi/uji agar gambar dari objek yang sama tidak bocor lintas partisi.

**Model.** Transfer learning pada backbone ringan (MobileNetV2 atau EfficientNet-B0) yang telah dilatih di ImageNet, di-*fine-tune* untuk klasifikasi 3 kelas. Backbone ringan dipilih agar inferensi tetap murah dijalankan sebagai Azure Function pada tier gratis (§8.5), konsisten dengan pilihan LightGBM di §12.2 yang juga mengutamakan model hemat sumber daya di atas dataset kecil.

**Baseline pembanding — wajib dilaporkan**

1. *Mayoritas kelas* — selalu memprediksi kelas paling umum di data latih.
2. *Klasifikasi warna sederhana* (mis. ambang HSV pada area insang) — pembanding non-deep-learning.

Model hanya dipakai bila mengalahkan keduanya pada set uji, mengikuti aturan yang sama dengan §12.2.

**Evaluasi.** Akurasi dan F1-score per kelas, dilaporkan terpisah untuk tiap dataset sumber (C dan D) sebelum digabung, agar terlihat jelas jika salah satu dataset mendominasi kinerja.

**Batasan yang harus dinyatakan di antarmuka dan laporan.** Dataset C dan D tidak memuat spesies lokal yang persis sama dengan yang dipakai pelaku bisnis pengguna KRIO. Fine-tuning dengan foto lokal masuk daftar pekerjaan lanjutan (§16, R11), sama seperti kalibrasi parameter Arrhenius pada R7.

---

## 13. Model Umur Simpan

### 13.1 Formulasi

Laju degradasi mutu mengikuti persamaan Arrhenius:

```
k(T) = k_ref · exp[ −(Ea/R) · (1/T − 1/T_ref) ]
```

| Simbol | Arti | Nilai untuk ikan segar |
|---|---|---|
| `Ea` | Energi aktivasi | 60.000 J/mol |
| `R` | Konstanta gas universal | 8,314 J·mol⁻¹·K⁻¹ |
| `T_ref` | Suhu referensi | 273,15 K (0 °C) |
| `SL_ref` | Umur simpan pada `T_ref` | 240 jam (10 hari) |
| `k_ref` | Laju pada `T_ref` | 1 / `SL_ref` = 1/240 per jam |

Nilai `Ea` = 60 kJ/mol berada di dalam rentang literatur 49–84 kJ/mol untuk indeks mutu ikan.

**Akumulasi kerusakan** (Time-Temperature Integration):

```
D(t) = ∫₀ᵗ k(T(τ)) dτ
```

Dihitung secara numerik dengan aturan trapesium atas pembacaan diskrit. `D = 1` berarti umur simpan habis.

```
Sisa umur simpan (%) = max(0, (1 − D) × 100)
Sisa waktu pada suhu saat ini (jam) = (1 − D) / k(T_sekarang)
```

**Proyeksi ke depan.** Inilah yang menjadikan estimasi ini prediktif, bukan sekadar historis: suhu hasil prediksi model (§12.2) dimasukkan ke perhitungan `D` untuk 60 menit ke depan, sehingga sistem melaporkan kondisi produk yang **akan** terjadi, bukan hanya yang sudah terjadi.

### 13.2 Pemeriksaan kewajaran

Umur simpan yang dihasilkan model pada suhu konstan, dengan parameter di atas:

| Suhu | Faktor laju relatif terhadap 0 °C | Umur simpan |
|---|---|---|
| 0 °C | 1,00 | 10,0 hari |
| 2 °C | 1,21 | 8,3 hari |
| 4 °C | 1,46 | 6,8 hari |
| 10 °C | 2,54 | 3,9 hari |
| 15 °C | 3,96 | 2,5 hari |

Hasil ini konsisten dengan rentang literatur 2–10 hari untuk ikan segar, yang memberi keyakinan bahwa parameter yang dipilih masuk akal.

> **Batasan yang harus dinyatakan di antarmuka.** Parameter ini diambil dari literatur untuk spesies dan kondisi penanganan yang belum tentu sama dengan yang dipakai pengguna. Angka sisa umur simpan adalah **estimasi berbasis model**, bukan hasil pengukuran mutu. Kalibrasi terhadap spesies dan praktik penanganan lokal masuk daftar pekerjaan lanjutan (§16, R7).

### 13.3 Mean Kinetic Temperature

MKT adalah suhu isotermal tunggal yang menghasilkan total degradasi setara dengan degradasi yang terjadi pada rangkaian suhu yang berfluktuasi. Dipakai pada laporan compliance (F5) sebagai ringkasan satu angka atas seluruh riwayat pengiriman.

```
              Ea / R
T_MKT = ────────────────────────────────────
        −ln[ (1/n) · Σᵢ exp(−Ea / (R·Tᵢ)) ]
```

dengan `Tᵢ` pembacaan suhu dalam Kelvin dan `n` jumlah pembacaan. Rumus mengikuti USP General Chapter 1079.2, yang juga menyatakan interval pengambilan seperti setiap 15 menit sudah memadai — interval sampling KRIO (5 dan 10 menit) memenuhi syarat ini dengan margin.

MKT selalu **lebih tinggi** dari rata-rata aritmetik suhu, karena degradasi mempercepat secara eksponensial terhadap suhu. Inilah sebabnya rata-rata biasa tidak boleh dipakai sebagai bukti compliance.

---

## 14. Model Bisnis

Asumsi kurs: USD 1 = Rp 16.000. Seluruh angka adalah estimasi awal yang harus diverifikasi terhadap harga pasar saat pengadaan.

### 14.1 Bill of Materials per perangkat

| Komponen | Jalur seluler | Jalur LoRa |
|---|---|---|
| ESP32-S3 development board | Rp 55.000 | Rp 55.000 |
| Sensor suhu DS18B20 waterproof | Rp 25.000 | Rp 25.000 |
| Sensor suhu + kelembapan SHT31 | Rp 45.000 | Rp 45.000 |
| Modul NB-IoT SIM7020 | Rp 85.000 | — |
| Modul GPS NEO-6M | Rp 60.000 | — |
| Modul LoRa RFM95 | — | Rp 75.000 |
| Baterai 18650 3000 mAh + TP4056 + holder | Rp 60.000 | Rp 60.000 |
| Casing IP65, kabel, konektor | Rp 50.000 | Rp 50.000 |
| PCB dan perakitan | Rp 40.000 | Rp 40.000 |
| **Total** | **Rp 420.000** | **Rp 350.000** |

Gateway LoRaWAN dibagi antar perangkat pada satu lokasi: **Rp 1.200.000 per lokasi**, sekali bayar.

**Opsi penyediaan perangkat**

| Model | Harga | Catatan |
|---|---|---|
| Beli putus | Rp 650.000 per unit | Margin kotor ~35% |
| Sewa | Rp 35.000 per unit per bulan | Modal perangkat kembali dalam 12 bulan |

### 14.2 Tier langganan

| | **Gratis** | **Dasar** | **Pro** |
|---|---|---|---|
| Harga | Rp 0 | **Rp 45.000** /perangkat/bulan | **Rp 85.000** /perangkat/bulan |
| Jumlah perangkat | 1 | Tidak dibatasi | Tidak dibatasi |
| Retensi data | 7 hari | 12 bulan | 24 bulan |
| Pemantauan real-time | ✓ | ✓ | ✓ |
| Peringatan ambang statis | ✓ | ✓ | ✓ |
| Prediksi AI | — | 30 menit | 30 dan 60 menit |
| Deteksi anomali | — | ✓ | ✓ |
| Estimasi sisa umur simpan | — | — | ✓ |
| Deteksi kualitas visual (Computer Vision) | — | — | ✓ |
| Laporan PDF + MKT | — | ✓ | ✓ |
| Notifikasi email | — | ✓ | ✓ |
| Multi-pengguna | — | 3 pengguna | Tidak dibatasi |
| Akses API | — | — | ✓ |

Tier Gratis berfungsi sebagai jalur masuk: pelaku bisnis dapat mencoba satu boks tanpa komitmen, yang menjawab hambatan adopsi terbesar pada segmen ini.

### 14.3 Struktur biaya Azure

Biaya bulanan pada skala 100 perangkat aktif:

| Layanan | SKU | Biaya bulanan |
|---|---|---|
| Azure IoT Hub | S1 (400.000 pesan/hari) | Rp 400.000 |
| Azure Database for PostgreSQL | Flexible Server B1ms | Rp 240.000 |
| Azure App Service | B1 | Rp 208.000 |
| Functions, Blob Storage, Communication Services | Consumption | Rp 80.000 |
| **Total** | | **Rp 928.000** |

| Metrik | Nilai |
|---|---|
| Biaya per perangkat per bulan (100 perangkat) | **Rp 9.300** |
| Margin kotor tier Dasar | **79%** |
| Margin kotor tier Pro | **89%** |
| Titik impas biaya infrastruktur | **21 perangkat** berlangganan tier Dasar |

Satu IoT Hub S1 menampung sekitar 1.388 perangkat pada interval 5 menit, sehingga biaya tetap ini tidak perlu naik sampai jauh melewati skala 100 perangkat — margin justru membaik seiring pertumbuhan.

Selama pengembangan dan demo, seluruh sistem berjalan pada tier gratis (§8.5), sehingga kredit Azure student tidak terpakai untuk operasional harian.

### 14.4 Posisi harga

| | Biaya per titik pantau per bulan |
|---|---|
| **KRIO tier Dasar** | Rp 45.000 |
| Controlant, Tive | Tidak dipublikasikan; berbasis kontrak enterprise |
| Data logger konvensional | Rp 0 berulang, tetapi tanpa peringatan apa pun |

Diferensiasi KRIO bukan pada fitur yang lebih banyak dari Controlant — jelas tidak. Diferensiasinya adalah **satu-satunya opsi pemantauan prediktif pada titik harga yang dapat dijangkau pelaku bisnis Indonesia**, dengan antarmuka berbahasa Indonesia.

---

## 15. Analisis Kompetitor

### 15.1 Controlant — kompetitor langsung

Platform pemantauan rantai dingin real-time berbasis logger nirkabel dan dashboard analitik, banyak dipakai pada distribusi farmasi global.

**Target:** perusahaan farmasi multinasional dan penyedia logistik rantai dingin skala besar.

| Kelebihan | Kekurangan |
|---|---|
| Rekam jejak kuat pada distribusi vaksin internasional | Biaya berlangganan sangat tinggi, berorientasi kontrak enterprise |
| Perangkat keras tervalidasi, memenuhi standar regulasi farmasi | Proses onboarding panjang, tidak realistis untuk usaha kecil |
| Jangkauan operasional lintas negara dengan dukungan penuh | Tidak ada layanan lokal maupun antarmuka berbahasa Indonesia |

**Posisi KRIO:** Controlant menyasar korporasi farmasi beranggaran besar. KRIO menyasar pelaku bisnis distributor hasil laut di Indonesia dengan perangkat berbiaya rendah, harga terukur (§14), dan antarmuka berbahasa Indonesia.

### 15.2 Tive — kompetitor langsung

Tracker multi-sensor sekali pakai maupun isi ulang yang memantau lokasi, suhu, guncangan, dan cahaya selama pengiriman.

**Target:** perusahaan logistik dan pengirim barang lintas negara pada industri pangan dan farmasi.

| Kelebihan | Kekurangan |
|---|---|
| Perangkat mandiri dengan konektivitas seluler bawaan, mudah dipasang | Biaya per perangkat tinggi, tidak ekonomis untuk pengiriman jarak pendek harian |
| Pemantauan multi-parameter dalam satu perangkat | Analitik berfokus pada pelaporan kejadian, bukan prediksi sebelum kerusakan |
| Integrasi dengan berbagai sistem manajemen transportasi | Berorientasi pengiriman lintas negara, bukan distribusi harian jarak pendek |

**Posisi KRIO:** diferensiasinya adalah **lapisan prediksi**. Tive melaporkan bahwa excursion telah terjadi; KRIO memperingatkan 30–60 menit sebelumnya sehingga tindakan pencegahan masih mungkin.

> **Koreksi terhadap argumen di worksheet awal.** Worksheet mengkritik Tive karena bergantung pada konektivitas seluler dan menawarkan LoRaWAN sebagai keunggulan. Argumen itu dicabut. Untuk armada bergerak di Indonesia, cakupan seluler jauh melampaui cakupan LoRaWAN publik, dan pilihan Tive memakai seluler untuk kasus bergerak adalah keputusan yang benar. KRIO memakai seluler untuk kasus yang sama (§8), dan memakai LoRa hanya pada titik statis yang memang menjadi kekuatannya. Diferensiasi KRIO terhadap Tive terletak pada harga dan prediksi, bukan pada jenis radio.

### 15.3 Data logger konvensional (Elitech, Testo, sejenisnya) — kompetitor tidak langsung

Perangkat perekam suhu mandiri yang datanya dibaca setelah pengiriman selesai melalui USB atau aplikasi pendamping.

| Kelebihan | Kekurangan |
|---|---|
| Harga perangkat murah, mudah diperoleh di pasar lokal | Data hanya terbaca setelah pengiriman selesai — kerusakan tidak dapat dicegah |
| Tanpa biaya berlangganan maupun infrastruktur jaringan | Tidak ada peringatan dini maupun notifikasi |
| Pengoperasian sederhana tanpa pelatihan | Rekapitulasi dan pelaporan masih manual |

**Posisi KRIO:** perbedaannya terletak pada waktu. Data logger bersifat forensik — ia menjelaskan mengapa produk rusak. KRIO bersifat preventif — ia memberi peringatan selagi pengiriman masih berjalan dan kerugian masih dapat dicegah.

### 15.4 Antares (Telkom IoT) — kompetitor tidak langsung, lokal

Platform IoT umum dari Telkom Indonesia yang menyediakan konektivitas, ingest data perangkat, dan dashboard generik.

**Target:** pengembang dan perusahaan Indonesia yang membangun solusi IoT sendiri.

| Kelebihan | Kekurangan |
|---|---|
| Penyedia lokal, dukungan dan penagihan dalam negeri | Platform horizontal — bukan solusi rantai dingin siap pakai |
| Terintegrasi dengan infrastruktur seluler Telkom | Tidak ada model umur simpan, MKT, maupun prediksi khusus rantai dingin |
| Harga sesuai pasar Indonesia | Pengguna harus membangun sendiri lapisan aplikasi dan analitiknya |

**Posisi KRIO:** Antares menyediakan pipa datanya; KRIO menyediakan jawabannya. pelaku bisnis tidak memiliki kapasitas teknis untuk membangun lapisan domain di atas platform generik.

### 15.5 Status quo — pemeriksaan manual

Kompetitor sebenarnya bagi sebagian besar calon pengguna bukanlah produk, melainkan kebiasaan: memeriksa termometer beberapa kali sehari dan mencatat di buku, atau tidak memeriksa sama sekali.

| Kelebihan | Kekurangan |
|---|---|
| Tanpa biaya sama sekali | Malam hari dan waktu perjalanan sama sekali tidak terpantau |
| Tidak perlu belajar apa pun | Tidak ada bukti tertulis saat pelanggan komplain |
| Sudah menjadi kebiasaan | Kerugian tidak pernah terukur, sehingga masalahnya tidak terlihat |

**Posisi KRIO:** hambatan adopsi terbesar bukan kompetitor lain, melainkan meyakinkan pengguna bahwa ada masalah yang layak dibayar. Karena itu tier Gratis (§14.2) dan laporan compliance (F5) penting secara strategis — keduanya membuat kerugian yang selama ini tak terlihat menjadi terukur.

---

## 16. Risiko dan Mitigasi

| # | Risiko | Dampak | Mitigasi |
|---|---|---|---|
| **R1** | Cakupan LoRaWAN tidak memadai untuk armada bergerak | Fitur inti tidak berfungsi di lapangan | Arsitektur hybrid (§8.2); LoRa dibatasi pada titik statis |
| **R2** | Batas airtime LoRaWAN membatasi frekuensi data | Interval 1 menit tidak dapat dipenuhi | Interval diturunkan ke 5/10 menit dengan justifikasi (§8.4); backlog LoRa diturunkan resolusinya |
| **R3** | Tidak ada perangkat keras | Tidak ada data nyata dan tidak ada demo | Device Emulator sebagai komponen tetap dengan kontrak identik firmware (§8.6, §9); firmware dinyatakan di luar scope |
| **R4** | **Dataset A mungkin tidak dapat diunduh publik** | Rencana pelatihan model gagal | Tautan pada preprint mengarah ke pratinjau draf Mendeley yang memerlukan autentikasi. **Tindakan pertama tim: verifikasi akses.** Jika gagal, hubungi penulis (aabdella@usf.edu, iuysal@usf.edu, jkbrecht@ufl.edu). Cadangan: Dataset B untuk seluruh pekerjaan model, ditambah dataset suhu IoT publik lain |
| **R5** | Domain data latih berbeda dari produk target | Model dituding tidak relevan | Argumen pemisahan lapisan (§12.1); lapisan spesifik produk dipisahkan ke §13 dan berparameter |
| **R6** | Dataset kecil (6 pengiriman) | Model overfit, metrik menyesatkan | Pembagian per pengiriman bukan acak; model berkapasitas kecil; baseline wajib dilaporkan; kekalahan terhadap baseline dilaporkan terbuka |
| **R7** | Parameter kinetika ikan belum dikalibrasi lokal | Angka sisa umur simpan tidak akurat | Nilai literatur dinyatakan sebagai asumsi di antarmuka dan dokumen; parameter dapat diubah per produk; kalibrasi masuk pekerjaan lanjutan |
| **R8** | Kuota IoT Hub F1 terlampaui | Ingest berhenti | Anggaran kuota dihitung eksplisit (§8.5); demo dibatasi 3 armada; pemantauan pemakaian kuota |
| **R9** | Kredit Azure student habis | Sistem mati sebelum sidang | Seluruh sistem dirancang muat di tier gratis; infrastruktur didefinisikan sebagai kode di `infra/` agar dapat dibangun ulang cepat; sumber daya dimatikan di luar sesi demo |
| **R10** | Emulator secara tak sengaja dipakai sebagai data latih | Hasil AI menjadi sirkular dan tidak bermakna | Aturan pemisahan tegas (§12.4); direktori data latih dan keluaran emulator dipisah; dinyatakan terbuka di laporan akhir |
| **R11** | Dataset C dan D memuat spesies ikan berbeda dari kondisi lokal pengguna | Klasifikasi kesegaran visual tidak akurat untuk spesies lokal tertentu | Dataset D sudah mencakup spesies umum Indonesia (kembung, nila); batasan dinyatakan terbuka di antarmuka (§12.5); fine-tuning data lokal masuk pekerjaan lanjutan |
| **R12** | Kualitas foto dari ponsel pengguna tidak konsisten (pencahayaan, sudut, fokus) | Akurasi klasifikasi menurun di lapangan meski akurat pada data uji | Panduan pengambilan foto ditampilkan saat unggah; skor keyakinan rendah ditandai eksplisit di dashboard, bukan disembunyikan |
| **R13** | Link sekali pakai untuk foto `after` (F8) tersadap atau diteruskan ke pihak lain sebelum dipakai sopir | Foto `after` bisa diunggah oleh pihak yang salah, mencemari bukti compliance | Token terikat satu `shipment_id`, mati otomatis setelah dipakai sekali atau kedaluwarsa 24 jam; tidak ada data sensitif lain yang bisa diakses lewat token selain form unggah foto pengiriman tersebut |

---

## 17. Rencana Rilis Bertahap

Tanpa penanggalan kalender — urutan dan ketergantungan yang mengikat, bukan tanggalnya.

### MVP — sistem berjalan ujung ke ujung

Tujuan: data mengalir dari emulator sampai dashboard, dengan peringatan berbasis ambang statis.

- Provisioning Azure via `infra/`: IoT Hub F1, PostgreSQL, App Service, Blob Storage
- Skema basis data dan migrasi (§10)
- Device Emulator: model termal, 3 armada, kejadian pintu dan kegagalan (§8.6)
- `fn_ingest`: validasi skema, tulis ke `readings`, hitung paket hilang dari `seq`
- Autentikasi dan isolasi tenant
- F7 — manajemen perangkat, produk, pengiriman
- F1 — dashboard pemantauan real-time
- Peringatan ambang statis (belum prediktif)

**Kriteria selesai:** tiga armada berjalan serentak di dashboard; melewati ambang memicu peringatan.

### V1 — lapisan kecerdasan

Tujuan: peringatan berubah dari reaktif menjadi prediktif.

- Akuisisi dan eksplorasi Dataset A dan B (**mulai dari verifikasi R4**)
- Rekayasa fitur dan pelatihan model prediksi (§12.2)
- Evaluasi terhadap baseline, dengan laporan terbuka
- Artefak model ke Blob Storage; `fn_forecast` memuat dan menjalankannya
- F2 — peringatan dini prediktif
- F4 — deteksi anomali residual/CUSUM, dikalibrasi pada Dataset B
- Notifikasi email via Azure Communication Services

**Kriteria selesai:** peringatan terbit sebelum ambang terlampaui pada skenario emulator; metrik model terdokumentasi terhadap baseline.

### V2 — lapisan domain dan compliance

Tujuan: sistem berbicara dalam bahasa produk, bukan hanya derajat Celsius.

- F3 — estimasi sisa umur simpan Arrhenius/TTI, termasuk proyeksi ke depan (§13)
- F5 — laporan compliance PDF dengan MKT
- F6 — store-and-forward dan sinkronisasi, termasuk penurunan resolusi jalur LoRa
- F8 — deteksi kualitas visual ikan (computer vision), termasuk akuisisi Dataset C dan D
- Simulasi perilaku jaringan pada emulator: packet loss, zona tanpa sinyal, batas airtime
- Pemangkasan retensi data sesuai tier

**Kriteria selesai:** satu pengiriman lengkap menghasilkan PDF berisi MKT dan riwayat utuh, termasuk segmen yang sempat offline; foto `before` dan `after` menghasilkan klasifikasi kesegaran yang tampil berdampingan dengan estimasi berbasis suhu.

### Pasca-MVP — didokumentasikan, tidak dibangun

Notifikasi WhatsApp; firmware ESP32 dan uji perangkat nyata; kalibrasi parameter kinetika terhadap spesies lokal; integrasi TMS/ERP; penagihan otomatis; aplikasi mobile.

---

## 18. Lampiran

### 18.1 Peran tim

| Nama | NIM | Peran | Tanggung jawab utama di PRD ini |
|---|---|---|---|
| Ramzi Alfito Rizky | 24/540550/TK/60008 | Project Manager | Scope dan prioritas (§5, §17), koordinasi, model bisnis (§14) |
| Dien Muhammad Scientivan Kurniapramono | 24/533571/TK/59114 | UI/UX Designer & Software Engineer | Dashboard dan API (§6, §11), skema data (§10) |
| Yohanes Anthony Saputra | 24/536237/TK/59524 | AI Engineer & Cloud Engineer | Model dan evaluasi (§12), umur simpan (§13), infrastruktur Azure (§7) |

Desain jaringan (§8) dan kontrak perangkat (§9) dikerjakan bersama, karena keduanya menjadi batas antara pekerjaan cloud dan pekerjaan aplikasi.

### 18.2 Daftar pustaka

Seluruh rujukan di bawah sudah diverifikasi dapat diakses.

**Dataset**

1. Abdella, A., Brecht, J. K., Uysal, I. *A Time-Temperature Dataset for the Strawberry Cold Chain Across Multiple Shipments and Locations.* arXiv:2103.12895 (2021). https://arxiv.org/abs/2103.12895
   Dataset: Mendeley Data `nxttkftnzk` — *lihat R4, akses perlu diverifikasi*
2. Abdella, A. et al. *Statistical and temporal analysis of a novel multivariate time series data for food engineering.* Journal of Food Engineering (2021). https://doi.org/10.1016/j.jfoodeng.2021.110477
3. Numenta Anomaly Benchmark, kategori `realKnownCause`. https://github.com/numenta/NAB/tree/master/data — *periksa lisensi repositori sebelum digunakan*
4. Prasetyo, E., Adityo, R. D., Suciati, N., Fatichah, C. *The Freshness of the Fish Eyes Dataset* (Version 1) [Data set]. Mendeley Data (2022). https://doi.org/10.17632/xzyx7pbr3w.1
5. Prasetyo, E., Suciati, N., Sutramiani, N. P., Adiananda, A., Dewi, A. P. W. K. *DaFiF: A Complete Dataset for Fish's Freshness Problems.* Data in Brief, 57, 111016 (2024). https://doi.org/10.1016/j.dib.2024.111016

**Kinetika dan umur simpan**

6. FAO. *Quality and quality changes in fresh fish — Bab 6: Quality changes and shelf life for chilled fish.* https://www.fao.org/4/v7180e/v7180e07.htm
7. *Quality and Shelf-Life Modeling of Frozen Fish at Constant and Variable Temperature Conditions.* Foods 9(12):1893 (2020). https://www.mdpi.com/2304-8158/9/12/1893
8. *Applicability of an Arrhenius Model for the Combined Effect of Temperature and CO₂ Packaging on the Spoilage Microflora of Fish.* https://pmc.ncbi.nlm.nih.gov/articles/PMC92181/
9. *Development of shelf life kinetic model for fresh rainbow trout fillets stored under modified atmosphere packaging.* https://pmc.ncbi.nlm.nih.gov/articles/PMC6400768/
10. United States Pharmacopeia. *General Chapter 1079.2 — Mean Kinetic Temperature in the Evaluation of Temperature Excursions During Storage and Transportation of Drug Products.* https://www.usp.org/sites/default/files/usp/document/supply-chain/apec-toolkit/USP%20GC1079.2.pdf

**Konteks Indonesia**

11. Kementerian PPN/Bappenas. *Laporan Kajian Food Loss and Waste di Indonesia* (2021). https://lcdi-indonesia.id/wp-content/uploads/2021/06/Report-Kajian-FLW-FINAL-4.pdf
   Versi bahasa Inggris: https://lcdi-indonesia.id/wp-content/uploads/2021/07/Report-Kajian-FLW-ENG.pdf

**Infrastruktur**

12. Microsoft. *Understand Azure IoT Hub quotas and throttling.* https://learn.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-quotas-throttling
13. Microsoft. *Azure IoT Hub scaling.* https://learn.microsoft.com/en-us/azure/iot-hub/iot-hub-scaling
14. Microsoft. *Azure IoT Hub pricing.* https://azure.microsoft.com/en-us/pricing/details/iot-hub/

### 18.3 Perubahan terhadap Worksheet Pertemuan 1

Ringkasan agar perbedaan terhadap proposal awal dapat ditelusuri.

| Aspek | Worksheet awal | PRD ini | Alasan |
|---|---|---|---|
| Produk target | Pangan segar, beku, ikan, dan vaksin | Ikan segar saja | Arrhenius butuh parameter per produk; MKT adalah standar farmasi |
| Konektivitas | LoRaWAN untuk semua kasus | Hybrid berdasarkan mobilitas | LoRa tidak punya cakupan untuk armada bergerak (§8.1) |
| Interval sampling | 1 menit | 5 menit seluler, 10 menit LoRa | Batas airtime, kesesuaian data latih, fisika termal (§8.4) |
| Network Server LoRaWAN | Tidak disebut | Eksplisit dalam arsitektur | IoT Hub tidak menerima LoRaWAN langsung (§7) |
| Lokasi armada | Dijanjikan, tanpa GPS di daftar sensor | Hanya jalur seluler | Batas payload dan daya LoRa (§8.3) |
| Deteksi anomali | Klasifikasi tersupervisi | Residual + CUSUM | Tidak ada dataset rantai dingin publik berlabel kegagalan (§12.3) |
| Sinkronisasi offline | Backlog penuh saat pulih | Dibatasi laju; resolusi diturunkan di LoRa | Burst backlog melanggar batas airtime (§8.4) |
| Data latih AI | Eksperimen mandiri dengan boks pendingin | Dataset publik nyata; emulator tidak dipakai melatih | Tidak ada hardware; sekaligus menutup celah sirkularitas (§12.4) |
| Klaim keterjangkauan | Tanpa angka | BOM, tier harga, biaya Azure, margin, titik impas | Diferensiasi utama harus terukur (§14) |
| Daftar pustaka | "Disarankan untuk ditelusuri dan diverifikasi" | Terverifikasi dengan URL | §18.2 |
| Fitur computer vision kesegaran ikan | Ada di worksheet awal | Sempat tidak tercantum di draf PRD v1.0 ini, dikonfirmasi ulang tetap dibutuhkan oleh PM, ditambahkan sebagai F8 dengan Dataset C dan D | §6 (F8), §12.5, §16 (R11, R12) |
| Pengambil foto `after` pada F8 | Diasumsikan pelaku bisnis/admin gudang, sama seperti foto `before` | Kontradiksi dengan Persona 2 (Pak Joko, sengaja bukan pengguna aplikasi) ditemukan saat review; foto `after` dipindah ke link sekali pakai untuk sopir, tanpa login | §3 (Persona 2), §6 (F8), §10 (`shipment_photo_links`), §11, §16 (R13) |
