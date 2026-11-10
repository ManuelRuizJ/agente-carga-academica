# Agente de carga académica

Sistema multiagente que recomienda a un alumno qué materias inscribir en el periodo.
Respeta la seriación, el rango de 24 a 48 créditos y los horarios, y toma en cuenta las
preferencias del alumno (turno, modalidad, días libres e intereses).

Proyecto final de **Agentes Inteligentes**, Universidad Iberoamericana Puebla.

## Cómo funciona

```
            petición del alumno
                    │
        AgenteHorarios: interpreta preferencias
                    │
        AgenteManager (Contract Net)
          ├─ cfp ─▶ AgenteHistorial ─▶ materias válidas
          ├─ cfp ─▶ CargaAvance       ┐
          ├─ cfp ─▶ CargaEquilibrio   ├─▶ ofertas (compiten)
          ├─ cfp ─▶ CargaPreferencias ┘
          ├─ cfp ─▶ AgenteHorarios  ─▶ grupos sin choques
          ├─ evalúa, adjudica (accept / reject) y recibe el resultado (inform)
          └─ calcula los valores de Shapley
                    │
        Ontología OWL (lee datos y guarda resultados)
```

| Agente | Qué hace |
|---|---|
| **Historial** | Lee el kárdex y descarta las materias ya aprobadas, las que no tienen sus prerrequisitos y las que no se ofertan. Da prioridad a las reprobadas y a las materias "llave" |
| **Carga** (3 contratistas) | Arman combinaciones de materias, cada uno con su estrategia: **Avance** (prioridad académica), **Equilibrio** (meta de créditos y pocas materias difíciles) y **Preferencias** (intereses, turno y modalidad). Cada uno manda sus 2 mejores ofertas |
| **Horarios** | Interpreta la petición en lenguaje natural y asigna grupos sin choques que respeten turno, modalidad y días libres |
| **Manager** | Coordina el Contract Net (`cfp` → `propose` → `accept`/`reject` → `inform`), califica todas las ofertas con la misma función y elige la mejor |

**Función de evaluación:** `Score = 0.30·Avance + 0.25·Horario + 0.25·Carga + 0.20·Preferencias`

**Transparencia:** al final se calcula el **valor de Shapley** de cada agente, que indica
cuántos puntos de la recomendación aportó cada uno. Se calcula de forma exacta con las 8
coaliciones posibles, y la suma de los tres valores es igual a la puntuación final. Hay un
segundo cálculo de Shapley entre los 3 contratistas de carga.

**Base de conocimiento:** una ontología OWL 2 (`ontologia/`) con el plan real de Ingeniería
en Sistemas Computacionales (79 materias con su seriación), la oferta de grupos, los
profesores y los alumnos. Los agentes la consultan con SPARQL y escriben de vuelta sus
resultados. El razonador HermiT clasifica las clases definidas (`MateriaLlave`,
`MateriaSeriada`, `GrupoEnLinea`, `GrupoVespertino` y `EstudianteConAdeudo`).

**LLM (opcional):** `llama3.2` con Ollama. Solo interpreta la petición y redacta la
explicación final; no decide qué materias son válidas. Sin LLM, el sistema usa reglas y
da la misma recomendación.

> Los alumnos, la oferta de grupos y los profesores son datos de prueba. El plan de
> estudios es el real.

## Instalación

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Java solo se necesita para la opción `--razonador` (HermiT). Ollama solo se necesita para
usar el LLM.

## Uso

### Sin LLM (segundos)

```bash
python main.py alumnos                  # alumnos disponibles: A001, A002, A003
python main.py demo                     # recomendación para los 3 alumnos
python main.py recomendar A001 --sin-llm
python main.py experimento              # compara el MAS contra otros sistemas
```

### Con LLM

1. En una terminal, levanta Ollama solo con CPU y déjala abierta:

   ```bash
   ./iniciar_ollama_cpu.sh
   ```

2. En otra terminal, con el entorno activado (`source .venv/bin/activate`):

   ```bash
   # Revisa que Ollama responda
   python main.py diagnostico

   # Recomendación con petición en lenguaje natural (30–60 s)
   python main.py recomendar A002 -p "quiero algo ligero, en la mañana y sin clases el viernes"
   python main.py recomendar A003 -p "quiero adelantar, en línea, me interesa IA y la nube"

   # Con el razonador HermiT (requiere Java)
   python main.py recomendar A001 -p "me interesa inteligencia artificial, prefiero la tarde" --razonador

   # Orquestación con CrewAI (varios minutos)
   python main.py crew A001
   python main.py crew A002 -p "quiero carga ligera y sin viernes" --proceso jerarquico

   # Experimento que agrega el "LLM solo" a la comparación (~5 min)
   python main.py experimento --llm
   ```

3. Al terminar, presiona Ctrl + C en la terminal de Ollama para apagarlo.

Los comandos de `main.py` terminan solos. En el reporte (`salidas/reporte_<matrícula>.md`),
los campos "Interpretado por" y "Redactado por" dicen `LLM (llama3.2)` cuando se usó el
modelo. Si dicen "reglas" o "plantilla", se usó el respaldo sin LLM y la recomendación es
la misma. Las respuestas del LLM se guardan
en `salidas/cache_llm.json`, así que repetir la misma petición tarda menos de un segundo.

**Notebook:** `demo.ipynb` muestra el proceso paso a paso: base de conocimiento,
preferencias, Contract Net, Shapley, HermiT y reporte final.

### Resultados

Cada ejecución guarda en `salidas/`:

- `reporte_<matrícula>.md`: recomendación, horario semanal, ofertas del Contract Net y
  valores de Shapley.
- `trazas_<matrícula>.json`: trazas de cada agente (tarea, entrada, salida, tiempo y puntuación).
- `kb_<matrícula>.owl`: ontología con los resultados. Se puede abrir en Protégé.
- `experimento.md` y `experimento.csv`: tabla comparativa del comando `experimento`.

Para agregar alumnos o cambiar la oferta, edita `datos/semilla.py` y ejecuta
`python main.py poblar`.

## Estructura

```
main.py                  línea de comandos
demo.ipynb               demostración paso a paso
iniciar_ollama_cpu.sh    servidor de Ollama solo con CPU
datos/                   plan de estudios y datos de prueba
ontologia/               ontología base y ontología poblada
carga/
  agentes.py             los 4 agentes
  contract_net.py        protocolo Contract Net y valores de Shapley
  kb.py                  acceso a la ontología (owlready2, SPARQL, HermiT)
  preferencias.py        lenguaje natural → preferencias
  evaluacion.py          reglas académicas y función de evaluación
  sistema.py · crew.py   orquestación (Python o CrewAI)
  experimento.py         comparación contra otros sistemas
  poblar.py · persistencia.py · trazas.py · reporte.py · llm.py · config.py
```
