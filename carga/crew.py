# -*- coding: utf-8 -*-
"""
Capa de ejecución y orquestación con CrewAI (Proyecto 2, sección 1).

Diferencias con el prototipo anterior (y por qué ya no truena):
  * Las herramientas NO dependen de que el LLM razone: ejecutan la lógica
    determinista (ontología + Contract Net) y devuelven un resumen corto.
    El LLM solo decide llamar la herramienta y redactar.
  * La sesión (alumno, preferencias, ontología) ya está cargada; cada
    herramienta recibe solo la matrícula. Menos parámetros = menos errores
    de "tool calling" en un modelo de 3B.
  * max_iter bajo, sin memoria de CrewAI, sin delegación entre
    especialistas, sin telemetría. Proceso secuencial por defecto (≈8 llamadas
    al LLM); el jerárquico existe pero hace bastantes más llamadas.
  * Pase lo que pase con el LLM, al final se calcula y guarda el resultado
    determinista: la recomendación nunca depende de que el modelo "atine".
"""
import os

os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")

from . import config, sistema  # noqa: E402
from .agentes import AgenteCarga, AgenteHistorial, AgenteHorarios  # noqa: E402
from .evaluacion import conflictos  # noqa: E402
from .preferencias import describir  # noqa: E402


def _herramientas(s):
    from crewai.tools import tool

    kb, est = s.kb, s.est
    estado = {}

    @tool("consultar_historial_academico")
    def consultar_historial_academico(matricula: str) -> str:
        """Consulta la ontología: kárdex del alumno, prerrequisitos y seriación.
        Devuelve las materias que SÍ puede cursar y las descartadas con su motivo."""
        with s.trazas.tarea("AgenteHistorial", "crewai:consultar_historial", matricula) as t:
            el, desc = AgenteHistorial().analizar(kb, est)
            estado["elegibles"] = el
            t["output"] = f"{len(el)} válidas"
        validas = "; ".join(f"{c} {kb.materias[c].nombre} ({kb.materias[c].creditos} cr, prioridad {p})"
                            for c, p in sorted(el.items(), key=lambda x: -x[1]))
        descart = "; ".join(f"{c}: {m}" for c, m in desc.items()) or "ninguna"
        return (f"Alumno {est.nombre} ({est.matricula}), semestre {est.semestre}, promedio {est.promedio}. "
                f"Aprobadas: {len(est.aprobadas)}. Reprobadas: {', '.join(est.reprobadas) or 'ninguna'}.\n"
                f"MATERIAS VÁLIDAS: {validas}\nDESCARTADAS: {descart}")

    @tool("evaluar_carga_academica")
    def evaluar_carga_academica(matricula: str) -> str:
        """Calcula créditos y número de materias y propone combinaciones equilibradas
        dentro de los límites institucionales de créditos."""
        el = estado.get("elegibles") or AgenteHistorial().analizar(kb, est)[0]
        with s.trazas.tarea("AgenteCarga", "crewai:evaluar_carga", matricula) as t:
            combos = AgenteCarga().proponer(kb, est, s.prefs, el)
            estado["combos"] = combos
            t["output"] = f"{len(combos)} combinaciones"
        lineas = [f"{i}. {', '.join(c)} = {sum(kb.materias[x].creditos for x in c)} créditos"
                  for i, c in enumerate(combos[:4], 1)]
        return (f"Límites: {kb.creditos_min}-{kb.creditos_max} créditos. Meta del alumno: "
                f"{s.prefs['creditos_objetivo']} créditos, máximo {s.prefs['max_materias']} materias.\n"
                + "\n".join(lineas))

    @tool("analizar_horarios_y_preferencias")
    def analizar_horarios_y_preferencias(matricula: str) -> str:
        """Asigna grupos a las combinaciones, detecta choques de horario y mide
        el ajuste con las preferencias (turno, modalidad, días libres)."""
        el = estado.get("elegibles") or AgenteHistorial().analizar(kb, est)[0]
        combos = estado.get("combos") or AgenteCarga().proponer(kb, est, s.prefs, el)
        with s.trazas.tarea("AgenteHorarios", "crewai:analizar_horarios", matricula) as t:
            asign = AgenteHorarios().asignar(kb, combos[:3], s.prefs, el)
            t["output"] = f"{len(asign)} propuestas"
        lineas = []
        for i, (m, g) in enumerate(asign, 1):
            ch = conflictos(kb, g)
            lineas.append(f"{i}. grupos {', '.join(g.values())} — "
                          f"{'SIN choques' if not ch else f'{len(ch)} choque(s)'}")
        return f"Preferencias interpretadas: {describir(s.prefs)}.\n" + "\n".join(lineas)

    def resumen_coordinacion() -> str:
        """Ejecuta (una sola vez) el Contract Net + Shapley y lo resume sin horarios."""
        if s.resultado is None:
            sistema.correr_contract_net(s)
            sistema.correr_shapley(s)
        g = s.resultado.ganadora
        mats = "; ".join(
            f"{kb.materias[c].nombre} ({kb.materias[c].creditos} créditos, "
            f"{kb.grupos[g.grupos[c]].modalidad.replace('_', ' ')}"
            f"{', la recursa' if c in est.reprobadas else ''}"
            f"{', le interesa' if c in s.prefs.get('materias_interes', []) else ''})" for c in g.materias)
        return (f"PROPUESTA GANADORA: {len(g.materias)} materias, {g.creditos(kb)} créditos, "
                f"puntuación {g.puntuacion}/100, sin choques de horario: {mats}.\n"
                "Criterios (0-100): " + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in g.criterios.items()) + ".")

    @tool("coordinar_carga")
    def coordinar_carga(matricula: str) -> str:
        """Herramienta de coordinación (Contract Net): evalúa todas las propuestas con
        0.30 avance + 0.25 horario + 0.25 carga + 0.20 preferencias, elige la mejor
        y calcula los valores de Shapley de cada agente."""
        return resumen_coordinacion()

    return (consultar_historial_academico, evaluar_carga_academica, analizar_horarios_y_preferencias,
            coordinar_carga, resumen_coordinacion)


def _limpiar(texto: str) -> str:
    """Quita muletillas típicas de modelos pequeños ("Lo siento, hubo un error…")."""
    import re
    lineas = texto.strip().splitlines()
    while lineas and re.match(r"^\s*(lo siento|disculpa|perd[oó]n|a continuaci[oó]n|aqu[ií] (est[aá]|tienes))",
                              lineas[0], re.I):
        lineas.pop(0)
    return "\n".join(lineas).strip() or texto.strip()


def ejecutar_crew(matricula, peticion="", proceso="secuencial", usar_llm=True, razonador=False):
    s = sistema.nueva_sesion(matricula, peticion, usar_llm=usar_llm, eco=True)
    if not s.llm.disponible:
        print(f"⚠ CrewAI necesita Ollama ({s.llm.motivo}).\n"
              f"  Levántalo con ./iniciar_ollama_cpu.sh  — mientras tanto se ejecuta el MAS sin CrewAI.")
        sistema.correr_contract_net(s)
        sistema.correr_shapley(s)
        sistema.cerrar(s, razonador=razonador)
        return s

    import logging

    from crewai import LLM, Agent, Crew, Process, Task
    logging.getLogger("crewai.llms.base_llm").setLevel(logging.ERROR)   # aviso de conteo de tokens

    llm = LLM(model=f"ollama/{s.llm.modelo}", base_url=s.llm.url, temperature=0.1, max_tokens=500)
    h_hist, h_carga, h_hor, h_coord, resumen_coordinacion = _herramientas(s)
    comun = dict(llm=llm, verbose=True, max_iter=3, allow_delegation=False, cache=True)

    a_hist = Agent(role="Analista de historial académico y requisitos",
                   goal="Determinar qué materias puede cursar el estudiante según su historial, "
                        "prerrequisitos, seriación y restricciones institucionales.",
                   backstory="Analiza la trayectoria académica y descarta asignaturas que el estudiante "
                             "todavía no puede cursar, usando la ontología institucional.",
                   tools=[h_hist], **comun)
    a_carga = Agent(role="Analista de carga académica",
                    goal="Evaluar combinaciones de materias y determinar cuáles representan una carga equilibrada.",
                    backstory="Analiza créditos y número de materias para evitar cargas excesivas.",
                    tools=[h_carga], **comun)
    a_hor = Agent(role="Analista de horarios y preferencias del estudiante",
                  goal="Evaluar compatibilidad de horarios y adaptar las propuestas a las preferencias.",
                  backstory="Interpreta preferencias como carga ligera, clases por la tarde o en línea.",
                  tools=[h_hor], **comun)
    a_man = Agent(role="Coordinador y recomendador académico",
                  goal="Coordinar a los especialistas, comparar propuestas y elegir la mejor carga.",
                  backstory="Integra los resultados de los especialistas mediante Contract Net.",
                  tools=[h_coord] if proceso == "secuencial" else [],
                  **{**comun, "allow_delegation": proceso == "jerarquico"})

    m = s.est.matricula
    t1 = Task(description=f"Usa la herramienta consultar_historial_academico con matricula '{m}'. "
                          "Resume en español qué materias puede cursar y cuáles no y por qué.",
              expected_output="Lista breve de materias válidas y descartadas.", agent=a_hist)
    t2 = Task(description=f"Usa la herramienta evaluar_carga_academica con matricula '{m}'. "
                          "Resume en español las combinaciones con sus créditos.",
              expected_output="Combinaciones de materias con total de créditos.", agent=a_carga)
    t3 = Task(description=f"Usa la herramienta analizar_horarios_y_preferencias con matricula '{m}'. "
                          "Resume en español si hay choques y cómo se respetan las preferencias.",
              expected_output="Reporte breve de compatibilidad de horarios.", agent=a_hor)
    # Un modelo de 3B a veces "se salta" la herramienta y redacta de memoria (lo
    # vimos en las pruebas). Por eso el resultado oficial del Contract Net se le
    # entrega en la propia tarea: el coordinador solo tiene que explicarlo.
    oficial = resumen_coordinacion()
    t4 = Task(description=f"Eres el coordinador. El protocolo Contract Net ya adjudicó la carga para '{m}'. "
                          f"RESULTADO OFICIAL (no lo cambies, puedes confirmarlo con la herramienta "
                          f"coordinar_carga):\n{oficial}\n\nRedacta para el estudiante, en español, 2 párrafos "
                          "cortos (máximo 120 palabras) que expliquen POR QUÉ se recomienda esa carga, "
                          "usando solo esas materias. No describas días ni horas, no uses listas ni JSON.",
              expected_output="Recomendación final en lenguaje natural, 2 párrafos, sin listas.",
              agent=a_man, context=[t1, t2, t3], tools=[h_coord])

    if proceso == "jerarquico":
        for t in (t1, t2, t3, t4):      # en jerárquico el manager decide quién hace qué
            t.agent = None
        crew = Crew(agents=[a_hist, a_carga, a_hor], tasks=[t1, t2, t3, t4], manager_agent=a_man,
                    process=Process.hierarchical, verbose=True, memory=False, tracing=False)
    else:
        crew = Crew(agents=[a_hist, a_carga, a_hor, a_man], tasks=[t1, t2, t3, t4],
                    process=Process.sequential, verbose=True, memory=False, tracing=False)

    texto, fuente = None, None
    try:
        with s.trazas.tarea("AgenteManager", f"crewai:kickoff_{proceso}", m) as t:
            salida = crew.kickoff()
            texto = str(getattr(salida, "raw", salida)).strip()
            t["output"] = f"{len(texto)} caracteres"
        fuente = f"CrewAI ({proceso}, {s.llm.modelo})"
    except Exception as e:
        print(f"\n⚠ CrewAI falló ({e}). Se usa el resultado determinista.")

    if s.resultado is None:          # el LLM nunca llamó la herramienta de coordinación
        sistema.correr_contract_net(s)
        sistema.correr_shapley(s)

    if texto:
        texto = _limpiar(texto)
        from .agentes import _es_fiel
        g = s.resultado.ganadora
        dias = {b.dia for c in g.materias for b in s.kb.grupos[g.grupos[c]].bloques}
        libres = [d for d in ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"] if d not in dias]
        if not _es_fiel(texto, s.kb, g, libres):
            print("⚠ La redacción de CrewAI mencionaba datos inexistentes; se usa la del Manager.")
            texto, fuente = None, None
    sistema.cerrar(s, explicacion=texto, fuente=fuente, razonador=razonador)
    return s
