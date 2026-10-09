"""Aturan peringatan KRIO: pelanggaran ambang suhu dan perangkat offline.

Modul ini murni komputasi, tanpa akses basis data maupun Azure, sehingga dapat
dipanggil dari fn_ingest (PRD §7) dan diuji lokal. Lapisan basis data berada di
``repository.py``.

Jenis peringatan mengikuti kolom ``alerts.kind`` pada skema basis data:

- ``KEGAGALAN_PENDINGIN`` — suhu terukur sudah keluar dari rentang produk;
- ``DEVICE_OFFLINE``      — perangkat berhenti mengirim telemetri.

``PREDICTED_EXCURSION`` sengaja tidak dipakai di sini: jenis itu untuk peringatan
berbasis prediksi suhu (F2, issue #61), bukan untuk pelanggaran yang sudah terjadi.

``PINTU_DIBUKA`` (lihat ``residual.py``, issue #62/F4) memakai deteksi anomali
residual + CUSUM untuk membedakan simpangan singkat (pintu dibuka, info) dari
simpangan berkepanjangan yang juga terklasifikasi ``KEGAGALAN_PENDINGIN`` lewat
jalur yang berbeda dari ``evaluate_threshold`` di atas — konstanta ``KIND_DOOR_OPEN``
didefinisikan di sini supaya satu-satunya sumber kebenaran nama ``kind`` tetap
di modul ini, sesuai kolom ``alerts.kind``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

KIND_THRESHOLD = "KEGAGALAN_PENDINGIN"
KIND_OFFLINE = "DEVICE_OFFLINE"
KIND_DOOR_OPEN = "PINTU_DIBUKA"

# Ambang keparahan, dinyatakan sebagai simpangan dari batas produk (°C).
SEVERITY_CRITICAL_C = 5.0

# Jendela peredaman agar satu kejadian tidak membanjiri pengguna (PRD §6, F2).
THRESHOLD_COOLDOWN = timedelta(minutes=30)
OFFLINE_COOLDOWN = timedelta(hours=1)

# Perangkat dianggap offline bila tidak ada telemetri selama jangka ini.
OFFLINE_AFTER = timedelta(minutes=10)


@dataclass(frozen=True)
class ThresholdRange:
    """Rentang suhu aman satu produk (kolom tabel ``products``)."""

    temp_min_c: float
    temp_max_c: float

    def __post_init__(self) -> None:
        if self.temp_min_c >= self.temp_max_c:
            raise ValueError("temp_min_c harus lebih kecil daripada temp_max_c")

    @classmethod
    def from_product(cls, row: dict) -> "ThresholdRange":
        return cls(float(row["temp_min_c"]), float(row["temp_max_c"]))

    def deviation_c(self, temp_c: float) -> float:
        """Simpangan di luar rentang; 0 bila suhu masih aman."""
        if temp_c > self.temp_max_c:
            return temp_c - self.temp_max_c
        if temp_c < self.temp_min_c:
            return self.temp_min_c - temp_c
        return 0.0


@dataclass(frozen=True)
class AlertDraft:
    """Peringatan yang siap disimpan ke tabel ``alerts``."""

    kind: str
    severity: str
    raised_at: datetime
    message: str


def severity_for(deviation_c: float) -> str:
    """Keparahan berdasarkan besar simpangan dari batas produk (issue #48).

    Simpangan sampai 5 °C -> warning; di atas 5 °C -> critical.
    """
    return "critical" if deviation_c > SEVERITY_CRITICAL_C else "warning"


def evaluate_threshold(
    temp_c: float,
    ts: datetime,
    thresholds: ThresholdRange,
    device_label: str,
    last_alert_at: datetime | None = None,
) -> AlertDraft | None:
    """Menilai satu pembacaan terhadap rentang produk.

    Mengembalikan ``None`` bila suhu masih aman, atau bila peringatan sejenis
    untuk perangkat yang sama sudah terbit dalam 30 menit terakhir.
    """
    deviation = thresholds.deviation_c(temp_c)
    if deviation == 0.0:
        return None
    if last_alert_at is not None and ts - last_alert_at < THRESHOLD_COOLDOWN:
        return None

    arah = "di atas" if temp_c > thresholds.temp_max_c else "di bawah"
    batas = thresholds.temp_max_c if temp_c > thresholds.temp_max_c else thresholds.temp_min_c
    return AlertDraft(
        kind=KIND_THRESHOLD,
        severity=severity_for(deviation),
        raised_at=ts,
        message=(
            f"{device_label}: suhu {temp_c:.2f} °C, {deviation:.2f} °C {arah} "
            f"batas produk {batas:.2f} °C"
        ),
    )


def evaluate_offline(
    last_seen_at: datetime | None,
    now: datetime,
    device_label: str,
    last_alert_at: datetime | None = None,
) -> AlertDraft | None:
    """Menilai satu perangkat terhadap batas diam 10 menit.

    Mengembalikan ``None`` bila perangkat masih mengirim, bila perangkat belum
    pernah mengirim sama sekali (``last_seen_at`` kosong, bukan kehilangan
    kontak), atau bila peringatan sejenis sudah terbit dalam 1 jam terakhir.
    """
    if last_seen_at is None:
        return None
    diam = now - last_seen_at
    if diam < OFFLINE_AFTER:
        return None
    if last_alert_at is not None and now - last_alert_at < OFFLINE_COOLDOWN:
        return None

    menit = int(diam.total_seconds() // 60)
    return AlertDraft(
        kind=KIND_OFFLINE,
        severity="warning",
        raised_at=now,
        message=f"{device_label}: tidak mengirim telemetri selama {menit} menit",
    )
