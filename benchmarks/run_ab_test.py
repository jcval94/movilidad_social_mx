import ast
import csv
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_utils import load_and_process_data, load_and_process_data_uncached

OUT_CSV = ROOT / "benchmarks" / "ab_test_results.csv"
OUT_MD = ROOT / "benchmarks" / "ab_test_report.md"


def section4_static_metrics(source_text: str):
    tree = ast.parse(source_text)
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    duplicate_count = len(funcs) - len(set(funcs))
    return {
        "line_count": len(source_text.splitlines()),
        "function_defs": len(funcs),
        "duplicate_function_defs": duplicate_count,
    }


def benchmark_data_loading(repeats: int = 3):
    # A: baseline (sin cache)
    uncached_times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        _ = load_and_process_data_uncached()
        uncached_times.append(time.perf_counter() - t0)

    # B: refactor (con cache)
    if hasattr(load_and_process_data, "clear"):
        load_and_process_data.clear()

    t0 = time.perf_counter()
    _ = load_and_process_data()
    first_cached = time.perf_counter() - t0

    cached_hit_times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        _ = load_and_process_data()
        cached_hit_times.append(time.perf_counter() - t0)

    return {
        "uncached_avg_s": sum(uncached_times) / len(uncached_times),
        "cached_first_call_s": first_cached,
        "cached_hit_avg_s": sum(cached_hit_times) / len(cached_hit_times),
        "cache_speedup_vs_uncached_x": (sum(uncached_times) / len(uncached_times)) / max(sum(cached_hit_times) / len(cached_hit_times), 1e-9),
    }


def main():
    baseline_source = subprocess.check_output(
        ["git", "show", "HEAD:section4.py"],
        cwd=ROOT,
        text=True,
    )
    refactor_source = (ROOT / "section4.py").read_text(encoding="utf-8")

    baseline_metrics = section4_static_metrics(baseline_source)
    refactor_metrics = section4_static_metrics(refactor_source)
    perf_metrics = benchmark_data_loading(repeats=3)

    rows = [
        ["area", "variant", "metric", "value"],
        ["section4", "A_baseline", "line_count", baseline_metrics["line_count"]],
        ["section4", "A_baseline", "function_defs", baseline_metrics["function_defs"]],
        ["section4", "A_baseline", "duplicate_function_defs", baseline_metrics["duplicate_function_defs"]],
        ["section4", "B_refactor", "line_count", refactor_metrics["line_count"]],
        ["section4", "B_refactor", "function_defs", refactor_metrics["function_defs"]],
        ["section4", "B_refactor", "duplicate_function_defs", refactor_metrics["duplicate_function_defs"]],
        ["data_loading", "A_baseline_uncached", "avg_call_seconds", f"{perf_metrics['uncached_avg_s']:.6f}"],
        ["data_loading", "B_refactor_cached", "first_call_seconds", f"{perf_metrics['cached_first_call_s']:.6f}"],
        ["data_loading", "B_refactor_cached", "cache_hit_avg_seconds", f"{perf_metrics['cached_hit_avg_s']:.6f}"],
        ["data_loading", "B_refactor_cached", "speedup_cache_hit_vs_uncached_x", f"{perf_metrics['cache_speedup_vs_uncached_x']:.2f}"],
    ]

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    report = f"""# Informe AB Testing (Baseline vs Refactor)

## Resumen ejecutivo
- `section4.py` redujo tamaño de **{baseline_metrics['line_count']}** a **{refactor_metrics['line_count']}** líneas.
- Definiciones de función duplicadas pasaron de **{baseline_metrics['duplicate_function_defs']}** a **{refactor_metrics['duplicate_function_defs']}**.
- Carga de datos: promedio baseline sin caché **{perf_metrics['uncached_avg_s']:.4f}s**.
- Carga cacheada: primer llamado **{perf_metrics['cached_first_call_s']:.4f}s**, hit de caché promedio **{perf_metrics['cached_hit_avg_s']:.4f}s**.
- Aceleración en hits de caché: **{perf_metrics['cache_speedup_vs_uncached_x']:.2f}x**.

## Archivos de salida
- CSV de métricas: `benchmarks/ab_test_results.csv`
"""
    OUT_MD.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
