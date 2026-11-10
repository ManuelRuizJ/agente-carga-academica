# -*- coding: utf-8 -*-
"""
Genera la ontología poblada (TBox del Proyecto 2 + individuos).

Lee  ontologia/P2_ontologia_carga_academica.owx  (sin modificarlo) y escribe
ontologia/carga_academica_poblada.owl  (RDF/XML, se abre en Protégé).

Además agrega algunas CLASES DEFINIDAS (equivalencias en Lógica Descriptiva)
para que el razonador HermiT pueda clasificar individuos automáticamente.
"""
import sys
from datetime import datetime
from itertools import combinations

from owlready2 import World, AllDifferent

from . import config

sys.path.insert(0, str(config.RAIZ))
from datos import semilla as S  # noqa: E402


def _turno(hora_inicio: int) -> str:
    return "matutino" if hora_inicio < 13 else "vespertino"


def _se_traslapan(bloques_a, bloques_b) -> bool:
    return any(da == db and ia < fb and ib < fa
               for da, ia, fa in bloques_a for db, ib, fb in bloques_b)


def poblar(destino=config.ONTO_POBLADA, verbose=True):
    mundo = World()
    onto = mundo.get_ontology(config.ONTO_BASE.resolve().as_uri()).load()
    o = onto.get_namespace(config.NS)

    with o:
        # ---------------- Clases definidas (equivalencias DL / Manchester)
        class GrupoVespertino(o.Grupo):
            """Grupo and tieneBloqueHorario some (BloqueHorario and turno value "vespertino")"""
        GrupoVespertino.equivalent_to = [
            o.Grupo & o.tieneBloqueHorario.some(o.BloqueHorario & o.turno.value("vespertino"))]

        class GrupoMatutino(o.Grupo):
            """Grupo and tieneBloqueHorario some (BloqueHorario and turno value "matutino")"""
        GrupoMatutino.equivalent_to = [
            o.Grupo & o.tieneBloqueHorario.some(o.BloqueHorario & o.turno.value("matutino"))]

        class GrupoEnLinea(o.Grupo):
            """Grupo and tieneModalidad some ModalidadEnLinea"""
        GrupoEnLinea.equivalent_to = [o.Grupo & o.tieneModalidad.some(o.ModalidadEnLinea)]

        class MateriaSeriada(o.Materia):
            """Materia and tienePrerrequisito some Materia"""
        MateriaSeriada.equivalent_to = [o.Materia & o.tienePrerrequisito.some(o.Materia)]

        class MateriaLlave(o.Materia):
            """Materia and esPrerrequisitoDe min 2 Materia  (desbloquea 2 o más)"""
        MateriaLlave.equivalent_to = [o.Materia & o.esPrerrequisitoDe.min(2, o.Materia)]

        class EstudianteConAdeudo(o.Estudiante):
            """Estudiante and tieneRegistro some RegistroReprobado"""
        EstudianteConAdeudo.equivalent_to = [
            o.Estudiante & o.tieneRegistro.some(o.RegistroReprobado)]

        for c, txt in [(GrupoVespertino, "Grupo con al menos un bloque vespertino"),
                       (GrupoMatutino, "Grupo con al menos un bloque matutino"),
                       (GrupoEnLinea, "Grupo ofrecido en línea"),
                       (MateriaSeriada, "Materia que tiene al menos un prerrequisito"),
                       (MateriaLlave, "Materia que es prerrequisito de 2 o más materias"),
                       (EstudianteConAdeudo, "Estudiante con al menos una materia reprobada")]:
            c.comment = [txt]

        # ---------------- Programa y restricción
        prog = o.ProgramaAcademico(S.PROGRAMA["id"])
        prog.nombrePrograma = S.PROGRAMA["nombre"]
        prog.creditosTotales = S.PROGRAMA["creditos_totales"]

        r = S.RESTRICCION_CREDITOS
        restr = o.RestriccionCreditos(r["id"])
        restr.descripcionRestriccion = r["descripcion"]
        restr.creditosMinimos = r["minimos"]
        restr.creditosMaximos = r["maximos"]
        restr.aplicaAPrograma = prog

        # ---------------- Periodos
        def periodo(pid, nombre, ini, fin):
            p = o.Periodo(pid)
            p.nombrePeriodo = nombre
            p.fechaInicio = datetime.fromisoformat(ini)
            p.fechaFin = datetime.fromisoformat(fin)
            return p

        pa = S.PERIODO_ACTUAL
        per_actual = periodo(pa["id"], pa["nombre"], pa["inicio"], pa["fin"])
        per_pasados = {k: periodo(*v) for k, v in S.PERIODOS_PASADOS.items()}

        # ---------------- Modalidades
        mods = {}
        for clave, (mid, clase, nombre) in S.MODALIDADES.items():
            m = getattr(o, clase)(mid)
            m.nombreModalidad = nombre
            mods[clave] = m

        # ---------------- Materias
        materias = {}
        for clave, (nombre, cred, sem, horas, dif, oblig, _) in S.MATERIAS.items():
            cls = o.MateriaObligatoria if oblig else o.MateriaOptativa
            m = cls(f"mat_{clave}")
            m.claveMateria = clave
            m.nombreMateria = nombre
            m.creditos = cred
            m.semestreSugerido = sem
            m.horasPorSemana = horas
            m.nivelDificultad = dif
            m.perteneceAPrograma = [prog]
            m.label = [nombre]
            materias[clave] = m
        for clave, (*_, prereqs) in S.MATERIAS.items():
            materias[clave].tienePrerrequisito = [materias[p] for p in prereqs]
        # Sin esto el razonador no puede contar (OWL no asume nombres únicos)
        AllDifferent(list(materias.values()))

        # ---------------- Profesores
        profes = {}
        for pid, (nombre, clave) in S.PROFESORES.items():
            p = o.Profesor(pid)
            p.nombre = nombre
            p.claveEmpleado = clave
            p.label = [nombre]
            profes[pid] = p

        # ---------------- Grupos y bloques horario
        grupos, bloques_por_grupo = {}, {}
        for cg, (mat, prof, mod, patron, cmax, cdisp) in S.GRUPOS.items():
            g = o.Grupo("grp_" + cg.replace("-", "_"))
            g.claveGrupo = cg
            g.cupoMaximo = cmax
            g.cupoDisponible = cdisp
            g.esOfertaDe = materias[mat]
            g.impartidoPor = profes[prof]
            g.tieneModalidad = mods[mod]
            g.ofrecidoEnPeriodo = per_actual
            g.label = [f"{cg} {S.MATERIAS[mat][0]}"]
            for i, (dia, hi, hf) in enumerate(S.H[patron], 1):
                b = o.BloqueHorario(f"blq_{cg.replace('-', '_')}_{i}")
                b.diaSemana = dia
                b.horaInicio = hi
                b.horaFin = hf
                b.turno = _turno(hi)
                g.tieneBloqueHorario.append(b)
            grupos[cg] = g
            bloques_por_grupo[cg] = S.H[patron]

        # enConflictoCon (simétrica) se materializa para poder consultarla en Protégé
        n_conf = 0
        for a, b in combinations(grupos, 2):
            if _se_traslapan(bloques_por_grupo[a], bloques_por_grupo[b]):
                grupos[a].enConflictoCon.append(grupos[b])
                n_conf += 1

        # ---------------- Estudiantes, registros y preferencias
        for mat_est, e in S.ESTUDIANTES.items():
            est = o.Estudiante(e["id"])
            est.nombre = e["nombre"]
            est.matricula = mat_est
            est.semestreActual = e["semestre"]
            est.cursaPrograma = prog
            est.label = [e["nombre"]]
            cal = list(e["aprobadas"].values())
            est.promedioGeneral = round(sum(cal) / len(cal), 2) if cal else 0.0
            est.creditosAcumulados = sum(S.MATERIAS[c][1] for c in e["aprobadas"])

            def registro(clase, clave, calif, intento):
                sem = min(S.MATERIAS[clave][2], max(S.PERIODOS_PASADOS))
                reg = clase(f"reg_{mat_est}_{clave}_{intento}")
                reg.registraMateria = materias[clave]
                reg.calificacion = float(calif)
                reg.numeroIntento = intento
                reg.cursadoEnPeriodo = per_pasados[sem]
                est.tieneRegistro.append(reg)

            for clave, calif in e["aprobadas"].items():
                registro(o.RegistroAprobado, clave, calif, 1)
                est.haAprobado.append(materias[clave])
            for clave, calif in e["reprobadas"].items():
                registro(o.RegistroReprobado, clave, calif, 1)

            pr = e["preferencias"]
            valor, prio, texto = pr["turno"]
            ph = o.PreferenciaHorario(f"pref_{mat_est}_horario")
            ph.valorPreferencia, ph.prioridad, ph.textoOriginal = valor, prio, texto
            valor, prio, texto = pr["modalidad"]
            pm = o.PreferenciaModalidad(f"pref_{mat_est}_modalidad")
            pm.valorPreferencia, pm.prioridad, pm.textoOriginal = valor, prio, texto
            pm.prefiereModalidad = mods[valor]
            valor, prio, texto, cobj, maxm = pr["carga"]
            pc = o.PreferenciaCarga(f"pref_{mat_est}_carga")
            pc.valorPreferencia, pc.prioridad, pc.textoOriginal = valor, prio, texto
            pc.creditosObjetivo, pc.maxMateriasDeseadas = cobj, maxm
            est.tienePreferencia = [ph, pm, pc]

        # ---------------- Agentes del MAS
        for nombre, (aid, clase, rol) in S.AGENTES.items():
            a = getattr(o, clase)(aid)
            a.nombreAgente = nombre
            a.rolAgente = rol

    destino.parent.mkdir(parents=True, exist_ok=True)
    onto.save(file=str(destino), format="rdfxml")
    if verbose:
        n_ind = len(list(onto.individuals()))
        print(f"✔ Ontología poblada: {destino.relative_to(config.RAIZ)}")
        print(f"  {n_ind} individuos | {len(materias)} materias | {len(grupos)} grupos | "
              f"{len(S.ESTUDIANTES)} estudiantes | {n_conf} pares de grupos en conflicto")
    return destino


if __name__ == "__main__":
    poblar()
