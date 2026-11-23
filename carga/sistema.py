# -*- coding: utf-8 -*-
"""Punto único que ejecuta el MAS completo para un estudiante."""
from dataclasses import dataclass

from . import config
from .agentes import AgenteHorarios, AgenteManager
from .contract_net import ejecutar, shapley_contratistas, valores_shapley
from .evaluacion import analizar_elegibilidad, conflictos
from .kb import BaseConocimiento
from .llm import ClienteLLM
from .persistencia import guardar_en_ontologia
from .reporte import markdown, resumen_terminal
from .trazas import Trazas


@dataclass
class Sesion:
    kb: BaseConocimiento
    est: object
    llm: ClienteLLM
    trazas: Trazas
    prefs: dict = None
    elegibles_reales: dict = None
    resultado: object = None
    phi: dict = None
    v: dict = None
    phi_c: dict = None          # Shapley entre los 3 contratistas AgenteCarga (mejora 1)
    v_c: dict = None
    explicacion: str = ""
    fuente_exp: str = ""
    inferencias: dict = None
    validacion: object = None   # veredicto del AgenteValidador (HermiT en RAM)


def nueva_sesion(matricula, peticion="", usar_llm=True, eco=True, kb=None, llm=None):
    kb = kb or BaseConocimiento()
    est = kb.estudiante(matricula)
    llm = llm or ClienteLLM(habilitado=usar_llm)
    s = Sesion(kb, est, llm, Trazas(eco=eco))
    with s.trazas.tarea("AgenteHorarios", "interpretar_preferencias",
                        peticion or "(preferencias guardadas)") as t:
        s.prefs = AgenteHorarios().interpretar_preferencias(kb, est, peticion, llm)
        t["output"] = s.prefs["interpretado_por"]
    # Verdad de la ontología para el evaluador (no depende de la coalición)
    s.elegibles_reales, _ = analizar_elegibilidad(kb, est)
    return s


def correr_contract_net(s: Sesion):
    s.resultado = ejecutar(s.kb, s.est, s.prefs, s.elegibles_reales, trazas=s.trazas)
    # Si el alumno pidió una cifra alta de créditos y con ella todas las
    # propuestas chocan de horario, el Manager vuelve a licitar con una meta
    # 4 créditos menor (sin bajar de la meta de una carga normal).
    pedido = s.prefs["creditos_objetivo"]
    piso = min(pedido, config.CARGA_TIPO["normal"]["creditos"])
    while (s.prefs["fuente"].get("creditos_objetivo") and s.resultado.ganadora
           and conflictos(s.kb, s.resultado.ganadora.grupos)
           and s.prefs["creditos_objetivo"] - 4 >= piso):
        s.prefs["creditos_objetivo"] -= 4
        s.prefs["max_materias"] = max(config.CARGA_TIPO["normal"]["max_materias"],
                                      -(-s.prefs["creditos_objetivo"] // 6))
        s.trazas.mensaje("cfp", "AgenteManager", "AgenteCarga",
                         f"todas las propuestas chocan de horario; nueva licitación con "
                         f"meta {s.prefs['creditos_objetivo']} créditos")
        s.resultado = ejecutar(s.kb, s.est, s.prefs, s.elegibles_reales, trazas=s.trazas)
    if s.prefs["creditos_objetivo"] != pedido:
        previo = s.prefs.get("creditos_ajustados")
        nota = f"con {pedido} no hubo horario sin choques; se bajó a {s.prefs['creditos_objetivo']}"
        s.prefs["creditos_ajustados"] = f"{previo}; {nota}" if previo else nota
    return s.resultado


def correr_validacion(s: Sesion):
    """El AgenteValidador certifica la propuesta ganadora con HermiT (en RAM)."""
    from .validador import AgenteValidador
    if not s.resultado or not s.resultado.ganadora:
        return None
    mats = s.resultado.ganadora.materias
    s.trazas.mensaje("request", "AgenteManager", "AgenteValidador",
                     f"¿Es consistente con la ontología? {', '.join(mats)}")
    with s.trazas.tarea("AgenteValidador", "validar_consistencia_hermit", ", ".join(mats)) as t:
        s.validacion = AgenteValidador().validar(s.kb, s.est.matricula, mats, trazas=s.trazas)
        v = s.validacion
        t["output"] = ("CONSISTENTE" if v.consistente else
                       "INCONSISTENTE" if v.consistente is False else f"sin veredicto: {v.error}")
        t["detalles"] = {"tiempo_hermit": v.tiempo_hermit, "aceptada": v.aceptada}
    return s.validacion


def correr_shapley(s: Sesion):
    with s.trazas.tarea("AgenteManager", "calcular_valores_shapley", "8 coaliciones") as t:
        s.phi, s.v = valores_shapley(s.kb, s.est, s.prefs, s.elegibles_reales)
        t["output"] = ", ".join(f"{k}={v}" for k, v in s.phi.items())
    with s.trazas.tarea("AgenteManager", "shapley_entre_contratistas", "8 coaliciones") as t:
        s.phi_c, s.v_c = shapley_contratistas(s.kb, s.est, s.prefs, s.elegibles_reales)
        t["output"] = ", ".join(f"{k}={v}" for k, v in s.phi_c.items())
    return s.phi


def cerrar(s: Sesion, explicacion=None, fuente=None, razonador=False, imprimir=True):
    if razonador:
        with s.trazas.tarea("AgenteManager", "razonador_hermit", "clases definidas") as t:
            try:
                s.inferencias = s.kb.inferencias_hermit()
                t["output"] = f"{len(s.inferencias)} clases clasificadas"
            except Exception as e:      # Java ausente, etc.: no detiene el sistema
                s.inferencias = {"(error)": [str(e)[:200]]}
                t["output"] = f"no se pudo ejecutar HermiT: {e}"
    if explicacion is None and s.resultado.ganadora:
        with s.trazas.tarea("AgenteManager", "generar_recomendacion_final", "propuesta ganadora") as t:
            explicacion, fuente = AgenteManager().explicar(
                s.kb, s.est, s.prefs, s.resultado.ganadora, s.phi, s.llm)
            t["output"] = fuente
    s.explicacion, s.fuente_exp = explicacion or "Sin propuesta.", fuente or "-"

    base = config.DIR_SALIDAS / s.est.matricula
    md = markdown(s.kb, s.est, s.prefs, s.resultado, s.phi, s.v, s.explicacion, s.fuente_exp,
                  s.trazas, s.llm, s.inferencias, phi_c=s.phi_c, v_c=s.v_c)
    rutas = {"reporte": base.with_name(f"reporte_{s.est.matricula}.md"),
             "trazas": base.with_name(f"trazas_{s.est.matricula}.json"),
             "ontologia": base.with_name(f"kb_{s.est.matricula}.owl")}
    rutas["reporte"].parent.mkdir(parents=True, exist_ok=True)
    rutas["reporte"].write_text(md, encoding="utf-8")
    s.trazas.guardar(rutas["trazas"])
    if s.resultado.ganadora:
        guardar_en_ontologia(s.kb, s.est, s.resultado, s.phi, s.trazas, rutas["ontologia"],
                             phi_c=s.phi_c)
    else:
        rutas.pop("ontologia")
    if imprimir:
        resumen_terminal(s.kb, s.est, s.prefs, s.resultado, s.phi, s.explicacion, s.fuente_exp,
                         phi_c=s.phi_c)
        for k, r in rutas.items():
            print(f" {k:9} → {r.relative_to(config.RAIZ)}")
    return rutas


def recomendar(matricula, peticion="", usar_llm=True, razonador=False, eco=True):
    s = nueva_sesion(matricula, peticion, usar_llm, eco)
    if eco:
        print(f"\n▶ Contract Net para {s.est.nombre} ({matricula})")
    correr_contract_net(s)
    correr_validacion(s)
    correr_shapley(s)
    cerrar(s, razonador=razonador)
    if eco and s.validacion is not None:
        print(f" validador → {s.validacion.justificacion}")
    return s
