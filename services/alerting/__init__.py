"""Lapisan peringatan KRIO — ambang suhu (#48), perangkat offline (#49),
dan anomali residual + CUSUM (#62)."""

from .repository import AlertRepository, DeviceReading, DeviceStatus
from .residual import CalibrationParams, ResidualEvent, detect_events, estimate_sigma, update_cusum
from .rules import (
    KIND_DOOR_OPEN,
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
    "AlertDraft", "AlertRepository", "CalibrationParams", "DeviceReading",
    "DeviceStatus", "ResidualEvent", "ScanResult", "ThresholdRange",
    "KIND_DOOR_OPEN", "KIND_OFFLINE", "KIND_THRESHOLD", "OFFLINE_AFTER",
    "OFFLINE_COOLDOWN", "THRESHOLD_COOLDOWN", "detect_events", "estimate_sigma",
    "evaluate_offline", "evaluate_threshold", "scan", "severity_for", "update_cusum",
]
