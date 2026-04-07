#!/usr/bin/env python3
"""
LiteLLM Benchmarks Runner
Ejecuta todos los benchmarks disponibles contra los modelos configurados.
Orden: por modelo (carga modelo → corre todos los tests → descarga → siguiente modelo)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from framework.config import MODELS
from benchmarks.pi_benchmark import PiBenchmark
from benchmarks.primes_benchmark import PrimesBenchmark
from benchmarks.palindromes_benchmark import PalindromesBenchmark
from benchmarks.nqueens_benchmark import NQueensBenchmark
from benchmarks.fibcollatz_benchmark import FibCollatzBenchmark


AVAILABLE_BENCHMARKS = {
    "pi": PiBenchmark,
    "primes": PrimesBenchmark,
    "palindromes": PalindromesBenchmark,
    "nqueens": NQueensBenchmark,
    "fibcollatz": FibCollatzBenchmark,
}


def run_all_benchmarks(
    models: List[tuple] = None,
    benchmark_names: List[str] = None,
    output_dir: str = "results"
) -> Dict[str, Any]:
    if models is None:
        models = MODELS

    if benchmark_names is None:
        benchmark_names = list(AVAILABLE_BENCHMARKS.keys())
    else:
        benchmark_names = [b for b in benchmark_names if b in AVAILABLE_BENCHMARKS]
        if not benchmark_names:
            print(f"ERROR: Ningún benchmark válido. Disponibles: {list(AVAILABLE_BENCHMARKS.keys())}")
            sys.exit(1)

    # Instanciar benchmarks
    benchmarks = {name: AVAILABLE_BENCHMARKS[name]() for name in benchmark_names}

    print(f"\n{'='*80}")
    print("  LITELLM BENCHMARKS RUNNER")
    print(f"{'='*80}")
    print(f"  Fecha:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Modelos:    {len(models)}")
    print(f"  Benchmarks: {', '.join(benchmark_names)}")
    print(f"  Orden:      por modelo (todos los tests por modelo antes de descargar)")
    print(f"{'='*80}")

    # Estructura de resultados: { benchmark_name: [results...] }
    results_by_benchmark = {name: [] for name in benchmark_names}

    for i, (litellm_name, ollama_name) in enumerate(models):
        print(f"\n\n{'#'*80}")
        print(f"  MODELO {i+1}/{len(models)}: {litellm_name}")
        print(f"{'#'*80}")

        for j, bench_name in enumerate(benchmark_names):
            benchmark = benchmarks[bench_name]
            print(f"\n{'─'*60}")
            print(f"  TEST {j+1}/{len(benchmark_names)}: {bench_name.upper()}")
            print(f"{'─'*60}")

            try:
                result = benchmark.call_model(litellm_name)
                results_by_benchmark[bench_name].append(result)
            except Exception as e:
                print(f"\n  ✗ ERROR: {e}")
                results_by_benchmark[bench_name].append({
                    "model": litellm_name,
                    "error": str(e)
                })

        # Descargar modelo después de todos sus tests
        benchmarks[benchmark_names[0]].unload_model(ollama_name)

        if i < len(models) - 1:
            print(f"\n  Esperando 10s antes del siguiente modelo...")
            time.sleep(10)

    # Guardar resultados por benchmark
    timestamp = datetime.now()
    os.makedirs(output_dir, exist_ok=True)
    saved_files = {}

    for bench_name, results in results_by_benchmark.items():
        benchmark = benchmarks[bench_name]
        benchmark._print_summary(results)
        output_file = benchmark._save_results(results, timestamp)
        saved_files[bench_name] = output_file
        print(f"\n  Resultados guardados en: {output_file}")

    # Resumen final
    _print_final_summary(results_by_benchmark, benchmark_names, benchmarks)

    # Guardar sesión
    session_file = _save_session(results_by_benchmark, models, benchmark_names, timestamp, output_dir)
    print(f"\n\n📁 Sesión guardada en: {session_file}")

    return results_by_benchmark


def _print_final_summary(results_by_benchmark, benchmark_names, benchmarks):
    # Pivot: model_name -> {bench_name: result}
    models_order = []
    all_models = {}
    for bench_name in benchmark_names:
        for r in results_by_benchmark[bench_name]:
            model = r.get("model", "?")
            if model not in all_models:
                all_models[model] = {}
                models_order.append(model)
            all_models[model][bench_name] = r

    B_W = 15  # ancho de cada columna de benchmark
    n_bench = len(benchmark_names)
    total_width = 24 + 7 + 7 + 8 + 9 + n_bench * (B_W + 2) + 8 + 6
    W = max(total_width, 90)

    print(f"\n\n{'='*W}")
    print("  RESUMEN FINAL DE LA SESIÓN — TABLA COMPLETA")
    print(f"{'='*W}")

    # Cabecera
    hdr  = f"  {'Modelo':<24}"
    hdr += f"  {'Avg T/s':>7}"
    hdr += f"  {'TTFT':>6}"
    hdr += f"  {'Gen.s':>7}"
    hdr += f"  {'Tokens':>8}"
    for b in benchmark_names:
        hdr += f"  {b.upper()[:B_W]:^{B_W}}"
    hdr += f"  {'Score':>6}"
    print(hdr)

    sep  = f"  {'─'*24}"
    sep += f"  {'─'*7}"
    sep += f"  {'─'*6}"
    sep += f"  {'─'*7}"
    sep += f"  {'─'*8}"
    for _ in benchmark_names:
        sep += f"  {'─'*B_W}"
    sep += f"  {'─'*6}"
    print(sep)

    for model in models_order:
        bench_results = all_models[model]

        # Agrega métricas de los benchmarks que no fallaron a nivel API
        valid_runs = [r for r in bench_results.values() if "error" not in r]
        tps_list  = [r.get("tokens_per_second", 0) for r in valid_runs]
        ttft_list = [r.get("ttft_s") for r in valid_runs if r.get("ttft_s")]
        gen_list  = [r.get("generation_time_s", 0) for r in valid_runs]
        tok_list  = [r.get("total_tokens", 0) for r in valid_runs]

        avg_tps   = sum(tps_list) / len(tps_list) if tps_list else 0
        avg_ttft  = sum(ttft_list) / len(ttft_list) if ttft_list else None
        total_gen = sum(gen_list)
        total_tok = sum(tok_list)

        ttft_str = f"{avg_ttft:.1f}s" if avg_ttft else "N/A"
        gen_str  = f"{total_gen:.1f}s"

        correct_count = sum(
            1 for r in bench_results.values()
            if r.get("validation", {}).get("correct")
        )
        score_str = f"{correct_count}/{n_bench}"

        line  = f"  {model:<24}"
        line += f"  {avg_tps:>6.1f}"
        line += f"  {ttft_str:>6}"
        line += f"  {gen_str:>7}"
        line += f"  {total_tok:>8,}"

        for b in benchmark_names:
            r = bench_results.get(b)
            if r is None:
                cell = "N/A"
            elif "error" in r:
                cell = "✗ API-ERR"
            else:
                v = r.get("validation", {})
                run_s = v.get("run_time_s", 0)
                if not v.get("ran"):
                    err_short = (v.get("error") or "")[:8]
                    cell = f"✗ {err_short}"
                elif v.get("correct"):
                    cell = f"✓  {run_s}s"
                else:
                    if b == "pi":
                        cd  = v.get("correct_digits", 0)
                        tgt = v.get("target_digits", 1000)
                        cell = f"✗ {cd}/{tgt}"
                    else:
                        val = v.get("value", "?")
                        cell = f"✗ got {val}"
            line += f"  {cell:^{B_W}}"

        line += f"  {score_str:>6}"
        print(line)

    # Fila de totales por benchmark
    print(sep)
    tot_line  = f"  {'TOTALES':<24}  {'':>7}  {'':>6}  {'':>7}  {'':>8}"
    for b in benchmark_names:
        results = results_by_benchmark[b]
        c = sum(1 for r in results if r.get("validation", {}).get("correct"))
        t = len(results)
        e = sum(1 for r in results if "error" in r)
        err_tag = f" {e}err" if e else ""
        cell = f"{c}/{t}{err_tag}"
        tot_line += f"  {cell:^{B_W}}"
    tot_line += f"  {'':>6}"
    print(tot_line)

    print(f"{'='*W}")


def _save_session(results_by_benchmark, models, benchmark_names, timestamp, output_dir):
    ts = timestamp.strftime("%Y%m%d_%H%M%S")
    session_file = os.path.join(output_dir, f"session_{ts}.json")

    session = {
        "timestamp": timestamp.isoformat(),
        "models": [{"litellm": m[0], "ollama": m[1]} for m in models],
        "benchmark_names": benchmark_names,
        "results": {
            name: [{k: v for k, v in r.items() if k != "response"} for r in results]
            for name, results in results_by_benchmark.items()
        }
    }

    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2)

    return session_file


def main():
    parser = argparse.ArgumentParser(description="Ejecuta benchmarks de LiteLLM (por modelo)")

    parser.add_argument("--benchmarks", "-b", nargs="+",
                        choices=list(AVAILABLE_BENCHMARKS.keys()),
                        help="Benchmarks a ejecutar (default: todos)")

    parser.add_argument("--models", "-m", nargs="+",
                        help="Modelos específicos (nombres LiteLLM)")

    parser.add_argument("--output", "-o", default="results",
                        help="Directorio de salida (default: results)")

    parser.add_argument("--list-benchmarks", action="store_true")
    parser.add_argument("--list-models", action="store_true")

    args = parser.parse_args()

    if args.list_benchmarks:
        for name in AVAILABLE_BENCHMARKS:
            print(f"  {name}")
        return

    if args.list_models:
        for litellm_name, ollama_name in MODELS:
            print(f"  {litellm_name} -> {ollama_name}")
        return

    models_to_test = MODELS
    if args.models:
        specified = set(args.models)
        models_to_test = [m for m in MODELS if m[0] in specified]
        if not models_to_test:
            print("ERROR: Ningún modelo válido. Use --list-models para ver opciones.")
            sys.exit(1)

    try:
        run_all_benchmarks(
            models=models_to_test,
            benchmark_names=args.benchmarks,
            output_dir=args.output
        )
    except KeyboardInterrupt:
        print("\n\n  Benchmark interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n  Error durante la ejecución: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
