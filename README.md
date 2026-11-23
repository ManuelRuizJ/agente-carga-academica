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
          ├─ request ─▶ AgenteValidador ─▶ HermiT en RAM: ¿consistente? (si no, rechaza)
          └─ calcula los valores de Shapley
                    │
        Ontología OWL (lee datos y guarda resultados) · SQLite (auditoría)
```

### Arquitectura del backend

```
  CrewAI (5 agentes)                       Navegador (página de demo)
     │ @tool + httpx                              │ fetch
     ▼                                            ▼
  ┌──────────────────────── FastAPI (asíncrona) ────────────────────────┐
  │ /agentes/historial · /agentes/carga · /agentes/horarios             │
  │ /recomendar  (Contract Net + Validador + Shapley)                   │
  │ /validar     (AgenteValidador: HermiT en RAM)                       │
  │ /auditoria · /metricas · /salud                                     │
  └───────┬───────────────────────────┬───────────────────────┬─────────┘
          ▼                           ▼                       ▼
   Ontología OWL 2              HermiT efímero           SQLite
   (TBox + ABox, se carga       (un World nuevo en       ejecuciones, trazas,
    una vez al arrancar)         RAM por solicitud)      mensajes, Shapley, llamadas
```

**Modelo de datos híbrido.** La ontología guarda el conocimiento declarativo (plan,
seriación, axiomas) y SQLite los datos operativos (cada ejecución y su auditoría). Una
escritura en SQLite tarda menos de 1 ms. Una inferencia de HermiT tarda ~0.8 s, por eso
solo se ejecuta para validar.

**Inferencia efímera (reasoning offloading).** Para cada validación se crea un `World` de
owlready2 nuevo en memoria. Se le agregan la solicitud y un axioma de cierre del kárdex, se
le pregunta a HermiT solo si es **consistente** (`-k`; clasificar todo tardaba ~12 s) y
después se descarta. La ontología en disco nunca cambia y una solicitud no contamina a la
siguiente.

**Cómo HermiT detecta un error de seriación.** `poblar` agrega un axioma por cada materia
seriada (35 en total):

```
PropuestaCon_X ≡ PropuestaCarga ⊓ ∃incluyeGrupo.(Grupo ⊓ ∃esOfertaDe.{X})
PropuestaCon_X ⊑ ∀propuestaPara.(∃haAprobado.{P})        (P = prerrequisito de X)
```

El validador agrega `alumno : ∀haAprobado.{materias de su kárdex}`. OWL trabaja con mundo
abierto, y este axioma cierra el kárdex para ese alumno. Si la solicitud incluye X y el
alumno no aprobó P, la ontología queda **inconsistente** y la operación se rechaza,
indicando el axioma violado.

| Agente | Qué hace |
|---|---|
| **Historial** | Lee el kárdex y descarta las materias ya aprobadas, las que no tienen sus prerrequisitos y las que no se ofertan. Da prioridad a las reprobadas y a las materias "llave" |
| **Carga** (3 contratistas) | Arman combinaciones de materias, cada uno con su estrategia: **Avance** (prioridad académica), **Equilibrio** (meta de créditos y pocas materias difíciles) y **Preferencias** (intereses, turno y modalidad). Cada uno manda sus 2 mejores ofertas |
| **Horarios** | Interpreta la petición en lenguaje natural y asigna grupos sin choques que respeten turno, modalidad y días libres |
| **Validador** | Revisa con HermiT que la propuesta ganadora, o cualquier solicitud del alumno, no viole los axiomas de la ontología. También revisa créditos, choques de horario y oferta. Si la ontología queda inconsistente, rechaza la operación y da la justificación |
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

Java se necesita para HermiT (Agente Validador y opción `--razonador`). Ollama solo se
necesita para usar el LLM y CrewAI.

## Backend y demostración en vivo

```bash
python main.py api          # http://127.0.0.1:8077  (página)  ·  /docs  (Swagger)
```

El puerto se cambia con `CARGA_PORT` y la base con `CARGA_DB` (por defecto
`salidas/carga.db`). La página tiene tres pestañas:

1. **Recomendar carga:** ejecuta el MAS completo y muestra la carga, el veredicto del
   validador, la licitación, los mensajes FIPA-ACL, las trazas y las gráficas de Shapley.
2. **Validador semántico:** arma una solicitud con clic en las materias (las de borde rojo
   no cumplen la seriación) y la valida con HermiT.
3. **Auditoría y Shapley:** muestra las métricas (tasa de éxito, CRUD contra inferencia),
   las ejecuciones guardadas en SQLite con su detalle y la bitácora de llamadas a la API,
   donde aparecen las `@tool` de CrewAI.

Enlaces directos para la demo: `/#rec=A002`, `/#val=A001:LIIS2105,LIIS2112,LIIB2104,LICB2102,LIIN2104`
y `/#aud`.

| Minuto | Qué mostrar | Cómo |
|---|---|---|
| 1 · Entorno | FastAPI, SQLite y la ontología cargada | `python main.py api` y luego `/salud` o los indicadores de la página |
| 2 · Caso exitoso | La Crew, la `@tool`, el endpoint y el registro en SQLite | `python main.py crew A002 -p "quiero algo ligero y sin viernes"` (en la terminal de la API se ve cada `[api] POST … ← crewai @tool …`) |
| 3 · Rechazo semántico | HermiT detecta la inconsistencia y el Validador la frena | `python main.py crew A001 -m LIIS2105,LIIS2112,LIIB2104,LICB2102,LIIN2104` o `/#val=…` |
| 4–5 · Auditoría | Trazas en SQLite y valores de Shapley | pestaña **Auditoría y Shapley** (`/#aud`) |

Tiempos medidos con `llama3.2` solo en CPU: caso exitoso **~2 min 15 s** (5 tareas, 10 llamadas
al LLM) y rechazo **~1 min** (la API responde en ~2 s; el resto es el LLM). Con `--sin-llm`
las mismas herramientas llaman a la API en segundos, como respaldo si el LLM se alenta.

Resultado del caso 3: `RECHAZADA · HermiT: INCONSISTENTE · LIIN2104 viola la seriación:
requiere LIIB2104 · axioma PropuestaCon_LIIN2104 ⊑ ∀propuestaPara.(∃haAprobado.{LIIB2104})`.

### Pruebas

```bash
python -m pytest -q          # 27 pruebas, ~12 s (las de HermiT se saltan si no hay Java)
```

Prueban la ontología (los 35 axiomas y la inversa de la seriación), las reglas académicas,
el Contract Net (que la ganadora sea válida y que el orden de mensajes FIPA sea correcto),
Shapley (eficiencia Σφ = v(N), coalición vacía), el validador (acepta, rechaza y confirma
que la ontología no cambia), la API con SQLite y que las herramientas de CrewAI lleguen a
los endpoints. Cada prueba usa su propia base temporal.

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
   # Orquestación con CrewAI (varios minutos). Necesita la API levantada: python main.py api
   python main.py crew A001
   python main.py crew A002 -p "quiero carga ligera y sin viernes" --proceso jerarquico
   python main.py crew A001 -m LIIS2105,LIIS2112,LIIB2104,LICB2102,LIIN2104   # rechazo
   ```

   > **Resultado:** cada agente de CrewAI llama a su herramienta `@tool` (historial, carga,
   > horarios, validación y coordinación) y cada herramienta hace una petición HTTP con
   > httpx a la API. La recomendación final es la misma del Contract Net (A001: 92.29/100);
   > el LLM solo la redacta, y el servidor guarda la redacción únicamente si pasa el filtro
   > anti-alucinación. Con `-m`, el Agente Validador revisa esa solicitud y la rechaza si
   > viola la seriación.

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
tests/                   pruebas unitarias (pytest)
carga/
  api.py                 backend FastAPI (asíncrono)
  web/index.html         página de demostración (sin dependencias externas)
  db.py                  persistencia y auditoría en SQLite
  validador.py           AgenteValidador: HermiT en RAM (inferencia efímera)
  agentes.py             los agentes especialistas y el Manager
  contract_net.py        protocolo Contract Net y valores de Shapley
  kb.py                  acceso a la ontología (owlready2, SPARQL, HermiT)
  preferencias.py        lenguaje natural → preferencias
  evaluacion.py          reglas académicas y función de evaluación
  sistema.py             orquestación en Python
  crew.py                Crew de CrewAI: @tool → httpx → API
  experimento.py         comparación contra otros sistemas
  poblar.py · persistencia.py · trazas.py · reporte.py · llm.py · config.py
```
