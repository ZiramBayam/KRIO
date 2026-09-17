#!/usr/bin/env python3
"""
KRIO — Seed Script
Buat data demo: tenant, users, produk, device.
Jalankan: python3 scripts/seed.py
"""

import os
import sys
import uuid
import hashlib
import argparse
from datetime import datetime, timezone

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 belum terinstall. Jalankan:")
    print("  pip install psycopg2-binary")
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/krio_dev")


def hash_password(password: str) -> str:
    """Hash password dengan bcrypt-compatible format."""
    # SHA-256 fallback jika bcrypt tidak ada (untuk seed saja)
    return hashlib.sha256(password.encode()).hexdigest()


def seed(conn):
    cur = conn.cursor()
    now = datetime.now(timezone.utc)

    # --- Tenant ---
    tenant_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO tenants (id, name, created_at) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        (tenant_id, "Demo Seafood", now),
    )
    print(f"[OK] Tenant 'Demo Seafood' dibuat (id={tenant_id})")

    # --- Users ---
    users = [
        ("admin@demo.com", "owner", "Admin Demo"),
        ("operator@demo.com", "admin", "Operator Demo"),
        ("viewer@demo.com", "viewer", "Viewer Demo"),
    ]
    for email, role, name in users:
        user_id = str(uuid.uuid4())
        cur.execute(
            """INSERT INTO users (id, tenant_id, email, password_hash, role, created_at)
               VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (email) DO NOTHING""",
            (user_id, tenant_id, email, hash_password("password123"), role, now),
        )
        print(f"[OK] User '{email}' (role={role}) dibuat")

    # --- Product ---
    product_id = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO products (id, tenant_id, name, temp_min_c, temp_max_c,
           ea_j_per_mol, t_ref_k, shelf_life_ref_h)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
        (
            product_id, tenant_id, "Ikan Tongkol",
            0.0, 4.0,       # temp range
            83140.0,         # Ea (J/mol) — ikan segar
            278.15,          # T_ref (5°C dalam Kelvin)
            168.0,           # shelf life ref (7 hari × 24 jam)
        ),
    )
    print(f"[OK] Produk 'Ikan Tongkol' dibuat (id={product_id})")

    # --- Device ---
    device_id_db = str(uuid.uuid4())
    cur.execute(
        """INSERT INTO devices (id, tenant_id, device_id, label, link_type,
           registered_at)
           VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (device_id) DO NOTHING""",
        (
            device_id_db, tenant_id, "EMULATOR-001",
            "Emulator Utama", "cellular", now,
        ),
    )
    print(f"[OK] Device 'EMULATOR-001' dibuat (id={device_id_db})")

    conn.commit()
    print("\n=== SEED SELESAI ===")
    print(f"Tenant ID : {tenant_id}")
    print("Login     : admin@demo.com / password123")

    cur.close()


def main():
    parser = argparse.ArgumentParser(description="KRIO Database Seed Script")
    parser.add_argument("--url", help="Database URL (default: DATABASE_URL env var)")
    args = parser.parse_args()

    url = args.url or DATABASE_URL
    print(f"Connecting to: {url.split('@')[-1] if '@' in url else url}")

    try:
        conn = psycopg2.connect(url)
        conn.autocommit = False
        seed(conn)
        conn.close()
    except psycopg2.OperationalError as e:
        print(f"\nERROR: Tidak bisa koneksi ke database.\n{e}")
        print("Pastikan PostgreSQL berjalan dan DATABASE_URL benar.")
        sys.exit(1)


if __name__ == "__main__":
    main()
