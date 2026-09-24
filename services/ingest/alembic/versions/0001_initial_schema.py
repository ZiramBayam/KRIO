"""Skema awal KRIO

Revisi ini menjalankan db/migrations/0001_init.sql sebagai satu-satunya sumber
kebenaran skema awal, sehingga tidak ada duplikasi definisi tabel antara berkas
SQL dan berkas revisi ini.

Basis data yang skemanya sudah dibuat lebih dahulu melalui psql (lihat
scripts/deploy_db.sh) tidak perlu dimigrasikan ulang; tandai saja revisinya:

    alembic stamp 0001_initial_schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-24
"""
import re
from pathlib import Path

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

SQL_PATH = Path(__file__).resolve().parents[2] / "db" / "migrations" / "0001_init.sql"

# Tabel sesuai ERD Lab 2.4, diurutkan terbalik terhadap dependensinya.
TABLES = [
    "fish_quality_checks",
    "shipment_photo_links",
    "reports",
    "shelf_life_states",
    "alerts",
    "forecasts",
    "readings",
    "shipments",
    "devices",
    "products",
    "users",
    "tenants",
]


def upgrade() -> None:
    sql = SQL_PATH.read_text(encoding="utf-8")
    # Alembic sudah membuka transaksi sendiri; BEGIN/COMMIT di dalam berkas
    # akan menutup transaksi tersebut lebih awal, sehingga dibuang.
    sql = re.sub(r"^\s*(BEGIN|COMMIT)\s*;\s*$", "", sql, flags=re.MULTILINE | re.IGNORECASE)
    op.execute(sql)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS create_readings_partition(date)")
    for table in TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    # Ekstensi citext sengaja tidak di-drop: ekstensi bersifat tingkat basis
    # data dan dapat dipakai objek lain di luar migrasi ini.
