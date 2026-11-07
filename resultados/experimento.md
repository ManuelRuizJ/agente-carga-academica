# Resultados del experimento comparativo (mejora 2)

Generado el 6 de noviembre de 2026 con `python main.py experimento --llm`. Plan de
estudios real (Intrauia), alumnos sintéticos. La metodología y la discusión están en
`GUIA_EJECUCION.md`, sección 16. Los datos por alumno están en
`experimento_semilla7_llm.csv`.

## Tabla principal (20 alumnos, semilla 7)

| Sistema | Puntuación media | Mínima | Veces la mejor | Con materias inválidas | Con choques | Fuera de 24–48 cr | > 2 optativas | Día libre no respetado | Tiempo medio (s) |
|---|---|---|---|---|---|---|---|---|---|
| MAS (3 contratistas) | **89.57** | 84.06 | 12/20 | 0% | 0% | 0% | 0% | 0 de 2 | 0.066 |
| MAS (1 AgenteCarga, antes de la mejora 1) | **88.9** | 77.66 | 14/20 | 0% | 0% | 0% | 0% | 1 de 2 | 0.027 |
| Solo CargaAvance | **87.71** | 70.97 | 1/20 | 0% | 5.0% | 0% | 0% | 2 de 2 | 0.022 |
| Solo CargaEquilibrio | **87.92** | 75.18 | 4/20 | 0% | 5.0% | 0% | 0% | 1 de 2 | 0.022 |
| Solo CargaPreferencias | **88.48** | 84.06 | 8/20 | 0% | 0% | 0% | 0% | 0 de 2 | 0.022 |
| Monoagente simple (solo requisitos) | **70.9** | 47.51 | 0/20 | 0% | 15.0% | 5.0% | 70.0% | 2 de 2 | 0.0 |
| LLM solo (llama3.2) | **36.1** | 11.8 | 0/20 | 100% | 90.0% | 50.0% | 0% | 2 de 2 | 15.893 |

Comparación alumno por alumno contra el MAS (3 contratistas):

| Sistema | Mejor que el MAS | Igual | Peor | Diferencia media |
|---|---|---|---|---|
| MAS (1 AgenteCarga, antes de la mejora 1) | 8 | 6 | 6 | -0.67 |
| Solo CargaAvance | 0 | 3 | 17 | -1.86 |
| Solo CargaEquilibrio | 0 | 8 | 12 | -1.65 |
| Solo CargaPreferencias | 0 | 11 | 9 | -1.09 |
| Monoagente simple (solo requisitos) | 0 | 0 | 20 | -18.67 |
| LLM solo (llama3.2) | 0 | 0 | 20 | -53.47 |

## Sensibilidad a la muestra (sin LLM)

Puntuación media por sistema con otras semillas y con 50 alumnos. La última columna
cuenta, alumno por alumno, en cuántos el MAS de 3 contratistas sale mejor, igual o peor
que el AgenteCarga único de antes de la mejora 1.

| Muestra | MAS (3 contratistas) | MAS (1 AgenteCarga) | Mejor solo contratista | Monoagente simple | MAS vs 1 AgenteCarga (mejor / igual / peor) |
|---|---|---|---|---|---|
| 20 alumnos, semilla 7 | **89.57** | 88.9 | 88.48 (CargaPreferencias) | 70.9 | 6 / 6 / 8 |
| 20 alumnos, semilla 11 | **88.57** | 87.73 | 86.63 (CargaPreferencias) | 65.56 | 9 / 6 / 5 |
| 20 alumnos, semilla 13 | **89.03** | 88.56 | 88.27 (CargaPreferencias) | 65.81 | 7 / 10 / 3 |
| 50 alumnos, semilla 2027 | **89.44** | 88.37 | 88.67 (CargaPreferencias) | 66.06 | 18 / 24 / 8 |

## Notas

- **El LLM solo es `llama3.2` (3B) en CPU.** Recibe el plan completo con seriación y
  oferta, el kárdex, la meta de créditos y la petición del alumno. Responde con un JSON
  de siglas.
- **Los grupos del LLM solo.** El LLM no conoce los grupos, así que se toma el primero
  de cada materia, igual que el AgenteHorarios ingenuo.
- **Límite de tokens.** En una primera corrida con `max_tokens=150`, 6 de las 20
  respuestas quedaron cortadas y no se pudieron leer (media 31.2). Con 400 respondió en
  los 20 casos (media 36.1), que es la fila de la tabla.
- **Caché de Ollama.** La primera llamada de la sesión tardó 86 s; las demás, de 6 a 35 s, porque
  Ollama reutiliza el prefijo común del prompt.
- **Días libres.** Solo 2 de los 20 alumnos pidieron un día libre, así que esa columna se
  reporta como "k de 2" y no como porcentaje.
