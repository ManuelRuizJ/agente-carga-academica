# -*- coding: utf-8 -*-
"""
Reglas académicas y función de evaluación (Proyecto 2, sección 2.2):

    puntuación = 0.30·avance_académico + 0.25·compatibilidad_horario
               + 0.25·carga_equilibrada  + 0.20·preferencias          (0–100)

El EVALUADOR usa siempre la verdad de la ontología (prerrequisitos reales,
preferencias reales). Así, cuando para Shapley se simula una coalición sin
algún agente, la propuesta resultante se califica con el mismo criterio
objetivo y se nota qué tanto aporta ese agente.
"""
from dataclasses import dataclass, field
from itertools import combinations

from . import config


@dataclass
class Propuesta:
    id: str
    materias: list                       # claves
    grupos: dict = field(default_factory=dict)   # clave materia -> clave grupo
    origen: str = ""                     # qué agentes la construyeron
    autor: str = ""                      # contratista AgenteCarga que la ofertó (mejora 1)
    autoevaluacion: float = 0.0          # la nota que le puso su autor (0..1)
    criterios: dict = field(default_factory=dict)
    puntuacion: float = 0.0
    notas: list = field(default_factory=list)

    def creditos(self, kb) -> int:
        return sum(kb.materias[c].creditos for c in self.materias)


# =========================================================== reglas (TBox+ABox)
def analizar_elegibilidad(kb, est) -> tuple[dict, dict]:
    """Regresa (elegibles, descartadas). elegibles: clave -> prioridad 0..1."""
    aprobadas = set(est.aprobadas)
    elegibles, descartadas = {}, {}
    for clave in sorted(kb.materias):
        m = kb.materias[clave]
        if clave in aprobadas:
            continue                                  # ya aprobada: no se menciona
        faltan = [p for p in m.prerrequisitos if p not in aprobadas]
        if faltan:
            descartadas[clave] = "falta prerrequisito: " + ", ".join(faltan)
        elif clave not in kb.ofertadas:
            descartadas[clave] = f"no se oferta en {kb.periodo}"
        else:
            elegibles[clave] = prioridad_academica(kb, est, clave)
    return elegibles, descartadas


def prioridad_academica(kb, est, clave) -> float:
    """0..1 — rezago, obligatoriedad, materias que desbloquea, recursamiento.

    En una optativa el "semestre ideal" solo indica desde cuándo se puede
    tomar, así que su rezago pesa poco (si no, para una alumna de 6.º las
    optativas de 4.º parecerían más urgentes que sus obligatorias)."""
    m = kb.materias[clave]
    rezago = est.semestre - m.semestre
    peso_rezago = 0.40 if m.obligatoria else 0.15
    p = peso_rezago * max(0.0, min(1.0, (rezago + 1) / 3))
    p += 0.20 if m.obligatoria else 0.0
    p += 0.25 * min(1.0, len(m.desbloquea) / 3)
    p += 0.15 if clave in est.reprobadas else 0.0
    return round(p, 3)


def conflictos(kb, grupos: dict) -> list[tuple]:
    gs = [kb.grupos[g] for g in grupos.values() if g]
    return [(a.clave, b.clave) for a, b in combinations(gs, 2) if a.choca_con(b)]


def ajuste_grupo(grupo, prefs) -> float:
    """Qué tanto un grupo respeta turno, modalidad y días libres (0..1)."""
    total, peso = 0.0, 0.0
    if prefs.get("turno"):
        w = prefs["peso_turno"]
        ok = sum(b.turno == prefs["turno"] for b in grupo.bloques) / len(grupo.bloques)
        total, peso = total + w * ok, peso + w
    if prefs.get("modalidad"):
        w = prefs["peso_modalidad"]
        if grupo.modalidad == prefs["modalidad"]:
            ok = 1.0
        elif "hibrida" in (grupo.modalidad, prefs["modalidad"]):
            ok = 0.5
        else:
            ok = 0.0
        total, peso = total + w * ok, peso + w
    if prefs.get("dias_libres"):
        w = prefs["peso_dias"]
        ok = 0.0 if any(b.dia in prefs["dias_libres"] for b in grupo.bloques) else 1.0
        total, peso = total + w * ok, peso + w
    return total / peso if peso else 1.0


# =========================================================== criterios (0-100)
def c_avance(kb, est, prop, prefs, elegibles_reales) -> float:
    if not prop.materias:
        return 0.0
    validas = [c for c in prop.materias if c in elegibles_reales]
    total = prop.creditos(kb)
    cred_validos = sum(kb.materias[c].creditos for c in validas)
    if not validas:
        return 0.0
    r = cred_validos / total
    progreso = min(1.0, cred_validos / prefs["creditos_objetivo"])
    prioridad = sum(elegibles_reales[c] for c in validas) / len(validas)
    # Urgentes: reprobadas o muy rezagadas que bloquean otras materias
    urgentes = [c for c, p in elegibles_reales.items() if p >= UMBRAL_URGENTE]
    if urgentes:
        cupo = min(len(urgentes), prefs["max_materias"])
        cobertura = min(1.0, sum(c in prop.materias for c in urgentes) / cupo)
    else:
        cobertura = 1.0
    return 100 * r * (0.45 * progreso + 0.30 * prioridad + 0.25 * cobertura)


UMBRAL_URGENTE = 0.6


def c_horario(kb, prop) -> float:
    if not prop.materias:
        return 0.0
    sin_grupo = sum(1 for c in prop.materias if not prop.grupos.get(c))
    return max(0.0, 100 - 35 * len(conflictos(kb, prop.grupos)) - 35 * sin_grupo)


def c_carga(kb, prop, prefs) -> float:
    if not prop.materias:
        return 0.0
    cr, n = prop.creditos(kb), len(prop.materias)
    obj = prefs["creditos_objetivo"]
    s1 = max(0.0, 1 - 2 * abs(cr - obj) / obj)
    if cr > kb.creditos_max or cr < kb.creditos_min:
        s1 *= 0.4                                         # viola la restricción institucional
    s2 = 1.0 if n <= prefs["max_materias"] else max(0.0, 1 - 0.3 * (n - prefs["max_materias"]))
    dificiles = sum(kb.materias[c].dificultad >= 4 for c in prop.materias)
    exceso = max(0, dificiles - prefs["max_dificiles"])
    optativas = sum(not kb.materias[c].obligatoria for c in prop.materias)
    exceso += max(0, optativas - config.MAX_OPTATIVAS)
    s3 = max(0.0, 1 - 0.3 * exceso)
    return 100 * (0.5 * s1 + 0.25 * s2 + 0.25 * s3)


def c_preferencias(kb, prop, prefs, elegibles_reales) -> float:
    if not prop.materias:
        return 0.0
    ajustes = [ajuste_grupo(kb.grupos[g], prefs) if g else 0.0
               for g in (prop.grupos.get(c) for c in prop.materias)]
    s_horario = sum(ajustes) / len(ajustes)
    interes = [c for c in prefs.get("materias_interes", []) if c in elegibles_reales]
    s_int = (sum(c in prop.materias for c in interes) / len(interes)) if interes else 1.0
    evitar = sum(c in prop.materias for c in prefs.get("materias_evitar", []))
    s_int = max(0.0, s_int - 0.5 * evitar)
    return 100 * (0.75 * s_horario + 0.25 * s_int)


def evaluar_propuesta(kb, est, prop, prefs, elegibles_reales) -> Propuesta:
    """Función de evaluación del Contract Net (la usa el AgenteManager)."""
    prop.criterios = {
        "avance_academico": round(c_avance(kb, est, prop, prefs, elegibles_reales), 1),
        "compatibilidad_horario": round(c_horario(kb, prop), 1),
        "carga_equilibrada": round(c_carga(kb, prop, prefs), 1),
        "preferencias": round(c_preferencias(kb, prop, prefs, elegibles_reales), 1),
    }
    prop.puntuacion = round(sum(config.PESOS[k] * v for k, v in prop.criterios.items()), 2)
    invalidas = [c for c in prop.materias if c not in elegibles_reales]
    if invalidas:
        prop.notas.append("materias no válidas: " + ", ".join(invalidas))
    choques = conflictos(kb, prop.grupos)
    if choques:
        prop.notas.append("choques: " + ", ".join(f"{a}↔{b}" for a, b in choques))
    return prop
