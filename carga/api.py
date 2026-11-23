# -*- coding: utf-8 -*-
"""
Backend asíncrono (FastAPI) del sistema multiagente.

    python main.py api            → http://127.0.0.1:8077      (página de demo)
                                    http://127.0.0.1:8077/docs (Swagger)

La ontología se carga UNA vez al arrancar (BaseConocimiento). Cada endpoint
pesado (Contract Net, Shapley, HermiT) corre en un hilo aparte con
`run_in_threadpool`, así el bucle asíncrono no se bloquea. Toda ejecución y
toda llamada a la API queda en SQLite para auditoría.

Los endpoints /agentes/* son los que invocan las herramientas @tool de CrewAI
(ver crew.py) por HTTP con httpx.
"""
import subprocess
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import owlready2 as ow
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import config, db, sistema
from .agentes import AgenteHistorial, AgenteHorarios, _es_fiel
from .contract_net import crear_contratistas
from .evaluacion import analizar_elegibilidad, conflictos
from .kb import BaseConocimiento
from .llm import ClienteLLM
from .preferencias import construir_preferencias, describir
from .validador import AgenteValidador

WEB = Path(__file__).resolve().parent / "web" / "index.html"
ESTADO: dict = {}
_MAS = threading.Lock()          # owlready2 no es thread-safe: una ejecución del MAS a la vez


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    db.inicializar()
    t0 = time.perf_counter()
    ESTADO["kb"] = await run_in_threadpool(BaseConocimiento)
    ESTADO["carga_ontologia_s"] = round(time.perf_counter() - t0, 3)
    print(f"✔ Ontología cargada en {ESTADO['carga_ontologia_s']} s · SQLite en {config.DB}")
    yield


app = FastAPI(title="Agente de carga académica",
              description="Sistema multiagente (Contract Net + CrewAI) con ontología OWL 2, "
                          "validación HermiT en RAM y auditoría en SQLite.",
              version="2.0", lifespan=ciclo_de_vida)


def kb() -> BaseConocimiento:
    return ESTADO["kb"]


# ------------------------------------------------------------------ auditoría HTTP
@app.middleware("http")
async def auditar(request: Request, call_next):
    t0 = time.perf_counter()
    resp = await call_next(request)
    ruta = request.url.path
    if ruta != "/" and not ruta.startswith(("/docs", "/openapi", "/favicon", "/redoc")):
        cliente = request.headers.get("x-cliente") or request.headers.get("user-agent", "-")[:40]
        dt = time.perf_counter() - t0
        await run_in_threadpool(db.registrar_llamada, request.method, ruta, cliente,
                                resp.status_code, dt)
        print(f"  [api] {request.method} {ruta} ← {cliente} · {resp.status_code} · {dt:.2f}s", flush=True)
    return resp


# ------------------------------------------------------------------ modelos
class PeticionAlumno(BaseModel):
    matricula: str = Field(examples=["A001"])
    peticion: str = Field("", examples=["quiero algo ligero, en la mañana y sin clases el viernes"])


class PeticionRecomendar(PeticionAlumno):
    usar_llm: bool = Field(False, description="redactar con Ollama (lento en CPU)")
    origen: str = Field("api", description="api | web | crewai")


class PeticionValidar(BaseModel):
    matricula: str = Field(examples=["A001"])
    materias: list[str] = Field(examples=[["LIIS2105", "LIIS2112", "LIIB2104", "LICB2102", "LIIN2104"]])
    origen: str = "api"


class Explicacion(BaseModel):
    texto: str
    fuente: str = "CrewAI"


def _alumno(m):
    try:
        return kb().estudiante(m)
    except KeyError as e:
        raise HTTPException(404, str(e.args[0]))


def _prefs(est, peticion):
    return construir_preferencias(est, kb().materias, peticion, None)


# ------------------------------------------------------------------ página y salud
@app.get("/", include_in_schema=False)
async def pagina():
    return FileResponse(WEB)


_JAVA = {}


def _java():
    if "v" not in _JAVA:
        try:
            p = subprocess.run([ow.JAVA_EXE, "-version"], capture_output=True, text=True, timeout=20)
            _JAVA["v"] = (p.stderr or p.stdout).splitlines()[0]
        except Exception as e:
            _JAVA["v"] = f"no disponible: {e}"
    return _JAVA["v"]


@app.get("/salud", tags=["servicio"], summary="Estado de API, ontología, SQLite, HermiT y LLM")
async def salud():
    k = kb()
    llm = await run_in_threadpool(ClienteLLM, None, True)
    return {
        "api": "ok",
        "ontologia": {
            "archivo": str(config.ONTO_POBLADA.relative_to(config.RAIZ)),
            "cargada_en_s": ESTADO.get("carga_ontologia_s"),
            "materias": len(k.materias), "grupos": len(k.grupos), "alumnos": len(k.matriculas()),
            "axiomas_seriacion": sum(c.name.startswith("PropuestaCon_") for c in k.onto.classes()),
            "periodo": k.periodo,
            "creditos": [k.creditos_min, k.creditos_max],
        },
        "sqlite": {"archivo": str(config.DB), "tablas": await run_in_threadpool(db.conteos)},
        "hermit": {"java": await run_in_threadpool(_java), "modo": "consistencia (-k) en RAM"},
        "llm": {"disponible": llm.disponible, "modelo": llm.modelo, "detalle": llm.url or llm.motivo},
    }


# ------------------------------------------------------------------ ontología
@app.get("/alumnos", tags=["ontología"])
async def alumnos():
    k = kb()
    salida = []
    for m in k.matriculas():
        e = k.estudiante(m)
        salida.append({"matricula": m, "nombre": e.nombre, "semestre": e.semestre,
                       "promedio": e.promedio, "aprobadas": len(e.aprobadas),
                       "reprobadas": list(e.reprobadas)})
    return salida


@app.get("/alumnos/{matricula}", tags=["ontología"], summary="Kárdex y materias válidas/descartadas")
async def alumno(matricula: str):
    est = _alumno(matricula)
    k = kb()
    el, desc = analizar_elegibilidad(k, est)
    return {"matricula": est.matricula, "nombre": est.nombre, "semestre": est.semestre,
            "promedio": est.promedio, "creditos_acumulados": est.creditos_acumulados,
            "aprobadas": [{"clave": c, "nombre": k.materias[c].nombre, "calificacion": v}
                          for c, v in sorted(est.aprobadas.items())],
            "reprobadas": [{"clave": c, "nombre": k.materias[c].nombre, "calificacion": v}
                           for c, v in sorted(est.reprobadas.items())],
            "validas": [{"clave": c, "nombre": k.materias[c].nombre, "creditos": k.materias[c].creditos,
                         "prioridad": p} for c, p in sorted(el.items(), key=lambda x: -x[1])],
            "descartadas": [{"clave": c, "nombre": k.materias[c].nombre, "motivo": mot}
                            for c, mot in desc.items()]}


# ------------------------------------------------------------------ agentes (los usa CrewAI)
@app.post("/agentes/historial", tags=["agentes"], summary="AgenteHistorial: kárdex + seriación")
async def agente_historial(req: PeticionAlumno):
    est = _alumno(req.matricula)
    k = kb()
    el, desc = await run_in_threadpool(AgenteHistorial().analizar, k, est)
    validas = "; ".join(f"{c} {k.materias[c].nombre} ({k.materias[c].creditos} cr, prioridad {p})"
                        for c, p in sorted(el.items(), key=lambda x: -x[1]))
    return {"validas": el, "descartadas": desc,
            "resumen": (f"Alumno {est.nombre} ({est.matricula}), semestre {est.semestre}, promedio "
                        f"{est.promedio}. Aprobadas: {len(est.aprobadas)}. Reprobadas: "
                        f"{', '.join(est.reprobadas) or 'ninguna'}.\nMATERIAS VÁLIDAS: {validas}\n"
                        f"DESCARTADAS: {'; '.join(f'{c}: {m}' for c, m in desc.items()) or 'ninguna'}")}


def _ofertas(est, peticion):
    k = kb()
    prefs = _prefs(est, peticion)
    el, _ = analizar_elegibilidad(k, est)
    ofertas = {c.nombre: c.ofertar(k, est, prefs, el, k=config.OFERTAS_POR_CONTRATISTA)
               for c in crear_contratistas()}
    return prefs, el, ofertas


@app.post("/agentes/carga", tags=["agentes"], summary="3 contratistas AgenteCarga: ofertas")
async def agente_carga(req: PeticionAlumno):
    est = _alumno(req.matricula)
    k = kb()
    prefs, _, ofertas = await run_in_threadpool(_ofertas, est, req.peticion)
    lineas = [f"{n}: {', '.join(combo)} = {sum(k.materias[x].creditos for x in combo)} créditos "
              f"(autoevaluación {nota})" for n, ofs in ofertas.items() for combo, nota in ofs]
    return {"ofertas": {n: [{"materias": c, "autoevaluacion": nota} for c, nota in ofs]
                        for n, ofs in ofertas.items()},
            "resumen": (f"Límites: {k.creditos_min}-{k.creditos_max} créditos. Meta: "
                        f"{prefs['creditos_objetivo']} créditos, máximo {prefs['max_materias']} materias.\n"
                        + "\n".join(lineas))}


@app.post("/agentes/horarios", tags=["agentes"], summary="AgenteHorarios: grupos sin choques")
async def agente_horarios(req: PeticionAlumno):
    est = _alumno(req.matricula)
    k = kb()

    def correr():
        prefs, el, ofertas = _ofertas(est, req.peticion)
        combos = list(dict.fromkeys(tuple(c) for ofs in ofertas.values() for c, _ in ofs))[:3]
        return prefs, AgenteHorarios().asignar(k, [list(c) for c in combos], prefs, el)

    prefs, asign = await run_in_threadpool(correr)
    lineas = []
    for i, (m, g) in enumerate(asign, 1):
        ch = conflictos(k, g)
        lineas.append(f"{i}. grupos {', '.join(x for x in g.values() if x)} — "
                      f"{'SIN choques' if not ch else f'{len(ch)} choque(s)'}")
    return {"preferencias": describir(prefs), "asignaciones": [{"materias": m, "grupos": g} for m, g in asign],
            "resumen": f"Preferencias interpretadas: {describir(prefs)}.\n" + "\n".join(lineas)}


# ------------------------------------------------------------------ validador (HermiT en RAM)
@app.post("/validar", tags=["validador"],
          summary="AgenteValidador: consistencia de una solicitud con HermiT (inferencia efímera)")
async def validar(req: PeticionValidar):
    _alumno(req.matricula)
    from .trazas import Trazas
    tr = Trazas()

    def correr():
        with tr.tarea("AgenteValidador", "validar_consistencia_hermit", ", ".join(req.materias)) as t:
            r = AgenteValidador().validar(kb(), req.matricula, req.materias, trazas=tr)
            t["output"] = "ACEPTADA" if r.aceptada else "RECHAZADA"
        return r, db.guardar_validacion(r, req.origen, tr)

    res, ej_id = await run_in_threadpool(correr)
    k = kb()
    return {"ejecucion_id": ej_id, **res.a_dict(),
            "detalle_materias": [{"clave": c, "nombre": k.materias[c].nombre,
                                  "creditos": k.materias[c].creditos,
                                  "prerrequisitos": k.materias[c].prerrequisitos,
                                  "grupo": res.grupos.get(c)} for c in res.materias if c in k.materias]}


# ------------------------------------------------------------------ MAS completo
def _materias_payload(k, g):
    salida = []
    for c in g.materias:
        grp = k.grupos.get(g.grupos.get(c))
        salida.append({"clave": c, "nombre": k.materias[c].nombre, "creditos": k.materias[c].creditos,
                       "grupo": grp.clave if grp else None,
                       "modalidad": grp.modalidad if grp else None,
                       "profesor": grp.profesor if grp else None,
                       "horario": ", ".join(str(b) for b in grp.bloques) if grp else ""})
    return salida


def _recomendar(req: PeticionRecomendar):
    with _MAS:
        t0 = time.perf_counter()
        llm = ClienteLLM(habilitado=req.usar_llm)
        s = sistema.nueva_sesion(req.matricula, req.peticion, usar_llm=req.usar_llm, eco=False,
                                 kb=kb(), llm=llm)
        sistema.correr_contract_net(s)
        sistema.correr_validacion(s)
        sistema.correr_shapley(s)
        sistema.cerrar(s, imprimir=False)
        dur = time.perf_counter() - t0
        ej_id = db.guardar_recomendacion(s, req.origen, dur)
    k, g, r = s.kb, s.resultado.ganadora, s.resultado
    return {
        "ejecucion_id": ej_id,
        "alumno": {"matricula": s.est.matricula, "nombre": s.est.nombre, "semestre": s.est.semestre,
                   "promedio": s.est.promedio},
        "preferencias": describir(s.prefs), "interpretado_por": s.prefs["interpretado_por"],
        "estado": r.estado,
        "ganadora": {"id": g.id, "autor": g.autor, "puntuacion": g.puntuacion, "creditos": g.creditos(k),
                     "criterios": g.criterios, "materias": _materias_payload(k, g)} if g else None,
        "licitacion": [{"id": p.id, "autor": p.autor, "puntuacion": p.puntuacion,
                        "creditos": p.creditos(k), "materias": p.materias} for p in r.propuestas],
        "validacion": s.validacion.a_dict() if s.validacion else None,
        "shapley": {"especialistas": s.phi, "contratistas": s.phi_c},
        "coaliciones": {"+".join(sorted(x.replace("Agente", "") for x in S)) or "∅": val
                        for S, val in (s.v or {}).items()},
        "explicacion": s.explicacion, "fuente": s.fuente_exp,
        "mensajes": [m.__dict__ for m in s.trazas.mensajes],
        "trazas": [{"agente": e.agent, "tarea": e.task, "salida": e.output, "tiempo": e.execution_time,
                    "exito": e.success} for e in s.trazas.eventos],
        "duracion_s": round(dur, 3),
    }


@app.post("/recomendar", tags=["MAS"],
          summary="Contract Net completo + validación HermiT + Shapley; se guarda en SQLite")
async def recomendar(req: PeticionRecomendar):
    _alumno(req.matricula)
    return await run_in_threadpool(_recomendar, req)


@app.post("/auditoria/{ej_id}/explicacion", tags=["auditoría"],
          summary="Guarda la redacción de CrewAI si pasa el filtro anti-alucinación")
async def guardar_explicacion(ej_id: int, exp: Explicacion):
    ej = await run_in_threadpool(db.ejecucion, ej_id)
    if ej is None or ej["tipo"] != "recomendacion" or not ej["materias"]:
        raise HTTPException(404, "ejecución de recomendación no encontrada")
    k = kb()
    from .evaluacion import Propuesta
    prop = Propuesta("g", ej["materias"], ej["detalle"].get("grupos", {}))
    dias = {b.dia for c in prop.materias if prop.grupos.get(c) for b in k.grupos[prop.grupos[c]].bloques}
    libres = [d for d in ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"] if d not in dias]
    fiel = _es_fiel(exp.texto, k, prop, libres)
    if fiel:
        await run_in_threadpool(db.guardar_explicacion, ej_id, exp.texto, exp.fuente)
    return {"guardada": fiel,
            "motivo": "ok" if fiel else "la redacción menciona datos que no están en la propuesta"}


# ------------------------------------------------------------------ auditoría
@app.get("/auditoria", tags=["auditoría"], summary="Últimas ejecuciones guardadas en SQLite")
async def auditoria(limite: int = 30, tipo: str | None = None):
    return await run_in_threadpool(db.listar_ejecuciones, limite, tipo)


@app.get("/auditoria/llamadas", tags=["auditoría"], summary="Bitácora de llamadas HTTP (incluye @tool)")
async def auditoria_llamadas(limite: int = 50):
    return await run_in_threadpool(db.llamadas, limite)


@app.get("/auditoria/{ej_id}", tags=["auditoría"], summary="Una ejecución con trazas, mensajes y Shapley")
async def auditoria_detalle(ej_id: int):
    ej = await run_in_threadpool(db.ejecucion, ej_id)
    if ej is None:
        raise HTTPException(404, "no existe esa ejecución")
    return ej


@app.get("/metricas", tags=["auditoría"], summary="CRUD vs inferencia, tasa de éxito, Shapley promedio")
async def metricas():
    return await run_in_threadpool(db.metricas)
