# Project Senior Project TI

## KRIO — Sistem Pemantauan Rantai Dingin Prediktif untuk Distributor Hasil Laut

**Kelompok Manut**

| Nama | NIM | Peran |
|---|---|---|
| Ramzi Alfito Rizky | 24/540550/TK/60008 | Project Manager |
| Dien Muhammad Scientivan Kurniapramono | 24/533571/TK/59114 | UI/UX Designer & Software Engineer |
| Yohanes Anthony Saputra | 24/536237/TK/59524 | AI Engineer & Cloud Engineer |

Departemen Teknologi Elektro dan Teknologi Informasi \
Fakultas Teknik, Universitas Gadjah Mada

---

## Nama Produk

**KRIO**

## Jenis Produk

Aplikasi web pemantauan rantai dingin berbasis Internet of Things dan kecerdasan buatan. Sistem terdiri atas perangkat sensor suhu pada boks pendingin, layanan cloud yang mengolah telemetri, dan dashboard web yang diakses pemilik usaha maupun admin gudang.

## Latar Belakang dan Permasalahan

Kajian *Food Loss and Waste* Kementerian PPN/Bappenas (2021) mencatat Indonesia menghasilkan 23–48 juta ton kehilangan dan sampah pangan per tahun sepanjang 2000–2019, setara 115–184 kg per kapita per tahun. Potensi kerugian ekonominya mencapai Rp213–551 triliun per tahun, atau 4–5% dari Produk Domestik Bruto nasional. Sebagian kehilangan itu terjadi pada tahap distribusi dan penyimpanan — tahap yang bergantung langsung pada kualitas rantai dingin.

Ikan segar termasuk komoditas paling rentan. Umur simpannya hanya 2–10 hari tergantung spesies, beban bakteri awal, dan kondisi suhu. Laju pembusukannya sangat sensitif terhadap suhu: menaikkan suhu penyimpanan dari 0 °C ke 10 °C memangkas umur simpan menjadi kurang dari setengahnya.

Masalahnya, distributor yang menjadi tulang punggung distribusi pangan umumnya masih memeriksa suhu secara manual dan berkala. Metode ini meninggalkan jeda panjang yang tidak terpantau, terutama pada malam hari dan selama kendaraan dalam perjalanan. Solusi otomatis yang tersedia di pasar dirancang untuk korporasi dengan biaya berlangganan yang tidak terjangkau pelaku usaha kecil.

Tiga pertanyaan yang ingin dijawab:

1. Bagaimana merancang pemantauan rantai dingin yang bekerja terus-menerus selama distribusi, termasuk di wilayah dengan kualitas jaringan terbatas?
2. Bagaimana memanfaatkan kecerdasan buatan untuk memprediksi pelanggaran ambang suhu dan mengestimasi sisa umur simpan, sehingga pencegahan dapat dilakukan sebelum kerusakan terjadi?
3. Bagaimana menyajikannya dalam aplikasi web yang terjangkau dan dapat dioperasikan tanpa keahlian teknis khusus?

## Ide Solusi

KRIO memberi peringatan **sebelum** produk rusak, bukan sesudahnya. Sistem memprediksi suhu 30–60 menit ke depan dan menerjemahkannya menjadi estimasi sisa umur simpan produk, sehingga distributor dapat bertindak selagi barang masih dapat diselamatkan.

| Kode | Fitur |
|---|---|
| F1 | Pemantauan suhu real-time |
| F2 | Peringatan dini prediktif (horizon 30–60 menit) |
| F3 | Estimasi sisa umur simpan berbasis Arrhenius/TTI |
| F4 | Deteksi anomali berbasis residual — membedakan pintu dibuka dari kegagalan pendingin |
| F5 | Laporan compliance otomatis dengan Mean Kinetic Temperature |
| F6 | Store-and-forward dan sinkronisasi untuk wilayah tanpa sinyal |
| F7 | Manajemen perangkat, produk, dan pengiriman |
| F8 | Deteksi kualitas visual ikan dari foto ponsel (computer vision) |

Konektivitas dirancang hybrid: LoRaWAN untuk titik statis seperti cold storage, seluler NB-IoT/GSM untuk boks yang bergerak bersama armada. Telemetri masuk melalui Azure IoT Hub, diolah Azure Functions, dan ditampilkan pada dashboard Next.js.

Segmen MVP: distributor ikan segar dan hasil laut, rantai dingin 0–4 °C.

## Analisis Kompetitor

| Kompetitor | Jenis | Kelebihan | Kekurangan | Posisi KRIO |
|---|---|---|---|---|
| **Controlant** | Langsung | Rekam jejak kuat pada distribusi vaksin internasional; perangkat tervalidasi standar farmasi | Biaya berlangganan sangat tinggi; onboarding panjang; tanpa dukungan dan antarmuka lokal | Menyasar distributor hasil laut Indonesia dengan perangkat berbiaya rendah dan antarmuka berbahasa Indonesia |
| **Tive** | Langsung | Tracker mandiri dengan seluler bawaan; multi-parameter dalam satu perangkat | Biaya per perangkat tinggi untuk pengiriman harian jarak pendek; analitik berorientasi pelaporan kejadian | Diferensiasi pada lapisan prediksi — Tive melaporkan excursion sudah terjadi, KRIO memperingatkan 30–60 menit sebelumnya |
| **Data logger konvensional** (Elitech, Testo) | Tidak langsung | Perangkat murah dan mudah didapat; tanpa biaya langganan | Data baru terbaca setelah pengiriman selesai; tanpa peringatan dini; pelaporan manual | Perbedaannya pada waktu — logger bersifat forensik, KRIO bersifat preventif |
| **Antares (Telkom IoT)** | Tidak langsung, lokal | Penyedia lokal; terintegrasi infrastruktur seluler Telkom; harga sesuai pasar Indonesia | Platform horizontal, bukan solusi rantai dingin siap pakai; tanpa model umur simpan maupun prediksi | Antares menyediakan pipa datanya, KRIO menyediakan jawabannya |
| **Pemeriksaan manual** (status quo) | Tidak langsung | Tanpa biaya; tidak perlu belajar apa pun | Malam hari dan waktu perjalanan tidak terpantau; tanpa bukti tertulis; kerugian tak pernah terukur | Tier gratis dan laporan compliance membuat kerugian yang selama ini tak terlihat menjadi terukur |

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
