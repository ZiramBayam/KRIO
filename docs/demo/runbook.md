# Runbook VM demo KRIO

Panduan operasional untuk VM demo. Keputusan arsitekturnya ada di
[azure.md](azure.md).

## Ringkasan VM

| Hal | Nilai |
|---|---|
| Resource | `krio-vm` di `Resource_Group_7-9`, subscription `DTETI-LabIT`, Central India |
| Ukuran | `Standard_B2s` (2 vCPU, 4 GB RAM), Ubuntu 24.04, disk OS 64 GB |
| Alamat | `http://20.204.52.237` (dashboard), `http://20.204.52.237/api/health` |
| SSH | `ssh -i ~/.ssh/krio_vm krio@20.204.52.237` |
| Secret | `/etc/krio/krio.env` (mode 600), tidak pernah di repo |

Semua resource KRIO di resource group memakai tag `project=krio`. Azure tidak
punya folder di dalam resource group, jadi tag ini yang mengelompokkannya. Di
portal, buka resource group lalu filter **Tags: project = krio**.

Port 22 hanya terbuka untuk IP tim. Jika IP berubah, perbarui rule `ssh-team`:

```sh
az network nsg rule update -g Resource_Group_7-9 --nsg-name krio-vm-nsg -n ssh-team \
  --source-address-prefixes "$(curl -s https://api.ipify.org)/32"
```

## Komponen di VM

| Komponen | Cara berjalan |
|---|---|
| PostgreSQL 16 | Service `postgresql`, hanya mendengarkan `127.0.0.1:5432` |
| API dan scanner alert | Service `krio-api` (`infra/vm/krio-api.service`), uvicorn di `127.0.0.1:8000` |
| Dashboard | Hasil `npm run build` di `/var/www/krio`, disajikan nginx |
| nginx | Port 80, `/api/` diteruskan ke API (`infra/vm/nginx-krio.conf`) |
| Backup | Timer `krio-backup.timer`, setiap hari 19.00 UTC (02.00 WIB) |
| Partisi readings | Timer `krio-partitions.timer`, setiap tanggal 1 dan saat boot |

Semua service memakai `Restart=always` atau timer `Persistent=true`, jadi
semuanya hidup lagi sendiri setelah VM di-restart.

## Deploy versi terbaru

```sh
ssh -i ~/.ssh/krio_vm krio@20.204.52.237 '~/KRIO/infra/vm/deploy.sh main'
```

Skrip ini menarik `main`, memasang dependensi, menjalankan migrasi, membangun
dashboard, memasang unit systemd dan konfigurasi nginx, lalu memeriksa
`/api/health`. Argumen pertama bisa diganti nama branch untuk uji coba.

## Cek kondisi

```sh
systemctl status krio-api --no-pager
journalctl -u krio-api -n 100 --no-pager
systemctl list-timers 'krio-*'
curl -s http://127.0.0.1/api/health
```

## Backup dan restore

Backup tersimpan di `/var/backups/krio`, tujuh salinan terakhir.

```sh
sudo systemctl start krio-backup.service       # backup sekarang
ls -lh /var/backups/krio
```

Restore ke database baru, lalu arahkan API ke sana bila hasilnya benar:

```sh
sudo -u postgres createdb -O krio_app krio_restore
pg_restore --no-owner --dbname=postgresql://krio_app:PASSWORD@127.0.0.1/krio_restore \
  /var/backups/krio/krio-YYYYMMDDTHHMMSSZ.dump
```

Ganti `PASSWORD` dengan nilai di `/etc/krio/krio.env`. Jangan tulis password
itu ke riwayat chat atau repo.

## Reset data demo sebelum presentasi

Menghapus pembacaan dan alert hasil latihan, lalu mengisi ulang data seed.

```sh
sudo systemctl start krio-backup.service
set -a; . /etc/krio/krio.env; set +a
psql "$DATABASE_URL" -c "TRUNCATE alerts, readings; UPDATE devices SET last_seen_at = NULL;"
cd ~/KRIO && .venv/bin/python -m scripts.seed
```

## Partisi readings

Tabel `readings` dipartisi per bulan. Partisi September 2026 sampai Februari
2027 dibuat oleh migrasi, dan `krio-partitions.timer` membuat partisi bulan
ini dan dua bulan berikutnya. Data di luar rentang masuk `readings_default`.
Partisi baru gagal dibuat jika `readings_default` sudah berisi data untuk
bulan tersebut, jadi timer harus tetap aktif.

## Menghemat biaya

VM yang menyala terus ditagih per jam. Matikan saat tidak dipakai, lalu
nyalakan lagi sebelum demo. IP statis tetap sama.

```sh
az vm deallocate -g Resource_Group_7-9 -n krio-vm
az vm start -g Resource_Group_7-9 -n krio-vm
```
