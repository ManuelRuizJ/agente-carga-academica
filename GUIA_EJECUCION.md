# Guía de ejecución y funcionamiento: Agente de carga académica v3

Esta guía explica, paso a paso, cómo correr el sistema y cómo funciona por dentro.
**Todas las salidas que aparecen aquí son reales:** se obtuvieron ejecutando cada paso
en tu laptop (Fedora 44, Ryzen 7 5700U, 14 GB de RAM) el 5 de noviembre de 2026.
Las bitácoras completas de esas ejecuciones están en `salidas/_verificacion/`
(sección 17).

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
| 1 | `python main.py poblar` (genera la ontología con individuos) | ✅ 203 individuos | 0.2 s |
| 2 | `python main.py alumnos` | ✅ 3 alumnos | < 1 s |
| 3 | `python main.py demo` (3 alumnos, sin LLM) | ✅ | 0.5 s |
| 4 | `recomendar A001 --sin-llm` | ✅ 89.17/100 | < 1 s |
| 5 | `recomendar A003 --razonador` (HermiT en Java) | ✅ 6 clases inferidas | 1.9 s |
| 6 | 10 consultas DL Query sobre la ontología de salida | ✅ todas con resultado correcto | — |
| 7 | `demo.ipynb` completo con su kernel | ✅ 7 celdas, 0 errores | 3 s |
| 8 | Casos de error (alumno inexistente, Ollama apagado) | ✅ mensajes claros, no truena | — |
| 9 | Ollama solo CPU: `library=cpu`, **VRAM = 0 bytes** | ✅ | — |
| 10 | `recomendar` con LLM (interpretación + redacción) | ✅ | 67 s (1ª vez), 24 s (2ª), 0.4 s (caché) |
| 11 | `crew A001` (CrewAI secuencial, 4 agentes, 4 herramientas) | ✅ | 4 min |
| 12 | `crew A002 --proceso jerarquico` (Manager delega a los especialistas) | ✅ 4 herramientas | 5 min 20 s |
| 13 | Agregar un alumno nuevo (A004) en `datos/semilla.py` | ✅ | < 1 s |

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
  203 individuos | 27 materias | 35 grupos | 3 estudiantes | 34 pares de grupos en conflicto
```

No es necesario ejecutarlo la primera vez, porque el archivo ya existe. Solo vuelve a
correrlo cuando edites `datos/semilla.py`. Tu archivo original
`ontologia/P2_ontologia_carga_academica.owx` **nunca se modifica**.

### 4.2 Listar los alumnos

```text
$ python main.py alumnos
A001  Ana Torres Medina        sem 5  prom 8.79  aprobadas 15  reprobadas ['SOP401']
A002  Luis Hernández Rojas     sem 3  prom 7.93  aprobadas  6  reprobadas ['MAT201']
A003  Sofía Ramírez Lara       sem 6  prom 9.56  aprobadas 18  reprobadas -
```

Cada dato sale de la ontología. Las materias aprobadas y reprobadas se obtienen con una
**consulta SPARQL** sobre los individuos `RegistroAprobado` y `RegistroReprobado`
(`carga/kb.py`, método `_sparql_registros`).

| Alumno | Para qué sirve en la demo |
|---|---|
| **A001 Ana** | Reprobó Sistemas Operativos, que bloquea Sistemas Distribuidos. Sirve para ver si el sistema prioriza recursar. Prefiere la tarde y la modalidad presencial |
| **A002 Luis** | Va atrasado y reprobó Cálculo Integral. Le quedan pocas materias válidas. Quiere una carga ligera |
| **A003 Sofía** | Alumna avanzada que quiere adelantar (carga pesada) y prefiere en línea |

---

## 5. Paso 3: la demo rápida, sin LLM

```text
$ time python main.py demo
 CARGA RECOMENDADA (40 créditos · puntuación 89.17/100)       ← A001
 Shapley: Historial 41.91 | Carga 20.43 | Horarios 26.83
 CARGA RECOMENDADA (32 créditos · puntuación 96.25/100)       ← A002
 Shapley: Historial 42.87 | Carga 27.49 | Horarios 25.89
 CARGA RECOMENDADA (44 créditos · puntuación 84.7/100)        ← A003
 Shapley: Historial 37.16 | Carga 27.93 | Horarios 19.61
python main.py demo  0.49s user 0.04s system 98% cpu 0.544 total
```

(Arriba se muestra solo el resumen; en pantalla verás el bloque completo de cada alumno.)

En **medio segundo** procesa a los 3 alumnos: Contract Net, 8 coaliciones de Shapley
por alumno, el reporte y la escritura en la ontología. El prototipo anterior tardaba
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
  [    propose     ] AgenteHistorial → AgenteManager: válidas: SOP401, IAR501, OPT03, CMP501, SEG501, WEB501, OPT04, DSC601, OPT01, OPT02
  [      cfp       ] AgenteManager → AgenteCarga: Combinaciones entre 24-48 créditos, meta 40
  [    propose     ] AgenteCarga → AgenteManager: 6 combinaciones (mejor: SOP401, IAR501, SEG501, WEB501, DSC601)
  [      cfp       ] AgenteManager → AgenteHorarios: Asignar grupos a 6 combinaciones
  [    propose     ] AgenteHorarios → AgenteManager: 6 propuestas con horario
  [accept-proposal ] AgenteManager → *: P1 (89.17): SOP401, IAR501, SEG501, WEB501, DSC601
  [reject-proposal ] AgenteManager → *: P2 (89.02)
  [reject-proposal ] AgenteManager → *: P3 (88.79)
  [reject-proposal ] AgenteManager → *: P4 (88.64)
  [reject-proposal ] AgenteManager → *: P5 (87.95)
  [reject-proposal ] AgenteManager → *: P6 (87.35)
```

Cómo leerlo:

- **`cfp`** (*call for proposals*): el Manager pide propuestas a un especialista.
- **`propose`**: el especialista responde. El Historial manda las 10 materias válidas,
  ordenadas por prioridad. SOP401 va primero porque Ana la reprobó y bloquea SDI601.
- **`accept-proposal` / `reject-proposal`**: el Manager califica las 6 propuestas con la
  función de evaluación, adjudica la mejor (P1) y rechaza las demás.

Son las performativas del protocolo Contract Net, con el estilo FIPA-ACL/KQML del tema 5.

### 6.2 La recomendación

```text
══════════════════════════════════════════════════════════════════════════════
 Ana Torres Medina (A001) · semestre 5 · Primavera 2027
 Preferencias: carga normal (~40 créditos, máx. 5 materias); turno vespertino; modalidad presencial
   ↳ interpretadas por: solo ontología
══════════════════════════════════════════════════════════════════════════════
 CARGA RECOMENDADA (40 créditos · puntuación 89.17/100)
  • SOP401  Sistemas Operativos              SOP401-A  presencial Mar 09-11, Jue 09-11
  • IAR501  Inteligencia Artificial          IAR501-B  presencial Lun 17-19, Mie 17-19
  • SEG501  Seguridad Informática            SEG501-B  en_linea   Vie 15-19
  • WEB501  Desarrollo Web                   WEB501-B  presencial Mar 07-09, Jue 07-09
  • DSC601  Ciencia de Datos                 DSC601-A  hibrida    Lun 15-17, Mie 15-17
  Criterios: avance 81.9 | compatibilidad 100 | carga 100.0 | preferencias 73.0

 Shapley: Historial 41.91 | Carga 20.43 | Horarios 26.83
```

- **"interpretadas por: solo ontología"**: como no se escribió ninguna petición (`-p`), se
  usan las preferencias que Ana tiene guardadas en la ontología (`PreferenciaHorario`,
  `PreferenciaModalidad` y `PreferenciaCarga`).
- **Los 4 criterios** son los del Proyecto 2 (0 a 100 cada uno). La puntuación es
  0.30·81.9 + 0.25·100 + 0.25·100 + 0.20·73 = **89.17**. La [sección 15.3](#153-la-función-de-evaluación-paso-a-paso)
  hace el cálculo completo.
- **¿Por qué SOP401 va en la mañana si Ana prefiere la tarde?** Su grupo de la tarde
  (SOP401-B, lunes y miércoles de 15 a 17) choca con Ciencia de Datos. El sistema prefirió
  recursar SOP401 en la mañana antes que dejarla fuera.
- **Shapley**: cuánto aportó cada especialista. La suma es 41.91 + 20.43 + 26.83 = 89.17,
  igual a la puntuación final (propiedad de eficiencia).

### 6.3 La explicación y los archivos generados

```text
 Ana, para Primavera 2027 te recomendamos inscribir 5 materias (40 créditos): Sistemas
 Operativos, Inteligencia Artificial, Seguridad Informática, Desarrollo Web, Ciencia de
 Datos. Se prioriza recursar Sistemas Operativos porque es prerrequisito de materias
 posteriores. La combinación cumple el rango institucional de 24–48 créditos y obtuvo
 89.17/100 en la evaluación del coordinador. No hay choques de horario y el ajuste a tus
 preferencias de turno, modalidad e intereses es de 73.0/100.
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
de interés o a evitar (por nombre, siglas como "IA" o "POO", o palabras como "redes") y
un número de materias.

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
| **Materias descartadas** | P. ej. `AGI601 Agentes Inteligentes: falta prerrequisito: IAR501` |
| **Propuestas evaluadas** | Las 6 propuestas con sus 4 criterios y su total. La ganadora lleva ✅ |
| **Valores de Shapley** | La tabla v(S) de las 8 coaliciones y φ de cada agente, con su porcentaje |
| **Inferencias de HermiT** | Solo si usaste `--razonador` |
| **Mensajes del Contract Net** | El diálogo FIPA completo |
| **Trazas de ejecución** | Hora, agente, tarea, salida, tiempo, éxito y score (sección 3.2 del Proyecto 2) |

Fragmento real (A003, de la ejecución del paso 6; los números cambian si cambias la petición):

```text
| Coalición S | v(S) |          | Agente              | φ     | %     |
|---|---|                       |---|---|---|
| {}      | 0.0   |             | AgenteHistorial (A) | 37.16 | 43.9% |
| {A}     | 70.38 |             | AgenteCarga (B)     | 27.93 | 33.0% |
| {B}     | 58.4  |             | AgenteHorarios (C)  | 19.61 | 23.2% |
| {C}     | 50.33 |             | Suma                | 84.7 = v(N) | 100% |
| {A,B}   | 81.56 |
| {A,C}   | 73.0  |
| {B,C}   | 66.52 |
| {A,B,C} | 84.7  |
```

`salidas/trazas_<mat>.json` contiene lo mismo en formato JSON. Ejemplo de un evento real:

```json
{
  "timestamp": "2026-11-05T18:32:43",
  "agent": "AgenteManager",
  "task": "evaluar_propuestas_contract_net",
  "input": "6 propuestas",
  "output": "gana P3 con 85.94",
  "execution_time": 0.0003,
  "success": true,
  "score": 85.94
}
```

---

## 8. Paso 6: el razonador HermiT

```text
$ time python main.py recomendar A003 -q --sin-llm --razonador -p "quiero adelantar, en línea, me interesa IA y no quiero compiladores"
...
python main.py recomendar A003 ...  1.884 total
```

`--razonador` ejecuta **HermiT** (en Java, con el límite de memoria en 512 MB) sobre la
ontología. HermiT **clasifica automáticamente** los individuos en las clases definidas
que se agregaron a tu TBox. Resultado real (está en el reporte):

| Clase definida (Manchester) | Individuos inferidos por HermiT |
|---|---|
| `MateriaLlave` ≡ `Materia and esPrerrequisitoDe min 2 Materia` | ARQ301, BDD301, MAT101, MAT301, PRG201, PRG301, PRG401, RED401 |
| `MateriaSeriada` ≡ `Materia and tienePrerrequisito some Materia` | 21 materias (todas las que tienen prerrequisito) |
| `GrupoVespertino` ≡ `Grupo and tieneBloqueHorario some (BloqueHorario and turno value "vespertino")` | 18 grupos |
| `GrupoEnLinea` ≡ `Grupo and tieneModalidad some ModalidadEnLinea` | AGI601-B, MAT301-B, OPT02-A, OPT03-A, PRG301-B, RED401-B, SDI601-B, SEG501-B, WEB501-A |
| `EstudianteConAdeudo` ≡ `Estudiante and tieneRegistro some RegistroReprobado` | A001, A002 |

Nadie escribió "ARQ301 es MateriaLlave": **el razonador lo dedujo**, porque ARQ301 es
prerrequisito de SOP401 y de RED401. Para que `min 2` funcione se declaró `AllDifferent`
entre las materias. OWL no asume nombres únicos (supuesto de mundo abierto), así que sin
esa declaración HermiT no podría contar.

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
  Modelo configurado: llama3.2 | hilos: 6 | contexto: 4096
```

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
 CARGA RECOMENDADA (40 créditos · puntuación 89.17/100)
```

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
| 2 | Alumno A001 según la ontología | `Ana Torres Medina \| semestre 5 \| promedio 8.79`, aprobadas y reprobadas |
| 3 | Interpreta "Me interesa inteligencia artificial, prefiero la tarde y no quiero clases los viernes" | `...sin clases: Viernes; le interesa: IAR501` |
| 4 | Contract Net | Mensajes FIPA y las 6 propuestas. Gana P1 con 90.45 |
| 5 | Shapley | Las 8 coaliciones: `v({A})=75.09 … v({A,B,C})=90.45` y `suma: 90.45 = v(N)` |
| 6 | HermiT | Las 6 clases definidas con sus individuos |
| 7 | Cierra y muestra el reporte | El reporte Markdown completo dentro del notebook |

Verificación automática: **7 celdas de código ejecutadas, 0 con error, en 3 s.**

Observa que en la celda 3 se pidió "no quiero clases los viernes" y por eso Seguridad
Informática se movió a lunes y miércoles (grupo SEG501-A). En el paso 4, sin esa
petición, quedaba en viernes (SEG501-B).

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
| `Materia and puedeSerCursadaPor value est_A001` | 10: CMP501, DSC601, IAR501, OPT01, OPT02, OPT03, OPT04, SEG501, SOP401, WEB501 |
| `MateriaLlave` | 8: ARQ301, BDD301, MAT101, MAT301, PRG201, PRG301, PRG401, RED401 |
| `EstudianteConAdeudo` | 2: est_A001, est_A002 |
| `Grupo and esOfertaDe value mat_IAR501 and tieneModalidad some ModalidadPresencial` | 2: IAR501-A, IAR501-B |
| `Grupo and enConflictoCon value grp_SOP401_B` | 3: DSC601-A, PRG301-B, WEB501-A |
| `GrupoVespertino and GrupoEnLinea` | 8: MAT301-B, OPT02-A, OPT03-A, PRG301-B, RED401-B, SDI601-B, SEG501-B, WEB501-A |
| `Materia and tienePrerrequisito some (Materia and aprobadaPor value est_A002)` | 7: BDD301, FIS201, MAT201, MAT202, OPT01, PRG201, PRG301 |
| `PropuestaCarga and esValida value true` | 1: la propuesta ganadora (`prop_A001_<fecha>_P1`) |
| `PropuestaCarga and puntuacion some xsd:decimal[>= 88.0]` | 4 propuestas (89.17, 89.02, 88.79, 88.64) |
| `Agente and valorShapley some xsd:decimal[> 25.0]` | 2: AgenteHistorial (41.91), AgenteHorarios (26.83) |

En Protégé los grupos aparecen con su nombre de individuo (por ejemplo `grp_IAR501_A`) y
las materias como `mat_IAR501`.

Cómo leer algunas:
- **`enConflictoCon value grp_SOP401_B`** explica por qué Ana no tomó SOP401 en la tarde:
  ese grupo choca con DSC601-A.
- **`puedeSerCursadaPor`** es la inversa de `puedeCursar`. La escribió el AgenteHistorial,
  pero la consulta la resuelve el razonador.
- **`tienePrerrequisito some (… aprobadaPor value est_A002)`** devuelve las materias de
  las que Luis aprobó **al menos un** prerrequisito, porque `some` es existencial (∃).
  Fíjate en dos cosas:
  - **PRG201 y MAT202 aparecen aunque Luis ya las aprobó.** La consulta no las excluye
    porque no se lo pediste.
  - **`some` no significa "todos los prerrequisitos".** Una materia con dos requisitos
    aparecería aunque solo tuviera uno aprobado. En OWL, "todos aprobados" no se puede
    deducir por el supuesto de mundo abierto (no saber que algo está aprobado no
    significa que no lo esté). Por eso esa regla la verifica el **AgenteHistorial en
    Python**, y su conclusión se guarda como `puedeCursar`.

---

## 14. Paso 12: agregar tus propios alumnos o materias

Todos los datos están en **`datos/semilla.py`**; no tienes que tocar Protégé. Esto se
probó agregando una alumna A004.

**1.** En `datos/semilla.py`, dentro del diccionario `ESTUDIANTES`, después del bloque
de `"A003": {...},`, agrega:

```python
    "A004": {
        "id": "est_A004",
        "nombre": "Mariana López Cruz",
        "semestre": 4,
        "aprobadas": {
            "MAT101": 8.5, "PRG101": 9.0, "MAT102": 8.0, "ISC101": 9.2,
            "MAT201": 7.8, "PRG201": 8.9, "MAT202": 8.1, "FIS201": 8.4,
            "PRG301": 8.7, "BDD301": 9.1,
        },
        "reprobadas": {"ARQ301": 5.8},
        "preferencias": {
            "turno": ("matutino", 2, "Prefiero en la mañana"),          # (valor, prioridad 1-3, texto)
            "modalidad": ("hibrida", 1, "Híbrida está bien"),           # presencial | en_linea | hibrida
            "carga": ("normal", 2, "Carga normal", 40, 5),              # (+ créditos objetivo, máx. materias)
        },
    },
```

**2.** Regenera la ontología y pruébala:

```text
$ python main.py poblar
✔ Ontología poblada: ontologia/carga_academica_poblada.owl
  218 individuos | 27 materias | 35 grupos | 4 estudiantes | 34 pares de grupos en conflicto

$ python main.py alumnos
...
A004  Mariana López Cruz       sem 4  prom 8.57  aprobadas 10  reprobadas ['ARQ301']

$ python main.py recomendar A004 --sin-llm -q
 CARGA RECOMENDADA (40 créditos · puntuación 93.41/100)
  • ARQ301  Arquitectura de Computadoras     ARQ301-A  presencial Lun 09-11, Mie 09-11
  • MAT301  Probabilidad y Estadística       MAT301-A  presencial Mar 11-13, Jue 11-13
  • PRG401  Análisis de Algoritmos           PRG401-A  presencial Lun 11-13, Mie 11-13
  • ISW401  Ingeniería de Software           ISW401-A  hibrida    Vie 09-13
  • WEB501  Desarrollo Web                   WEB501-B  presencial Mar 07-09, Jue 07-09
 Shapley: Historial 33.79 | Carga 33.71 | Horarios 25.9
 ... Se prioriza recursar Arquitectura de Computadoras porque es prerrequisito de materias posteriores.
```

El promedio (8.57) y los créditos acumulados se calculan solos. Todos los grupos quedaron
en la mañana, como pidió.

**Otras cosas que puedes editar en el mismo archivo:**

| Quieres… | Edita | Formato |
|---|---|---|
| Una materia nueva | `MATERIAS` | `"CLAVE": ("Nombre", créditos, semestre, horas, dificultad 1-5, ¿obligatoria?, ["PRERREQ1", ...])` |
| Un grupo nuevo | `GRUPOS` | `"CLAVE-X": ("MATERIA", "prof_00N", "presencial/en_linea/hibrida", "PATRÓN", cupo_max, cupo_disp)` |
| Un horario nuevo | `H` | `"NOMBRE": [("Lunes", 15, 17), ("Miercoles", 15, 17)]` (horas enteras, 24 h, días sin acento) |
| El rango de créditos | `RESTRICCION_CREDITOS` | `minimos` / `maximos` |

Para pesos, metas de carga o el modelo de LLM, edita `carga/config.py` (`PESOS`,
`CARGA_TIPO`, `MODELO`).

Siempre que edites `semilla.py`, ejecuta `python main.py poblar`.

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
        │                 ── Manager: cfp ──▶ Carga     ─propose▶ 6 mejores combinaciones
        │                 ── Manager: cfp ──▶ Horarios  ─propose▶ propuestas con grupos sin choques
        │                 ── Manager evalúa (0.30/0.25/0.25/0.20) → accept / reject
        ▼
 [contract_net.valores_shapley]  repite el protocolo con las 8 coaliciones → φ exacto
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
prioridad = 0.40·rezago + 0.20·(obligatoria) + 0.25·(cuántas desbloquea, máx 3) + 0.15·(la reprobó)
```

Prioridades reales de Ana: **SOP401 0.70**, IAR501 0.417, OPT03 0.40, CMP501/SEG501/WEB501
0.333, OPT04 0.267, DSC601 0.20, OPT01 0.133, OPT02 0.0. SOP401 sale tan alta porque está
un semestre atrasada, es obligatoria, desbloquea SDI601 y Ana la reprobó.

Descartadas: `AGI601: falta prerrequisito: IAR501` y `SDI601: falta prerrequisito: SOP401`.

**AgenteCarga** (`agentes.py: AgenteCarga.proponer`):
1. Toma hasta 12 materias candidatas: primero las de interés y luego las de mayor
   prioridad. Excluye las que el alumno quiere evitar.
2. Prueba todas las combinaciones de 1 hasta `max_materias` materias. Ana tiene 10 válidas y
   máximo 5 materias: C(10,1)+…+C(10,5) = 637 combinaciones, evaluadas en milisegundos.
3. Descarta las que se salen del rango institucional (24–48 créditos).
4. Las califica así: 0.5·(carga equilibrada) + 0.3·(prioridad promedio) + 0.2·(materias de interés).
5. Envía las 6 mejores al Manager.

**AgenteHorarios** (`agentes.py: AgenteHorarios.asignar`):
1. Para cada combinación prueba **todas** las asignaciones de grupos (producto cartesiano).
2. Elige la de **menos choques** y, si empatan, la de **mejor ajuste** a turno, modalidad
   y días libres.
3. Si un choque es inevitable, propone además una variante sin la materia de menor
   prioridad que choca.

El ajuste de un grupo es un promedio ponderado por la prioridad de cada preferencia. Con
Ana (turno vespertino con peso 3, presencial con peso 2):

| Grupo | Turno | Modalidad | Ajuste |
|---|---|---|---|
| IAR501-B (Lun/Mié 17-19, presencial) | ✔ (3) | ✔ (2) | (3+2)/5 = **1.0** |
| DSC601-A (Lun/Mié 15-17, híbrida) | ✔ (3) | híbrida = ½ (1) | (3+1)/5 = **0.8** |
| SEG501-B (Vie 15-19, en línea) | ✔ (3) | ✘ (0) | 3/5 = **0.6** |
| SOP401-A (Mar/Jue 9-11, presencial) | ✘ (0) | ✔ (2) | 2/5 = **0.4** |
| WEB501-B (Mar/Jue 7-9, presencial) | ✘ (0) | ✔ (2) | 2/5 = **0.4** |

**AgenteManager** evalúa cada propuesta con la función del Proyecto 2.

### 15.3 La función de evaluación paso a paso

Propuesta ganadora de Ana: SOP401, IAR501, SEG501, WEB501, DSC601 (40 créditos).

**Avance académico (peso 0.30)**

```text
avance = 100 · r · (0.45·progreso + 0.30·prioridad_media + 0.25·cobertura_urgentes)
  r                  = créditos válidos / créditos totales     = 40/40 = 1.0
  progreso           = min(1, créditos válidos / meta)          = min(1, 40/40) = 1.0
  prioridad_media    = (0.70+0.417+0.333+0.333+0.20)/5          = 0.3966
  cobertura_urgentes = urgentes incluidas / urgentes             = 1/1 = 1.0   (urgente = SOP401, prioridad ≥ 0.6)
avance = 100 · 1 · (0.45 + 0.119 + 0.25) = 81.9
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
s2 = 1.0  (5 materias ≤ máximo 5; si se pasa, −0.3 por cada materia extra)
s3 = 1.0  (2 difíciles —SOP401 e IAR501, dificultad ≥ 4— ≤ máximo 2 para carga "normal")
carga = 100 · (0.5·s1 + 0.25·s2 + 0.25·s3) = 100
```

**Preferencias (peso 0.20)**

```text
ajuste_horario = promedio de ajustes = (0.4+1.0+0.6+0.4+0.8)/5 = 0.64
intereses      = 1.0 (no pidió materias de interés ni a evitar)
preferencias   = 100 · (0.75·0.64 + 0.25·1.0) = 73.0
```

**Total**

```text
0.30·81.9 + 0.25·100 + 0.25·100 + 0.20·73.0 = 24.57 + 25 + 25 + 14.6 = 89.17 ✔
```

### 15.4 Shapley paso a paso

Para medir lo que aporta un agente hay que ver qué pasa **sin** él. Cuando un especialista
no está en la coalición, su tarea se hace de forma **ingenua**:

| Si falta… | La tarea se hace así | Efecto real con Ana |
|---|---|---|
| Historial (A) | Todo lo ofertado "parece válido" | Coalición {B,C}: propone ARQ301, BDD301, MAT301, PRG301 y PRG401, **todas ya aprobadas**. Avance = 0 → v = 64.6 |
| Carga (B) | 5 materias "de arriba hacia abajo" del plan | Ignora la meta de créditos y los intereses |
| Horarios (C) | El primer grupo de cada materia, sin revisar choques | Coalición {A,B}: preferencias 67 en lugar de 73 → v = 86.24 |

El evaluador **siempre** usa la verdad de la ontología, así que una propuesta mala
recibe una calificación baja. Los 8 valores reales de Ana:

```text
v({})=0   v({A})=73.73   v({B})=52.25   v({C})=65.2
v({A,B})=86.24   v({A,C})=86.09   v({B,C})=64.6   v({A,B,C})=89.17
```

Cálculo de φ para el Historial (A): contribución marginal promediada sobre todas las
coaliciones S que no lo contienen, con el peso `|S|!·(n−|S|−1)!/n!`:

| S (sin A) | Peso | v(S ∪ {A}) − v(S) | Peso × marginal |
|---|---|---|---|
| {} | 1/3 | 73.73 − 0 = 73.73 | 24.58 |
| {B} | 1/6 | 86.24 − 52.25 = 33.99 | 5.67 |
| {C} | 1/6 | 86.09 − 65.2 = 20.89 | 3.48 |
| {B,C} | 1/3 | 89.17 − 64.6 = 24.57 | 8.19 |
| | | **φ_A** | **41.91** ✔ |

De la misma forma φ_B = 20.43 y φ_C = 26.83. La suma da **89.17 = v(N)**.

**Interpretación:** para Ana, el Historial es el agente más valioso, porque sin él se
recomiendan materias ya aprobadas. Le sigue Horarios, porque Ana tiene preferencias
fuertes de turno. Con A004, en cambio, Historial (33.79) y Carga (33.71) quedan casi
empatados: cada alumno produce un reparto distinto, que es justo lo que Shapley mide.

### 15.5 Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Comandos de terminal |
| `carga/config.py` | Rutas, modelo, hilos, pesos y metas de carga |
| `datos/semilla.py` | Datos: materias, grupos, profesores y alumnos |
| `carga/poblar.py` | Semilla → individuos OWL + clases definidas |
| `carga/kb.py` | Ontología → objetos Python; SPARQL; HermiT |
| `carga/preferencias.py` | Lenguaje natural → preferencias (LLM con esquema + reglas + validación) |
| `carga/evaluacion.py` | Elegibilidad, prioridad, choques, los 4 criterios |
| `carga/agentes.py` | Los 4 agentes, versiones ingenuas, guardia anti-alucinación |
| `carga/contract_net.py` | Protocolo cfp/propose/accept/reject + Shapley exacto |
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
$ HILOS_LLM=4 python main.py recomendar A001                     # menos hilos = laptop más fresca
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
