import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from ml.eda.dataset_b import (
    anomaly_window_stats,
    detect_sampling_interval_minutes,
    fahrenheit_to_celsius,
    load_anomaly_windows,
    load_nab_series,
    summarize_series,
    validate_series,
)


def _write_csv(tmpdir: Path, name: str, rows: list[tuple[str, float]]) -> Path:
    path = tmpdir / name
    with open(path, "w", encoding="utf-8") as f:
        f.write("timestamp,value\n")
        for ts, val in rows:
            f.write(f"{ts},{val}\n")
    return path


class KonversiSuhuTest(unittest.TestCase):
    def test_titik_beku(self):
        self.assertAlmostEqual(fahrenheit_to_celsius(32.0), 0.0, places=9)

    def test_titik_didih(self):
        self.assertAlmostEqual(fahrenheit_to_celsius(212.0), 100.0, places=9)

    def test_suhu_ruangan_nab(self):
        # ambient_temperature_system_failure.csv berkisar ~69-71 F
        self.assertAlmostEqual(fahrenheit_to_celsius(69.88083514), 21.044908, places=4)


class MuatDataTest(unittest.TestCase):
    def test_urut_dan_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            path = _write_csv(
                Path(td),
                "a.csv",
                [
                    ("2013-07-04 01:00:00", 70.0),
                    ("2013-07-04 00:00:00", 69.0),
                    ("2013-07-04 01:00:00", 70.0),  # duplikat timestamp
                ],
            )
            df = load_nab_series(path)
            self.assertEqual(len(df), 2)
            self.assertEqual(df.attrs["n_duplicates_dropped"], 1)
            self.assertTrue(df["timestamp"].is_monotonic_increasing)

    def test_kolom_value_wajib_ada(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.csv"
            path.write_text("timestamp,suhu\n2013-07-04 00:00:00,70.0\n")
            with self.assertRaises(ValueError):
                load_nab_series(path)


class IntervalSamplingTest(unittest.TestCase):
    def test_interval_per_jam(self):
        with tempfile.TemporaryDirectory() as td:
            rows = [(f"2013-07-04 0{h}:00:00", 70.0) for h in range(5)]
            path = _write_csv(Path(td), "hourly.csv", rows)
            df = load_nab_series(path)
            self.assertAlmostEqual(detect_sampling_interval_minutes(df), 60.0, places=6)

    def test_interval_5_menit(self):
        with tempfile.TemporaryDirectory() as td:
            rows = [
                ("2013-07-04 00:00:00", 70.0),
                ("2013-07-04 00:05:00", 70.0),
                ("2013-07-04 00:10:00", 70.0),
                ("2013-07-04 00:15:00", 70.0),
            ]
            path = _write_csv(Path(td), "five_min.csv", rows)
            df = load_nab_series(path)
            self.assertAlmostEqual(detect_sampling_interval_minutes(df), 5.0, places=6)

    def test_kurang_dari_2_baris_raise(self):
        with tempfile.TemporaryDirectory() as td:
            path = _write_csv(Path(td), "one_row.csv", [("2013-07-04 00:00:00", 70.0)])
            df = load_nab_series(path)
            with self.assertRaises(ValueError):
                detect_sampling_interval_minutes(df)


class ValidasiSeriesTest(unittest.TestCase):
    def test_tanpa_gap(self):
        with tempfile.TemporaryDirectory() as td:
            rows = [(f"2013-07-04 0{h}:00:00", 70.0) for h in range(5)]
            path = _write_csv(Path(td), "clean.csv", rows)
            df = load_nab_series(path)
            report = validate_series(df)
            self.assertEqual(report.n_gaps, 0)
            self.assertTrue(report.is_clean())

    def test_dengan_gap_terdeteksi(self):
        with tempfile.TemporaryDirectory() as td:
            rows = [
                ("2013-07-04 00:00:00", 70.0),
                ("2013-07-04 01:00:00", 70.0),
                ("2013-07-04 02:00:00", 70.0),
                # celah 4 jam, jauh di atas 1.5x interval median (1 jam)
                ("2013-07-04 06:00:00", 70.0),
                ("2013-07-04 07:00:00", 70.0),
            ]
            path = _write_csv(Path(td), "gappy.csv", rows)
            df = load_nab_series(path)
            report = validate_series(df)
            self.assertEqual(report.n_gaps, 1)
            self.assertAlmostEqual(report.max_gap_minutes, 240.0, places=6)


class RingkasanSeriesTest(unittest.TestCase):
    def test_statistik_dasar(self):
        with tempfile.TemporaryDirectory() as td:
            rows = [
                ("2013-07-04 00:00:00", 32.0),
                ("2013-07-04 01:00:00", 212.0),
            ]
            path = _write_csv(Path(td), "extremes.csv", rows)
            df = load_nab_series(path)
            summary = summarize_series(df)
            self.assertEqual(summary.n_rows, 2)
            self.assertAlmostEqual(summary.min_f, 32.0)
            self.assertAlmostEqual(summary.max_f, 212.0)
            self.assertAlmostEqual(summary.min_c, 0.0, places=9)
            self.assertAlmostEqual(summary.max_c, 100.0, places=9)


class AnomaliBerlabelTest(unittest.TestCase):
    def test_muat_window_dari_json(self):
        with tempfile.TemporaryDirectory() as td:
            labels_path = Path(td) / "combined_windows.json"
            labels_path.write_text(
                json.dumps(
                    {
                        "realKnownCause/machine_temperature_system_failure.csv": [
                            ["2013-12-10 06:25:00.000000", "2013-12-12 05:35:00.000000"]
                        ]
                    }
                )
            )
            windows = load_anomaly_windows(
                labels_path, "realKnownCause/machine_temperature_system_failure.csv"
            )
            self.assertEqual(len(windows), 1)
            self.assertEqual(windows[0].start, pd.Timestamp("2013-12-10 06:25:00"))

    def test_key_tidak_ditemukan_raise(self):
        with tempfile.TemporaryDirectory() as td:
            labels_path = Path(td) / "combined_windows.json"
            labels_path.write_text(json.dumps({}))
            with self.assertRaises(KeyError):
                load_anomaly_windows(labels_path, "tidak/ada.csv")

    def test_statistik_di_dalam_window(self):
        with tempfile.TemporaryDirectory() as td:
            rows = [
                ("2013-07-04 00:00:00", 70.0),
                ("2013-07-04 01:00:00", 90.0),  # di dalam window
                ("2013-07-04 02:00:00", 95.0),  # di dalam window
                ("2013-07-04 03:00:00", 71.0),  # di luar window
            ]
            path = _write_csv(Path(td), "windowed.csv", rows)
            df = load_nab_series(path)
            from ml.eda.dataset_b import AnomalyWindow

            windows = [
                AnomalyWindow(
                    start=pd.Timestamp("2013-07-04 01:00:00"),
                    end=pd.Timestamp("2013-07-04 02:00:00"),
                )
            ]
            stats = anomaly_window_stats(df, windows)
            self.assertEqual(len(stats), 1)
            self.assertEqual(stats[0]["n_points"], 2)
            self.assertAlmostEqual(stats[0]["max_f"], 95.0)


if __name__ == "__main__":
    unittest.main()
