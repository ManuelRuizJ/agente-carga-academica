# -*- coding: utf-8 -*-
"""
Persistencia transaccional en SQLite (modelo de datos híbrido).

    Ontología OWL 2  → conocimiento declarativo: reglas, seriación, axiomas (TBox)
    SQLite           → datos operativos: cada ejecución, sus trazas, los mensajes
                       del Contract Net, los valores de Shapley y las llamadas a la API

Las escrituras son rápidas (milisegundos) y quedan para auditoría; el
razonamiento costoso (HermiT) se hace aparte, en RAM, solo cuando se valida.
"""
import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime

from . import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS ejecuciones (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    creada        TEXT NOT NULL,
    tipo          TEXT NOT NULL,            -- recomendacion | validacion
    origen        TEXT NOT NULL,            -- api | crewai | web | cli
    matricula     TEXT NOT NULL,
    peticion      TEXT,
    estado        TEXT NOT NULL,            -- exito | sin_propuesta | aceptada | rechazada
    puntuacion    REAL,
    creditos      INTEGER,
    materias      TEXT,                     -- JSON
    justificacion TEXT,
    explicacion   TEXT,
    fuente        TEXT,
    detalle       TEXT,                     -- JSON (criterios, hallazgos, grupos...)
    duracion      REAL,                     -- s, ejecución completa
    tiempo_hermit REAL,                     -- s, inferencia semántica
    tiempo_db     REAL                      -- s, escritura en SQLite
);
CREATE TABLE IF NOT EXISTS trazas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ejecucion_id  INTEGER NOT NULL REFERENCES ejecuciones(id) ON DELETE CASCADE,
    timestamp     TEXT, agente TEXT, tarea TEXT, entrada TEXT, salida TEXT,
    tiempo        REAL, exito INTEGER, score REAL
);
CREATE TABLE IF NOT EXISTS mensajes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ejecucion_id  INTEGER NOT NULL REFERENCES ejecuciones(id) ON DELETE CASCADE,
    timestamp     TEXT, performativa TEXT, emisor TEXT, receptor TEXT, contenido TEXT
);
CREATE TABLE IF NOT EXISTS shapley (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ejecucion_id  INTEGER NOT NULL REFERENCES ejecuciones(id) ON DELETE CASCADE,
    juego         TEXT NOT NULL,            -- especialistas | contratistas
    agente        TEXT NOT NULL,
    phi           REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS llamadas_api (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT, metodo TEXT, ruta TEXT, cliente TEXT,
    estado_http   INTEGER, tiempo REAL
);
CREATE INDEX IF NOT EXISTS ix_trazas_ej   ON trazas(ejecucion_id);
CREATE INDEX IF NOT EXISTS ix_mensajes_ej ON mensajes(ejecucion_id);
CREATE INDEX IF NOT EXISTS ix_shapley_ej  ON shapley(ejecucion_id);
"""


def _ruta():
    return config.DB


@contextmanager
def conexion():
    """Una conexión por operación (seguro con los hilos de FastAPI)."""
    ruta = _ruta()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # Si alguien borró la base con la API encendida, se recrea el esquema aquí
    # mismo en lugar de fallar con "no such table".
    nueva = not ruta.exists() or ruta.stat().st_size == 0
    con = sqlite3.connect(ruta, timeout=10)
    con.row_factory = sqlite3.Row
    if nueva:
        con.execute("PRAGMA journal_mode = WAL")
        con.executescript(ESQUEMA)
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def inicializar():
    with conexion() as con:
        con.execute("PRAGMA journal_mode = WAL")
        con.executescript(ESQUEMA)


def _ahora():
    return datetime.now().isoformat(timespec="seconds")


def _insertar_trazas(con, ej_id, trazas):
    con.executemany(
        "INSERT INTO trazas (ejecucion_id, timestamp, agente, tarea, entrada, salida, tiempo, exito, score)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        [(ej_id, e.timestamp, e.agent, e.task, str(e.input)[:500], str(e.output)[:500],
          e.execution_time, int(e.success), e.score) for e in trazas.eventos])
    con.executemany(
        "INSERT INTO mensajes (ejecucion_id, timestamp, performativa, emisor, receptor, contenido)"
        " VALUES (?,?,?,?,?,?)",
        [(ej_id, m.timestamp, m.performativa, m.emisor, m.receptor, m.contenido[:500])
         for m in trazas.mensajes])


# ------------------------------------------------------------------ escrituras
def guardar_recomendacion(s, origen="api", duracion=0.0) -> int:
    """Guarda una sesión completa del MAS (sistema.Sesion) en una transacción."""
    t0 = time.perf_counter()
    g = s.resultado.ganadora if s.resultado else None
    v = s.validacion
    detalle = {
        "preferencias": {k: v_ for k, v_ in (s.prefs or {}).items() if k != "texto"},
        "grupos": g.grupos if g else {},
        "criterios": g.criterios if g else {},
        "autor": g.autor if g else None,
        "licitacion": [{"id": p.id, "autor": p.autor, "puntuacion": p.puntuacion,
                        "materias": p.materias} for p in (s.resultado.propuestas if s.resultado else [])],
        "descartadas": s.resultado.descartadas if s.resultado else {},
        "validacion": v.a_dict() if v else None,
        "v_especialistas": {"+".join(sorted(k)) or "∅": val for k, val in (s.v or {}).items()},
    }
    with conexion() as con:
        cur = con.execute(
            "INSERT INTO ejecuciones (creada, tipo, origen, matricula, peticion, estado, puntuacion,"
            " creditos, materias, justificacion, explicacion, fuente, detalle, duracion, tiempo_hermit)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (_ahora(), "recomendacion", origen, s.est.matricula, s.prefs.get("texto", "") if s.prefs else "",
             s.resultado.estado if s.resultado else "error",
             g.puntuacion if g else None, g.creditos(s.kb) if g else None,
             json.dumps(g.materias if g else []), v.justificacion if v else None,
             s.explicacion, s.fuente_exp, json.dumps(detalle, ensure_ascii=False, default=str),
             round(duracion, 4), v.tiempo_hermit if v else None))
        ej_id = cur.lastrowid
        _insertar_trazas(con, ej_id, s.trazas)
        filas = [(ej_id, "especialistas", a, p) for a, p in (s.phi or {}).items()]
        filas += [(ej_id, "contratistas", a, p) for a, p in (s.phi_c or {}).items()]
        con.executemany("INSERT INTO shapley (ejecucion_id, juego, agente, phi) VALUES (?,?,?,?)", filas)
        con.execute("UPDATE ejecuciones SET tiempo_db = ? WHERE id = ?",
                    (round(time.perf_counter() - t0, 5), ej_id))
    return ej_id


def guardar_validacion(res, origen="api", trazas=None) -> int:
    t0 = time.perf_counter()
    with conexion() as con:
        cur = con.execute(
            "INSERT INTO ejecuciones (creada, tipo, origen, matricula, peticion, estado, creditos,"
            " materias, justificacion, detalle, duracion, tiempo_hermit)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (_ahora(), "validacion", origen, res.matricula, ", ".join(res.materias),
             "aceptada" if res.aceptada else "rechazada", res.creditos,
             json.dumps(res.materias), res.justificacion,
             json.dumps({"hallazgos": [asdict(h) for h in res.hallazgos], "grupos": res.grupos,
                         "consistente": res.consistente, "error": res.error}, ensure_ascii=False),
             res.tiempo_total, res.tiempo_hermit))
        ej_id = cur.lastrowid
        if trazas is not None:
            _insertar_trazas(con, ej_id, trazas)
        con.execute("UPDATE ejecuciones SET tiempo_db = ? WHERE id = ?",
                    (round(time.perf_counter() - t0, 5), ej_id))
    return ej_id


def guardar_explicacion(ej_id, texto, fuente) -> bool:
    with conexion() as con:
        cur = con.execute("UPDATE ejecuciones SET explicacion = ?, fuente = ? WHERE id = ?",
                          (texto, fuente, ej_id))
        return cur.rowcount == 1


def registrar_llamada(metodo, ruta, cliente, estado_http, tiempo):
    with conexion() as con:
        con.execute("INSERT INTO llamadas_api (timestamp, metodo, ruta, cliente, estado_http, tiempo)"
                    " VALUES (?,?,?,?,?,?)", (_ahora(), metodo, ruta, cliente, estado_http, round(tiempo, 4)))


# ------------------------------------------------------------------ lecturas
def _fila(r):
    d = dict(r)
    for k in ("materias", "detalle"):
        if d.get(k):
            d[k] = json.loads(d[k])
    return d


def listar_ejecuciones(limite=30, tipo=None) -> list[dict]:
    q = ("SELECT id, creada, tipo, origen, matricula, peticion, estado, puntuacion, creditos, materias,"
         " justificacion, duracion, tiempo_hermit, tiempo_db FROM ejecuciones")
    args = []
    if tipo:
        q += " WHERE tipo = ?"
        args.append(tipo)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limite)
    with conexion() as con:
        return [_fila(r) for r in con.execute(q, args)]


def ejecucion(ej_id) -> dict | None:
    with conexion() as con:
        r = con.execute("SELECT * FROM ejecuciones WHERE id = ?", (ej_id,)).fetchone()
        if r is None:
            return None
        d = _fila(r)
        d["trazas"] = [dict(x) for x in con.execute(
            "SELECT timestamp, agente, tarea, entrada, salida, tiempo, exito, score FROM trazas"
            " WHERE ejecucion_id = ? ORDER BY id", (ej_id,))]
        d["mensajes"] = [dict(x) for x in con.execute(
            "SELECT timestamp, performativa, emisor, receptor, contenido FROM mensajes"
            " WHERE ejecucion_id = ? ORDER BY id", (ej_id,))]
        d["shapley"] = {}
        for x in con.execute("SELECT juego, agente, phi FROM shapley WHERE ejecucion_id = ? ORDER BY id",
                             (ej_id,)):
            d["shapley"].setdefault(x["juego"], {})[x["agente"]] = x["phi"]
        return d


def llamadas(limite=50) -> list[dict]:
    with conexion() as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM llamadas_api ORDER BY id DESC LIMIT ?", (limite,))]


def conteos() -> dict:
    with conexion() as con:
        return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("ejecuciones", "trazas", "mensajes", "shapley", "llamadas_api")}


def metricas() -> dict:
    """Desempeño: CRUD (SQLite) vs inferencia semántica (HermiT) y tasa de éxito."""
    with conexion() as con:
        t0 = time.perf_counter()
        for _ in range(20):
            con.execute("SELECT * FROM ejecuciones ORDER BY id DESC LIMIT 20").fetchall()
        lectura = (time.perf_counter() - t0) / 20

        def prom(q):
            r = con.execute(q).fetchone()
            return {"promedio_s": round(r[0], 5) if r[0] is not None else None, "n": r[1]}

        rec = con.execute("SELECT COUNT(*), SUM(estado = 'exito') FROM ejecuciones"
                          " WHERE tipo = 'recomendacion'").fetchone()
        cert = con.execute("SELECT COUNT(*), SUM(justificacion LIKE 'HermiT: la ontología sigue CONSISTENTE%')"
                           " FROM ejecuciones WHERE tipo = 'recomendacion' AND estado = 'exito'").fetchone()
        val = con.execute("SELECT COUNT(*), SUM(estado = 'aceptada'), SUM(estado = 'rechazada')"
                          " FROM ejecuciones WHERE tipo = 'validacion'").fetchone()
        return {
            "tiempos": {
                "crud_lectura_sqlite": {"promedio_s": round(lectura, 6), "n": 20},
                "crud_escritura_sqlite": prom("SELECT AVG(tiempo_db), COUNT(tiempo_db) FROM ejecuciones"),
                "inferencia_hermit": prom("SELECT AVG(tiempo_hermit), COUNT(tiempo_hermit) FROM ejecuciones"
                                          " WHERE tiempo_hermit > 0"),
                "recomendacion_completa": prom("SELECT AVG(duracion), COUNT(*) FROM ejecuciones"
                                               " WHERE tipo = 'recomendacion'"),
            },
            "recomendaciones": {"total": rec[0], "con_propuesta": rec[1] or 0,
                                "tasa_exito": round((rec[1] or 0) / rec[0], 3) if rec[0] else None,
                                "certificadas_por_hermit": cert[1] or 0},
            "validaciones": {"total": val[0], "aceptadas": val[1] or 0, "rechazadas": val[2] or 0},
            "shapley_promedio": {r["agente"]: round(r["p"], 2) for r in con.execute(
                "SELECT agente, AVG(phi) AS p FROM shapley WHERE juego = 'especialistas' GROUP BY agente")},
        }
