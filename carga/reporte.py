# -*- coding: utf-8 -*-
"""Reporte final en Markdown (salidas/) y resumen para la terminal."""
from .contract_net import ESPECIALISTAS, SIGLAS
from .kb import DIAS
from .preferencias import describir


def _coal(S):
    return "{" + ",".join(SIGLAS[a] for a in ESPECIALISTAS if a in S) + "}"


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


def markdown(kb, est, prefs, res, phi, v, explicacion, fuente_exp, trazas, llm, inferencias=None):
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
        L += [f"**Propuesta ganadora {g.id}** — {g.creditos(kb)} créditos · "
              f"puntuación **{g.puntuacion}/100**", "",
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
    L += ["", "## Contract Net: propuestas evaluadas", "",
          "| Propuesta | Materias | Créd. | Avance (0.30) | Horario (0.25) | Carga (0.25) | "
          "Preferencias (0.20) | **Total** | Notas |",
          "|---|---|---|---|---|---|---|---|---|"]
    for p in res.propuestas:
        cr = p.criterios
        marca = " ✅" if p is g else ""
        L.append(f"| {p.id}{marca} | {', '.join(p.materias)} | {p.creditos(kb)} | "
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


def resumen_terminal(kb, est, prefs, res, phi, explicacion, fuente_exp):
    g = res.ganadora
    print("\n" + "═" * 78)
    print(f" {est.nombre} ({est.matricula}) · semestre {est.semestre} · {kb.periodo}")
    print(f" Preferencias: {describir(prefs)}")
    print(f"   ↳ interpretadas por: {prefs['interpretado_por']}")
    print("═" * 78)
    if not g:
        print(" No se encontró una carga académica válida.")
        return
    print(f" CARGA RECOMENDADA ({g.creditos(kb)} créditos · puntuación {g.puntuacion}/100)")
    for c in g.materias:
        gr = kb.grupos.get(g.grupos.get(c))
        hor = ", ".join(str(b) for b in gr.bloques) if gr else "-"
        print(f"  • {c:7} {kb.materias[c].nombre[:32]:32} {gr.clave if gr else '-':9} "
              f"{(gr.modalidad if gr else '-'):10} {hor}")
    print(f"  Criterios: " + " | ".join(f"{k.split('_')[0]} {v}" for k, v in g.criterios.items()))
    if g.notas:
        print("  ⚠ " + "; ".join(g.notas))
    print("\n Shapley: " + " | ".join(f"{a.replace('Agente', '')} {v}" for a, v in phi.items()))
    print("\n " + explicacion.replace("\n", "\n "))
    print(f"   ({fuente_exp})")
    print("═" * 78)
