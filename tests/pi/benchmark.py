#!/usr/bin/env python3
"""
LiteLLM Model Benchmark
Testea velocidad, tokens y calidad de respuesta para todos los modelos.
"""

import json
import os
import ssl
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

API_URL = "https://ai-api.berguecio.cl/v1"

def _load_api_key() -> str:
    # 1. Variable de entorno (si ya está exportada correctamente)
    if os.environ.get("LITELLM_MASTER_KEY"):
        return os.environ["LITELLM_MASTER_KEY"]
    # 2. Leer .env del mismo directorio que el script
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("LITELLM_MASTER_KEY="):
                return line.split("=", 1)[1]
    return ""

API_KEY = _load_api_key()

# Orden: más grande primero
MODELS = [
    ("qwen3.5:35b",  "qwen3.5:35b-a3b"),   # (nombre litellm, nombre ollama)
    ("gemma4:26b",   "gemma4:26b"),
    ("gemma4:e4b",   "gemma4:e4b"),
    ("gemma4:e2b",   "gemma4:e2b"),
]

QUESTION = (
    "Write a Python script that computes as many correct digits of pi as possible within a time limit.\n\n"
    "Requirements:\n"
    "- The script must run for exactly 10 seconds, then stop and print the result\n"
    "- Output must be ONLY the digits of pi, starting with 3, no spaces, no newlines, no labels\n"
    "- Example of valid output: 314159265358979323846...\n"
    "- Use arbitrary precision arithmetic (mpmath or decimal module)\n"
    "- Use an efficient algorithm (Chudnovsky recommended)\n"
    "- The script must be self-contained and run with no arguments\n"
    "- Do not print anything other than the digits\n\n"
    "Output only the Python script, no explanations, no markdown, no code fences."
)

OLLAMA_CONTAINER = "ollama-prod"

PI_DIGITS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pi.txt")).read().strip()

# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_code(text: str) -> str:
    """Extrae el código Python del response (remueve markdown si lo hay)."""
    import re
    # Si hay bloque ```python ... ``` o ``` ... ```
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Si no hay markdown, asume que todo es código
    return text.strip()


def run_and_validate(code: str) -> dict:
    """Ejecuta el script generado y valida los dígitos de pi contra pi.txt."""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    print("\n  → Ejecutando script generado (15s timeout)...")
    try:
        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True, text=True, timeout=20
        )
        output = result.stdout.strip()
        stderr = result.stderr.strip()
    except subprocess.TimeoutExpired:
        return {"ran": False, "error": "timeout al ejecutar el script"}
    except Exception as e:
        return {"ran": False, "error": str(e)}
    finally:
        os.unlink(tmp_path)

    if not output:
        return {"ran": True, "error": f"sin output. stderr: {stderr[:200]}"}

    # Validar que el output son solo dígitos
    if not output.isdigit():
        return {"ran": True, "error": f"output no son solo dígitos: {output[:80]}"}

    # Contar dígitos correctos comparando contra pi.txt
    correct = 0
    for a, b in zip(output, PI_DIGITS):
        if a == b:
            correct += 1
        else:
            break

    return {
        "ran": True,
        "digits_output": len(output),
        "correct_digits": correct,
        "correct_pct": round(correct / len(PI_DIGITS) * 100, 4),
        "first_error_pos": correct if correct < len(output) else None,
    }


def unload_model(ollama_name: str):
    """Descarga el modelo de RAM usando 'ollama stop'."""
    print(f"\n  → Descargando {ollama_name} de memoria...")
    result = subprocess.run(
        ["docker", "exec", OLLAMA_CONTAINER, "ollama", "stop", ollama_name],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        print("  ✓ Modelo descargado")
    else:
        # fallback: keep_alive=0 via API interna
        print(f"  ⚠ ollama stop falló ({result.stderr.strip()}), intentando keep_alive=0...")
        try:
            subprocess.run(
                ["docker", "exec", OLLAMA_CONTAINER, "curl", "-s", "-X", "POST",
                 "http://localhost:11434/api/generate",
                 "-d", json.dumps({"model": ollama_name, "keep_alive": 0})],
                capture_output=True, text=True, timeout=30
            )
            print("  ✓ Modelo descargado via API")
        except Exception as e:
            print(f"  ✗ No se pudo descargar: {e}")


def test_model(litellm_name: str) -> dict:
    """Llama al modelo via LiteLLM streaming y mide métricas."""
    print(f"\n{'═'*60}")
    print(f"  Modelo: {litellm_name}")
    print(f"{'═'*60}")
    print(f"  Pregunta: {QUESTION[:80]}...")
    print()

    payload = json.dumps({
        "model": litellm_name,
        "messages": [{"role": "user", "content": QUESTION}],
        "stream": True,
        "temperature": 0.1,
        "max_tokens": 3000,
        "stream_options": {"include_usage": True},
    }).encode()

    ctx = ssl.create_default_context()
    req = urllib.request.Request(
        f"{API_URL}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "User-Agent": "Mozilla/5.0",
        },
    )

    start = time.time()
    first_token_at = None
    response_text = ""
    completion_tokens = 0
    prompt_tokens = 0

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=600) as resp:
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

                # tokens de uso (último chunk)
                if chunk.get("usage"):
                    usage = chunk["usage"]
                    prompt_tokens     = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)

                choices = chunk.get("choices", [])
                if not choices:
                    continue
                content = choices[0].get("delta", {}).get("content", "")
                if content:
                    if first_token_at is None:
                        first_token_at = time.time()
                        ttft = first_token_at - start
                        print(f"  [TTFT: {ttft:.2f}s]\n")
                    response_text += content
                    print(content, end="", flush=True)

    except Exception as e:
        print(f"\n  ✗ ERROR: {e}")
        return {"model": litellm_name, "error": str(e)}

    end = time.time()
    total_time      = end - start
    ttft            = (first_token_at - start) if first_token_at else None
    generation_time = (end - first_token_at)   if first_token_at else total_time

    # Estimación si la API no devolvió usage
    if completion_tokens == 0:
        completion_tokens = max(1, int(len(response_text.split()) * 1.3))

    tps = completion_tokens / generation_time if generation_time > 0 else 0

    metrics = {
        "model":              litellm_name,
        "total_time_s":       round(total_time, 2),
        "ttft_s":             round(ttft, 2) if ttft else None,
        "generation_time_s":  round(generation_time, 2),
        "tokens_per_second":  round(tps, 1),
        "prompt_tokens":      prompt_tokens,
        "completion_tokens":  completion_tokens,
        "total_tokens":       prompt_tokens + completion_tokens,
        "response":           response_text,
    }

    print(f"\n\n{'─'*40}")
    print(f"  Tiempo total:        {metrics['total_time_s']}s")
    print(f"  Time to first token: {metrics['ttft_s']}s")
    print(f"  Tiempo generación:   {metrics['generation_time_s']}s")
    print(f"  Tokens/segundo:      {metrics['tokens_per_second']}")
    print(f"  Prompt tokens:       {metrics['prompt_tokens']}")
    print(f"  Completion tokens:   {metrics['completion_tokens']}")
    print(f"  Total tokens:        {metrics['total_tokens']}")

    # Validar correctitud del código generado
    print(f"\n  → Validando código generado...")
    code = extract_code(response_text)
    validation = run_and_validate(code)
    metrics["validation"] = validation

    if validation.get("ran"):
        if "error" in validation:
            print(f"  ✗ Error al validar: {validation['error']}")
        else:
            print(f"  ✓ Dígitos generados:  {validation['digits_output']}")
            print(f"  ✓ Dígitos correctos:  {validation['correct_digits']} ({validation['correct_pct']}%)")
            if validation["first_error_pos"] is not None:
                print(f"  ✗ Primer error en posición: {validation['first_error_pos']}")
    else:
        print(f"  ✗ No se pudo ejecutar: {validation.get('error')}")
    print(f"{'─'*40}")

    return metrics


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not API_KEY:
        print("ERROR: Exportá LITELLM_MASTER_KEY antes de correr el script.")
        print("  export LITELLM_MASTER_KEY=<tu-key>")
        sys.exit(1)

    print(f"\nLiteLLM Benchmark — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {API_URL}")
    print(f"Modelos: {[m[0] for m in MODELS]}\n")

    results = []

    for i, (litellm_name, ollama_name) in enumerate(MODELS):
        result = test_model(litellm_name)
        results.append(result)
        unload_model(ollama_name)
        if i < len(MODELS) - 1:
            print("\n  Esperando 5s antes del siguiente modelo...")
            time.sleep(5)

    # ── Resumen ───────────────────────────────────────────────────────────────
    print(f"\n\n{'═'*60}")
    print("  RESUMEN FINAL")
    print(f"{'═'*60}")
    print(f"  {'Modelo':<22} {'T/s':>6}  {'TTFT':>6}  {'Total':>7}  {'Tokens':>7}  {'Pi correcto':>12}")
    print(f"  {'─'*22} {'─'*6}  {'─'*6}  {'─'*7}  {'─'*7}  {'─'*12}")
    for r in results:
        if "error" in r:
            print(f"  {r['model']:<22}  ERROR: {r['error']}")
        else:
            ttft_str = f"{r['ttft_s']}s" if r['ttft_s'] else "  N/A"
            v = r.get("validation", {})
            if v.get("ran") and "correct_digits" in v:
                pi_str = f"{v['correct_digits']} ({v['correct_pct']}%)"
            elif v.get("error"):
                pi_str = v["error"][:12]
            else:
                pi_str = "N/A"
            print(
                f"  {r['model']:<22}"
                f"  {r['tokens_per_second']:>5.1f}"
                f"  {ttft_str:>6}"
                f"  {r['total_time_s']:>6.1f}s"
                f"  {r['completion_tokens']:>7}"
                f"  {pi_str:>12}"
            )

    # ── Guardar resultados ────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"benchmark_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        # no guardamos el texto completo de respuesta en el resumen por legibilidad
        summary = [{k: v for k, v in r.items() if k != "response"} for r in results]
        json.dump({"timestamp": ts, "question": QUESTION, "results": summary}, f, indent=2)
    print(f"\n  Resultados guardados en: {out}\n")


if __name__ == "__main__":
    main()
