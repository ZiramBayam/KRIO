"""Uji Device Emulator: model termal, mode simulasi, dan kontrak payload.

Jalankan dari akar repositori:

    PYTHONPATH=services python3 -m unittest discover -s services/emulator/tests -v
"""
from __future__ import annotations

import random
import unittest
from datetime import datetime, timezone

from emulator import BoxThermalModel, DeviceConfig, Simulation, ThermalParams, build_fleet, build_payload, encode
from emulator.payload import MAX_PAYLOAD_BYTES, SCHEMA
from emulator.thermal import NOISE_SIGMA_C


def trace(mode: str, minutes: int, event_start_s: float = 600.0, tick: float = 10.0, **params):
    """Menjalankan model dan mengembalikan daftar (menit, suhu sebenarnya)."""
    model = BoxThermalModel(
        mode=mode,
        params=ThermalParams(**params),
        event_start_s=event_start_s,
        rng=random.Random(1),
    )
    series, t = [], 0.0
    while t <= minutes * 60:
        model.step(t, tick)
        t += tick
        series.append((t / 60, model.state.temp_c))
    return series


class ThermalModelTest(unittest.TestCase):
    def test_mode_normal_stabil_di_rentang_rantai_dingin(self):
        temps = [temp for _, temp in trace("normal", minutes=180)]
        self.assertGreaterEqual(min(temps), 0.0, "suhu tidak boleh membeku di bawah 0 °C")
        self.assertLessEqual(max(temps), 4.0, "mode normal harus bertahan di bawah ambang 4 °C")

    def test_mode_excursion_menanjak_monoton_setelah_kompresor_gagal(self):
        series = trace("excursion", minutes=90)
        after = [temp for minute, temp in series if minute > 12]
        self.assertTrue(
            all(b >= a - 1e-9 for a, b in zip(after, after[1:])),
            "suhu harus menanjak monoton setelah kompresor gagal",
        )
        minute_4c = next(m for m, t in series if t >= 4.0)
        minute_10c = next(m for m, t in series if t >= 10.0)
        self.assertTrue(
            25 <= minute_10c - minute_4c <= 40,
            f"kenaikan 4 °C ke 10 °C seharusnya ~30 menit, terukur {minute_10c - minute_4c:.0f} menit",
        )

    def test_mode_door_open_melonjak_lalu_pulih(self):
        series = trace("door-open", minutes=40)
        baseline = min(temp for minute, temp in series if minute < 10)
        peak = max(temp for _, temp in series)
        recovered = min(temp for minute, temp in series if 25 < minute < 35)
        self.assertGreaterEqual(peak - baseline, 4.0, "lonjakan pintu dibuka seharusnya sekitar +5 °C")
        self.assertLess(recovered - baseline, 1.0, "suhu harus pulih ke kurva normal setelah pintu ditutup")

    def test_mode_offline_menghentikan_pengiriman_pada_jendelanya(self):
        model = BoxThermalModel(mode="offline", event_start_s=600, rng=random.Random(1))
        self.assertTrue(model.is_transmitting(300, offline_seconds=1800))
        self.assertFalse(model.is_transmitting(900, offline_seconds=1800))
        self.assertTrue(model.is_transmitting(2500, offline_seconds=1800))

    def test_ambien_mengikuti_siklus_harian(self):
        model = BoxThermalModel(rng=random.Random(1))
        suhu_harian = [model.ambient_c(jam * 3600) for jam in range(24)]
        self.assertAlmostEqual(max(suhu_harian), 33.0, delta=0.2)
        self.assertAlmostEqual(min(suhu_harian), 25.0, delta=0.2)

    def test_derau_sensor_tidak_mengubah_suhu_sebenarnya(self):
        model = BoxThermalModel(rng=random.Random(7))
        bacaan = [model.measure(3.0) for _ in range(500)]
        rata = sum(bacaan) / len(bacaan)
        self.assertAlmostEqual(rata, 3.0, delta=0.1)
        self.assertLess(max(abs(b - 3.0) for b in bacaan), 5 * NOISE_SIGMA_C)

    def test_mode_tidak_dikenal_ditolak(self):
        with self.assertRaises(ValueError):
            BoxThermalModel(mode="turbo")


class PayloadTest(unittest.TestCase):
    def setUp(self):
        self.ts = datetime(2026, 9, 24, 9, 15, tzinfo=timezone.utc)

    def test_payload_sesuai_kontrak_dan_muat_satu_kuota_pesan(self):
        device = DeviceConfig("KRIO-0001", "cellular", lat=-7.7956, lon=110.3695)
        payload = build_payload(device, self.ts, seq=10432, temp_c=2.4051,
                                rh_pct=78.12, batt_v=3.913, rssi=-87)
        self.assertEqual(payload["schema"], SCHEMA)
        self.assertEqual(payload["ts"], "2026-09-24T09:15:00Z")
        self.assertEqual(payload["temp_c"], 2.41, "presisi suhu 0,01 °C")
        self.assertEqual(payload["gps"], {"lat": -7.7956, "lon": 110.3695})
        self.assertFalse(payload["buffered"])
        self.assertLessEqual(len(encode(payload)), MAX_PAYLOAD_BYTES)

    def test_gps_selalu_null_pada_jalur_lora(self):
        device = DeviceConfig("KRIO-0003", "lora", lat=-7.79, lon=110.36)
        payload = build_payload(device, self.ts, seq=1, temp_c=2.0)
        self.assertIsNone(payload["gps"], "perangkat LoRa tidak membawa GPS (PRD §8.3)")

    def test_link_tidak_dikenal_ditolak(self):
        with self.assertRaises(ValueError):
            DeviceConfig("KRIO-0004", "wifi")

    def test_payload_kebesaran_ditolak(self):
        device = DeviceConfig("K" * 600, "cellular")
        with self.assertRaises(ValueError):
            encode(build_payload(device, self.ts, seq=1, temp_c=2.0))


class CollectingSink:
    def __init__(self):
        self.messages = []

    def send(self, payload):
        self.messages.append(payload)

    def close(self):
        pass


class SimulationTest(unittest.TestCase):
    def _run(self, mode="normal", duration_s=7200, **kwargs):
        sink = CollectingSink()
        devices = build_fleet(
            [("KRIO-0001", "cellular"), ("KRIO-0002", "cellular"), ("KRIO-0003", "lora")],
            mode=mode, seed=42,
        )
        summary = Simulation(devices=devices, sink=sink, duration_s=duration_s, **kwargs).run()
        return sink, summary

    def test_tiga_armada_mengirim_sesuai_interval_per_jalur(self):
        sink, summary = self._run()
        per_device = {}
        for message in sink.messages:
            per_device.setdefault(message["device_id"], []).append(message)
        self.assertEqual(set(per_device), {"KRIO-0001", "KRIO-0002", "KRIO-0003"})
        # 2 jam: seluler tiap 5 menit, LoRa tiap 10 menit (PRD §8.4)
        self.assertEqual(len(per_device["KRIO-0001"]), 25)
        self.assertEqual(len(per_device["KRIO-0003"]), 13)
        self.assertEqual(summary["payload_melebihi_batas"], 0)

    def test_seq_monoton_naik_per_perangkat(self):
        sink, _ = self._run()
        seqs = [m["seq"] for m in sink.messages if m["device_id"] == "KRIO-0001"]
        self.assertEqual(seqs, list(range(1, len(seqs) + 1)))

    def test_mode_offline_meninggalkan_jeda_pada_deret_waktu(self):
        sink, summary = self._run(mode="offline", offline_seconds=1800)
        self.assertGreater(summary["pesan_dilewati_offline"], 0)
        waktu = [
            datetime.strptime(m["ts"], "%Y-%m-%dT%H:%M:%SZ")
            for m in sink.messages if m["device_id"] == "KRIO-0001"
        ]
        jeda = [(b - a).total_seconds() for a, b in zip(waktu, waktu[1:])]
        self.assertTrue(
            any(g >= 1800 for g in jeda),
            f"harus ada jeda >= 30 menit saat perangkat offline, jeda terbesar {max(jeda):.0f} detik",
        )

    def test_simulasi_dapat_diulang_dengan_seed_sama(self):
        first, _ = self._run()
        second, _ = self._run()
        self.assertEqual(
            [m["temp_c"] for m in first.messages],
            [m["temp_c"] for m in second.messages],
            "seed yang sama harus menghasilkan deret suhu yang sama",
        )


if __name__ == "__main__":
    unittest.main()
