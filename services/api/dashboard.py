"""Tenant-scoped device, reading, alert and shipment views."""

from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import AwareDatetime, BaseModel

from services.alerting.rules import offline_after

from .auth import Authenticated, Writer
from .db import transaction
from .simulation import time_scale

router = APIRouter()

DEVICE_QUERY = """
SELECT d.id, d.device_id, d.label, d.link_type, greatest(d.last_seen_at, r.ts) AS last_seen_at,
       r.temp_c, r.batt_v, r.rh_pct, r.rssi, r.ts AS reading_at,
       p.temp_min_c, p.temp_max_c
FROM devices d
LEFT JOIN LATERAL (
    SELECT temp_c, batt_v, rh_pct, rssi, ts FROM readings
    WHERE device_id = d.id ORDER BY ts DESC LIMIT 1
) r ON true
LEFT JOIN shipments s ON s.device_id = d.id AND s.tenant_id = d.tenant_id AND s.status = 'active'
LEFT JOIN products p ON p.id = s.product_id AND p.tenant_id = d.tenant_id
WHERE d.tenant_id = %s
"""


class Device(BaseModel):
    id: UUID
    device_id: str
    label: str
    link_type: Literal["cellular", "lora"]
    last_seen_at: datetime | None
    reading_at: datetime | None
    temp_c: float | None
    batt_v: float | None
    rh_pct: float | None
    rssi: int | None
    temp_min_c: float | None
    temp_max_c: float | None
    status: Literal["online", "offline"]


def device_status(row, now):
    last_seen = row["last_seen_at"]
    scale = time_scale(str(row["id"]))
    online = last_seen is not None and (now - last_seen) * scale <= offline_after(row["link_type"])
    return dict(row, last_seen_at=last_seen, status="online" if online else "offline")


@router.get("/devices")
def devices(user: Authenticated) -> list[Device]:
    with transaction() as cur:
        cur.execute(DEVICE_QUERY + " ORDER BY d.label, d.id", (str(user.tenant_id),))
        now = datetime.now(timezone.utc)
        return [device_status(row, now) for row in cur.fetchall()]


@router.get("/devices/{device_id}")
def device(device_id: UUID, user: Authenticated) -> Device:
    with transaction() as cur:
        cur.execute(DEVICE_QUERY + " AND d.id = %s", (str(user.tenant_id), str(device_id)))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Device not found")
    return device_status(row, datetime.now(timezone.utc))


class ReadingBucket(BaseModel):
    ts: datetime
    temp_c: float
    count: int


@router.get("/readings")
def readings(
    device_id: UUID, user: Authenticated,
    from_at: AwareDatetime | None = Query(default=None, alias="from"),
    to: AwareDatetime | None = None, bucket: Literal["10s", "1m", "5m", "1h"] = "5m",
) -> list[ReadingBucket]:
    end = to or datetime.now(timezone.utc)
    start = from_at or end - timedelta(hours=24)
    if not timedelta(0) < end - start <= timedelta(days=7):
        raise HTTPException(400, "Reading range must be positive and at most 7 days")
    interval = {"10s": 10, "1m": 60, "5m": 300, "1h": 3600}[bucket]
    with transaction() as cur:
        cur.execute(
            "SELECT 1 FROM devices WHERE id = %s AND tenant_id = %s",
            (str(device_id), str(user.tenant_id)),
        )
        if not cur.fetchone():
            raise HTTPException(404, "Device not found")
        cur.execute(
            """
            SELECT to_timestamp(floor(extract(epoch FROM r.ts) / %s::int) * %s::int) AS ts,
                   avg(r.temp_c) AS temp_c, count(*) AS count
            FROM readings r JOIN devices d ON d.id = r.device_id
            WHERE d.id = %s AND d.tenant_id = %s AND r.ts >= %s AND r.ts <= %s
            GROUP BY 1 ORDER BY 1
            """,
            (interval, interval, str(device_id), str(user.tenant_id), start, end),
        )
        return cur.fetchall()


class Alert(BaseModel):
    id: UUID
    device_id: UUID
    shipment_id: UUID | None
    kind: str
    severity: Literal["info", "warning", "critical"]
    message: str
    raised_at: datetime
    resolved_at: datetime | None
    acked_by: UUID | None


ALERT_COLUMNS = "id, device_id, shipment_id, kind, severity, message, raised_at, resolved_at, acked_by"


@router.get("/alerts")
def alerts(user: Authenticated, status: Literal["active", "resolved", "all"] = "active") -> list[Alert]:
    condition = {
        "active": " AND resolved_at IS NULL",
        "resolved": " AND resolved_at IS NOT NULL",
        "all": "",
    }[status]
    with transaction() as cur:
        cur.execute(
            f"SELECT {ALERT_COLUMNS} FROM alerts WHERE tenant_id = %s"
            f"{condition} ORDER BY raised_at DESC, id LIMIT 200",
            (str(user.tenant_id),),
        )
        return cur.fetchall()


@router.post("/alerts/{alert_id}/ack")
def acknowledge(alert_id: UUID, user: Writer) -> Alert:
    with transaction() as cur:
        cur.execute(
            f"""
            UPDATE alerts SET acked_by = coalesce(acked_by, %s), resolved_at = coalesce(resolved_at, now())
            WHERE id = %s AND tenant_id = %s
            RETURNING {ALERT_COLUMNS}
            """,
            (str(user.id), str(alert_id), str(user.tenant_id)),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Alert not found")
    return row


class Shipment(BaseModel):
    id: UUID
    device_id: UUID
    device_label: str
    product_id: UUID
    product_name: str
    origin: str
    destination: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    temp_min_c: float
    temp_max_c: float


SHIPMENTS_QUERY = """
SELECT s.id, s.device_id, d.label AS device_label, s.product_id, p.name AS product_name,
       s.origin, s.destination, s.status, s.started_at, s.ended_at, p.temp_min_c, p.temp_max_c
FROM shipments s
JOIN devices d ON d.id = s.device_id AND d.tenant_id = s.tenant_id
JOIN products p ON p.id = s.product_id AND p.tenant_id = s.tenant_id
WHERE s.tenant_id = %s
"""


@router.get("/shipments")
def shipments(user: Authenticated) -> list[Shipment]:
    with transaction() as cur:
        cur.execute(SHIPMENTS_QUERY + " ORDER BY s.started_at DESC, s.id", (str(user.tenant_id),))
        return cur.fetchall()


@router.get("/shipments/{shipment_id}")
def shipment(shipment_id: UUID, user: Authenticated) -> Shipment:
    with transaction() as cur:
        cur.execute(SHIPMENTS_QUERY + " AND s.id = %s", (str(user.tenant_id), str(shipment_id)))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Shipment not found")
    return row
