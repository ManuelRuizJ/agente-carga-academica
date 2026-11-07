# -*- coding: utf-8 -*-
"""
Los cuatro agentes del MAS (fichas del Proyecto 2, sección 1.2).

Cada agente especializado tiene:
  * su comportamiento experto (lo que hace cuando participa), y
  * un comportamiento "ingenuo" (`*_ingenuo`) que se usa cuando NO participa
    en una coalición. Así se puede medir con Shapley cuánto aporta cada uno.
"""
from itertools import combinations, product

from . import config
from .evaluacion import (Propuesta, ajuste_grupo, analizar_elegibilidad,
                         c_carga, conflictos, evaluar_propuesta)
from .preferencias import construir_preferencias


# =========================================================================
class AgenteHistorial:
    nombre = "AgenteHistorial"
    rol = "Analista de historial académico y requisitos"

    def analizar(self, kb, est):
        """Kárdex + prerrequisitos + seriación + oferta → materias válidas."""
        return analizar_elegibilidad(kb, est)

    @staticmethod
    def ingenuo(kb, est):
        """Sin este agente nadie revisa el historial: todo lo ofertado parece válido."""
        return {c: 0.5 for c in sorted(kb.ofertadas)}, {}


# =========================================================================
class AgenteCarga:
    nombre = "AgenteCarga"
    rol = "Analista de carga académica"

    def proponer(self, kb, est, prefs, elegibles: dict, k=config.TOP_COMBINACIONES):
        """Genera combinaciones que respetan créditos mín./máx. y la carga deseada."""
        evitar = set(prefs.get("materias_evitar", []))
        interes = [c for c in prefs.get("materias_interes", []) if c in elegibles]
        orden = sorted((c for c in elegibles if c not in evitar),
                       key=lambda c: (-elegibles[c], kb.materias[c].semestre, c))
        candidatas = list(dict.fromkeys(interes + orden))[:config.MAX_CANDIDATAS]
        total_disp = sum(kb.materias[c].creditos for c in candidatas)

        evaluadas = []
        for n in range(1, min(prefs["max_materias"], len(candidatas)) + 1):
            for combo in combinations(candidatas, n):
                cr = sum(kb.materias[c].creditos for c in combo)
                if cr > kb.creditos_max:
                    continue
                if sum(not kb.materias[c].obligatoria for c in combo) > config.MAX_OPTATIVAS:
                    continue
                if cr < kb.creditos_min and total_disp >= kb.creditos_min:
                    continue
                prop = Propuesta("tmp", list(combo))
                carga = c_carga(kb, prop, prefs) / 100
                prio = sum(elegibles[c] for c in combo) / n
                s_int = (sum(c in combo for c in interes) / len(interes)) if interes else 1.0
                evaluadas.append((0.5 * carga + 0.3 * prio + 0.2 * s_int, combo))
        if not evaluadas and candidatas:     # muy pocas opciones: lo que alcance
            evaluadas = [(0.0, tuple(candidatas[:prefs["max_materias"]]))]
        evaluadas.sort(key=lambda x: (-x[0], x[1]))
        return [list(c) for _, c in evaluadas[:k]]

    @staticmethod
    def ingenuo(kb, est, prefs, elegibles: dict):
        """Sin este agente: se toman 5 materias 'de arriba hacia abajo' del plan."""
        orden = sorted(elegibles, key=lambda c: (kb.materias[c].semestre, c))
        return [orden[:5]]


# =========================================================================
class AgenteHorarios:
    nombre = "AgenteHorarios"
    rol = "Analista de horarios y preferencias del estudiante"

    def interpretar_preferencias(self, kb, est, texto, llm):
        """Única tarea con LLM de los especialistas: lenguaje natural → JSON."""
        return construir_preferencias(est, kb.materias, texto, llm)

    def _mejor_asignacion(self, kb, materias, prefs):
        opciones = [kb.grupos_de(c) for c in materias]
        if any(not o for o in opciones):
            return {c: (o[0].clave if o else None) for c, o in zip(materias, opciones)}
        mejor, mejor_llave = None, None
        for combo in product(*opciones):
            choques = sum(a.choca_con(b) for a, b in combinations(combo, 2))
            ajuste = sum(ajuste_grupo(g, prefs) for g in combo)
            llave = (choques, -ajuste)
            if mejor_llave is None or llave < mejor_llave:
                mejor, mejor_llave = combo, llave
        return {g.materia: g.clave for g in mejor}

    def asignar(self, kb, combos, prefs, elegibles):
        """Asigna grupos sin choques y lo más alineados a las preferencias.
        Si una combinación tiene choques inevitables, propone también una
        variante quitando la materia de menor prioridad que choca."""
        propuestas, vistos = [], set()
        for combo in combos:
            grupos = self._mejor_asignacion(kb, combo, prefs)
            propuestas.append((combo, grupos))
            vistos.add(frozenset(combo))
            choques = conflictos(kb, grupos)
            if choques:
                implicadas = {kb.grupos[g].materia for par in choques for g in par}
                quitar = min(implicadas, key=lambda c: (elegibles.get(c, 0), c))
                variante = [c for c in combo if c != quitar]
                if variante and frozenset(variante) not in vistos:
                    vistos.add(frozenset(variante))
                    propuestas.append((variante, self._mejor_asignacion(kb, variante, prefs)))
        return propuestas

    @staticmethod
    def ingenuo(kb, combos, prefs, elegibles):
        """Sin este agente: el primer grupo de cada materia, sin revisar choques."""
        return [(combo, {c: (kb.grupos_de(c)[0].clave if kb.grupos_de(c) else None)
                         for c in combo}) for combo in combos]


# =========================================================================
class AgenteManager:
    nombre = "AgenteManager"
    rol = "Coordinador y recomendador académico"

    def evaluar(self, kb, est, propuestas, prefs, elegibles_reales):
        return [evaluar_propuesta(kb, est, p, prefs, elegibles_reales) for p in propuestas]

    def explicar(self, kb, est, prefs, ganadora, shapley, llm) -> tuple[str, str]:
        """Redacta la recomendación final. Con LLM si hay; si no, plantilla."""
        # Al LLM NO se le dan horas ni días por materia: un modelo de 3B los
        # "resume" mal ("de lunes a viernes…"). El horario exacto ya lo muestra
        # la tabla calculada; el LLM solo explica el porqué.
        lineas = []
        for c in ganadora.materias:
            m, g = kb.materias[c], kb.grupos.get(ganadora.grupos.get(c))
            motivo = "la recursa" if c in est.reprobadas else (
                "le interesa" if c in prefs.get("materias_interes", []) else
                ("obligatoria" if m.obligatoria else "optativa"))
            lineas.append(f"- {m.nombre}: {m.creditos} créditos, modalidad "
                          f"{g.modalidad.replace('_', ' ') if g else '-'}, {motivo}")
        dias = sorted({b.dia for c in ganadora.materias
                       for b in (kb.grupos[ganadora.grupos[c]].bloques if ganadora.grupos.get(c) else [])},
                      key=["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado"].index)
        libres = [d for d in ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"] if d not in dias]
        recursa = [kb.materias[c].nombre for c in ganadora.materias if c in est.reprobadas]
        hechos = (
            f"Estudiante: {est.nombre}, semestre {est.semestre}, promedio {est.promedio}.\n"
            f"Preferencias: {prefs_txt(prefs)}.\n"
            f"Carga recomendada ({len(ganadora.materias)} materias, {ganadora.creditos(kb)} créditos, "
            f"puntuación {ganadora.puntuacion}/100):\n" + "\n".join(lineas) + "\n"
            f"Días con clase: {', '.join(dias)}. Días sin clase: {', '.join(libres) or 'ninguno'}.\n"
            f"Materias que recursa: {', '.join(recursa) or 'ninguna'}.\n"
            f"Criterios (0-100): {ganadora.criterios}.\n"
            f"Observaciones: {'; '.join(ganadora.notas) or 'sin choques de horario'}."
        )
        if llm is not None and llm.disponible:
            sistema = ("Eres un asesor académico universitario. Escribe en español, en segunda persona, "
                       "2 párrafos cortos (máximo 120 palabras en total) que expliquen POR QUÉ se "
                       "recomienda esta carga. Usa ÚNICAMENTE los datos proporcionados. NO describas "
                       "horarios, días ni horas de cada materia (eso ya aparece en una tabla). "
                       "No inventes nada. No uses listas, viñetas ni JSON.")
            texto = llm.chat(sistema, hechos, max_tokens=260, temperatura=0.2)
            if texto and _es_fiel(texto, kb, ganadora, libres):
                return texto, f"LLM ({llm.modelo})"
            if texto:
                return _plantilla(kb, est, prefs, ganadora), \
                    "plantilla (la redacción del LLM mencionaba datos que no existen y se descartó)"
        return _plantilla(kb, est, prefs, ganadora), "plantilla (sin LLM)"


def _es_fiel(texto, kb, prop, dias_libres) -> bool:
    """Guardia anti-alucinación: el LLM no puede nombrar materias que no están
    en la propuesta ni decir que hay clase en un día libre (o al revés)."""
    import re
    from .preferencias import _norm
    t = _norm(texto)
    dias_re = "lunes|martes|miercoles|jueves|viernes"
    if re.search(rf"\b(de|del)\s+({dias_re})\s+a(l)?\s+({dias_re})\b", t):   # "de lunes a viernes"
        return False
    if re.search(r"\b\d{1,2}:\d{2}\b", t):          # el LLM no recibe horas: si escribe una, la inventó
        return False
    if re.search(r"^\s*([-*•]|\d+\.)\s", texto, re.M):   # se pidió prosa, no listas
        return False
    if not texto.rstrip().endswith((".", "!", ")", "»", '"')):   # respuesta cortada a la mitad
        return False
    for c, m in kb.materias.items():
        if c not in prop.materias and len(m.nombre) > 8 and _norm(m.nombre) in t:
            return False
    if "solo" in t or "unicamente" in t:          # "clases solo lunes y miércoles"
        import re
        for frase in re.split(r"[.;\n]", t):
            if ("solo" in frase or "unicamente" in frase) and any(
                    _norm(d) in frase for d in ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]):
                con_clase = [d for d in ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
                             if d not in dias_libres]
                if not all(_norm(d) in frase for d in con_clase):
                    return False
    return True


def prefs_txt(p):
    from .preferencias import describir
    return describir(p)


def _plantilla(kb, est, prefs, g):
    nombres = [kb.materias[c].nombre for c in g.materias]
    recursa = [kb.materias[c].nombre for c in g.materias if c in est.reprobadas]
    txt = (f"{est.nombre.split()[0]}, para {kb.periodo} te recomendamos inscribir "
           f"{len(nombres)} materias ({g.creditos(kb)} créditos): {', '.join(nombres)}. ")
    if recursa:
        txt += f"Se prioriza recursar {', '.join(recursa)} porque es prerrequisito de materias posteriores. "
    txt += (f"La combinación cumple el rango institucional de {kb.creditos_min}–{kb.creditos_max} créditos "
            f"y obtuvo {g.puntuacion}/100 en la evaluación del coordinador. ")
    if g.criterios.get("compatibilidad_horario", 0) == 100:
        txt += "No hay choques de horario"
    else:
        txt += "Atención: hay choques de horario"
    txt += (f" y el ajuste a tus preferencias de turno, modalidad e intereses es de "
            f"{g.criterios.get('preferencias')}/100.")
    return txt
