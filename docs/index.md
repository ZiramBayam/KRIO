# KRIO

**Sistem Pemantauan Rantai Dingin Prediktif untuk Distributor Hasil Laut**

Kelompok Manut — Senior Project (Jaringan Komputer, Komputasi Awan, dan AI)

| Nama | NIM | Peran |
|---|---|---|
| Ramzi Alfito Rizky | 24/540550/TK/60008 | Project Manager |
| Dien Muhammad Scientivan Kurniapramono | 24/533571/TK/59114 | UI/UX Designer & Software Engineer |
| Yohanes Anthony Saputra | 24/536237/TK/59524 | AI Engineer & Cloud Engineer |

---

## Tujuan Produk

KRIO memberi peringatan **sebelum** produk rusak, bukan sesudahnya. Sistem memprediksi suhu 30–60 menit ke depan dan menerjemahkannya menjadi estimasi sisa umur simpan produk, sehingga distributor ikan segar dapat bertindak selagi barang masih dapat diselamatkan.

Sebagai validasi silang, pengguna juga dapat memotret ikan sebelum dan sesudah pengiriman; model computer vision mengklasifikasikan kesegaran dari citra mata, insang, dan tekstur, sehingga bukti mutu tidak hanya berupa angka suhu.

Segmen MVP: distributor ikan segar dan hasil laut, rantai dingin 0–4 °C.

---

## Metodologi SDLC

**Metodologi yang digunakan:** Agile — Iterative & Incremental, dengan rilis bertahap MVP → V1 → V2.

**Alasan pemilihan:**

1. Kelayakan model AI belum pasti. Tim menetapkan syarat bahwa model prediksi suhu harus mengalahkan baseline sederhana (*persistence* dan *Newton cooling*), dan model computer vision harus mengalahkan baseline mayoritas kelas serta ambang warna sederhana. Bila syarat itu tidak terpenuhi, baseline yang dipakai dan hasilnya dilaporkan apa adanya. Keputusan semacam ini hanya bisa diambil setelah iterasi evaluasi, bukan direncanakan di muka seperti pada Waterfall.
2. Setiap rilis berdiri sendiri. MVP sudah menghasilkan sistem berjalan ujung ke ujung dengan ambang statis, sehingga ada yang bisa didemokan meski lapisan kecerdasan tertunda.
3. Tim beranggota tiga orang dengan peran berbeda (aplikasi, cloud/AI, manajemen). Iterasi pendek per pertemuan membuat integrasi antar-peran terjadi rutin, bukan menumpuk di akhir semester.
4. Tim tidak memiliki hardware. Device Emulator menggantikan perangkat fisik dengan kontrak payload identik, dan pendekatan inkremental memungkinkan perangkat nyata masuk belakangan tanpa mengubah backend.

---

## Gantt Chart — Rencana Pengerjaan 1 Semester

Legenda: █ pertemuan saat kegiatan berjalan · sel kosong = tidak berjalan

| Kegiatan | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Brainstorming & riset kebutuhan | █ | █ | █ | | | | | | | | | |
| Perancangan sistem & desain UI/UX | | | █ | █ | █ | | | | | | | |
| Pengembangan MVP | | | | | █ | █ | █ | █ | | | | |
| Pengembangan V1 | | | | | | | | █ | █ | █ | | |
| Pengembangan V2 | | | | | | | | | | █ | █ | █ |
| Pengujian & demo akhir | | | | | | | | | | | █ | █ |

**Penanda rilis:** MVP selesai pertemuan 8 · V1 selesai pertemuan 10 · V2 selesai pertemuan 12.

---

## Pengguna Potensial dan Kebutuhannya

| Persona | Peran | Kebutuhan |
|---|---|---|
| Bu Sari | Pemilik usaha distribusi (pengguna utama) | Tahu ada masalah selagi masih bisa ditindaklanjuti; bukti tertulis suhu terjaga saat pelanggan komplain |
| Pak Joko | Sopir/kurir | Tidak membuka dashboard sama sekali — cukup dihubungi Bu Sari bila ada masalah. Sistem tidak boleh bergantung pada interaksinya |
| Rina | Admin gudang | Registrasi perangkat yang sederhana, pencatatan pengiriman, laporan bulanan yang bisa diunduh |

---

## Fitur Utama

| Kode | Fitur |
|---|---|
| F1 | Pemantauan suhu real-time |
| F2 | Peringatan dini prediktif (horizon 30–60 menit) |
| F3 | Estimasi sisa umur simpan (Arrhenius/TTI) |
| F4 | Deteksi anomali berbasis residual |
| F5 | Laporan compliance otomatis dengan Mean Kinetic Temperature |
| F6 | Store-and-forward dan sinkronisasi |
| F7 | Manajemen perangkat, produk, dan pengiriman |
| F8 | Deteksi kualitas visual ikan dari foto ponsel (computer vision) |

---

## Arsitektur Ringkas

Perangkat/emulator → Azure IoT Hub (F1) → Azure Functions (Python) → PostgreSQL, Blob Storage, Azure Communication Services → dashboard Next.js di Azure App Service.

Foto kesegaran yang diunggah lewat dashboard disimpan di Blob Storage dan diklasifikasikan oleh model transfer learning (MobileNetV2/EfficientNet-B0) yang dijalankan sebagai Azure Function.

Konektivitas perangkat dirancang hybrid: LoRaWAN untuk titik statis seperti cold storage, dan seluler NB-IoT/GSM untuk boks yang bergerak bersama armada. Karena tim tidak memiliki perangkat keras, sumber telemetri selama pengembangan adalah Device Emulator yang memakai kontrak payload identik dengan firmware nyata, sehingga perangkat fisik dapat masuk kemudian tanpa mengubah backend.
