#!/usr/bin/env python3
"""
LiteLLM Benchmarks Runner
Ejecuta todos los benchmarks disponibles contra los modelos configurados.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Any

# Agregar el directorio actual al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar configuración y benchmarks
from framework.config import MODELS
from benchmarks.pi_benchmark import PiBenchmark
from benchmarks.primes_benchmark import PrimesBenchmark
from benchmarks.palindromes_benchmark import PalindromesBenchmark


def run_all_benchmarks(
    models: List[tuple] = None,
    benchmarks: List[str] = None,
    output_dir: str = "results"
) -> Dict[str, Any]:
    """
    Ejecuta todos los benchmarks especificados contra los modelos dados.

    Args:
        models: Lista de tuplas (litellm_name, ollama_name). Si None, usa MODELS por defecto.
        benchmarks: Lista de nombres de benchmarks a ejecutar. Si None, ejecuta todos.
        output_dir: Directorio donde guardar resultados

    Returns:
        Dict con resultados de todos los benchmarks
    """
    if models is None:
        models = MODELS

    # Configurar benchmarks disponibles
    available_benchmarks = {
        "pi": PiBenchmark(),
        "primes": PrimesBenchmark(),
        "palindromes": PalindromesBenchmark(),
    }

    # Seleccionar benchmarks a ejecutar
    if benchmarks is None:
        benchmarks_to_run = list(available_benchmarks.keys())
    else:
        benchmarks_to_run = [b for b in benchmarks if b in available_benchmarks]
        if not benchmarks_to_run:
            print(f"ERROR: Ningún benchmark válido especificado. Disponibles: {list(available_benchmarks.keys())}")
            sys.exit(1)

    print(f"\\n{'='*80}")
    print("  LITELLM BENCHMARKS RUNNER")
    print(f"{'='*80}")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Modelos a probar: {len(models)} modelos")
    print(f"  Benchmarks a ejecutar: {len(benchmarks_to_run)} benchmarks")
    print(f"  Lista de benchmarks: {', '.join(benchmarks_to_run)}")
    print(f"{'='*80}")

    session_results = {
        "session_start": datetime.now().isoformat(),
        "models": [{"litellm": m[0], "ollama": m[1]} for m in models],
        "benchmarks": [],
        "summary": {}
    }

    # Ejecutar cada benchmark
    for i, benchmark_name in enumerate(benchmarks_to_run):
        benchmark = available_benchmarks[benchmark_name]

        print(f"\\n\\n🚀 EJECUTANDO BENCHMARK {i+1}/{len(benchmarks_to_run)}: {benchmark_name.upper()}")
        print(f"{'─'*80}")

        try:
            benchmark_result = benchmark.run_benchmark(models)
            session_results["benchmarks"].append(benchmark_result)

            # Breve pausa entre benchmarks
            if i < len(benchmarks_to_run) - 1:
                print(f"\\n⏳ Pausa de 10s antes del siguiente benchmark...")
                time.sleep(10)

        except Exception as e:
            print(f"\\n❌ ERROR ejecutando benchmark {benchmark_name}: {e}")
            session_results["benchmarks"].append({
                "benchmark": benchmark_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    # Generar resumen final
    session_results["session_end"] = datetime.now().isoformat()
    session_results["summary"] = _generate_session_summary(session_results)

    # Guardar resumen de la sesión
    session_file = _save_session_results(session_results, output_dir)

    # Mostrar resumen final
    _print_final_summary(session_results)

    print(f"\\n\\n📁 Resultados de la sesión guardados en: {session_file}")
    print(f"📁 Resultados individuales en directorio: {output_dir}/")

    return session_results


def _generate_session_summary(session_results: Dict[str, Any]) -> Dict[str, Any]:
    """Genera un resumen de la sesión de benchmarks."""
    summary = {
        "total_benchmarks": len(session_results["benchmarks"]),
        "successful_benchmarks": 0,
        "failed_benchmarks": 0,
        "models_tested": len(session_results["models"]),
        "benchmark_results": {}
    }

    for benchmark_result in session_results["benchmarks"]:
        if "error" in benchmark_result:
            summary["failed_benchmarks"] += 1
            continue

        summary["successful_benchmarks"] += 1
        benchmark_name = benchmark_result["benchmark"]

        # Analizar resultados por modelo
        model_stats = {}
        for result in benchmark_result.get("results", []):
            model_name = result.get("model", "unknown")
            validation = result.get("validation", {})

            model_stats[model_name] = {
                "success": not ("error" in result),
                "correct": validation.get("correct", False) if validation.get("ran") else False,
                "tokens_per_second": result.get("tokens_per_second", 0),
                "total_time_s": result.get("total_time_s", 0)
            }

        summary["benchmark_results"][benchmark_name] = model_stats

    return summary


def _save_session_results(session_results: Dict[str, Any], output_dir: str) -> str:
    """Guarda los resultados de toda la sesión."""
    import os
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_file = os.path.join(output_dir, f"session_{timestamp}.json")

    os.makedirs(output_dir, exist_ok=True)

    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_results, f, indent=2)

    return session_file


def _print_final_summary(session_results: Dict[str, Any]):
    """Imprime el resumen final de toda la sesión."""
    summary = session_results["summary"]

    print(f"\\n\\n{'='*80}")
    print("  RESUMEN FINAL DE LA SESIÓN")
    print(f"{'='*80}")
    print(f"  Total de benchmarks:     {summary['total_benchmarks']}")
    print(f"  Benchmarks exitosos:     {summary['successful_benchmarks']}")
    print(f"  Benchmarks fallidos:     {summary['failed_benchmarks']}")
    print(f"  Modelos probados:        {summary['models_tested']}")

    # Mostrar éxito por benchmark y modelo
    for benchmark_name, models in summary["benchmark_results"].items():
        print(f"\\n  📊 {benchmark_name.upper()} BENCHMARK:")
        successful_models = sum(1 for stats in models.values() if stats["success"] and stats["correct"])
        print(f"    Modelos exitosos: {successful_models}/{len(models)}")

        for model_name, stats in models.items():
            status = "✓" if stats["success"] and stats["correct"] else "✗"
            tps = stats["tokens_per_second"]
            print(f"    {status} {model_name}: {tps:.1f} t/s")

    print(f"{'='*80}")


def main():
    """Función principal con argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Ejecuta benchmarks de LiteLLM")

    parser.add_argument(
        "--benchmarks", "-b",
        nargs="+",
        choices=["pi", "primes", "palindromes"],
        help="Benchmarks específicos a ejecutar (por defecto: todos)"
    )

    parser.add_argument(
        "--models", "-m",
        nargs="+",
        help="Modelos específicos a probar (nombres LiteLLM, por defecto: todos configurados)"
    )

    parser.add_argument(
        "--output", "-o",
        default="results",
        help="Directorio de salida para resultados (por defecto: results)"
    )

    parser.add_argument(
        "--list-benchmarks",
        action="store_true",
        help="Lista benchmarks disponibles y termina"
    )

    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Lista modelos configurados y termina"
    )

    args = parser.parse_args()

    # Mostrar información y terminar si se solicita
    if args.list_benchmarks:
        print("Benchmarks disponibles:")
        print("  pi          - Cálculo de dígitos de Pi")
        print("  primes      - Encontrar el N-ésimo número primo")
        print("  palindromes - Único primo que es suma de dígitos de n³ (con condición palindrómica)")
        return

    if args.list_models:
        print("Modelos configurados:")
        for litellm_name, ollama_name in MODELS:
            print(f"  {litellm_name} -> {ollama_name}")
        return

    # Preparar lista de modelos
    models_to_test = MODELS
    if args.models:
        # Filtrar modelos especificados
        specified_models = set(args.models)
        models_to_test = [m for m in MODELS if m[0] in specified_models]
        if not models_to_test:
            print(f"ERROR: Ningún modelo válido especificado. Use --list-models para ver opciones.")
            sys.exit(1)

    # Ejecutar benchmarks
    try:
        run_all_benchmarks(
            models=models_to_test,
            benchmarks=args.benchmarks,
            output_dir=args.output
        )
    except KeyboardInterrupt:
        print("\\n\\n⏹️  Benchmark interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\\n\\n❌ Error durante la ejecución: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()