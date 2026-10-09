"""EDA untuk Dataset B — NAB realKnownCause (issue #56, PRD §12.1).

Modul ini berisi fungsi murni (tanpa I/O plotting, tanpa side-effect selain
baca file) agar mudah diuji, mengikuti pola services/shelflife/kinetics.py:
logika dipisah dari skrip CLI (lihat ml/scripts/run_eda_dataset_b.py).

Catatan unit: nilai mentah NAB realKnownCause untuk kedua file ini
berada dalam derajat Fahrenheit (dikonfirmasi lewat rentang nilai —
~69-71°F untuk ambient, ~60-90°F untuk machine — bukan skala Celsius
yang masuk akal untuk suhu ruangan/mesin). PRD KRIO §13 memakai Celsius
di semua tempat, sehingga konversi dilakukan secara eksplisit di sini,
bukan diasumsikan diam-diam oleh pemanggil.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Sequence

import pandas as pd


class AnomalyWindow(NamedTuple):
    start: pd.Timestamp
    end: pd.Timestamp


@dataclass(frozen=True)
class ValidationReport:
    n_rows: int
    n_duplicate_timestamps: int
    is_monotonic: bool
    interval_minutes: float
    n_gaps: int
    """Jumlah selisih waktu berurutan yang > 1.5x interval median (indikasi data hilang)."""
    max_gap_minutes: float

    def is_clean(self) -> bool:
        return self.n_duplicate_timestamps == 0 and self.is_monotonic


@dataclass(frozen=True)
class SeriesSummary:
    n_rows: int
    min_f: float
    max_f: float
    mean_f: float
    std_f: float
    median_f: float
    min_c: float
    max_c: float
    mean_c: float
    std_c: float
    median_c: float
    start: pd.Timestamp
    end: pd.Timestamp


def fahrenheit_to_celsius(value_f: float) -> float:
    """Konversi °F ke °C. PRD §13 memakai Celsius untuk semua parameter kinetik."""
    return (value_f - 32.0) * 5.0 / 9.0


def load_nab_series(path: str | Path) -> pd.DataFrame:
    """Baca CSV NAB berformat `timestamp,value`, urutkan, dan hapus duplikat timestamp.

    NAB menyimpan satu baris per timestamp tanpa indeks; fungsi ini tidak
    melakukan resampling atau interpolasi — itu keputusan terpisah yang
    didokumentasikan saat data benar-benar dipakai untuk kalibrasi (#62).
    """
    df = pd.read_csv(path, parse_dates=["timestamp"])
    if "value" not in df.columns:
        raise ValueError(f"{path}: kolom 'value' tidak ditemukan, header = {list(df.columns)}")
    before = len(df)
    df = df.drop_duplicates(subset="timestamp", keep="first")
    df = df.sort_values("timestamp").reset_index(drop=True)
    df.attrs["n_duplicates_dropped"] = before - len(df)
    return df


def detect_sampling_interval_minutes(df: pd.DataFrame) -> float:
    """Median selisih antar-timestamp berurutan, dalam menit.

    Median dipakai (bukan mean) supaya tahan terhadap gap besar yang
    seharusnya dilaporkan lewat validate_series(), bukan mencemari estimasi
    interval nominal.
    """
    if len(df) < 2:
        raise ValueError("minimal 2 baris diperlukan untuk mendeteksi interval sampling")
    diffs = df["timestamp"].diff().dropna().dt.total_seconds() / 60.0
    return float(diffs.median())


def validate_series(df: pd.DataFrame) -> ValidationReport:
    """Cek kualitas data: duplikat, urutan waktu, dan gap (celah) sampling."""
    n_rows = len(df)
    n_dup = int(df.attrs.get("n_duplicates_dropped", 0))
    is_monotonic = bool(df["timestamp"].is_monotonic_increasing)
    interval = detect_sampling_interval_minutes(df)
    diffs_minutes = df["timestamp"].diff().dropna().dt.total_seconds() / 60.0
    gap_threshold = interval * 1.5
    gaps = diffs_minutes[diffs_minutes > gap_threshold]
    return ValidationReport(
        n_rows=n_rows,
        n_duplicate_timestamps=n_dup,
        is_monotonic=is_monotonic,
        interval_minutes=interval,
        n_gaps=int(len(gaps)),
        max_gap_minutes=float(gaps.max()) if len(gaps) else 0.0,
    )


def summarize_series(df: pd.DataFrame) -> SeriesSummary:
    """Statistik deskriptif dalam satuan asli (°F) dan hasil konversi (°C)."""
    values_f = df["value"]
    values_c = values_f.apply(fahrenheit_to_celsius)
    return SeriesSummary(
        n_rows=len(df),
        min_f=float(values_f.min()),
        max_f=float(values_f.max()),
        mean_f=float(values_f.mean()),
        std_f=float(values_f.std()),
        median_f=float(values_f.median()),
        min_c=float(values_c.min()),
        max_c=float(values_c.max()),
        mean_c=float(values_c.mean()),
        std_c=float(values_c.std()),
        median_c=float(values_c.median()),
        start=df["timestamp"].iloc[0],
        end=df["timestamp"].iloc[-1],
    )


def load_anomaly_windows(labels_path: str | Path, key: str) -> list[AnomalyWindow]:
    """Ambil window anomali berlabel dari labels/combined_windows.json milik NAB.

    `key` adalah path relatif NAB, mis. "realKnownCause/machine_temperature_system_failure.csv".
    """
    with open(labels_path, "r", encoding="utf-8") as f:
        all_windows: dict = json.load(f)
    if key not in all_windows:
        raise KeyError(f"{key} tidak ditemukan di {labels_path}")
    return [
        AnomalyWindow(start=pd.Timestamp(start), end=pd.Timestamp(end))
        for start, end in all_windows[key]
    ]


def anomaly_window_stats(df: pd.DataFrame, windows: Sequence[AnomalyWindow]) -> list[dict]:
    """Statistik nilai di dalam tiap window anomali berlabel, untuk validasi visual/manual."""
    stats = []
    for w in windows:
        mask = (df["timestamp"] >= w.start) & (df["timestamp"] <= w.end)
        subset = df.loc[mask, "value"]
        duration_h = (w.end - w.start).total_seconds() / 3600.0
        stats.append(
            {
                "start": w.start,
                "end": w.end,
                "duration_hours": duration_h,
                "n_points": int(len(subset)),
                "min_f": float(subset.min()) if len(subset) else None,
                "max_f": float(subset.max()) if len(subset) else None,
                "mean_f": float(subset.mean()) if len(subset) else None,
            }
        )
    return stats
