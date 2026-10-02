"""Uji aturan peringatan: ambang suhu (#48) dan perangkat offline (#49).

Jalankan dari akar repositori:

    PYTHONPATH=services python3 -m unittest discover -s services/alerting/tests -v
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from alerting import (
    KIND_OFFLINE,
    KIND_THRESHOLD,
    ThresholdRange,
    evaluate_offline,
    evaluate_threshold,
    severity_for,
)

IKAN_SEGAR = ThresholdRange(temp_min_c=0.0, temp_max_c=4.0)
T0 = datetime(2026, 10, 2, 8, 0, tzinfo=timezone.utc)


class ThresholdRangeTest(unittest.TestCase):
    def test_rentang_terbalik_ditolak(self):
        with self.assertRaises(ValueError):
            ThresholdRange(temp_min_c=4.0, temp_max_c=0.0)

    def test_simpangan_nol_saat_suhu_aman(self):
        self.assertEqual(IKAN_SEGAR.deviation_c(2.5), 0.0)
        self.assertEqual(IKAN_SEGAR.deviation_c(4.0), 0.0)

    def test_simpangan_dihitung_dari_batas_terdekat(self):
        self.assertAlmostEqual(IKAN_SEGAR.deviation_c(6.5), 2.5)
        self.assertAlmostEqual(IKAN_SEGAR.deviation_c(-1.5), 1.5)


class SeverityTest(unittest.TestCase):
    def test_simpangan_sampai_lima_derajat_warning(self):
        self.assertEqual(severity_for(0.1), "warning")
        self.assertEqual(severity_for(5.0), "warning")

    def test_simpangan_di_atas_lima_derajat_critical(self):
        self.assertEqual(severity_for(5.01), "critical")
        self.assertEqual(severity_for(12.0), "critical")


class ThresholdAlertTest(unittest.TestCase):
    def test_suhu_di_dalam_rentang_tidak_memicu_peringatan(self):
        self.assertIsNone(evaluate_threshold(2.4, T0, IKAN_SEGAR, "Boks A-01"))

    def test_suhu_di_atas_batas_memicu_kegagalan_pendingin(self):
        draft = evaluate_threshold(6.2, T0, IKAN_SEGAR, "Boks B-04")
        self.assertIsNotNone(draft)
        self.assertEqual(draft.kind, KIND_THRESHOLD)
        self.assertEqual(draft.severity, "warning")
        self.assertEqual(draft.raised_at, T0)
        self.assertIn("Boks B-04", draft.message)
        self.assertIn("di atas", draft.message)

    def test_suhu_jauh_di_atas_batas_menjadi_critical(self):
        draft = evaluate_threshold(12.0, T0, IKAN_SEGAR, "Boks B-04")
        self.assertEqual(draft.severity, "critical")

    def test_suhu_di_bawah_batas_bawah_juga_memicu_peringatan(self):
        draft = evaluate_threshold(-2.0, T0, IKAN_SEGAR, "Boks C-02")
        self.assertIsNotNone(draft)
        self.assertIn("di bawah", draft.message)

    def test_peringatan_diredam_tiga_puluh_menit(self):
        self.assertIsNone(
            evaluate_threshold(
                6.2, T0 + timedelta(minutes=29), IKAN_SEGAR, "Boks B-04", last_alert_at=T0
            )
        )

    def test_peringatan_terbit_lagi_setelah_jendela_peredaman(self):
        draft = evaluate_threshold(
            6.2, T0 + timedelta(minutes=31), IKAN_SEGAR, "Boks B-04", last_alert_at=T0
        )
        self.assertIsNotNone(draft)


class OfflineAlertTest(unittest.TestCase):
    def test_perangkat_yang_baru_mengirim_tidak_memicu_peringatan(self):
        self.assertIsNone(
            evaluate_offline(T0 - timedelta(minutes=6), T0, "Boks A-01")
        )

    def test_diam_sepuluh_menit_memicu_device_offline(self):
        draft = evaluate_offline(T0 - timedelta(minutes=12), T0, "Boks A-01")
        self.assertIsNotNone(draft)
        self.assertEqual(draft.kind, KIND_OFFLINE)
        self.assertEqual(draft.severity, "warning")
        self.assertIn("12 menit", draft.message)

    def test_perangkat_tanpa_telemetri_sama_sekali_dilewati(self):
        self.assertIsNone(evaluate_offline(None, T0, "Boks baru"))

    def test_peringatan_offline_diredam_satu_jam(self):
        self.assertIsNone(
            evaluate_offline(
                T0 - timedelta(minutes=40), T0, "Boks A-01",
                last_alert_at=T0 - timedelta(minutes=59),
            )
        )

    def test_peringatan_offline_terbit_lagi_setelah_satu_jam(self):
        draft = evaluate_offline(
            T0 - timedelta(minutes=90), T0, "Boks A-01",
            last_alert_at=T0 - timedelta(minutes=61),
        )
        self.assertIsNotNone(draft)


if __name__ == "__main__":
    unittest.main()
