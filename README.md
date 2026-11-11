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
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Java solo se necesita para la opción `--razonador` (HermiT). Ollama solo se necesita para
usar el LLM.

## Uso

### Sin LLM (segundos)

```bash
python main.py alumnos                  # alumnos disponibles: A001, A002, A003
```

> **Resultado:** 3 alumnos de prueba.
>
> | Matrícula | Alumno | Semestre | Reprobadas |
> |---|---|---|---|
> | A001 | Ana Torres Medina | 5 | Programación Avanzada y Algoritmos |
> | A002 | Luis Hernández Rojas | 3 | Cálculo Diferencial e Integral |
> | A003 | Sofía Ramírez Lara | 6 | — |

```bash
python main.py demo                     # recomendación para los 3 alumnos
```

> **Resultado:** cada alumno con una petición distinta. φ es el valor de Shapley: cuántos
> puntos aportó cada agente (la suma da la puntuación).
>
> | Alumno | Petición | Carga recomendada | Puntuación | Ganó | φ Historial | φ Carga | φ Horarios |
> |---|---|---|---|---|---|---|---|
> | A001 | (preferencias guardadas: tarde, presencial) | 6 materias, 40 créditos | 92.29 | CargaPreferencias | 39.41 | 30.07 | 22.80 |
> | A002 | "ligero, en la mañana y sin clases el viernes" | 4 materias, 30 créditos | 94.53 | CargaPreferencias | 41.04 | 27.79 | 25.70 |
> | A003 | "adelantar, en línea, IA y la nube…" | 8 materias, 48 créditos | 84.39 | CargaAvance | 28.10 | 31.31 | 24.97 |
>
> En A001 y A002, que tienen materias reprobadas, el que más aporta es **Historial**: la
> seriación descarta muchas materias. En A003, que no debe nada y pide carga pesada, aporta
> más **Carga**.

```bash
python main.py recomendar A001 --sin-llm
```

> **Resultado:** primero se ven los mensajes del Contract Net (`cfp` → `propose` →
> `accept`/`reject` → `inform`) y después la recomendación:
>
> | Clave | Materia | Grupo | Horario |
> |---|---|---|---|
> | LIIS2105 | Programación Avanzada y Algoritmos (recursa) | B | Mar y Jue 11–13 |
> | LIIS2112 | Diseño y Gestión de Bases de Datos I | A | Lun y Mié 07–09 |
> | LIIB2104 | Proyecto de Ingeniería IV | B | Lun 17–19 |
> | LICB2102 | Estadística y Probabilidad | A | Lun y Mié 19–21 |
> | LIIE2104 | Circuitos Electrónicos I | B | Mar y Jue 17–19 |
> | LIIS2106 | Sistemas Embebidos I | A | Vie 15–19 |
>
> 40 créditos, sin choques, **92.29/100**. Licitación: Avance 91.88, Equilibrio 91.19,
> **Preferencias 92.29 (gana)**. Se prioriza recursar Programación Avanzada porque es
> prerrequisito de materias posteriores.

```bash
python main.py experimento              # compara el MAS contra otros sistemas
```

> **Resultado:** 20 alumnos de prueba, todos calificados con la misma función. La fila del
> LLM solo sale con `experimento --llm`.
>
> | Sistema | Puntuación media | Con materias inválidas | Con choques | Tiempo por alumno |
> |---|---|---|---|---|
> | **MAS (3 contratistas)** | **89.57** | 0 % | 0 % | 0.07 s |
> | MAS con un solo agente de Carga | 88.90 | 0 % | 0 % | 0.03 s |
> | Monoagente (solo revisa requisitos) | 70.90 | 0 % | 15 % | < 0.01 s |
> | LLM solo (llama3.2, sin agentes) | 36.10 | 100 % | 90 % | 16 s |
>
> La coordinación entre especialistas es lo que más aporta. El LLM solo, aunque recibe el
> plan y el kárdex, propone materias que el alumno no puede cursar: por eso en el sistema
> el LLM no decide.


### Con LLM

1. En una terminal, levanta Ollama solo con CPU y déjala abierta:

   ```bash
   ./iniciar_ollama_cpu.sh
   ```

2. En otra terminal, con el entorno activado (`source venv/bin/activate`):

   ```bash
   # Revisa que Ollama responda
   python main.py diagnostico
   ```

   > **Resultado:** `Ollama responde en http://127.0.0.1:11435`, la RAM libre y si el
   > cargador está conectado (sin cargador el LLM se desactiva solo).

   ```bash
   # Recomendación con petición en lenguaje natural (30–60 s)
   python main.py recomendar A002 -p "quiero algo ligero, en la mañana y sin clases el viernes"
   ```
   ```bash
   python main.py recomendar A003 -p "quiero adelantar, en línea, me interesa IA y la nube"
   ```

   > **Resultado (A002):** entiende *carga ligera, turno matutino, sin viernes* y recomienda
   > 4 materias, 30 créditos, **94.53/100**, sin ninguna clase el viernes: Cálculo
   > Diferencial e Integral (recursa), Programación Avanzada y Algoritmos, Formulación de
   > Proyectos y Bases de Datos I.
   >
   > **Resultado (A003):** entiende *carga pesada, en línea, le interesan IA y Cómputo en la
   > Nube* y recomienda 7 materias, 48 créditos, **84.17/100**, con Fundamentos de IA y
   > Cómputo en la Nube incluidas.
   >
   > Al final, el LLM redacta la explicación para el alumno. Estos valores son los que se
   > obtienen cuando las preferencias se interpretan así; si el LLM entiende algo distinto,
   > la carga puede cambiar.

   ```bash
   # Con el razonador HermiT (requiere Java)
   python main.py recomendar A001 -p "me interesa inteligencia artificial, prefiero la tarde" --razonador
   ```

   > **Resultado:** ahora incluye Fundamentos de Inteligencia Artificial (6 materias, 40
   > créditos, **92.55/100**, ganó CargaAvance). En el reporte aparece lo que dedujo HermiT:
   >
   > - **MateriaLlave** (prerrequisito de 2 o más materias): Programación Avanzada y
   >   Algoritmos, Bases de Datos I y Persona y Humanismo.
   > - **EstudianteConAdeudo** (tiene una materia reprobada): A001 y A002.
   > - Además clasifica las materias seriadas, los grupos vespertinos y matutinos, y los grupos en línea.

   ```bash
   # Orquestación con CrewAI (varios minutos)
   python main.py crew A001
   python main.py crew A002 -p "quiero carga ligera y sin viernes" --proceso jerarquico
   ```

   > **Resultado:** cada agente de CrewAI llama a su herramienta (historial, carga, horarios
   > y coordinación) y resume su parte. La recomendación final es la misma del Contract Net
   > (A001: 92.29/100); el LLM solo la redacta.

   ```bash
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
  agentes.py             los 6 agentes (4 roles)
  contract_net.py        protocolo Contract Net y valores de Shapley
  kb.py                  acceso a la ontología (owlready2, SPARQL, HermiT)
  preferencias.py        lenguaje natural → preferencias
  evaluacion.py          reglas académicas y función de evaluación
  sistema.py · crew.py   orquestación (Python o CrewAI)
  experimento.py         comparación contra otros sistemas
  poblar.py · persistencia.py · trazas.py · reporte.py · llm.py · config.py
```
