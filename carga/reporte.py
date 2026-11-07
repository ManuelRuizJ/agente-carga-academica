# -*- coding: utf-8 -*-
"""Reporte final en Markdown (salidas/) y resumen para la terminal."""
from . import config
from .contract_net import CONTRATISTAS, ESPECIALISTAS, SIGLAS
from .kb import DIAS
from .preferencias import describir


def _coal(S):
    return "{" + ",".join(SIGLAS[a] for a in ESPECIALISTAS if a in S) + "}"


def _coal_c(S):
    return "{" + ", ".join(c.replace("Carga", "") for c in CONTRATISTAS if c in S) + "}"


def licitacion(res) -> list[tuple]:
    """Por contratista: (nombre, # ofertas, mejor puntuación oficial, su autoevaluación
    de esa oferta, ¿ganó?). Cuenta también las ofertas que repitió de otro contratista:
    si dos ofertan la misma carga, ambos "la tienen" (la adjudicación es del primero)."""
    puntos = {frozenset(p.materias): p.puntuacion for p in res.propuestas}
    filas = []
    for c in CONTRATISTAS:
        suyas = [(puntos[frozenset(m)], nota) for m, nota in res.ofertas.get(c, [])
                 if frozenset(m) in puntos]
        mejor = max(suyas, default=(None, None))
        filas.append((c, len(res.ofertas.get(c, [])), mejor[0], mejor[1],
                      bool(res.ganadora and res.ganadora.autor == c)))
    return filas


def horario_semanal(kb, prop) -> list[str]:
    celdas = {}
    horas = set()
    for c, g in prop.grupos.items():
        if not g:
            continue
        for b in kb.grupos[g].bloques:
            for h in range(b.inicio, b.fin):
                celdas.setdefault((b.dia, h), []).append(c)
                horas.add(h)
    if not horas:
        return []
    dias = [d for d in DIAS[:5]]
    filas = ["| Hora | " + " | ".join(d[:3] for d in dias) + " |",
             "|---|" + "---|" * len(dias)]
    for h in range(min(horas), max(horas) + 1):
        fila = []
        for d in dias:
            v = celdas.get((d, h), [])
            fila.append(("⚠ " if len(v) > 1 else "") + "/".join(v))
        filas.append(f"| {h:02d}:00 | " + " | ".join(fila) + " |")
    return filas


def markdown(kb, est, prefs, res, phi, v, explicacion, fuente_exp, trazas, llm, inferencias=None,
             phi_c=None, v_c=None):
    g = res.ganadora
    L = [f"# Recomendación de carga académica — {est.nombre} ({est.matricula})", "",
         f"**Periodo:** {kb.periodo} · **Semestre:** {est.semestre} · **Promedio:** {est.promedio} · "
         f"**Créditos acumulados:** {est.creditos_acumulados}", "",
         "## Preferencias interpretadas", "",
         f"- Petición: _{prefs['texto'] or '(ninguna, se usan las guardadas en la ontología)'}_",
         f"- Interpretado por: {prefs['interpretado_por']}",
         f"- Resultado: {describir(prefs)}", ""]
    L += ["| Campo | Valor | Fuente |", "|---|---|---|"]
    for k in ("tipo_carga", "turno", "modalidad", "dias_libres", "materias_interes", "materias_evitar"):
        val = prefs.get(k)
        if val:
            L.append(f"| {k} | {val} | {prefs['fuente'].get(k, '-')} |")
    L += ["", "## Recomendación final", "", explicacion, "", f"_Redactado por: {fuente_exp}_", ""]

    if g:
        L += [f"**Propuesta ganadora {g.id}** (ofertada por **{g.autor}**) — "
              f"{g.creditos(kb)} créditos · puntuación **{g.puntuacion}/100**", "",
              "| Clave | Materia | Créd. | Grupo | Modalidad | Horario | Profesor |",
              "|---|---|---|---|---|---|---|"]
        for c in g.materias:
            m = kb.materias[c]
            gr = kb.grupos.get(g.grupos.get(c))
            L.append(f"| {c} | {m.nombre}{' (recursa)' if c in est.reprobadas else ''} | "
                     f"{m.creditos} | {gr.clave if gr else '-'} | "
                     f"{gr.modalidad.replace('_', ' ') if gr else '-'} | "
                     f"{', '.join(str(b) for b in gr.bloques) if gr else '-'} | "
                     f"{gr.profesor if gr else '-'} |")
        L += ["", "### Horario semanal", ""] + horario_semanal(kb, g) + [""]

    L += ["## Agente de Historial: materias descartadas", ""]
    L += [f"- **{c}** {kb.materias[c].nombre}: {mot}" for c, mot in res.descartadas.items()] or ["- Ninguna"]
    L += ["", "## Contract Net: licitación entre los AgentesCarga", "",
          "El Manager anunció la misma tarea a 3 contratistas. Cada uno ofertó sus "
          f"{config.OFERTAS_POR_CONTRATISTA} mejores cargas según su estrategia (autoevaluación) "
          "y el Manager las calificó con la función oficial.", "",
          "| Contratista | Pesos (carga/prioridad/interés/horario/facilidad) | Ofertas | "
          "Mejor puntuación oficial | Su autoevaluación | Resultado |", "|---|---|---|---|---|---|"]
    for c, n, mejor, auto, gano in licitacion(res):
        w = config.ESTRATEGIAS_CARGA[c]
        pesos = "/".join(str(w[k]) for k in ("carga", "prioridad", "interes", "horario", "facilidad"))
        if gano:
            estado = "**gana** ✅"
        elif g and mejor == g.puntuacion:
            estado = f"empata con la ganadora (desempate por orden de oferta: gana {g.autor})"
        else:
            estado = "rechazado"
        L.append(f"| {c} | {pesos} | {n} | {mejor if mejor is not None else '-'} | "
                 f"{auto if auto is not None else '-'} | {estado} |")
    L += ["", "Las autoevaluaciones **no se comparan entre sí**: cada contratista se califica "
          "con su propia escala. Por eso el Manager adjudica con la función oficial y no con "
          "lo que cada uno dice de sí mismo."]
    L += ["", "## Contract Net: propuestas evaluadas", "",
          "| Propuesta | Ofertó | Materias | Créd. | Avance (0.30) | Horario (0.25) | Carga (0.25) | "
          "Preferencias (0.20) | **Total** | Notas |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for p in res.propuestas:
        cr = p.criterios
        marca = " ✅" if p is g else ""
        L.append(f"| {p.id}{marca} | {p.autor.replace('Carga', '')} | {', '.join(p.materias)} | {p.creditos(kb)} | "
                 f"{cr['avance_academico']} | {cr['compatibilidad_horario']} | "
                 f"{cr['carga_equilibrada']} | {cr['preferencias']} | **{p.puntuacion}** | "
                 f"{'; '.join(p.notas)} |")

    L += ["", "## Transparencia: valores de Shapley", "",
          "v(S) = puntuación de la mejor propuesta que logra la coalición S "
          "(A = Historial, B = Carga, C = Horarios). Cuando un agente no participa, "
          "su tarea se hace de forma ingenua.", "",
          "| Coalición S | v(S) |", "|---|---|"]
    for S, val in sorted(v.items(), key=lambda x: (len(x[0]), _coal(x[0]))):
        L.append(f"| {_coal(S)} | {val} |")
    total = sum(phi.values()) or 1
    L += ["", "| Agente | φ (Shapley) | % de la contribución |", "|---|---|---|"]
    for a, val in sorted(phi.items(), key=lambda x: -x[1]):
        L.append(f"| {a} ({SIGLAS[a]}) | {val} | {100 * val / total:.1f}% |")
    L.append(f"| **Suma** | **{round(sum(phi.values()), 2)}** = v(N) | 100% |")
    L += ["", "B es el **equipo** de los 3 contratistas: cuando B no participa, la carga "
          "se arma de forma ingenua."]

    if phi_c:
        L += ["", "### Shapley entre los contratistas", "",
              "Segundo juego: Historial y Horarios siempre presentes; juegan solo los 3 "
              "AgentesCarga. v(S) = puntuación con los contratistas de S **menos** la "
              "puntuación sin ninguno (carga ingenua), para que v(∅) = 0.", "",
              "| Coalición S | v(S) |", "|---|---|"]
        for S, val in sorted(v_c.items(), key=lambda x: (len(x[0]), _coal_c(x[0]))):
            L.append(f"| {_coal_c(S)} | {val} |")
        L += ["", "| Contratista | φ |", "|---|---|"]
        for c in CONTRATISTAS:
            L.append(f"| {c} | {phi_c[c]} |")
        L.append(f"| **Suma** | **{round(sum(phi_c.values()), 2)}** = v(N) |")

    if inferencias:
        L += ["", "## Inferencias del razonador HermiT (clases definidas)", ""]
        L += [f"- **{k}**: {', '.join(vals) or '—'}" for k, vals in inferencias.items()]

    L += ["", "## Mensajes del Contract Net (FIPA-ACL)", "", "```"]
    L += [f"[{m.performativa:^16}] {m.emisor} → {m.receptor}: {m.contenido}" for m in trazas.mensajes]
    L += ["```", "", "## Trazas de ejecución", "",
          "| Hora | Agente | Tarea | Salida | Tiempo (s) | Éxito | Score |", "|---|---|---|---|---|---|---|"]
    for e in trazas.eventos:
        L.append(f"| {e.timestamp[11:]} | {e.agent} | {e.task} | {e.output} | {e.execution_time} | "
                 f"{'✔' if e.success else '✘'} | {e.score if e.score is not None else ''} |")
    L += ["", f"_LLM: {llm.modelo if llm.disponible else 'no disponible'} · llamadas: {llm.llamadas} · "
              f"tiempo LLM: {llm.segundos:.1f} s · {llm.motivo}_"]
    return "\n".join(L) + "\n"


def resumen_terminal(kb, est, prefs, res, phi, explicacion, fuente_exp, phi_c=None):
    g = res.ganadora
    print("\n" + "═" * 78)
    print(f" {est.nombre} ({est.matricula}) · semestre {est.semestre} · {kb.periodo}")
    print(f" Preferencias: {describir(prefs)}")
    print(f"   ↳ interpretadas por: {prefs['interpretado_por']}")
    print("═" * 78)
    if not g:
        print(" No se encontró una carga académica válida.")
        return
    print(f" CARGA RECOMENDADA ({g.creditos(kb)} créditos · puntuación {g.puntuacion}/100)"
          f" · la ofertó {g.autor}")
    for c in g.materias:
        gr = kb.grupos.get(g.grupos.get(c))
        hor = ", ".join(str(b) for b in gr.bloques) if gr else "-"
        print(f"  • {c:7} {kb.materias[c].nombre[:32]:32} {gr.clave if gr else '-':9} "
              f"{(gr.modalidad if gr else '-'):10} {hor}")
    print(f"  Criterios: " + " | ".join(f"{k.split('_')[0]} {v}" for k, v in g.criterios.items()))
    if g.notas:
        print("  ⚠ " + "; ".join(g.notas))
    print("\n Licitación: " + " | ".join(
        f"{c.replace('Carga', '')} {mejor if mejor is not None else '-'}{' ✔' if gano else ''}"
        for c, _, mejor, _, gano in licitacion(res)))
    print(" Shapley: " + " | ".join(f"{a.replace('Agente', '')} {v}" for a, v in phi.items()))
    if phi_c:
        print(" Shapley contratistas: " + " | ".join(
            f"{c.replace('Carga', '')} {v}" for c, v in phi_c.items()))
    print("\n " + explicacion.replace("\n", "\n "))
    print(f"   ({fuente_exp})")
    print("═" * 78)
