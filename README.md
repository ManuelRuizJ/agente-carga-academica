# Agente de carga académica v3: MAS con ontología como base de conocimiento

Prototipo final del proyecto de **Agentes Inteligentes** (Ibero Puebla).
Recomienda una carga académica personalizada con 4 agentes (Historial, Carga,
Horarios y Manager). Los agentes se coordinan con **Contract Net**, se
auditan con **valores de Shapley** y usan una **ontología OWL** como base de
conocimiento compartida.

Esta versión reemplaza a `../integracion_ontologica.ipynb` y conserva el diseño
del Proyecto 2: las mismas fichas de agentes, los mismos pesos de evaluación, la
misma función v(S) y la misma ontología.

> **Datos.** El plan de estudios es el **real** de Ingeniería en Sistemas
> Computacionales de la Ibero Puebla (programa 2801): 79 materias con sigla,
> créditos, semestre ideal, horas y seriación, exportadas del portal **Intrauia** e
> importadas con `datos/importar_intrauia.py` → `datos/plan_ibero.json`. Son
> **sintéticos**: la dificultad de cada materia (heurística), la oferta del periodo
> (grupos, horarios, cupos y modalidades, generados de forma reproducible a partir del
> plan real), los profesores, los alumnos y el rango de 24–48 créditos por periodo.

---

## 1. Por qué fallaba el prototipo anterior (y por qué se reiniciaba la laptop)

| Problema encontrado | Evidencia | Solución en v3 |
|---|---|---|
| Ollama intentaba usar la **GPU integrada Radeon (gfx90c)**, que ROCm no soporta | Última celda del notebook: `ROCm error: invalid device function` | `iniciar_ollama_cpu.sh` oculta todas las GPUs y fuerza CPU. Además, cada petición manda `num_gpu: 0` |
| CrewAI usa el endpoint `/v1` de Ollama, que **ignora** `num_gpu` | código de `crewai/llms/providers/openai_compatible` | La GPU se desactiva en el **servidor**, no en la petición |
| La ontología **no tenía individuos** (ni alumnos, ni materias, ni grupos) | `P2_ontologia_carga_academica.owx`: 0 `ClassAssertion` | `datos/semilla.py` + `carga/poblar.py` la pueblan con 452 individuos (con el plan real de Intrauia) |
| La herramienta buscaba `"P2_ontologia_carga_academica (1).owx"`, un archivo que no existe | celda 3 del notebook | Rutas centralizadas en `carga/config.py` |
| Todo el razonamiento dependía del LLM (4 agentes en modo jerárquico, más de 20 llamadas en CPU) | — | El razonamiento lo hacen Python y la ontología (milisegundos). El LLM solo hace **2 llamadas** |
| El `venv` mezclaba Python 3.14 y 3.12 (`python` → 3.14, paquetes en 3.12) | `venv/pyvenv.cfg` | `.venv` nuevo y limpio con Python 3.12 |
| Se recargaba el `.owx` en cada llamada a la herramienta | celda 3 | La ontología se carga una sola vez (0.13 s) |
| La laptop **se apagaba en batería** al correr el LLM | apagado sin log (6 nov); batería a 8.02 V con mínimo de diseño 7.64 V | Sin cargador el LLM se desactiva solo (`LLM_EN_BATERIA=1` lo fuerza) y usa 4 hilos en vez de 6 |

**Recomendaciones para tu laptop** (Ryzen 7 5700U, 14 GB de RAM, sin GPU dedicada):
- Usa `llama3.2` (3B, unos 2.5 GB). Evita `llama3.1:8b`, que necesita más de 6 GB y te dejaría sin RAM.
- Cierra el navegador antes de usar el LLM si `python main.py diagnostico` muestra menos de 3.5 GB libres.
- Usa el LLM **con el cargador conectado**: en batería el pico de consumo puede apagar la laptop. `diagnostico` muestra la fuente de energía.
- El servidor CPU se descarga de la RAM a los 2 minutos sin uso. Para liberarla de inmediato, presiona Ctrl+C.

---

## 2. Instalación

```bash
cd agente-carga3
python3.12 -m venv .venv          # CrewAI todavía no soporta Python 3.14
source .venv/bin/activate
pip install -r requirements.txt
```

Java solo se necesita para `--razonador` (HermiT). Ya lo tienes instalado (OpenJDK 25).

## 3. Uso

```bash
# Terminal 1 (solo si quieres LLM): servidor Ollama SOLO CPU en el puerto 11435
./iniciar_ollama_cpu.sh

# Terminal 2
python main.py diagnostico                   # ¿Ollama en CPU? ¿cuánta RAM libre?
python main.py alumnos                       # A001, A002, A003
python main.py demo                          # los 3 alumnos sin LLM (~3 s)
python main.py experimento                   # mejora 2: compara el MAS contra otros sistemas (~4 s)
python main.py experimento --llm             # ... y contra "LLM solo" (~1.5 min por alumno, con cargador)

python main.py recomendar A001               # preferencias guardadas en la ontología
python main.py recomendar A002 -p "trabajo, quiero pocas materias, en la mañana y sin viernes"
python main.py recomendar A003 -p "quiero adelantar, en línea, me interesa IA" --razonador
python main.py recomendar A001 --sin-llm     # sin Ollama: todo por reglas

python main.py crew A001 -p "me interesa IA" # misma lógica orquestada por CrewAI
python main.py crew A001 --proceso jerarquico
```

**Notebook:** `demo.ipynb` recorre el sistema paso a paso (base de conocimiento →
preferencias → Contract Net → Shapley → HermiT → reporte) y sirve para la
presentación. Ábrelo con el kernel **"agente-carga3 (.venv)"**.

Cada ejecución genera en `salidas/`:

| Archivo | Contenido |
|---|---|
| `reporte_<mat>.md` | Recomendación, horario semanal, tabla de las propuestas del Contract Net, tabla de v(S) y φ de Shapley, mensajes FIPA y trazas |
| `trazas_<mat>.json` | Trace Collector (formato de la sección 3.2 del Proyecto 2) |
| `kb_<mat>.owl` | Ontología con los resultados escritos de vuelta (`puedeCursar`, `PropuestaCarga`, `TrazaEjecucion`, `valorShapley`). Se abre en Protégé |
| `experimento.md` · `experimento.csv` | Mejora 2: tabla comparativa y resultados por alumno y sistema |

Tiempos medidos en tu laptop:

| Modo | Tiempo | Llamadas al LLM |
|---|---|---|
| `demo` / `--sin-llm` | ~3 s (3 alumnos) | 0 |
| `experimento` (20 alumnos, 6 sistemas) | ~4 s | 0 |
| `experimento --llm` | ~1.5 min por alumno | 1 por alumno |
| `recomendar` con LLM | ~30–50 s | 2 (preferencias + redacción) |
| `crew` (secuencial) | varios minutos | ~8 o más |

---

## 4. Arquitectura

```
                 petición en lenguaje natural
                            │
                 ┌──────────▼──────────┐   LLM (CPU)  → JSON validado
                 │   AgenteHorarios    │   reglas     → respaldo sin LLM
                 │ interpretar_prefs   │
                 └──────────┬──────────┘
                            │ preferencias
 ┌──────────────────────────▼──────────────────────────────┐
 │                AgenteManager (Contract Net)             │
 │  cfp ─▶ AgenteHistorial ─propose▶ materias válidas      │
 │  cfp ─▶ CargaAvance       ─propose▶ 2 ofertas ┐         │
 │  cfp ─▶ CargaEquilibrio   ─propose▶ 2 ofertas ├ compiten│
 │  cfp ─▶ CargaPreferencias ─propose▶ 2 ofertas ┘         │
 │  cfp ─▶ AgenteHorarios  ─propose▶ ofertas con grupos    │
 │  evaluar: 0.30·A + 0.25·H + 0.25·C + 0.20·P             │
 │  accept-proposal (ganador) / reject-proposal (resto)    │
 │  inform ◀─ contratista ganador                          │
 │  Shapley exacto: 8 coaliciones de roles                 │
 │                + 8 coaliciones de contratistas          │
 └──────────┬───────────────────────────────┬──────────────┘
            │ lee (owlready2 + SPARQL)       │ escribe resultados
 ┌──────────▼───────────────────────────────▼──────────────┐
 │  Ontología OWL (TBox Proyecto 2 + ABox poblada)         │
 │  clases definidas → HermiT las clasifica                │
 └─────────────────────────────────────────────────────────┘
```

### Qué hace cada agente

| Agente | Comportamiento experto | Comportamiento "ingenuo" (cuando no participa, para Shapley) |
|---|---|---|
| **A: Historial** | Kárdex (vía SPARQL), prerrequisitos, seriación y oferta del periodo. Prioriza materias reprobadas, rezagadas y "llave" | Supone que todo lo ofertado es válido |
| **B: Carga** (3 contratistas que compiten) | Cada uno combina materias dentro de 24–48 créditos y de la meta del alumno, con máx. 2 optativas, y las califica con **su** estrategia: CargaAvance (prioridad académica), CargaEquilibrio (meta y pocas difíciles) o CargaPreferencias (intereses y turno/modalidad). Cada uno oferta sus 2 mejores | Toma 5 materias "de arriba hacia abajo" |
| **C: Horarios** | Interpreta las preferencias, asigna grupos sin choques que respeten turno, modalidad y días libres, y si hay choques propone una variante | Toma el primer grupo de cada materia sin revisar choques |
| **Manager** | Anuncia la tarea, evalúa todas las ofertas con la función del Proyecto 2 (no con la autoevaluación de cada contratista), adjudica, calcula Shapley y redacta | Siempre presente (coordinador) |

**Mejora 1, Contract Net con competencia.** Sigue los 4 pasos vistos en clase: anuncio
(`cfp`), oferta (cada contratista evalúa su capacidad y manda su *bid*), adjudicación al
mejor postor (`accept`/`reject`) y resultado (`inform`). Cada propuesta queda en la
ontología con `generadaPor` apuntando al contratista que la ofertó. El razonador deduce la
inversa `generaPropuesta`, así que en Protégé se puede preguntar qué contratista ganó.

### Transparencia: Shapley
v(S) es la puntuación de la mejor propuesta que obtiene la coalición S, calificada
siempre con la verdad de la ontología. Como el protocolo es determinista, las 8
coaliciones se calculan en milisegundos y φ es exacto (no una aproximación). Se
cumple la eficiencia: φ_A + φ_B + φ_C = v(N).

Hay un **segundo juego**, solo entre los 3 contratistas, con Historial y Horarios siempre
presentes. Ahí v(S) = mejor oferta de S − puntuación con la carga ingenua. Muestra los
axiomas vistos en clase: con A003 los 3 ofertan lo mismo y reciben lo mismo (simetría).
En un juego de "la mejor oferta gana", el ganador no se lleva todo: lo que cualquiera
lograría solo se reparte entre los 3 (GUIA §15.5).

### Papel del LLM
El LLM no decide nada: **interpreta** y **redacta**.
- **Interpretación:** pide un JSON con esquema fijo (`format` de Ollama). Se descartan los valores fuera del esquema y las materias que no aparecen en el texto del alumno. Si el LLM no responde, se usan reglas.
- **Redacción:** si el texto nombra una materia que no está en la propuesta, o inventa días de clase, se descarta y se usa una plantilla.
- **Caché:** las respuestas se guardan en `salidas/cache_llm.json`, así que repetir una ejecución no vuelve a llamar al modelo.

### Resultados: ¿sirve el MAS? (mejora 2)

`python main.py experimento --llm` arma la carga de 20 alumnos sintéticos con 7 sistemas.
Todos se califican con la misma función oficial y las mismas reglas duras. Detalle y
discusión en `GUIA_EJECUCION.md` §16; tablas en `resultados/experimento.md`.

| Sistema | Puntuación media | Con materias inválidas | Con choques | Fuera de 24–48 cr | Tiempo por alumno |
|---|---|---|---|---|---|
| **MAS (3 contratistas)** | **89.57** | 0% | 0% | 0% | 0.07 s |
| MAS (1 AgenteCarga, antes de la mejora 1) | 88.9 | 0% | 0% | 0% | 0.03 s |
| Mejor contratista solo (CargaPreferencias) | 88.48 | 0% | 0% | 0% | 0.02 s |
| Monoagente simple (solo requisitos) | 70.9 | 0% | 15% | 5% | < 0.01 s |
| LLM solo (llama3.2, 3B, CPU) | 36.1 | 100% | 90% | 50% | 16 s |

En pocas palabras:
- La coordinación entre especialistas es lo que más aporta.
- El LLM de 3B, por sí solo, no respeta el kárdex ni la seriación.
- La competencia entre contratistas (mejora 1) gana en promedio por 0.5–1.1 puntos en 4
  muestras, pero no en todos los alumnos.

---

## 5. Integración ontológica (tema 5 del curso)

- **TBox:** `ontologia/P2_ontologia_carga_academica.owx` (tu archivo original, sin cambios).
- **ABox:** `python main.py poblar` genera `ontologia/carga_academica_poblada.owl` (452 individuos) con las 79 materias reales y su seriación, 97 grupos, 12 profesores ficticios, 3 alumnos con registros y preferencias, y los agentes (los 4 roles + los 3 AgentesCarga contratistas). También materializa `enConflictoCon` (295 pares de grupos).
- **Clases definidas** (Lógica Descriptiva) que clasifica HermiT:

| Clase | Definición (Manchester) |
|---|---|
| `MateriaLlave` | `Materia and esPrerrequisitoDe min 2 Materia` |
| `MateriaSeriada` | `Materia and tienePrerrequisito some Materia` |
| `GrupoVespertino` | `Grupo and tieneBloqueHorario some (BloqueHorario and turno value "vespertino")` |
| `GrupoEnLinea` | `Grupo and tieneModalidad some ModalidadEnLinea` |
| `EstudianteConAdeudo` | `Estudiante and tieneRegistro some RegistroReprobado` |

  Para que `min 2` funcione se declara `AllDifferent` entre materias: OWL no asume nombres únicos (OWA).
  Con el plan real, HermiT deduce 3 materias llave: Programación Avanzada y Algoritmos (LIIS2105), Diseño y Gestión de Bases de Datos I (LIIS2112) y Persona y Humanismo (LYRU2101).

### Consultas DL Query para Protégé
Abre `salidas/kb_A001.owl`, inicia HermiT (Reasoner → Start reasoner) y prueba:

```
Materia and puedeSerCursadaPor value est_A001
MateriaLlave
EstudianteConAdeudo
Grupo and esOfertaDe value mat_LIIS2109 and tieneModalidad some ModalidadPresencial
Grupo and enConflictoCon value grp_LIIS2112_B
GrupoVespertino and GrupoEnLinea
Materia and tienePrerrequisito some (Materia and aprobadaPor value est_A002)
PropuestaCarga and esValida value true
PropuestaCarga and puntuacion some xsd:decimal[>= 92.0]
Agente and valorShapley some xsd:decimal[> 25.0]
PropuestaCarga and generadaPor value agente_carga_preferencias
AgenteCarga and generaPropuesta some (PropuestaCarga and esValida value true)
```

---

## 6. Estructura

```
agente-carga3/
├── main.py                  CLI
├── demo.ipynb               demostración paso a paso
├── iniciar_ollama_cpu.sh    Ollama sin GPU (evita el crash de ROCm)
├── requirements.txt
├── datos/
│   ├── intrauia/            exportación del portal (NO se versiona: trae datos de sesión)
│   ├── importar_intrauia.py exportación → plan_ibero.json (con validación)
│   ├── plan_ibero.json      plan de estudios real (79 materias)
│   └── semilla.py           ← oferta generada, profesores y alumnos
├── ontologia/
│   ├── P2_ontologia_carga_academica.owx   TBox original
│   └── carga_academica_poblada.owl        TBox + ABox (generada)
├── carga/
│   ├── config.py            rutas, modelo, pesos, metas de carga
│   ├── poblar.py            semilla → individuos OWL + clases definidas
│   ├── kb.py                ontología → objetos Python (owlready2 + SPARQL + HermiT)
│   ├── preferencias.py      lenguaje natural → preferencias (LLM validado + reglas)
│   ├── evaluacion.py        reglas académicas y función de evaluación
│   ├── agentes.py           los 4 agentes
│   ├── contract_net.py      protocolo + Shapley
│   ├── trazas.py            Trace Collector + mensajes FIPA
│   ├── persistencia.py      resultados → ontología
│   ├── reporte.py           Markdown y salida en terminal
│   ├── sistema.py           orquestación del modo normal
│   ├── crew.py              orquestación con CrewAI
│   ├── experimento.py       mejora 2: comparación contra otros sistemas
│   └── llm.py               cliente de Ollama solo CPU + caché + diagnóstico
├── resultados/              experimento comparativo (mejora 2), versionado para el reporte
└── salidas/                 reportes, trazas y ontologías de resultado (no se versiona)
```

Para cambiar el plan: vuelve a exportar de Intrauia a `datos/intrauia/plan_isc.txt` y
ejecuta `python datos/importar_intrauia.py`. Para agregar alumnos o cambiar la oferta,
edita `datos/semilla.py`. En ambos casos, después, ejecuta `python main.py poblar`
(detalle en la sección 14 de `GUIA_EJECUCION.md`).
