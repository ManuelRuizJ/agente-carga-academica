# -*- coding: utf-8 -*-
"""
Base de conocimiento: la ontología OWL es la ÚNICA fuente de verdad.

La ontología se carga UNA sola vez con owlready2 y se convierte a objetos
Python ligeros (dataclasses). Así los agentes razonan en milisegundos sin
volver a abrir el archivo en cada consulta (el prototipo anterior recargaba
el .owx en cada llamada a la herramienta).
"""
from dataclasses import dataclass, field
from functools import cached_property

import owlready2 as ow

from . import config

DIAS = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado"]


@dataclass(frozen=True)
class Bloque:
    dia: str
    inicio: int
    fin: int
    turno: str

    def __str__(self):
        return f"{self.dia[:3]} {self.inicio:02d}-{self.fin:02d}"


@dataclass
class Materia:
    clave: str
    nombre: str
    creditos: int
    semestre: int
    dificultad: int
    obligatoria: bool
    prerrequisitos: list = field(default_factory=list)   # claves
    desbloquea: list = field(default_factory=list)       # claves (inversa)


@dataclass
class Grupo:
    clave: str
    materia: str
    profesor: str
    modalidad: str          # presencial | en_linea | hibrida
    bloques: tuple
    cupo_disponible: int

    def choca_con(self, otro: "Grupo") -> bool:
        return any(a.dia == b.dia and a.inicio < b.fin and b.inicio < a.fin
                   for a in self.bloques for b in otro.bloques)


@dataclass
class Estudiante:
    matricula: str
    iri: str
    nombre: str
    semestre: int
    promedio: float
    creditos_acumulados: int
    aprobadas: dict          # clave -> calificación
    reprobadas: dict         # clave -> calificación
    preferencias: dict       # tal como están guardadas en la ontología


_MOD = {"ModalidadPresencial": "presencial", "ModalidadEnLinea": "en_linea",
        "ModalidadHibrida": "hibrida"}


class BaseConocimiento:
    def __init__(self, ruta=None):
        ruta = ruta or config.ONTO_POBLADA
        if not ruta.exists():
            from .poblar import poblar
            poblar(verbose=True)
        self.mundo = ow.World()
        self.onto = self.mundo.get_ontology(ruta.resolve().as_uri()).load()
        self.o = self.onto.get_namespace(config.NS)
        self._cargar()

    # ------------------------------------------------------------ carga
    def _cargar(self):
        o = self.o
        self.materias: dict[str, Materia] = {}
        for m in o.Materia.instances():
            self.materias[m.claveMateria] = Materia(
                clave=m.claveMateria, nombre=m.nombreMateria, creditos=m.creditos,
                semestre=m.semestreSugerido, dificultad=m.nivelDificultad,
                obligatoria=o.MateriaObligatoria in m.is_a,
                prerrequisitos=sorted(p.claveMateria for p in m.tienePrerrequisito),
                desbloquea=sorted(p.claveMateria for p in m.esPrerrequisitoDe))

        self.grupos: dict[str, Grupo] = {}
        for g in o.Grupo.instances():
            mod = g.tieneModalidad
            self.grupos[g.claveGrupo] = Grupo(
                clave=g.claveGrupo, materia=g.esOfertaDe.claveMateria,
                profesor=g.impartidoPor.nombre if g.impartidoPor else "Por asignar",
                modalidad=_MOD.get(type(mod).__name__, "presencial") if mod else "presencial",
                bloques=tuple(sorted(
                    (Bloque(b.diaSemana, b.horaInicio, b.horaFin, b.turno)
                     for b in g.tieneBloqueHorario),
                    key=lambda b: (DIAS.index(b.dia), b.inicio))),
                cupo_disponible=g.cupoDisponible or 0)

        r = o.RestriccionCreditos.instances()[0]
        self.creditos_min, self.creditos_max = r.creditosMinimos, r.creditosMaximos
        self.restriccion_txt = r.descripcionRestriccion
        per = o.Periodo.instances()
        actuales = [p for p in per if p.periodoOfrece]
        self.periodo = actuales[0].nombrePeriodo if actuales else "Periodo actual"
        self.periodo_iri = actuales[0].name if actuales else None

    # ------------------------------------------------------------ consultas
    def grupos_de(self, clave_materia: str) -> list[Grupo]:
        return sorted((g for g in self.grupos.values() if g.materia == clave_materia),
                      key=lambda g: g.clave)

    @cached_property
    def ofertadas(self) -> set:
        """Materias con al menos un grupo con cupo en el periodo actual."""
        return {g.materia for g in self.grupos.values() if g.cupo_disponible > 0}

    def matriculas(self) -> list[str]:
        return sorted(e.matricula for e in self.o.Estudiante.instances())

    def _sparql_registros(self, matricula: str, clase: str) -> dict:
        """Consulta SPARQL sobre la ontología: registros de un tipo para un alumno."""
        q = f"""
        PREFIX ca: <{config.NS}>
        SELECT ?clave ?cal WHERE {{
            ?e ca:matricula "{matricula}" .
            ?e ca:tieneRegistro ?r .
            ?r a ca:{clase} .
            ?r ca:registraMateria ?m .
            ?m ca:claveMateria ?clave .
            ?r ca:calificacion ?cal .
        }}"""
        return {clave: float(cal) for clave, cal in self.mundo.sparql(q)}

    def estudiante(self, matricula: str) -> Estudiante:
        ind = self.o.search_one(matricula=matricula)
        if ind is None:
            disponibles = ", ".join(self.matriculas())
            raise KeyError(f"No existe el estudiante '{matricula}'. Disponibles: {disponibles}")
        prefs = {}
        for p in ind.tienePreferencia:
            tipo = type(p).__name__
            if tipo == "PreferenciaHorario":
                prefs["turno"] = (p.valorPreferencia, p.prioridad or 1)
            elif tipo == "PreferenciaModalidad":
                prefs["modalidad"] = (p.valorPreferencia, p.prioridad or 1)
            elif tipo == "PreferenciaCarga":
                prefs["carga"] = (p.valorPreferencia, p.prioridad or 1,
                                  p.creditosObjetivo, p.maxMateriasDeseadas)
        return Estudiante(
            matricula=matricula, iri=ind.name, nombre=ind.nombre,
            semestre=ind.semestreActual, promedio=ind.promedioGeneral or 0.0,
            creditos_acumulados=ind.creditosAcumulados or 0,
            aprobadas=self._sparql_registros(matricula, "RegistroAprobado"),
            reprobadas=self._sparql_registros(matricula, "RegistroReprobado"),
            preferencias=prefs)

    # ------------------------------------------------------------ razonador
    def inferencias_hermit(self) -> dict:
        """Ejecuta HermiT (Java) y devuelve los miembros de las clases definidas."""
        ow.reasoning.JAVA_MEMORY = 512   # MB; suficiente y no satura la RAM
        mundo = ow.World()
        onto = mundo.get_ontology(config.ONTO_POBLADA.resolve().as_uri()).load()
        o = onto.get_namespace(config.NS)
        with onto:
            ow.sync_reasoner_hermit(mundo, infer_property_values=False, debug=0)
        nombres = ["MateriaLlave", "MateriaSeriada", "GrupoVespertino",
                   "GrupoMatutino", "GrupoEnLinea", "EstudianteConAdeudo"]
        res = {}
        for n in nombres:
            c = getattr(o, n, None)
            if c is not None:
                res[n] = sorted(getattr(i, "claveMateria", None) or getattr(i, "claveGrupo", None)
                                or getattr(i, "matricula", None) or i.name
                                for i in c.instances())
        mundo.close()
        return res
