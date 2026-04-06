#!/usr/bin/env python3
"""
LiteLLM Benchmark — Nth Prime Test
Pide a cada modelo que encuentre el primo número N e imprime solo ese número.
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

# ── Parámetros del test ───────────────────────────────────────────────────────

TARGET_N        = 98_765       # Cuál primo buscar (el N-ésimo)
EXPECTED_PRIME  = 1_282_213    # Valor correcto del primo N-ésimo

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
    f"Write a Python script that finds and prints the {TARGET_N}th prime number.\n"
    "Print only the number, no labels, no explanation, no newlines before or after.\n"
    "The script must run with no arguments.\n"
    "Do not import anything — no imports at all.\n"
    "Output only the Python script, no explanations, no markdown, no code fences."
)

OLLAMA_CONTAINER = "ollama-prod"

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


def run_and_validate(code: str) -> dict:
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    print(f"\n  → Ejecutando script generado (60s timeout)...")
    run_start = time.time()
    try:
        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True, text=True, timeout=60
        )
        output = result.stdout.strip()
        stderr = result.stderr.strip()
    except subprocess.TimeoutExpired:
        return {"ran": False, "error": "timeout al ejecutar el script"}
    except Exception as e:
        return {"ran": False, "error": str(e)}
    finally:
        run_elapsed = round(time.time() - run_start, 2)
        os.unlink(tmp_path)

    if not output:
        return {"ran": True, "error": f"sin output. stderr: {stderr[:300]}"}

    try:
        value = int(output)
    except ValueError:
        return {"ran": True, "error": f"output no es un entero: '{output}'", "run_time_s": run_elapsed}

    correct = value == EXPECTED_PRIME
    return {
        "ran": True,
        "value": value,
        "expected": EXPECTED_PRIME,
        "correct": correct,
        "run_time_s": run_elapsed,
    }


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
    print(f"  T/s:                 {metrics['tokens_per_second']}")
    print(f"  Total tokens:        {metrics['total_tokens']}")

    print(f"\n  → Ejecutando y validando código generado...")
    code = extract_code(response_text)
    validation = run_and_validate(code)
    metrics["validation"] = validation

    if validation.get("ran"):
        if "error" in validation:
            print(f"  ✗ Error: {validation['error']}")
        else:
            status = "✓ CORRECTO" if validation["correct"] else f"✗ INCORRECTO (obtuvo {validation['value']:,}, esperado {validation['expected']:,})"
            print(f"  {status}")
            print(f"  Tiempo de ejecución: {validation['run_time_s']}s")
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
    print(f"Buscando el primo número: {TARGET_N:,}  (esperado: {EXPECTED_PRIME:,})")
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
    print(f"  {'Modelo':<22} {'T/s':>6}  {'TTFT':>6}  {'Tot.tok':>8}  {'Ejecución':>10}  {'Valor':>10}  {'OK':>4}")
    print(f"  {'─'*22} {'─'*6}  {'─'*6}  {'─'*8}  {'─'*10}  {'─'*10}  {'─'*4}")
    for r in results:
        if "error" in r:
            print(f"  {r['model']:<22}  ERROR: {r['error']}")
            continue
        v = r.get("validation", {})
        ttft_str = f"{r['ttft_s']}s" if r['ttft_s'] else "N/A"
        if v.get("ran") and "value" in v:
            val_str  = f"{v['value']:,}"
            ok_str   = "✓" if v.get("correct") else "✗"
            run_str  = f"{v['run_time_s']}s"
        else:
            val_str  = "ERROR"
            ok_str   = "✗"
            run_str  = "N/A"
        print(
            f"  {r['model']:<22}"
            f"  {r['tokens_per_second']:>5.1f}"
            f"  {ttft_str:>6}"
            f"  {r['total_tokens']:>8}"
            f"  {run_str:>10}"
            f"  {val_str:>10}"
            f"  {ok_str:>4}"
        )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"benchmark_{ts}.json")
    with open(out, "w", encoding="utf-8") as f:
        summary = [{k: v for k, v in r.items() if k != "response"} for r in results]
        json.dump({"timestamp": ts, "target_n": TARGET_N, "expected_prime": EXPECTED_PRIME,
                   "question": QUESTION, "results": summary}, f, indent=2)
    print(f"\n  Resultados guardados en: {out}\n")


if __name__ == "__main__":
    main()
