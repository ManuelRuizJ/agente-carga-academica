# -*- coding: utf-8 -*-
"""
Datos semilla para poblar la ontología P2_ontologia_carga_academica.owx.

La ontología del Proyecto 2 solo tenía clases y propiedades (TBox), sin
individuos (ABox). Este archivo define los casos concretos y
`python main.py poblar` los convierte en individuos OWL.

QUÉ ES REAL Y QUÉ ES SINTÉTICO
  * REAL — el plan de estudios de Ingeniería en Sistemas Computacionales de la
    Ibero Puebla (79 materias: sigla, nombre, créditos, semestre ideal, horas y
    seriación), exportado del portal Intrauia y limpiado por
    `datos/importar_intrauia.py` → `datos/plan_ibero.json`.
  * SINTÉTICO — la dificultad de cada materia (heurística), la oferta del
    periodo (grupos, horarios, cupos, modalidades), los profesores y los
    alumnos. La oferta se GENERA de forma determinista a partir del plan real.

Para cambiar materias: vuelve a exportar de Intrauia y corre
`python datos/importar_intrauia.py`. Para cambiar alumnos u oferta: edita este
archivo. En ambos casos, después: `python main.py poblar`.
"""
import json
import random
from pathlib import Path

_PLAN = json.loads((Path(__file__).resolve().parent / "plan_ibero.json").read_text(encoding="utf-8"))

PROGRAMA = {
    "id": "prog_ISC",
    "nombre": "Ingeniería en Sistemas Computacionales (Ibero Puebla, programa 2801)",
    # Solo obligatorias: el portal no dice cuántas optativas exige el plan
    "creditos_totales": _PLAN["creditos_obligatorios"],
}

# Restricción institucional de créditos por periodo (SUPUESTO: no viene de
# Intrauia). El plan ideal carga entre 32 y 42 créditos por semestre.
RESTRICCION_CREDITOS = {
    "id": "restr_creditos_ISC",
    "descripcion": "Un alumno regular debe inscribir entre 24 y 48 créditos por periodo.",
    "minimos": 24,
    "maximos": 48,
}

PERIODO_ACTUAL = {
    "id": "per_P2027",
    "nombre": "Primavera 2027",
    "inicio": "2027-01-11T00:00:00",
    "fin": "2027-05-14T00:00:00",
}

PERIODOS_PASADOS = {
    1: ("per_O2024", "Otoño 2024", "2024-08-12T00:00:00", "2024-12-06T00:00:00"),
    2: ("per_P2025", "Primavera 2025", "2025-01-13T00:00:00", "2025-05-16T00:00:00"),
    3: ("per_O2025", "Otoño 2025", "2025-08-11T00:00:00", "2025-12-05T00:00:00"),
    4: ("per_P2026", "Primavera 2026", "2026-01-12T00:00:00", "2026-05-15T00:00:00"),
    5: ("per_O2026", "Otoño 2026", "2026-08-10T00:00:00", "2026-12-04T00:00:00"),
}

MODALIDADES = {
    "presencial": ("mod_presencial", "ModalidadPresencial", "Presencial"),
    "en_linea": ("mod_en_linea", "ModalidadEnLinea", "En línea"),
    "hibrida": ("mod_hibrida", "ModalidadHibrida", "Híbrida"),
}

# clave (sigla de Intrauia): (nombre, créditos, semestre ideal, horas/semana,
#                             dificultad 1-5, obligatoria?, [prerrequisitos])
MATERIAS = {
    m["sigla"]: (m["nombre"], m["creditos"], m["semestre"], m["horas_semana"],
                 m["dificultad"], m["obligatoria"], m["prerrequisitos"])
    for m in _PLAN["materias"]
}

# --------------------------------------------------------------- profesores
# Ficticios: no se publican nombres reales de profesores.
PROFESORES = {
    "prof_001": ("Dra. Elena Márquez", "E-1001"),
    "prof_002": ("Mtro. Ricardo Solís", "E-1002"),
    "prof_003": ("Dr. Paulo Vázquez", "E-1003"),
    "prof_004": ("Mtra. Laura Peña", "E-1004"),
    "prof_005": ("Dr. Andrés Cuevas", "E-1005"),
    "prof_006": ("Mtra. Gabriela Ortiz", "E-1006"),
    "prof_007": ("Ing. Tomás Rivera", "E-1007"),
    "prof_008": ("Dra. Mariana Lozano", "E-1008"),
    "prof_009": ("Mtro. Héctor Aguilar", "E-1009"),
    "prof_010": ("Dra. Rocío Benítez", "E-1010"),
    "prof_011": ("Mtro. Daniel Fuentes", "E-1011"),
    "prof_012": ("Mtra. Isabel Carmona", "E-1012"),
}

# --------------------------------------------------------------- horarios
# Patrones de horario: nombre -> [(día, hora_inicio, hora_fin)], horas enteras 24 h.
# Se generan según las horas con docente por semana (2, 4 o 6).
_INICIOS = [7, 9, 11, 13, 15, 17, 19]
H = {}
for _h in _INICIOS:
    for _d in ("Lunes", "Martes", "Miercoles", "Jueves", "Viernes"):
        H[f"{_d[:2]}{_h}"] = [(_d, _h, _h + 2)]                                   # 2 h
    H[f"LuMi{_h}"] = [("Lunes", _h, _h + 2), ("Miercoles", _h, _h + 2)]           # 4 h
    H[f"MaJu{_h}"] = [("Martes", _h, _h + 2), ("Jueves", _h, _h + 2)]
    H[f"LuMiVi{_h}"] = [("Lunes", _h, _h + 2), ("Miercoles", _h, _h + 2),
                        ("Viernes", _h, _h + 2)]                                 # 6 h
for _h in (7, 10, 13, 16, 19):
    H[f"MaJu{_h}x3"] = [("Martes", _h, _h + 3), ("Jueves", _h, _h + 3)]
for _h in (9, 15):
    H[f"Vi{_h}x4"] = [("Viernes", _h, _h + 4)]

_PATRONES_POR_HORAS = {
    2: [k for k, v in H.items() if len(v) == 1 and v[0][2] - v[0][1] == 2],
    4: [k for k in H if k.startswith(("LuMi", "MaJu")) and len(H[k]) == 2
        and not k.endswith("x3")] + ["Vi9x4", "Vi15x4"],
    6: [k for k in H if k.startswith("LuMiVi") or k.endswith("x3")],
}


# --------------------------------------------------------------- oferta
# Optativas que SÍ se abren en Primavera 2027 (las demás: "no se oferta").
OPTATIVAS_OFERTADAS = {
    "LYRU2105", "LYRU2111", "LYRU2113", "LYRU2104", "LYRU2110",   # Reflexión Universitaria
    "LIIS2122", "LIIS2123", "LIIS2125", "LIIS2124", "LIIN2110",   # Área Menor
}


def _generar_grupos(semilla=2027):
    """Oferta SINTÉTICA, pero reproducible (misma semilla → mismos grupos).

    * Las materias de 1.er semestre solo se abren en Otoño (no hay grupos).
    * Obligatorias de semestre par o del Área Mayor: 2 grupos; el resto: 1.
    * Optativas: solo las de OPTATIVAS_OFERTADAS, 1 grupo.
    * Un grupo matutino y otro vespertino cuando hay 2, para que haya choques
      que resolver y preferencias de turno que respetar.
    * Un profesor nunca tiene dos grupos a la misma hora.
    """
    rng = random.Random(semilla)
    profes = list(PROFESORES)
    ocupado = {p: [] for p in profes}
    grupos = {}

    def libre(p, bloques):
        return not any(d1 == d2 and i1 < f2 and i2 < f1
                       for d1, i1, f1 in ocupado[p] for d2, i2, f2 in bloques)

    for m in _PLAN["materias"]:
        clave, sem, oblig = m["sigla"], m["semestre"], m["obligatoria"]
        if sem == 1:
            continue
        if not oblig and clave not in OPTATIVAS_OFERTADAS:
            continue
        n = 2 if oblig and (sem % 2 == 0 or m["area"].startswith("Area Mayor")) else 1
        patrones = _PATRONES_POR_HORAS[m["horas_semana"]]
        turnos = rng.sample(["matutino", "vespertino"], 2)[:n]
        for i, turno in enumerate(turnos):
            opciones = [p for p in patrones
                        if (H[p][0][1] < 13) == (turno == "matutino")]
            rng.shuffle(opciones)
            prof = None
            for patron in opciones:
                candidatos = [p for p in profes if libre(p, H[patron])]
                if candidatos:
                    prof = rng.choice(candidatos)
                    break
            if prof is None:
                raise RuntimeError(f"No hay profesor libre para {clave}: agrega profesores")
            ocupado[prof].extend(H[patron])
            modalidad = rng.choices(["presencial", "hibrida", "en_linea"], [0.55, 0.2, 0.25])[0]
            cupo_max = rng.choice([25, 30, 35, 40])
            cupo_disp = rng.randint(2, min(20, cupo_max))
            grupos[f"{clave}-{'AB'[i]}"] = (clave, prof, modalidad, patron, cupo_max, cupo_disp)
    return grupos


# Oferta del periodo actual:
# clave_grupo: (materia, profesor, modalidad, patrón de horario, cupo máx, cupo disponible)
GRUPOS = _generar_grupos()


# --------------------------------------------------------------- estudiantes
def _kardex(hasta_semestre, excepto=(), extra=(), media=8.5, semilla=0):
    """Aprobadas SINTÉTICAS: todas las obligatorias hasta `hasta_semestre`
    (menos `excepto`) más las optativas de `extra`, con calificaciones
    alrededor de `media`. Respeta la seriación real del plan."""
    rng = random.Random(semilla)
    claves = [c for c, (_, _, sem, _, _, oblig, _) in MATERIAS.items()
              if oblig and sem <= hasta_semestre and c not in excepto] + list(extra)
    aprobadas = {c: round(min(10.0, max(7.0, rng.gauss(media, 0.6))), 1) for c in claves}
    for c in aprobadas:   # verificación: nadie aprueba algo sin su prerrequisito
        faltan = [p for p in MATERIAS[c][6] if p not in aprobadas]
        assert not faltan, f"kárdex incoherente: {c} sin {faltan}"
    return aprobadas


# aprobadas: {clave: calificación}; reprobadas: {clave: calificación}
# preferencias guardadas (las que el alumno dejó registradas en el sistema)
ESTUDIANTES = {
    # Trabaja en las mañanas; reprobó una materia LLAVE (Programación Avanzada
    # y Algoritmos desbloquea 4 materias), por eso también trae pendiente
    # Paradigmas de Programación Avanzados.
    "A001": {
        "id": "est_A001",
        "nombre": "Ana Torres Medina",
        "semestre": 5,
        "aprobadas": _kardex(4, excepto={"LIIS2105", "LIIS2110"},
                             extra={"LYRU2105"}, media=8.7, semilla=1),
        "reprobadas": {"LIIS2105": 5.4},
        "preferencias": {
            "turno": ("vespertino", 3, "Prefiero tomar clases en la tarde porque trabajo en las mañanas"),
            "modalidad": ("presencial", 2, "Me gustan más las clases presenciales"),
            "carga": ("normal", 1, "Una carga normal", 40, 7),
        },
    },
    # Reprobó Cálculo Diferencial e Integral; quiere carga ligera.
    "A002": {
        "id": "est_A002",
        "nombre": "Luis Hernández Rojas",
        "semestre": 3,
        "aprobadas": _kardex(2, excepto={"LICB2103"}, media=7.9, semilla=2),
        "reprobadas": {"LICB2103": 5.0},
        "preferencias": {
            "turno": ("matutino", 2, "En la mañana"),
            "modalidad": ("presencial", 1, "Presencial"),
            "carga": ("ligera", 3, "No quiero saturarme este semestre", 30, 5),
        },
    },
    # Alumna regular y sobresaliente; vive lejos y quiere adelantar.
    "A003": {
        "id": "est_A003",
        "nombre": "Sofía Ramírez Lara",
        "semestre": 6,
        "aprobadas": _kardex(5, extra={"LYRU2102", "LYRU2108"}, media=9.5, semilla=3),
        "reprobadas": {},
        "preferencias": {
            "turno": ("vespertino", 1, "Indistinto, de preferencia en la tarde"),
            "modalidad": ("en_linea", 3, "Prefiero en línea porque vivo lejos"),
            "carga": ("pesada", 2, "Quiero adelantar materias", 48, 8),
        },
    },
}

# Agentes del MAS (también se modelan en la ontología: clase Agente)
AGENTES = {
    "AgenteHistorial": ("agente_historial", "AgenteHistorial", "Analista de historial académico y requisitos"),
    "AgenteCarga": ("agente_carga", "AgenteCarga", "Analista de carga académica (equipo de contratistas)"),
    # Mejora 1: los 3 contratistas que compiten en el Contract Net (clase AgenteCarga)
    "CargaAvance": ("agente_carga_avance", "AgenteCarga", "Contratista: prioriza el avance académico"),
    "CargaEquilibrio": ("agente_carga_equilibrio", "AgenteCarga", "Contratista: prioriza una carga equilibrada"),
    "CargaPreferencias": ("agente_carga_preferencias", "AgenteCarga", "Contratista: prioriza intereses y horario"),
    "AgenteHorarios": ("agente_horarios", "AgenteHorarios", "Analista de horarios y preferencias del estudiante"),
    "AgenteManager": ("agente_manager", "AgenteManager", "Coordinador y recomendador académico"),
}
