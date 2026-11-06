# -*- coding: utf-8 -*-
"""Punto único que ejecuta el MAS completo para un estudiante."""
from dataclasses import dataclass

from . import config
from .agentes import AgenteHorarios, AgenteManager
from .contract_net import ejecutar, valores_shapley
from .evaluacion import analizar_elegibilidad
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
    explicacion: str = ""
    fuente_exp: str = ""
    inferencias: dict = None


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
    return s.resultado


def correr_shapley(s: Sesion):
    with s.trazas.tarea("AgenteManager", "calcular_valores_shapley", "8 coaliciones") as t:
        s.phi, s.v = valores_shapley(s.kb, s.est, s.prefs, s.elegibles_reales)
        t["output"] = ", ".join(f"{k}={v}" for k, v in s.phi.items())
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
                  s.trazas, s.llm, s.inferencias)
    rutas = {"reporte": base.with_name(f"reporte_{s.est.matricula}.md"),
             "trazas": base.with_name(f"trazas_{s.est.matricula}.json"),
             "ontologia": base.with_name(f"kb_{s.est.matricula}.owl")}
    rutas["reporte"].parent.mkdir(parents=True, exist_ok=True)
    rutas["reporte"].write_text(md, encoding="utf-8")
    s.trazas.guardar(rutas["trazas"])
    if s.resultado.ganadora:
        guardar_en_ontologia(s.kb, s.est, s.resultado, s.phi, s.trazas, rutas["ontologia"])
    else:
        rutas.pop("ontologia")
    if imprimir:
        resumen_terminal(s.kb, s.est, s.prefs, s.resultado, s.phi, s.explicacion, s.fuente_exp)
        for k, r in rutas.items():
            print(f" {k:9} → {r.relative_to(config.RAIZ)}")
    return rutas


def recomendar(matricula, peticion="", usar_llm=True, razonador=False, eco=True):
    s = nueva_sesion(matricula, peticion, usar_llm, eco)
    if eco:
        print(f"\n▶ Contract Net para {s.est.nombre} ({matricula})")
    correr_contract_net(s)
    correr_shapley(s)
    cerrar(s, razonador=razonador)
    return s
