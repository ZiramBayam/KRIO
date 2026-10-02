"""Pemindaian peringatan: ambang suhu (#48) dan perangkat offline (#49).

Satu pemindaian memeriksa seluruh pengiriman aktif, lalu menulis peringatan baru
yang lolos peredaman. Fungsi di sini menjadi isi ``fn_alerting`` ketika Azure
Functions aktif (issue #26); pemisahan ini membuat logikanya dapat dijalankan dan
diuji tanpa Azure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .repository import AlertRepository
from .rules import KIND_OFFLINE, KIND_THRESHOLD, evaluate_offline, evaluate_threshold


@dataclass
class ScanResult:
    """Ringkasan satu pemindaian."""

    threshold_alerts: int = 0
    offline_alerts: int = 0
    resolved_offline: int = 0
    devices_checked: int = 0
    messages: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "perangkat_diperiksa": self.devices_checked,
            "peringatan_ambang_suhu": self.threshold_alerts,
            "peringatan_perangkat_offline": self.offline_alerts,
            "peringatan_offline_ditutup": self.resolved_offline,
            "pesan": self.messages,
        }


def scan_thresholds(repo: AlertRepository, result: ScanResult) -> None:
    """Membandingkan pembacaan terbaru tiap perangkat dengan ambang produknya."""
    for reading in repo.latest_readings():
        result.devices_checked += 1
        last_alert = repo.last_alert_at(reading.tenant_id, reading.device_id, KIND_THRESHOLD)
        draft = evaluate_threshold(
            temp_c=reading.temp_c,
            ts=reading.ts,
            thresholds=reading.thresholds,
            device_label=reading.device_label,
            last_alert_at=last_alert,
        )
        if draft is None:
            continue
        repo.insert_alert(reading.tenant_id, reading.device_id, reading.shipment_id, draft)
        result.threshold_alerts += 1
        result.messages.append(f"[{draft.severity}] {draft.message}")


def scan_offline(repo: AlertRepository, result: ScanResult, now: datetime) -> None:
    """Mencari perangkat dengan pengiriman aktif yang berhenti mengirim."""
    for device in repo.active_devices():
        last_alert = repo.last_alert_at(device.tenant_id, device.device_id, KIND_OFFLINE)
        draft = evaluate_offline(
            last_seen_at=device.last_seen_at,
            now=now,
            device_label=device.device_label,
            last_alert_at=last_alert,
        )
        if draft is None:
            continue
        repo.insert_alert(device.tenant_id, device.device_id, device.shipment_id, draft)
        result.offline_alerts += 1
        result.messages.append(f"[{draft.severity}] {draft.message}")


def scan(conn, now: datetime | None = None) -> ScanResult:
    """Menjalankan seluruh pemeriksaan peringatan satu kali."""
    now = now or datetime.now(timezone.utc)
    repo = AlertRepository(conn)
    result = ScanResult()
    result.resolved_offline = repo.resolve_recovered_offline()
    scan_thresholds(repo, result)
    scan_offline(repo, result, now)
    return result
