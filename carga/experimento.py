# -*- coding: utf-8 -*-
"""
Mejora 2: experimento comparativo.

¿Sirve de algo el MAS? Se generan N alumnos sintéticos (en memoria, NO se
agregan a la ontología) sobre el plan real, y a cada uno se le arma una carga
con varios sistemas. Todos se califican con la MISMA función oficial del
Proyecto 2 y se revisan con las MISMAS reglas duras:

  * materias inválidas  (ya aprobadas, sin prerrequisito o no ofertadas)
  * choques de horario
  * créditos fuera del rango institucional (24–48)
  * más optativas de las permitidas
  * clases en un día que el alumno pidió libre

Sistemas:
  1. MAS completo (Historial + 3 AgentesCarga en competencia + Horarios)
  2. MAS con un solo AgenteCarga (como estaba antes de la mejora 1)
  3-5. MAS con un solo contratista (Avance, Equilibrio o Preferencias)
  6. Monoagente simple: solo revisa requisitos y toma las primeras materias
     del plan (es la coalición {Historial} del Shapley)
  7. LLM solo (llama3.2): recibe el plan, el kárdex y la petición, y elige
     las materias él solo. Opcional (--llm), lento en CPU.

Uso:  python main.py experimento            (20 alumnos, sin LLM, segundos)
      python main.py experimento --llm      (agrega el LLM solo; ~1 min por alumno)
"""
import csv
import json
import random
import time
from statistics import mean

from . import config
from .agentes import AgenteCarga, AgenteHorarios
from .contract_net import ejecutar
from .evaluacion import Propuesta, analizar_elegibilidad, conflictos, evaluar_propuesta
from .kb import Estudiante
from .preferencias import construir_preferencias

HIST, HOR = "AgenteHistorial", "AgenteHorarios"

# Frases para las peticiones en lenguaje natural (se combinan al azar)
FRASES = ["sin clases el viernes", "no quiero clases los lunes", "prefiero la tarde",
          "en la mañana", "quiero algo ligero", "quiero adelantar materias",
          "me interesa inteligencia artificial", "me interesa la nube",
          "me interesan las bases de datos", "no quiero métodos numéricos",
          "me gustaría en línea", "nada de embebidos"]


# =========================================================== alumnos sintéticos
def _dependientes(materias, clave):
    """Todas las materias que dependen (directa o indirectamente) de `clave`."""
    hijos = {c for c, m in materias.items() if clave in m[6]}
    for h in list(hijos):
        hijos |= _dependientes(materias, h)
    return hijos


def generar_alumnos(n=20, semilla=7):
    """Alumnos coherentes con la seriación real: aprueban las obligatorias de los
    semestres anteriores, a veces reprueban una o dos (y entonces tampoco pudieron
    cursar lo que depende de ellas), y tienen preferencias y petición al azar."""
    from datos import semilla as S
    rng = random.Random(semilla)
    optativas_ru = [c for c in S.MATERIAS if c.startswith("LYRU") and not S.MATERIAS[c][5]]
    alumnos = []
    for i in range(1, n + 1):
        semestre = rng.randint(2, 8)
        cursadas = [c for c, m in S.MATERIAS.items() if m[5] and m[2] <= semestre - 1]
        if semestre >= 5:                       # ya llevó alguna optativa de Reflexión
            cursadas += rng.sample(optativas_ru, rng.randint(0, 2))
        reprobadas = {}
        n_rep = rng.choices([0, 1, 2], [0.45, 0.4, 0.15])[0]
        recientes = [c for c in cursadas if S.MATERIAS[c][2] >= semestre - 2 and S.MATERIAS[c][5]]
        for c in rng.sample(recientes, min(n_rep, len(recientes))):
            reprobadas[c] = round(rng.uniform(4.5, 5.9), 1)
        quitar = set(reprobadas)
        for c in reprobadas:
            quitar |= _dependientes(S.MATERIAS, c)
        media = rng.uniform(7.6, 9.4)
        aprobadas = {c: round(min(10, max(6, rng.gauss(media, 0.6))), 1)
                     for c in cursadas if c not in quitar}
        for c in aprobadas:                     # coherencia con la seriación
            assert all(p in aprobadas for p in S.MATERIAS[c][6]), c
        tipo = rng.choice(list(config.CARGA_TIPO))
        meta = config.CARGA_TIPO[tipo]
        prefs = {
            "turno": (rng.choice(["matutino", "vespertino"]), rng.randint(1, 3)),
            "modalidad": (rng.choice(["presencial", "hibrida", "en_linea"]), rng.randint(1, 3)),
            "carga": (tipo, rng.randint(1, 3), meta["creditos"], meta["max_materias"]),
        }
        peticion = ", ".join(rng.sample(FRASES, rng.choice([0, 0, 1, 2, 2, 3])))
        cal = list(aprobadas.values())
        est = Estudiante(
            matricula=f"E{i:02d}", iri=f"est_E{i:02d}", nombre=f"Alumno sintético {i:02d}",
            semestre=semestre, promedio=round(mean(cal), 2) if cal else 0.0,
            creditos_acumulados=sum(S.MATERIAS[c][1] for c in aprobadas),
            aprobadas=aprobadas, reprobadas=reprobadas, preferencias=prefs)
        alumnos.append((est, peticion))
    return alumnos


# =========================================================== LLM solo
ESQUEMA_LLM = {"type": "object",
               "properties": {"materias": {"type": "array", "items": {"type": "string"}}},
               "required": ["materias"]}


def _prompt_llm(kb, est, prefs, peticion):
    """Lo que tendría un alumno que le pega su plan y su kárdex a un chatbot."""
    lineas = []
    for c, m in sorted(kb.materias.items(), key=lambda x: (x[1].semestre, x[0])):
        req = f", requiere {', '.join(m.prerrequisitos)}" if m.prerrequisitos else ""
        oferta = "" if c in kb.ofertadas else ", NO se oferta"
        tipo = "" if m.obligatoria else ", optativa"
        lineas.append(f"{c} {m.nombre} ({m.creditos} cr, sem {m.semestre}{tipo}{req}{oferta})")
    sistema = (
        "Eres un asesor académico. Elige las materias que el alumno debe inscribir el "
        "próximo periodo. Reglas: no repitas materias aprobadas; solo materias cuyos "
        "prerrequisitos estén aprobados; solo materias que se ofertan; entre "
        f"{kb.creditos_min} y {kb.creditos_max} créditos; máximo {config.MAX_OPTATIVAS} "
        "optativas. Prioriza las reprobadas. Responde SOLO un JSON con la lista de siglas.")
    usuario = (
        f"Plan de estudios (sigla, nombre, créditos, semestre ideal):\n" + "\n".join(lineas) +
        f"\n\nAlumno en {est.semestre}.º semestre.\nAprobadas: {', '.join(sorted(est.aprobadas))}\n"
        f"Reprobadas: {', '.join(est.reprobadas) or 'ninguna'}\n"
        f"Quiere unos {prefs['creditos_objetivo']} créditos y máximo {prefs['max_materias']} materias. "
        f"Petición: \"{peticion or 'ninguna'}\"")
    return sistema, usuario


def llm_solo(kb, est, prefs, peticion, llm):
    """El LLM elige las materias; como no conoce los grupos, se toma el primer
    grupo de cada materia (igual que el AgenteHorarios ingenuo)."""
    sistema, usuario = _prompt_llm(kb, est, prefs, peticion)
    # 400 tokens alcanzan para ~40 siglas: con 150, a veces el JSON quedaba cortado
    crudo = llm.chat(sistema, usuario, esquema=ESQUEMA_LLM, max_tokens=400, temperatura=0)
    try:
        elegidas = json.loads(crudo or "{}").get("materias", [])
    except json.JSONDecodeError:
        elegidas = []
    # solo se limpian siglas que no existen en el plan (texto inventado)
    materias = list(dict.fromkeys(c.strip().upper() for c in elegidas
                                  if isinstance(c, str) and c.strip().upper() in kb.materias))
    if not materias:
        return None
    combo, grupos = AgenteHorarios.ingenuo(kb, [materias], prefs, {})[0]
    return Propuesta("LLM", combo, grupos, autor="LLM")


# =========================================================== sistemas a comparar
def _mas(activos, estrategias=None, k=None):
    def correr(kb, est, prefs, peticion, elegibles, llm):
        return ejecutar(kb, est, prefs, elegibles, activos, estrategias=estrategias,
                        k_ofertas=k).ganadora
    return correr


SISTEMAS = {
    "MAS (3 contratistas)": _mas((HIST, "AgenteCarga", HOR)),
    "MAS (1 AgenteCarga, antes de la mejora 1)": _mas(
        (HIST, "AgenteCarga", HOR), {"AgenteCarga": AgenteCarga.PESOS_ORIGINALES},
        config.TOP_COMBINACIONES),
    "Solo CargaAvance": _mas((HIST, "CargaAvance", HOR)),
    "Solo CargaEquilibrio": _mas((HIST, "CargaEquilibrio", HOR)),
    "Solo CargaPreferencias": _mas((HIST, "CargaPreferencias", HOR)),
    "Monoagente simple (solo requisitos)": _mas((HIST,)),
}


# =========================================================== revisión
def revisar(kb, est, prefs, prop, elegibles):
    """Reglas duras sobre una carga. La calificación es la oficial del Manager."""
    if prop is None or not prop.materias:
        return {"propuesta": False, "puntuacion": 0.0, "invalidas": 0, "choques": 0,
                "fuera_rango": True, "exceso_optativas": False, "dia_libre_violado": False,
                "creditos": 0, "materias": ""}
    p = Propuesta("rev", list(prop.materias), dict(prop.grupos))
    evaluar_propuesta(kb, est, p, prefs, elegibles)
    cr = p.creditos(kb)
    dias = {b.dia for g in p.grupos.values() if g for b in kb.grupos[g].bloques}
    return {
        "propuesta": True,
        "puntuacion": p.puntuacion,
        "invalidas": sum(c not in elegibles for c in p.materias),
        "choques": len(conflictos(kb, p.grupos)),
        "fuera_rango": not kb.creditos_min <= cr <= kb.creditos_max,
        "exceso_optativas": sum(not kb.materias[c].obligatoria for c in p.materias) > config.MAX_OPTATIVAS,
        "dia_libre_violado": bool(set(prefs["dias_libres"]) & dias),
        "creditos": cr,
        "materias": " ".join(p.materias),
    }


def correr(kb, n=20, semilla=7, llm=None, eco=True):
    """Regresa (filas por alumno y sistema, resumen por sistema)."""
    sistemas = dict(SISTEMAS)
    if llm is not None and llm.disponible:
        sistemas["LLM solo (" + llm.modelo + ")"] = (
            lambda kb, est, prefs, peticion, elegibles, llm: llm_solo(kb, est, prefs, peticion, llm))
    filas = []
    for est, peticion in generar_alumnos(n, semilla):
        # las preferencias se interpretan igual para todos (reglas, sin LLM)
        prefs = construir_preferencias(est, kb.materias, peticion, llm=None)
        elegibles, _ = analizar_elegibilidad(kb, est)
        for nombre, sistema in sistemas.items():
            t0 = time.perf_counter()
            prop = sistema(kb, est, prefs, peticion, elegibles, llm)
            seg = time.perf_counter() - t0
            r = revisar(kb, est, prefs, prop, elegibles)
            filas.append({"alumno": est.matricula, "semestre": est.semestre,
                          "reprobadas": len(est.reprobadas), "peticion": peticion,
                          "sistema": nombre, "segundos": round(seg, 3), **r})
        if eco:
            mas = next(f for f in filas if f["alumno"] == est.matricula)
            print(f"  {est.matricula} sem {est.semestre} rep {len(est.reprobadas)} "
                  f"válidas {len(elegibles):2} → MAS {mas['puntuacion']}"
                  f"  petición: {peticion or '-'}")
    return filas, resumir(filas, sistemas)


def _pide_dia_libre(peticion):
    return "sin clases" in peticion or "no quiero clases" in peticion


def resumir(filas, sistemas):
    resumen = []
    alumnos = sorted({f["alumno"] for f in filas})
    mejor = {a: max(f["puntuacion"] for f in filas if f["alumno"] == a) for a in alumnos}
    referencia = next(iter(sistemas))           # el MAS completo
    del_mas = {f["alumno"]: f["puntuacion"] for f in filas if f["sistema"] == referencia}
    for nombre in sistemas:
        fs = [f for f in filas if f["sistema"] == nombre]
        con_dia = [f for f in fs if _pide_dia_libre(f["peticion"])]
        dif = [f["puntuacion"] - del_mas[f["alumno"]] for f in fs]
        resumen.append({
            "sistema": nombre,
            "puntuacion_media": round(mean(f["puntuacion"] for f in fs), 2),
            "puntuacion_min": round(min(f["puntuacion"] for f in fs), 2),
            "veces_mejor": sum(f["puntuacion"] >= mejor[f["alumno"]] - 1e-9 for f in fs),
            "pct_invalidas": round(100 * mean(f["invalidas"] > 0 for f in fs), 1),
            "pct_choques": round(100 * mean(f["choques"] > 0 for f in fs), 1),
            "pct_fuera_rango": round(100 * mean(f["fuera_rango"] for f in fs), 1),
            "pct_exceso_optativas": round(100 * mean(f["exceso_optativas"] for f in fs), 1),
            "dia_libre_violado": sum(f["dia_libre_violado"] for f in con_dia),
            "piden_dia_libre": len(con_dia),
            "vs_mas": (sum(d > 0.005 for d in dif), sum(abs(d) <= 0.005 for d in dif),
                       sum(d < -0.005 for d in dif)),
            "dif_media_vs_mas": round(mean(dif), 2),
            "segundos_media": round(mean(f["segundos"] for f in fs), 3),
            "n": len(fs),
        })
    return resumen


def tabla_markdown(resumen, n, semilla):
    L = [f"Experimento con {n} alumnos sintéticos (semilla {semilla}), plan real de la Ibero.",
         "Todas las cargas se califican con la función oficial del Proyecto 2.", "",
         "| Sistema | Puntuación media | Mínima | Veces la mejor | Con materias inválidas | "
         "Con choques | Fuera de 24–48 cr | > 2 optativas | Día libre no respetado | Tiempo medio (s) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in resumen:
        dia = f"{r['dia_libre_violado']} de {r['piden_dia_libre']}" if r["piden_dia_libre"] else "-"
        L.append(f"| {r['sistema']} | **{r['puntuacion_media']}** | {r['puntuacion_min']} | "
                 f"{r['veces_mejor']}/{r['n']} | {r['pct_invalidas']}% | {r['pct_choques']}% | "
                 f"{r['pct_fuera_rango']}% | {r['pct_exceso_optativas']}% | {dia} | "
                 f"{r['segundos_media']} |")
    ref = resumen[0]["sistema"]
    L += ["", f"Comparación alumno por alumno contra **{ref}**:", "",
          "| Sistema | Mejor que el MAS | Igual | Peor | Diferencia media |", "|---|---|---|---|---|"]
    for r in resumen[1:]:
        mejor, igual, peor = r["vs_mas"]
        L.append(f"| {r['sistema']} | {mejor} | {igual} | {peor} | {r['dif_media_vs_mas']:+} |")
    return "\n".join(L) + "\n"


def guardar(filas, resumen, n, semilla):
    config.DIR_SALIDAS.mkdir(parents=True, exist_ok=True)
    md = config.DIR_SALIDAS / "experimento.md"
    md.write_text("# Experimento comparativo (mejora 2)\n\n" + tabla_markdown(resumen, n, semilla),
                  encoding="utf-8")
    ruta_csv = config.DIR_SALIDAS / "experimento.csv"
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    return md, ruta_csv
