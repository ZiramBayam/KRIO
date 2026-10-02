"""CLI pemindai peringatan KRIO.

Contoh:

    DATABASE_URL=postgresql://localhost/krio_dev PYTHONPATH=services python3 -m alerting
    PYTHONPATH=services python3 -m alerting --dsn postgresql://localhost/krio_dev --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from .scanner import scan


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="alerting", description="Pemindai peringatan KRIO (#48, #49)")
    p.add_argument("--dsn", default=os.getenv("DATABASE_URL"), help="DSN PostgreSQL")
    p.add_argument("--now", help="waktu acuan ISO 8601 UTC untuk pemeriksaan offline (uji)")
    p.add_argument("--dry-run", action="store_true", help="jalankan lalu batalkan transaksi")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dsn:
        print("DATABASE_URL atau --dsn wajib diisi", file=sys.stderr)
        return 2

    import psycopg2

    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    conn = psycopg2.connect(args.dsn)
    try:
        result = scan(conn, now=now)
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
    finally:
        conn.close()

    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
