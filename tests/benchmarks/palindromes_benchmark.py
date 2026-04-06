"""
Benchmark específico para encontrar el único primo que es suma de dígitos de n³.
"""

import os
import sys
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.base_benchmark import BaseBenchmark


class PalindromesBenchmark(BaseBenchmark):
    """
    Benchmark que busca el único primo que es la suma de dígitos de n³,
    donde n (1 ≤ n ≤ 1,000,000) no es palíndromo pero n² sí es palíndromo.
    """

    def __init__(self, max_n: int = 1_000_000, expected_prime: int = 37):
        super().__init__("Palindromes")
        self.max_n = max_n
        self.expected_prime = expected_prime

    def get_question(self) -> str:
        """Retorna la pregunta específica para el benchmark de palíndromos."""
        return (
            f"Write a Python script that finds the only prime number that is also the digit sum of n³, "
            f"for some integer n where 1 ≤ n ≤ {self.max_n:,}, n is not a palindrome, but n² is a palindrome.\n\n"
            "A palindrome reads the same forwards and backwards (e.g., 121, 1331).\n"
            "Print only that prime number, no labels, no explanation, no newlines before or after.\n"
            "The script must run with no arguments.\n"
            "Do not import anything — no imports at all.\n"
            "Output only the Python script, no explanations, no markdown, no code fences."
        )

    def validate_result(self, code: str, output: str) -> Dict[str, Any]:
        """
        Valida que el primo encontrado sea correcto.

        Returns:
            Dict con información de validación específica para Palíndromos
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
            "max_n": self.max_n,
            "difference": result_value - self.expected_prime if not correct else 0
        }

    def _print_validation_result(self, validation: Dict[str, Any]):
        """Imprime los resultados de validación específicos para Palíndromos."""
        if not validation.get("ran"):
            print(f"  ✗ No se pudo ejecutar: {validation.get('error')}")
            return

        if "error" in validation:
            print(f"  ✗ Error al validar: {validation['error']}")
            return

        if validation.get("correct"):
            print(f"  ✓ CORRECTO: {validation['value']} (único primo que es suma de dígitos de n³)")
        else:
            expected = validation['expected']
            actual = validation['value']
            diff = validation.get('difference', 0)
            print(f"  ✗ INCORRECTO: obtuvo {actual}, esperado {expected} (diferencia: {diff:+})")

        if "run_time_s" in validation:
            print(f"  ✓ Tiempo ejecución:   {validation['run_time_s']}s")

    def _print_summary(self, results: list):
        """Imprime el resumen específico para el benchmark de Palíndromos."""
        print(f"\n\n{'═'*60}")
        print("  RESUMEN FINAL - PALINDROMES BENCHMARK")
        print(f"{'═'*60}")
        print(f"  Objetivo: Único primo que es suma de dígitos de n³")
        print(f"  Donde n no es palíndromo pero n² sí (n ≤ {self.max_n:,})")
        print(f"  Primo esperado: {self.expected_prime}")
        print(f"{'═'*60}")
        print(f"  {'Modelo':<22} {'T/s':>6}  {'TTFT':>6}  {'Tot.tok':>8}  {'Ejecución':>10}  {'Primo':>6}  {'OK':>4}")
        print(f"  {'─'*22} {'─'*6}  {'─'*6}  {'─'*8}  {'─'*10}  {'─'*6}  {'─'*4}")

        for r in results:
            if "error" in r:
                print(f"  {r['model']:<22}  ERROR: {r['error']}")
                continue

            ttft_str = f"{r['ttft_s']}s" if r['ttft_s'] else "N/A"
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