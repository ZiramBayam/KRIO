"""Validate and store telemetry from a registered device."""

import hmac
from datetime import timedelta
import os
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.security import APIKeyHeader
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, field_validator

from services.emulator.device_keys import device_key
from services.emulator.payload import MAX_PAYLOAD_BYTES, SCHEMA

from .db import transaction

router = APIRouter()
header = APIKeyHeader(name="X-Device-Key", auto_error=False)


class Coordinates(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    lat: float = Field(ge=-90, le=90, strict=True)
    lon: float = Field(ge=-180, le=180, strict=True)


class Telemetry(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: Literal[SCHEMA] = Field(alias="schema")
    device_id: str = Field(min_length=1, max_length=100)
    ts: AwareDatetime
    link: Literal["cellular", "lora"]
    seq: int = Field(strict=True, ge=0, le=2**63 - 1)
    temp_c: float = Field(strict=True, ge=-273.15, le=1000)
    rh_pct: float | None = Field(default=None, strict=True, ge=0, le=100)
    batt_v: float | None = Field(default=None, strict=True, ge=0, le=100)
    rssi: int | None = Field(default=None, strict=True, ge=-32768, le=32767)
    gps: Coordinates | None = None
    buffered: bool = Field(strict=True)

    @field_validator("ts", mode="before")
    @classmethod
    def timestamp_is_text(cls, value):
        if not isinstance(value, str) or "T" not in value:
            raise ValueError("Expected an ISO 8601 timestamp")
        return value

    @field_validator("ts")
    @classmethod
    def timestamp_is_utc(cls, value):
        if value.utcoffset() != timedelta(0):
            raise ValueError("Expected a UTC timestamp")
        return value


def store_reading(data: Telemetry) -> bool:
    with transaction() as cur:
        cur.execute(
            "SELECT id, tenant_id, link_type FROM devices WHERE device_id = %s FOR UPDATE",
            (data.device_id,),
        )
        device = cur.fetchone()
        if not device:
            raise HTTPException(404, "Unknown device")
        if data.link != device["link_type"]:
            raise HTTPException(400, "Link does not match the registered device")
        cur.execute(
            """
            INSERT INTO readings
                (device_id, ts, shipment_id, seq, temp_c, rh_pct, batt_v, rssi, lat, lon, buffered)
            VALUES (%s, %s, (
                SELECT id FROM shipments
                WHERE tenant_id = %s AND device_id = %s AND started_at <= %s
                    AND (ended_at >= %s OR status = 'active')
                ORDER BY started_at DESC LIMIT 1
            ), %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (device_id, ts) DO NOTHING
            """,
            (
                device["id"], data.ts, device["tenant_id"], device["id"], data.ts, data.ts,
                data.seq, data.temp_c, data.rh_pct, data.batt_v, data.rssi,
                data.gps.lat if data.gps else None, data.gps.lon if data.gps else None, data.buffered,
            ),
        )
        inserted = cur.rowcount == 1
        if inserted:
            cur.execute(
                "UPDATE devices SET last_seen_at = greatest(last_seen_at, %s) WHERE id = %s",
                (data.ts, device["id"]),
            )
        return inserted


class IngestResult(BaseModel):
    inserted: bool


@router.post(
    "/ingest",
    status_code=201,
    responses={200: {"model": IngestResult}, 400: {"description": "Invalid telemetry"}},
    openapi_extra={"requestBody": {"required": True, "content": {
        "application/json": {"schema": {"$ref": "#/components/schemas/Telemetry"}}
    }}},
)
async def ingest(
    request: Request, response: Response, key: Annotated[str | None, Depends(header)]
) -> IngestResult:
    if not key:
        raise HTTPException(401, "Missing device key")
    payload = bytearray()
    async for chunk in request.stream():
        if len(payload) + len(chunk) >= MAX_PAYLOAD_BYTES:
            raise HTTPException(400, "Telemetry must be less than 512 bytes")
        payload.extend(chunk)
    try:
        data = Telemetry.model_validate_json(payload)
    except ValidationError as exc:
        errors = [
            {"field": ".".join(map(str, error["loc"])), "message": error["msg"]}
            for error in exc.errors(include_input=False, include_url=False, include_context=False)
        ]
        raise HTTPException(400, errors) from None
    if data.link == "lora" and data.gps is not None:
        raise HTTPException(400, "LoRa telemetry cannot carry GPS coordinates")
    expected = device_key(os.environ["KRIO_DEVICE_SECRET"], data.device_id)
    if not hmac.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(401, "Invalid device key")
    inserted = await run_in_threadpool(store_reading, data)
    if not inserted:
        response.status_code = 200
    return IngestResult(inserted=inserted)
