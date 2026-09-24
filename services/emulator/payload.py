"""Pembentukan payload telemetri `krio.telemetry.v1` (PRD §9.2).

Kontrak payload emulator sengaja dibuat identik dengan firmware nyata, sehingga
perangkat fisik dapat menggantikan emulator tanpa mengubah backend.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

SCHEMA = "krio.telemetry.v1"
MAX_PAYLOAD_BYTES = 512  # satu kuota pesan IoT Hub (PRD §9.2)
LINK_TYPES = ("lora", "cellular")


@dataclass
class DeviceConfig:
    """Identitas dan jalur komunikasi satu perangkat."""

    device_id: str
    link: str = "cellular"
    lat: float | None = None
    lon: float | None = None

    def __post_init__(self) -> None:
        if self.link not in LINK_TYPES:
            raise ValueError(f"link harus salah satu dari {LINK_TYPES}, bukan {self.link!r}")


def build_payload(
    device: DeviceConfig,
    ts: datetime,
    seq: int,
    temp_c: float,
    rh_pct: float | None = None,
    batt_v: float | None = None,
    rssi: int | None = None,
    buffered: bool = False,
) -> dict:
    """Menyusun satu pesan telemetri sesuai skema `krio.telemetry.v1`.

    GPS selalu ``null`` pada jalur LoRa: perangkat LoRa bersifat statis dan tidak
    membawa modul GPS (PRD §8.3).
    """
    gps = None
    if device.link == "cellular" and device.lat is not None and device.lon is not None:
        gps = {"lat": round(device.lat, 4), "lon": round(device.lon, 4)}

    payload = {
        "schema": SCHEMA,
        "device_id": device.device_id,
        "ts": ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "link": device.link,
        "seq": seq,
        "temp_c": round(temp_c, 2),
        "rh_pct": None if rh_pct is None else round(rh_pct, 1),
        "batt_v": None if batt_v is None else round(batt_v, 2),
        "rssi": rssi,
        "gps": gps,
        "buffered": buffered,
    }
    return {k: v for k, v in payload.items() if v is not None or k in ("gps",)}


def encode(payload: dict) -> bytes:
    """Menyandikan payload menjadi JSON dan menegakkan batas ukuran pesan."""
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise ValueError(
            f"payload {len(raw)} byte melebihi batas {MAX_PAYLOAD_BYTES} byte (PRD §9.2)"
        )
    return raw
