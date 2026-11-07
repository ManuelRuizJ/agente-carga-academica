# HANDOFF: Agente de carga académica v3

_Última actualización: 6 de noviembre de 2026._

## 1. Qué es el proyecto

Es el prototipo del **proyecto final de Agentes Inteligentes** (Ibero Puebla). Lo hacen
Jesús Manuel Ruiz Fuentes (195116) y Diana Laura Valencia Barragán.

Es un **Sistema Multiagente** que recomienda una carga académica personalizada. Tiene 4
agentes:
- **AgenteHistorial:** revisa kárdex, prerrequisitos y seriación.
- **AgenteCarga:** arma combinaciones dentro de los límites de créditos.
- **AgenteHorarios:** asigna grupos sin choques e interpreta las preferencias.
- **AgenteManager:** coordina, evalúa y redacta.

Los agentes se coordinan con **Contract Net** en Python puro. Su aporte se audita con
**valores de Shapley** exactos, y usan una **ontología OWL** como base de conocimiento
compartida (owlready2, SPARQL y el razonador HermiT). **CrewAI** es una capa opcional
de orquestación. El LLM local (`llama3.2` en Ollama) solo interpreta lenguaje natural y
redacta la explicación final.

Es la continuación directa del **Proyecto 2**
(`../../parcial-2/Proyecto 2. Arquitectura MAS y capa de transparencia.pdf`). Conserva
sus fichas de agentes, los pesos de evaluación (0.30/0.25/0.25/0.20), la definición de
v(S) y su ontología (`P2_ontologia_carga_academica.owx`, que no se modifica).

## 2. Dónde está y en qué estado

| Cosa | Valor |
|---|---|
| Carpeta | `~/Documentos/universidad/agentes/parcial-3/agente-carga3/` |
| Repositorio | **Propio**, dentro de la carpeta: `github.com/ManuelRuizJ/agente-carga-academica`, rama `main` |
| Último commit | `feb07e2 proyecto carga acedemica version 3` (ya está en `origin/main`) |
| **Sin commit** | `carga/config.py` y `carga/llm.py`, con la protección de batería (ver §5.1) |
| Entorno | `.venv/` con Python **3.12.16** (CrewAI no soporta 3.14). Kernel de Jupyter registrado como `agente-carga3` |
| Prototipo anterior | `../integracion_ontologica.ipynb` (reemplazado; no se tocó). `../venv` está roto: `python`→3.14 y los paquetes están en 3.12 |

> ⚠️ `agente-carga3/` es un repo git **dentro** del repo de la clase
> (`~/Documentos/universidad/agentes`). En ese repo aparece como `?? agente-carga3/`. No
> lo agregues con `git add` desde el repo de la clase: git lo trataría como repo
> incrustado. Decide si lo quieres como submódulo o ignorarlo en el `.gitignore` de la clase.

## 3. Qué ya está hecho

- **La ontología ya tiene individuos.** La del Proyecto 2 solo tenía TBox, y por eso el
  notebook nunca encontraba a `alumno_001`. `datos/semilla.py` → `python main.py poblar`
  genera `ontologia/carga_academica_poblada.owl`: 203 individuos, 27 materias, 35 grupos,
  7 profesores, 3 alumnos (A001, A002, A003), 34 pares `enConflictoCon` y 6 **clases
  definidas** que HermiT clasifica (`MateriaLlave` con `min 2` + `AllDifferent`,
  `MateriaSeriada`, `GrupoVespertino`, `GrupoMatutino`, `GrupoEnLinea`,
  `EstudianteConAdeudo`).
- **Los 4 agentes y el Contract Net** (`cfp`, `propose`, `accept-proposal`,
  `reject-proposal`, con mensajes estilo FIPA). Cada especialista tiene un
  comportamiento experto y uno "ingenuo"; el ingenuo se usa cuando el agente no está
  en la coalición.
- **La función de evaluación del Proyecto 2.** Se le agregó al avance una "cobertura de
  materias urgentes" para que el sistema priorice recursar las reprobadas.
- **Shapley exacto** sobre las 8 coaliciones, en milisegundos. Se verificó a mano para
  A001 (§15.4 de la guía).
- **Trace Collector** (formato de la §3.2 del Proyecto 2). Los resultados se **escriben de
  vuelta en la ontología** (`puedeCursar`, `PropuestaCarga`, `TrazaEjecucion`,
  `valorShapley`) en `salidas/kb_<mat>.owl`.
- **Preferencias en lenguaje natural.** Se parte de las guardadas en la ontología. La
  petición la interpretan unas reglas y, si hay Ollama, el LLM con un JSON Schema
  validado. Se descartan las materias que el alumno no mencionó y las que ya aprobó.
- **Guardias anti-alucinación** en la redacción del LLM: rechazan materias ajenas a la
  propuesta, rangos de días, horas, listas, "solo lunes…" falsos y textos cortados. Si
  rechazan, se usa una plantilla.
- **Modo CrewAI**, secuencial y jerárquico. Las herramientas ejecutan la lógica
  determinista; al coordinador se le entrega el resultado oficial del Contract Net.
- **`iniciar_ollama_cpu.sh`:** Ollama solo con CPU en el puerto 11435, usando los
  modelos de `~/.ollama/models`.
- **Caché del LLM** en `salidas/cache_llm.json`.
- **CLI:** `poblar`, `alumnos`, `diagnostico`, `demo`, `recomendar` y `crew`.
- **Notebook `demo.ipynb`** para la presentación.
- **Documentación:** `README.md` (arquitectura y diagnóstico) y `GUIA_EJECUCION.md`
  (guía paso a paso con salidas reales, ejemplo numérico y solución de problemas).
- **Verificación completa** del 5 de noviembre. Las bitácoras están en
  `salidas/_verificacion/` (00–19); no están en git porque `salidas/` está ignorado.

| Prueba | Resultado |
|---|---|
| Instalación limpia desde `requirements.txt` | ✅ 40 s |
| `demo` (3 alumnos, sin LLM) | ✅ 0.5 s |
| `recomendar --razonador` (HermiT) | ✅ 1.9 s |
| 10 consultas DL Query sobre `kb_A001.owl` | ✅ |
| `demo.ipynb` | ✅ 7 celdas, 0 errores |
| Ollama CPU | ✅ `library=cpu`, VRAM 0 bytes, 2.48 GB de RAM |
| `recomendar` con LLM | ✅ 67 s la primera vez, 0.4 s desde la caché |
| `crew` secuencial / jerárquico | ✅ 4 min / 5 min 20 s, 4 herramientas llamadas |
| Agregar alumno A004 vía `semilla.py` | ✅ (y se revirtió) |

Resultados de referencia para detectar regresiones: `python main.py demo` debe dar
**89.17** (A001), **96.25** (A002) y **84.7** (A003), con Shapley de A001 = 41.91 / 20.43 / 26.83.

## 4. Decisiones tomadas (y por qué)

| Decisión | Motivo |
|---|---|
| **El razonamiento lo hacen Python y la ontología; el LLM solo interpreta y redacta (2 llamadas)** | El prototipo anterior dependía del LLM para todo, con más de 20 llamadas en CPU. Era lento, frágil y, con un modelo de 3B, poco confiable. Ahora la recomendación es correcta aunque el LLM falle |
| **Ollama solo con CPU** (script + `num_gpu: 0`) | El notebook moría con `ROCm error: invalid device function`, porque la Radeon integrada (gfx90c) no tiene soporte de ROCm. CrewAI usa `/v1`, que ignora `num_gpu`, así que la GPU se oculta desde el servidor |
| **Puerto 11435** para el Ollama propio | El servicio de Fedora (11434) no tiene modelos, y así no se toca nada del sistema sin sudo |
| **`llama3.2` (3B)**, no `llama3.1:8b` | El de 8B necesita más de 6 GB y la laptop suele tener 3–5 GB libres |
| **Nuevo `.venv` con Python 3.12** | El `venv` anterior estaba mezclado (3.14/3.12) y CrewAI no soporta 3.14 |
| **La ontología se carga una vez** y se pasa a dataclasses | Antes se recargaba el `.owx` en cada llamada a la herramienta |
| **Las clases definidas** se agregan en la ontología poblada, no en el `.owx` original | Se conserva intacta la TBox entregada en el Proyecto 2 |
| **El evaluador usa siempre la verdad de la ontología** y los agentes ausentes se reemplazan por su versión "ingenua" | Así v(S) mide de verdad el aporte de cada agente; v(∅) = 0 por definición |
| **"Todos los prerrequisitos aprobados" se verifica en Python, no en OWL** | Por el supuesto de mundo abierto, OWL/HermiT no puede deducir "todos aprobados". Se materializa como `puedeCursar` |
| **El LLM no recibe horarios** al redactar | En las pruebas, `llama3.2` inventó "de lunes a viernes 13:00–15:00". Los horarios los muestra la tabla calculada |
| **El coordinador de CrewAI recibe el resultado oficial en su tarea** | En una corrida no llamó a `coordinar_carga` y redactó una carga incorrecta (el guardia la atrapó) |
| **CrewAI secuencial por defecto**, jerárquico como opción | Dan la misma recomendación; el jerárquico es más fiel al Proyecto 2 pero hace más llamadas |
| **Sin LLM cuando la laptop está en batería** (último cambio, ver §5.1) | La laptop se apagó en batería al correr el LLM |

## 5. Hallazgos importantes y problemas conocidos

### 5.1 La causa real de los apagados (cambio más reciente)
- Hubo un apagado la mañana del 6 de noviembre (el boot anterior terminó a las 10:33).
  Después se agregó la detección de energía:
  - `llm.py` tiene `estado_energia()` y `en_bateria()`, que leen `/sys/class/power_supply`.
  - Sin cargador, `ClienteLLM` **desactiva el LLM** y el sistema sigue con reglas. Se
    puede forzar con `LLM_EN_BATERIA=1`.
  - `diagnostico` muestra la fuente, el % y el voltaje de la batería (8.02 V con un
    mínimo de diseño de 7.64 V).
- `config.py`: `HILOS_LLM` bajó de 6 a **4**, para reducir el pico de consumo y la temperatura.
- **Hipótesis actual:** la batería está desgastada, y el pico de consumo de la CPU con el
  LLM hace caer el voltaje bajo el mínimo, lo que apaga la laptop sin dejar log. Esto se
  suma al problema de ROCm, que ya está resuelto con el modo CPU.
- **Pendiente:**
  - [ ] Hacer commit de estos dos archivos.
  - [ ] Actualizar la documentación (la guía todavía muestra `hilos: 6` en §9.3 y no
    menciona la batería).
  - [ ] Probar el camino "en batería". Solo se comprobó `diagnostico` con el cargador
    conectado; el caso "sin cargador" no se ha ejecutado.

### 5.2 Otros puntos
- **Protégé:** abre solo un `kb_*.owl` a la vez. Cada archivo trae los agentes con un
  `valorShapley` distinto y esa propiedad es funcional, así que si mezclas dos, HermiT
  marca la ontología como inconsistente. Es correcto, no es un error del sistema.
- **Los datos son sintéticos**, de `semilla.py`. Hay que decirlo en la entrega.
- En `carga/__pycache__/` aparecen `.pyc` de cpython-314: en algún momento se ejecutó
  con el `python3` del sistema en vez del `.venv`. El núcleo podría funcionar así, pero
  **CrewAI no**. Usa siempre `source .venv/bin/activate`.
- El flag `-q` de `crew` se acepta pero no se usa (CrewAI siempre imprime).
- Se corrigieron durante la verificación: la redacción con horarios inventados, el
  coordinador de CrewAI que no usaba su herramienta y el error de "uno de más" en el
  tamaño de las combinaciones del AgenteCarga.

## 6. Qué falta

Estas son las críticas que un profesor podría hacer, en orden de prioridad (de la
evaluación del 5 de noviembre):

| # | Pendiente | Qué resuelve | Esfuerzo |
|---|---|---|---|
| 0 | **Hacer commit de la protección de batería y sincronizar `README.md` y `GUIA_EJECUCION.md`** | Que el repo refleje lo que corre | Bajo |
| 1 | **Contract Net "real":** 2 o 3 instancias de AgenteCarga con estrategias distintas ("máximo avance", "carga ligera", "prioriza intereses") que compitan con ofertas por el mismo `cfp`; el Manager adjudica | La crítica "es una cadena de pasos, no Contract Net". También hace más interesante a Shapley | Medio |
| 2 | **Experimento comparativo:** MAS contra un LLM solo contra un solo agente, sobre unos 20 alumnos generados. Medir % de propuestas con materias inválidas, choques, puntuación y tiempo, en una tabla | La falta de una sección de resultados medibles | Medio |
| 3 | **Sensibilidad de Shapley:** recalcular φ con otra definición de "ingenuo" y mostrar que el orden de los agentes se mantiene | La crítica "v(S) depende de tu baseline" | Bajo |
| 4 | **Pruebas con pytest:** prerrequisitos, choques, eficiencia de Shapley (Σφ = v(N)) y guardias | "¿Cómo sabes que funciona?" | Bajo |
| 5 | Modo conversacional ("quita Compiladores", "todo en la tarde") que vuelva a lanzar el Contract Net | Que se note más como agente y se luzca en la demo en vivo | Medio |
| — | Revisar la **rúbrica oficial del proyecto final**: nunca se tuvo; solo el PDF del Proyecto 2 y las presentaciones | Confirmar que no falta ningún entregable | — |
| — | Decidir qué hacer con las carpetas vacías `../agente_carga` y `../agente_carga2` y con el `../venv` roto | Limpieza | Bajo |

## 7. Cuál era el siguiente paso

La última conversación terminó con una propuesta **todavía sin respuesta**: implementar
las mejoras **#1 (Contract Net con AgentesCarga en competencia)** y **#2 (experimento
comparativo)**, y redactar la sección de resultados para el reporte.

Orden sugerido al retomar:
1. Commit de `carga/config.py` y `carga/llm.py` (protección de batería).
2. Actualizar la guía (§9.3 `hilos: 4`, nota sobre la batería y `LLM_EN_BATERIA`).
3. Confirmar con el equipo si se hacen la #1 y la #2. Si sí, empezar por la #1, porque
   cambia los valores de Shapley y de las tablas que usaría el experimento.
4. Después de cualquier cambio, volver a correr `python main.py demo` y comparar contra
   los valores de referencia de §3, o actualizarlos a propósito.

## 8. Cómo retomar en 1 minuto

```bash
cd ~/Documentos/universidad/agentes/parcial-3/agente-carga3
source .venv/bin/activate
git status                       # config.py y llm.py modificados (batería)
python main.py diagnostico       # Ollama, RAM y ENERGÍA (conecta el cargador para usar el LLM)
python main.py demo              # debe dar 89.17 / 96.25 / 84.7
./iniciar_ollama_cpu.sh          # otra terminal, solo si se usará el LLM (con cargador)
```

Documentos de referencia: `README.md` (arquitectura), `GUIA_EJECUCION.md` (paso a
paso, ejemplo numérico §15, problemas §16) y `salidas/_verificacion/` (evidencia de
pruebas, solo local).
