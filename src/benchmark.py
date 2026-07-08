"""
Benchmark: DYSOLUTION (loop-based) vs DYSOLUTION2 (sparse-matrix optimized)

Runs both solvers on identical instances at multiple scales and prints a
comparison table of runtime, states explored, pruning %, and incumbent.
"""

import time
import sys
import io
import json
import os

from instance import generate_instance, Paper_Example
from DYSOLUTION import Dynamic_solution
from DYSOLUTION2 import OPT_Dynamic_Solution

# Suppress solver/debug output during benchmarking
import logging

logging.disable(logging.CRITICAL)


def suppress_print(func, *args, **kwargs):
    """Run func with stdout suppressed, return its result."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return func(*args, **kwargs)
    finally:
        sys.stdout = old_stdout


def benchmark_single(instance, time_limit, label):
    """Run both solvers on the same instance and return comparison dict."""

    # --- DYSOLUTION (original, loop-based) ---
    s1 = Dynamic_solution(instance, time_limit)
    t0 = time.perf_counter()
    suppress_print(s1.run_DP)
    t1_runtime = time.perf_counter() - t0

    # --- DYSOLUTION2 (sparse-matrix optimized) ---
    s2 = OPT_Dynamic_Solution(instance, time_limit)
    t0 = time.perf_counter()
    suppress_print(s2.run, use_lower_bound=True)
    t2_runtime = time.perf_counter() - t0

    return {
        "label": label,
        "v1_runtime": t1_runtime,
        "v1_incumbent": s1.incumbent,
        "v1_explored": s1.statistic["n_states_explored"],
        "v1_generated": s1.statistic["n_states_generated"],
        "v1_pruning": s1.statistic["n_pruning"],
        "v1_solver_calls": s1.statistic["n_solver_calls"],
        "v2_runtime": t2_runtime,
        "v2_incumbent": s2.incumbent,
        "v2_explored": s2.statistic["n_states_explored"],
        "v2_generated": s2.statistic["n_states_generated"],
        "v2_pruning": s2.statistic["n_pruning"],
        "v2_solver_calls": s2.statistic["n_solver_calls"],
    }


def pruning_pct(pruned, explored):
    if explored == 0:
        return 0.0
    return pruned / explored * 100


def print_table(results):
    """Pretty-print comparison table."""
    hdr = (
        f"{'Instance':<30} │ {'V1 (loop)':<12} {'V2 (sparse)':<12} {'Speedup':<8} │ "
        f"{'V1 Expl':<10} {'V2 Expl':<10} │ "
        f"{'V1 Prune%':<10} {'V2 Prune%':<10} │ "
        f"{'V1 Inc':<7} {'V2 Inc':<7} │ "
        f"{'Match?':<6}"
    )
    sep = "─" * len(hdr)

    print(sep)
    print(hdr)
    print(sep)

    for r in results:
        speedup = r["v1_runtime"] / r["v2_runtime"] if r["v2_runtime"] > 0 else float("inf")
        v1_prune = pruning_pct(r["v1_pruning"], r["v1_explored"])
        v2_prune = pruning_pct(r["v2_pruning"], r["v2_explored"])

        v1_inc = r["v1_incumbent"] if r["v1_incumbent"] != float("inf") else "∞"
        v2_inc = r["v2_incumbent"] if r["v2_incumbent"] != float("inf") else "∞"
        match = "✅" if r["v1_incumbent"] == r["v2_incumbent"] else "❌"

        print(
            f"{r['label']:<30} │ "
            f"{r['v1_runtime']:>10.4f}s {r['v2_runtime']:>10.4f}s {speedup:>6.2f}x │ "
            f"{r['v1_explored']:>9} {r['v2_explored']:>9} │ "
            f"{v1_prune:>8.1f}% {v2_prune:>8.1f}% │ "
            f"{str(v1_inc):>6} {str(v2_inc):>6} │ "
            f"{match:<6}"
        )
    print(sep)


def main():
    TIME_LIMIT = 100.0  # seconds per solver run

    test_cases = [
        # (label, instance_or_generator)
        ("Paper Example (5i/8o/3r)", Paper_Example()),
        ("Small (10i/8o/5r, B=2)", generate_instance(n_items=10, n_orders=8, n_racks=5, capacity=2)),
        ("Medium (15i/10o/8r, B=2)", generate_instance(n_items=15, n_orders=10, n_racks=8, capacity=2)),
        ("Medium (20i/12o/8r, B=3)", generate_instance(n_items=20, n_orders=12, n_racks=8, capacity=3)),
        ("Large (30i/15o/10r, B=3)", generate_instance(n_items=30, n_orders=15, n_racks=10, capacity=3)),
        ("Large (50i/20o/12r, B=3)", generate_instance(n_items=50, n_orders=20, n_racks=12, capacity=3)),
        ("XLarge (100i/30o/15r, B=3)", generate_instance(n_items=100, n_orders=30, n_racks=15, capacity=3)),
    ]

    print(f"\n{'=' * 80}")
    print("  BENCHMARK: DYSOLUTION (V1 loop) vs DYSOLUTION2 (V2 sparse)")
    print(f"  Time limit per run: {TIME_LIMIT}s")
    print(f"{'=' * 80}\n")

    results = []
    for label, inst in test_cases:
        print(f"  Running: {label} ...", end="", flush=True)
        r = benchmark_single(inst, TIME_LIMIT, label)
        results.append(r)
        speedup = r["v1_runtime"] / r["v2_runtime"] if r["v2_runtime"] > 0 else float("inf")
        print(f" done ({speedup:.2f}x)")

    print()
    print_table(results)

    # Also save raw JSON
    os.makedirs("output", exist_ok=True)
    with open("output/benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nRaw results saved to output/benchmark_results.json")


if __name__ == "__main__":
    main()
