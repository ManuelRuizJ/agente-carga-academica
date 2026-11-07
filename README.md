# Agente de carga académica v3: MAS con ontología como base de conocimiento

Prototipo final del proyecto de **Agentes Inteligentes** (Ibero Puebla).
Recomienda una carga académica personalizada con 4 agentes (Historial, Carga,
Horarios y Manager). Los agentes se coordinan con **Contract Net**, se
auditan con **valores de Shapley** y usan una **ontología OWL** como base de
conocimiento compartida.

Esta versión reemplaza a `../integracion_ontologica.ipynb` y conserva el diseño
del Proyecto 2: las mismas fichas de agentes, los mismos pesos de evaluación, la
misma función v(S) y la misma ontología.

---

## 1. Por qué fallaba el prototipo anterior (y por qué se reiniciaba la laptop)

| Problema encontrado | Evidencia | Solución en v3 |
|---|---|---|
| Ollama intentaba usar la **GPU integrada Radeon (gfx90c)**, que ROCm no soporta | Última celda del notebook: `ROCm error: invalid device function` | `iniciar_ollama_cpu.sh` oculta todas las GPUs y fuerza CPU. Además, cada petición manda `num_gpu: 0` |
| CrewAI usa el endpoint `/v1` de Ollama, que **ignora** `num_gpu` | código de `crewai/llms/providers/openai_compatible` | La GPU se desactiva en el **servidor**, no en la petición |
| La ontología **no tenía individuos** (ni alumnos, ni materias, ni grupos) | `P2_ontologia_carga_academica.owx`: 0 `ClassAssertion` | `datos/semilla.py` + `carga/poblar.py` la pueblan con 203 individuos |
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
python main.py demo                          # los 3 alumnos sin LLM (menos de 1 s)

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

Tiempos medidos en tu laptop:

| Modo | Tiempo | Llamadas al LLM |
|---|---|---|
| `demo` / `--sin-llm` | ~0.5 s | 0 |
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
 │  cfp ─▶ AgenteCarga     ─propose▶ combinaciones         │
 │  cfp ─▶ AgenteHorarios  ─propose▶ propuestas con grupos │
 │  evaluar: 0.30·A + 0.25·H + 0.25·C + 0.20·P             │
 │  accept-proposal (mejor) / reject-proposal (resto)      │
 │  Shapley exacto sobre las 8 coaliciones                 │
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
| **B: Carga** | Combina materias dentro de 24–48 créditos y de la meta del alumno (ligera, normal o pesada), y limita las materias difíciles | Toma 5 materias "de arriba hacia abajo" |
| **C: Horarios** | Interpreta las preferencias, asigna grupos sin choques que respeten turno, modalidad y días libres, y si hay choques propone una variante | Toma el primer grupo de cada materia sin revisar choques |
| **Manager** | Evalúa con la función del Proyecto 2, adjudica, calcula Shapley y redacta | Siempre presente (coordinador) |

### Transparencia: Shapley
v(S) es la puntuación de la mejor propuesta que obtiene la coalición S, calificada
siempre con la verdad de la ontología. Como el protocolo es determinista, las 8
coaliciones se calculan en milisegundos y φ es exacto (no una aproximación). Se
cumple la eficiencia: φ_A + φ_B + φ_C = v(N).

### Papel del LLM
El LLM no decide nada: **interpreta** y **redacta**.
- **Interpretación:** pide un JSON con esquema fijo (`format` de Ollama). Se descartan los valores fuera del esquema y las materias que no aparecen en el texto del alumno. Si el LLM no responde, se usan reglas.
- **Redacción:** si el texto nombra una materia que no está en la propuesta, o inventa días de clase, se descarta y se usa una plantilla.
- **Caché:** las respuestas se guardan en `salidas/cache_llm.json`, así que repetir una ejecución no vuelve a llamar al modelo.

---

## 5. Integración ontológica (tema 5 del curso)

- **TBox:** `ontologia/P2_ontologia_carga_academica.owx` (tu archivo original, sin cambios).
- **ABox:** `python main.py poblar` genera `ontologia/carga_academica_poblada.owl` con 27 materias, 35 grupos, 7 profesores, 3 alumnos con registros y preferencias, y los 4 agentes. También materializa `enConflictoCon` (34 pares de grupos).
- **Clases definidas** (Lógica Descriptiva) que clasifica HermiT:

| Clase | Definición (Manchester) |
|---|---|
| `MateriaLlave` | `Materia and esPrerrequisitoDe min 2 Materia` |
| `MateriaSeriada` | `Materia and tienePrerrequisito some Materia` |
| `GrupoVespertino` | `Grupo and tieneBloqueHorario some (BloqueHorario and turno value "vespertino")` |
| `GrupoEnLinea` | `Grupo and tieneModalidad some ModalidadEnLinea` |
| `EstudianteConAdeudo` | `Estudiante and tieneRegistro some RegistroReprobado` |

  Para que `min 2` funcione se declara `AllDifferent` entre materias: OWL no asume nombres únicos (OWA).

### Consultas DL Query para Protégé
Abre `salidas/kb_A001.owl`, inicia HermiT (Reasoner → Start reasoner) y prueba:

```
Materia and puedeSerCursadaPor value est_A001
MateriaLlave
EstudianteConAdeudo
Grupo and esOfertaDe value mat_IAR501 and tieneModalidad some ModalidadPresencial
Grupo and enConflictoCon value grp_SOP401_B
GrupoVespertino and GrupoEnLinea
Materia and tienePrerrequisito some (Materia and aprobadaPor value est_A002)
PropuestaCarga and esValida value true
PropuestaCarga and puntuacion some xsd:decimal[>= 88.0]
Agente and valorShapley some xsd:decimal[> 25.0]
```

---

## 6. Estructura

```
agente-carga3/
├── main.py                  CLI
├── demo.ipynb               demostración paso a paso
├── iniciar_ollama_cpu.sh    Ollama sin GPU (evita el crash de ROCm)
├── requirements.txt
├── datos/semilla.py         ← edita aquí materias, grupos y alumnos
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
│   └── llm.py               cliente de Ollama solo CPU + caché + diagnóstico
└── salidas/                 reportes, trazas y ontologías de resultado
```

Para agregar alumnos o materias, edita `datos/semilla.py` y ejecuta `python main.py poblar`.
