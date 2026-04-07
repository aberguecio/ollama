"""
Benchmark: mayor número de Fibonacci estrictamente menor que la longitud
de la secuencia de Collatz más larga para cualquier n < 1.000.000.

Respuesta esperada: 377
  - La secuencia Collatz más larga para n < 1.000.000 es la de n=837.799, longitud=525
  - El mayor Fibonacci estrictamente menor que 525 es 377 (377 < 525 < 610)
"""

import os
import sys
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.base_benchmark import BaseBenchmark


class FibCollatzBenchmark(BaseBenchmark):
    """
    Benchmark que pide a modelos generar código para encontrar el mayor Fibonacci
    estrictamente menor que la longitud de la secuencia de Collatz más larga
    para cualquier número bajo 1.000.000.
    """

    def __init__(self, limit: int = 1_000_000, expected: int = 377):
        super().__init__("FibCollatz")
        self.limit = limit
        self.expected = expected

    def get_question(self) -> str:
        return (
            f"Write a Python script that finds the largest Fibonacci number strictly less than "
            f"the length of the longest Collatz sequence for any number under {self.limit:,}.\n\n"
            "The Collatz sequence for n: if n is even divide by 2, if odd multiply by 3 and add 1, "
            "repeat until reaching 1. Count every step including the starting number and 1.\n"
            "A Fibonacci sequence starts 1, 1, 2, 3, 5, 8, 13, ...\n"
            "Print only that Fibonacci number, no labels, no explanation, no newlines before or after.\n"
            "The script must run with no arguments.\n"
            "Do not import anything — no imports at all.\n"
            "Output only the Python script, no explanations, no markdown, no code fences."
        )

    def validate_result(self, code: str, output: str) -> Dict[str, Any]:
        if not output:
            return {"ran": True, "error": "sin output del script", "correct": False}

        candidates = [l.strip() for l in output.strip().splitlines() if l.strip().isdigit()]
        try:
            result_value = int(candidates[-1]) if candidates else int(output.strip())
        except ValueError:
            return {
                "ran": True,
                "error": f"output no es un entero: '{output[:100]}'",
                "correct": False,
            }

        correct = result_value == self.expected

        return {
            "ran": True,
            "correct": correct,
            "value": result_value,
            "expected": self.expected,
            "limit": self.limit,
            "difference": result_value - self.expected if not correct else 0,
        }

    def _print_validation_result(self, validation: Dict[str, Any]):
        if not validation.get("ran"):
            print(f"  ✗ No se pudo ejecutar: {validation.get('error')}")
            return

        if "error" in validation:
            print(f"  ✗ Error al validar: {validation['error']}")
            return

        if validation.get("correct"):
            print(
                f"  ✓ CORRECTO: {validation['value']} "
                f"(mayor Fibonacci < longitud Collatz máxima bajo {validation['limit']:,})"
            )
        else:
            expected = validation["expected"]
            actual = validation["value"]
            diff = validation.get("difference", 0)
            print(f"  ✗ INCORRECTO: obtuvo {actual}, esperado {expected} (diferencia: {diff:+})")

        if "run_time_s" in validation:
            print(f"  ✓ Tiempo ejecución:   {validation['run_time_s']}s")

    def _print_summary(self, results: list):
        print(f"\n\n{'═'*60}")
        print("  RESUMEN FINAL - FIB-COLLATZ BENCHMARK")
        print(f"{'═'*60}")
        print(f"  Objetivo: Mayor Fibonacci < longitud Collatz máx (n<{self.limit:,})")
        print(f"  Esperado: {self.expected}")
        print(f"{'═'*60}")
        print(f"  {'Modelo':<22} {'T/s':>6}  {'TTFT':>6}  {'Tot.tok':>8}  {'Ejecución':>10}  {'Valor':>6}  {'OK':>4}")
        print(f"  {'─'*22} {'─'*6}  {'─'*6}  {'─'*8}  {'─'*10}  {'─'*6}  {'─'*4}")

        for r in results:
            if "error" in r:
                print(f"  {r['model']:<22}  ERROR: {r['error']}")
                continue

            ttft_str = f"{r['ttft_s']}s" if r["ttft_s"] else "N/A"
            v = r.get("validation", {})

            if v.get("ran") and not v.get("error"):
                val_str = f"{v.get('value', 0)}"
                ok_str = "✓" if v.get("correct") else "✗"
                run_str = f"{v.get('run_time_s', 0)}s"
            else:
                val_str = "ERROR"
                ok_str = "✗"
                run_str = "N/A"

            print(
                f"  {r['model']:<22}"
                f"  {r['tokens_per_second']:>5.1f}"
                f"  {ttft_str:>6}"
                f"  {r['total_tokens']:>8}"
                f"  {run_str:>10}"
                f"  {val_str:>6}"
                f"  {ok_str:>4}"
            )
