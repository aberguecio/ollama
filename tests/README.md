# LiteLLM Model Benchmarks

Framework estandarizado para evaluar modelos LLM a través de LiteLLM. Permite testear la capacidad de los modelos para generar código Python correcto que resuelva problemas específicos.

## 🏗️ Estructura del Framework

```
tests/
├── framework/              # Framework base reutilizable
│   ├── base_benchmark.py   # Clase base con funcionalidad común
│   ├── config.py          # Configuración compartida (API, modelos)
│   └── runner.py          # Runner para múltiples benchmarks
├── benchmarks/            # Benchmarks específicos
│   ├── pi_benchmark.py    # Test de cálculo de dígitos de Pi
│   └── primes_benchmark.py # Test de números primos
├── results/               # Resultados de ejecuciones
├── run_all.py            # Script principal
└── README.md             # Esta documentación
```

## 🎯 Benchmarks Disponibles

### 1. Pi Benchmark (`pi`)
- **Objetivo**: Generar código que calcule dígitos de Pi con precisión
- **Entrada**: Solicitud para calcular N dígitos de Pi
- **Validación**: Compara dígitos generados con valores correctos
- **Métricas**:
  - Dígitos correctos generados
  - Porcentaje de precisión
  - Posición del primer error
  - Tiempo de ejecución

### 2. Primes Benchmark (`primes`)
- **Objetivo**: Generar código que encuentre el N-ésimo número primo
- **Entrada**: Solicitud para encontrar el primo #98,765 (esperado: 1,282,213)
- **Validación**: Verifica que el resultado sea exactamente correcto
- **Métricas**:
  - Valor obtenido vs esperado
  - Diferencia numérica
  - Tiempo de ejecución
  - Éxito/fallo binario

### 3. Palindromes Benchmark (`palindromes`)
- **Objetivo**: Encontrar el único primo que es suma de dígitos de n³, donde n no es palíndromo pero n² sí
- **Entrada**: Solicitud para encontrar ese primo único (esperado: 37)
- **Condiciones**: n entre 1 y 1,000,000, n no es palíndromo, n² es palíndromo
- **Validación**: Verifica que el primo encontrado sea exactamente correcto
- **Métricas**:
  - Primo obtenido vs esperado (37)
  - Diferencia numérica
  - Tiempo de ejecución
  - Éxito/fallo binario

## 🚀 Uso Rápido

### Ejecutar todos los benchmarks
```bash
cd tests/
python run_all.py
```

### Ejecutar benchmarks específicos
```bash
# Solo el benchmark de Pi
python run_all.py -b pi

# Solo números primos
python run_all.py -b primes

# Solo palíndromos
python run_all.py -b palindromes

# Múltiples benchmarks específicos
python run_all.py -b pi primes palindromes
```

### Probar modelos específicos
```bash
# Solo probar un modelo
python run_all.py -m "qwen3.5:35b"

# Probar varios modelos específicos
python run_all.py -m "qwen3.5:35b" "gemma4:26b"
```

### Cambiar directorio de resultados
```bash
python run_all.py -o mi_experimento
```

### Ver información disponible
```bash
# Listar benchmarks disponibles
python run_all.py --list-benchmarks

# Listar modelos configurados
python run_all.py --list-models
```

## 📊 Métricas Reportadas

Para todos los benchmarks se miden:

- **Tokens por segundo (T/s)**: Velocidad de generación
- **Time to First Token (TTFT)**: Latencia inicial
- **Tokens totales**: Prompt + completion tokens
- **Tiempo total**: Duración completa de la llamada
- **Tiempo de ejecución**: Cuánto tarda en ejecutar el código generado
- **Correctitud**: Si el código produce el resultado esperado

## 🔧 Configuración

### Archivo `framework/config.py`

```python
# URL de tu instancia LiteLLM
API_URL = "https://ai-api.berguecio.cl/v1"

# Modelos a probar (orden: más grandes primero)
MODELS = [
    ("qwen3.5:35b", "qwen3.5:35b-a3b"),    # (litellm_name, ollama_name)
    ("gemma4:26b", "gemma4:26b"),
    # ... más modelos
]
```

### API Key
El framework busca la API key en este orden:
1. Variable de entorno `LITELLM_MASTER_KEY`
2. Archivo `.env` en la raíz del proyecto
3. Fallback hardcoded en config.py (⚠️ reemplazar por tu key real)

### Configurar modelos Docker
Ajusta `OLLAMA_CONTAINER` si tu contenedor Ollama tiene otro nombre.

## 📁 Resultados

### Archivos generados
- `results/session_YYYYMMDD_HHMMSS.json`: Resumen de toda la sesión
- `results/pi_benchmark_YYYYMMDD_HHMMSS.json`: Resultados detallados del benchmark Pi
- `results/primes_benchmark_YYYYMMDD_HHMMSS.json`: Resultados detallados del benchmark Primes

### Formato de resultados
```json
{
  "benchmark": "pi",
  "timestamp": "20260406_123456",
  "question": "Write a Python script that computes...",
  "results": [
    {
      "model": "qwen3.5:35b",
      "total_time_s": 15.4,
      "ttft_s": 0.8,
      "tokens_per_second": 45.2,
      "total_tokens": 650,
      "validation": {
        "ran": true,
        "correct": true,
        "digits_generated": 1000,
        "correct_digits": 1000,
        "accuracy_pct": 100.0
      }
    }
  ]
}
```

## 🔬 Extender el Framework

### Crear un nuevo benchmark

1. **Crear clase del benchmark** en `benchmarks/mi_benchmark.py`:

```python
from ..framework.base_benchmark import BaseBenchmark

class MiBenchmark(BaseBenchmark):
    def __init__(self):
        super().__init__("MiBenchmark")

    def get_question(self) -> str:
        return "Escribe un script que..."

    def validate_result(self, code: str, output: str) -> dict:
        # Tu lógica de validación
        return {
            "ran": True,
            "correct": output == "esperado",
            "custom_metric": 123
        }
```

2. **Registrar en el runner** (`run_all.py`):

```python
from benchmarks.mi_benchmark import MiBenchmark

available_benchmarks = {
    "pi": PiBenchmark(),
    "primes": PrimesBenchmark(),
    "mi_test": MiBenchmark(),  # ← Agregar aquí
}
```

### Personalizar métricas

Sobrescribe `_print_validation_result()` y `_print_summary()` para mostrar métricas específicas:

```python
def _print_validation_result(self, validation: dict):
    if validation.get("correct"):
        print(f"  ✓ Mi métrica: {validation['custom_metric']}")
    else:
        print(f"  ✗ Falló con valor: {validation.get('value', 'N/A')}")
```

## 🛠️ Desarrollo

### Ejecutar un benchmark individual
```python
from benchmarks.pi_benchmark import PiBenchmark
from framework.config import MODELS

benchmark = PiBenchmark(target_digits=100)  # Menos dígitos para pruebas
result = benchmark.run_benchmark(MODELS[:2])  # Solo 2 modelos
```

### Debugging
- Los scripts generados se ejecutan en archivos temporales
- Timeout configurable en `framework/config.py`
- Logs detallados durante la ejecución

## ⚠️ Consideraciones

### Rendimiento
- Los benchmarks descargan modelos de memoria entre ejecuciones
- Pausa configurable entre modelos (`INTER_MODEL_DELAY`)
- Timeout para scripts generados (`EXECUTION_TIMEOUT`)

### Seguridad
- Los scripts generados se ejecutan en el entorno local
- Solo ejecuta código Python sin imports (configurado en prompts)
- Timeout para prevenir bucles infinitos

### Limitaciones
- Requiere Docker con Ollama para descarga de modelos
- Específico para LiteLLM API
- Los benchmarks actuales requieren cálculos CPU intensivos

## 📈 Interpretación de Resultados

### Métricas clave por benchmark:

**Pi Benchmark**:
- `correct_digits`: Número de dígitos correctos calculados
- `accuracy_pct`: Porcentaje de precisión del cálculo
- `first_error_pos`: Posición donde aparece el primer error

**Primes Benchmark**:
- `correct`: Boolean si encontró el primo correcto
- `value` vs `expected`: Valor obtenido vs esperado
- `difference`: Diferencia numérica con el valor correcto

**Palindromes Benchmark**:
- `correct`: Boolean si encontró el primo correcto
- `value` vs `expected`: Primo obtenido vs esperado (37)
- `difference`: Diferencia numérica con el primo correcto

### Patrones típicos:
- **Modelos grandes**: Mejor precisión, menor velocidad
- **Modelos pequeños**: Mayor velocidad, menor precisión
- **TTFT alto**: Modelo cargándose o servidor ocupado
- **Timeout**: Código ineficiente o bucle infinito

## 🤝 Contribuir

1. Fork del repositorio
2. Crear nueva rama para tu benchmark/mejora
3. Seguir la estructura del framework
4. Añadir tests para tu nuevo benchmark
5. Actualizar documentación
6. Pull request

¡Los nuevos benchmarks son bienvenidos! Ideas: sorting algorithms, fibonacci, string parsing, data structures, etc.