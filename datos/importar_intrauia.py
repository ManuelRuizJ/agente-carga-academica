# -*- coding: utf-8 -*-
"""
Importa el plan de estudios REAL desde la exportación del portal Intrauia.

Entrada:  datos/intrauia/plan_isc.txt
          (tabla copiada de Intrauia → "Plan de estudios" de Ingeniería en
          Sistemas Computacionales; la carpeta datos/intrauia/ NO se versiona
          porque la exportación completa trae datos de la sesión del alumno)
Salida:   datos/plan_ibero.json   (catálogo limpio, sí se versiona)

Lo que viene del portal es REAL: clave, sigla, nombre, seriación, semestre
ideal, horas, créditos, área y coordinación. Lo que el portal no tiene se
DERIVA y queda marcado en el JSON:
  * obligatoria  ← por área (Área Menor y las optativas de Reflexión
                   Universitaria son optativas)
  * horas_semana ← horas con docente / 16 semanas
  * dificultad   ← heurística (ver `_dificultad`), es SINTÉTICA

Uso:  python datos/importar_intrauia.py [ruta_txt]
"""
import json
import sys
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ENTRADA = AQUI / "intrauia" / "plan_isc.txt"
SALIDA = AQUI / "plan_ibero.json"

COLUMNAS = ["Clave", "Materia", "Sigla", "Clave de seriación", "Sigla de seriación",
            "Semestre ideal", "Horas con docente", "Horas independiente", "Horas totales",
            "Créditos", "Área", "Coordinación responsable"]

# Reflexión Universitaria: "Persona y Humanismo" es la base obligatoria y
# "Dilemas Éticos en la Ingeniería" es la específica de ingeniería; las demás
# son el menú de optativas de reflexión.
REFLEXION_OBLIGATORIAS = {"LYRU2101", "LYRU2118"}
COORD_TECNICAS = {"CIENCIAS BÁSICAS", "INGENIERÍA EN SISTEMAS", "INGENIERÍA ELECTRÓNICA",
                  "INGENIERÍA MECÁNICA"}


def leer_txt(ruta: Path) -> list[dict]:
    """La tabla pegada de Intrauia trae cada materia en 3 líneas:
    'clave<TAB>' / 'nombre' / 'sigla<TAB>seriación…'."""
    lineas = [l.rstrip("\n") for l in ruta.read_text(encoding="utf-8").splitlines()]
    encabezado = [c.strip() for c in lineas[0].split("\t")]
    if encabezado != COLUMNAS:
        sys.exit(f"Encabezado inesperado en {ruta}:\n  {encabezado}")
    filas, i = [], 1
    while i < len(lineas):
        if not lineas[i].strip():
            i += 1
            continue
        clave = lineas[i].split("\t")[0].strip()
        nombre = lineas[i + 1].strip()
        resto = [c.strip() for c in lineas[i + 2].split("\t")]
        if len(resto) != 10 or not clave.isdigit():
            sys.exit(f"Fila mal formada cerca de la línea {i + 1}: {clave!r} {nombre!r} {resto}")
        sigla, cl_ser, sig_ser, sem, hdoc, hind, htot, cred, area, coord = resto
        filas.append({
            "clave": clave, "sigla": sigla, "nombre": nombre,
            "clave_seriacion": cl_ser or None, "sigla_seriacion": sig_ser or None,
            "semestre": int(sem), "horas_docente": int(hdoc), "horas_independiente": int(hind),
            "horas_totales": int(htot), "creditos": int(cred), "area": area,
            "coordinacion": coord,
        })
        i += 3
    return filas


def _obligatoria(f: dict) -> bool:
    if f["area"].startswith("Area Menor"):
        return False
    if f["area"].startswith("Area de Reflexión"):
        return f["sigla"] in REFLEXION_OBLIGATORIAS
    return True


def _dificultad(f: dict) -> int:
    """SINTÉTICA (1–5): el portal no da dificultad. Sube con el semestre, con
    8 créditos y si es de una coordinación técnica; reflexión/servicio = 1."""
    if f["area"].startswith(("Area de Reflexión", "Area de Servicio")):
        return 1
    d = 1 + (f["semestre"] >= 3) + (f["semestre"] >= 6) + (f["creditos"] >= 8) \
        + (f["coordinacion"] in COORD_TECNICAS)
    if f["nombre"].startswith("Laboratorio"):
        d = min(d, 2)
    return max(1, min(5, d))


def validar(filas: list[dict]) -> list[str]:
    errores = []
    siglas = [f["sigla"] for f in filas]
    claves = [f["clave"] for f in filas]
    for nombre, lista in (("sigla", siglas), ("clave", claves)):
        dup = {x for x in lista if lista.count(x) > 1}
        if dup:
            errores.append(f"{nombre} duplicada: {sorted(dup)}")
    por_sigla = {f["sigla"]: f for f in filas}
    por_clave = {f["clave"]: f for f in filas}
    for f in filas:
        if f["horas_totales"] != f["horas_docente"] + f["horas_independiente"]:
            errores.append(f"{f['sigla']}: horas totales no cuadran")
        s = f["sigla_seriacion"]
        if not s:
            continue
        if s not in por_sigla:
            errores.append(f"{f['sigla']}: su seriación {s} no está en el plan")
            continue
        if por_clave.get(f["clave_seriacion"]) is not por_sigla[s]:
            errores.append(f"{f['sigla']}: clave {f['clave_seriacion']} y sigla {s} no coinciden")
        if por_sigla[s]["semestre"] >= f["semestre"]:
            errores.append(f"{f['sigla']} (sem {f['semestre']}) seriada con {s} "
                           f"(sem {por_sigla[s]['semestre']}), que no es anterior")
    # ciclos (una materia tiene a lo más una seriación, basta seguir la cadena)
    for f in filas:
        vistos, s = set(), f["sigla"]
        while s:
            if s in vistos:
                errores.append(f"ciclo de seriación que pasa por {s}")
                break
            vistos.add(s)
            s = por_sigla[s]["sigla_seriacion"] if s in por_sigla else None
    return errores


def importar(ruta: Path = ENTRADA, salida: Path = SALIDA) -> dict:
    filas = leer_txt(ruta)
    errores = validar(filas)
    if errores:
        sys.exit("✘ Validación fallida:\n  " + "\n  ".join(errores))
    materias = []
    for f in filas:
        materias.append({
            **f,
            "prerrequisitos": [f["sigla_seriacion"]] if f["sigla_seriacion"] else [],
            "obligatoria": _obligatoria(f),
            "horas_semana": f["horas_docente"] // 16,
            "dificultad": _dificultad(f),
        })
    oblig = [m for m in materias if m["obligatoria"]]
    plan = {
        "_fuente": "Intrauia (Ibero Puebla) → Plan de estudios, exportado por el alumno",
        "_consultado": date.today().isoformat(),
        "_derivados": {
            "obligatoria": "por área: Área Menor y Reflexión Universitaria (salvo LYRU2101 "
                           "y LYRU2118) se marcan optativas",
            "horas_semana": "horas con docente / 16 semanas",
            "dificultad": "SINTÉTICA: heurística por semestre, créditos y coordinación",
        },
        "programa": {"clave": "2801", "nombre": "Ingeniería en Sistemas Computacionales",
                     "institucion": "Universidad Iberoamericana Puebla"},
        "creditos_obligatorios": sum(m["creditos"] for m in oblig),
        "materias": materias,
    }
    salida.write_text(json.dumps(plan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return plan


if __name__ == "__main__":
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else ENTRADA
    plan = importar(ruta)
    ms = plan["materias"]
    print(f"✔ {len(ms)} materias importadas → {SALIDA.relative_to(AQUI.parent)}")
    print(f"  obligatorias: {sum(m['obligatoria'] for m in ms)} "
          f"({plan['creditos_obligatorios']} créditos) | optativas: "
          f"{sum(not m['obligatoria'] for m in ms)} | seriadas: "
          f"{sum(bool(m['prerrequisitos']) for m in ms)}")
