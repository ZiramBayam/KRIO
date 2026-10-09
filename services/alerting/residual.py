"""Deteksi anomali residual + CUSUM (issue #62, F4, PRD §6 & §12.3).

Membedakan dua penyebab simpangan suhu dari prediksi:

- ``PINTU_DIBUKA``       — simpangan singkat (< 15 menit) yang kembali ke kurva normal.
- ``KEGAGALAN_PENDINGIN``— simpangan berkepanjangan (>= 20 menit) dengan CUSUM naik,
                           menandakan tren memburuk yang terus-menerus, bukan sekali lonjak.

Modul ini murni komputasi (tanpa akses basis data/Azure), mengikuti pola
``services/alerting/rules.py`` dan ``services/shelflife/kinetics.py``: dipanggil
dari ``fn_alerting`` nanti, diuji lokal sekarang. ``evaluate_threshold`` di
``rules.py`` TIDAK digantikan oleh modul ini — keduanya berjalan berdampingan;
lihat README untuk pembagian tanggung jawab.

## Keputusan desain yang perlu diketahui pembaca/reviewer

1. **Sumber T_prediksi(t).** AC issue #62 mengasumsikan model forecast (LightGBM,
   issue #58) sudah tersedia. Karena #58 belum dikerjakan, modul ini menerima
   residual yang SUDAH dihitung (``r(t)``) dari pemanggil, bukan menghitungnya
   sendiri dari T_terukur dan T_prediksi mentah — supaya begitu #58/#60 selesai
   dan tabel ``forecasts`` terisi, pemanggil tinggal mengganti sumber prediksi
   tanpa menyentuh modul ini. Untuk kalibrasi saat ini (lihat ``ml/calibration/``),
   T_prediksi dihasilkan dari baseline persistence sederhana sebagai pengganti
   sementara — bukan model forecast sungguhan.
2. **Real-time vs retrospektif.** AC menuliskan dua kondisi klasifikasi yang
   secara implisit punya titik waktu keputusan berbeda:
   - ``PINTU_DIBUKA`` baru bisa dipastikan SETELAH suhu kembali normal dalam
     < 15 menit (keputusan retrospektif terhadap episode yang sudah berakhir).
   - ``KEGAGALAN_PENDINGIN`` tidak boleh menunggu episode berakhir — begitu
     durasi simpangan mencapai >= 20 menit dan CUSUM masih naik, peringatan
     critical harus terbit SAAT ITU JUGA, bukan menunggu pendingin pulih
     sendiri (yang mungkin tidak pernah terjadi). ``detect_events`` meniru
     perilaku ini: satu event ``KEGAGALAN_PENDINGIN`` dipancarkan tepat saat
     ambang 20 menit terlampaui, lalu episode yang sama tidak memancarkan
     event kedua kalinya (lihat ``_EXCURSION_ALREADY_ESCALATED``).
3. **Arah CUSUM.** CUSUM di sini hanya mengakumulasi simpangan POSITIF
   (``r(t) > 0`` = lebih panas dari prediksi = indikasi kegagalan pendingin),
   sesuai rumus AC ``S(t) = max(0, S(t-1) + r(t) - k)`` diterapkan apa adanya
   pada ``r(t)`` bertanda, bukan ``|r(t)|``. Pembacaan ``r(t) < 0`` (lebih
   dingin dari prediksi) menurunkan CUSUM tapi tetap bisa memicu ``PINTU_DIBUKA``
   lewat kondisi ``|r(t)| > 3sigma`` bila berdurasi singkat (mis. sensor
   terpapar udara luar yang lebih dingin saat pintu dibuka musim dingin).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence

from .rules import KIND_DOOR_OPEN, KIND_THRESHOLD

Reading = tuple[datetime, float]  # (ts, residual_c)


@dataclass(frozen=True)
class CalibrationParams:
    """Ambang hasil kalibrasi pada Dataset B (lihat ml/calibration/)."""

    sigma_c: float
    cusum_k: float
    excursion_sigma_multiplier: float = 3.0
    door_open_max_minutes: float = 15.0
    cooling_failure_min_minutes: float = 20.0

    def __post_init__(self) -> None:
        if self.sigma_c <= 0:
            raise ValueError("sigma_c harus positif")
        if self.cusum_k < 0:
            raise ValueError("cusum_k tidak boleh negatif")
        if self.door_open_max_minutes <= 0 or self.cooling_failure_min_minutes <= 0:
            raise ValueError("ambang durasi harus positif")
        if self.door_open_max_minutes > self.cooling_failure_min_minutes:
            raise ValueError(
                "door_open_max_minutes tidak boleh melebihi cooling_failure_min_minutes "
                "(AC: < 15 menit vs >= 20 menit — ada zona abu-abu 15-20 menit yang "
                "sengaja tidak diklasifikasikan, lihat README)"
            )

    @property
    def excursion_threshold_c(self) -> float:
        return self.excursion_sigma_multiplier * self.sigma_c


@dataclass(frozen=True)
class ResidualEvent:
    """Satu kejadian terdeteksi, siap dipetakan ke baris tabel ``alerts``."""

    kind: str  # KIND_DOOR_OPEN atau KIND_THRESHOLD
    severity: str  # "info" atau "critical"
    started_at: datetime
    detected_at: datetime
    """Waktu event ini SEHARUSNYA dipancarkan sebagai alert (lihat catatan desain #2)."""
    ended_at: datetime | None
    """None bila masih berlangsung saat deteksi (KEGAGALAN_PENDINGIN real-time)."""
    duration_minutes: float
    peak_residual_c: float
    cusum_at_detection: float


def estimate_sigma(residuals: Sequence[float]) -> float:
    """Simpangan baku sampel dari residual pada set validasi (bukan data anomali).

    AC #62 secara eksplisit minta sigma diestimasi dari "set validasi", bukan
    seluruh data — kalau dihitung dari seluruh data (termasuk window anomali
    berlabel), sigma akan terlalu besar dan ambang 3-sigma jadi tidak sensitif.
    Pemanggil bertanggung jawab menyaring data anomali sebelum memanggil ini
    (lihat ``ml/calibration/dataset_b_baseline.py::validation_residuals``).
    """
    n = len(residuals)
    if n < 2:
        raise ValueError("minimal 2 nilai residual diperlukan untuk estimasi sigma")
    mean = sum(residuals) / n
    variance = sum((r - mean) ** 2 for r in residuals) / (n - 1)
    return variance**0.5


def update_cusum(prev_s: float, residual_c: float, k: float) -> float:
    """S(t) = max(0, S(t-1) + r(t) - k), persis rumus AC #62."""
    return max(0.0, prev_s + residual_c - k)


def _classify_completed_excursion(
    duration_minutes: float,
    started_at: datetime,
    ended_at: datetime,
    peak_residual_c: float,
    cusum_at_end: float,
    params: CalibrationParams,
) -> ResidualEvent | None:
    """Klasifikasi retrospektif untuk episode yang SUDAH kembali normal.

    Hanya dipakai untuk kasus PINTU_DIBUKA (episode pendek). Episode panjang
    sudah dipancarkan sebagai KEGAGALAN_PENDINGIN secara real-time sebelum
    episode ini berakhir, jadi tidak diklasifikasi ulang di sini.
    """
    if duration_minutes < params.door_open_max_minutes:
        return ResidualEvent(
            kind=KIND_DOOR_OPEN,
            severity="info",
            started_at=started_at,
            detected_at=ended_at,
            ended_at=ended_at,
            duration_minutes=duration_minutes,
            peak_residual_c=peak_residual_c,
            cusum_at_detection=cusum_at_end,
        )
    # Zona 15-20 menit yang kembali normal sebelum mencapai ambang kegagalan:
    # sengaja tidak diberi label (bukan PINTU_DIBUKA karena sudah >= 15 menit,
    # bukan KEGAGALAN_PENDINGIN karena tidak pernah mencapai 20 menit). Lihat
    # README bagian "Zona abu-abu" untuk rasionalnya.
    return None


def detect_events(
    readings: Iterable[Reading],
    params: CalibrationParams,
) -> list[ResidualEvent]:
    """Jalankan state machine deteksi atas satu seri residual (ts, r(t)) terurut waktu.

    Catatan: ``readings`` adalah residual yang SUDAH dihitung oleh pemanggil
    (lihat dokumentasi modul, poin 1) — fungsi ini tidak tahu dan tidak perlu
    tahu dari mana T_prediksi berasal.
    """
    ordered = sorted(readings, key=lambda row: row[0])
    threshold = params.excursion_threshold_c

    events: list[ResidualEvent] = []
    cusum = 0.0
    in_excursion = False
    excursion_start: datetime | None = None
    excursion_values: list[float] = []
    escalated_this_excursion = False

    for ts, r in ordered:
        cusum = update_cusum(cusum, r, params.cusum_k)
        is_excursion_point = abs(r) > threshold

        if is_excursion_point:
            if not in_excursion:
                in_excursion = True
                excursion_start = ts
                excursion_values = []
                escalated_this_excursion = False
            excursion_values.append(r)

            duration_minutes = (ts - excursion_start).total_seconds() / 60.0
            is_rising = r > threshold  # arah positif = makin panas = berpotensi gagal
            if (
                not escalated_this_excursion
                and duration_minutes >= params.cooling_failure_min_minutes
                and is_rising
                and cusum > 0.0
            ):
                events.append(
                    ResidualEvent(
                        kind=KIND_THRESHOLD,
                        severity="critical",
                        started_at=excursion_start,
                        detected_at=ts,
                        ended_at=None,
                        duration_minutes=duration_minutes,
                        peak_residual_c=max(excursion_values, key=abs),
                        cusum_at_detection=cusum,
                    )
                )
                escalated_this_excursion = True
        else:
            if in_excursion:
                duration_minutes = (ts - excursion_start).total_seconds() / 60.0
                if not escalated_this_excursion:
                    event = _classify_completed_excursion(
                        duration_minutes=duration_minutes,
                        started_at=excursion_start,
                        ended_at=ts,
                        peak_residual_c=max(excursion_values, key=abs),
                        cusum_at_end=cusum,
                        params=params,
                    )
                    if event is not None:
                        events.append(event)
                in_excursion = False
                excursion_start = None
                excursion_values = []
                escalated_this_excursion = False

    return events
