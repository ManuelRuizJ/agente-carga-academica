# -*- coding: utf-8 -*-
"""
Datos semilla para poblar la ontología P2_ontologia_carga_academica.owx.

La ontología del Proyecto 2 solo tenía clases y propiedades (TBox), sin
individuos (ABox). Por eso, en el prototipo anterior, cualquier consulta a
"alumno_001" regresaba "no encontrado". Este archivo define los casos
concretos; `python main.py poblar` los convierte en individuos OWL.

Si quieres agregar materias, grupos o alumnos, edita SOLO este archivo y
vuelve a ejecutar `python main.py poblar`.
"""

PROGRAMA = {
    "id": "prog_ISC",
    "nombre": "Ingeniería en Sistemas Computacionales",
    "creditos_totales": 400,
}

# Restricción institucional de créditos por periodo
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

# clave: (nombre, créditos, semestre sugerido, horas/semana, dificultad 1-5,
#         obligatoria?, [prerrequisitos])
MATERIAS = {
    # --- 1er semestre
    "MAT101": ("Cálculo Diferencial", 8, 1, 4, 3, True, []),
    "PRG101": ("Fundamentos de Programación", 8, 1, 4, 2, True, []),
    "MAT102": ("Álgebra Lineal", 8, 1, 4, 3, True, []),
    "ISC101": ("Introducción a la Ingeniería", 6, 1, 3, 1, True, []),
    # --- 2do semestre
    "MAT201": ("Cálculo Integral", 8, 2, 4, 3, True, ["MAT101"]),
    "PRG201": ("Programación Orientada a Objetos", 8, 2, 4, 3, True, ["PRG101"]),
    "MAT202": ("Matemáticas Discretas", 8, 2, 4, 3, True, ["MAT102"]),
    "FIS201": ("Física I", 8, 2, 4, 3, True, ["MAT101"]),
    # --- 3er semestre
    "PRG301": ("Estructuras de Datos", 8, 3, 4, 4, True, ["PRG201", "MAT202"]),
    "BDD301": ("Bases de Datos", 8, 3, 4, 3, True, ["PRG201"]),
    "MAT301": ("Probabilidad y Estadística", 8, 3, 4, 3, True, ["MAT201"]),
    "ARQ301": ("Arquitectura de Computadoras", 8, 3, 4, 3, True, ["FIS201"]),
    # --- 4to semestre
    "PRG401": ("Análisis de Algoritmos", 8, 4, 4, 4, True, ["PRG301"]),
    "SOP401": ("Sistemas Operativos", 8, 4, 4, 4, True, ["ARQ301", "PRG301"]),
    "RED401": ("Redes de Computadoras", 8, 4, 4, 3, True, ["ARQ301"]),
    "ISW401": ("Ingeniería de Software", 8, 4, 4, 2, True, ["BDD301"]),
    # --- 5to semestre
    "IAR501": ("Inteligencia Artificial", 8, 5, 4, 4, True, ["PRG401", "MAT301"]),
    "WEB501": ("Desarrollo Web", 8, 5, 4, 2, True, ["BDD301"]),
    "CMP501": ("Compiladores", 8, 5, 4, 5, True, ["PRG401"]),
    "SEG501": ("Seguridad Informática", 8, 5, 4, 3, True, ["RED401"]),
    # --- 6to semestre
    "AGI601": ("Agentes Inteligentes", 8, 6, 4, 4, True, ["IAR501"]),
    "DSC601": ("Ciencia de Datos", 8, 6, 4, 3, True, ["MAT301", "BDD301"]),
    "SDI601": ("Sistemas Distribuidos", 8, 6, 4, 4, True, ["SOP401", "RED401"]),
    # --- Optativas
    "OPT01": ("Desarrollo de Videojuegos", 6, 5, 3, 2, False, ["PRG201"]),
    "OPT02": ("Computación en la Nube", 6, 6, 3, 2, False, ["RED401"]),
    "OPT03": ("Ética y Tecnología", 6, 3, 3, 1, False, []),
    "OPT04": ("Emprendimiento Tecnológico", 6, 4, 3, 1, False, []),
}

PROFESORES = {
    "prof_001": ("Dra. Elena Márquez", "E-1001"),
    "prof_002": ("Mtro. Ricardo Solís", "E-1002"),
    "prof_003": ("Dr. Paulo Vázquez", "E-1003"),
    "prof_004": ("Mtra. Laura Peña", "E-1004"),
    "prof_005": ("Dr. Andrés Cuevas", "E-1005"),
    "prof_006": ("Mtra. Gabriela Ortiz", "E-1006"),
    "prof_007": ("Ing. Tomás Rivera", "E-1007"),
}

# Patrones de horario: lista de (día, hora_inicio, hora_fin) — horas enteras 24h
H = {
    "LM7": [("Lunes", 7, 9), ("Miercoles", 7, 9)],
    "LM9": [("Lunes", 9, 11), ("Miercoles", 9, 11)],
    "LM11": [("Lunes", 11, 13), ("Miercoles", 11, 13)],
    "MJ7": [("Martes", 7, 9), ("Jueves", 7, 9)],
    "MJ9": [("Martes", 9, 11), ("Jueves", 9, 11)],
    "MJ11": [("Martes", 11, 13), ("Jueves", 11, 13)],
    "LM15": [("Lunes", 15, 17), ("Miercoles", 15, 17)],
    "LM17": [("Lunes", 17, 19), ("Miercoles", 17, 19)],
    "MJ15": [("Martes", 15, 17), ("Jueves", 15, 17)],
    "MJ17": [("Martes", 17, 19), ("Jueves", 17, 19)],
    "V9": [("Viernes", 9, 13)],
    "V15": [("Viernes", 15, 19)],
    "LV13": [("Lunes", 13, 15), ("Viernes", 13, 15)],
}

# Oferta del periodo actual:
# clave_grupo: (materia, profesor, modalidad, patrón de horario, cupo máx, cupo disponible)
GRUPOS = {
    "MAT201-A": ("MAT201", "prof_001", "presencial", "LM7", 35, 10),
    "MAT201-B": ("MAT201", "prof_001", "presencial", "MJ15", 35, 4),
    "FIS201-A": ("FIS201", "prof_005", "presencial", "MJ9", 30, 8),
    "FIS201-B": ("FIS201", "prof_005", "hibrida", "LM17", 30, 12),
    "MAT202-A": ("MAT202", "prof_001", "presencial", "LM11", 35, 6),
    "PRG301-A": ("PRG301", "prof_003", "presencial", "MJ7", 30, 5),
    "PRG301-B": ("PRG301", "prof_003", "en_linea", "LM15", 30, 9),
    "BDD301-A": ("BDD301", "prof_004", "presencial", "LM9", 30, 7),
    "BDD301-B": ("BDD301", "prof_004", "hibrida", "MJ17", 30, 15),
    "MAT301-A": ("MAT301", "prof_002", "presencial", "MJ11", 35, 11),
    "MAT301-B": ("MAT301", "prof_002", "en_linea", "LM17", 40, 20),
    "ARQ301-A": ("ARQ301", "prof_005", "presencial", "LM9", 30, 6),
    "PRG401-A": ("PRG401", "prof_003", "presencial", "LM11", 30, 3),
    "PRG401-B": ("PRG401", "prof_003", "hibrida", "MJ15", 30, 10),
    "SOP401-A": ("SOP401", "prof_007", "presencial", "MJ9", 30, 8),
    "SOP401-B": ("SOP401", "prof_007", "presencial", "LM15", 30, 2),
    "RED401-A": ("RED401", "prof_007", "presencial", "MJ11", 30, 9),
    "RED401-B": ("RED401", "prof_006", "en_linea", "MJ17", 35, 14),
    "ISW401-A": ("ISW401", "prof_004", "hibrida", "V9", 30, 12),
    "IAR501-A": ("IAR501", "prof_003", "presencial", "MJ9", 30, 6),
    "IAR501-B": ("IAR501", "prof_003", "presencial", "LM17", 30, 11),
    "WEB501-A": ("WEB501", "prof_006", "en_linea", "LM15", 35, 18),
    "WEB501-B": ("WEB501", "prof_006", "presencial", "MJ7", 30, 9),
    "CMP501-A": ("CMP501", "prof_002", "presencial", "MJ15", 25, 7),
    "SEG501-A": ("SEG501", "prof_007", "hibrida", "LM11", 30, 10),
    "SEG501-B": ("SEG501", "prof_006", "en_linea", "V15", 35, 16),
    "AGI601-A": ("AGI601", "prof_003", "presencial", "MJ17", 25, 8),
    "AGI601-B": ("AGI601", "prof_003", "en_linea", "V9", 25, 12),
    "DSC601-A": ("DSC601", "prof_002", "hibrida", "LM15", 30, 9),
    "SDI601-A": ("SDI601", "prof_005", "presencial", "LM9", 30, 7),
    "SDI601-B": ("SDI601", "prof_007", "en_linea", "MJ15", 30, 13),
    "OPT01-A": ("OPT01", "prof_006", "presencial", "LV13", 30, 6),
    "OPT02-A": ("OPT02", "prof_007", "en_linea", "V15", 40, 22),
    "OPT03-A": ("OPT03", "prof_004", "en_linea", "LV13", 40, 25),
    "OPT04-A": ("OPT04", "prof_004", "presencial", "MJ11", 35, 15),
}
# Nota: ISC101, MAT101, MAT102 y PRG101 no se ofertan este periodo (solo en Otoño).

# Estudiantes
# aprobadas: {clave: calificación}; reprobadas: {clave: calificación}
# preferencias guardadas (las que el alumno dejó registradas en el sistema)
ESTUDIANTES = {
    "A001": {
        "id": "est_A001",
        "nombre": "Ana Torres Medina",
        "semestre": 5,
        "aprobadas": {
            "MAT101": 9.1, "PRG101": 9.6, "MAT102": 8.4, "ISC101": 9.8,
            "MAT201": 8.0, "PRG201": 9.3, "MAT202": 8.7, "FIS201": 7.9,
            "PRG301": 8.9, "BDD301": 9.5, "MAT301": 8.2, "ARQ301": 8.1,
            "PRG401": 8.6, "ISW401": 9.4, "RED401": 8.3,
        },
        "reprobadas": {"SOP401": 5.4},
        "preferencias": {
            "turno": ("vespertino", 3, "Prefiero tomar clases en la tarde porque trabajo en las mañanas"),
            "modalidad": ("presencial", 2, "Me gustan más las clases presenciales"),
            "carga": ("normal", 1, "Una carga normal", 40, 5),
        },
    },
    "A002": {
        "id": "est_A002",
        "nombre": "Luis Hernández Rojas",
        "semestre": 3,
        "aprobadas": {
            "MAT101": 7.2, "PRG101": 8.8, "MAT102": 7.5, "ISC101": 9.0,
            "PRG201": 8.1, "MAT202": 7.0,
        },
        "reprobadas": {"MAT201": 5.0},
        "preferencias": {
            "turno": ("matutino", 2, "En la mañana"),
            "modalidad": ("presencial", 1, "Presencial"),
            "carga": ("ligera", 3, "No quiero saturarme este semestre", 32, 4),
        },
    },
    "A003": {
        "id": "est_A003",
        "nombre": "Sofía Ramírez Lara",
        "semestre": 6,
        "aprobadas": {
            "MAT101": 9.9, "PRG101": 10.0, "MAT102": 9.7, "ISC101": 9.5,
            "MAT201": 9.4, "PRG201": 9.8, "MAT202": 9.6, "FIS201": 9.0,
            "PRG301": 9.7, "BDD301": 9.9, "MAT301": 9.3, "ARQ301": 9.1,
            "PRG401": 9.5, "SOP401": 9.0, "RED401": 9.2, "ISW401": 9.8,
            "WEB501": 10.0, "OPT03": 9.6,
        },
        "reprobadas": {},
        "preferencias": {
            "turno": ("vespertino", 1, "Indistinto, de preferencia en la tarde"),
            "modalidad": ("en_linea", 3, "Prefiero en línea porque vivo lejos"),
            "carga": ("pesada", 2, "Quiero adelantar materias", 48, 6),
        },
    },
}

# Agentes del MAS (también se modelan en la ontología: clase Agente)
AGENTES = {
    "AgenteHistorial": ("agente_historial", "AgenteHistorial", "Analista de historial académico y requisitos"),
    "AgenteCarga": ("agente_carga", "AgenteCarga", "Analista de carga académica"),
    "AgenteHorarios": ("agente_horarios", "AgenteHorarios", "Analista de horarios y preferencias del estudiante"),
    "AgenteManager": ("agente_manager", "AgenteManager", "Coordinador y recomendador académico"),
}
