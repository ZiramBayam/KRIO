"""Uji model umur simpan Arrhenius/TTI (PRD §13).

Jalankan dari akar repositori:

    PYTHONPATH=services python3 -m unittest discover -s services/shelflife/tests -v
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from shelflife import (
    KineticParams,
    accumulate_decay,
    decay_rate_per_h,
    mkt_c,
    project_remaining_pct,
    rate_factor,
    remaining_hours,
    remaining_pct,
)

# Parameter baku PRD §13.1 (ikan segar): Ea 60 kJ/mol, T_ref 0 °C, SL_ref 10 hari.
PRD = KineticParams(ea_j_per_mol=60_000.0, t_ref_k=273.15, shelf_life_ref_h=240.0)
T0 = datetime(2026, 9, 25, 8, 0, tzinfo=timezone.utc)


def constant_series(temp_c: float, hours: float, step_min: int = 10):
    n = int(hours * 60 / step_min)
    return [(T0 + timedelta(minutes=step_min * i), temp_c) for i in range(n + 1)]


class TabelKewajaranTest(unittest.TestCase):
    """Tabel PRD §13.2: faktor laju dan umur simpan pada suhu konstan."""

    TABEL = [  # suhu °C, faktor laju, umur simpan (hari)
        (0, 1.00, 10.0),
        (2, 1.21, 8.3),
        (4, 1.46, 6.8),
        (10, 2.54, 3.9),
        (15, 3.96, 2.5),
    ]

    def test_faktor_laju_sesuai_tabel(self):
        for temp, faktor, _ in self.TABEL:
            with self.subTest(temp=temp):
                self.assertAlmostEqual(rate_factor(temp, PRD), faktor, places=2)

    def test_umur_simpan_sesuai_tabel(self):
        for temp, _, hari in self.TABEL:
            with self.subTest(temp=temp):
                jam = PRD.shelf_life_ref_h / rate_factor(temp, PRD)
                self.assertAlmostEqual(jam / 24.0, hari, places=1)


class AkumulasiKerusakanTest(unittest.TestCase):
    def test_laju_pada_t_ref_sama_dengan_satu_per_sl_ref(self):
        self.assertAlmostEqual(decay_rate_per_h(0.0, PRD), 1.0 / 240.0, places=12)

    def test_suhu_konstan_di_t_ref_habis_tepat_setelah_sl_ref(self):
        d = accumulate_decay(constant_series(0.0, hours=240), PRD)
        self.assertAlmostEqual(d, 1.0, places=9)
        self.assertAlmostEqual(remaining_pct(d), 0.0, places=9)

    def test_suhu_konstan_linear_terhadap_waktu(self):
        d = accumulate_decay(constant_series(4.0, hours=24), PRD)
        self.assertAlmostEqual(d, 24 * decay_rate_per_h(4.0, PRD), places=9)

    def test_lebih_hangat_lebih_cepat_rusak(self):
        dingin = accumulate_decay(constant_series(2.0, hours=12), PRD)
        hangat = accumulate_decay(constant_series(10.0, hours=12), PRD)
        self.assertGreater(hangat, dingin)

    def test_data_buffered_tak_berurutan_disisipkan_sesuai_ts(self):
        seri = constant_series(3.0, hours=6)
        acak = list(reversed(seri))
        self.assertAlmostEqual(accumulate_decay(acak, PRD), accumulate_decay(seri, PRD), places=12)

    def test_ts_kembar_tidak_dihitung_ganda(self):
        seri = constant_series(3.0, hours=6)
        self.assertAlmostEqual(accumulate_decay(seri + seri, PRD), accumulate_decay(seri, PRD), places=12)

    def test_pembaruan_inkremental_sama_dengan_hitung_penuh(self):
        seri = constant_series(5.0, hours=8)
        penuh = accumulate_decay(seri, PRD)
        d_awal = accumulate_decay(seri[:25], PRD)
        lanjut = accumulate_decay(seri[24:], PRD, d0=d_awal)   # titik 24 dipakai ulang sebagai jangkar
        self.assertAlmostEqual(lanjut, penuh, places=12)

    def test_kurang_dari_dua_titik_tidak_menambah_kerusakan(self):
        self.assertEqual(accumulate_decay([], PRD), 0.0)
        self.assertEqual(accumulate_decay([(T0, 2.0)], PRD, d0=0.25), 0.25)


class SisaUmurSimpanTest(unittest.TestCase):
    def test_persen_dibatasi_0_sampai_100(self):
        self.assertEqual(remaining_pct(0.0), 100.0)
        self.assertEqual(remaining_pct(-0.1), 100.0)      # tidak melebihi 100 (constraint DB)
        self.assertAlmostEqual(remaining_pct(0.25), 75.0)
        self.assertEqual(remaining_pct(1.7), 0.0)

    def test_sisa_jam_pada_suhu_saat_ini(self):
        self.assertAlmostEqual(remaining_hours(0.0, 0.0, PRD), 240.0, places=6)
        self.assertAlmostEqual(remaining_hours(0.5, 0.0, PRD), 120.0, places=6)
        self.assertEqual(remaining_hours(1.2, 4.0, PRD), 0.0)

    def test_proyeksi_60_menit_lebih_rendah_bila_suhu_prediksi_naik(self):
        now = remaining_pct(0.10)
        stabil = project_remaining_pct(0.10, 2.0, [(30, 2.0), (60, 2.0)], PRD)
        naik = project_remaining_pct(0.10, 2.0, [(30, 6.0), (60, 10.0)], PRD)
        self.assertLess(stabil, now)
        self.assertLess(naik, stabil)

    def test_proyeksi_suhu_konstan_cocok_dengan_integrasi_langsung(self):
        d_60 = accumulate_decay(constant_series(4.0, hours=1, step_min=30), PRD, d0=0.10)
        proyeksi = project_remaining_pct(0.10, 4.0, [(30, 4.0), (60, 4.0)], PRD)
        self.assertAlmostEqual(proyeksi, remaining_pct(d_60), places=9)


class MeanKineticTemperatureTest(unittest.TestCase):
    """Uji mkt_c (PRD §13.3, USP GC 1079.2)."""

    EA = PRD.ea_j_per_mol  # 60.000 J/mol, sama dengan parameter baku ikan segar

    def test_suhu_konstan_mkt_sama_dengan_suhu_itu(self):
        for temp in (0.0, 2.0, 4.0, -1.5, 10.0):
            with self.subTest(temp=temp):
                self.assertAlmostEqual(mkt_c([temp] * 20, self.EA), temp, places=6)

    def test_mkt_selalu_lebih_tinggi_atau_sama_dengan_rata_rata_aritmetik(self):
        # Ketaksamaan Jensen: exp(-1/T) cembung terhadap T, jadi MKT >= mean.
        kasus = [
            [0.0, 4.0],
            [-2.0, 0.0, 2.0, 8.0],
            [0.0, 0.0, 0.0, 15.0],          # satu lonjakan tajam, sisanya dingin
            [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        ]
        for suhu in kasus:
            with self.subTest(suhu=suhu):
                rata2 = sum(suhu) / len(suhu)
                self.assertGreaterEqual(mkt_c(suhu, self.EA), rata2 - 1e-9)

    def test_mkt_sama_dengan_rata_rata_hanya_saat_suhu_konstan(self):
        konstan = mkt_c([3.0] * 10, self.EA)
        fluktuatif = mkt_c([1.0, 3.0, 5.0] * 4, self.EA)
        self.assertAlmostEqual(konstan, 3.0, places=6)
        self.assertGreater(fluktuatif, 3.0)   # rata-rata aritmetiknya juga 3.0

    def test_rentang_lebih_lebar_membuat_selisih_mkt_vs_rata_rata_makin_besar(self):
        sempit = [1.0, 3.0] * 10
        lebar = [-5.0, 9.0] * 10              # rata-rata aritmetik sama (2.0)
        rata2 = 2.0
        selisih_sempit = mkt_c(sempit, self.EA) - rata2
        selisih_lebar = mkt_c(lebar, self.EA) - rata2
        self.assertGreater(selisih_lebar, selisih_sempit)

    def test_menerima_pasangan_ts_temp_sama_seperti_accumulate_decay(self):
        seri = constant_series(4.0, hours=6)                      # list[(ts, temp)]
        hanya_suhu = [c for _, c in seri]
        self.assertAlmostEqual(mkt_c(seri, self.EA), mkt_c(hanya_suhu, self.EA), places=9)

    def test_tidak_bergantung_urutan_atau_jarak_antar_waktu(self):
        # Berbeda dari accumulate_decay (trapesium), MKT hanya fungsi himpunan
        # nilai suhu — mengacak urutan tidak mengubah hasil.
        suhu = [0.0, 1.0, 2.0, 10.0, 3.0]
        import random
        acak = suhu[:]
        random.Random(42).shuffle(acak)
        self.assertAlmostEqual(mkt_c(suhu, self.EA), mkt_c(acak, self.EA), places=9)

    def test_satu_pembacaan_mkt_sama_dengan_suhu_itu(self):
        self.assertAlmostEqual(mkt_c([2.7], self.EA), 2.7, places=9)

    def test_readings_kosong_ditolak(self):
        with self.assertRaises(ValueError):
            mkt_c([], self.EA)

    def test_suhu_di_bawah_nol_mutlak_ditolak(self):
        with self.assertRaises(ValueError):
            mkt_c([-300.0, 2.0], self.EA)

    def test_ea_lebih_besar_membuat_mkt_lebih_tinggi_pada_suhu_fluktuatif(self):
        # Semakin besar Ea, semakin sensitif reaksi terhadap puncak suhu tinggi,
        # sehingga MKT makin jauh di atas rata-rata (konsisten dengan §13.1).
        suhu = [0.0, 1.0, 20.0]
        mkt_rendah = mkt_c(suhu, ea_j_per_mol=40_000.0)
        mkt_tinggi = mkt_c(suhu, ea_j_per_mol=90_000.0)
        rata2 = sum(suhu) / len(suhu)
        self.assertGreater(mkt_tinggi - rata2, mkt_rendah - rata2)


class ParameterTest(unittest.TestCase):
    def test_from_product_membaca_kolom_tabel_products(self):
        p = KineticParams.from_product(
            {"ea_j_per_mol": 60000.0, "t_ref_k": 273.15, "shelf_life_ref_h": 240.0}
        )
        self.assertEqual(p, PRD)

    def test_parameter_tidak_valid_ditolak(self):
        with self.assertRaises(ValueError):
            KineticParams(ea_j_per_mol=0)
        with self.assertRaises(ValueError):
            rate_factor(-300.0, PRD)


if __name__ == "__main__":
    unittest.main()
