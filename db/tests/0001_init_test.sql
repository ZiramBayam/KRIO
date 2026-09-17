-- =============================================================================
-- Uji migrasi 0001: data valid harus diterima, data yang melanggar aturan
-- integritas Lab 2.4 harus ditolak. Jalankan pada basis data yang baru saja
-- dimigrasi (lihat db/README.md). Seluruh data uji di-ROLLBACK di akhir.
-- =============================================================================

\set ON_ERROR_STOP on
\pset tuples_only on
\pset format unaligned

BEGIN;

-- Menjalankan p_sql dan memastikan gagal dengan SQLSTATE p_state.
-- Mengembalikan baris 'LULUS ...'; bila tidak sesuai, seluruh uji berhenti.
CREATE FUNCTION pg_temp.expect_fail(p_label text, p_state text, p_sql text)
RETURNS text
LANGUAGE plpgsql
AS $$
BEGIN
  BEGIN
    EXECUTE p_sql;
  EXCEPTION WHEN OTHERS THEN
    IF SQLSTATE = p_state THEN
      RETURN 'LULUS  ' || p_label;
    END IF;
    RAISE EXCEPTION 'GAGAL  % (SQLSTATE % bukan %: %)', p_label, SQLSTATE, p_state, SQLERRM;
  END;
  RAISE EXCEPTION 'GAGAL  % (perintah seharusnya ditolak)', p_label;
END;
$$;

-- -----------------------------------------------------------------------------
-- Data valid: dua tenant, masing-masing dengan pengguna, produk, perangkat
-- -----------------------------------------------------------------------------
INSERT INTO tenants (id, name) VALUES
  ('00000000-0000-0000-0000-00000000000a', 'CV Samudra Segar'),
  ('00000000-0000-0000-0000-00000000000b', 'UD Bahari Jaya');

INSERT INTO users (id, tenant_id, email, password_hash, role) VALUES
  ('00000000-0000-0000-0000-0000000000a1', '00000000-0000-0000-0000-00000000000a', 'sari@samudra.id', 'x', 'owner'),
  ('00000000-0000-0000-0000-0000000000b1', '00000000-0000-0000-0000-00000000000b', 'admin@bahari.id', 'x', 'admin');

INSERT INTO products (id, tenant_id, name, temp_min_c, temp_max_c, ea_j_per_mol, t_ref_k, shelf_life_ref_h) VALUES
  ('00000000-0000-0000-0000-0000000000a2', '00000000-0000-0000-0000-00000000000a', 'Ikan segar (utuh, dalam es)', 0, 4, 60000, 273.15, 240),
  ('00000000-0000-0000-0000-0000000000b2', '00000000-0000-0000-0000-00000000000b', 'Ikan segar (utuh, dalam es)', 0, 4, 60000, 273.15, 240);

INSERT INTO devices (id, tenant_id, device_id, label, link_type, static_lat, static_lon) VALUES
  ('00000000-0000-0000-0000-0000000000a3', '00000000-0000-0000-0000-00000000000a', 'KRIO-0001', 'Truk L-2213', 'cellular', NULL, NULL),
  ('00000000-0000-0000-0000-0000000000a4', '00000000-0000-0000-0000-00000000000a', 'KRIO-0002', 'Boks A-01', 'lora', -7.80, 110.36),
  ('00000000-0000-0000-0000-0000000000b3', '00000000-0000-0000-0000-00000000000b', 'KRIO-0101', 'Truk B-9081', 'cellular', NULL, NULL);

INSERT INTO shipments (id, tenant_id, device_id, product_id, origin, destination, started_at, status) VALUES
  ('00000000-0000-0000-0000-0000000000a5', '00000000-0000-0000-0000-00000000000a',
   '00000000-0000-0000-0000-0000000000a3', '00000000-0000-0000-0000-0000000000a2',
   'Gudang Muara', 'Resto Pantai', '2026-09-17 08:00+07', 'active');

INSERT INTO readings (device_id, ts, shipment_id, seq, temp_c) VALUES
  ('00000000-0000-0000-0000-0000000000a3', '2026-09-17 08:05+07', '00000000-0000-0000-0000-0000000000a5', 1, 2.4),
  ('00000000-0000-0000-0000-0000000000a4', '2031-01-01 00:00+07', NULL, 1, 3.0);  -- masuk partisi default

INSERT INTO shipment_photo_links (id, tenant_id, shipment_id, token, created_by) VALUES
  ('00000000-0000-0000-0000-0000000000a6', '00000000-0000-0000-0000-00000000000a',
   '00000000-0000-0000-0000-0000000000a5', 'tok-123', '00000000-0000-0000-0000-0000000000a1');

INSERT INTO fish_quality_checks (tenant_id, shipment_id, stage, photo_url, freshness_class, confidence, model_version, upload_channel, uploaded_by, link_id) VALUES
  ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a5', 'before', 'blob/a.jpg', 'sangat_segar', 0.92, 'cv-v1', 'dashboard', '00000000-0000-0000-0000-0000000000a1', NULL),
  ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a5', 'after', 'blob/b.jpg', 'segar', 0.81, 'cv-v1', 'one_time_link', NULL, '00000000-0000-0000-0000-0000000000a6');

SELECT 'LULUS  data valid diterima; readings tersebar ke ' || count(DISTINCT tableoid) || ' partisi' AS hasil
FROM readings;

-- -----------------------------------------------------------------------------
-- Data yang melanggar aturan harus ditolak
-- 23514 = check_violation, 23505 = unique_violation, 23503 = foreign_key_violation
-- -----------------------------------------------------------------------------
SELECT pg_temp.expect_fail('Aturan 1  role di luar owner/admin/viewer', '23514',
  $q$INSERT INTO users (tenant_id, email, password_hash, role)
     VALUES ('00000000-0000-0000-0000-00000000000a', 'x@x.id', 'x', 'superadmin')$q$);

SELECT pg_temp.expect_fail('         email sama walau beda huruf besar (citext)', '23505',
  $q$INSERT INTO users (tenant_id, email, password_hash, role)
     VALUES ('00000000-0000-0000-0000-00000000000a', 'SARI@samudra.id', 'x', 'admin')$q$);

SELECT pg_temp.expect_fail('Aturan 2  link_type di luar lora/cellular', '23514',
  $q$INSERT INTO devices (tenant_id, device_id, label, link_type)
     VALUES ('00000000-0000-0000-0000-00000000000a', 'KRIO-9', 'X', 'wifi')$q$);

SELECT pg_temp.expect_fail('Aturan 3  perangkat LoRa tanpa koordinat statis', '23514',
  $q$INSERT INTO devices (tenant_id, device_id, label, link_type)
     VALUES ('00000000-0000-0000-0000-00000000000a', 'KRIO-9', 'X', 'lora')$q$);

SELECT pg_temp.expect_fail('Aturan 4  status pengiriman tidak dikenal', '23514',
  $q$INSERT INTO shipments (tenant_id, device_id, product_id, origin, destination, started_at, status)
     VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a4',
             '00000000-0000-0000-0000-0000000000a2', 'A', 'B', now(), 'paused')$q$);

SELECT pg_temp.expect_fail('Aturan 5  ended_at lebih awal dari started_at', '23514',
  $q$INSERT INTO shipments (tenant_id, device_id, product_id, origin, destination, started_at, ended_at, status)
     VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a4',
             '00000000-0000-0000-0000-0000000000a2', 'A', 'B', now(), now() - interval '1 hour', 'completed')$q$);

SELECT pg_temp.expect_fail('Aturan 6  dua pengiriman aktif pada satu perangkat', '23505',
  $q$INSERT INTO shipments (tenant_id, device_id, product_id, origin, destination, started_at, status)
     VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a3',
             '00000000-0000-0000-0000-0000000000a2', 'A', 'B', now(), 'active')$q$);

SELECT pg_temp.expect_fail('Aturan 7  temp_min_c tidak lebih kecil dari temp_max_c', '23514',
  $q$INSERT INTO products (tenant_id, name, temp_min_c, temp_max_c, ea_j_per_mol, t_ref_k, shelf_life_ref_h)
     VALUES ('00000000-0000-0000-0000-00000000000a', 'X', 5, 4, 60000, 273.15, 240)$q$);

SELECT pg_temp.expect_fail('Aturan 8  horizon prediksi selain 30/60', '23514',
  $q$INSERT INTO forecasts (device_id, issued_at, horizon_min, target_ts, predicted_c, model_version)
     VALUES ('00000000-0000-0000-0000-0000000000a3', now(), 45, now(), 3.1, 'm1')$q$);

SELECT pg_temp.expect_fail('Aturan 9  remaining_pct di luar 0-100', '23514',
  $q$INSERT INTO shelf_life_states (shipment_id, updated_at, accumulated_decay, remaining_pct)
     VALUES ('00000000-0000-0000-0000-0000000000a5', now(), 0.1, 120)$q$);

SELECT pg_temp.expect_fail('Aturan 10 pembacaan duplikat (device_id, ts)', '23505',
  $q$INSERT INTO readings (device_id, ts, seq, temp_c)
     VALUES ('00000000-0000-0000-0000-0000000000a3', '2026-09-17 08:05+07', 2, 2.5)$q$);

SELECT pg_temp.expect_fail('Aturan 11 satu link dipakai untuk dua pemeriksaan', '23505',
  $q$INSERT INTO fish_quality_checks (tenant_id, shipment_id, stage, photo_url, freshness_class, confidence, model_version, upload_channel, link_id)
     VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a5', 'after', 'blob/c.jpg',
             'segar', 0.7, 'cv-v1', 'one_time_link', '00000000-0000-0000-0000-0000000000a6')$q$);

SELECT pg_temp.expect_fail('Aturan 12 pengiriman tenant A memakai perangkat tenant B', '23503',
  $q$INSERT INTO shipments (tenant_id, device_id, product_id, origin, destination, started_at, status)
     VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000b3',
             '00000000-0000-0000-0000-0000000000a2', 'A', 'B', now(), 'completed')$q$);

SELECT pg_temp.expect_fail('Aturan 12 peringatan tenant B di-ack pengguna tenant A', '23503',
  $q$INSERT INTO alerts (tenant_id, device_id, kind, severity, raised_at, acked_by, message)
     VALUES ('00000000-0000-0000-0000-00000000000b', '00000000-0000-0000-0000-0000000000b3',
             'DEVICE_OFFLINE', 'warning', now(), '00000000-0000-0000-0000-0000000000a1', 'offline')$q$);

SELECT pg_temp.expect_fail('Aturan 13 stage foto selain before/after', '23514',
  $q$INSERT INTO fish_quality_checks (tenant_id, shipment_id, stage, photo_url, freshness_class, confidence, model_version, upload_channel, uploaded_by)
     VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a5', 'during', 'blob/d.jpg',
             'segar', 0.7, 'cv-v1', 'dashboard', '00000000-0000-0000-0000-0000000000a1')$q$);

SELECT pg_temp.expect_fail('Aturan 14 kelas kesegaran tidak dikenal', '23514',
  $q$INSERT INTO fish_quality_checks (tenant_id, shipment_id, stage, photo_url, freshness_class, confidence, model_version, upload_channel, uploaded_by)
     VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a5', 'before', 'blob/d.jpg',
             'busuk', 0.7, 'cv-v1', 'dashboard', '00000000-0000-0000-0000-0000000000a1')$q$);

SELECT pg_temp.expect_fail('Aturan 15 confidence di luar 0-1', '23514',
  $q$INSERT INTO fish_quality_checks (tenant_id, shipment_id, stage, photo_url, freshness_class, confidence, model_version, upload_channel, uploaded_by)
     VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a5', 'before', 'blob/d.jpg',
             'segar', 1.5, 'cv-v1', 'dashboard', '00000000-0000-0000-0000-0000000000a1')$q$);

SELECT pg_temp.expect_fail('Aturan 16 kanal unggah tidak dikenal', '23514',
  $q$INSERT INTO fish_quality_checks (tenant_id, shipment_id, stage, photo_url, freshness_class, confidence, model_version, upload_channel, uploaded_by)
     VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a5', 'before', 'blob/d.jpg',
             'segar', 0.7, 'cv-v1', 'email', '00000000-0000-0000-0000-0000000000a1')$q$);

SELECT pg_temp.expect_fail('Aturan 17 foto dashboard tanpa uploaded_by', '23514',
  $q$INSERT INTO fish_quality_checks (tenant_id, shipment_id, stage, photo_url, freshness_class, confidence, model_version, upload_channel)
     VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a5', 'before', 'blob/d.jpg',
             'segar', 0.7, 'cv-v1', 'dashboard')$q$);

SELECT pg_temp.expect_fail('Aturan 18 token link duplikat', '23505',
  $q$INSERT INTO shipment_photo_links (tenant_id, shipment_id, token, created_by)
     VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a5',
             'tok-123', '00000000-0000-0000-0000-0000000000a1')$q$);

SELECT pg_temp.expect_fail('Aturan 18 link dipakai setelah kedaluwarsa', '23514',
  $q$UPDATE shipment_photo_links SET used_at = expires_at + interval '1 minute'
     WHERE id = '00000000-0000-0000-0000-0000000000a6'$q$);

SELECT pg_temp.expect_fail('Aturan 19 link untuk tahap selain after', '23514',
  $q$INSERT INTO shipment_photo_links (tenant_id, shipment_id, stage, token, created_by)
     VALUES ('00000000-0000-0000-0000-00000000000a', '00000000-0000-0000-0000-0000000000a5',
             'before', 'tok-456', '00000000-0000-0000-0000-0000000000a1')$q$);

SELECT 'SELESAI seluruh uji lulus' AS hasil;

ROLLBACK;
