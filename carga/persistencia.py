# -*- coding: utf-8 -*-
"""
Escribe el resultado de una ejecución DE VUELTA en la ontología.

La TBox del Proyecto 2 ya tenía PropuestaCarga, TrazaEjecucion, valorShapley,
puedeCursar, etc. Aquí se usan: la ontología funciona como memoria compartida
y persistente del MAS (tema "Integración de ontologías como base de conocimiento").

Resultado: salidas/kb_<matricula>.owl  → ábrelo en Protégé y consulta con DL Query.
"""
from datetime import datetime

import owlready2 as ow

from . import config


def guardar_en_ontologia(kb, est, resultado, phi, trazas, destino, phi_c=None):
    mundo = ow.World()
    onto = mundo.get_ontology(config.ONTO_POBLADA.resolve().as_uri()).load()
    o = onto.get_namespace(config.NS)
    alumno = o[est.iri]
    periodo = o[kb.periodo_iri] if kb.periodo_iri else None
    agentes = {a.nombreAgente: a for a in o.Agente.instances()}
    sello = datetime.now().strftime("%Y%m%d%H%M%S")

    with onto:
        # Conclusión del AgenteHistorial: puedeCursar (propiedad del TBox)
        for clave in resultado.elegibles:
            alumno.puedeCursar.append(o[f"mat_{clave}"])

        # Propuestas evaluadas en el Contract Net
        individuos = {}
        for p in resultado.propuestas:
            ind = o.PropuestaCarga(f"prop_{est.matricula}_{sello}_{p.id}")
            ind.propuestaPara = alumno
            if periodo:
                ind.propuestaParaPeriodo = periodo
            # generadaPor: el contratista que la ofertó ("En Contract Net cada
            # propuesta la emite un agente", comentario de la propia TBox)
            ind.generadaPor = agentes.get(p.autor) or agentes.get("AgenteManager")
            ind.totalCreditos = p.creditos(kb)
            ind.numeroMaterias = len(p.materias)
            ind.puntuacion = float(p.puntuacion)
            ind.avanceAcademico = float(p.criterios["avance_academico"])
            ind.compatibilidadHorario = float(p.criterios["compatibilidad_horario"])
            ind.cargaEquilibrada = float(p.criterios["carga_equilibrada"])
            ind.cumplimientoPreferencias = float(p.criterios["preferencias"])
            ind.esValida = p is resultado.ganadora
            for g in p.grupos.values():
                if g:
                    ind.incluyeGrupo.append(o["grp_" + g.replace("-", "_")])
            ind.comment = [("RECOMENDADA. " if p is resultado.ganadora else "") +
                           f"{p.id}: {', '.join(p.materias)}"]
            individuos[p.id] = ind

        # Trazas de ejecución
        ganadora_ind = individuos.get(resultado.ganadora.id) if resultado.ganadora else None
        for i, ev in enumerate(trazas.eventos, 1):
            t = o.TrazaEjecucion(f"traza_{est.matricula}_{sello}_{i:02d}")
            t.marcaTiempo = datetime.fromisoformat(ev.timestamp)
            t.tareaEjecutada = ev.task
            t.tiempoEjecucion = float(ev.execution_time)
            t.exito = ev.success
            if ev.score is not None:
                t.scoreTraza = float(ev.score)
            if ev.agent in agentes:
                t.trazaDeAgente = agentes[ev.agent]
            if ganadora_ind is not None:
                t.trazaDePropuesta = ganadora_ind

        # Transparencia: valor de Shapley de cada especialista
        for nombre, valor in phi.items():
            if nombre in agentes:
                agentes[nombre].valorShapley = float(valor)
        # y el de cada contratista en el juego entre AgentesCarga (mejora 1)
        for nombre, valor in (phi_c or {}).items():
            if nombre in agentes:
                agentes[nombre].valorShapley = float(valor)

    destino.parent.mkdir(parents=True, exist_ok=True)
    onto.save(file=str(destino), format="rdfxml")
    mundo.close()
    return destino
