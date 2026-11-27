# Backend demo KRIO

FastAPI menyediakan autentikasi, pemantauan perangkat, riwayat suhu, alert,
pengiriman baca-saja, dan ingest telemetri. Buka `/docs` untuk mencoba API
atau gunakan [kontrak OpenAPI](../../docs/openapi.yaml) untuk frontend.

## Menjalankan dari checkout bersih

Jalankan dari root repo. Contoh ini mengasumsikan PostgreSQL lokal sudah
berjalan dan akun shell boleh membuat database.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
createdb krio_dev

export DATABASE_URL=postgresql:///krio_dev
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export KRIO_DEVICE_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python -m alembic -c services/ingest/alembic.ini upgrade head
python -m scripts.seed
python -m uvicorn services.api.main:app --host 127.0.0.1 --port 8000
```

Pertahankan nilai kedua secret saat membuka terminal lain. Simpan di `.env`
lokal jika perlu. Muat `.env` ke shell emulator dengan `set -a; . ./.env; set +a`.
Kredensial demo lokal adalah `admin@demo.com` dan `password123`. Seed database
remote memerlukan `KRIO_DEMO_PASSWORD` unik. Gunakan `viewer@demo.com` untuk
menguji akses baca-saja.

## Menjalankan telemetri

```sh
python -m services.emulator --sink http \
  --endpoint http://127.0.0.1:8000/api/ingest \
  --device-id KRIO-0001 --interval 5 --duration 3m --speed 1 \
  --mode excursion --event-start 10s --setpoint 3.7
```

Contoh ini mengirim tiap 5 detik dan memulai boks dekat batas atas 4 °C agar
alert suhu cepat terlihat. Saat
memakai interval normal, seluler mengirim setiap 5 menit dan LoRa setiap 10
menit. KRIO menganggap perangkat offline setelah jeda **lebih dari 10 menit**
untuk seluler dan **lebih dari 20 menit** untuk LoRa. Seed menempatkan pengiriman
aktif pada perangkat `KRIO-0001`, sehingga perangkat itu memicu alert suhu saat
mode `excursion` melewati ambang. Scheduler memindai setiap 30 detik.

## Menghubungkan frontend

- API lokal menggunakan `http://127.0.0.1:8000`. CORS mengizinkan
  `http://localhost:3000` secara default. Atur `KRIO_CORS_ORIGINS` sebagai
  daftar origin yang dipisahkan koma untuk alamat lain.
- Login mengembalikan `access_token` dan `user`. Kirim
  `Authorization: Bearer <token>` pada endpoint dashboard. Token berlaku 30 menit.
- Pakai UUID `id` perangkat di endpoint browser. `device_id` seperti
  `KRIO-0001` adalah kode yang dipakai emulator.
- `/api/readings` menerima waktu `from` dan `to` dalam ISO 8601 dengan zona
  waktu, serta bucket `1m`, `5m`, atau `1h`. Setiap bucket berisi waktu,
  rata-rata suhu, dan jumlah pembacaan.
- `/api/alerts?status=active` adalah daftar aktif. Acknowledge mengisi
  `acked_by` dan menutup alert untuk daftar aktif. Alert offline juga ditutup
  otomatis saat telemetri kembali masuk.
- Header `X-Device-Key` digunakan oleh emulator pada endpoint ingest.
  `KRIO_DEVICE_SECRET` hanya dibagikan pada backend dan operator emulator.

## Pengujian

Gunakan database kosong yang terpisah untuk pengujian. Tes integrasi menolak DB
yang sudah memiliki tenant.

```sh
createdb krio_api_test
export KRIO_TEST_DATABASE_URL=postgresql:///krio_api_test
DATABASE_URL="$KRIO_TEST_DATABASE_URL" python -m alembic -c services/ingest/alembic.ini upgrade head
PYTHONPATH=.:services python -m pytest -q
```

Untuk memperbarui kontrak setelah perubahan API, jalankan:

```sh
python -c 'from services.api.main import app; import yaml; print(yaml.safe_dump(app.openapi(), sort_keys=False), end="")' > docs/openapi.yaml
```
