# Guía de ejecución y funcionamiento: Agente de carga académica v3

Esta guía explica, paso a paso, cómo correr el sistema y cómo funciona por dentro.
**Todas las salidas que aparecen aquí son reales:** se obtuvieron ejecutando cada paso
en tu laptop (Fedora 44, Ryzen 7 5700U, 14 GB de RAM). Las bitácoras completas están en
`salidas/_verificacion/` (sección 17).

> **Datos: qué es real y qué es sintético.** Desde el 6 de noviembre de 2026 el plan de
> estudios es el **real** de Ingeniería en Sistemas Computacionales de la Ibero Puebla
> (programa 2801): 79 materias con su sigla, créditos, semestre ideal, horas y seriación,
> exportadas del portal **Intrauia** (sección 14). Son **sintéticos**: la dificultad de
> cada materia (heurística), la oferta de Primavera 2027 (grupos, horarios, cupos y
> modalidades, generados a partir del plan real), los profesores, los alumnos y el rango
> de 24–48 créditos por periodo.
>
> Las salidas de los pasos 2 a 6 y 10 a 12 se regeneraron el 6 de noviembre con el plan
> real. Las de los pasos 8 y 9 (LLM y CrewAI) son de la verificación del 5 de noviembre,
> **con el catálogo sintético anterior** (claves como `IAR501` o `SOP401`): el
> funcionamiento es el mismo, solo cambian los nombres de las materias.

> **Convención:** las líneas que empiezan con `$` son comandos que escribes en la
> terminal (sin el `$`). Lo demás es lo que debe aparecer en pantalla.

---

## Índice

1. [Resumen de la verificación](#1-resumen-de-la-verificación)
2. [Requisitos previos](#2-requisitos-previos)
3. [Paso 1: entrar a la carpeta y activar el entorno](#3-paso-1-entrar-a-la-carpeta-y-activar-el-entorno)
4. [Paso 2: comprobar que la ontología responde](#4-paso-2-comprobar-que-la-ontología-responde)
5. [Paso 3: la demo rápida, sin LLM](#5-paso-3-la-demo-rápida-sin-llm)
6. [Paso 4: una recomendación completa y cómo leer la salida](#6-paso-4-una-recomendación-completa-y-cómo-leer-la-salida)
7. [Paso 5: leer el reporte Markdown](#7-paso-5-leer-el-reporte-markdown)
8. [Paso 6: el razonador HermiT](#8-paso-6-el-razonador-hermit)
9. [Paso 7: encender Ollama SOLO con CPU](#9-paso-7-encender-ollama-solo-con-cpu)
10. [Paso 8: recomendación con LLM (lenguaje natural)](#10-paso-8-recomendación-con-llm-lenguaje-natural)
11. [Paso 9: orquestación con CrewAI](#11-paso-9-orquestación-con-crewai)
12. [Paso 10: el notebook de demostración](#12-paso-10-el-notebook-de-demostración)
13. [Paso 11: consultar los resultados en Protégé (DL Query)](#13-paso-11-consultar-los-resultados-en-protégé-dl-query)
14. [Paso 12: agregar tus propios alumnos o materias](#14-paso-12-agregar-tus-propios-alumnos-o-materias)
15. [Cómo funciona por dentro (con un ejemplo numérico completo)](#15-cómo-funciona-por-dentro-con-un-ejemplo-numérico-completo)
16. [Solución de problemas](#16-solución-de-problemas)
17. [Apagar todo y bitácoras de verificación](#17-apagar-todo-y-bitácoras-de-verificación)

---

## 1. Resumen de la verificación

| # | Prueba | Resultado | Tiempo |
|---|---|---|---|
| 0 | Instalación limpia desde `requirements.txt` en un entorno nuevo | ✅ OK | 40 s |
| 1 | `python main.py poblar` (genera la ontología con individuos) | ✅ 452 individuos, 79 materias reales | 0.2 s |
| 2 | `python main.py alumnos` | ✅ 3 alumnos | < 1 s |
| 3 | `python main.py demo` (3 alumnos, sin LLM) | ✅ | 2.6 s |
| 4 | `recomendar A001 --sin-llm` | ✅ 92.29/100 | 1.2 s |
| 5 | `recomendar A003 --razonador` (HermiT en Java) | ✅ 6 clases inferidas | 5 s |
| 6 | 10 consultas DL Query sobre la ontología de salida | ✅ todas con resultado correcto | — |
| 7 | `demo.ipynb` completo con su kernel | ✅ 7 celdas, 0 errores | 6 s |
| 8 | Casos de error (alumno inexistente, Ollama apagado) | ✅ mensajes claros, no truena | — |
| 9 | Ollama solo CPU: `library=cpu`, **VRAM = 0 bytes** | ✅ | — |
| 10 | `recomendar` con LLM (interpretación + redacción) | ✅ | 67 s (1ª vez), 24 s (2ª), 0.4 s (caché) |
| 11 | `crew A001` (CrewAI secuencial, 4 agentes, 4 herramientas) | ✅ | 4 min |
| 12 | `crew A002 --proceso jerarquico` (Manager delega a los especialistas) | ✅ 4 herramientas | 5 min 20 s |
| 13 | Agregar un alumno nuevo (A004) en `datos/semilla.py` | ✅ | < 1 s |
| 14 | Importar el plan real de Intrauia (`datos/importar_intrauia.py`) | ✅ 79 materias, 0 errores de validación | < 1 s |
| 15 | Reglas duras en las 3 recomendaciones (seriación, choques, créditos, optativas, días libres) | ✅ las 3 pasan | < 1 s |
| 16 | Mejora 1: licitación entre 3 AgentesCarga + Shapley entre contratistas (Σφ = v(N)) | ✅ en los 3 alumnos | — |

Las pruebas 0, 8 a 12 son de la verificación del 5 de noviembre (catálogo sintético). Las
demás se repitieron el 6 de noviembre con el plan real.

**Tres problemas que encontré durante esta verificación y ya están corregidos:**

1. **El LLM inventaba horarios en la redacción final.** Escribió, por ejemplo, "Desarrollo
   de Videojuegos de lunes a viernes de 13:00 a 15:00", cuando en realidad es lunes y
   viernes. Ahora el LLM ya no recibe horas, solo explica *por qué* se recomienda cada
   materia. Además, un guardia rechaza cualquier texto con rangos de días, horas, listas,
   materias ajenas a la propuesta o frases cortadas. Si lo rechaza, se usa una plantilla.
2. **En CrewAI, el coordinador a veces no llamaba a su herramienta** y redactaba una
   carga de memoria (incorrecta). El guardia la detectó y la reemplazó. Ahora el
   resultado oficial del Contract Net se le entrega dentro de su tarea, y en la
   siguiente corrida llamó las 4 herramientas y su texto pasó el guardia.
3. **El AgenteCarga probaba combinaciones con una materia de más** (6 cuando el máximo
   era 5). No cambiaba ningún resultado, porque el criterio de carga las castigaba, pero
   era trabajo inútil. Se corrigió y la demo dio exactamente los mismos números.

---

## 2. Requisitos previos

Ya los tienes todos. Si algún día lo instalas en otra máquina, verifica:

```text
$ python3.12 --version
Python 3.12.16                 ← CrewAI aún no soporta 3.14; usa 3.12

$ java -version
openjdk version "25.0.4.1"     ← solo para --razonador (HermiT)

$ ls ~/.ollama/models/manifests/registry.ollama.ai/library/
gemma3  llama3.1  llama3.2     ← modelos ya descargados (solo para el LLM)
```

Lo único **obligatorio** es Python 3.12. Java y Ollama son opcionales: sin Java solo
no funciona `--razonador`, y sin Ollama el sistema usa reglas en lugar del LLM.

---

## 3. Paso 1: entrar a la carpeta y activar el entorno

```text
$ cd ~/Documentos/universidad/agentes/parcial-3/agente-carga3
$ source .venv/bin/activate
```

El prompt de tu terminal debe mostrar `(.venv)` al inicio. Comprueba que se usa el
Python correcto:

```text
$ which python && python --version
/home/jesus/Documentos/universidad/agentes/parcial-3/agente-carga3/.venv/bin/python
Python 3.12.16
```

> ⚠️ **No uses el `venv` viejo de `parcial-3/`.** Está roto: `python` apunta a 3.14
> pero los paquetes se instalaron para 3.12.

### Si necesitas crear el entorno desde cero

Esto es exactamente lo que se probó en un entorno nuevo (40 segundos):

```text
$ python3.12 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ pip list | grep -E '^(crewai|owlready2|requests|ipykernel) '
crewai                                   1.15.34
ipykernel                                7.4.0
owlready2                                0.51
requests                                 2.34.2
```

Para usar el notebook, registra además el kernel (una sola vez):

```text
$ python -m ipykernel install --user --name agente-carga3 --display-name "agente-carga3 (.venv)"
```

### Ver todos los comandos disponibles

```text
$ python main.py --help
usage: main.py [-h] {poblar,alumnos,diagnostico,demo,recomendar,crew} ...

  poblar              (re)genera la ontología poblada desde datos/semilla.py
  alumnos             lista los estudiantes de la ontología
  diagnostico         revisa Ollama (CPU/GPU) y memoria
  demo                ejecuta los 3 alumnos sin LLM (segundos)
  recomendar          MAS en Python puro + LLM mínimo (recomendado)
  crew                misma lógica, orquestada por CrewAI (lento en CPU)

$ python main.py recomendar --help
usage: main.py recomendar [-h] [-p PETICION] [--sin-llm] [--razonador] [-q] matricula

  -p PETICION, --peticion PETICION   preferencias en lenguaje natural
  --sin-llm                          no usar Ollama (todo por reglas)
  --razonador                        ejecutar HermiT (requiere Java)
  -q, --silencioso                   no mostrar mensajes del protocolo
```

---

## 4. Paso 2: comprobar que la ontología responde

### 4.1 (Opcional) Regenerar la ontología poblada

Tu ontología del Proyecto 2 solo tenía clases y propiedades. Este comando le agrega
los individuos definidos en `datos/semilla.py`:

```text
$ python main.py poblar
✔ Ontología poblada: ontologia/carga_academica_poblada.owl
  452 individuos | 79 materias | 97 grupos | 3 estudiantes | 295 pares de grupos en conflicto
```

Los 3 individuos extra (452 en vez de 449) son los 3 AgentesCarga contratistas de la
mejora 1 (sección 6.1). Las 79 materias son las del plan real (`datos/plan_ibero.json`). Los 97 grupos se
generan con una semilla fija a partir de ese plan, así que salen iguales en cada corrida.

No es necesario ejecutarlo la primera vez, porque el archivo ya existe. Solo vuelve a
correrlo cuando edites `datos/semilla.py`. Tu archivo original
`ontologia/P2_ontologia_carga_academica.owx` **nunca se modifica**.

### 4.2 Listar los alumnos

```text
$ python main.py alumnos
A001  Ana Torres Medina        sem 5  prom 8.78  aprobadas 27  reprobadas ['LIIS2105']
A002  Luis Hernández Rojas     sem 3  prom 7.79  aprobadas 14  reprobadas ['LICB2103']
A003  Sofía Ramírez Lara       sem 6  prom 9.3  aprobadas 36  reprobadas -
```

Cada dato sale de la ontología. Las materias aprobadas y reprobadas se obtienen con una
**consulta SPARQL** sobre los individuos `RegistroAprobado` y `RegistroReprobado`
(`carga/kb.py`, método `_sparql_registros`).

| Alumno | Para qué sirve en la demo |
|---|---|
| **A001 Ana** | Reprobó **Programación Avanzada y Algoritmos** (LIIS2105), una materia llave: bloquea Paradigmas, Móviles, Web y Ambientes Virtuales y Juegos. Sirve para ver si el sistema prioriza recursar. Trabaja en las mañanas: prefiere la tarde y la modalidad presencial |
| **A002 Luis** | Reprobó **Cálculo Diferencial e Integral** (LICB2103), que bloquea Cálculo Multivariable. Quiere una carga ligera |
| **A003 Sofía** | Alumna regular y sobresaliente (todo aprobado hasta 5.º) que quiere adelantar (carga pesada) y prefiere en línea |

Los kárdex se generan con la función `_kardex` de `datos/semilla.py`: "todas las
obligatorias hasta el semestre N, menos estas". La función verifica que nadie tenga
aprobada una materia sin su prerrequisito real.

---

## 5. Paso 3: la demo rápida, sin LLM

```text
$ time python main.py demo
 CARGA RECOMENDADA (40 créditos · puntuación 92.29/100) · la ofertó CargaPreferencias   ← A001
 Licitación: Avance 91.88 | Equilibrio 91.19 | Preferencias 92.29 ✔
 Shapley: Historial 39.41 | Carga 30.07 | Horarios 22.8
 Shapley contratistas: Avance 5.22 | Equilibrio 4.88 | Preferencias 5.63
 CARGA RECOMENDADA (30 créditos · puntuación 94.53/100) · la ofertó CargaPreferencias   ← A002
 Licitación: Avance 92.44 | Equilibrio 92.77 | Preferencias 94.53 ✔
 Shapley: Historial 41.04 | Carga 27.79 | Horarios 25.7
 Shapley contratistas: Avance 0.44 | Equilibrio 0.6 | Preferencias 2.37
 CARGA RECOMENDADA (48 créditos · puntuación 84.39/100) · la ofertó CargaAvance         ← A003
 Licitación: Avance 84.39 ✔ | Equilibrio 84.39 | Preferencias 84.39
 Shapley: Historial 28.1 | Carga 31.31 | Horarios 24.97
 Shapley contratistas: Avance 10.2 | Equilibrio 10.2 | Preferencias 10.2
python main.py demo  2.58s user 0.04s system 99% cpu 2.628 total
```

(Arriba se muestra solo el resumen; en pantalla verás el bloque completo de cada alumno.)

En **menos de 3 segundos** procesa a los 3 alumnos: Contract Net con la licitación, 8
coaliciones de Shapley entre roles y otras 8 entre contratistas por alumno, el reporte y
la escritura en la ontología. El prototipo anterior tardaba
minutos y terminaba con el error de ROCm.

---

## 6. Paso 4: una recomendación completa y cómo leer la salida

```text
$ python main.py recomendar A001 --sin-llm
```

Salida real, comentada por bloques:

### 6.1 Mensajes del Contract Net (FIPA-ACL)

```text
▶ Contract Net para Ana Torres Medina (A001)
  [      cfp       ] AgenteManager → AgenteHistorial: ¿Qué materias puede cursar A001?
  [    propose     ] AgenteHistorial → AgenteManager: válidas: LIIS2105, LIIS2112, LIIB2104, LICB2102, LIIE2104, LIIS2113, LIIS2114, LIIN2103, LIIS2106, LIIS2108, LIIS2117, LICB1229, LIIE2103, LIII0428, LIIN2105, LIIN2106, LIIS2109, LIIS2120, LRSS2102, LYRU2118, LYRU2104, LYRU2110, LYRU2111, LYRU2113, LIIN2110, LIIS2122, LIIS2123, LIIS2124
  [      cfp       ] AgenteManager → CargaAvance: Arma una carga de 24-48 créditos, meta 40
  [      cfp       ] AgenteManager → CargaEquilibrio: Arma una carga de 24-48 créditos, meta 40
  [      cfp       ] AgenteManager → CargaPreferencias: Arma una carga de 24-48 créditos, meta 40
  [    propose     ] CargaAvance → AgenteManager: 2 ofertas; la mejor (autoevaluación 0.692): LIIS2105, LIIS2112, LIIB2104, LICB2102, LIIE2104, LIIS2113
  [    propose     ] CargaEquilibrio → AgenteManager: 2 ofertas; la mejor (autoevaluación 0.859): LIIS2105, LIIS2112, LIIB2104, LICB2102, LIIS2114, LIIS2108, LIIN2103
  [    propose     ] CargaPreferencias → AgenteManager: 2 ofertas; la mejor (autoevaluación 0.948): LIIS2105, LIIS2112, LIIB2104, LICB2102, LIIE2104, LIIS2106
  [      cfp       ] AgenteManager → AgenteHorarios: Asignar grupos a 6 combinaciones
  [    propose     ] AgenteHorarios → AgenteManager: 6 propuestas con horario
  [accept-proposal ] AgenteManager → CargaPreferencias: P5 (92.29): LIIS2105, LIIS2112, LIIB2104, LICB2102, LIIE2104, LIIS2106
  [reject-proposal ] AgenteManager → CargaPreferencias: P6 (92.29)
  [reject-proposal ] AgenteManager → CargaAvance: P1 (91.88)
  [reject-proposal ] AgenteManager → CargaAvance: P2 (91.38)
  [reject-proposal ] AgenteManager → CargaEquilibrio: P3 (91.19)
  [reject-proposal ] AgenteManager → CargaEquilibrio: P4 (90.21)
  [     inform     ] CargaPreferencias → AgenteManager: carga adjudicada: 40 créditos, 6 materias
```

Es el protocolo de la clase (tema 2, "Asignación de tareas: protocolo Contract Net"), con
sus 4 pasos:

| Paso de la clase | Aquí |
|---|---|
| **1. Anuncio**: el Manager publica la tarea | 3 `cfp` con la misma tarea, uno a cada AgenteCarga contratista |
| **2. Oferta**: los contratistas evalúan su capacidad y mandan su *bid* | Cada uno manda sus 2 mejores cargas y la nota que él mismo les pone (autoevaluación) |
| **3. Adjudicación**: el Manager evalúa y asigna al mejor postor | Califica las 6 con la función **oficial** (0.30/0.25/0.25/0.20): `accept-proposal` al ganador, `reject-proposal` a los demás |
| **4. Resultado**: el contratista ejecuta y reporta | `inform` del ganador con la carga adjudicada |

Cómo leerlo:

- **El Historial va primero** y manda las 28 materias válidas, ordenadas por prioridad.
  LIIS2105 va primero porque Ana la reprobó y desbloquea 4 materias. Los 3 contratistas
  trabajan sobre esa misma lista.
- **Los 3 contratistas son el mismo tipo de agente** (`AgenteCarga`) con distinta
  estrategia, es decir, distintos pesos al calificar sus combinaciones
  (`config.ESTRATEGIAS_CARGA`):

  | Contratista | Carga | Prioridad | Interés | Horario | Facilidad | En pocas palabras |
  |---|---|---|---|---|---|---|
  | CargaAvance | 0.3 | 0.6 | 0.1 | 0 | 0 | Primero lo urgente: reprobadas, rezagadas, llave |
  | CargaEquilibrio | 0.5 | 0.1 | 0.1 | 0 | 0.3 | Cerca de la meta y con pocas materias difíciles |
  | CargaPreferencias | 0.3 | 0.1 | 0.3 | 0.3 | 0 | Materias de interés y con grupo en el turno y la modalidad que pide |

- **La autoevaluación no decide.** CargaPreferencias se puso 0.948 y CargaAvance 0.692,
  pero cada uno se califica con su propia escala y esas notas no se comparan. El Manager
  adjudica con su función. (Es la idea de la diapositiva de subastas VCG: no conviene
  premiar lo que cada uno dice de sí mismo.)
- **Gana CargaPreferencias con P5 (92.29).** P5 y P6 empatan; el desempate es por
  identificador. Su carga es la de CargaAvance cambiando LIIS2113 por LIIS2106: Sistemas
  Embebidos I tiene grupo el viernes por la tarde, y Ana prefiere la tarde.

Son las performativas del protocolo Contract Net, con el estilo FIPA-ACL/KQML del tema 5.

### 6.2 La recomendación

```text
══════════════════════════════════════════════════════════════════════════════
 Ana Torres Medina (A001) · semestre 5 · Primavera 2027
 Preferencias: carga normal (~40 créditos, máx. 7 materias); turno vespertino; modalidad presencial
   ↳ interpretadas por: solo ontología
══════════════════════════════════════════════════════════════════════════════
 CARGA RECOMENDADA (40 créditos · puntuación 92.29/100) · la ofertó CargaPreferencias
  • LIIS2105 Programación Avanzada y Algoritm LIIS2105-B presencial Mar 11-13, Jue 11-13
  • LIIS2112 Diseño y Gestión de Bases de Dat LIIS2112-A presencial Lun 07-09, Mie 07-09
  • LIIB2104 Proyecto de Ingeniería IV        LIIB2104-B presencial Lun 17-19
  • LICB2102 Estadística y Probabilidad       LICB2102-A presencial Lun 19-21, Mie 19-21
  • LIIE2104 Circuitos Electrónicos I         LIIE2104-B presencial Mar 17-19, Jue 17-19
  • LIIS2106 Sistemas Embebidos I             LIIS2106-A presencial Vie 15-19
  Criterios: avance 84.3 | compatibilidad 100 | carga 100.0 | preferencias 85.0

 Licitación: Avance 91.88 | Equilibrio 91.19 | Preferencias 92.29 ✔
 Shapley: Historial 39.41 | Carga 30.07 | Horarios 22.8
 Shapley contratistas: Avance 5.22 | Equilibrio 4.88 | Preferencias 5.63
```

- **"interpretadas por: solo ontología"**: como no se escribió ninguna petición (`-p`), se
  usan las preferencias que Ana tiene guardadas en la ontología (`PreferenciaHorario`,
  `PreferenciaModalidad` y `PreferenciaCarga`).
- **Los 4 criterios** son los del Proyecto 2 (0 a 100 cada uno). La puntuación es
  0.30·84.3 + 0.25·100 + 0.25·100 + 0.20·85 = **92.29**. La [sección 15.3](#153-la-función-de-evaluación-paso-a-paso)
  hace el cálculo completo.
- **¿Por qué dos materias van en la mañana si Ana prefiere la tarde?** El grupo de la tarde
  de LIIS2105 (A, lunes y miércoles de 17 a 19) choca con LIIB2104-B, y el de LIIS2112
  (B, lunes y miércoles de 17 a 19) también. El sistema prefirió recursar la materia llave
  y avanzar en Bases de Datos en la mañana antes que dejarlas fuera.
- **Licitación**: la mejor puntuación oficial de cada contratista; ✔ marca al ganador.
- **Shapley**: cuánto aportó cada rol. B (Carga) es ahora el **equipo** de los 3
  contratistas. La suma es 39.41 + 30.07 + 22.8 = 92.28 ≈ 92.29 (redondeo), igual a la
  puntuación final (propiedad de eficiencia).
- **Shapley contratistas**: un segundo juego, solo entre los 3 AgentesCarga (sección 15.5).

### 6.3 La explicación y los archivos generados

```text
 Ana, para Primavera 2027 te recomendamos inscribir 6 materias (40 créditos): Programación
 Avanzada y Algoritmos, Diseño y Gestión de Bases de Datos I, Proyecto de Ingeniería IV,
 Estadística y Probabilidad, Circuitos Electrónicos I, Sistemas Embebidos I. Se prioriza
 recursar Programación Avanzada y Algoritmos porque es prerrequisito de materias
 posteriores. La combinación cumple el rango institucional de 24–48 créditos y obtuvo
 92.29/100 en la evaluación del coordinador. No hay choques de horario y el ajuste a tus
 preferencias de turno, modalidad e intereses es de 85.0/100.
   (plantilla (sin LLM))
══════════════════════════════════════════════════════════════════════════════
 reporte   → salidas/reporte_A001.md
 trazas    → salidas/trazas_A001.json
 ontologia → salidas/kb_A001.owl
```

Con `--sin-llm` el texto sale de una plantilla. Con LLM, lo redacta el modelo (paso 8).

### 6.4 Variantes útiles

```text
$ python main.py recomendar A001 --sin-llm -q          # -q oculta los mensajes cfp/propose
$ python main.py recomendar A002 --sin-llm -p "quiero algo ligero, en la mañana y sin clases el viernes"
```

Aunque uses `--sin-llm`, puedes escribir una petición con `-p`: el **analizador por
reglas** la interpreta. Detecta tipo de carga, turno, modalidad, días libres, materias
de interés o a evitar (por nombre, sigla de Intrauia como `LIIS2109`, siglas como "IA"
o palabras como "redes" o "nube") y un número de materias.

Con los nombres reales hubo que cuidar dos cosas en `carga/preferencias.py`:
- **Palabras comunes que parecían siglas o palabras clave.** "Sistemas Informáticos en los
  Negocios" daría la sigla "sin", así que "sin viernes" la habría marcado para evitar. Lo
  mismo pasaba con "por" (Dibujo por Computadora) y "al" (Álgebra Lineal). Esas palabras
  ya no cuentan.
- **Varias materias comparten palabras.** "Inteligencia artificial" también tocaba
  "Inteligencia de Datos". Ahora, en cada frase, solo cuentan las materias que mejor
  coinciden.

---

## 7. Paso 5: leer el reporte Markdown

Abre `salidas/reporte_A003.md` en VS Code y presiona `Ctrl+Shift+V` para ver la vista
previa. Estas son sus secciones, con los valores reales de A003:

| Sección | Qué muestra |
|---|---|
| **Preferencias interpretadas** | Tabla campo · valor · **fuente** (ontología, petición con LLM o petición con reglas). Así ves de dónde salió cada preferencia |
| **Recomendación final** | La explicación y quién la redactó |
| **Propuesta ganadora** | Clave, materia, créditos, grupo, modalidad, horario y profesor |
| **Horario semanal** | Cuadrícula lunes a viernes por hora (un `⚠` marca los choques) |
| **Materias descartadas** | P. ej. `LIIS2107 Sistemas Embebidos II: falta prerrequisito: LIIS2106` o `LYRU2102 …: no se oferta en Primavera 2027` |
| **Licitación entre los AgentesCarga** | Por contratista: sus pesos, cuántas ofertas mandó, su mejor puntuación oficial, su autoevaluación y si ganó, empató o fue rechazado |
| **Propuestas evaluadas** | Las 6 propuestas, **quién las ofertó**, sus 4 criterios y su total. La ganadora lleva ✅ |
| **Valores de Shapley** | La tabla v(S) de las 8 coaliciones y φ de cada agente, con su porcentaje |
| **Shapley entre los contratistas** | El segundo juego: v(S) de las 8 coaliciones de AgentesCarga y φ de cada uno |
| **Inferencias de HermiT** | Solo si usaste `--razonador` |
| **Mensajes del Contract Net** | El diálogo FIPA completo |
| **Trazas de ejecución** | Hora, agente, tarea, salida, tiempo, éxito y score (sección 3.2 del Proyecto 2) |

Fragmento real (A003 de la demo, con la petición "quiero adelantar, en línea, me interesa
IA y la nube, no quiero métodos numéricos"; los números cambian si cambias la petición):

```text
| Coalición S | v(S) |          | Agente              | φ     | %     |
|---|---|                       |---|---|---|
| {}      | 0.0   |             | AgenteCarga (B)     | 31.31 | 37.1% |
| {A}     | 53.78 |             | AgenteHistorial (A) | 28.1  | 33.3% |
| {B}     | 46.53 |             | AgenteHorarios (C)  | 24.97 | 29.6% |
| {C}     | 52.82 |             | Suma                | 84.38 ≈ v(N) | 100% |
| {A,B}   | 72.75 |
| {A,C}   | 53.78 |
| {B,C}   | 67.45 |
| {A,B,C} | 84.39 |
```

Con Sofía el rol más valioso es el **AgenteCarga** (el equipo de contratistas). Ella tiene 28 materias válidas y
quiere una carga pesada, así que el problema difícil ya no es "qué puede cursar", sino
"cuáles 8 de esas 28". Sin el AgenteCarga, la versión ingenua toma 5 materias en orden
del plan.

Y entre los contratistas pasa algo que vale la pena mostrar en clase. Los 3 ofertan
**la misma** mejor carga (84.39). Cualquiera de ellos, solo, logra lo mismo que los 3
juntos, así que Shapley les paga lo mismo: 10.2 cada uno. Es el axioma de **simetría**
de la diapositiva ("aportes idénticos, pagos idénticos"). El contrato se adjudica a
CargaAvance solo por ser el primero en ofertar; en la tabla de licitación los otros dos
aparecen como "empata con la ganadora".

`salidas/trazas_<mat>.json` contiene lo mismo en formato JSON. Ejemplo de un evento real:

```json
{
  "timestamp": "2026-11-06T21:46:38",
  "agent": "AgenteManager",
  "task": "evaluar_propuestas_contract_net",
  "input": "6 propuestas",
  "output": "gana P1 con 84.39",
  "execution_time": 0.0004,
  "success": true,
  "score": 84.39,
  "detalles": {}
}
```

---

## 8. Paso 6: el razonador HermiT

```text
$ time python main.py recomendar A003 -q --sin-llm --razonador -p "quiero adelantar, en línea, me interesa IA y la nube, no quiero métodos numéricos"
...
python main.py recomendar A003 ...  5.345 total
```

Con el plan real la ontología tiene 452 individuos (antes 203), por eso HermiT tarda unos
4 s en lugar de 2.

`--razonador` ejecuta **HermiT** (en Java, con el límite de memoria en 512 MB) sobre la
ontología. HermiT **clasifica automáticamente** los individuos en las clases definidas
que se agregaron a tu TBox. Resultado real (está en el reporte):

| Clase definida (Manchester) | Individuos inferidos por HermiT |
|---|---|
| `MateriaLlave` ≡ `Materia and esPrerrequisitoDe min 2 Materia` | LIIS2105, LIIS2112, LYRU2101 |
| `MateriaSeriada` ≡ `Materia and tienePrerrequisito some Materia` | 35 materias (todas las que tienen seriación en Intrauia) |
| `GrupoVespertino` ≡ `Grupo and tieneBloqueHorario some (BloqueHorario and turno value "vespertino")` | 48 grupos |
| `GrupoMatutino` ≡ `Grupo and tieneBloqueHorario some (BloqueHorario and turno value "matutino")` | 49 grupos |
| `GrupoEnLinea` ≡ `Grupo and tieneModalidad some ModalidadEnLinea` | 15 grupos: LHLF1201-B, LICB1202-B, LICB1229-A, LICB1231-A, LIIN2103-A, LIIN2103-B, LIIN2105-A, LIIN2106-B, LIIS2102-A, LIIS2106-B, LIIS2110-B, LIIS2111-A, LIIS2114-A, LIIS2116-B, LIIS2118-B |
| `EstudianteConAdeudo` ≡ `Estudiante and tieneRegistro some RegistroReprobado` | A001, A002 |

Nadie escribió "LIIS2112 es MateriaLlave": **el razonador lo dedujo**, porque en el plan
real Diseño y Gestión de Bases de Datos I es seriación de Bases de Datos II (LIIS2115) y de
Cómputo en la Nube (LIIS2118). Las otras dos son Programación Avanzada y Algoritmos
(desbloquea 4) y Persona y Humanismo (desbloquea 15: las 13 optativas de Reflexión
Universitaria, Dilemas Éticos en la Ingeniería y Reflexión y Acción Social). Para que `min 2` funcione se declaró `AllDifferent` entre las materias.
OWL no asume nombres únicos (supuesto de mundo abierto), así que sin esa declaración
HermiT no podría contar.

En el plan real cada materia tiene **a lo más una** seriación, por eso no hay ninguna
materia con dos prerrequisitos.

---

## 9. Paso 7: encender Ollama SOLO con CPU

### 9.1 Por qué hay que usar el script

Tu notebook anterior terminaba con:

```text
InternalServerError: Error code: 500 - llama runner process has terminated:
ROCm error: invalid device function
```

Ollama intentaba usar la Radeon integrada de tu Ryzen (gfx90c), que ROCm no soporta. Un
fallo así en el driver `amdgpu` puede congelar o reiniciar la laptop. El script
`iniciar_ollama_cpu.sh` oculta todas las GPUs a Ollama, así que **nunca toca el driver
de video**.

### 9.2 Encenderlo

Abre una **segunda terminal** (déjala abierta mientras usas el LLM):

```text
$ cd ~/Documentos/universidad/agentes/parcial-3/agente-carga3
$ ./iniciar_ollama_cpu.sh
Ollama (solo CPU) en http://127.0.0.1:11435  · modelos: /home/jesus/.ollama/models
Ctrl+C para detenerlo.
time=... level=INFO source=types.go:60 msg="inference compute" id=cpu library=cpu ...
```

La línea clave es **`library=cpu`**.

Detalles del servidor:
- Escucha en el puerto **11435**, para no chocar con el servicio de Fedora en 11434, que
  además no tiene modelos.
- Usa tus modelos ya descargados en `~/.ollama/models`; no descarga nada.
- Corre con prioridad baja (`nice`) y carga un solo modelo a la vez.
- Libera la RAM a los 2 minutos sin uso.

### 9.3 Verificarlo

En la primera terminal:

```text
$ python main.py diagnostico
✔ Ollama responde en http://127.0.0.1:11435 — modelos: llama3.1:8b, llama3.2:latest, gemma3:1b
✔ Ollama responde en http://127.0.0.1:11434 — modelos: NINGUNO
  RAM disponible: 5.4 GB de 14.9 GB
  Energía: cargador conectado ✔ — batería 100%, 8.02 V (mín. de diseño 7.64 V)
  Modelo configurado: llama3.2 | hilos: 4 | contexto: 4096
```

> **Batería.** Usa el LLM **con el cargador conectado**. Con la batería desgastada, el
> pico de consumo de la CPU al correr el modelo puede bajar el voltaje por debajo del
> mínimo y apagar la laptop de golpe (sin dejar log). Por eso, si no hay cargador,
> `ClienteLLM` desactiva el LLM, avisa con `⚠ LLM desactivado: laptop en batería` y el
> sistema sigue solo con reglas. Para forzarlo bajo tu riesgo: `LLM_EN_BATERIA=1`.
> Por la misma razón el LLM usa 4 hilos por defecto (antes 6).

Mientras un modelo está cargado, `diagnostico` muestra además:

```text
    cargado: llama3.2:latest (2.5 GB) → CPU ✔
```

Si alguna vez dice **`⚠ USANDO GPU`**, detén todo (Ctrl+C) y revisa la sección 16.
También puedes comprobarlo directamente; esto se midió durante la prueba:

```text
$ curl -s 127.0.0.1:11435/api/ps
Modelo cargado: llama3.2:latest | RAM 2.48 GB | VRAM 0 bytes
```

> 💡 Si `diagnostico` muestra **menos de 3.5 GB libres**, cierra el navegador antes de
> usar el LLM. No uses `llama3.1:8b`: necesita más de 6 GB.

---

## 10. Paso 8: recomendación con LLM (lenguaje natural)

> ℹ️ Las salidas de este paso y del 9 son de la verificación del 5 de noviembre, **con el
> catálogo sintético anterior** (IAR501 = Inteligencia Artificial, SEG501 = Seguridad,
> CMP501 = Compiladores). Con el plan real el mecanismo es idéntico: el LLM recibe el
> catálogo de 79 nombres reales y sus respuestas pasan por la misma validación. Para
> repetirlo, conecta el cargador (sección 9.3) y usa, por ejemplo: *"me interesan la
> inteligencia artificial y la seguridad computacional, pero no quiero métodos numéricos"*.

Con Ollama encendido, ya **no** pongas `--sin-llm`:

```text
$ time python main.py recomendar A003 -p "Ya quiero acabar la carrera, así que dame bastantes materias. Vivo lejos, prefiero en línea y por la tarde. Me interesan la inteligencia artificial y la seguridad, pero no quiero compiladores"
```

### 10.1 Qué hace el LLM (solo 2 cosas)

**1. Interpreta la petición** (AgenteHorarios). Se le pide un JSON con un esquema fijo y
esto fue lo que devolvió `llama3.2`:

```json
{ "tipo_carga": "pesada", "turno": "vespertino", "modalidad": "en_linea",
  "dias_libres": [], "materias_interes": ["Inteligencia Artificial", "Seguridad Informática"],
  "materias_evitar": ["Compiladores"], "max_materias": null }
```

Después, ese JSON se **valida en Python**:
- los valores tienen que estar dentro del esquema;
- los nombres de materias se convierten a claves del catálogo;
- se descarta cualquier materia que no aparezca en tu texto (anti-alucinación);
- se descartan las materias que el alumno ya aprobó.

Así queda en el reporte:

```text
| Campo            | Valor                 | Fuente         |
| tipo_carga       | pesada                | petición (LLM) |
| turno            | vespertino            | petición (LLM) |
| modalidad        | en_linea              | petición (LLM) |
| materias_interes | ['IAR501', 'SEG501']  | petición (LLM) |
| materias_evitar  | ['CMP501']            | petición (LLM) |
```

**2. Redacta la explicación final** (AgenteManager). Solo recibe las materias, los
créditos, los motivos y los criterios; **no recibe horarios**. Salida real:

```text
 Sofía, se recomienda esta carga debido a tu preferencia por una carga pesada y tu interés
 en las materias de Inteligencia Artificial y Seguridad Informática. Además, la carga
 equilibrada y la compatibilidad con tu turno vespertino son aspectos clave que se han
 tenido en cuenta al seleccionar estas materias.

 La carga recomendada ha sido diseñada para satisfacer tus necesidades académicas y
 personales, evitando materias que no te interesan, como CMP501. La obligatoriedad de
 Ciencia de Datos y Sistemas Distribuidos garantiza una formación sólida en estos temas
 fundamentales del campo.
   (LLM (llama3.2))
```

El LLM **no decide** qué materias van. Eso lo decide el Contract Net. Aunque el modelo se
equivoque, la recomendación sigue siendo correcta.

### 10.2 Tiempos reales y caché

| Ejecución | LLM | Tiempo total |
|---|---|---|
| 1ª vez (nada en caché) | 2 llamadas | **67 s** |
| 2ª vez (la interpretación ya estaba en caché) | 1 llamada | **24 s** |
| 3ª vez (todo en caché) | 0 llamadas | **0.4 s** |

Las respuestas del LLM se guardan en `salidas/cache_llm.json`. Si repites la misma
petición, por ejemplo al presentar en clase, la respuesta es instantánea. La última línea
del reporte indica cuántas llamadas se hicieron:

```text
_LLM: llama3.2 · llamadas: 0 · tiempo LLM: 0.0 s ·_
```

### 10.3 Si el LLM redacta algo falso

Antes de aceptar la redacción, un guardia la revisa. Se rechaza si:
- nombra una materia que no está en la propuesta;
- dice "de lunes a viernes" o escribe una hora como "13:00", aunque el LLM nunca recibió horas;
- usa listas;
- dice "solo lunes y miércoles" cuando hay clase otros días;
- quedó cortada a la mitad.

Si la rechaza, verás:

```text
   (plantilla (la redacción del LLM mencionaba datos que no existen y se descartó))
```

Se probó con el texto alucinado real que produjo `llama3.2` en la primera prueba: el
guardia lo rechazó (`False`), aceptó un texto correcto (`True`) y rechazó uno que
mencionaba Compiladores (`False`).

---

## 11. Paso 9: orquestación con CrewAI

> ℹ️ Salidas del 5 de noviembre, con el catálogo sintético anterior (ver la nota del paso 8),
> y **antes de la mejora 1**. Desde la mejora 1, la herramienta `evaluar_carga_academica`
> lista la mejor oferta de cada uno de los 3 contratistas, y `coordinar_carga` corre el
> Contract Net completo con la licitación. El resultado oficial es el mismo que el de
> `recomendar`.

Este modo cumple la "capa de ejecución y orquestación mediante CrewAI" del Proyecto 2.
Requiere Ollama encendido (paso 7).

```text
$ time python main.py crew A001 -p "me interesa inteligencia artificial y prefiero la tarde"
```

**Tarda unos 4 minutos** en tu laptop. Es normal: cada agente hace al menos 2 llamadas al
LLM en CPU.

### 11.1 Qué vas a ver

CrewAI imprime recuadros de colores. El orden real fue:

```text
📋 Task Started   Agent: Analista de historial académico y requisitos
🔧 Tool Execution Started (#1)   Tool: consultar_historial_academico
✅ Tool Execution Completed (#1)
✅ Agent Final Answer   ...resumen del historial...
📋 Task Completed

📋 Task Started   Agent: Analista de carga académica
🔧 Tool: evaluar_carga_academica  →  ✅ Completed  →  Final Answer  →  Task Completed

📋 Task Started   Agent: Analista de horarios y preferencias del estudiante
🔧 Tool: analizar_horarios_y_preferencias  →  ✅ Completed  →  Final Answer  →  Task Completed

📋 Task Started   Agent: Coordinador y recomendador académico
🔧 Tool: coordinar_carga  →  ✅ Completed  →  Final Answer  →  Task Completed
```

Al final aparece el mismo resumen de siempre, con la redacción hecha por CrewAI:

```text
 CARGA RECOMENDADA (40 créditos · puntuación 89.17/100)
  • IAR501  Inteligencia Artificial          IAR501-B  presencial Lun 17-19, Mie 17-19
  • SOP401  Sistemas Operativos              SOP401-A  presencial Mar 09-11, Jue 09-11
  ...
 La propuesta ganadora para la carga de Ana Torres Medina es una combinación de 5 materias
 que cumple con todos los criterios establecidos. ...
   (CrewAI (secuencial, llama3.2))
python main.py crew A001 -p ...  3:58.69 total
```

En el reporte, las trazas incluyen las llamadas de CrewAI:

```text
| 18:37:50 | AgenteHistorial | crewai:consultar_historial | 10 válidas    | ✔ |
| 18:38:30 | AgenteCarga     | crewai:evaluar_carga       | 6 combinaciones | ✔ |
| 18:39:19 | AgenteHorarios  | crewai:analizar_horarios   | 3 propuestas  | ✔ |
| 18:41:31 | AgenteManager   | crewai:kickoff_secuencial  | 987 caracteres | ✔ |
```

### 11.2 Por qué ya no truena

- Las herramientas ejecutan la lógica determinista (ontología y Contract Net) y devuelven
  un **resumen corto**. El LLM no tiene que razonar sobre la ontología.
- Cada herramienta recibe solo la matrícula. Con un solo parámetro, un modelo de 3B se
  equivoca mucho menos al llamar herramientas.
- `max_iter=3`, sin memoria de CrewAI, sin delegación entre especialistas y sin telemetría.
- Ollama corre en CPU.
- Si CrewAI falla o el coordinador inventa datos, el resultado se calcula de todas formas
  y la redacción pasa por el mismo guardia del paso 8.

### 11.3 Si Ollama está apagado

```text
$ python main.py crew A001
⚠ CrewAI necesita Ollama (http://127.0.0.1:11435: sin respuesta; http://127.0.0.1:11434: no tiene el modelo 'llama3.2').
  Levántalo con ./iniciar_ollama_cpu.sh  — mientras tanto se ejecuta el MAS sin CrewAI.
 CARGA RECOMENDADA (40 créditos · puntuación 92.29/100)
```

(Esta salida sí es del 6 de noviembre, con el plan real.)

### 11.4 Modo jerárquico

```text
$ python main.py crew A002 --proceso jerarquico
```

Es el proceso que propone el Proyecto 2 (sección 1.3): el **Manager no tiene
herramientas propias**, recibe las 4 tareas y **decide a qué especialista delegar** cada
una. Resultado real:

```text
(en los recuadros todo aparece bajo "Agent: Coordinador y recomendador académico",
 porque en modo jerárquico CrewAI muestra al Manager como responsable de las tareas)

 CARGA RECOMENDADA (32 créditos · puntuación 96.25/100)
  • MAT201  Cálculo Integral                 MAT201-A  presencial Lun 07-09, Mie 07-09
  • BDD301  Bases de Datos                   BDD301-A  presencial Lun 09-11, Mie 09-11
  • FIS201  Física I                         FIS201-A  presencial Mar 09-11, Jue 09-11
  • PRG301  Estructuras de Datos             PRG301-A  presencial Mar 07-09, Jue 07-09
 ...
 En primer lugar, se incluye el Cálculo Integral (MAT201), que es una materia fundamental
 en la carrera y proporciona un buen avance académico. Además, su prioridad es del 0.7 ...
   (CrewAI (jerarquico, llama3.2))
timeout 900 python main.py crew A002 --proceso jerarquico  ...  5:20.72 total
```

Las trazas confirman que el Manager sí delegó en los tres especialistas:

```text
| 18:42:13 | AgenteHistorial | crewai:consultar_historial | 7 válidas       | ✔ |
| 18:43:37 | AgenteCarga     | crewai:evaluar_carga       | 6 combinaciones | ✔ |
| 18:44:41 | AgenteHorarios  | crewai:analizar_horarios   | 3 propuestas    | ✔ |
| 18:47:15 | AgenteManager   | crewai:kickoff_jerarquico  | 1150 caracteres | ✔ |
```

**¿Secuencial o jerárquico?** Ambos dan la **misma recomendación**, porque la decide el
Contract Net y no el LLM. El jerárquico es más fiel al diseño del Proyecto 2 y hace más
llamadas al LLM: 5 min 20 s contra 4 min. Para la presentación usa el jerárquico si tienes
tiempo; para probar rápido, el secuencial o `recomendar`.

---

## 12. Paso 10: el notebook de demostración

`demo.ipynb` recorre el sistema celda por celda y sirve para la presentación.

1. Abre `demo.ipynb` en VS Code.
2. Arriba a la derecha, en **Select Kernel**, elige **"agente-carga3 (.venv)"**.
3. Ejecuta todo con **Run All**.

Para usar el LLM, enciende antes `./iniciar_ollama_cpu.sh` y cambia `USAR_LLM = False` a
`True` en la primera celda.

| Celda | Qué hace | Qué verás (salida real, con `USAR_LLM = False`) |
|---|---|---|
| 1 | Diagnóstico + carga la ontología | Estado de Ollama y RAM |
| 2 | Alumno A001 según la ontología | `Ana Torres Medina \| semestre 5 \| promedio 8.78`, aprobadas y reprobadas |
| 3 | Interpreta "Me interesa inteligencia artificial, prefiero la tarde y no quiero clases los viernes" | `...sin clases: Viernes; le interesa: LIIS2109` |
| 4 | Contract Net (licitación) | Mensajes FIPA y las 6 propuestas con su autor. `Ganador del contrato: CargaAvance` con P2 (93.01) |
| 5 | Shapley entre roles | Las 8 coaliciones: `v({A})=71.88 … v({A,B,C})=93.01` y `suma: 93.0 = v(N)` (redondeo) |
| 6 | Shapley entre contratistas | `CargaAvance ofertas=2 mejor oficial=93.01 autoevaluación=0.67 GANA`, las 8 coaliciones y `φ contratistas: Avance 7.94, Equilibrio 6.45, Preferencias 6.74`, `suma: 21.13 = v(N)` |
| 7 | HermiT | Las 6 clases definidas con sus individuos |
| 8 | Cierra y muestra el reporte | El reporte Markdown completo dentro del notebook |

Verificación automática: **8 celdas de código ejecutadas, 0 con error.**

Fíjate en que aquí gana **CargaAvance**, mientras que en el paso 4, para la misma Ana pero
sin petición, ganó CargaPreferencias. Lo que pide el alumno cambia qué estrategia sirve
mejor, y eso es justo lo que la competencia del Contract Net aprovecha.

Observa el efecto de la petición de la celda 3:
- **"Me interesa inteligencia artificial"** mete Fundamentos de Inteligencia Artificial
  (LIIS2109, de 7.º semestre y sin seriación), que en el paso 4 no aparecía.
- **"No quiero clases los viernes"** saca Sistemas Embebidos I, que en el paso 4 iba el
  viernes de 15 a 19, y deja Fundamentos de Sistemas Operativos en su grupo de martes y
  jueves (LIIS2114-A) en lugar del de viernes (LIIS2114-B). Ninguna materia de la carga
  ganadora tiene clase el viernes.

El día libre pedido pesa **6**, el doble que un turno pedido (3). Con peso 3, el grupo del
viernes ganaba porque sí cumplía el turno vespertino; en la verificación del 6 de
noviembre eso se detectó y se corrigió.

---

## 13. Paso 11: consultar los resultados en Protégé (DL Query)

Cada ejecución escribe sus resultados **de vuelta en la ontología**
(`salidas/kb_<mat>.owl`). Se usan clases y propiedades que ya existían en tu TBox del
Proyecto 2: `puedeCursar`, `PropuestaCarga`, `TrazaEjecucion` y `valorShapley`. La
ontología funciona como memoria compartida del MAS.

### 13.1 Abrirla

1. Ejecuta `python main.py recomendar A001 --sin-llm` (genera `salidas/kb_A001.owl`).
2. Protégé → **File → Open** → `salidas/kb_A001.owl`.
3. **Reasoner → HermiT** → **Reasoner → Start reasoner**.
4. Pestaña **DL Query**. Escribe la consulta y marca **Instances**.

> ⚠️ **Abre solo un `kb_*.owl` a la vez.** Cada archivo trae los mismos agentes con un
> `valorShapley` distinto, y esa propiedad es *funcional* (un solo valor). Si mezclas dos
> archivos, HermiT reporta la ontología como **inconsistente**. Me pasó al verificar:
> es el comportamiento correcto del razonador, no un error del sistema.

### 13.2 Consultas verificadas

Estas consultas se ejecutaron con HermiT sobre `kb_A001.owl` y estos son sus resultados
reales:

| Consulta DL Query (sintaxis Manchester) | Resultado esperado |
|---|---|
| `Materia and puedeSerCursadaPor value est_A001` | 28: LICB1229, LICB2102, LIIB2104, LIIE2103, LIIE2104, LIII0428, LIIN2103, LIIN2105, LIIN2106, LIIN2110, LIIS2105, LIIS2106, LIIS2108, LIIS2109, LIIS2112, LIIS2113, LIIS2114, LIIS2117, LIIS2120, LIIS2122, LIIS2123, LIIS2124, LRSS2102, LYRU2104, LYRU2110, LYRU2111, LYRU2113, LYRU2118 |
| `MateriaLlave` | 3: LIIS2105, LIIS2112, LYRU2101 |
| `EstudianteConAdeudo` | 2: est_A001, est_A002 |
| `Grupo and esOfertaDe value mat_LIIS2109 and tieneModalidad some ModalidadPresencial` | 2: LIIS2109-A, LIIS2109-B |
| `Grupo and enConflictoCon value grp_LIIS2112_B` | 4: LIIB2102-A, LIIB2104-B, LIIS2102-B, LIIS2105-A |
| `GrupoVespertino and GrupoEnLinea` | 7: LICB1202-B, LICB1229-A, LICB1231-A, LIIN2103-B, LIIN2105-A, LIIN2106-B, LIIS2111-A |
| `Materia and tienePrerrequisito some (Materia and aprobadaPor value est_A002)` | 5: LICB2103, LICB2108, LIIB2102, LIIB2103, LIIM2102 |
| `PropuestaCarga and esValida value true` | 1: la propuesta ganadora (`prop_A001_<fecha>_P5`) |
| `PropuestaCarga and puntuacion some xsd:decimal[>= 92.0]` | 2 propuestas: P5 y P6 (las dos con 92.29) |
| `Agente and valorShapley some xsd:decimal[> 25.0]` | 2: AgenteHistorial (39.41), AgenteCarga (30.07, el equipo) |
| `PropuestaCarga and generadaPor value agente_carga_preferencias` | 2: P5 y P6, las 2 ofertas de CargaPreferencias |
| `AgenteCarga and generaPropuesta some (PropuestaCarga and esValida value true)` | 1: CargaPreferencias (el ganador del contrato) |

En Protégé los grupos aparecen con su nombre de individuo (por ejemplo `grp_LIIS2109_A`) y
las materias como `mat_LIIS2109`.

Cómo leer algunas:
- **`generaPropuesta some (… esValida value true)`** responde "¿qué contratista ganó?".
  Nadie escribió `generaPropuesta`: el sistema solo guarda `generadaPor` en cada
  propuesta, y el razonador deduce la inversa porque así está declarada en tu TBox.
  Tu propia TBox ya lo anticipaba en el comentario de `generadaPor`: *"En Contract Net
  cada propuesta la emite un agente"*.
- **`valorShapley`** de los 3 contratistas (`agente_carga_avance`, etc.) viene del
  **segundo** juego (5.22, 4.88 y 5.63); el de `agente_carga` (30.07) es el del equipo en
  el juego entre roles. No se suman entre sí: son dos juegos distintos.
- **`enConflictoCon value grp_LIIS2112_B`** explica por qué Ana tomó Bases de Datos I en la
  mañana: el grupo de la tarde choca con LIIB2104-B (Proyecto de Ingeniería IV) y con
  LIIS2105-A (la materia que recursa).
- **`puedeSerCursadaPor`** es la inversa de `puedeCursar`. La escribió el AgenteHistorial,
  pero la consulta la resuelve el razonador.
- **`tienePrerrequisito some (… aprobadaPor value est_A002)`** devuelve las materias cuyo
  prerrequisito ya aprobó Luis, porque `some` es existencial (∃). Fíjate en dos cosas:
  - **LIIB2102 (Proyecto de Ingeniería II) aparece aunque Luis ya la aprobó.** La
    consulta no la excluye porque no se lo pediste.
  - **LICB2103 (Cálculo Diferencial e Integral) aparece aunque Luis la reprobó:** su
    prerrequisito (Matemáticas Universitarias) sí está aprobado, que es lo que pregunta la
    consulta.
- **`some` no significa "todos los prerrequisitos".** En el plan real cada materia tiene
  a lo más una seriación, así que aquí no se nota. Pero en general, en OWL "todos
  aprobados" no se puede deducir por el supuesto de mundo abierto (no saber que algo está
  aprobado no significa que no lo esté). Por eso esa regla la verifica el
  **AgenteHistorial en Python**, y su conclusión se guarda como `puedeCursar`.

---

## 14. Paso 12: el plan real, tus propios alumnos y la oferta

### 14.1 De dónde salen las materias: Intrauia

El plan de estudios **no se escribe a mano**: se exporta del portal y se importa con un
script.

**1.** En Intrauia → *Plan de estudios*, elige Licenciatura → (2801) Ingeniería en
Sistemas Computacionales. Selecciona la tabla completa, cópiala y pégala en
`datos/intrauia/plan_isc.txt`. Cada materia ocupa 3 líneas (clave, nombre, resto de
columnas) y el encabezado debe ser el del portal.

> ⚠️ `datos/intrauia/` está en `.gitignore` y **no se sube a git**. Si guardas la página
> completa con Ctrl+S, la carpeta `Intrauia_files/` trae datos de tu sesión (por ejemplo
> `Acceso.html`). Solo se versiona el catálogo limpio, `datos/plan_ibero.json`.

**2.** Importa y valida:

```text
$ python datos/importar_intrauia.py
✔ 79 materias importadas → datos/plan_ibero.json
  obligatorias: 56 (332 créditos) | optativas: 23 | seriadas: 35
```

El importador **se detiene** si la exportación tiene alguno de estos problemas:
- una seriación que apunta a una materia que no existe;
- una clave y una sigla de seriación que no coinciden;
- una materia seriada con otra de su mismo semestre o de uno posterior;
- un ciclo de seriación;
- claves o siglas duplicadas;
- horas totales que no cuadran.

Lo que viene del portal es real. Lo que el portal no trae se **deriva**, y así queda
anotado en el propio JSON (`_derivados`):

| Campo | Cómo se obtiene |
|---|---|
| `obligatoria` | Por área. Son optativas el Área Menor y las de Reflexión Universitaria, salvo Persona y Humanismo (LYRU2101) y Dilemas Éticos en la Ingeniería (LYRU2118) |
| `horas_semana` | Horas con docente / 16 semanas |
| `dificultad` (1–5) | **Sintética**: sube con el semestre, con 8 créditos y si la imparte una coordinación técnica. Reflexión y Servicio Social = 1, laboratorios ≤ 2 |

**3.** Regenera la ontología: `python main.py poblar`.

### 14.2 La oferta del periodo (sintética, pero generada del plan real)

`_generar_grupos()`, en `datos/semilla.py`, crea los grupos de Primavera 2027 con una
semilla fija (2027), así que siempre salen los mismos:
- Las materias de 1.er semestre no se abren en Primavera (solo en Otoño).
- Las obligatorias de semestre par o del Área Mayor tienen 2 grupos (uno matutino y otro
  vespertino). Las demás tienen 1.
- De las optativas, solo se abren las de `OPTATIVAS_OFERTADAS` (5 de Reflexión y 5 del
  Área Menor). Las demás aparecen como `no se oferta en Primavera 2027`.
- El horario depende de las horas con docente: 2 h son un bloque, 4 h son dos bloques
  (o un bloque de 4 h el viernes) y 6 h son tres bloques de 2 h o dos de 3 h.
- Un profesor (ficticio) nunca tiene dos grupos a la misma hora.

Para cambiar la oferta, edita `OPTATIVAS_OFERTADAS`, `PROFESORES` o la semilla del
generador.

### 14.3 Agregar un alumno

Esto se probó agregando una alumna A004. Los kárdex se arman con `_kardex(hasta_semestre,
excepto=…, extra=…)`: todas las obligatorias hasta ese semestre, menos las de `excepto` y
más las optativas de `extra`. Las calificaciones se generan alrededor de `media`.

**1.** En `datos/semilla.py`, dentro del diccionario `ESTUDIANTES`, después del bloque
de `"A003": {...},`, agrega:

```python
    "A004": {
        "id": "est_A004",
        "nombre": "Mariana López Cruz",
        "semestre": 4,
        "aprobadas": _kardex(3, excepto={"LICB0423"}, media=8.6, semilla=4),
        "reprobadas": {"LICB0423": 5.8},                               # Formulación de Proyectos
        "preferencias": {
            "turno": ("matutino", 2, "Prefiero en la mañana"),          # (valor, prioridad 1-3, texto)
            "modalidad": ("hibrida", 1, "Híbrida está bien"),           # presencial | en_linea | hibrida
            "carga": ("normal", 2, "Carga normal", 40, 7),              # (+ créditos objetivo, máx. materias)
        },
    },
```

Si el kárdex es incoherente, por ejemplo si dejas aprobada una materia cuya seriación
quitaste con `excepto`, `_kardex` falla con `kárdex incoherente: … sin [...]`.

**2.** Regenera la ontología y pruébala:

```text
$ python main.py poblar
✔ Ontología poblada: ontologia/carga_academica_poblada.owl
  475 individuos | 79 materias | 97 grupos | 4 estudiantes | 295 pares de grupos en conflicto

$ python main.py alumnos
...
A004  Mariana López Cruz       sem 4  prom 8.66  aprobadas 21  reprobadas ['LICB0423']

$ python main.py recomendar A004 --sin-llm -q
 CARGA RECOMENDADA (40 créditos · puntuación 92.22/100)
  • LICB0423 Formulación de Proyectos         LICB0423-A presencial Lun 07-09, Mie 07-09
  • LIIB2103 Proyecto de Ingeniería III       LIIB2103-A presencial Mar 11-13
  • LIIS2111 Diseño de Software I             LIIS2111-B presencial Vie 09-13
  • LICB2110 Electromagnetismo                LICB2110-B presencial Lun 11-13, Mie 11-13
  • LIIS2110 Paradigmas de Programación Avanz LIIS2110-B en_linea   Mar 07-09, Jue 07-09
  • LIIS2108 Redes Digitales e Internet       LIIS2108-B presencial Mar 09-11, Jue 09-11
 Shapley: Historial 37.92 | Carga 28.31 | Horarios 25.99
 ... Se prioriza recursar Formulación de Proyectos porque es prerrequisito de materias posteriores.
```

El promedio (8.66) y los créditos acumulados se calculan solos. Todos los grupos quedaron
en la mañana, como pidió. Formulación de Proyectos se prioriza porque es seriación de
Desarrollo de Proyectos (LIIS2117), que a su vez lo es de Implementación y Evaluación de
Proyectos.

**Otras cosas que puedes editar:**

| Quieres… | Edita | Formato |
|---|---|---|
| Cambiar el plan de estudios | `datos/intrauia/plan_isc.txt` → `python datos/importar_intrauia.py` | Exportación de Intrauia |
| Cambiar qué optativas se abren | `OPTATIVAS_OFERTADAS` en `datos/semilla.py` | Siglas de Intrauia |
| Un horario nuevo | `H` en `datos/semilla.py` | `"NOMBRE": [("Lunes", 15, 17), ("Miercoles", 15, 17)]` (horas enteras, 24 h, días sin acento) |
| El rango de créditos | `RESTRICCION_CREDITOS` en `datos/semilla.py` | `minimos` / `maximos` (24–48 es un supuesto, no viene de Intrauia) |

Para pesos, metas de carga, el tope de optativas o el modelo de LLM, edita
`carga/config.py` (`PESOS`, `CARGA_TIPO`, `MAX_OPTATIVAS`, `MODELO`).

Siempre que cambies datos, ejecuta `python main.py poblar`.

---

## 15. Cómo funciona por dentro (con un ejemplo numérico completo)

### 15.1 Flujo general

```text
 petición del alumno (opcional)
        │
        ▼
 [kb.py] carga la ontología UNA vez → objetos Python (materias, grupos, alumno vía SPARQL)
        │
        ▼
 [AgenteHorarios.interpretar_preferencias]  preferencias guardadas en la ontología
        │                                    + petición (LLM validado o reglas)
        ▼
 [contract_net.ejecutar]  ── Manager: cfp ──▶ Historial ─propose▶ materias válidas + prioridad
        │                 ── Manager: cfp ──▶ CargaAvance       ─propose▶ 2 ofertas ┐
        │                 ── Manager: cfp ──▶ CargaEquilibrio   ─propose▶ 2 ofertas ├ compiten
        │                 ── Manager: cfp ──▶ CargaPreferencias ─propose▶ 2 ofertas ┘
        │                 ── Manager: cfp ──▶ Horarios  ─propose▶ las 6 ofertas con grupos sin choques
        │                 ── Manager evalúa (0.30/0.25/0.25/0.20) → accept al ganador / reject
        │                 ◀─ inform ── contratista ganador (resultado)
        ▼
 [contract_net.valores_shapley]       8 coaliciones de roles (A, B = equipo de carga, C) → φ
 [contract_net.shapley_contratistas]  8 coaliciones de contratistas → φ de cada AgenteCarga
        │
        ▼
 [AgenteManager.explicar]  LLM (con guardia) o plantilla
        │
        ▼
 [reporte.py] reporte .md   [trazas.py] trazas .json   [persistencia.py] resultados → kb_<mat>.owl
```

### 15.2 Cada agente, con el caso de Ana (A001)

**AgenteHistorial** (`evaluacion.py: analizar_elegibilidad`). Revisa cada materia:
- si ya está aprobada, la ignora;
- si le falta un prerrequisito, la descarta con su motivo;
- si no tiene grupo con cupo en el periodo, la descarta;
- si pasa todo, la marca válida y le calcula una **prioridad** de 0 a 1.

```text
prioridad = w·rezago + 0.20·(obligatoria) + 0.25·(cuántas desbloquea, máx 3) + 0.15·(la reprobó)
            w = 0.40 si es obligatoria, 0.15 si es optativa
            rezago = min(1, max(0, (semestre del alumno − semestre ideal + 1) / 3))
```

En una optativa el semestre ideal solo dice desde cuándo se puede tomar. Por eso su rezago
pesa menos: si no, para una alumna de 6.º las optativas de Reflexión (semestre ideal 4)
parecerían más urgentes que sus obligatorias.

Prioridades reales de Ana (28 válidas). Las más altas: **LIIS2105 1.0**, LIIS2112 0.5,
LIIB2104 0.417, y LICB2102, LIIE2104, LIIS2113 y LIIS2114 con 0.333. Al final quedan las
optativas: las de Reflexión con 0.1 y las del Área Menor con 0.0. LIIS2105 llega al máximo:

```text
0.40·min(1, (5−3+1)/3) + 0.20 + 0.25·min(1, 4/3) + 0.15 = 0.40 + 0.20 + 0.25 + 0.15 = 1.0
   (2 semestres de atraso)   (oblig.)  (desbloquea 4)     (la reprobó)
```

Ana tiene 24 materias descartadas. Algunos ejemplos:
- `LIIS2110: falta prerrequisito: LIIS2105`, y lo mismo LIIS2116, LIIS2119 y LIIS2121:
  las 4 que bloquea la materia llave reprobada;
- `LIIS2115: falta prerrequisito: LIIS2112`;
- `LYRU2102: no se oferta en Primavera 2027`.

**AgenteCarga** (`agentes.py: AgenteCarga.ofertar`). Hay 3 instancias, una por
estrategia; las 3 hacen lo mismo y solo cambian los pesos del paso 4:
1. Toma hasta 12 materias candidatas: primero las de interés y luego las de mayor
   prioridad. Excluye las que el alumno quiere evitar.
2. Prueba todas las combinaciones de 1 hasta `max_materias` materias. Ana tiene 28 válidas,
   de las que se toman 12 candidatas, y máximo 7 materias:
   C(12,1)+…+C(12,7) = 3,301 combinaciones, evaluadas en milisegundos.
3. Descarta las que se salen del rango institucional (24–48 créditos) y las que llevan más
   de `MAX_OPTATIVAS` = 2 optativas.
4. Las califica con **sus** pesos (sección 6.1):
   `w_carga·carga + w_prioridad·prioridad + w_interés·interés + w_horario·horario + w_facilidad·facilidad`.
   Por ejemplo, CargaAvance usa 0.3·carga + 0.6·prioridad + 0.1·interés. "Horario" es el
   ajuste promedio del mejor grupo de cada materia, sin revisar choques, y "facilidad" es
   1 − (difíciles / materias).
5. Envía sus 2 mejores como oferta, con su nota (autoevaluación). Si una oferta repite
   una carga que ya mandó otro contratista, no se duplica.

El AgenteCarga original (antes de la mejora 1) era uno solo, con pesos 0.5/0.3/0.2, y
mandaba 6 combinaciones. Esos pesos siguen como valor por omisión
(`AgenteCarga.PESOS_ORIGINALES`).

**AgenteHorarios** (`agentes.py: AgenteHorarios.asignar`):
1. Para cada combinación prueba **todas** las asignaciones de grupos (producto cartesiano).
2. Elige la de **menos choques** y, si empatan, la de **mejor ajuste** a turno, modalidad
   y días libres.
3. Si un choque es inevitable, propone además una variante sin la materia de menor
   prioridad que choca.

El ajuste de un grupo es un promedio ponderado por la prioridad de cada preferencia. Con
Ana (turno vespertino con peso 3, presencial con peso 2; un día libre pedido pesaría 6):

| Grupo | Turno | Modalidad | Ajuste |
|---|---|---|---|
| LIIB2104-B (Lun 17-19, presencial) | ✔ (3) | ✔ (2) | (3+2)/5 = **1.0** |
| LICB2102-A (Lun/Mié 19-21, presencial) | ✔ (3) | ✔ (2) | **1.0** |
| LIIE2104-B (Mar/Jue 17-19, presencial) | ✔ (3) | ✔ (2) | **1.0** |
| LIIS2106-A (Vie 15-19, presencial) | ✔ (3) | ✔ (2) | **1.0** |
| LIIS2105-B (Mar/Jue 11-13, presencial) | ✘ (0) | ✔ (2) | 2/5 = **0.4** |
| LIIS2112-A (Lun/Mié 7-9, presencial) | ✘ (0) | ✔ (2) | 2/5 = **0.4** |

Los grupos vespertinos de LIIS2105 y LIIS2112 chocan con LIIB2104-B y entre sí (sección
13.2). El AgenteHorarios prueba todas las asignaciones y se queda con la de 0 choques y
mejor ajuste.

**AgenteManager** evalúa cada propuesta con la función del Proyecto 2.

### 15.3 La función de evaluación paso a paso

Propuesta ganadora de Ana: LIIS2105 (6 cr), LIIS2112 (8), LIIB2104 (4), LICB2102 (6),
LIIE2104 (8) y LIIS2106 (8): 40 créditos.

**Avance académico (peso 0.30)**

```text
avance = 100 · r · (0.45·progreso + 0.30·prioridad_media + 0.25·cobertura_urgentes)
  r                  = créditos válidos / créditos totales     = 40/40 = 1.0
  progreso           = min(1, créditos válidos / meta)          = min(1, 40/40) = 1.0
  prioridad_media    = (1.0+0.5+0.417+0.333+0.333+0.283)/6      = 0.4777
  cobertura_urgentes = urgentes incluidas / urgentes             = 1/1 = 1.0   (urgente = LIIS2105, prioridad ≥ 0.6)
avance = 100 · 1 · (0.45 + 0.1433 + 0.25) = 84.3
```

Si una propuesta incluye materias no válidas (ya aprobadas o sin prerrequisitos), `r`
baja y el avance cae. Así se castiga trabajar sin el Historial.

**Compatibilidad de horario (peso 0.25)**

```text
horario = 100 − 35·(pares de grupos que chocan) − 35·(materias sin grupo) = 100 − 0 − 0 = 100
```

**Carga equilibrada (peso 0.25)**

```text
s1 = 1 − 2·|créditos − meta|/meta = 1 − 0 = 1.0     (×0.4 si sale de 24–48 créditos)
s2 = 1.0  (6 materias ≤ máximo 7; si se pasa, −0.3 por cada materia extra)
s3 = 1.0  (3 difíciles —LIIS2112, LIIE2104 y LIIS2106, dificultad ≥ 4— ≤ máximo 3 para
           carga "normal"; 0 optativas ≤ 2. Cada difícil u optativa de más resta 0.3)
carga = 100 · (0.5·s1 + 0.25·s2 + 0.25·s3) = 100
```

Las metas de `CARGA_TIPO` se recalibraron al plan real. Las materias valen de 2 a 8
créditos (unos 6 en promedio) y el semestre ideal carga 32–42 créditos en 6–8 materias:

| Tipo | Créditos | Máx. materias | Máx. difíciles |
|---|---|---|---|
| ligera | 30 | 5 | 2 |
| normal | 40 | 7 | 3 |
| pesada | 48 | 8 | 4 |

**Preferencias (peso 0.20)**

```text
ajuste_horario = promedio de ajustes = (0.4+0.4+1.0+1.0+1.0+1.0)/6 = 0.80
intereses      = 1.0 (no pidió materias de interés ni a evitar)
preferencias   = 100 · (0.75·0.80 + 0.25·1.0) = 85.0
```

**Total**

```text
0.30·84.3 + 0.25·100 + 0.25·100 + 0.20·85.0 = 25.29 + 25 + 25 + 17.0 = 92.29 ✔
```

### 15.4 Shapley paso a paso

Para medir lo que aporta un agente hay que ver qué pasa **sin** él. Cuando un rol no está
en la coalición, su tarea se hace de forma **ingenua**:

| Si falta… | La tarea se hace así | Efecto real con Ana |
|---|---|---|
| Historial (A) | Todo lo ofertado "parece válido" | Coalición {B,C}: CargaPreferencias propone LHLF1201, LICB1231, LICB2103, LICB2106, LICB2107, LIIB2102 y LICB2108, **todas de 2.º y 3.er semestre y ya aprobadas**. Avance = 0 → v = 67.86 |
| Carga (B), es decir, **los 3 contratistas** | 5 materias "de arriba hacia abajo" del plan | Coalición {A}: LIIS2105 y **4 optativas de Reflexión** (semestre ideal 4, antes que las de 5.º). Carga = 60 → v = 76.56 |
| Horarios (C) | El primer grupo de cada materia, sin revisar choques | Coalición {A,B}: sin el AgenteHorarios, la mejor oferta pasa a ser la de CargaEquilibrio, pero con el primer grupo de cada materia 4 de sus 7 materias quedan en la mañana (preferencias 63.6) → v = 87.77 |

El evaluador **siempre** usa la verdad de la ontología, así que una propuesta mala
recibe una calificación baja. Los 8 valores reales de Ana:

```text
v({})=0   v({A})=76.56   v({B})=66.58   v({C})=63.25
v({A,B})=87.77   v({A,C})=76.56   v({B,C})=67.86   v({A,B,C})=92.29
```

Cálculo de φ para el Historial (A): contribución marginal promediada sobre todas las
coaliciones S que no lo contienen, con el peso `|S|!·(n−|S|−1)!/n!`:

| S (sin A) | Peso | v(S ∪ {A}) − v(S) | Peso × marginal |
|---|---|---|---|
| {} | 1/3 | 76.56 − 0 = 76.56 | 25.52 |
| {B} | 1/6 | 87.77 − 66.58 = 21.19 | 3.53 |
| {C} | 1/6 | 76.56 − 63.25 = 13.31 | 2.22 |
| {B,C} | 1/3 | 92.29 − 67.86 = 24.43 | 8.14 |
| | | **φ_A** | **39.41** ✔ |

De la misma forma φ_B = 30.07 y φ_C = 22.8. La suma da 92.28, que es **92.29 = v(N)**
salvo redondeo.

**Interpretación:** para Ana, el Historial sigue siendo el rol más valioso, porque sin él
se recomiendan materias ya aprobadas. Con la mejora 1 el φ del rol Carga subió de 25.67
(un solo AgenteCarga) a **30.07**, porque ahora son 3 contratistas con criterios distintos.
Con Sofía (A003), el rol más valioso es Carga (31.31): tiene 28 materias válidas y el reto
es elegir 8. Cada alumno produce un reparto distinto, que es justo lo que Shapley mide.

Un detalle: v({A,C}) = v({A}) = 76.56. Sin contratistas, la combinación es LIIS2105 más
4 optativas de Reflexión. Cada optativa tiene un solo grupo, y el primer grupo de LIIS2105
ya es el de la tarde, así que el AgenteHorarios no tiene nada que mejorar.

### 15.5 La licitación y el Shapley entre contratistas (mejora 1)

El Shapley de la sección anterior dice cuánto vale el **rol** Carga, pero no cuánto vale
cada contratista. Para eso hay un segundo juego (`contract_net.shapley_contratistas`):

- **Jugadores:** CargaAvance, CargaEquilibrio y CargaPreferencias.
- **Siempre presentes:** Historial y Horarios. No juegan.
- **v(S)** = puntuación de la mejor propuesta con los contratistas de S, **menos** la
  puntuación sin ninguno (carga ingenua, 76.56 con Ana). Así v(∅) = 0, como pide la
  definición de Shapley.

Los 8 valores reales de Ana:

```text
v({})=0   v({Avance})=15.32   v({Equilibrio})=14.63   v({Preferencias})=15.73
v({Avance,Equilibrio})=15.32   v({Avance,Preferencias})=15.73
v({Equilibrio,Preferencias})=15.73   v({los 3})=15.73
```

Cada v(S) es simplemente **la mejor oferta de S**, porque el Manager se queda con la
mejor. En un juego así, ordenando las ofertas de mayor a menor (a ≥ b ≥ c), Shapley queda
en una fórmula que se puede hacer a mano:

```text
φ(peor)    = c/3                         = 14.63/3                     = 4.88   (CargaEquilibrio)
φ(media)   = c/3 + (b − c)/2             = 4.88 + (15.32 − 14.63)/2    = 5.22   (CargaAvance)
φ(mejor)   = c/3 + (b − c)/2 + (a − b)   = 5.22 + (15.73 − 15.32)      = 5.63   (CargaPreferencias)
suma       = 15.73 = v(N) ✔
```

Cómo se lee:
- **c/3:** lo que cualquiera de los 3 logra se reparte en partes iguales, porque son
  sustitutos.
- **El resto:** solo se lo lleva quien lo mejora.
- **El ganador obtiene más, pero no todo.** Esto pasa porque los otros dos por sí solos
  también habrían dado una buena carga.

Resultados de los 3 alumnos:

| Alumno | Gana | φ Avance | φ Equilibrio | φ Preferencias | Lectura |
|---|---|---|---|---|---|
| A001 Ana | CargaPreferencias (92.29) | 5.22 | 4.88 | 5.63 | Prefiere la tarde: gana quien mira los grupos |
| A002 Luis | CargaPreferencias (94.53) | 0.44 | 0.6 | 2.37 | La carga ingenua ya era buena (91.12): los contratistas aportan poco, y casi todo lo extra lo pone Preferencias |
| A003 Sofía | CargaAvance (84.39), empate triple | 10.2 | 10.2 | 10.2 | Los 3 ofertan lo mismo: **simetría** |

Si con algún contratista el resultado nunca cambiara (v(S ∪ {i}) = v(S) para toda
coalición S, incluida la vacía), su φ sería 0: el **jugador ficticio (dummy)** de la
diapositiva. Con estas 3 estrategias no pasa con ningún alumno, porque cada una, sola,
mejora a la carga ingenua.

**Límite honesto de la licitación.** La competencia no garantiza la mejor carga posible:
cada contratista oferta lo mejor según **su** criterio, y el Manager califica con **otro**.
Se comparó contra el AgenteCarga único de antes (pesos 0.5/0.3/0.2, 6 combinaciones) en
4 casos:

| Caso | AgenteCarga único | 3 contratistas |
|---|---|---|
| A001 sin petición | 92.29 | 92.29 |
| A001 con la petición del notebook | **93.14** | 93.01 |
| A002 (ligera, sin viernes) | 94.53 | 94.53 |
| A003 (pesada, en línea) | 84.39 | 84.39 |

En 3 casos empatan y en uno el agente único gana por 0.13. Ese caso no se recupera
subiendo a 3 ofertas por contratista. Lo que gana el sistema con la mejora no es
puntuación, sino **transparencia**: ahora se sabe qué criterio sirvió para cada alumno y
cuánto aportó cada contratista.

### 15.6 Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Comandos de terminal |
| `carga/config.py` | Rutas, modelo, hilos, pesos, metas de carga y estrategias de los contratistas |
| `datos/importar_intrauia.py` | Exportación de Intrauia → `datos/plan_ibero.json` (con validación) |
| `datos/plan_ibero.json` | Plan de estudios real (79 materias) |
| `datos/semilla.py` | Materias (desde el JSON), oferta generada, profesores y alumnos |
| `carga/poblar.py` | Semilla → individuos OWL + clases definidas |
| `carga/kb.py` | Ontología → objetos Python; SPARQL; HermiT |
| `carga/preferencias.py` | Lenguaje natural → preferencias (LLM con esquema + reglas + validación) |
| `carga/evaluacion.py` | Elegibilidad, prioridad, choques, los 4 criterios |
| `carga/agentes.py` | Los 4 agentes (el AgenteCarga con estrategia y `ofertar`), versiones ingenuas, guardia anti-alucinación |
| `carga/contract_net.py` | Protocolo cfp/propose/accept/reject/inform con 3 contratistas + Shapley exacto (roles y contratistas) |
| `carga/trazas.py` | Trace Collector + mensajes FIPA |
| `carga/persistencia.py` | Resultados → `kb_<mat>.owl` |
| `carga/reporte.py` | Reporte Markdown y resumen en terminal |
| `carga/sistema.py` | Orquestación del modo `recomendar` |
| `carga/crew.py` | Orquestación con CrewAI |
| `carga/llm.py` | Cliente de Ollama (num_gpu=0, hilos, caché) y `diagnostico` |

---

## 16. Solución de problemas

| Síntoma | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'owlready2'` (o `carga`) | No activaste `.venv` o no estás en la carpeta | `cd …/agente-carga3 && source .venv/bin/activate` |
| `Error: No existe el estudiante 'A009'. Disponibles: A001, A002, A003` | Matrícula equivocada | Revisa con `python main.py alumnos` |
| `interpretadas por: reglas (sin LLM)` aunque querías LLM | Ollama apagado o sin el modelo | `./iniciar_ollama_cpu.sh` en otra terminal y `python main.py diagnostico` |
| `diagnostico` dice `11434 — modelos: NINGUNO` | Es el servicio de Fedora, que no tiene modelos | Normal; el sistema usa el 11435 |
| `Ya hay un Ollama escuchando en 127.0.0.1:11435` | El script ya estaba corriendo | Úsalo; o ciérralo con Ctrl+C en su terminal |
| `diagnostico` dice `⚠ USANDO GPU` | Algún Ollama se arrancó sin el script | Ctrl+C en ese Ollama y usa solo `./iniciar_ollama_cpu.sh` |
| `⚠ LLM desactivado: laptop en batería` | No hay cargador conectado (protección contra apagados) | Conecta el cargador; o `LLM_EN_BATERIA=1` bajo tu riesgo |
| La laptop se apaga de golpe al correr el LLM | Batería desgastada: el pico de consumo baja el voltaje | Usa el LLM solo con cargador; `HILOS_LLM=2` reduce el pico |
| La laptop se pone lenta con el LLM | Poca RAM libre | Cierra el navegador; usa `llama3.2`, no `llama3.1:8b`; o `--sin-llm` |
| El LLM tarda más de 4 min y se cancela | CPU saturada | `TIMEOUT_LLM=400 python main.py ...` o usa `--sin-llm` |
| `plantilla (la redacción del LLM… se descartó)` | El guardia detectó un dato inventado | Normal y deseado; la recomendación es correcta |
| `--razonador` muestra `no se pudo ejecutar HermiT` | Java no instalado | `sudo dnf install java-latest-openjdk` |
| Protégé dice que la ontología es inconsistente | Abriste dos `kb_*.owl` juntos | Abre uno solo (sección 13.1) |
| Cambié `semilla.py` y no veo el cambio | No regeneraste la ontología | `python main.py poblar` |
| El notebook no encuentra `carga` | Kernel equivocado | Kernel "agente-carga3 (.venv)" |

Variables de entorno útiles (se ponen antes del comando):

```text
$ MODELO_LLM=gemma3:1b python main.py recomendar A002 -p "..."   # modelo más ligero (1 GB), menos preciso
$ HILOS_LLM=2 python main.py recomendar A001                     # menos hilos = laptop más fresca (default 4)
$ LLM_EN_BATERIA=1 python main.py recomendar A001                # usar el LLM aunque no haya cargador (riesgo de apagado)
$ OLLAMA_URL=http://127.0.0.1:11435 python main.py diagnostico   # forzar un servidor específico
```

---

## 17. Apagar todo y bitácoras de verificación

### Apagar

- En la terminal de Ollama, presiona **Ctrl+C**. La RAM del modelo (~2.5 GB) se libera
  al instante.
- Para salir del entorno, escribe `deactivate`.

### Bitácoras de esta verificación

En `salidas/_verificacion/` están las salidas completas de cada prueba:

| Archivo | Prueba |
|---|---|
| `00_instalacion_limpia.log` | Entorno nuevo + `pip install -r requirements.txt` + demo |
| `01_entorno.log` | Python del `.venv` |
| `02_poblar.log` | Generación de la ontología |
| `03_alumnos.log` · `04_diagnostico_sin_ollama.log` | Consultas básicas |
| `05_demo.log` | Demo de los 3 alumnos |
| `06_recomendar_A001_sin_llm.log` | Recomendación completa sin LLM |
| `07_recomendar_A003_razonador.log` | HermiT |
| `08_consultas_dl_query.log` | Las 10 consultas DL Query |
| `09_notebook.log` | Ejecución completa de `demo.ipynb` |
| `10_casos_de_error.log` | Alumno inexistente, Ollama apagado |
| `11_ollama_servidor.log` · `12_diagnostico_con_ollama.log` | Servidor solo CPU |
| `13_recomendar_A003_con_llm.log` | 1ª prueba con LLM: aquí se detectó la redacción con horarios inventados |
| `14_recomendar_A003_con_llm_corregido.log` · `15_cache.log` | Después de la corrección, y la caché |
| `16_crew_secuencial.log` | 1ª prueba de CrewAI: el coordinador no usó su herramienta y el guardia lo atrapó |
| `17_crew_secuencial_corregido.log` | CrewAI ya corregido: 4 herramientas, redacción aceptada |
| `18_agregar_alumno.log` | Alta de la alumna A004 |
| `19_crew_jerarquico.log` | Modo jerárquico |
| `ejecutar_notebook.py` | Script que ejecutó el notebook sin abrir Jupyter |
