"""PostgreSQL transactions used by the demo API."""

import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor


@contextmanager
def transaction(dsn=None):
    conn = psycopg2.connect(dsn or os.environ["DATABASE_URL"], connect_timeout=5)
    try:
        with conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            yield cursor
    finally:
        conn.close()
