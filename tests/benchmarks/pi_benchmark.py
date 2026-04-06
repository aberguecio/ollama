"""
Benchmark específico para el cálculo de dígitos de Pi.
"""

import os
import sys
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.base_benchmark import BaseBenchmark


class PiBenchmark(BaseBenchmark):
    """Benchmark que pide a modelos generar código para calcular dígitos de Pi."""

    def __init__(self, target_digits: int = 1_000):
        super().__init__("Pi")
        self.target_digits = target_digits
        self._load_pi_digits()

    def _load_pi_digits(self):
        """Carga los dígitos correctos de Pi desde el archivo de referencia."""
        pi_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "pi", "pi.txt"
        )
        try:
            with open(pi_file, 'r') as f:
                self.pi_digits = f.read().strip()
        except FileNotFoundError:
            # Fallback con los primeros 1000 dígitos
            self.pi_digits = ("3141592653589793238462643383279502884197169399375"
                             "1058209749445923078164062862089986280348253421170679"
                             "8214808651328230664709384460955058223172535940812848"
                             "1117450284102701938521105559644622948954930381964428"
                             "8109756659334461284756482337867831652712019091456485"
                             "6692346034861045432664821339360726024914127372458700"
                             "6606315588174881520920962829254091715364367892590360"
                             "0113305305488204665213841469519415116094330572703657"
                             "5959195309218611738193261179310511854807446237996274"
                             "9567351885752724891227938183011949129833673362440656"
                             "6430860213949463952247371907021798609437027705392171"
                             "7629317675238467481846766940513200056812714526356082"
                             "7785771342757789609173637178721468440901224953430146"
                             "5495853710507922796892589235420199561121290219608640"
                             "3441815981362977477130996051870721134999999837297804"
                             "9951059731732816096318595024459455346908302642522308"
                             "2533446850352619311881710100031378387528865875332083"
                             "8142061717766914730359825349042875546873115956286388"
                             "2353787593751957781857780532171226806613001927876611"
                             "1959092164201989380952572010654858632788659361533818")

    def get_question(self) -> str:
        """Retorna la pregunta específica para el benchmark de Pi."""
        return (
            f"Write a Python script that computes and prints exactly {self.target_digits} digits of pi.\n"
            "Output must be ONLY the digits, starting with 3, no spaces, no newlines, no labels.\n"
            "Example of valid output: 314159265358979323846...\n"
            "The script must be self-contained and run with no arguments.\n"
            "Output only the Python script, no explanations, no markdown, no code fences."
        )

    def validate_result(self, code: str, output: str) -> Dict[str, Any]:
        """
        Valida que los dígitos calculados sean correctos.

        Returns:
            Dict con información de validación específica para Pi
        """
        if not output:
            return {
                "ran": True,
                "error": "sin output del script",
                "correct": False
            }

        # Verificar que el output sean solo dígitos
        if not output.isdigit():
            return {
                "ran": True,
                "error": f"output no son solo dígitos: {output[:80]}",
                "correct": False
            }

        # Comparar con los dígitos correctos de Pi
        correct_count = 0
        for i, (generated, expected) in enumerate(zip(output, self.pi_digits)):
            if generated == expected:
                correct_count += 1
            else:
                break

        # Calcular métricas de precisión
        digits_generated = len(output)
        accuracy_pct = round(correct_count / len(self.pi_digits) * 100, 4) if self.pi_digits else 0

        return {
            "ran": True,
            "correct": correct_count >= self.target_digits and digits_generated >= self.target_digits,
            "digits_generated": digits_generated,
            "correct_digits": correct_count,
            "accuracy_pct": accuracy_pct,
            "first_error_pos": correct_count if correct_count < digits_generated else None,
            "target_digits": self.target_digits
        }

    def _print_validation_result(self, validation: Dict[str, Any]):
        """Imprime los resultados de validación específicos para Pi."""
        if not validation.get("ran"):
            print(f"  ✗ No se pudo ejecutar: {validation.get('error')}")
            return

        if "error" in validation:
            print(f"  ✗ Error al validar: {validation['error']}")
            return

        print(f"  ✓ Dígitos generados:  {validation['digits_generated']:,}")
        print(f"  ✓ Dígitos correctos:  {validation['correct_digits']:,} ({validation['accuracy_pct']}%)")

        if validation["first_error_pos"] is not None:
            print(f"  ✗ Primer error en posición: {validation['first_error_pos']:,}")

        if validation.get("correct"):
            print("  ✓ BENCHMARK PASADO")
        else:
            print(f"  ✗ BENCHMARK FALLIDO (objetivo: {validation['target_digits']:,} dígitos)")

        if "run_time_s" in validation:
            print(f"  ✓ Tiempo ejecución:   {validation['run_time_s']}s")

    def _print_summary(self, results: list):
        """Imprime el resumen específico para el benchmark de Pi."""
        print(f"\n\n{'═'*60}")
        print("  RESUMEN FINAL - PI BENCHMARK")
        print(f"{'═'*60}")
        print(f"  {'Modelo':<22} {'T/s':>6}  {'TTFT':>6}  {'Tot.tok':>8}  {'Ejecución':>10}  {'Dígitos ok':>10}  {'%':>6}")
        print(f"  {'─'*22} {'─'*6}  {'─'*6}  {'─'*8}  {'─'*10}  {'─'*10}  {'─'*6}")

        for r in results:
            if "error" in r:
                print(f"  {r['model']:<22}  ERROR: {r['error']}")
                continue

            ttft_str = f"{r['ttft_s']}s" if r['ttft_s'] else "N/A"
            v = r.get("validation", {})

            if v.get("ran") and not v.get("error"):
                digits_str = str(v.get('correct_digits', 0))
                pct_str = f"{v.get('accuracy_pct', 0)}%"
                run_str = f"{v.get('run_time_s', 0)}s"
            else:
                digits_str = "ERROR"
                pct_str = "─"
                run_str = "N/A"

            print(
                f"  {r['model']:<22}"
                f"  {r['tokens_per_second']:>5.1f}"
                f"  {ttft_str:>6}"
                f"  {r['total_tokens']:>8}"
                f"  {run_str:>10}"
                f"  {digits_str:>10}"
                f"  {pct_str:>6}"
            )