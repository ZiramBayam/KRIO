"""Estimasi sisa umur simpan berbasis Arrhenius dan Time-Temperature Integration (PRD §13.1).

Laju degradasi mutu:

    k(T) = k_ref * exp[ -(Ea/R) * (1/T - 1/T_ref) ],   k_ref = 1 / SL_ref

Akumulasi kerusakan (aturan trapesium atas pembacaan diskrit):

    D(t) = integral k(T(tau)) dtau        D = 1  ->  umur simpan habis

Modul ini murni komputasi: tanpa akses basis data maupun Azure, sehingga dapat
dipanggil oleh ``fn_shelflife`` (PRD §7) dan diuji lokal. Parameter kinetika
dibaca dari baris ``products`` (``ea_j_per_mol``, ``t_ref_k``,
``shelf_life_ref_h``), jadi tidak ada nilai produk yang ditanam di sini.

Angka yang dihasilkan adalah estimasi berbasis parameter literatur yang belum
dikalibrasi lokal (PRD §13.2, risiko R7).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence

GAS_CONSTANT = 8.314          # J/(mol·K), sesuai PRD §13.1
KELVIN_OFFSET = 273.15

Reading = tuple[datetime, float]   # (ts, temp_c)


@dataclass(frozen=True)
class KineticParams:
    """Parameter kinetika satu produk (kolom tabel ``products``)."""

    ea_j_per_mol: float = 60_000.0
    t_ref_k: float = 273.15
    shelf_life_ref_h: float = 240.0

    def __post_init__(self) -> None:
        if self.ea_j_per_mol <= 0 or self.t_ref_k <= 0 or self.shelf_life_ref_h <= 0:
            raise ValueError("ea_j_per_mol, t_ref_k, dan shelf_life_ref_h harus positif")

    @classmethod
    def from_product(cls, row: dict) -> "KineticParams":
        """Membangun dari baris ``products`` (dict hasil kueri)."""
        return cls(
            ea_j_per_mol=float(row["ea_j_per_mol"]),
            t_ref_k=float(row["t_ref_k"]),
            shelf_life_ref_h=float(row["shelf_life_ref_h"]),
        )


def rate_factor(temp_c: float, params: KineticParams) -> float:
    """Laju degradasi relatif terhadap T_ref: k(T) / k_ref."""
    t_k = temp_c + KELVIN_OFFSET
    if t_k <= 0:
        raise ValueError(f"suhu {temp_c} °C di bawah nol mutlak")
    return math.exp(-(params.ea_j_per_mol / GAS_CONSTANT) * (1.0 / t_k - 1.0 / params.t_ref_k))


def decay_rate_per_h(temp_c: float, params: KineticParams) -> float:
    """k(T) dalam satuan 1/jam."""
    return rate_factor(temp_c, params) / params.shelf_life_ref_h


def accumulate_decay(readings: Iterable[Reading], params: KineticParams, d0: float = 0.0) -> float:
    """Menghitung D = d0 + integral k(T) dt dengan aturan trapesium.

    - ``readings`` boleh tidak berurutan: diurutkan menurut ``ts``, bukan waktu
      terima, agar data ``buffered`` (F6) jatuh di posisi kronologis yang benar.
    - Stempel waktu kembar dibuang (sisa satu, yang terakhir muncul).
    - Celah tanpa data (zona tanpa sinyal) diinterpolasi linear antar dua
      pembacaan terdekat — asumsi yang harus disebut di laporan.
    - Untuk pembaruan inkremental (fn_shelflife tiap 15 menit), sertakan
      pembacaan terakhir jendela sebelumnya sebagai elemen pertama dan berikan
      ``d0`` hasil jendela itu; jangan hitung ulang dari awal pengiriman.
    """
    by_ts: dict[datetime, float] = {ts: temp for ts, temp in readings}
    ordered = sorted(by_ts.items())
    d = d0
    for (t1, c1), (t2, c2) in zip(ordered, ordered[1:]):
        dt_h = (t2 - t1).total_seconds() / 3600.0
        d += 0.5 * (decay_rate_per_h(c1, params) + decay_rate_per_h(c2, params)) * dt_h
    return d


def remaining_pct(d: float) -> float:
    """Sisa umur simpan (%) = max(0, (1 - D) * 100), dibatasi 0–100 (constraint DB)."""
    return min(100.0, max(0.0, (1.0 - d) * 100.0))


def remaining_hours(d: float, temp_c: float, params: KineticParams) -> float:
    """Sisa waktu (jam) bila suhu bertahan di ``temp_c``: (1 - D) / k(T)."""
    return max(0.0, (1.0 - d) / decay_rate_per_h(temp_c, params))


def project_remaining_pct(
    d_now: float,
    current_temp_c: float,
    forecast: Sequence[tuple[float, float]],
    params: KineticParams,
) -> float:
    """Proyeksi sisa umur simpan (%) memakai suhu hasil prediksi (PRD §13.1).

    ``forecast`` berisi pasangan ``(menit_ke_depan, suhu_prediksi_c)``, mis.
    ``[(30, 2.8), (60, 3.4)]`` dari tabel ``forecasts``. Titik awal (0 menit)
    adalah suhu terukur saat ini. Hasil untuk titik terjauh dilaporkan sebagai
    ``projected_pct_60m``.
    """
    points = [(0.0, current_temp_c)] + sorted(forecast)
    d = d_now
    for (m1, c1), (m2, c2) in zip(points, points[1:]):
        d += 0.5 * (decay_rate_per_h(c1, params) + decay_rate_per_h(c2, params)) * (m2 - m1) / 60.0
    return remaining_pct(d)
