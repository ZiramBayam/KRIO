"""Run emulator scenarios from the dashboard (issue #110).

A simulation drives the existing emulator engine for one demo device in a
background thread. Telemetry goes through ``POST /api/ingest`` like a real
device, with real wall-clock timestamps. Simulated time runs ``SPEED`` times
faster than real time; while a run is active, device status and the offline
alert rule shorten their silence threshold by the same factor, so the chart,
device status and alerts stay consistent without waiting 10 to 20 real minutes.
"""

from __future__ import annotations

import os
import random
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.emulator.fleet import build_fleet
from services.emulator.sinks import HttpSink, Sink

from .auth import Authenticated, Writer
from .db import transaction

router = APIRouter(prefix="/simulation")

SPEED = 20.0          # simulated seconds per real second
TICK_S = 30.0         # simulated seconds per step
DURATION_S = 3600.0   # one simulated hour, about 3 real minutes
EVENT_START_S = 600.0
OFFLINE_S = 1500.0

Mode = Literal["normal", "excursion", "door-open", "offline"]
State = Literal["running", "finished", "stopped", "failed"]

EVENT_TEXT = {
    "excursion": "Pendingin berhenti bekerja",
    "door-open": "Pintu boks dibuka selama 5 menit",
    "offline": "Perangkat berhenti mengirim data",
}


def ingest_sink() -> Sink:
    return HttpSink(
        os.getenv("KRIO_INGEST_URL", "http://127.0.0.1:8000/api/ingest"),
        os.environ["KRIO_DEVICE_SECRET"],
    )


# Replaced in tests so telemetry can go through the in-process test client.
make_sink: Callable[[], Sink] = ingest_sink


class Event(BaseModel):
    sim_s: float
    at: datetime
    text: str


class Simulation(BaseModel):
    id: UUID
    device_id: UUID
    device_code: str
    device_label: str
    mode: Mode
    state: State
    speed: float
    duration_s: float
    sim_elapsed_s: float
    started_at: datetime
    ended_at: datetime | None
    sent: int
    error: str | None
    events: list[Event]


@dataclass
class Run:
    id: UUID
    tenant_id: str
    device_id: str
    device_code: str
    device_label: str
    link: str
    mode: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    state: str = "running"
    sim_elapsed_s: float = 0.0
    ended_at: datetime | None = None
    sent: int = 0
    error: str | None = None
    events: list[dict] = field(default_factory=list)
    stop: threading.Event = field(default_factory=threading.Event)

    def log(self, text: str) -> None:
        self.events.append({"sim_s": self.sim_elapsed_s, "at": datetime.now(timezone.utc), "text": text})

    def view(self) -> Simulation:
        return Simulation(
            id=self.id, device_id=UUID(self.device_id), device_code=self.device_code,
            device_label=self.device_label, mode=self.mode, state=self.state, speed=SPEED,
            duration_s=DURATION_S, sim_elapsed_s=self.sim_elapsed_s, started_at=self.started_at,
            ended_at=self.ended_at, sent=self.sent, error=self.error, events=list(self.events),
        )


_lock = threading.Lock()
_runs: dict[str, Run] = {}   # latest run per tenant


def time_scale(device_id: str) -> float:
    """Speed-up factor for a device: ``SPEED`` while it is being simulated, else 1."""
    with _lock:
        for run in _runs.values():
            if run.state == "running" and run.device_id == device_id:
                return SPEED
    return 1.0


def any_running() -> bool:
    with _lock:
        return any(run.state == "running" for run in _runs.values())


def phase(mode: str, t: float) -> str | None:
    """Name of the event active at simulated second ``t``, for the timeline."""
    if t < EVENT_START_S or mode == "normal":
        return None
    if mode == "excursion":
        return "event"
    if mode == "offline":
        return "event" if t < EVENT_START_S + OFFLINE_S else None
    since = t - EVENT_START_S
    return "event" if since % 1800 < 300 else None


def execute(run: Run, sink: Sink) -> None:
    device = build_fleet(
        specs=[(run.device_code, run.link)], mode=run.mode, seed=random.randrange(1 << 30),
        event_start_s=EVENT_START_S,
    )[0]
    t = 0.0
    previous = None
    try:
        while t <= DURATION_S and not run.stop.is_set():
            run.sim_elapsed_s = t
            current = phase(run.mode, t)
            if current != previous:
                if current:
                    run.log(EVENT_TEXT[run.mode])
                elif previous:
                    run.log("Perangkat kembali mengirim data" if run.mode == "offline"
                            else "Pintu ditutup dan suhu kembali turun")
                previous = current
            device.model.step(t, TICK_S)
            # Anchor the timeline so each payload carries the real current time.
            payload = device.sample(t, datetime.now(timezone.utc) - timedelta(seconds=t), OFFLINE_S)
            if payload is not None:
                sink.send(payload)
                run.sent += 1
            t += TICK_S
            run.stop.wait(TICK_S / SPEED)
        run.state = "stopped" if run.stop.is_set() else "finished"
        run.log("Simulasi dihentikan operator" if run.stop.is_set() else "Simulasi selesai")
    except Exception as exc:  # noqa: BLE001 - surface any failure to the operator
        run.state = "failed"
        run.error = str(exc) or exc.__class__.__name__
        run.log("Simulasi gagal")
    finally:
        run.ended_at = datetime.now(timezone.utc)
        sink.close()


class StartSimulation(BaseModel):
    device_id: UUID
    mode: Mode


@router.get("")
def current(user: Authenticated) -> Simulation | None:
    with _lock:
        run = _runs.get(str(user.tenant_id))
    return run.view() if run else None


@router.post("", status_code=201, responses={409: {"description": "A simulation is already running"}})
def start(form: StartSimulation, user: Writer) -> Simulation:
    with transaction() as cur:
        cur.execute(
            "SELECT id, device_id, label, link_type FROM devices WHERE id = %s AND tenant_id = %s",
            (str(form.device_id), str(user.tenant_id)),
        )
        device = cur.fetchone()
    if not device:
        raise HTTPException(404, "Device not found")
    tenant = str(user.tenant_id)
    with _lock:
        existing = _runs.get(tenant)
        if existing and existing.state == "running":
            raise HTTPException(409, "A simulation is already running")
        run = Run(
            id=UUID(int=random.getrandbits(128), version=4), tenant_id=tenant,
            device_id=str(device["id"]), device_code=device["device_id"],
            device_label=device["label"], link=device["link_type"], mode=form.mode,
        )
        run.log("Simulasi dimulai")
        _runs[tenant] = run
    try:
        sink = make_sink()
    except (KeyError, ValueError) as exc:
        run.state, run.error, run.ended_at = "failed", str(exc), datetime.now(timezone.utc)
        raise HTTPException(503, "Simulation sink is not configured") from None
    threading.Thread(target=execute, args=(run, sink), daemon=True, name=f"simulation-{run.id}").start()
    return run.view()


@router.post("/stop")
def stop(user: Writer) -> Simulation:
    with _lock:
        run = _runs.get(str(user.tenant_id))
    if not run or run.state != "running":
        raise HTTPException(409, "No simulation is running")
    run.stop.set()
    return run.view()
