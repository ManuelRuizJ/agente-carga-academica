# -*- coding: utf-8 -*-
"""
Capa de coordinación en Python puro: Contract Net Protocol (Proyecto 2, sección 2).

  Manager ──cfp──▶ AgenteHistorial   ──propose(materias válidas)──▶
          ──cfp──▶ CargaAvance       ──propose(2 ofertas)──┐
          ──cfp──▶ CargaEquilibrio   ──propose(2 ofertas)──┼─▶  (compiten)
          ──cfp──▶ CargaPreferencias ──propose(2 ofertas)──┘
          ──cfp──▶ AgenteHorarios    ──propose(ofertas c/grupos)▶
  Manager evalúa todas → accept-proposal (ganador) / reject-proposal (resto)
  Ganador ──inform──▶ Manager  (resultado)

Son los 4 pasos del protocolo vistos en clase (tema 2, "Asignación de tareas"):
anuncio (cfp), oferta (cada contratista evalúa su capacidad y manda su bid),
adjudicación (al mejor postor) y resultado.

`ejecutar(..., activos=...)` permite correr el protocolo con cualquier
coalición; es lo que usa el cálculo de Shapley. "AgenteCarga" en `activos`
significa "el equipo completo de contratistas"; también se puede pasar el
nombre de contratistas sueltos (Shapley entre contratistas).
"""
from dataclasses import dataclass, field
from itertools import combinations
from math import factorial

from . import config
from .agentes import AgenteCarga, AgenteHistorial, AgenteHorarios, AgenteManager
from .evaluacion import Propuesta
from .trazas import Trazas

ESPECIALISTAS = ("AgenteHistorial", "AgenteCarga", "AgenteHorarios")
SIGLAS = {"AgenteHistorial": "A", "AgenteCarga": "B", "AgenteHorarios": "C"}
CONTRATISTAS = tuple(config.ESTRATEGIAS_CARGA)          # CargaAvance, CargaEquilibrio, ...


def crear_contratistas(estrategias=None):
    estrategias = estrategias or config.ESTRATEGIAS_CARGA
    return [AgenteCarga(nombre, pesos) for nombre, pesos in estrategias.items()]


@dataclass
class ResultadoCN:
    estado: str
    ganadora: Propuesta | None = None
    propuestas: list = field(default_factory=list)
    elegibles: dict = field(default_factory=dict)
    descartadas: dict = field(default_factory=dict)
    ofertas: dict = field(default_factory=dict)   # contratista -> [(combinación, autoevaluación)]

    @property
    def puntuacion(self):
        return self.ganadora.puntuacion if self.ganadora else 0.0


def ejecutar(kb, est, prefs, elegibles_reales, activos=ESPECIALISTAS, trazas=None,
             estrategias=None, k_ofertas=None) -> ResultadoCN:
    """`estrategias` y `k_ofertas` permiten cambiar a los contratistas; el
    experimento (mejora 2) los usa para correr el sistema de ANTES de la mejora 1:
    un solo AgenteCarga con los pesos originales y 6 ofertas."""
    trazas = trazas or Trazas(activo=False)
    activos = set(activos)
    if not activos:                     # v(∅) = 0: sin especialistas no hay propuestas
        return ResultadoCN("sin_propuesta")
    hist, hor, man = AgenteHistorial(), AgenteHorarios(), AgenteManager()
    # Qué contratistas participan: todos si está "AgenteCarga" (el equipo), o
    # solo los que se nombren uno por uno (para el Shapley entre contratistas).
    contratistas = [c for c in crear_contratistas(estrategias)
                    if "AgenteCarga" in activos or c.nombre in activos]
    k_ofertas = k_ofertas or config.OFERTAS_POR_CONTRATISTA
    if contratistas:
        activos.add("AgenteCarga")
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

    # ---- 2. Carga académica: licitación entre contratistas
    autor_de, nota_de = {}, {}          # combinación -> quién la ofertó primero y con qué nota
    combos, ofertas_de = [], {}
    if contratistas:
        for c in contratistas:          # 1. anuncio: la misma tarea a todos
            trazas.mensaje("cfp", man.nombre, c.nombre,
                           f"Arma una carga de {kb.creditos_min}-{kb.creditos_max} créditos, "
                           f"meta {prefs['creditos_objetivo']}")
        for c in contratistas:          # 2. oferta: cada uno evalúa su capacidad
            with trazas.tarea(c.nombre, "ofertar_carga",
                              f"{len(elegibles)} materias candidatas") as t:
                ofertas = c.ofertar(kb, est, prefs, elegibles, k=k_ofertas)
                ofertas_de[c.nombre] = ofertas
                t["output"] = f"{len(ofertas)} ofertas (mejor autoevaluación {ofertas[0][1] if ofertas else '-'})"
                t["detalles"] = {"ofertas": ofertas, "estrategia": c.pesos}
            nuevas = 0
            for combo, nota in ofertas:
                llave = frozenset(combo)
                if llave in autor_de:   # otro contratista ya ofertó lo mismo
                    continue
                autor_de[llave], nota_de[llave] = c.nombre, nota
                combos.append(combo)
                nuevas += 1
            if ofertas:
                repetidas = f" ({len(ofertas) - nuevas} repetida(s))" if nuevas < len(ofertas) else ""
                trazas.mensaje("propose", c.nombre, man.nombre,
                               f"{len(ofertas)} ofertas{repetidas}; la mejor (autoevaluación "
                               f"{ofertas[0][1]}): {', '.join(ofertas[0][0])}")
            else:
                trazas.mensaje("refuse", c.nombre, man.nombre, "no tengo una carga que cumpla")
    else:
        combos = AgenteCarga.ingenuo(kb, est, prefs, elegibles)
    if not combos:
        trazas.mensaje("refuse", "AgenteCarga", man.nombre, "ninguna combinación cumple los créditos")
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

    propuestas, autor = [], "AgenteCarga"
    for i, (m, g) in enumerate(asignadas, 1):
        # las variantes del AgenteHorarios (sin una materia) heredan el autor de la anterior
        autor = autor_de.get(frozenset(m), autor)
        propuestas.append(Propuesta(f"P{i}", list(m), dict(g), origen=etiqueta, autor=autor,
                                    autoevaluacion=nota_de.get(frozenset(m), 0.0)))

    # ---- 4. Evaluación y adjudicación (Manager)
    with trazas.tarea(man.nombre, "evaluar_propuestas_contract_net",
                      f"{len(propuestas)} propuestas") as t:
        man.evaluar(kb, est, propuestas, prefs, elegibles_reales)
        propuestas.sort(key=lambda p: (-p.puntuacion, p.id))
        ganadora = propuestas[0]
        t["output"] = f"gana {ganadora.id} con {ganadora.puntuacion}"
        t["score"] = ganadora.puntuacion
    # ---- 3. adjudicación: accept al mejor postor, reject a los demás
    for p in propuestas:
        if p is ganadora:
            trazas.mensaje("accept-proposal", man.nombre, p.autor,
                           f"{p.id} ({p.puntuacion}): {', '.join(p.materias)}")
        else:
            trazas.mensaje("reject-proposal", man.nombre, p.autor, f"{p.id} ({p.puntuacion})")
    # ---- 4. resultado: el ganador confirma la carga adjudicada
    trazas.mensaje("inform", ganadora.autor, man.nombre,
                   f"carga adjudicada: {ganadora.creditos(kb)} créditos, {len(ganadora.materias)} materias")
    return ResultadoCN("exito", ganadora, propuestas, elegibles, descartadas, ofertas_de)


# =========================================================================
def coaliciones(jugadores=ESPECIALISTAS):
    for r in range(len(jugadores) + 1):
        for c in combinations(jugadores, r):
            yield frozenset(c)


def valores_shapley(kb, est, prefs, elegibles_reales, jugadores=ESPECIALISTAS, fijos=()):
    """Valor de Shapley exacto: v(S) = puntuación de la mejor propuesta de S.

        φ_i = Σ_{S ⊆ N\\{i}} |S|!(n-|S|-1)!/n! · [v(S ∪ {i}) − v(S)]

    `fijos` son agentes que siempre están (no juegan). Se usa para el Shapley
    entre contratistas: Historial y Horarios fijos, y v(S) se mide contra lo
    que se logra SIN contratistas (carga ingenua), para que v(∅) = 0.
    """
    fijos = frozenset(fijos)
    base = ejecutar(kb, est, prefs, elegibles_reales, fijos).puntuacion if fijos else 0.0
    v = {S: round(ejecutar(kb, est, prefs, elegibles_reales, fijos | S).puntuacion - base, 2)
         for S in coaliciones(jugadores)}
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


def shapley_contratistas(kb, est, prefs, elegibles_reales):
    """¿Cuánto aporta cada contratista? Juego entre los 3 AgentesCarga, con
    Historial y Horarios siempre presentes."""
    return valores_shapley(kb, est, prefs, elegibles_reales, jugadores=CONTRATISTAS,
                           fijos=("AgenteHistorial", "AgenteHorarios"))
