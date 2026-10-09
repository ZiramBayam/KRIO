#!/usr/bin/env python3
"""CLI kalibrasi residual + CUSUM pada Dataset B (issue #62, F4).

Membandingkan DUA baseline T_prediksi(t) (keduanya pengganti sementara untuk
model forecast LightGBM sungguhan, issue #58 belum dikerjakan):

  1. persistence   — T_prediksi(t) = T(t-5menit)
  2. moving_average — T_prediksi(t) = rata-rata 1 jam sebelum t

Menghasilkan:
  - ml/reports/dataset_b_calibration.md            ringkasan + perbandingan baseline
  - ml/reports/figures/dataset_b_calibration_<baseline>.png   plot per baseline

Jalankan dari root repo:
    PYTHONPATH=services:. python3 -m ml.scripts.run_calibration_dataset_b
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from alerting.residual import CalibrationParams, detect_events
from alerting.rules import KIND_THRESHOLD
from ml.calibration.dataset_b_baseline import (
    calibrate_k_grid,
    events_outside_windows,
    match_events_to_windows,
    moving_average_predict,
    persistence_predict,
    residual_series,
    validation_residuals,
)
from ml.eda.dataset_b import load_anomaly_windows, load_nab_series

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "ml" / "data" / "raw" / "nab" / "machine_temperature_system_failure.csv"
LABELS_PATH = REPO_ROOT / "ml" / "data" / "raw" / "nab" / "labels" / "combined_windows.json"
NAB_KEY = "realKnownCause/machine_temperature_system_failure.csv"
REPORTS_DIR = REPO_ROOT / "ml" / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

K_GRID = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
MA_WINDOW_STEPS = 12  # 12 x 5 menit = 1 jam


def plot_calibration(df, windows, chosen_events, title: str, out_path: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    ax1.plot(df["timestamp"], df["residual"], linewidth=0.5, color="#2563eb", label="r(t)")
    sigma = df.attrs["sigma_c"]
    ax1.axhline(3 * sigma, color="#dc2626", linestyle="--", linewidth=0.8, label="+3 sigma")
    ax1.axhline(-3 * sigma, color="#dc2626", linestyle="--", linewidth=0.8, label="-3 sigma")
    for w in windows:
        ax1.axvspan(w.start, w.end, color="#f59e0b", alpha=0.12)
    for e in chosen_events:
        color = "#dc2626" if e.kind == KIND_THRESHOLD else "#16a34a"
        ax1.axvline(e.detected_at, color=color, linewidth=1.2, alpha=0.8)
    ax1.set_ylabel("residual (°F)")
    ax1.set_title(title)
    ax1.legend(loc="upper right", fontsize=8)

    cusum_vals = []
    s = 0.0
    k = df.attrs["cusum_k"]
    for r in df["residual"]:
        s = max(0.0, s + r - k)
        cusum_vals.append(s)
    ax2.plot(df["timestamp"], cusum_vals, color="#7c3aed", linewidth=0.7)
    ax2.set_ylabel("CUSUM S(t)")
    ax2.set_xlabel("waktu")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def run_baseline(name: str, df, windows) -> dict:
    val_residuals = validation_residuals(df, windows)
    sigma = statistics.stdev(val_residuals)  # sample stdev (ddof=1), konsisten dgn estimate_sigma()

    grid_results = calibrate_k_grid(df, windows, sigma_c=sigma, k_grid=K_GRID)
    best = max(
        grid_results,
        key=lambda r: (r["n_window_berlabel_tertangkap"], -r["n_kegagalan_pendingin"]),
    )
    chosen_k = best["k"]

    params = CalibrationParams(sigma_c=sigma, cusum_k=chosen_k)
    readings = residual_series(df)
    events = detect_events(readings, params)
    matches = match_events_to_windows(events, windows)

    df = df.copy()
    df.attrs["sigma_c"] = sigma
    df.attrs["cusum_k"] = chosen_k
    fig_path = FIGURES_DIR / f"dataset_b_calibration_{name}.png"
    plot_calibration(
        df,
        windows,
        events,
        title=f"Baseline: {name} — oranye=window berlabel, merah=KEGAGALAN_PENDINGIN terdeteksi",
        out_path=fig_path,
    )

    n_matched = sum(1 for m in matches if m.matched)
    outside = events_outside_windows(events, windows)
    n_critical = sum(1 for e in events if e.kind == KIND_THRESHOLD)
    print(
        f"[{name}] sigma={sigma:.4f} F, k terpilih={chosen_k}, "
        f"{n_matched}/{len(windows)} window tertangkap, {len(events)} event total, "
        f"{len(outside)}/{n_critical} event kritis di LUAR window berlabel"
    )

    return {
        "name": name,
        "sigma": sigma,
        "chosen_k": chosen_k,
        "n_rows": len(df),
        "val_n": len(val_residuals),
        "grid_results": grid_results,
        "events": events,
        "matches": matches,
        "events_outside": outside,
        "fig_path": fig_path,
    }


def render_section(result: dict, windows) -> list[str]:
    name, sigma, chosen_k = result["name"], result["sigma"], result["chosen_k"]
    n_critical = sum(1 for e in result["events"] if e.kind == KIND_THRESHOLD)
    n_door = len(result["events"]) - n_critical
    n_matched = sum(1 for m in result["matches"] if m.matched)

    lines = [
        f"## Baseline: `{name}`",
        "",
        f"- Baris dipakai: {result['n_rows']}",
        f"- Sigma (set validasi, n={result['val_n']}): **{sigma:.4f} °F** "
        f"(ambang 3-sigma = {3 * sigma:.4f} °F)",
        f"- k terpilih: **{chosen_k}** (dari grid {K_GRID})",
        f"- Event: {len(result['events'])} total ({n_critical} KEGAGALAN_PENDINGIN, {n_door} PINTU_DIBUKA)",
        f"- **Window berlabel tertangkap (recall): {n_matched}/{len(windows)}**",
        f"- **Event kritis di LUAR window berlabel manapun: {len(result['events_outside'])}/{n_critical}** "
        "— proxy kasar false-positive; sebagian bisa jadi anomali nyata yang belum dilabeli NAB "
        "(mis. siklus defrost), bukan otomatis kesalahan deteksi, tapi tetap perlu ditinjau manual "
        "sebelum dipakai ke data produksi.",
        "",
        "| k | event kritis | event pintu-dibuka | window tertangkap |",
        "|---|---|---|---|",
    ]
    for row in result["grid_results"]:
        marker = " ← dipilih" if row["k"] == chosen_k else ""
        lines.append(
            f"| {row['k']:.1f} | {row['n_kegagalan_pendingin']} | {row['n_pintu_dibuka']} | "
            f"{row['n_window_berlabel_tertangkap']}/{row['n_window_berlabel_total']}{marker} |"
        )
    lines.append("")
    lines.append("Pencocokan per window:")
    lines.append("")
    for m in result["matches"]:
        status = f"tertangkap ({len(m.matching_events)} event)" if m.matched else "TIDAK tertangkap"
        lines.append(f"- {m.window.start} s/d {m.window.end} — {status}")
    lines.append("")
    lines.append(f"Plot: `ml/reports/figures/{result['fig_path'].name}`")
    lines.append("")
    return lines


def main() -> int:
    if not DATA_PATH.exists() or not LABELS_PATH.exists():
        print(f"ERROR: data/label tidak ditemukan di {DATA_PATH} / {LABELS_PATH}", file=sys.stderr)
        return 1

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    raw = load_nab_series(DATA_PATH)
    windows = load_anomaly_windows(LABELS_PATH, NAB_KEY)

    df_persist = persistence_predict(raw, lag_steps=1)
    df_ma = moving_average_predict(raw, window_steps=MA_WINDOW_STEPS)

    result_persist = run_baseline("persistence", df_persist, windows)
    result_ma = run_baseline("moving_average_1h", df_ma, windows)

    recall_persist = sum(1 for m in result_persist["matches"] if m.matched)
    recall_ma = sum(1 for m in result_ma["matches"] if m.matched)
    winner = result_ma if recall_ma >= recall_persist else result_persist

    lines = [
        "# Kalibrasi Residual + CUSUM — Dataset B (#62, F4)",
        "",
        "**Kedua baseline di bawah ini adalah pengganti sementara untuk model forecast "
        "LightGBM sungguhan (issue #58 belum dikerjakan).** Ambang hasil kalibrasi ini "
        "WAJIB dikalibrasi ulang begitu #58/#60 selesai dan residual sungguhan dari "
        "`forecasts` tersedia — angka di sini adalah bukti bahwa logika deteksi di "
        "`services/alerting/residual.py` bekerja dan tahap kalibrasinya sudah disiapkan, "
        "bukan ambang final untuk produksi.",
        "",
        "## Ringkasan perbandingan baseline",
        "",
        "| Baseline | Sigma (°F) | k | Window tertangkap |",
        "|---|---|---|---|",
        f"| persistence (T(t-5menit)) | {result_persist['sigma']:.4f} | "
        f"{result_persist['chosen_k']} | {recall_persist}/{len(windows)} |",
        f"| moving_average (rata-rata 1 jam) | {result_ma['sigma']:.4f} | "
        f"{result_ma['chosen_k']} | {recall_ma}/{len(windows)} |",
        "",
        f"**Temuan utama:** baseline `persistence` gagal menangkap window anomali yang "
        f"berbentuk drift landai (bukan lonjakan tajam) — begitu suhu berubah, "
        f"T_prediksi(t) langsung 'mengikuti' nilai baru dalam 1 langkah (5 menit), "
        f"sehingga residual kembali kecil meski suhu sebenarnya masih jauh dari kondisi "
        f"normal. Ini BUKAN soal tuning k (lihat grid persistence: hasil identik di semua "
        f"nilai k) — baseline `moving_average` ({MA_WINDOW_STEPS} langkah) mengingat "
        f"kondisi lebih lama sebelum ikut bergeser, sehingga residual tetap elevated "
        f"lebih lama saat drift terjadi. **Baseline yang dipakai untuk hasil akhir: "
        f"`{winner['name']}`** ({recall_persist if winner is result_persist else recall_ma}"
        f"/{len(windows)} window tertangkap).",
        "",
    ]
    lines += render_section(result_persist, windows)
    lines += render_section(result_ma, windows)
    lines += [
        "## Keterbatasan yang perlu ditindaklanjuti",
        "",
        "- Kedua baseline di atas memakai nilai suhu historis itu sendiri, bukan model "
        "forecast — ambang hasil kalibrasi ini adalah titik awal, bukan hasil final. "
        "Begitu #58/#60 selesai, ulangi proses ini dengan residual dari tabel `forecasts`.",
        "- Residual persistence bisa 'bocor' satu langkah lag ke depan dari batas window "
        "berlabel (lihat docstring `ml/calibration/dataset_b_baseline.py`); moving average "
        "punya efek serupa dengan lag lebih panjang.",
        "- Kondisi `PREDICTED_EXCURSION` (prediksi melewati ambang) dan `DEVICE_OFFLINE` "
        "(data > 2x interval) ada di luar cakupan modul ini — `DEVICE_OFFLINE` sudah ada "
        "di `services/alerting/rules.py::evaluate_offline` (memakai ambang tetap 10 menit, "
        "bukan 2x interval per perangkat — perlu diselaraskan terpisah di issue lain), "
        "`PREDICTED_EXCURSION` milik issue #61.",
        "- Integrasi ke `services/alerting/scanner.py` (memanggil `detect_events` dengan "
        "residual dari tabel `forecasts`) sengaja BELUM dikerjakan karena tabel itu masih "
        "kosong (menunggu #58/#60). Fungsi murni di `residual.py` sudah siap dipanggil "
        "begitu sumber prediksi tersedia — tinggal mengganti cara residual dihitung, "
        "bukan menulis ulang state machine-nya.",
        "- Tampilan linimasa pengiriman untuk event ini adalah pekerjaan frontend, di luar scope.",
    ]

    report_path = REPORTS_DIR / "dataset_b_calibration.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nLaporan ditulis ke {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
