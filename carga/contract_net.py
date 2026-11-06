# -*- coding: utf-8 -*-
"""
Capa de coordinación en Python puro: Contract Net Protocol (Proyecto 2, sección 2).

  Manager ──cfp──▶ AgenteHistorial   ──propose(materias válidas)──▶
          ──cfp──▶ AgenteCarga       ──propose(combinaciones)──────▶
          ──cfp──▶ AgenteHorarios    ──propose(propuestas c/grupos)▶
  Manager evalúa cada propuesta → accept-proposal (mejor) / reject-proposal (resto)

`ejecutar(..., activos=...)` permite correr el protocolo con cualquier
coalición de especialistas; es lo que usa el cálculo de Shapley.
"""
from dataclasses import dataclass, field
from itertools import combinations
from math import factorial

from .agentes import AgenteCarga, AgenteHistorial, AgenteHorarios, AgenteManager
from .evaluacion import Propuesta
from .trazas import Trazas

ESPECIALISTAS = ("AgenteHistorial", "AgenteCarga", "AgenteHorarios")
SIGLAS = {"AgenteHistorial": "A", "AgenteCarga": "B", "AgenteHorarios": "C"}


@dataclass
class ResultadoCN:
    estado: str
    ganadora: Propuesta | None = None
    propuestas: list = field(default_factory=list)
    elegibles: dict = field(default_factory=dict)
    descartadas: dict = field(default_factory=dict)

    @property
    def puntuacion(self):
        return self.ganadora.puntuacion if self.ganadora else 0.0


def ejecutar(kb, est, prefs, elegibles_reales, activos=ESPECIALISTAS, trazas=None) -> ResultadoCN:
    trazas = trazas or Trazas(activo=False)
    activos = set(activos)
    if not activos:                     # v(∅) = 0: sin especialistas no hay propuestas
        return ResultadoCN("sin_propuesta")
    hist, carga, hor, man = AgenteHistorial(), AgenteCarga(), AgenteHorarios(), AgenteManager()
    etiqueta = "+".join(SIGLAS[a] for a in ESPECIALISTAS if a in activos)

    # ---- 1. Historial y requisitos
    trazas.mensaje("cfp", man.nombre, hist.nombre, f"¿Qué materias puede cursar {est.matricula}?")
    if hist.nombre in activos:
        with trazas.tarea(hist.nombre, "verificar_historial_y_seriacion",
                          f"{est.matricula}: {len(est.aprobadas)} aprobadas, "
                          f"{len(est.reprobadas)} reprobadas") as t:
            elegibles, descartadas = hist.analizar(kb, est)
            t["output"] = f"{len(elegibles)} válidas, {len(descartadas)} descartadas"
            t["detalles"] = {"elegibles": elegibles, "descartadas": descartadas}
        trazas.mensaje("propose", hist.nombre, man.nombre,
                       f"válidas: {', '.join(sorted(elegibles, key=lambda c: -elegibles[c]))}")
    else:
        elegibles, descartadas = AgenteHistorial.ingenuo(kb, est)

    if not elegibles:
        trazas.mensaje("refuse", hist.nombre, man.nombre, "no hay materias válidas")
        return ResultadoCN("sin_propuesta", descartadas=descartadas)

    # ---- 2. Carga académica
    trazas.mensaje("cfp", man.nombre, carga.nombre,
                   f"Combinaciones entre {kb.creditos_min}-{kb.creditos_max} créditos, "
                   f"meta {prefs['creditos_objetivo']}")
    if carga.nombre in activos:
        with trazas.tarea(carga.nombre, "evaluar_creditos_y_carga",
                          f"{len(elegibles)} materias candidatas") as t:
            combos = carga.proponer(kb, est, prefs, elegibles)
            t["output"] = f"{len(combos)} combinaciones equilibradas"
            t["detalles"] = {"combinaciones": combos}
        if combos:
            trazas.mensaje("propose", carga.nombre, man.nombre,
                           f"{len(combos)} combinaciones (mejor: {', '.join(combos[0])})")
    else:
        combos = AgenteCarga.ingenuo(kb, est, prefs, elegibles)
    if not combos:
        trazas.mensaje("refuse", carga.nombre, man.nombre, "ninguna combinación cumple los créditos")
        return ResultadoCN("sin_propuesta", elegibles=elegibles, descartadas=descartadas)

    # ---- 3. Horarios y preferencias
    trazas.mensaje("cfp", man.nombre, hor.nombre, f"Asignar grupos a {len(combos)} combinaciones")
    if hor.nombre in activos:
        with trazas.tarea(hor.nombre, "detectar_conflictos_y_preferencias",
                          f"{len(combos)} combinaciones") as t:
            asignadas = hor.asignar(kb, combos, prefs, elegibles)
            t["output"] = f"{len(asignadas)} propuestas con grupos asignados"
        trazas.mensaje("propose", hor.nombre, man.nombre, f"{len(asignadas)} propuestas con horario")
    else:
        asignadas = AgenteHorarios.ingenuo(kb, combos, prefs, elegibles)

    propuestas = [Propuesta(f"P{i}", list(m), dict(g), origen=etiqueta)
                  for i, (m, g) in enumerate(asignadas, 1)]

    # ---- 4. Evaluación y adjudicación (Manager)
    with trazas.tarea(man.nombre, "evaluar_propuestas_contract_net",
                      f"{len(propuestas)} propuestas") as t:
        man.evaluar(kb, est, propuestas, prefs, elegibles_reales)
        propuestas.sort(key=lambda p: (-p.puntuacion, p.id))
        ganadora = propuestas[0]
        t["output"] = f"gana {ganadora.id} con {ganadora.puntuacion}"
        t["score"] = ganadora.puntuacion
    for p in propuestas:
        if p is ganadora:
            trazas.mensaje("accept-proposal", man.nombre, "*",
                           f"{p.id} ({p.puntuacion}): {', '.join(p.materias)}")
        else:
            trazas.mensaje("reject-proposal", man.nombre, "*", f"{p.id} ({p.puntuacion})")
    return ResultadoCN("exito", ganadora, propuestas, elegibles, descartadas)


# =========================================================================
def coaliciones(jugadores=ESPECIALISTAS):
    for r in range(len(jugadores) + 1):
        for c in combinations(jugadores, r):
            yield frozenset(c)


def valores_shapley(kb, est, prefs, elegibles_reales, jugadores=ESPECIALISTAS):
    """Valor de Shapley exacto: v(S) = puntuación de la mejor propuesta de S.

        φ_i = Σ_{S ⊆ N\\{i}} |S|!(n-|S|-1)!/n! · [v(S ∪ {i}) − v(S)]
    """
    v = {S: ejecutar(kb, est, prefs, elegibles_reales, S).puntuacion for S in coaliciones(jugadores)}
    n = len(jugadores)
    phi = {}
    for i in jugadores:
        resto = [j for j in jugadores if j != i]
        total = 0.0
        for r in range(n):
            for S in combinations(resto, r):
                S = frozenset(S)
                peso = factorial(len(S)) * factorial(n - len(S) - 1) / factorial(n)
                total += peso * (v[S | {i}] - v[S])
        phi[i] = round(total, 2)
    return phi, v
