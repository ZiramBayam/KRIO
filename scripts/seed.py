#!/usr/bin/env python3
"""Seed a dedicated demo tenant and telemetry. Safe to rerun."""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import bcrypt
import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import parse_dsn

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.emulator.fleet import INTERVAL_BY_LINK

DEVICES = (
    ("KRIO-0001", "Boks A-01", "cellular"),
    ("KRIO-0002", "Boks A-02", "cellular"),
    ("KRIO-0003", "Gudang B-01", "lora"),
)


def seed_id(name):
    return str(uuid5(NAMESPACE_URL, f"urn:krio:demo:{name}"))


def seed(conn, password):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    tenant_id = seed_id("tenant")
    product_id = seed_id("ikan-tongkol")
    shipment_id = seed_id("active-shipment")
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    with conn, conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (847206184,))
        cur.execute(
            "INSERT INTO tenants (id, name) VALUES (%s, 'Demo Seafood') ON CONFLICT (id) DO NOTHING",
            (tenant_id,),
        )
        for account, role in (("admin", "owner"), ("operator", "admin"), ("viewer", "viewer")):
            cur.execute(
                """
                INSERT INTO users (id, tenant_id, email, password_hash, role)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash
                WHERE users.tenant_id = EXCLUDED.tenant_id
                """,
                (seed_id(account), tenant_id, f"{account}@demo.com", password_hash, role),
            )
            if cur.rowcount != 1:
                raise ValueError("A demo account already belongs to another tenant")

        for slug, label in (("ikan-tongkol", "Ikan Tongkol"), ("ikan-nila", "Ikan Nila")):
            cur.execute(
                """
                INSERT INTO products
                    (id, tenant_id, name, temp_min_c, temp_max_c, ea_j_per_mol,
                     t_ref_k, shelf_life_ref_h)
                VALUES (%s, %s, %s, 0, 4, 60000, 273.15, 240)
                ON CONFLICT (id) DO NOTHING
                """,
                (seed_id(slug), tenant_id, label),
            )

        for code, label, link in DEVICES:
            static_location = (-7.7956, 110.3695) if link == "lora" else (None, None)
            cur.execute(
                """
                INSERT INTO devices
                    (id, tenant_id, device_id, label, link_type, static_lat, static_lon, registered_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (device_id) DO UPDATE SET label = EXCLUDED.label
                WHERE devices.tenant_id = EXCLUDED.tenant_id AND devices.id = EXCLUDED.id
                """,
                (seed_id(code), tenant_id, code, label, link, *static_location, now - timedelta(days=1)),
            )
            if cur.rowcount != 1:
                raise ValueError(f"{code} already belongs to another device record")

        cur.execute(
            """
            INSERT INTO shipments
                (id, tenant_id, device_id, product_id, origin, destination, started_at, status)
            VALUES (%s, %s, %s, %s, 'Gudang KRIO', 'Pasar Tujuan', %s, 'active')
            ON CONFLICT (id) DO NOTHING
            """,
            (shipment_id, tenant_id, seed_id(DEVICES[0][0]), product_id, now - timedelta(days=1)),
        )

        for index, (code, _, link) in enumerate(DEVICES):
            device_id = seed_id(code)
            step = timedelta(seconds=INTERVAL_BY_LINK[link])
            end = now - step
            cur.execute(
                """
                INSERT INTO readings (device_id, ts, shipment_id, seq, temp_c, batt_v, rh_pct, rssi)
                SELECT %s, ts, %s, row_number() OVER (ORDER BY ts),
                       2.0 + 0.3 * sin(extract(epoch FROM ts) / 1800 + %s), 4.1, 75, -82
                FROM generate_series(%s::timestamptz, %s::timestamptz, %s::interval) AS series(ts)
                WHERE NOT EXISTS (SELECT 1 FROM readings WHERE device_id = %s)
                ON CONFLICT (device_id, ts) DO NOTHING
                """,
                (device_id, shipment_id if index == 0 else None, index,
                 now - timedelta(days=1), end, step, device_id),
            )
            cur.execute(
                "UPDATE devices SET last_seen_at = greatest(last_seen_at, "
                "(SELECT max(ts) FROM readings WHERE device_id = %s)) WHERE id = %s",
                (device_id, device_id),
            )

        for key, severity, minutes in (("warning", "warning", 120), ("critical", "critical", 60)):
            cur.execute(
                """
                INSERT INTO alerts (id, tenant_id, device_id, shipment_id, kind, severity, raised_at, message)
                VALUES (%s, %s, %s, %s, 'KEGAGALAN_PENDINGIN', %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (seed_id(key), tenant_id, seed_id(DEVICES[0][0]), shipment_id, severity,
                 now - timedelta(minutes=minutes), f"Contoh demo: suhu melampaui ambang ({severity})"),
            )


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("DATABASE_URL"))
    args = parser.parse_args()
    if not args.url:
        parser.error("Set DATABASE_URL or pass --url")
    password = os.getenv("KRIO_DEMO_PASSWORD")
    host = parse_dsn(args.url).get("host", os.getenv("PGHOST", ""))
    local = host in ("", "localhost", "127.0.0.1", "::1") or host.startswith("/")
    if not local and (not password or len(password) < 12 or password == "password123"):
        parser.error("Set KRIO_DEMO_PASSWORD to a unique password of at least 12 characters")
    if password and len(password.encode()) > 72:
        parser.error("KRIO_DEMO_PASSWORD must be at most 72 bytes for bcrypt")
    conn = psycopg2.connect(args.url, connect_timeout=5)
    try:
        seed(conn, password or "password123")
    finally:
        conn.close()
    print("Demo tenant, accounts, devices, shipment, readings and sample alerts are ready.")


if __name__ == "__main__":
    main()
