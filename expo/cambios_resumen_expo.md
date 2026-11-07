# Cambios al resumen de Expo: busca → reemplaza

_Preparado el 7 de noviembre de 2026 sobre la versión `Plantilla_resumen_O25 (3).docx`._

Archivo: `Plantilla_resumen_O25 (3).docx`. Cada "**Busca**" está copiado tal cual de tu
versión. Usa Ctrl+F en Word, o copia por párrafo. Todos los números salen de
`resultados/experimento.md` y del sistema actual.

**Numeración de referencias (IEEE, por orden de aparición).** Las de la introducción
([1]–[5]) no cambian; las demás quedan así:
[6] antecedente (nueva), [7] CrewAI, [8] Llama 3.2 (nueva), [9] Protégé,
[10] owlready2 (nueva), [11] plan de estudios (nueva), [12] HermiT, [13] Shapley,
[14] Claude. Los textos nuevos de abajo ya traen esos números.

---

## Encabezado

**1. Título**
- Busca: "Asesor académico multiagente con CrewAI, ontología OWL y transparencia por Valores de Shapley para la recomendación personalizada de carga académica"
- Cambia a: "Asesor académico multiagente con ontología OWL, Contract Net y Valores de Shapley para la recomendación personalizada de carga académica"

**2. Autor corresponsal** (falta el asterisco)
- Busca: "Valencia Barragán Diana Laura (séptimo semestre en Ingeniería en Sistemas Computacionales)1,"
- Cambia a: "Valencia Barragán Diana Laura (séptimo semestre en Ingeniería en Sistemas Computacionales)1,*"

**3. Palabras clave** (opcional, más distintivas)
- Busca: "Sistema Multiagente, ontologías OWL, Recomendación académica"
- Cambia a: "Sistema multiagente, Ontología OWL, Valor de Shapley"

## Introducción

**4. Antecedente** (la plantilla lo pide)
- Busca: "La aportación es una arquitectura híbrida y auditable: cada recomendación puede explicarse con el Valor de Shapley de cada agente."
- Cambia a: "A diferencia de los sistemas de recomendación educativos, que suelen sugerir cursos sin justificar su decisión [6], la aportación es una arquitectura híbrida y auditable: cada recomendación puede explicarse con el Valor de Shapley de cada agente."
- La [6] la tienen que buscar ustedes: una revisión sistemática real sobre sistemas de recomendación en educación. **Verifíquenla.** Si no la encuentran, no agreguen esta frase y resten 1 a todas las referencias de la [7] en adelante.

**5. Objetivos específicos**
- Busca: "Objetivos específicos: (i) modelar el dominio en una ontología OWL 2; (ii) orquestar cuatro agentes especializados con CrewAI; (iii) coordinar sus propuestas con Contract Net como herramienta personalizada en Python; y (iv) cuantificar la contribución de cada agente con Valores de Shapley."
- Cambia a: "Objetivos específicos: (i) modelar el dominio en una ontología OWL 2 poblada con el plan de estudios real; (ii) coordinar agentes especializados mediante Contract Net, con competencia entre contratistas; (iii) cuantificar la contribución de cada agente con Valores de Shapley; y (iv) evaluar el sistema frente a un monoagente y frente a un LLM sin agentes."

## Metodología

**6. Primer párrafo** (CrewAI deja de ser el núcleo)
- Busca: "La orquestación se realiza con CrewAI [6] mediante Process.hierarchical (Fig. 1). Un Manager Agent coordina tres agentes con rol, objetivo, historia y herramientas propias: el Analista de Historial y Requisitos (kárdex, prerrequisitos y seriación), el Analista de Carga Académica (créditos y equilibrio de la carga) y el Analista de Horarios y Preferencias (conflictos e interpretación de preferencias con el LLM). Las tres tareas son independientes y sus resultados se integran en una tarea de coordinación a cargo del Manager, que compara las propuestas y genera la recomendación final."
- Cambia a: "El sistema tiene un Manager y tres especialistas (Fig. 1): el AgenteHistorial (kárdex, prerrequisitos y seriación), el AgenteCarga (créditos y equilibrio de la carga) y el AgenteHorarios (grupos sin choques e interpretación de preferencias). La coordinación sigue los cuatro pasos de Contract Net [3], implementado en Python: el Manager anuncia la tarea (cfp); tres instancias del AgenteCarga con estrategias distintas (priorizar el avance, el equilibrio o las preferencias) ofertan cada una sus dos mejores cargas, construidas solo con las materias que el AgenteHistorial validó; el AgenteHorarios les asigna grupos sin choques; el Manager adjudica la de mayor puntuación (1) y el ganador confirma el resultado. CrewAI [7] se usa como capa opcional de orquestación, secuencial o jerárquica, pero la decisión siempre la toma el protocolo."

**7. Pie de la Fig. 1**
- Busca: "Fig. 1. Orquestación realizada con CrewAI mediante Process.hierarchical"
- Cambia a: "Fig. 1. Arquitectura del sistema: Contract Net con tres AgentesCarga en competencia, ontología OWL y capa de transparencia."
- La imagen debe cambiar a ese diagrama.

**8. Agregar la ecuación (1)** con el editor de ecuaciones, centrada, justo después del párrafo del punto 6:
`Score = 0.30·Av + 0.25·Ho + 0.25·Ca + 0.20·Pr        (1)`

**9. Segundo párrafo** (pesos y papel del LLM)
- Busca: "La coordinación sigue Contract Net [3] y se expone a CrewAI como una herramienta personalizada (@tool coordinar_carga) en Python puro: el Manager solicita propuestas, cada agente responde y se selecciona la de mayor puntuación (1), donde Av es el avance académico, Ho la compatibilidad de horario, Ca el equilibrio de carga y Pr el cumplimiento de preferencias; los pesos se ajustarán con las pruebas. La evaluación contempla escenarios que varían el historial del alumno, sus preferencias y la oferta de grupos, y mide por escenario los créditos, los conflictos de horario, la puntuación y el tiempo de ejecución."
- Cambia a: "En (1), Av es el avance académico, Ho la compatibilidad de horario, Ca el equilibrio de carga y Pr el cumplimiento de preferencias, cada uno de 0 a 100, con los pesos definidos en el diseño. El Manager adjudica con (1) y no con la autoevaluación de cada contratista, porque cada uno se califica con su propia escala. El LLM local llama3.2 [8], ejecutado solo en CPU con Ollama, únicamente convierte la petición del alumno en un JSON validado y redacta la explicación final; un filtro descarta cualquier texto que mencione materias u horarios ajenos a la propuesta."

**10. Párrafo de la ontología** (conteos correctos y plan real). Reemplaza el párrafo completo.
- Busca: "La base de conocimiento es una ontología OWL 2 construida en Protégé (Fig. 2)[7] con 36 clases, 57 object properties (con sus inversas) y 50 data properties. Modela programas, planes, materias y su seriación (tienePrerrequisito, asimétrica e irreflexiva), el kárdex (registros aprobados, reprobados y en curso), la oferta de grupos con horario y modalidad, las preferencias, las recomendaciones y los elementos del propio MAS (agentes y trazas). Su consistencia se verificó con el razonador HermiT [8]. Bajo el supuesto de mundo abierto (OWA), la ausencia de un registro aprobado no implica que la materia no esté aprobada, por lo que la verificación de prerrequisitos debe consultar explícitamente el historial completo del alumno."
- Cambia a: "La base de conocimiento es una ontología OWL 2 construida en Protégé (Fig. 2) [9] con 31 clases, 44 object properties (21 pares de inversas) y 51 data properties. Modela programas, planes, materias y su seriación (tienePrerrequisito, asimétrica e irreflexiva), el kárdex (registros aprobados, reprobados y en curso), la oferta de grupos con horario y modalidad, las preferencias, las recomendaciones y los elementos del propio MAS (agentes y trazas). Se pobló desde Python con owlready2 [10] con el plan de estudios real de Ingeniería en Sistemas Computacionales (79 materias, 35 con seriación) [11] y una oferta sintética de 97 grupos, en total 452 individuos. El razonador HermiT [12] verificó su consistencia y clasifica seis clases definidas, por ejemplo MateriaLlave (prerrequisito de dos o más materias). Bajo el supuesto de mundo abierto (OWA), la ausencia de un registro aprobado no implica que la materia no esté aprobada; por eso la regla «todos los prerrequisitos aprobados» la verifica el AgenteHistorial en Python, y su conclusión se guarda en la ontología como puedeCursar."

**11. Párrafo de transparencia** (se cambian las referencias y se agrega el final)
- Busca: "Con esas trazas se calcula el Valor de Shapley (2) [9] de cada agente i, donde N es el conjunto de agentes especializados, n=|N| y v(S) es la puntuación de la mejor recomendación construida solo con la coalición S."
- Cambia a: "Con esas trazas se calcula el Valor de Shapley (2) [13] de cada agente i, donde N es el conjunto de agentes especializados, n=|N| y v(S) es la puntuación de la mejor recomendación construida solo con la coalición S; cuando un agente no pertenece a S, su tarea se resuelve de forma ingenua (por ejemplo, sin el AgenteHistorial todo lo ofertado parece válido). Se calculan dos juegos: entre los tres roles y entre los tres contratistas."

**12. Agregar un párrafo nuevo** al final de Metodología: el diseño experimental y la declaración de uso de IA.
- "Para evaluar el sistema se generaron 20 alumnos sintéticos con semilla fija y coherentes con la seriación real (semestres 2.º a 8.º, 12 con materias reprobadas y 13 con una petición en lenguaje natural). Se comparó el MAS con: el MAS con un solo AgenteCarga, cada contratista por separado, un monoagente que solo verifica requisitos y el LLM sin agentes, que recibe el plan, el kárdex y la petición. Todos se calificaron con (1) y se revisaron con las mismas reglas: materias inválidas, choques de horario, créditos fuera del rango de 24–48, exceso de optativas y tiempo de ejecución. La prueba se repitió con otras tres muestras, una de ellas de 50 alumnos. Se utilizó un asistente de IA generativa [14] como apoyo en la programación y la redacción; los autores revisaron y validaron el contenido."

## Resultados y Discusión

**13. Párrafo inicial**
- Busca: "Se definieron tres escenarios sobre un catálogo sintético de ejemplo (14 materias y 26 grupos): un alumno regular con preferencia vespertina (E1), un alumno con dos materias reprobadas que pide carga ligera y clases presenciales (E2) y un alumno avanzado que pide clases en línea, vespertinas y carga ligera (E3). Las métricas se muestran en la Tabla 1; el tiempo corresponde a la lógica en Python, sin LLM."
- Cambia a: "La Tabla 1 resume el experimento (Fig. 3). El MAS obtuvo la mayor puntuación media y fue el único sistema sin incumplimientos: ninguna materia inválida, ningún choque de horario y todas las cargas dentro del rango de créditos."

**14. Tabla 1** (reemplaza el pie y todo el contenido)
- Pie: "Tabla 1: Métricas de los escenarios de prueba del prototipo." → "Tabla 1. Comparación de sistemas en 20 alumnos sintéticos con el plan de estudios real."
- Contenido nuevo (6 columnas, 4 filas):

| Sistema | Puntuación media | Con materias inválidas | Con choques | Fuera de 24–48 créditos | Tiempo por alumno (s) |
|---|---|---|---|---|---|
| MAS (3 contratistas) | 89.57 | 0% | 0% | 0% | 0.07 |
| MAS (1 AgenteCarga) | 88.90 | 0% | 0% | 0% | 0.03 |
| Monoagente simple | 70.90 | 0% | 15% | 5% | < 0.01 |
| LLM sin agentes (llama3.2) | 36.10 | 100% | 90% | 50% | 16 |

**15. Párrafo de la Tabla 2**
- Busca: "La Tabla 2 muestra los Valores de Shapley calculados con las trazas de cada escenario. En todos los casos su suma coincide con v(N), salvo redondeo, propiedad de eficiencia de Shapley [9]. La contribución varía con el perfil: el agente de historial domina en E1 y E2 (43.6 y 42.7), donde la seriación descarta varias materias, mientras que en E3, con pocas materias cursables, pesa más el agente de carga (37.0)."
- Cambia a: "La Tabla 2 muestra los Valores de Shapley de tres alumnos de prueba: A1 reprobó una materia llave, A2 reprobó Cálculo y pide carga ligera, y A3 es regular y pide carga pesada en línea. La suma coincide con v(N), salvo redondeo, por la propiedad de eficiencia [13]. El AgenteHistorial domina en A1 y A2, donde la seriación descarta muchas materias; en A3, con 28 materias válidas, pesa más el AgenteCarga (31.31), porque el reto es elegir 8 de ellas. En el juego entre contratistas, los tres ofertaron la misma carga para A3 y recibieron el mismo valor (10.2), lo que ilustra la propiedad de simetría."

**16. Tabla 2** (reemplaza el pie y los números)
- Pie: "Tabla 2. Valores de Shapley por agente y escenario (catálogo sintético de ejemplo)." → "Tabla 2. Valores de Shapley por agente y alumno de prueba."
- Contenido nuevo:

| Agente | A1 | A2 | A3 |
|---|---|---|---|
| A: Historial y requisitos | 39.41 | 41.04 | 28.10 |
| B: Carga académica (3 contratistas) | 30.07 | 27.79 | 31.31 |
| C: Horarios y preferencias | 22.80 | 25.70 | 24.97 |
| v(N) = Score de la recomendación | 92.29 | 94.53 | 84.39 |

**17. Discusión.** Reemplaza el párrafo completo.
- Busca: desde "Discusión: Las propuestas de los agentes de carga y de horarios" hasta "con el catálogo y el kárdex reales."
- Cambia a: "Discusión: La coordinación entre especialistas es lo que más aporta: el monoagente queda entre 18 y 23 puntos abajo en las cuatro muestras, y en la principal el 70% de sus cargas excede las optativas permitidas. El LLM sin agentes no respeta el kárdex ni la seriación: 233 de las 250 materias que propuso fueron inválidas (ya aprobadas, sin prerrequisito o no ofertadas), lo que justifica que en el sistema el LLM solo interprete y redacte. La competencia entre contratistas eleva la media de 88.90 a 89.57 y gana en promedio en las cuatro muestras (de +0.5 a +1.1 puntos), aunque no mejora a todos los alumnos; su principal aporte es saber qué estrategia sirve a cada perfil. Como limitaciones, los alumnos y la oferta son sintéticos, la función (1) otorga puntos parciales incluso a cargas inválidas, y solo se probó un LLM de 3B en CPU."

## Conclusiones

**18. Aporte central**
- Busca: "Contract Net aporta un mecanismo simple para comparar propuestas y Shapley una capa de auditoría de la contribución de cada agente."
- Cambia a: "Contract Net, con contratistas en competencia, permite comparar estrategias de forma explícita, y Shapley audita la contribución de cada agente. El experimento muestra que la validez académica la garantiza el razonamiento formal sobre la ontología y no el modelo de lenguaje."

**19. Trabajo futuro** (lo del catálogo completo ya se hizo)
- Busca: "Como trabajo futuro se plantea escalar la ontología al catálogo completo y a datos reales del kárdex, añadir reglas SWRL y verificaciones bajo mundo cerrado, integrar recuperación vectorial (RAG) para consultar reglamentos y ajustar los pesos de (1) con datos de uso."
- Cambia a: "Como trabajo futuro se plantea validar el sistema con kárdex y oferta reales y con estudiantes, compararlo con modelos de lenguaje de mayor tamaño, añadir reglas SWRL y ajustar los pesos de (1) con datos de uso."

## Referencias (lista final en orden)

- **[1]–[5]:** sin cambios. En la [3], borra los espacios de más en "IEEE            Trans.".
- **[6]:** NUEVA. El antecedente que ustedes buscan y verifican.
- **[7]:** la actual [6] (CrewAI).
- **[8]:** NUEVA. Meta, "Llama 3.2," 2024. [Online]. Available: https://www.llama.com
- **[9]:** la actual [7] (Protégé, Musen).
- **[10]:** NUEVA. J.-B. Lamy, "Owlready: Ontology-oriented programming in Python with automatic classification and high level constructs for biomedical ontologies," Artif. Intell. Med., vol. 80, pp. 11–28, 2017.
- **[11]:** NUEVA. Universidad Iberoamericana Puebla, "Plan de estudios de Ingeniería en Sistemas Computacionales (programa 2801)," portal Intrauia, consultado: 6 nov. 2026. Va sin enlace, porque es un portal con sesión.
- **[12]:** la actual [8] (HermiT).
- **[13]:** la actual [9] (Shapley).
- **[14]:** la actual [10] (Claude), sin cambios en su texto. Ahora sí se cita en el párrafo del punto 12.

## Anexo

**20. Fig. 3** (hoy no se cita en el texto). Reemplázala por la gráfica ya generada: `expo/fig3_puntuacion_por_sistema.png` (1771 × 732 px, es decir 300 dpi a 15 cm de ancho). Insértala a 15 cm de ancho en el Anexo; ya se cita en el punto 13. Si cambian los resultados, se regenera con `python3 expo/figura3.py`.
- Pie: "Fig. 3. Secuencia de ejecución: Contract Net, evaluación de propuestas, registro de trazas y cálculo de Shapley (elaboración propia)." → "Fig. 3. Puntuación media por sistema en el experimento con 20 alumnos sintéticos (elaboración propia)."
- Fig. 2 (ontología): el pie se queda igual; solo hay que subir la resolución.

## Al terminar
- **Extensión:** exporta a PDF. El cuerpo debe caber en 2 páginas, las referencias en la 3 y el anexo en la 4.
- **Si te pasas,** recorta en este orden:
  1. la última oración del punto 15 (simetría);
  2. "La prueba se repitió con otras tres muestras, una de ellas de 50 alumnos." del punto 12;
  3. la fila "MAS (1 AgenteCarga)" de la Tabla 1, pero entonces quita también del punto 17 la frase "eleva la media de 88.90 a 89.57".
- **Citas:** cada [n] del texto debe estar en la lista y cada referencia de la lista debe citarse.
- **Ecuaciones:** (1) y (2) con el editor de ecuaciones y su número.
