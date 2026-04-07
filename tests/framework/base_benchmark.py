"""
Clase base para benchmarks de modelos LLM.
Contiene toda la funcionalidad común, mientras que benchmarks específicos
solo necesitan implementar get_question() y validate_result().
"""

import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any

from .config import (
    API_URL, load_api_key, OLLAMA_CONTAINER,
    DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS, DEFAULT_TIMEOUT,
    EXECUTION_TIMEOUT, INTER_MODEL_DELAY
)


class BaseBenchmark(ABC):
    """Clase base para benchmarks de modelos."""

    def __init__(self, name: str):
        self.name = name
        self.api_key = load_api_key()

    @abstractmethod
    def get_question(self) -> str:
        """Retorna la pregunta/prompt específica para este benchmark."""
        pass

    @abstractmethod
    def validate_result(self, code: str, output: str) -> Dict[str, Any]:
        """
        Valida el resultado del código ejecutado.

        Args:
            code: El código Python extraído
            output: La salida del script cuando se ejecutó

        Returns:
            Dict con resultados de la validación, debe incluir al menos:
            - ran: bool (si se pudo ejecutar)
            - correct: bool (si el resultado es correcto)
            - run_time_s: float (tiempo de ejecución)
        """
        pass

    def extract_code(self, text: str) -> str:
        """Extrae código Python de la respuesta del modelo."""
        # Buscar bloques de código markdown
        match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def run_code(self, code: str) -> Dict[str, Any]:
        """
        Ejecuta el código Python y retorna el resultado.

        Returns:
            Dict con:
            - ran: bool
            - output: str (stdout si successful)
            - error: str (descripción del error si falló)
            - run_time_s: float
        """
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(code)
            tmp_path = f.name

        print(f"\\n  → Ejecutando script generado ({EXECUTION_TIMEOUT}s timeout)...")
        run_start = time.time()

        try:
            result = subprocess.run(
                ["python3", tmp_path],
                capture_output=True, text=True,
                timeout=EXECUTION_TIMEOUT
            )
            output = result.stdout.strip()
            stderr = result.stderr.strip()

            if result.returncode != 0:
                return {
                    "ran": False,
                    "error": f"script failed with code {result.returncode}. stderr: {stderr[:300]}",
                    "run_time_s": round(time.time() - run_start, 2)
                }

            return {
                "ran": True,
                "output": output,
                "run_time_s": round(time.time() - run_start, 2)
            }

        except subprocess.TimeoutExpired:
            return {
                "ran": False,
                "error": "timeout al ejecutar el script",
                "run_time_s": round(time.time() - run_start, 2)
            }
        except Exception as e:
            return {
                "ran": False,
                "error": str(e),
                "run_time_s": round(time.time() - run_start, 2)
            }
        finally:
            os.unlink(tmp_path)

    def unload_model(self, ollama_name: str):
        """Descarga el modelo de RAM usando 'ollama stop'."""
        print(f"\\n  → Descargando {ollama_name} de memoria...")
        try:
            result = subprocess.run(
                ["docker", "exec", OLLAMA_CONTAINER, "ollama", "stop", ollama_name],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print("  ✓ Modelo descargado")
                return

            # Fallback: keep_alive=0 via API interna
            print(f"  ⚠ ollama stop falló ({result.stderr.strip()}), intentando keep_alive=0...")
            subprocess.run(
                ["docker", "exec", OLLAMA_CONTAINER, "curl", "-s", "-X", "POST",
                 "http://localhost:11434/api/generate",
                 "-d", json.dumps({"model": ollama_name, "keep_alive": 0})],
                capture_output=True, text=True, timeout=30
            )
            print("  ✓ Modelo descargado via API")

        except Exception as e:
            print(f"  ✗ No se pudo descargar: {e}")

    def call_model(self, litellm_name: str) -> Dict[str, Any]:
        """Llama al modelo via LiteLLM streaming y mide métricas."""
        print(f"\\n{'═'*60}")
        print(f"  Modelo: {litellm_name}")
        print(f"{'═'*60}")
        print()

        payload = json.dumps({
            "model": litellm_name,
            "messages": [{"role": "user", "content": self.get_question()}],
            "stream": True,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "stream_options": {"include_usage": True},
        }).encode()

        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            f"{API_URL}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "Mozilla/5.0",
            },
        )

        start = time.time()
        first_token_at = None
        response_text = ""
        completion_tokens = 0
        prompt_tokens = 0

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=DEFAULT_TIMEOUT) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data: "):
                        continue
                    line = line[6:]
                    if line == "[DONE]":
                        break
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Tokens de uso (último chunk)
                    if chunk.get("usage"):
                        usage = chunk["usage"]
                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get("completion_tokens", 0)

                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    content = choices[0].get("delta", {}).get("content", "")
                    if content:
                        if first_token_at is None:
                            first_token_at = time.time()
                            ttft = first_token_at - start
                            print(f"  [TTFT: {ttft:.2f}s]\\n")
                        response_text += content
                        print(content, end="", flush=True)

        except Exception as e:
            print(f"\\n  ✗ ERROR: {e}")
            return {"model": litellm_name, "error": str(e)}

        end = time.time()
        total_time = end - start
        ttft = (first_token_at - start) if first_token_at else None
        generation_time = (end - first_token_at) if first_token_at else total_time

        # Estimación si la API no devolvió usage
        if completion_tokens == 0:
            completion_tokens = max(1, int(len(response_text.split()) * 1.3))

        tps = completion_tokens / generation_time if generation_time > 0 else 0

        metrics = {
            "model": litellm_name,
            "total_time_s": round(total_time, 2),
            "ttft_s": round(ttft, 2) if ttft else None,
            "generation_time_s": round(generation_time, 2),
            "tokens_per_second": round(tps, 1),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "response": response_text,
        }

        print(f"\\n\\n{'─'*40}")
        print(f"  Tiempo total:        {metrics['total_time_s']}s")
        print(f"  Time to first token: {metrics['ttft_s']}s")
        print(f"  Tiempo generación:   {metrics['generation_time_s']}s")
        print(f"  Tokens/segundo:      {metrics['tokens_per_second']}")
        print(f"  Prompt tokens:       {metrics['prompt_tokens']}")
        print(f"  Completion tokens:   {metrics['completion_tokens']}")
        print(f"  Total tokens:        {metrics['total_tokens']}")
        preview = response_text[:100].replace('\n', '↵').replace('\r', '')
        ellipsis = '…' if len(response_text) > 100 else ''
        print(f"  Respuesta (100c):    {preview}{ellipsis}")

        # Validar correctitud del código generado
        print("\\n  → Validando código generado...")
        code = self.extract_code(response_text)
        execution_result = self.run_code(code)

        if execution_result["ran"]:
            validation = self.validate_result(code, execution_result["output"])
            validation["run_time_s"] = execution_result["run_time_s"]
        else:
            validation = execution_result

        metrics["validation"] = validation
        self._print_validation_result(validation)
        print(f"{'─'*40}")

        return metrics

    def _print_validation_result(self, validation: Dict[str, Any]):
        """Imprime los resultados de la validación."""
        if not validation.get("ran"):
            print(f"  ✗ No se pudo ejecutar: {validation.get('error')}")
            return

        if "error" in validation:
            print(f"  ✗ Error al validar: {validation['error']}")
            return

        # Los benchmarks específicos pueden sobrescribir este método
        # para mostrar información más detallada
        if validation.get("correct"):
            print("  ✓ CORRECTO")
        else:
            print("  ✗ INCORRECTO")

        if "run_time_s" in validation:
            print(f"  Tiempo ejecución: {validation['run_time_s']}s")

    def run_benchmark(self, models: list) -> Dict[str, Any]:
        """
        Ejecuta el benchmark contra una lista de modelos.

        Args:
            models: Lista de tuplas (litellm_name, ollama_name)

        Returns:
            Dict con metadatos y resultados del benchmark
        """
        if not self.api_key:
            print("ERROR: No se pudo cargar LITELLM_MASTER_KEY.")
            print("Asegurate de que la variable de entorno esté configurada o el archivo .env exista.")
            sys.exit(1)

        timestamp = datetime.now()
        print(f"\\n{self.name} Benchmark — {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API: {API_URL}")
        print(f"Modelos: {[m[0] for m in models]}\\n")

        results = []

        for i, (litellm_name, ollama_name) in enumerate(models):
            result = self.call_model(litellm_name)
            results.append(result)
            self.unload_model(ollama_name)

            if i < len(models) - 1:
                print(f"\\n  Esperando {INTER_MODEL_DELAY}s antes del siguiente modelo...")
                time.sleep(INTER_MODEL_DELAY)

        # Resumen final
        self._print_summary(results)

        # Guardar resultados
        output_file = self._save_results(results, timestamp)
        print(f"\\n  Resultados guardados en: {output_file}\\n")

        return {
            "benchmark": self.name,
            "timestamp": timestamp.isoformat(),
            "results": results,
            "output_file": output_file
        }

    def _print_summary(self, results: list):
        """Imprime el resumen final de resultados."""
        print(f"\\n\\n{'═'*60}")
        print("  RESUMEN FINAL")
        print(f"{'═'*60}")

        # Header con columnas básicas - benchmarks específicos pueden sobrescribir
        print(f"  {'Modelo':<22} {'T/s':>6}  {'TTFT':>6}  {'Tot.tok':>8}  {'Status':>8}")
        print(f"  {'─'*22} {'─'*6}  {'─'*6}  {'─'*8}  {'─'*8}")

        for r in results:
            if "error" in r:
                print(f"  {r['model']:<22}  ERROR: {r['error']}")
                continue

            ttft_str = f"{r['ttft_s']}s" if r['ttft_s'] else "N/A"
            v = r.get("validation", {})

            if v.get("ran") and not v.get("error"):
                status = "✓" if v.get("correct") else "✗"
            else:
                status = "ERROR"

            print(
                f"  {r['model']:<22}"
                f"  {r['tokens_per_second']:>5.1f}"
                f"  {ttft_str:>6}"
                f"  {r['total_tokens']:>8}"
                f"  {status:>8}"
            )

    def _save_results(self, results: list, timestamp: datetime) -> str:
        """Guarda los resultados en un archivo JSON."""
        ts = timestamp.strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(output_dir, f"../results/{self.name.lower()}_benchmark_{ts}.json")

        # Crear directorio de resultados si no existe
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            # No guardamos el texto completo de respuesta por legibilidad
            summary = [{k: v for k, v in r.items() if k != "response"} for r in results]
            json.dump({
                "benchmark": self.name,
                "timestamp": ts,
                "question": self.get_question(),
                "results": summary
            }, f, indent=2)

        return output_file