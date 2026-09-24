"""Menjalankan simulasi satu armada boks pendingin."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .payload import DeviceConfig, build_payload, encode
from .sinks import Sink
from .thermal import BoxThermalModel, ThermalParams

# Interval sampling default mengikuti PRD §8.4.
INTERVAL_BY_LINK = {"cellular": 300, "lora": 600}


@dataclass
class Device:
    """Satu perangkat tersimulasi beserta model termal dan penghitungnya."""

    config: DeviceConfig
    model: BoxThermalModel
    interval_s: int
    seq: int = 0
    batt_v: float = 4.10
    sent: int = 0
    skipped_offline: int = 0
    _next_send_s: float = 0.0

    def sample(self, t_s: float, started_at: datetime, offline_seconds: float) -> dict | None:
        """Mengembalikan payload bila perangkat harus mengirim pada detik ``t_s``."""
        if t_s < self._next_send_s:
            return None
        self._next_send_s = t_s + self.interval_s

        true_temp = self.model.state.temp_c
        if not self.model.is_transmitting(t_s, offline_seconds):
            self.skipped_offline += 1
            return None

        self.seq += 1
        self.sent += 1
        self.batt_v = max(3.30, self.batt_v - 0.0004)
        rng = self.model.rng
        return build_payload(
            device=self.config,
            ts=started_at + timedelta(seconds=t_s),
            seq=self.seq,
            temp_c=self.model.measure(true_temp),
            rh_pct=min(99.0, max(40.0, 75.0 + rng.gauss(0, 3))),
            batt_v=self.batt_v,
            rssi=int(rng.gauss(-82, 6)),
        )


@dataclass
class Simulation:
    """Menjalankan seluruh perangkat pada satu garis waktu tersimulasi.

    ``speed`` mempercepat waktu simulasi terhadap waktu nyata: ``speed=1``
    berjalan real-time, sedangkan ``speed=0`` menjalankan secepat mungkin
    (dipakai untuk pengujian dan demo).
    """

    devices: list[Device]
    sink: Sink
    duration_s: float
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tick_s: float = 30.0
    speed: float = 0.0
    offline_seconds: float = 1_800.0

    def run(self) -> dict:
        t = 0.0
        oversize = 0
        while t <= self.duration_s:
            for device in self.devices:
                device.model.step(t, self.tick_s)
                payload = device.sample(t, self.started_at, self.offline_seconds)
                if payload is None:
                    continue
                try:
                    encode(payload)  # menegakkan batas 512 byte
                except ValueError:
                    oversize += 1
                    continue
                self.sink.send(payload)
            t += self.tick_s
            if self.speed > 0:
                time.sleep(self.tick_s / self.speed)

        return {
            "durasi_simulasi_menit": round(self.duration_s / 60),
            "pesan_terkirim": sum(d.sent for d in self.devices),
            "pesan_dilewati_offline": sum(d.skipped_offline for d in self.devices),
            "payload_melebihi_batas": oversize,
            "suhu_akhir_c": {d.config.device_id: round(d.model.state.temp_c, 2) for d in self.devices},
        }


def build_fleet(
    specs: list[tuple[str, str]],
    mode: str,
    seed: int,
    interval_s: int | None = None,
    setpoint_c: float = 2.0,
    event_start_s: float = 600.0,
) -> list[Device]:
    """Membuat daftar perangkat dari pasangan ``(device_id, link)``."""
    devices = []
    for index, (device_id, link) in enumerate(specs):
        rng = random.Random(seed + index)
        config = DeviceConfig(
            device_id=device_id,
            link=link,
            lat=-7.7956 + rng.uniform(-0.05, 0.05) if link == "cellular" else None,
            lon=110.3695 + rng.uniform(-0.05, 0.05) if link == "cellular" else None,
        )
        devices.append(
            Device(
                config=config,
                model=BoxThermalModel(
                    mode=mode,
                    params=ThermalParams(setpoint_c=setpoint_c),
                    event_start_s=event_start_s,
                    rng=rng,
                ),
                interval_s=interval_s or INTERVAL_BY_LINK[link],
            )
        )
    return devices
