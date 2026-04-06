"""
Benchmark específico para encontrar el N-ésimo número primo.
"""

import os
import sys
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.base_benchmark import BaseBenchmark


class PrimesBenchmark(BaseBenchmark):
    """Benchmark que pide a modelos generar código para encontrar el N-ésimo primo."""

    def __init__(self, target_n: int = 98_765, expected_prime: int = 1_282_213):
        super().__init__("Primes")
        self.target_n = target_n
        self.expected_prime = expected_prime

    def get_question(self) -> str:
        """Retorna la pregunta específica para el benchmark de primos."""
        return (
            f"Write a Python script that finds and prints the {self.target_n}th prime number.\n"
            "Print only the number, no labels, no explanation, no newlines before or after.\n"
            "The script must run with no arguments.\n"
            "Do not import anything — no imports at all.\n"
            "Output only the Python script, no explanations, no markdown, no code fences."
        )

    def validate_result(self, code: str, output: str) -> Dict[str, Any]:
        """
        Valida que el primo encontrado sea correcto.

        Returns:
            Dict con información de validación específica para Primos
        """
        if not output:
            return {
                "ran": True,
                "error": "sin output del script",
                "correct": False
            }

        # Intentar convertir el output a entero
        try:
            result_value = int(output.strip())
        except ValueError:
            return {
                "ran": True,
                "error": f"output no es un entero: '{output[:100]}'",
                "correct": False
            }

        # Verificar si el resultado es correcto
        correct = result_value == self.expected_prime

        return {
            "ran": True,
            "correct": correct,
            "value": result_value,
            "expected": self.expected_prime,
            "target_n": self.target_n,
            "difference": result_value - self.expected_prime if not correct else 0
        }

    def _print_validation_result(self, validation: Dict[str, Any]):
        """Imprime los resultados de validación específicos para Primos."""
        if not validation.get("ran"):
            print(f"  ✗ No se pudo ejecutar: {validation.get('error')}")
            return

        if "error" in validation:
            print(f"  ✗ Error al validar: {validation['error']}")
            return

        if validation.get("correct"):
            print(f"  ✓ CORRECTO: {validation['value']:,} (primo #{validation['target_n']:,})")
        else:
            expected = validation['expected']
            actual = validation['value']
            diff = validation.get('difference', 0)
            print(f"  ✗ INCORRECTO: obtuvo {actual:,}, esperado {expected:,} (diferencia: {diff:+,})")

        if "run_time_s" in validation:
            print(f"  ✓ Tiempo ejecución:   {validation['run_time_s']}s")

    def _print_summary(self, results: list):
        """Imprime el resumen específico para el benchmark de Primos."""
        print(f"\n\n{'═'*60}")
        print("  RESUMEN FINAL - PRIMES BENCHMARK")
        print(f"{'═'*60}")
        print(f"  Objetivo: Encontrar el primo #{self.target_n:,} (esperado: {self.expected_prime:,})")
        print(f"{'═'*60}")
        print(f"  {'Modelo':<22} {'T/s':>6}  {'TTFT':>6}  {'Tot.tok':>8}  {'Ejecución':>10}  {'Valor':>12}  {'OK':>4}")
        print(f"  {'─'*22} {'─'*6}  {'─'*6}  {'─'*8}  {'─'*10}  {'─'*12}  {'─'*4}")

        for r in results:
            if "error" in r:
                print(f"  {r['model']:<22}  ERROR: {r['error']}")
                continue

            ttft_str = f"{r['ttft_s']}s" if r['ttft_s'] else "N/A"
            v = r.get("validation", {})

            if v.get("ran") and not v.get("error"):
                val_str = f"{v.get('value', 0):,}"
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
                f"  {val_str:>12}"
                f"  {ok_str:>4}"
            )