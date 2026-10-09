"""Uji deteksi anomali residual + CUSUM (issue #62, F4).

Jalankan dari akar repositori:

    PYTHONPATH=services python3 -m unittest discover -s services/alerting/tests -v
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from alerting.residual import CalibrationParams, detect_events, estimate_sigma, update_cusum
from alerting.rules import KIND_DOOR_OPEN, KIND_THRESHOLD

T0 = datetime(2026, 10, 2, 8, 0, tzinfo=timezone.utc)
PARAMS = CalibrationParams(sigma_c=1.0, cusum_k=0.5)  # threshold = 3 sigma = 3.0 C


def series(pairs: list[tuple[int, float]]) -> list[tuple[datetime, float]]:
    """Bangun deret (ts, residual) dari daftar (menit_offset, residual)."""
    return [(T0 + timedelta(minutes=m), r) for m, r in pairs]


class CalibrationParamsTest(unittest.TestCase):
    def test_sigma_non_positif_ditolak(self):
        with self.assertRaises(ValueError):
            CalibrationParams(sigma_c=0.0, cusum_k=0.5)

    def test_k_negatif_ditolak(self):
        with self.assertRaises(ValueError):
            CalibrationParams(sigma_c=1.0, cusum_k=-0.1)

    def test_ambang_door_open_melebihi_cooling_failure_ditolak(self):
        with self.assertRaises(ValueError):
            CalibrationParams(sigma_c=1.0, cusum_k=0.5, door_open_max_minutes=25, cooling_failure_min_minutes=20)

    def test_threshold_dihitung_dari_sigma(self):
        p = CalibrationParams(sigma_c=2.0, cusum_k=0.5, excursion_sigma_multiplier=3.0)
        self.assertAlmostEqual(p.excursion_threshold_c, 6.0)


class EstimasiSigmaTest(unittest.TestCase):
    def test_nilai_konstan_sigma_nol_gagal_dipakai_di_params(self):
        # estimate_sigma sendiri boleh mengembalikan 0 untuk data konstan;
        # CalibrationParams-lah yang menolak sigma <= 0.
        self.assertEqual(estimate_sigma([5.0, 5.0, 5.0]), 0.0)

    def test_sigma_data_sederhana(self):
        # residual = [-1, 1] -> mean 0, variance sampel = ((1)+(1))/1 = 2, std = sqrt(2)
        self.assertAlmostEqual(estimate_sigma([-1.0, 1.0]), 2**0.5, places=9)

    def test_kurang_dari_2_nilai_raise(self):
        with self.assertRaises(ValueError):
            estimate_sigma([1.0])


class UpdateCusumTest(unittest.TestCase):
    def test_tidak_pernah_negatif(self):
        s = update_cusum(prev_s=0.0, residual_c=-5.0, k=0.5)
        self.assertEqual(s, 0.0)

    def test_akumulasi_naik_saat_residual_melebihi_k(self):
        s = update_cusum(prev_s=1.0, residual_c=2.0, k=0.5)
        self.assertAlmostEqual(s, 2.5)


class DeteksiPintuDibukaTest(unittest.TestCase):
    def test_lonjakan_singkat_kembali_normal_jadi_pintu_dibuka(self):
        data = series(
            [
                (0, 0.1), (5, 0.0),
                (10, 4.0), (15, 4.5),  # > 3 sigma, 2 titik (10 menit)
                (20, 0.2), (25, 0.0),  # kembali normal
            ]
        )
        events = detect_events(data, PARAMS)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, KIND_DOOR_OPEN)
        self.assertEqual(events[0].severity, "info")
        self.assertAlmostEqual(events[0].duration_minutes, 10.0)

    def test_tidak_ada_lonjakan_tidak_ada_event(self):
        data = series([(m, 0.1) for m in range(0, 30, 5)])
        self.assertEqual(detect_events(data, PARAMS), [])

    def test_lonjakan_dingin_juga_terdeteksi_pintu_dibuka(self):
        # residual negatif (lebih dingin dari prediksi) tetap |r| > 3 sigma
        data = series([(0, 0.0), (5, -4.0), (10, -4.2), (15, 0.0)])
        events = detect_events(data, PARAMS)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, KIND_DOOR_OPEN)


class DeteksiKegagalanPendinginTest(unittest.TestCase):
    def test_lonjakan_panas_berkepanjangan_jadi_kegagalan_pendingin(self):
        # residual > 3C terus-menerus selama >= 20 menit dengan CUSUM naik terus
        points = [(0, 0.0)] + [(m, 4.0) for m in range(5, 26, 5)]
        data = series(points)
        events = detect_events(data, PARAMS)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, KIND_THRESHOLD)
        self.assertEqual(events[0].severity, "critical")
        self.assertAlmostEqual(events[0].duration_minutes, 20.0)
        self.assertIsNone(events[0].ended_at)

    def test_event_tidak_diulang_dalam_satu_episode(self):
        points = [(0, 0.0)] + [(m, 4.0) for m in range(5, 41, 5)]  # 35 menit berturut-turut
        data = series(points)
        events = detect_events(data, PARAMS)
        # hanya 1 event meski episode berlanjut jauh melebihi 20 menit
        self.assertEqual(len(events), 1)

    def test_zona_abu_abu_15_sampai_20_menit_tidak_dilabel(self):
        # kembali normal setelah 15 menit (tepat di batas), sebelum 20 menit
        points = [(0, 0.0)] + [(m, 4.0) for m in (5, 10, 15)] + [(20, 0.0)]
        data = series(points)
        events = detect_events(data, PARAMS)
        self.assertEqual(events, [])


class KalibrasiMachineTemperatureTest(unittest.TestCase):
    """Uji regresi memakai bentuk nyata window anomali #1 Dataset B (disederhanakan).

    Window asli: 2013-12-10 06:25 s/d 2013-12-12 05:35 (~47 jam) — jauh lebih
    panjang dari 20 menit, jadi harus terklasifikasi KEGAGALAN_PENDINGIN, bukan
    PINTU_DIBUKA atau tidak terdeteksi sama sekali.
    """

    def test_window_anomali_panjang_terdeteksi_kritis(self):
        start = datetime(2013, 12, 10, 6, 25, tzinfo=timezone.utc)
        data = [(start, 0.0)]
        for step in range(1, 10):  # 9 titik x 5 menit = 40 menit di dalam window
            data.append((start + timedelta(minutes=5 * step), 5.0))
        events = detect_events(data, PARAMS)
        self.assertTrue(any(e.kind == KIND_THRESHOLD for e in events))


if __name__ == "__main__":
    unittest.main()
