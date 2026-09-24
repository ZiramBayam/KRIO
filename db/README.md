# Basis Data KRIO

Skema PostgreSQL untuk KRIO. Acuan rancangan: ERD pada Lab 2.4 (Tahap 3 — Software Design) dan PRD KRIO v1.2 §10.

## Struktur

| Path | Isi |
|---|---|
| `migrations/0001_init.sql` | Skema awal: 12 tabel, relasi, aturan integritas data, partisi bulanan `readings` |
| `tests/0001_init_test.sql` | Uji aturan integritas; seluruh data uji di-rollback |
| `../alembic/versions/0001_initial_schema.py` | Revisi Alembic yang menjalankan `migrations/0001_init.sql` |

## Menjalankan

Membutuhkan PostgreSQL 13 atau lebih baru.

Cara yang dianjurkan adalah melalui Alembic, agar versi skema tercatat pada tabel `alembic_version`:

```bash
createdb krio_dev
pip install -r requirements.txt
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/krio_dev alembic upgrade head
psql -X -d krio_dev -f db/tests/0001_init_test.sql
```

Menjalankan berkas SQL secara langsung juga tetap didukung (dipakai `scripts/deploy_db.sh`) dan menghasilkan skema yang sama persis:

```bash
psql -X -d krio_dev -v ON_ERROR_STOP=1 -f db/migrations/0001_init.sql
```

Berkas SQL adalah satu-satunya sumber definisi skema; revisi Alembic hanya menjalankannya, sehingga kedua cara tidak dapat berbeda isi.

### Basis data yang sudah dibuat lewat psql

Basis data yang skemanya sudah ada sebelum revisi ini dibuat (misalnya Azure PostgreSQL pada #29) tidak boleh dimigrasikan ulang. Tandai versinya saja, lalu lanjutkan seperti biasa:

```bash
alembic stamp 0001_initial_schema
alembic current   # harus menampilkan 0001_initial_schema (head)
```

### Mengembalikan skema

`alembic downgrade base` menghapus seluruh tabel dan fungsi migrasi ini. Ekstensi `citext` sengaja dibiarkan, karena ekstensi berlaku untuk seluruh basis data dan dapat dipakai objek lain.

Uji berhasil bila seluruh baris diawali `LULUS` dan diakhiri `SELESAI seluruh uji lulus`. Bila ada aturan yang tidak ditegakkan, uji berhenti dengan pesan `GAGAL`.

## Keputusan desain

- **Nama tabel mengikuti ERD Lab 2.4**, yaitu `shelf_life_states` (PRD §10 menulis `shelf_life_state`), serta memuat tabel `reports` dan kolom `readings.shipment_id` hasil penyesuaian Lab 2.4.
- **Isolasi tenant.** Tabel yang memiliki `tenant_id` memakai foreign key gabungan `(tenant_id, id)` sehingga relasi lintas tenant ditolak basis data. `readings`, `forecasts`, `shelf_life_states`, dan `reports` tidak memiliki `tenant_id`, sehingga isolasinya ditegakkan di lapisan kueri aplikasi.
- **Partisi `readings`.** Partisi bulanan September 2026 – Februari 2027 dibuat saat migrasi; bulan berikutnya dibuat dengan `SELECT create_readings_partition('2027-03-01');`. Partisi `readings_default` menampung data di luar rentang agar ingest tidak gagal; buat partisi bulan baru **sebelum** bulan tersebut dimulai, karena PostgreSQL menolak pembuatan partisi bila `readings_default` sudah berisi baris untuk rentang itu.
- **Aturan yang belum ditegakkan basis data:**
  - token link hanya dapat dipakai satu kali (Aturan 18) ditegakkan aplikasi saat mengisi `used_at`; basis data hanya menolak `used_at` setelah `expires_at`;
  - konsistensi `readings.shipment_id` dengan `device_id` pengiriman ditegakkan aplikasi.

## Catatan Azure

Azure Database for PostgreSQL Flexible Server mewajibkan ekstensi `citext` diizinkan terlebih dahulu melalui parameter server `azure.extensions` sebelum migrasi dijalankan ([dokumentasi](https://learn.microsoft.com/en-us/azure/postgresql/extensions/how-to-allow-extensions)).
