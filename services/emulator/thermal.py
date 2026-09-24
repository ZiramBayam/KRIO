"""Model termal boks pendingin (PRD §8.6).

Suhu boks mengikuti hukum pendinginan Newton dengan tambahan beban panas:

    dT/dt = -k * (T - T_target) + Q(t) / C

- ``k``        konstanta pendinginan aktif kompresor (1/detik)
- ``T_target`` setpoint pendingin
- ``Q(t)``     beban panas: rembesan dari lingkungan + kejadian (pintu dibuka)
- ``C``        kapasitas termal boks

Suhu ambien mengikuti siklus harian sinusoidal, dan pembacaan sensor diberi
derau Gaussian σ = 0,3 °C sesuai akurasi logger nyata.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

MODES = ("normal", "excursion", "door-open", "offline")

SECONDS_PER_DAY = 86_400
NOISE_SIGMA_C = 0.3


@dataclass
class ThermalParams:
    """Parameter fisik satu boks pendingin."""

    setpoint_c: float = 2.0
    k_cooling: float = 6.0e-3       # 1/detik; konstanta waktu pendinginan ~3 menit
    u_ingress: float = 1.1e-2       # W/K; rembesan panas dari lingkungan
    heat_capacity: float = 90.0     # J/K (skala relatif, dikalibrasi ke laju realistis)
    ambient_mean_c: float = 29.0    # rata-rata suhu udara Yogyakarta
    ambient_amplitude_c: float = 4.0
    ambient_peak_hour: float = 14.0  # jam ambien tertinggi
    door_open_watt: float = 2.4     # beban panas saat pintu terbuka
    door_open_seconds: int = 300    # 5 menit; batas atas rentang 2-5 menit PRD,
                                    # dipilih agar lonjakan tetap terekam pada
                                    # interval sampling 5 menit (PRD §8.4)


@dataclass
class ThermalState:
    """Keadaan simulasi satu boks pada satu titik waktu."""

    temp_c: float
    compressor_ok: bool = True


@dataclass
class BoxThermalModel:
    """Menyimulasikan suhu satu boks pendingin pada mode tertentu.

    Waktu dinyatakan dalam detik sejak awal simulasi. ``event_start_s``
    menentukan kapan kejadian mode dimulai (kegagalan kompresor atau pintu
    pertama dibuka).
    """

    mode: str = "normal"
    params: ThermalParams = field(default_factory=ThermalParams)
    event_start_s: float = 600.0
    door_period_s: float = 1_800.0   # pintu dibuka tiap 30 menit pada mode door-open
    rng: random.Random = field(default_factory=random.Random)
    state: ThermalState = field(init=False)

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"mode tidak dikenal: {self.mode!r}; pilihan: {', '.join(MODES)}")
        self.state = ThermalState(temp_c=self.params.setpoint_c)

    # ------------------------------------------------------------------ fisika
    def ambient_c(self, t_s: float) -> float:
        """Suhu udara luar pada detik ke-``t_s`` (siklus harian sinusoidal)."""
        p = self.params
        phase = 2 * math.pi * (t_s / SECONDS_PER_DAY - p.ambient_peak_hour / 24) - math.pi / 2
        return p.ambient_mean_c + p.ambient_amplitude_c * math.sin(phase)

    def _apply_events(self, t_s: float) -> float:
        """Memperbarui keadaan kejadian dan mengembalikan beban panas tambahan (W)."""
        p = self.params
        s = self.state

        if self.mode == "excursion" and t_s >= self.event_start_s:
            # Kompresor gagal: pendinginan aktif berhenti, suhu menanjak monoton
            # menuju suhu lingkungan.
            s.compressor_ok = False

        if self.mode == "door-open" and t_s >= self.event_start_s:
            since = t_s - self.event_start_s
            if since % self.door_period_s < p.door_open_seconds:
                return p.door_open_watt

        return 0.0

    def step(self, t_s: float, dt_s: float) -> float:
        """Memajukan simulasi ``dt_s`` detik dan mengembalikan suhu sebenarnya."""
        p = self.params
        s = self.state
        q_event = self._apply_events(t_s)

        # Integrasi Euler; dt kecil relatif terhadap konstanta waktu boks.
        remaining = dt_s
        max_step = 30.0
        while remaining > 0:
            h = min(max_step, remaining)
            q_ingress = p.u_ingress * (self.ambient_c(t_s) - s.temp_c)
            cooling = -p.k_cooling * (s.temp_c - p.setpoint_c) if s.compressor_ok else 0.0
            s.temp_c += (cooling + (q_ingress + q_event) / p.heat_capacity) * h
            remaining -= h
            t_s += h
        return s.temp_c

    def measure(self, true_temp_c: float) -> float:
        """Pembacaan sensor: suhu sebenarnya + derau Gaussian, presisi 0,01 °C."""
        return round(true_temp_c + self.rng.gauss(0.0, NOISE_SIGMA_C), 2)

    def is_transmitting(self, t_s: float, offline_seconds: float) -> bool:
        """False bila perangkat sedang pada jendela offline (mode ``offline``)."""
        if self.mode != "offline":
            return True
        return not (self.event_start_s <= t_s < self.event_start_s + offline_seconds)
