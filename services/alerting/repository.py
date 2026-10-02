"""Akses basis data untuk peringatan KRIO (issue #48 dan #49).

Seluruh kueri difilter ``tenant_id`` mengikuti aturan isolasi tenant pada
PRD §10. Modul ini hanya membaca dan menulis; keputusan ada di ``rules.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .rules import AlertDraft, ThresholdRange

# Pembacaan terbaru tiap perangkat yang sedang menjalani pengiriman aktif,
# beserta ambang produk yang dibawanya.
SQL_ACTIVE_READINGS = """
SELECT DISTINCT ON (d.id)
       d.id            AS device_id,
       d.tenant_id     AS tenant_id,
       d.device_id     AS device_code,
       d.label         AS device_label,
       s.id            AS shipment_id,
       p.temp_min_c    AS temp_min_c,
       p.temp_max_c    AS temp_max_c,
       r.ts            AS ts,
       r.temp_c        AS temp_c
FROM shipments s
JOIN devices  d ON d.id = s.device_id  AND d.tenant_id = s.tenant_id
JOIN products p ON p.id = s.product_id AND p.tenant_id = s.tenant_id
JOIN readings r ON r.device_id = d.id
WHERE s.status = 'active'
ORDER BY d.id, r.ts DESC
"""

# Perangkat dengan pengiriman aktif beserta telemetri terakhirnya.
SQL_ACTIVE_DEVICES = """
SELECT d.id        AS device_id,
       d.tenant_id AS tenant_id,
       d.label     AS device_label,
       s.id        AS shipment_id,
       (SELECT max(r.ts) FROM readings r WHERE r.device_id = d.id) AS last_seen_at
FROM shipments s
JOIN devices d ON d.id = s.device_id AND d.tenant_id = s.tenant_id
WHERE s.status = 'active'
"""

SQL_LAST_ALERT = """
SELECT max(raised_at)
FROM alerts
WHERE tenant_id = %s AND device_id = %s AND kind = %s
"""

SQL_INSERT_ALERT = """
INSERT INTO alerts (tenant_id, shipment_id, device_id, kind, severity, raised_at, message)
VALUES (%s, %s, %s, %s, %s, %s, %s)
RETURNING id
"""

# Perangkat yang kembali mengirim setelah peringatan offline terbit.
SQL_RESOLVE_OFFLINE = """
UPDATE alerts a
SET resolved_at = r.last_ts
FROM (SELECT device_id, max(ts) AS last_ts FROM readings GROUP BY device_id) r
WHERE a.device_id = r.device_id
  AND a.kind = 'DEVICE_OFFLINE'
  AND a.resolved_at IS NULL
  AND r.last_ts > a.raised_at
RETURNING a.id
"""


@dataclass(frozen=True)
class DeviceReading:
    """Pembacaan terbaru satu perangkat beserta konteks pengirimannya."""

    device_id: str
    tenant_id: str
    device_label: str
    shipment_id: str
    thresholds: ThresholdRange
    ts: datetime
    temp_c: float


@dataclass(frozen=True)
class DeviceStatus:
    """Perangkat dengan pengiriman aktif dan waktu telemetri terakhirnya."""

    device_id: str
    tenant_id: str
    device_label: str
    shipment_id: str
    last_seen_at: datetime | None


class AlertRepository:
    """Pembungkus kueri peringatan di atas satu koneksi psycopg2."""

    def __init__(self, conn) -> None:
        self.conn = conn

    def latest_readings(self) -> list[DeviceReading]:
        with self.conn.cursor() as cur:
            cur.execute(SQL_ACTIVE_READINGS)
            return [
                DeviceReading(
                    device_id=row[0],
                    tenant_id=row[1],
                    device_label=row[3] or row[2],
                    shipment_id=row[4],
                    thresholds=ThresholdRange(float(row[5]), float(row[6])),
                    ts=row[7],
                    temp_c=float(row[8]),
                )
                for row in cur.fetchall()
            ]

    def active_devices(self) -> list[DeviceStatus]:
        with self.conn.cursor() as cur:
            cur.execute(SQL_ACTIVE_DEVICES)
            return [
                DeviceStatus(
                    device_id=row[0],
                    tenant_id=row[1],
                    device_label=row[2],
                    shipment_id=row[3],
                    last_seen_at=row[4],
                )
                for row in cur.fetchall()
            ]

    def last_alert_at(self, tenant_id: str, device_id: str, kind: str) -> datetime | None:
        with self.conn.cursor() as cur:
            cur.execute(SQL_LAST_ALERT, (tenant_id, device_id, kind))
            return cur.fetchone()[0]

    def insert_alert(
        self, tenant_id: str, device_id: str, shipment_id: str | None, draft: AlertDraft
    ) -> str:
        with self.conn.cursor() as cur:
            cur.execute(
                SQL_INSERT_ALERT,
                (
                    tenant_id,
                    shipment_id,
                    device_id,
                    draft.kind,
                    draft.severity,
                    draft.raised_at,
                    draft.message,
                ),
            )
            return cur.fetchone()[0]

    def resolve_recovered_offline(self) -> int:
        """Menutup peringatan DEVICE_OFFLINE bila perangkat kembali mengirim."""
        with self.conn.cursor() as cur:
            cur.execute(SQL_RESOLVE_OFFLINE)
            return len(cur.fetchall())
