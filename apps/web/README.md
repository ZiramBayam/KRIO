# apps/web

Dashboard KRIO (Next.js, static export). Halaman: login, pemantauan perangkat,
detail perangkat dengan grafik suhu, peringatan dengan tombol tandai ditangani,
dan Simulasi untuk menjalankan skenario emulator dari browser (#110).

## Menjalankan lokal

Jalankan API lebih dulu (lihat `services/api/README.md`), lalu:

```sh
cd apps/web
npm ci
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 npm run dev
```

Buka http://localhost:3000. `KRIO_CORS_ORIGINS` di API harus memuat
`http://localhost:3000`.

## Build produksi

`npm run build` menghasilkan `out/`. Di VM demo, nginx menyajikan `out/` dan
meneruskan `/api/` ke FastAPI di origin yang sama, jadi
`NEXT_PUBLIC_API_BASE` dibiarkan kosong. Lihat `docs/demo/runbook.md`.
