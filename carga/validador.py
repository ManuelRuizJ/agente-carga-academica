# -*- coding: utf-8 -*-
"""
AgenteValidador: validación semántica con HermiT en RAM (inferencia efímera).

Reasoning offloading
--------------------
Cada validación crea un `World` de owlready2 NUEVO y EN MEMORIA, carga la
ontología poblada (TBox + ABox), agrega SOLO los hechos de la solicitud,
ejecuta HermiT y descarta el mundo. Nada se escribe en disco: la ontología
"oficial" nunca se modifica y dos solicitudes no se contaminan entre sí.

Cómo se detecta la violación
----------------------------
La TBox (ver `poblar.py`) tiene, por cada materia seriada X:

    PropuestaCon_X ≡ PropuestaCarga ⊓ ∃incluyeGrupo.(Grupo ⊓ ∃esOfertaDe.{X})
    PropuestaCon_X ⊑ ∀propuestaPara.(∃haAprobado.{P})

OWL trabaja con mundo abierto: que el kárdex no diga "aprobó P" no significa
que no la aprobó. Por eso el validador agrega un AXIOMA DE CIERRE solo para
el alumno de la solicitud:

    alumno : ∀haAprobado.{materias de su kárdex}

Si la solicitud incluye X y P no está en el kárdex, HermiT deriva que el
alumno debe haber aprobado P y, a la vez, que solo aprobó otras materias
(todas distintas por AllDifferent) → la ontología es INCONSISTENTE y el
agente rechaza la operación con la justificación lógica.

Además revisa reglas que OWL no expresa bien (suma de créditos, choques de
horario, oferta del periodo); esas se reportan aparte como "regla".
"""
import os
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from itertools import product

import owlready2 as ow

from . import config

_CANDADO = threading.Lock()      # HermiT es un proceso Java: uno a la vez


@dataclass
class Hallazgo:
    origen: str          # "HermiT" (axioma OWL) | "regla"
    materia: str
    motivo: str
    axioma: str = ""


@dataclass
class ResultadoValidacion:
    matricula: str
    materias: list
    aceptada: bool
    consistente: bool | None          # veredicto de HermiT (None = no se pudo ejecutar)
    hallazgos: list = field(default_factory=list)
    grupos: dict = field(default_factory=dict)
    creditos: int = 0
    tiempo_hermit: float = 0.0
    tiempo_total: float = 0.0
    error: str = ""

    @property
    def justificacion(self) -> str:
        if self.aceptada:
            return ("HermiT: la ontología sigue CONSISTENTE con la solicitud; "
                    "se cumplen la seriación y las reglas institucionales.")
        return " | ".join(f"[{h.origen}] {h.materia}: {h.motivo}" for h in self.hallazgos)

    def a_dict(self) -> dict:
        d = asdict(self)
        d["justificacion"] = self.justificacion
        return d


def _texto_axioma(clave, prereq):
    return f"PropuestaCon_{clave} ⊑ ∀propuestaPara.(∃haAprobado.{{{prereq}}})"


def _elegir_grupos(kb, materias):
    """Busca una asignación de grupos sin choques (backtracking acotado)."""
    opciones = [[g for g in kb.grupos_de(c) if g.cupo_disponible > 0] or [None] for c in materias]
    for intento, combo in enumerate(product(*opciones)):
        if intento > 5000:
            break
        gs = [g for g in combo if g]
        if not any(a.choca_con(b) for i, a in enumerate(gs) for b in gs[i + 1:]):
            return {c: (g.clave if g else None) for c, g in zip(materias, combo)}, False
    combo = [o[0] for o in opciones]
    return {c: (g.clave if g else None) for c, g in zip(materias, combo)}, True


class AgenteValidador:
    nombre = "AgenteValidador"
    rol = "Validador semántico"

    def validar(self, kb, matricula: str, materias: list, trazas=None) -> ResultadoValidacion:
        t0 = time.perf_counter()
        est = kb.estudiante(matricula)
        materias = list(dict.fromkeys(m.strip().upper() for m in materias if m.strip()))
        res = ResultadoValidacion(matricula, materias, aceptada=False, consistente=None)

        desconocidas = [c for c in materias if c not in kb.materias]
        for c in desconocidas:
            res.hallazgos.append(Hallazgo("regla", c, "no existe en el plan de estudios"))
        materias = [c for c in materias if c in kb.materias]
        if not materias:
            res.tiempo_total = round(time.perf_counter() - t0, 4)
            return res

        # ---------------- 1. Reglas que OWL no expresa bien
        for c in materias:
            if c in est.aprobadas:
                res.hallazgos.append(Hallazgo("regla", c, "ya está aprobada en el kárdex"))
            if c not in kb.ofertadas:
                res.hallazgos.append(Hallazgo("regla", c, f"no se oferta en {kb.periodo}"))
        res.creditos = sum(kb.materias[c].creditos for c in materias)
        if not kb.creditos_min <= res.creditos <= kb.creditos_max:
            res.hallazgos.append(Hallazgo(
                "regla", "carga", f"{res.creditos} créditos, fuera del rango "
                                  f"{kb.creditos_min}-{kb.creditos_max}"))
        res.grupos, choque = _elegir_grupos(kb, materias)
        if choque:
            res.hallazgos.append(Hallazgo("regla", "horario",
                                          "no existe combinación de grupos sin choques"))

        # ---------------- 2. HermiT en RAM
        try:
            res.consistente, res.tiempo_hermit = self._hermit(kb, est, materias, res.grupos)
        except Exception as e:                      # Java ausente, etc.
            res.error = f"no se pudo ejecutar HermiT: {e}"[:300]

        if res.consistente is False:
            # El veredicto es de HermiT; aquí solo se señalan los axiomas implicados
            for c in materias:
                for p in kb.materias[c].prerrequisitos:
                    if p not in est.aprobadas:
                        res.hallazgos.append(Hallazgo(
                            "HermiT", c,
                            f"viola la seriación: requiere {p} ({kb.materias[p].nombre}) "
                            f"y no está en el kárdex", _texto_axioma(c, p)))

        res.aceptada = res.consistente is True and not res.hallazgos
        res.tiempo_total = round(time.perf_counter() - t0, 4)
        if trazas is not None:
            trazas.mensaje("inform" if res.aceptada else "failure", self.nombre, "AgenteManager",
                           ("solicitud VÁLIDA" if res.aceptada else "solicitud RECHAZADA")
                           + f" ({', '.join(materias)})")
        return res

    @staticmethod
    def _hermit(kb, est, materias, grupos):
        """Mundo efímero en RAM: carga, agrega la solicitud, razona y se descarta."""
        with _CANDADO:
            ow.reasoning.JAVA_MEMORY = 512
            mundo = ow.World()                      # sin filename → solo RAM
            try:
                onto = mundo.get_ontology(config.ONTO_POBLADA.resolve().as_uri()).load()
                o = onto.get_namespace(config.NS)
                alumno = o[est.iri]
                with onto:
                    # Axioma de cierre: el alumno SOLO aprobó lo que dice su kárdex
                    aprobadas = list(alumno.haAprobado)
                    alumno.is_a.append(o.haAprobado.only(
                        ow.OneOf(aprobadas) if aprobadas else ow.Nothing))
                    sol = o.PropuestaCarga("solicitud_validacion")
                    sol.propuestaPara = alumno     # funcional en la TBox
                    for c in materias:
                        g = grupos.get(c)
                        ind = o["grp_" + g.replace("-", "_")] if g else None
                        if ind is None:             # materia sin grupo: grupo hipotético
                            ind = o.Grupo(f"grp_solicitud_{c}")
                            ind.esOfertaDe = o[f"mat_{c}"]
                        sol.incluyeGrupo.append(ind)
                t = time.perf_counter()
                consistente = hermit_consistente(mundo)
                return consistente, round(time.perf_counter() - t, 4)
            finally:
                mundo.close()


_HERMIT = os.path.join(os.path.dirname(ow.__file__), "hermit")
_HERMIT_CP = os.pathsep.join([_HERMIT, os.path.join(_HERMIT, "HermiT.jar")])
_RAM = "/dev/shm" if os.path.isdir("/dev/shm") else None     # tmpfs de Linux = RAM


def hermit_consistente(mundo) -> bool:
    """Solo verificación de CONSISTENCIA (`HermiT -k`), sin clasificar ni realizar.

    `sync_reasoner_hermit` de owlready2 clasifica y realiza toda la ontología
    (~12 s aquí); para validar una solicitud basta saber si es consistente
    (~1.5 s). El mundo se serializa a N-Triples en /dev/shm (memoria) y se
    borra al terminar."""
    f = tempfile.NamedTemporaryFile("wb", delete=False, dir=_RAM, suffix=".nt")
    try:
        mundo.save(f, format="ntriples")
        f.close()
        p = subprocess.run([ow.JAVA_EXE, "-Xmx512M", "-cp", _HERMIT_CP,
                            "org.semanticweb.HermiT.cli.CommandLine", "-k", "file://" + f.name],
                           capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(f.name)
    if p.returncode == 0 and "is satisfiable" in p.stdout:
        return True
    if "nconsistent" in p.stderr:
        return False
    raise RuntimeError(f"HermiT terminó con código {p.returncode}: {p.stderr.strip()[-300:]}")
