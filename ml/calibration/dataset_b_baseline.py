"""Kalibrasi ambang deteksi residual + CUSUM pada Dataset B (issue #62, F4).

T_prediksi(t) BUKAN model forecast sungguhan (LightGBM, issue #58, belum
dikerjakan) — modul ini memakai baseline persistence sederhana,
T_prediksi(t) = T_terukur(t - lag), sebagai pengganti sementara supaya logika
deteksi di services/alerting/residual.py bisa dikalibrasi dan diuji terhadap
anomali berlabel SEKARANG. Ambang hasil kalibrasi di sini (sigma, k) HARUS
dikalibrasi ulang begitu #58/#60 selesai dan residual sungguhan tersedia —
baseline persistence punya residual rendah secara struktural (nilai bertetangga
sangat mirip), sehingga sigma yang didapat di sini kemungkinan besar lebih
kecil daripada sigma model forecast sungguhan.

Fungsi di sini murni (menerima/mengembalikan pandas Series/DataFrame) agar
testable; I/O dan plotting ada di ml/scripts/run_calibration_dataset_b.py.

## Keterbatasan yang diketahui

Residual persistence "bocor" satu langkah lag ke depan dari batas window
anomali berlabel: titik tepat setelah window berakhir masih memakai nilai DI
DALAM window sebagai T_prediksi, sehingga residualnya tetap besar meski
timestamp-nya sudah di luar window resmi. ``validation_residuals`` menyaring
berdasarkan window asli (tanpa buffer), jadi efek ini membuat estimasi sigma
sedikit lebih besar daripada seharusnya (konservatif, bukan under-estimate) —
diterima sebagai trade-off sementara, bukan cacat tersembunyi.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from alerting.residual import CalibrationParams, ResidualEvent, detect_events, estimate_sigma
from alerting.rules import KIND_THRESHOLD
from ml.eda.dataset_b import AnomalyWindow


def persistence_predict(df: pd.DataFrame, lag_steps: int = 1) -> pd.DataFrame:
    """Tambah kolom ``predicted`` = nilai ``lag_steps`` baris sebelumnya.

    ``df`` harus sudah terurut waktu (lihat ``ml.eda.dataset_b.load_nab_series``).
    Baris pertama sebanyak ``lag_steps`` tidak punya prediksi (NaN) dan dibuang.

    PERINGATAN (dikonfirmasi lewat kalibrasi nyata, lihat laporan): persistence
    "mengikuti" sinyal terlalu cepat untuk anomali bertipe drift lambat yang
    bertahan lama — begitu nilai berubah, residual kembali kecil dalam 1-2
    langkah karena T_prediksi(t) langsung memakai nilai terbaru yang sudah
    berubah. Akibatnya window anomali yang landai (bukan lonjakan tajam) bisa
    TIDAK terdeteksi sama sekali, berapa pun k di-tuning. Lihat
    ``moving_average_predict`` untuk alternatif yang lebih tahan terhadap efek
    ini.
    """
    out = df.copy()
    out["predicted"] = out["value"].shift(lag_steps)
    out["residual"] = out["value"] - out["predicted"]
    return out.dropna(subset=["predicted"]).reset_index(drop=True)


def moving_average_predict(df: pd.DataFrame, window_steps: int) -> pd.DataFrame:
    """Tambah kolom ``predicted`` = rata-rata ``window_steps`` nilai SEBELUM t (tanpa t sendiri).

    Dibanding ``persistence_predict``, baseline ini "mengingat" lebih lama
    sebelum ikut bergeser ke nilai baru, sehingga residual tetap elevated
    lebih lama saat terjadi drift berkepanjangan — lebih cocok untuk menguji
    apakah logika deteksi di ``residual.py`` bekerja ketika diberi sinyal
    residual yang representatif, bukan sekadar menyalahkan tuning k.
    """
    out = df.copy()
    out["predicted"] = out["value"].shift(1).rolling(window=window_steps, min_periods=window_steps).mean()
    out["residual"] = out["value"] - out["predicted"]
    return out.dropna(subset=["predicted"]).reset_index(drop=True)


def is_in_any_window(ts: pd.Timestamp, windows: list[AnomalyWindow]) -> bool:
    return any(w.start <= ts <= w.end for w in windows)


def validation_residuals(df: pd.DataFrame, windows: list[AnomalyWindow]) -> list[float]:
    """Residual di LUAR seluruh window anomali berlabel — dipakai untuk estimasi sigma.

    Ini "set validasi" yang dimaksud AC #62: representasi kondisi normal,
    bukan tercemar oleh periode anomali yang justru ingin dideteksi.
    """
    mask = ~df["timestamp"].apply(lambda ts: is_in_any_window(ts, windows))
    return df.loc[mask, "residual"].tolist()


@dataclass(frozen=True)
class WindowMatch:
    window: AnomalyWindow
    matched: bool
    matching_events: list[ResidualEvent]


def events_outside_windows(events: list[ResidualEvent], windows: list[AnomalyWindow]) -> list[ResidualEvent]:
    """Event KEGAGALAN_PENDINGIN yang TIDAK beririsan window anomali berlabel manapun.

    Dipakai sebagai proxy false-positive kasar: bukan berarti semuanya salah
    (bisa jadi anomali nyata yang belum dilabeli NAB, mis. siklus defrost
    normal yang kebetulan melewati ambang), tapi harus dilaporkan apa adanya,
    bukan disembunyikan di balik angka recall yang bagus.
    """
    return [
        e
        for e in events
        if e.kind == KIND_THRESHOLD
        and not any(e.started_at <= w.end and e.detected_at >= w.start for w in windows)
    ]


def match_events_to_windows(
    events: list[ResidualEvent], windows: list[AnomalyWindow]
) -> list[WindowMatch]:
    """Untuk tiap window berlabel, cek apakah ada event KEGAGALAN_PENDINGIN yang tumpang tindih.

    Dipakai sebagai bukti kalibrasi: idealnya setiap window anomali berlabel
    (durasinya berjam-jam, jauh di atas 20 menit) memunculkan minimal satu
    event KEGAGALAN_PENDINGIN yang beririsan waktu dengannya.
    """
    results = []
    for w in windows:
        matching = [
            e
            for e in events
            if e.kind == KIND_THRESHOLD and e.started_at <= w.end and e.detected_at >= w.start
        ]
        results.append(WindowMatch(window=w, matched=len(matching) > 0, matching_events=matching))
    return results


def residual_series(df: pd.DataFrame) -> list[tuple[datetime, float]]:
    """Ubah DataFrame hasil persistence_predict menjadi list (ts, residual) untuk detect_events."""
    return list(zip(df["timestamp"], df["residual"]))


def calibrate_k_grid(
    df: pd.DataFrame,
    windows: list[AnomalyWindow],
    sigma_c: float,
    k_grid: list[float],
) -> list[dict]:
    """Jalankan detect_events untuk tiap nilai k pada grid, laporkan hasil pencocokan.

    Dipakai untuk memilih k secara empiris, bukan menebak satu nilai lalu
    dianggap final. Hasilnya didokumentasikan apa adanya di laporan markdown,
    termasuk bila beberapa nilai k sama-sama buruk.
    """
    readings = residual_series(df)
    rows = []
    for k in k_grid:
        params = CalibrationParams(sigma_c=sigma_c, cusum_k=k)
        events = detect_events(readings, params)
        n_critical = sum(1 for e in events if e.kind == KIND_THRESHOLD)
        n_door = len(events) - n_critical
        matches = match_events_to_windows(events, windows)
        n_windows_matched = sum(1 for m in matches if m.matched)
        rows.append(
            {
                "k": k,
                "n_events_total": len(events),
                "n_kegagalan_pendingin": n_critical,
                "n_pintu_dibuka": n_door,
                "n_window_berlabel_tertangkap": n_windows_matched,
                "n_window_berlabel_total": len(windows),
            }
        )
    return rows
