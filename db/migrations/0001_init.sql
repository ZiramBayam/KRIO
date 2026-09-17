-- =============================================================================
-- KRIO — Migrasi 0001: skema awal basis data
-- Acuan : ERD Lab 2.4 (Tahap 3 — Software Design) dan PRD KRIO v1.2 §10
-- Target: PostgreSQL 13+ (gen_random_uuid() bawaan); diuji pada PostgreSQL 18
--
-- Nomor "Aturan N" pada komentar merujuk daftar "Aturan integritas data" Lab 2.4.
--
-- Isolasi tenant (Aturan 12):
--   - Tabel yang memiliki kolom tenant_id memakai foreign key gabungan
--     (tenant_id, id), sehingga relasi lintas tenant ditolak oleh basis data.
--   - readings, forecasts, shelf_life_states, dan reports tidak memiliki
--     tenant_id; konsistensi tenant untuk tabel tersebut ditegakkan di lapisan
--     kueri aplikasi (PRD §10, catatan implementasi).
-- =============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS citext;

-- -----------------------------------------------------------------------------
-- tenants
-- -----------------------------------------------------------------------------
CREATE TABLE tenants (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name       text        NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- users
-- -----------------------------------------------------------------------------
CREATE TABLE users (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid        NOT NULL REFERENCES tenants (id),
  email         citext      NOT NULL UNIQUE,
  password_hash text        NOT NULL,
  role          text        NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT users_role_chk CHECK (role IN ('owner', 'admin', 'viewer')),  -- Aturan 1
  CONSTRAINT users_tenant_id_uq UNIQUE (tenant_id, id)
);

-- -----------------------------------------------------------------------------
-- products
-- -----------------------------------------------------------------------------
CREATE TABLE products (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        uuid NOT NULL REFERENCES tenants (id),
  name             text NOT NULL,
  temp_min_c       real NOT NULL,
  temp_max_c       real NOT NULL,
  ea_j_per_mol     real NOT NULL,
  t_ref_k          real NOT NULL,
  shelf_life_ref_h real NOT NULL,

  CONSTRAINT products_temp_range_chk CHECK (temp_min_c < temp_max_c),      -- Aturan 7
  CONSTRAINT products_tenant_id_uq UNIQUE (tenant_id, id)
);

-- -----------------------------------------------------------------------------
-- devices
-- -----------------------------------------------------------------------------
CREATE TABLE devices (
  id            uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid             NOT NULL REFERENCES tenants (id),
  device_id     text             NOT NULL UNIQUE,  -- sama dengan identitas di IoT Hub
  label         text             NOT NULL,
  link_type     text             NOT NULL,
  static_lat    double precision,
  static_lon    double precision,
  registered_at timestamptz      NOT NULL DEFAULT now(),
  last_seen_at  timestamptz,

  CONSTRAINT devices_link_type_chk CHECK (link_type IN ('lora', 'cellular')),  -- Aturan 2
  CONSTRAINT devices_lora_location_chk CHECK (                                  -- Aturan 3
    link_type <> 'lora' OR (static_lat IS NOT NULL AND static_lon IS NOT NULL)
  ),
  CONSTRAINT devices_tenant_id_uq UNIQUE (tenant_id, id)
);

-- -----------------------------------------------------------------------------
-- shipments
-- -----------------------------------------------------------------------------
CREATE TABLE shipments (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    uuid        NOT NULL REFERENCES tenants (id),
  device_id    uuid        NOT NULL,
  product_id   uuid        NOT NULL,
  origin       text        NOT NULL,
  destination  text        NOT NULL,
  handler_name text,
  started_at   timestamptz NOT NULL,
  ended_at     timestamptz,
  status       text        NOT NULL,

  CONSTRAINT shipments_device_fk FOREIGN KEY (tenant_id, device_id)
    REFERENCES devices (tenant_id, id),
  CONSTRAINT shipments_product_fk FOREIGN KEY (tenant_id, product_id)
    REFERENCES products (tenant_id, id),
  CONSTRAINT shipments_status_chk CHECK (status IN ('active', 'completed', 'aborted')),  -- Aturan 4
  CONSTRAINT shipments_time_chk CHECK (ended_at IS NULL OR ended_at >= started_at),     -- Aturan 5
  CONSTRAINT shipments_tenant_id_uq UNIQUE (tenant_id, id)
);

-- Aturan 6: satu perangkat tidak boleh memiliki dua pengiriman aktif.
CREATE UNIQUE INDEX shipments_one_active_per_device_uq
  ON shipments (device_id) WHERE status = 'active';
CREATE INDEX shipments_product_id_idx ON shipments (product_id);

-- -----------------------------------------------------------------------------
-- readings — dipartisi bulanan (PRD §10) agar retensi cukup DROP PARTITION
-- -----------------------------------------------------------------------------
CREATE TABLE readings (
  device_id   uuid             NOT NULL REFERENCES devices (id),
  ts          timestamptz      NOT NULL,
  shipment_id uuid             REFERENCES shipments (id),  -- nullable (penyesuaian Lab 2.4)
  seq         bigint           NOT NULL,  -- deteksi paket hilang/duplikat, bukan urutan waktu (Aturan 11)
  temp_c      real             NOT NULL,
  rh_pct      real,
  batt_v      real,
  rssi        smallint,
  lat         double precision,
  lon         double precision,
  buffered    boolean          NOT NULL DEFAULT false,

  PRIMARY KEY (device_id, ts)  -- Aturan 10; indeks ini juga melayani kueri (device_id, ts DESC)
) PARTITION BY RANGE (ts);

CREATE INDEX readings_shipment_id_idx ON readings (shipment_id);

-- Membuat partisi readings untuk bulan yang memuat p_month (idempoten).
CREATE FUNCTION create_readings_partition(p_month date)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  v_start date := date_trunc('month', p_month)::date;
  v_end   date := (date_trunc('month', p_month) + interval '1 month')::date;
  v_name  text := format('readings_%s', to_char(v_start, 'YYYY_MM'));
BEGIN
  EXECUTE format(
    'CREATE TABLE IF NOT EXISTS %I PARTITION OF readings FOR VALUES FROM (%L) TO (%L)',
    v_name, v_start, v_end
  );
END;
$$;

-- Partisi satu semester (Sep 2026 – Feb 2027); bulan berikutnya dibuat oleh
-- Function terjadwal. Partisi default menampung data di luar rentang agar
-- ingest tidak pernah gagal.
DO $$
DECLARE
  m date;
BEGIN
  FOR m IN
    SELECT generate_series(date '2026-09-01', date '2027-02-01', interval '1 month')::date
  LOOP
    PERFORM create_readings_partition(m);
  END LOOP;
END;
$$;

CREATE TABLE readings_default PARTITION OF readings DEFAULT;

-- -----------------------------------------------------------------------------
-- forecasts
-- -----------------------------------------------------------------------------
CREATE TABLE forecasts (
  id            bigserial   PRIMARY KEY,
  device_id     uuid        NOT NULL REFERENCES devices (id),
  issued_at     timestamptz NOT NULL,
  horizon_min   smallint    NOT NULL,
  target_ts     timestamptz NOT NULL,
  predicted_c   real        NOT NULL,
  model_version text        NOT NULL,

  CONSTRAINT forecasts_horizon_chk CHECK (horizon_min IN (30, 60))  -- Aturan 8
);

CREATE INDEX forecasts_device_target_idx ON forecasts (device_id, target_ts DESC);

-- -----------------------------------------------------------------------------
-- alerts
-- -----------------------------------------------------------------------------
CREATE TABLE alerts (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     uuid        NOT NULL REFERENCES tenants (id),
  shipment_id   uuid,
  device_id     uuid        NOT NULL,
  kind          text        NOT NULL,
  severity      text        NOT NULL,
  raised_at     timestamptz NOT NULL,
  predicted_for timestamptz,
  resolved_at   timestamptz,
  acked_by      uuid,
  message       text        NOT NULL,

  CONSTRAINT alerts_device_fk FOREIGN KEY (tenant_id, device_id)
    REFERENCES devices (tenant_id, id),
  CONSTRAINT alerts_shipment_fk FOREIGN KEY (tenant_id, shipment_id)
    REFERENCES shipments (tenant_id, id),
  CONSTRAINT alerts_acked_by_fk FOREIGN KEY (tenant_id, acked_by)
    REFERENCES users (tenant_id, id),
  CONSTRAINT alerts_kind_chk CHECK (kind IN (
    'PREDICTED_EXCURSION', 'KEGAGALAN_PENDINGIN', 'PINTU_DIBUKA', 'DEVICE_OFFLINE'
  )),
  CONSTRAINT alerts_severity_chk CHECK (severity IN ('info', 'warning', 'critical'))
);

CREATE INDEX alerts_tenant_raised_idx ON alerts (tenant_id, raised_at DESC);
CREATE INDEX alerts_open_idx ON alerts (tenant_id) WHERE resolved_at IS NULL;
CREATE INDEX alerts_device_id_idx ON alerts (device_id);
CREATE INDEX alerts_shipment_id_idx ON alerts (shipment_id);

-- -----------------------------------------------------------------------------
-- shelf_life_states
-- -----------------------------------------------------------------------------
CREATE TABLE shelf_life_states (
  shipment_id       uuid        PRIMARY KEY REFERENCES shipments (id),
  updated_at        timestamptz NOT NULL,
  accumulated_decay real        NOT NULL,  -- D, tak berdimensi; 1.0 = habis
  remaining_pct     real        NOT NULL,
  projected_pct_60m real,
  mkt_c             real,

  CONSTRAINT shelf_life_remaining_chk CHECK (remaining_pct BETWEEN 0 AND 100),  -- Aturan 9
  CONSTRAINT shelf_life_projected_chk CHECK (
    projected_pct_60m IS NULL OR projected_pct_60m BETWEEN 0 AND 100
  )
);

-- -----------------------------------------------------------------------------
-- reports — metadata laporan compliance; berkas PDF di Blob Storage
-- -----------------------------------------------------------------------------
CREATE TABLE reports (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  shipment_id  uuid        NOT NULL REFERENCES shipments (id),
  blob_path    text        NOT NULL,
  mkt_c        real,
  generated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX reports_shipment_generated_idx ON reports (shipment_id, generated_at DESC);

-- -----------------------------------------------------------------------------
-- shipment_photo_links — link sekali pakai untuk foto `after`
-- (dibuat sebelum fish_quality_checks karena direferensikan olehnya)
-- -----------------------------------------------------------------------------
CREATE TABLE shipment_photo_links (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   uuid        NOT NULL REFERENCES tenants (id),
  shipment_id uuid        NOT NULL,
  stage       text        NOT NULL DEFAULT 'after',
  token       text        NOT NULL UNIQUE,                              -- Aturan 18
  expires_at  timestamptz NOT NULL DEFAULT now() + interval '24 hours', -- FR-66
  used_at     timestamptz,
  created_by  uuid        NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT photo_links_shipment_fk FOREIGN KEY (tenant_id, shipment_id)
    REFERENCES shipments (tenant_id, id),
  CONSTRAINT photo_links_created_by_fk FOREIGN KEY (tenant_id, created_by)
    REFERENCES users (tenant_id, id),
  CONSTRAINT photo_links_stage_chk CHECK (stage = 'after'),                   -- Aturan 19
  CONSTRAINT photo_links_expiry_chk CHECK (expires_at > created_at),
  CONSTRAINT photo_links_used_before_expiry_chk CHECK (                       -- Aturan 18
    used_at IS NULL OR used_at <= expires_at
  ),
  CONSTRAINT photo_links_tenant_id_uq UNIQUE (tenant_id, id)
);

CREATE INDEX photo_links_shipment_id_idx ON shipment_photo_links (shipment_id);

-- -----------------------------------------------------------------------------
-- fish_quality_checks
-- -----------------------------------------------------------------------------
CREATE TABLE fish_quality_checks (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid        NOT NULL REFERENCES tenants (id),
  shipment_id     uuid        NOT NULL,
  stage           text        NOT NULL,
  photo_url       text        NOT NULL,  -- path di Blob Storage
  freshness_class text        NOT NULL,
  confidence      real        NOT NULL,
  model_version   text        NOT NULL,
  upload_channel  text        NOT NULL,
  uploaded_by     uuid,
  link_id         uuid        UNIQUE,    -- Aturan 11: satu link menghasilkan maksimal satu pemeriksaan
  created_at      timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT fqc_shipment_fk FOREIGN KEY (tenant_id, shipment_id)
    REFERENCES shipments (tenant_id, id),
  CONSTRAINT fqc_uploaded_by_fk FOREIGN KEY (tenant_id, uploaded_by)
    REFERENCES users (tenant_id, id),
  CONSTRAINT fqc_link_fk FOREIGN KEY (tenant_id, link_id)
    REFERENCES shipment_photo_links (tenant_id, id),
  CONSTRAINT fqc_stage_chk CHECK (stage IN ('before', 'after')),              -- Aturan 13
  CONSTRAINT fqc_freshness_chk CHECK (                                        -- Aturan 14
    freshness_class IN ('sangat_segar', 'segar', 'tidak_segar')
  ),
  CONSTRAINT fqc_confidence_chk CHECK (confidence BETWEEN 0 AND 1),           -- Aturan 15
  CONSTRAINT fqc_upload_channel_chk CHECK (                                   -- Aturan 16
    upload_channel IN ('dashboard', 'one_time_link')
  ),
  -- Aturan 17: foto dashboard wajib uploaded_by; foto via link wajib link_id.
  -- Foto via link selalu tahap `after` (Aturan 19).
  CONSTRAINT fqc_channel_source_chk CHECK (
    (upload_channel = 'dashboard'
      AND uploaded_by IS NOT NULL AND link_id IS NULL)
    OR
    (upload_channel = 'one_time_link'
      AND link_id IS NOT NULL AND uploaded_by IS NULL AND stage = 'after')
  )
);

CREATE INDEX fqc_shipment_stage_idx ON fish_quality_checks (shipment_id, stage);

COMMIT;
