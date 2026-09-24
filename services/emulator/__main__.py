"""CLI Device Emulator KRIO.

Contoh:

    # tiga armada default, mode normal, 6 jam simulasi, keluaran JSON Lines
    python -m emulator --duration 6h

    # satu perangkat, kegagalan pendingin setelah 10 menit
    python -m emulator --devices KRIO-0001:cellular --mode excursion --duration 1h

    # menulis langsung ke PostgreSQL lokal
    DATABASE_URL=postgresql://localhost/krio_dev python -m emulator --sink postgres
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from .fleet import Simulation, build_fleet
from .sinks import PipeClosed, make_sink
from .thermal import MODES

DEFAULT_FLEET = "KRIO-0001:cellular,KRIO-0002:cellular,KRIO-0003:lora"
DURATION_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration(value: str) -> float:
    """Menerima '90s', '30m', '6h', '1d', atau angka polos (detik)."""
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([smhd]?)", value.strip().lower())
    if not match:
        raise argparse.ArgumentTypeError(f"durasi tidak valid: {value!r}; contoh: 30m, 6h")
    return float(match.group(1)) * DURATION_UNITS[match.group(2) or "s"]


def parse_devices(value: str) -> list[tuple[str, str]]:
    """Menerima 'KRIO-0001:cellular,KRIO-0003:lora'."""
    specs = []
    for item in value.split(","):
        device_id, _, link = item.strip().partition(":")
        if not device_id:
            raise argparse.ArgumentTypeError(f"device_id kosong pada {item!r}")
        specs.append((device_id, link or "cellular"))
    return specs


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="emulator", description="Device Emulator KRIO (PRD §8.6)")
    p.add_argument("--devices", type=parse_devices, default=parse_devices(DEFAULT_FLEET),
                   help=f"daftar perangkat 'id:link' dipisah koma (default: {DEFAULT_FLEET})")
    p.add_argument("--device-id", help="jalan pintas untuk satu perangkat saja")
    p.add_argument("--link", choices=("cellular", "lora"), default="cellular",
                   help="jalur untuk --device-id (default: cellular)")
    p.add_argument("--mode", choices=MODES, default="normal", help="skenario simulasi (default: normal)")
    p.add_argument("--interval", type=int, default=None,
                   help="interval kirim dalam detik (default: 300 seluler, 600 LoRa — PRD §8.4)")
    p.add_argument("--duration", type=parse_duration, default="6h", help="durasi simulasi (default: 6h)")
    p.add_argument("--speed", type=float, default=0.0,
                   help="0 = secepat mungkin (default), 1 = real-time, 60 = 1 menit simulasi per detik")
    p.add_argument("--event-start", type=parse_duration, default="10m",
                   help="kapan kejadian mode dimulai (default: 10m)")
    p.add_argument("--offline-duration", type=parse_duration, default="30m",
                   help="lama perangkat berhenti mengirim pada --mode offline (default: 30m)")
    p.add_argument("--setpoint", type=float, default=2.0, help="setpoint pendingin dalam °C (default: 2.0)")
    p.add_argument("--sink", choices=("stdout", "postgres"), default="stdout",
                   help="tujuan pengiriman (default: stdout)")
    p.add_argument("--dsn", default=os.getenv("DATABASE_URL"), help="DSN PostgreSQL untuk --sink postgres")
    p.add_argument("--seed", type=int, default=42, help="seed acak agar simulasi dapat diulang (default: 42)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    specs = [(args.device_id, args.link)] if args.device_id else args.devices

    devices = build_fleet(
        specs=specs,
        mode=args.mode,
        seed=args.seed,
        interval_s=args.interval,
        setpoint_c=args.setpoint,
        event_start_s=args.event_start,
    )
    sink = make_sink(args.sink, args.dsn)
    simulation = Simulation(
        devices=devices,
        sink=sink,
        duration_s=args.duration,
        speed=args.speed,
        offline_seconds=args.offline_duration,
    )

    try:
        summary = simulation.run()
    except KeyboardInterrupt:
        print("dihentikan pengguna", file=sys.stderr)
        return 130
    except PipeClosed:
        # Wajar ketika keluaran disalurkan ke `head`; berhenti tanpa jejak galat.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0
    finally:
        rejected = getattr(sink, "rejected", 0)
        sink.close()

    summary["mode"] = args.mode
    summary["perangkat"] = [d.config.device_id for d in devices]
    if rejected:
        summary["pesan_ditolak_device_tidak_terdaftar"] = rejected
    print(json.dumps(summary, ensure_ascii=False, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
