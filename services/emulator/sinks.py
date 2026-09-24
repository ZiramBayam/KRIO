"""Tujuan pengiriman telemetri emulator.

Emulator memisahkan model termal dari cara pengiriman, sehingga jalur IoT Hub
dapat ditambahkan tanpa mengubah simulasi. Selama Azure IoT Hub belum aktif
(lihat issue #22 dan #23), emulator menulis ke stdout atau langsung ke
PostgreSQL agar dashboard dan alerting tetap dapat dikembangkan.
"""
from __future__ import annotations

import json
import sys
from typing import Protocol


class Sink(Protocol):
    """Tujuan satu pesan telemetri."""

    def send(self, payload: dict) -> None: ...

    def close(self) -> None: ...


class StdoutSink:
    """Menulis satu pesan JSON per baris (JSON Lines) ke stdout."""

    def send(self, payload: dict) -> None:
        sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
        sys.stdout.flush()

    def close(self) -> None:
        pass


class PostgresSink:
    """Menulis telemetri langsung ke tabel ``readings``.

    Perangkat harus sudah terdaftar pada tabel ``devices``; pesan dari
    ``device_id`` yang tidak dikenal dilewati dan dihitung sebagai pesan ditolak,
    meniru validasi yang nantinya dilakukan fn_ingest (issue #34).
    """

    def __init__(self, dsn: str) -> None:
        import psycopg2  # impor lokal agar stdout sink tidak butuh driver

        self.conn = psycopg2.connect(dsn)
        self.conn.autocommit = True
        self.rejected = 0
        self._device_ids: dict[str, str] = {}
        with self.conn.cursor() as cur:
            cur.execute("SELECT device_id, id FROM devices")
            self._device_ids = {row[0]: row[1] for row in cur.fetchall()}

    def send(self, payload: dict) -> None:
        device_uuid = self._device_ids.get(payload["device_id"])
        if device_uuid is None:
            self.rejected += 1
            return
        gps = payload.get("gps") or {}
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO readings (device_id, ts, seq, temp_c, rh_pct, batt_v, rssi, lat, lon, buffered)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (device_id, ts) DO NOTHING
                """,
                (
                    device_uuid,
                    payload["ts"],
                    payload["seq"],
                    payload["temp_c"],
                    payload.get("rh_pct"),
                    payload.get("batt_v"),
                    payload.get("rssi"),
                    gps.get("lat"),
                    gps.get("lon"),
                    payload.get("buffered", False),
                ),
            )

    def close(self) -> None:
        self.conn.close()


def make_sink(name: str, dsn: str | None = None) -> Sink:
    if name == "stdout":
        return StdoutSink()
    if name == "postgres":
        if not dsn:
            raise ValueError("sink postgres membutuhkan DATABASE_URL atau --dsn")
        return PostgresSink(dsn)
    raise ValueError(f"sink tidak dikenal: {name!r}")
