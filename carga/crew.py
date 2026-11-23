# -*- coding: utf-8 -*-
"""
Capa de orquestación con CrewAI. La Crew es un CLIENTE del backend FastAPI.

    Crew (CrewAI) ──@tool──httpx──▶ FastAPI ──▶ ontología OWL / HermiT / SQLite

Cada herramienta @tool hace una petición HTTP con httpx a un endpoint de la
API (los endpoints /agentes/*, /validar, /recomendar). Así el razonamiento
del LLM queda desacoplado del conocimiento: el modelo solo decide qué
herramienta llamar y redacta; las reglas las aplica el backend.

Decisiones de diseño:
  * Cada herramienta recibe solo la matrícula (lo demás ya lo conoce la
    sesión). Menos parámetros = menos errores de "tool calling" en un 3B.
  * max_iter bajo, sin memoria, sin delegación entre especialistas, sin
    telemetría. Proceso secuencial por defecto; el jerárquico también existe.
  * El resultado oficial lo calcula el backend: la recomendación nunca
    depende de que el modelo "atine". La redacción de CrewAI solo se guarda
    si pasa el filtro anti-alucinación del servidor.

Requiere la API levantada:  python main.py api
"""
import os

os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")

import httpx  # noqa: E402

from . import config  # noqa: E402
from .llm import ClienteLLM  # noqa: E402


class ClienteAPI:
    """Envoltura mínima de httpx: cada llamada se etiqueta con la @tool que la hizo
    (encabezado x-cliente), así aparece en la bitácora de llamadas de SQLite."""

    def __init__(self, url=None):
        self.http = httpx.Client(base_url=url or config.API_URL, timeout=300)

    def get(self, ruta, quien="crewai"):
        r = self.http.get(ruta, headers={"x-cliente": quien})
        r.raise_for_status()
        return r.json()

    def post(self, ruta, quien="crewai", **cuerpo):
        r = self.http.post(ruta, json=cuerpo, headers={"x-cliente": quien})
        r.raise_for_status()
        return r.json()


def _resumen_oficial(rec) -> str:
    g = rec["ganadora"]
    mats = "; ".join(f"{m['nombre']} ({m['creditos']} créditos, {(m['modalidad'] or '-').replace('_', ' ')})"
                     for m in g["materias"])
    return (f"PROPUESTA GANADORA: {len(g['materias'])} materias, {g['creditos']} créditos, "
            f"puntuación {g['puntuacion']}/100, sin choques de horario: {mats}.\n"
            "Criterios (0-100): " + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in g["criterios"].items()))


def herramientas(api: ClienteAPI, peticion: str, estado: dict):
    """Funciones Python puras (se pueden probar sin CrewAI) que llaman a la API."""

    def consultar_historial_academico(matricula: str) -> str:
        """Consulta la ontología: kárdex del alumno, prerrequisitos y seriación.
        Devuelve las materias que SÍ puede cursar y las descartadas con su motivo."""
        return api.post("/agentes/historial", "crewai @tool consultar_historial_academico",
                        matricula=matricula)["resumen"]

    def evaluar_carga_academica(matricula: str) -> str:
        """Pide a los 3 contratistas AgenteCarga sus ofertas de combinaciones de
        materias dentro de los límites institucionales de créditos."""
        return api.post("/agentes/carga", "crewai @tool evaluar_carga_academica",
                        matricula=matricula, peticion=peticion)["resumen"]

    def analizar_horarios_y_preferencias(matricula: str) -> str:
        """Asigna grupos a las combinaciones, detecta choques de horario y mide
        el ajuste con las preferencias (turno, modalidad, días libres)."""
        return api.post("/agentes/horarios", "crewai @tool analizar_horarios_y_preferencias",
                        matricula=matricula, peticion=peticion)["resumen"]

    def validar_inscripcion(matricula: str) -> str:
        """Valida la solicitud de inscripción contra los axiomas de la ontología
        OWL con el razonador HermiT. Si es inconsistente, la RECHAZA con su justificación."""
        r = api.post("/validar", "crewai @tool validar_inscripcion",
                     matricula=matricula, materias=estado["materias_a_validar"], origen="crewai")
        estado["validacion"] = r
        return (f"{'ACEPTADA' if r['aceptada'] else 'RECHAZADA'} (HermiT: "
                f"{'consistente' if r['consistente'] else 'INCONSISTENTE' if r['consistente'] is False else 'sin veredicto'}"
                f", {r['tiempo_hermit']} s). Materias: {', '.join(r['materias'])}. "
                f"Justificación: {r['justificacion']}")

    def coordinar_carga(matricula: str) -> str:
        """Contract Net: confirma en la auditoría (SQLite) la propuesta adjudicada,
        evaluada con 0.30 avance + 0.25 horario + 0.25 carga + 0.20 preferencias."""
        ej = api.get(f"/auditoria/{estado['ejecucion_id']}", "crewai @tool coordinar_carga")
        return (estado["oficial"] + f"\nRegistro de auditoría #{ej['id']} ({ej['creada']}). "
                f"Shapley: {ej['shapley'].get('especialistas')}")

    return {f.__name__: f for f in (consultar_historial_academico, evaluar_carga_academica,
                                     analizar_horarios_y_preferencias, validar_inscripcion,
                                     coordinar_carga)}


def _limpiar(texto: str) -> str:
    """Quita muletillas típicas de modelos pequeños ("Lo siento, hubo un error…")."""
    import re
    lineas = texto.strip().splitlines()
    while lineas and re.match(r"^\s*(lo siento|disculpa|perd[oó]n|a continuaci[oó]n|aqu[ií] (est[aá]|tienes))",
                              lineas[0], re.I):
        lineas.pop(0)
    return "\n".join(lineas).strip() or texto.strip()


def _imprimir_validacion(v):
    print(f"\n{'═' * 78}\n VALIDADOR SEMÁNTICO · {v['matricula']} · {', '.join(v['materias'])}")
    print(f" HermiT: {'consistente' if v['consistente'] else 'INCONSISTENTE' if v['consistente'] is False else 'sin veredicto'}"
          f" ({v['tiempo_hermit']} s) → {'ACEPTADA' if v['aceptada'] else 'RECHAZADA'}")
    for h in v["hallazgos"]:
        print(f"  ✖ [{h['origen']}] {h['materia']}: {h['motivo']}")
        if h["axioma"]:
            print(f"      axioma: {h['axioma']}")
    print(f" auditoría SQLite → ejecución #{v.get('ejecucion_id')}\n{'═' * 78}")


def _imprimir_recomendacion(rec, texto, fuente):
    g = rec["ganadora"]
    print(f"\n{'═' * 78}\n {rec['alumno']['nombre']} ({rec['alumno']['matricula']}) · {rec['preferencias']}")
    print(f" CARGA RECOMENDADA ({g['creditos']} créditos · {g['puntuacion']}/100 · la ofertó {g['autor']})")
    for m in g["materias"]:
        print(f"  • {m['clave']} {m['nombre'][:34]:34} {m['grupo']} {m['modalidad']} {m['horario']}")
    v = rec["validacion"]
    print(f" Validador: {v['justificacion'] if v else '-'}")
    print(" Shapley: " + " | ".join(f"{k.replace('Agente', '')} {x}" for k, x in rec["shapley"]["especialistas"].items()))
    print(f"\n {texto or rec['explicacion']}\n   ({fuente or rec['fuente']})")
    print(f" auditoría SQLite → ejecución #{rec['ejecucion_id']}\n{'═' * 78}")


def ejecutar_crew(matricula, peticion="", proceso="secuencial", usar_llm=True, materias=None):
    """materias=None → recomendación completa; materias=[...] → validar esa solicitud."""
    api = ClienteAPI()
    try:
        salud = api.get("/salud", "crewai")
    except httpx.HTTPError as e:
        print(f"✖ No responde la API en {config.API_URL} ({e}).\n  Levántala con:  python main.py api")
        return None
    print(f"✔ API {config.API_URL} · ontología {salud['ontologia']['materias']} materias, "
          f"{salud['ontologia']['axiomas_seriacion']} axiomas · SQLite {salud['sqlite']['tablas']['ejecuciones']} ejecuciones")

    estado = {}
    fn = herramientas(api, peticion, estado)
    modo_validar = bool(materias)

    if modo_validar:
        estado["materias_a_validar"] = list(materias)
    else:
        # El backend corre el Contract Net completo (y lo guarda en SQLite). Un
        # modelo de 3B a veces "se salta" la herramienta; por eso el resultado
        # oficial se obtiene antes y se le da al coordinador en su tarea.
        rec = api.post("/recomendar", "crewai coordinador", matricula=matricula, peticion=peticion,
                       origen="crewai")
        if not rec["ganadora"]:
            print("✖ No hay una carga válida para este alumno.")
            return rec
        estado.update(ejecucion_id=rec["ejecucion_id"], oficial=_resumen_oficial(rec),
                      materias_a_validar=[m["clave"] for m in rec["ganadora"]["materias"]])

    llm_local = ClienteLLM(habilitado=usar_llm)
    if not llm_local.disponible:
        print(f"⚠ CrewAI necesita Ollama ({llm_local.motivo}).\n"
              f"  Levántalo con ./iniciar_ollama_cpu.sh — mientras tanto se llaman las herramientas directo.")
        if modo_validar:
            print(fn["consultar_historial_academico"](matricula).splitlines()[0])
            fn["validar_inscripcion"](matricula)
            _imprimir_validacion(estado["validacion"])
            return estado["validacion"]
        fn["validar_inscripcion"](matricula)
        _imprimir_recomendacion(rec, None, None)
        return rec

    import logging

    from crewai import LLM, Agent, Crew, Process, Task
    from crewai.tools import tool
    logging.getLogger("crewai.llms.base_llm").setLevel(logging.ERROR)   # aviso de conteo de tokens

    t = {nombre: tool(nombre)(f) for nombre, f in fn.items()}
    llm = LLM(model=f"ollama/{llm_local.modelo}", base_url=llm_local.url, temperature=0.1, max_tokens=500)
    comun = dict(llm=llm, verbose=True, max_iter=3, allow_delegation=False, cache=True)

    a_hist = Agent(role="Analista de historial académico y requisitos",
                   goal="Determinar qué materias puede cursar el estudiante según su historial, "
                        "prerrequisitos, seriación y restricciones institucionales.",
                   backstory="Analiza la trayectoria académica y descarta asignaturas que el estudiante "
                             "todavía no puede cursar, usando la ontología institucional.",
                   tools=[t["consultar_historial_academico"]], **comun)
    a_carga = Agent(role="Analista de carga académica",
                    goal="Evaluar combinaciones de materias y determinar cuáles representan una carga equilibrada.",
                    backstory="Coordina a tres contratistas que compiten con estrategias distintas "
                              "(avance, equilibrio, preferencias).",
                    tools=[t["evaluar_carga_academica"]], **comun)
    a_hor = Agent(role="Analista de horarios y preferencias del estudiante",
                  goal="Evaluar compatibilidad de horarios y adaptar las propuestas a las preferencias.",
                  backstory="Interpreta preferencias como carga ligera, clases por la tarde o en línea.",
                  tools=[t["analizar_horarios_y_preferencias"]], **comun)
    a_val = Agent(role="Validador semántico",
                  goal="Verificar con el razonador HermiT que la solicitud no viole ningún axioma de la "
                       "ontología y frenar la operación si la ontología se vuelve inconsistente.",
                  backstory="Es el guardián lógico del sistema: no opina, demuestra. Si HermiT encuentra "
                            "una inconsistencia, la operación se rechaza con su justificación.",
                  tools=[t["validar_inscripcion"]], **comun)
    a_man = Agent(role="Coordinador y recomendador académico",
                  goal="Coordinar a los especialistas, comparar propuestas y comunicar la decisión final.",
                  backstory="Integra los resultados de los especialistas mediante Contract Net.",
                  tools=[t["coordinar_carga"]] if not modo_validar else [],
                  **{**comun, "allow_delegation": proceso == "jerarquico"})

    m = matricula
    t_hist = Task(description=f"Usa la herramienta consultar_historial_academico con matricula '{m}'. "
                              "Resume en español qué materias puede cursar y cuáles no y por qué.",
                  expected_output="Lista breve de materias válidas y descartadas.", agent=a_hist)
    t_val = Task(description=f"Usa la herramienta validar_inscripcion con matricula '{m}'. Reporta en "
                             "español si la solicitud fue ACEPTADA o RECHAZADA y copia la justificación lógica.",
                 expected_output="Veredicto (ACEPTADA/RECHAZADA) y justificación.", agent=a_val)
    if modo_validar:
        t_fin = Task(description=f"Eres el coordinador. El alumno '{m}' pidió inscribir: "
                                 f"{', '.join(materias)}. Con el veredicto del validador, explica al alumno en "
                                 "español, en un párrafo corto, si puede inscribirlas y por qué. No inventes "
                                 "materias ni requisitos.",
                     expected_output="Un párrafo con la decisión y su justificación.",
                     agent=a_man, context=[t_hist, t_val])
        tareas, agentes = [t_hist, t_val, t_fin], [a_hist, a_val]
    else:
        t_carga = Task(description=f"Usa la herramienta evaluar_carga_academica con matricula '{m}'. "
                                   "Resume en español las combinaciones con sus créditos.",
                       expected_output="Combinaciones de materias con total de créditos.", agent=a_carga)
        t_hor = Task(description=f"Usa la herramienta analizar_horarios_y_preferencias con matricula '{m}'. "
                                 "Resume en español si hay choques y cómo se respetan las preferencias.",
                     expected_output="Reporte breve de compatibilidad de horarios.", agent=a_hor)
        t_fin = Task(description=f"Eres el coordinador. El protocolo Contract Net ya adjudicó la carga para '{m}'. "
                                 f"RESULTADO OFICIAL (no lo cambies, puedes confirmarlo con la herramienta "
                                 f"coordinar_carga):\n{estado['oficial']}\n\nRedacta para el estudiante, en español, "
                                 "2 párrafos cortos (máximo 120 palabras) que expliquen POR QUÉ se recomienda esa "
                                 "carga, usando solo esas materias. No describas días ni horas, no uses listas ni JSON.",
                       expected_output="Recomendación final en lenguaje natural, 2 párrafos, sin listas.",
                       agent=a_man, context=[t_hist, t_carga, t_hor, t_val], tools=[t["coordinar_carga"]])
        tareas, agentes = [t_hist, t_carga, t_hor, t_val, t_fin], [a_hist, a_carga, a_hor, a_val]

    if proceso == "jerarquico":
        for x in tareas:                # en jerárquico el manager decide quién hace qué
            x.agent = None
        crew = Crew(agents=agentes, tasks=tareas, manager_agent=a_man,
                    process=Process.hierarchical, verbose=True, memory=False, tracing=False)
    else:
        crew = Crew(agents=agentes + [a_man], tasks=tareas,
                    process=Process.sequential, verbose=True, memory=False, tracing=False)

    texto = None
    try:
        salida = crew.kickoff()
        texto = _limpiar(str(getattr(salida, "raw", salida)).strip())
    except Exception as e:
        print(f"\n⚠ CrewAI falló ({e}). Se usa el resultado del backend.")

    if "validacion" not in estado:      # el LLM nunca llamó al validador: se llama directo
        fn["validar_inscripcion"](matricula)

    if modo_validar:
        _imprimir_validacion(estado["validacion"])
        if texto:
            print(f"\n Coordinador (CrewAI, {proceso}):\n {texto}")
        return estado["validacion"]

    fuente = None
    if texto:
        r = api.post(f"/auditoria/{rec['ejecucion_id']}/explicacion", "crewai coordinador",
                     texto=texto, fuente=f"CrewAI ({proceso}, {llm_local.modelo})")
        if r["guardada"]:
            fuente = f"CrewAI ({proceso}, {llm_local.modelo})"
        else:
            print(f"⚠ La redacción de CrewAI no pasó el filtro del servidor ({r['motivo']}); "
                  "se usa la del Manager.")
            texto = None
    _imprimir_recomendacion(rec, texto, fuente)
    return rec
