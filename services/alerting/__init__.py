"""Lapisan peringatan KRIO — ambang suhu (#48) dan perangkat offline (#49)."""

from .repository import AlertRepository, DeviceReading, DeviceStatus
from .rules import (
    KIND_OFFLINE,
    KIND_THRESHOLD,
    OFFLINE_AFTER,
    OFFLINE_COOLDOWN,
    THRESHOLD_COOLDOWN,
    AlertDraft,
    ThresholdRange,
    evaluate_offline,
    evaluate_threshold,
    severity_for,
)
from .scanner import ScanResult, scan

__all__ = [
    "AlertDraft", "AlertRepository", "DeviceReading", "DeviceStatus", "ScanResult",
    "ThresholdRange", "KIND_OFFLINE", "KIND_THRESHOLD", "OFFLINE_AFTER",
    "OFFLINE_COOLDOWN", "THRESHOLD_COOLDOWN", "evaluate_offline", "evaluate_threshold",
    "scan", "severity_for",
]
