#!/usr/bin/env python3
"""CLI EDA untuk Dataset B — NAB realKnownCause (issue #56, PRD §12.1 & §18.2 ref. 3).

Menghasilkan:
  - ml/reports/dataset_b_eda.md          ringkasan statistik + hasil validasi
  - ml/reports/figures/*.png             plot time series dengan window anomali berlabel

Pakai hanya fungsi murni dari ml/eda/dataset_b.py agar logika inti tetap
testable lewat unittest (lihat ml/eda/tests/test_dataset_b.py); skrip ini
cuma mengurus I/O (baca file, plot, tulis laporan).

Jalankan dari root repo:
    python3 -m ml.scripts.run_eda_dataset_b
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless, tanpa display
import matplotlib.pyplot as plt

from ml.eda.dataset_b import (
    anomaly_window_stats,
    load_anomaly_windows,
    load_nab_series,
    summarize_series,
    validate_series,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "ml" / "data" / "raw" / "nab"
LABELS_PATH = DATA_DIR / "labels" / "combined_windows.json"
REPORTS_DIR = REPO_ROOT / "ml" / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

DATASETS = {
    "machine_temperature_system_failure.csv": "realKnownCause/machine_temperature_system_failure.csv",
    "ambient_temperature_system_failure.csv": "realKnownCause/ambient_temperature_system_failure.csv",
}


def plot_series(name: str, df, windows, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(14, 4.5))
    ax.plot(df["timestamp"], df["value"], linewidth=0.6, color="#2563eb")
    for w in windows:
        ax.axvspan(w.start, w.end, color="#dc2626", alpha=0.15)
    ax.set_title(f"NAB realKnownCause — {name}\n(area merah = window anomali berlabel)")
    ax.set_xlabel("waktu")
    ax.set_ylabel("value (°F, satuan asli NAB)")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def build_report(results: dict) -> str:
    lines = [
        "# EDA Dataset B — NAB realKnownCause (#56)",
        "",
        "Sumber: https://github.com/numenta/NAB — lisensi **MIT** (dicek langsung dari",
        "`LICENSE.txt` di root repo NAB, bukan diasumsikan; catatan sebelumnya yang",
        "menduga AGPL perlu dikoreksi — repo NAB memakai MIT).",
        "",
    ]
    for name, r in results.items():
        s = r["summary"]
        v = r["validation"]
        lines += [
            f"## `{name}`",
            "",
            f"- Baris: **{s.n_rows}** | Rentang waktu: {s.start} s/d {s.end}",
            f"- Interval sampling (median): **{v.interval_minutes:.1f} menit**",
            f"- Duplikat timestamp dibuang: {r['n_duplicates_dropped']}",
            f"- Urut monoton naik: {v.is_monotonic}",
            f"- Gap > 1.5x interval median: **{v.n_gaps}** (gap terbesar: {v.max_gap_minutes:.0f} menit)",
            f"- Nilai (°F): min {s.min_f:.2f}, max {s.max_f:.2f}, mean {s.mean_f:.2f}, std {s.std_f:.2f}",
            f"- Nilai (°C, dikonversi): min {s.min_c:.2f}, max {s.max_c:.2f}, "
            f"mean {s.mean_c:.2f}, std {s.std_c:.2f}",
            "",
            f"### Window anomali berlabel ({len(r['windows'])})",
            "",
        ]
        for w_stat in r["window_stats"]:
            lines.append(
                f"- {w_stat['start']} s/d {w_stat['end']} "
                f"({w_stat['duration_hours']:.1f} jam, {w_stat['n_points']} titik data) — "
                f"nilai min/mean/max (°F): "
                f"{w_stat['min_f']:.2f} / {w_stat['mean_f']:.2f} / {w_stat['max_f']:.2f}"
                if w_stat["n_points"]
                else f"- {w_stat['start']} s/d {w_stat['end']} — **0 titik data** di window ini"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    if not DATA_DIR.exists():
        print(f"ERROR: {DATA_DIR} tidak ditemukan. Unduh dulu sesuai AC #56.", file=sys.stderr)
        return 1

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for filename, nab_key in DATASETS.items():
        csv_path = DATA_DIR / filename
        if not csv_path.exists():
            print(f"ERROR: {csv_path} tidak ditemukan.", file=sys.stderr)
            return 1

        df = load_nab_series(csv_path)
        n_dup = df.attrs.get("n_duplicates_dropped", 0)
        validation = validate_series(df)
        summary = summarize_series(df)

        windows = []
        window_stats = []
        if LABELS_PATH.exists():
            windows = load_anomaly_windows(LABELS_PATH, nab_key)
            window_stats = anomaly_window_stats(df, windows)
        else:
            print(f"WARNING: {LABELS_PATH} tidak ada, lewati pemetaan window anomali.")

        fig_path = FIGURES_DIR / f"{filename.replace('.csv', '')}.png"
        plot_series(filename, df, windows, fig_path)

        results[filename] = {
            "summary": summary,
            "validation": validation,
            "n_duplicates_dropped": n_dup,
            "windows": windows,
            "window_stats": window_stats,
        }

        print(f"[{filename}] {len(df)} baris, interval={validation.interval_minutes:.1f} menit, "
              f"gap={validation.n_gaps}, window anomali={len(windows)} -> {fig_path}")

    report_md = build_report(results)
    report_path = REPORTS_DIR / "dataset_b_eda.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"\nLaporan ditulis ke {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
