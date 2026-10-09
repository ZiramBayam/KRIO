"""Uji kalibrasi baseline persistence pada Dataset B (issue #62).

Jalankan dari akar repositori:

    PYTHONPATH=services:. python3 -m unittest discover -s ml/calibration/tests -v
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

import pandas as pd

from alerting.residual import CalibrationParams, detect_events
from alerting.rules import KIND_THRESHOLD
from ml.calibration.dataset_b_baseline import (
    is_in_any_window,
    match_events_to_windows,
    moving_average_predict,
    persistence_predict,
    residual_series,
    validation_residuals,
)
from ml.eda.dataset_b import AnomalyWindow

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_df(values: list[float], step_minutes: int = 5) -> pd.DataFrame:
    ts = [T0 + timedelta(minutes=step_minutes * i) for i in range(len(values))]
    return pd.DataFrame({"timestamp": ts, "value": values})


class PersistencePredictTest(unittest.TestCase):
    def test_lag_satu_langkah(self):
        df = make_df([10.0, 11.0, 13.0, 12.0])
        out = persistence_predict(df, lag_steps=1)
        self.assertEqual(len(out), 3)  # baris pertama dibuang (tanpa prediksi)
        self.assertAlmostEqual(out["predicted"].iloc[0], 10.0)
        self.assertAlmostEqual(out["residual"].iloc[0], 1.0)  # 11 - 10
        self.assertAlmostEqual(out["residual"].iloc[1], 2.0)  # 13 - 11
        self.assertAlmostEqual(out["residual"].iloc[2], -1.0)  # 12 - 13

    def test_baris_tidak_cukup_untuk_lag_menghasilkan_kosong(self):
        df = make_df([10.0])
        out = persistence_predict(df, lag_steps=1)
        self.assertEqual(len(out), 0)


class MovingAveragePredictTest(unittest.TestCase):
    def test_prediksi_rata_rata_tanpa_nilai_saat_ini(self):
        df = make_df([10.0, 20.0, 30.0, 40.0, 50.0])
        out = moving_average_predict(df, window_steps=2)
        # baris pertama yang punya window penuh (2 nilai sebelum t): index asli 2
        # predicted = mean(10, 20) = 15, value = 30, residual = 15
        self.assertEqual(len(out), 3)
        self.assertAlmostEqual(out["predicted"].iloc[0], 15.0)
        self.assertAlmostEqual(out["residual"].iloc[0], 15.0)

    def test_drift_bertahan_tetap_terlihat_di_residual(self):
        # nilai naik bertahap terus-menerus (drift), bukan lonjakan tajam
        values = [10.0] * 5 + [15.0, 20.0, 25.0, 30.0, 35.0, 40.0]
        df = make_df(values)
        out_persist = persistence_predict(df, lag_steps=1)
        out_ma = moving_average_predict(df, window_steps=5)
        # moving average mempertahankan residual besar lebih lama daripada persistence
        # setelah drift dimulai, karena baseline-nya belum ikut naik
        last_persist_residual = out_persist["residual"].iloc[-1]
        last_ma_residual = out_ma["residual"].iloc[-1]
        self.assertGreater(abs(last_ma_residual), abs(last_persist_residual))


class WindowHelperTest(unittest.TestCase):
    def setUp(self):
        self.window = AnomalyWindow(
            start=pd.Timestamp(T0 + timedelta(minutes=10)),
            end=pd.Timestamp(T0 + timedelta(minutes=20)),
        )

    def test_di_dalam_window(self):
        self.assertTrue(is_in_any_window(pd.Timestamp(T0 + timedelta(minutes=15)), [self.window]))

    def test_di_luar_window(self):
        self.assertFalse(is_in_any_window(pd.Timestamp(T0), [self.window]))

    def test_tepat_di_batas_termasuk(self):
        self.assertTrue(is_in_any_window(pd.Timestamp(T0 + timedelta(minutes=10)), [self.window]))


class ValidationResidualsTest(unittest.TestCase):
    def test_residual_di_dalam_window_disaring(self):
        df = make_df([10.0, 10.0, 50.0, 50.0, 10.0])
        df = persistence_predict(df, lag_steps=1)
        # Window dibuat selebar [10, 20] (bukan hanya [10, 15]) karena residual
        # persistence "bocor" satu langkah lag ke depan: residual di ts=20
        # (10 - 50 = -40) adalah EFEK dari lonjakan yang terjadi SAAT ts=15,
        # bukan anomali baru di ts=20. Ini batasan baseline persistence yang
        # didokumentasikan di dataset_b_baseline.py dan laporan kalibrasi —
        # bukan bug di validation_residuals().
        window = AnomalyWindow(
            start=pd.Timestamp(T0 + timedelta(minutes=10)),
            end=pd.Timestamp(T0 + timedelta(minutes=20)),
        )
        residuals = validation_residuals(df, [window])
        self.assertTrue(all(abs(r) < 1e-9 for r in residuals))


class MatchEventsToWindowsTest(unittest.TestCase):
    def test_event_yang_beririsan_tertangkap(self):
        window = AnomalyWindow(
            start=pd.Timestamp(T0),
            end=pd.Timestamp(T0 + timedelta(hours=2)),
        )
        # buat deret residual panas terus-menerus 25 menit di dalam window
        readings = [(T0, 0.0)] + [
            (T0 + timedelta(minutes=5 * i), 4.0) for i in range(1, 6)
        ]
        params = CalibrationParams(sigma_c=1.0, cusum_k=0.5)
        events = detect_events(readings, params)
        self.assertTrue(any(e.kind == KIND_THRESHOLD for e in events))

        matches = match_events_to_windows(events, [window])
        self.assertEqual(len(matches), 1)
        self.assertTrue(matches[0].matched)

    def test_window_tanpa_event_tidak_tertangkap(self):
        window = AnomalyWindow(
            start=pd.Timestamp(T0 + timedelta(days=1)),
            end=pd.Timestamp(T0 + timedelta(days=2)),
        )
        matches = match_events_to_windows([], [window])
        self.assertFalse(matches[0].matched)


class ResidualSeriesTest(unittest.TestCase):
    def test_konversi_dataframe_ke_list_tuple(self):
        df = make_df([10.0, 11.0])
        df = persistence_predict(df, lag_steps=1)
        series = residual_series(df)
        self.assertEqual(len(series), 1)
        self.assertEqual(series[0][1], 1.0)


if __name__ == "__main__":
    unittest.main()
