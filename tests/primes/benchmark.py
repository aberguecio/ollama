#!/usr/bin/env python3
"""
LiteLLM Benchmark — Primes Test
Pide a cada modelo que encuentre todos los primos en 10 segundos
e imprime el conteo. Valida contra la tabla de π(x).
"""

import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

API_URL = "https://ai-api.berguecio.cl/v1"

def _load_api_key() -> str:
    if os.environ.get("LITELLM_MASTER_KEY"):
        return os.environ["LITELLM_MASTER_KEY"]
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("LITELLM_MASTER_KEY="):
                return line.split("=", 1)[1]
    return ""

API_KEY = _load_api_key()

# Orden: más grande primero
MODELS = [
    ("qwen3.5:35b",      "qwen3.5:35b-a3b"),
    ("glm-4.7-flash",    "glm-4.7-flash:q4_K_M"),
    ("ministral-3:14b",  "ministral-3:14b"),
    ("gemma4:26b",       "gemma4:26b"),
    ("gemma4:e4b",       "gemma4:e4b"),
    ("gemma4:e2b",       "gemma4:e2b"),
]

QUESTION = (
    "Write a Python script that finds as many prime numbers as possible in exactly 10 seconds.\n\n"
    "Requirements:\n"
    "- The script must run for exactly 10 seconds, then stop\n"
    "- Output must be exactly two integers separated by a space: COUNT LIMIT\n"
    "  where COUNT is the number of primes found and LIMIT is the largest number checked\n"
    "- Example output: 78498 1000000\n"
    "- Do NOT use any external libraries (no sympy, no gmpy2, etc.)\n"
    "- Use only Python standard library (no imports needed beyond time)\n"
    "- Use an efficient algorithm (Sieve of Eratosthenes recommended)\n"
    "- The script must be self-contained and run with no arguments\n"
    "- Do not print anything other than the two numbers\n\n"
    "Output only the Python script, no explanations, no markdown, no code fences."
)

OLLAMA_CONTAINER = "ollama-prod"

# Tabla de π(x): número de primos <= x
# Fuente: https://primes.utm.edu/howmany.html
PRIME_COUNT_TABLE = {
    10: 4,
    100: 25,
    1_000: 168,
    10_000: 1_229,
    100_000: 9_592,
    1_000_000: 78_498,
    10_000_000: 664_579,
    100_000_000: 5_761_455,
    1_000_000_000: 50_847_534,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def unload_model(ollama_name: str):
    print(f"\n  → Descargando {ollama_name} de memoria...")
    result = subprocess.run(
        ["docker", "exec", OLLAMA_CONTAINER, "ollama", "stop", ollama_name],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        print("  ✓ Modelo descargado")
    else:
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


def extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def validate_primes(output: str) -> dict:
    """Valida el output COUNT LIMIT contra la tabla de π(x)."""
    output = output.strip()
    parts = output.split()
    if len(parts) != 2:
        return {"valid": False, "error": f"output inesperado: '{output}'"}

    try:
        count = int(parts[0])
        limit = int(parts[1])
    except ValueError:
        return {"valid": False, "error": f"no son enteros: '{output}'"}

    # Buscar el valor esperado más cercano en la tabla
    expected = None
    for table_limit, table_count in sorted(PRIME_COUNT_TABLE.items()):
        if limit == table_limit:
            expected = table_count
            break

    result = {
        "valid": True,
        "count": count,
        "limit": limit,
        "expected": expected,
    }

    if expected is not None:
        result["correct"] = count == expected
        result["error_pct"] = round(abs(count - expected) / expected * 100, 4) if expected else None
    else:
        # Limit no está en la tabla — verificamos que esté en rango razonable
        # usando interpolación simple
        result["correct"] = None
        result["note"] = f"límite {limit} no está en la tabla — conteo no verificable exactamente"

    return result


def run_and_validate(code: str) -> dict:
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
        return {"ran": True, "error": f"sin output. stderr: {stderr[:300]}"}

    validation = validate_primes(output)
    return {"ran": True, **validation}


def call_model(litellm_name: str) -> dict:
    print(f"\n{'═'*60}")
    print(f"  Modelo: {litellm_name}")
    print(f"{'═'*60}")
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
                        print(f"  [TTFT: {first_token_at - start:.2f}s]\n")
                    response_text += content
                    print(content, end="", flush=True)

    except Exception as e:
        print(f"\n  ✗ ERROR: {e}")
        return {"model": litellm_name, "error": str(e)}

    end = time.time()
    total_time = end - start
    ttft = (first_token_at - start) if first_token_at else None
    generation_time = (end - first_token_at) if first_token_at else total_time

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

    print(f"\n\n{'─'*40}")
    print(f"  Tiempo total:        {metrics['total_time_s']}s")
    print(f"  Time to first token: {metrics['ttft_s']}s")
    print(f"  Tokens/segundo:      {metrics['tokens_per_second']}")
    print(f"  Completion tokens:   {metrics['completion_tokens']}")

    print(f"\n  → Validando código generado...")
    code = extract_code(response_text)
    validation = run_and_validate(code)
    metrics["validation"] = validation

    if validation.get("ran"):
        if "error" in validation:
            print(f"  ✗ Error: {validation['error']}")
        else:
            print(f"  ✓ Primos encontrados: {validation['count']:,}")
            print(f"  ✓ Limite chequeado:   {validation['limit']:,}")
            if validation.get("expected") is not None:
                status = "✓ CORRECTO" if validation["correct"] else f"✗ INCORRECTO (esperado {validation['expected']:,})"
                print(f"  {status}")
            elif validation.get("note"):
                print(f"  ⚠ {validation['note']}")
    else:
        print(f"  ✗ No se pudo ejecutar: {validation.get('error')}")
    print(f"{'─'*40}")

    return metrics


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not API_KEY:
        print("ERROR: Exportá LITELLM_MASTER_KEY antes de correr el script.")
        sys.exit(1)

    print(f"\nPrimes Benchmark — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {API_URL}")
    print(f"Modelos: {[m[0] for m in MODELS]}\n")

    results = []

    for i, (litellm_name, ollama_name) in enumerate(MODELS):
        result = call_model(litellm_name)
        results.append(result)
        unload_model(ollama_name)
        if i < len(MODELS) - 1:
            print("\n  Esperando 5s antes del siguiente modelo...")
            time.sleep(5)

    # ── Resumen ───────────────────────────────────────────────────────────────
    print(f"\n\n{'═'*60}")
    print("  RESUMEN FINAL")
    print(f"{'═'*60}")
    print(f"  {'Modelo':<22} {'T/s':>6}  {'TTFT':>6}  {'Primos':>10}  {'Correcto':>10}")
    print(f"  {'─'*22} {'─'*6}  {'─'*6}  {'─'*10}  {'─'*10}")
    for r in results:
        if "error" in r:
            print(f"  {r['model']:<22}  ERROR: {r['error']}")
            continue
        v = r.get("validation", {})
        ttft_str = f"{r['ttft_s']}s" if r['ttft_s'] else "N/A"
        if v.get("ran") and "count" in v:
            primes_str = f"{v['count']:,}"
            if v.get("correct") is True:
                correct_str = "✓"
            elif v.get("correct") is False:
                correct_str = "✗"
            else:
                correct_str = "?"
        else:
            primes_str = "ERROR"
            correct_str = "✗"
        print(
            f"  {r['model']:<22}"
            f"  {r['tokens_per_second']:>5.1f}"
            f"  {ttft_str:>6}"
            f"  {primes_str:>10}"
            f"  {correct_str:>10}"
        )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"benchmark_{ts}.json")
    with open(out, "w", encoding="utf-8") as f:
        summary = [{k: v for k, v in r.items() if k != "response"} for r in results]
        json.dump({"timestamp": ts, "question": QUESTION, "results": summary}, f, indent=2)
    print(f"\n  Resultados guardados en: {out}\n")


if __name__ == "__main__":
    main()
