# -*- coding: utf-8 -*-
"""Backend FastAPI + SQLite + herramientas @tool de CrewAI (vía httpx)."""
import pytest
from fastapi.testclient import TestClient

from carga import db

from .conftest import requiere_java


@pytest.fixture()
def cliente(db_temporal):
    from carga.api import app
    with TestClient(app) as c:
        yield c


def test_salud(cliente):
    d = cliente.get("/salud").json()
    assert d["api"] == "ok"
    assert d["ontologia"]["materias"] == 79 and d["ontologia"]["axiomas_seriacion"] == 35
    assert "ejecuciones" in d["sqlite"]["tablas"]


def test_alumnos_y_404(cliente):
    assert {a["matricula"] for a in cliente.get("/alumnos").json()} == {"A001", "A002", "A003"}
    assert cliente.get("/alumnos/ZZZ").status_code == 404
    assert cliente.post("/recomendar", json={"matricula": "ZZZ"}).status_code == 404


@requiere_java
def test_recomendar_se_guarda_en_sqlite(cliente):
    d = cliente.post("/recomendar", json={"matricula": "A002", "peticion": "algo ligero"}).json()
    assert d["estado"] == "exito" and d["validacion"]["aceptada"]
    ej = cliente.get(f"/auditoria/{d['ejecucion_id']}").json()
    assert ej["tipo"] == "recomendacion" and ej["materias"] == [m["clave"] for m in d["ganadora"]["materias"]]
    assert ej["trazas"] and ej["mensajes"]
    assert ej["shapley"]["especialistas"] == d["shapley"]["especialistas"]
    assert ej["tiempo_db"] is not None and ej["tiempo_hermit"] > 0


@requiere_java
def test_validar_rechaza_y_audita(cliente):
    d = cliente.post("/validar", json={"matricula": "A001",
                                       "materias": ["LIIS2105", "LIIS2112", "LIIB2104", "LICB2102", "LIIN2104"]}).json()
    assert d["aceptada"] is False and d["consistente"] is False
    assert db.ejecucion(d["ejecucion_id"])["estado"] == "rechazada"
    m = cliente.get("/metricas").json()
    assert m["validaciones"]["rechazadas"] == 1


def test_bitacora_de_llamadas(cliente):
    cliente.get("/alumnos", headers={"x-cliente": "crewai @tool prueba"})
    assert any(l["cliente"] == "crewai @tool prueba" for l in db.llamadas())


def test_explicacion_alucinada_se_rechaza(cliente, kb):
    from carga import sistema
    from carga.llm import ClienteLLM
    s = sistema.nueva_sesion("A003", "", usar_llm=False, eco=False, kb=kb, llm=ClienteLLM(habilitado=False))
    sistema.correr_contract_net(s)
    ej = db.guardar_recomendacion(s, "prueba", 0.1)
    otra = next(m.nombre for c, m in kb.materias.items()
                if c not in s.resultado.ganadora.materias and len(m.nombre) > 8)
    r = cliente.post(f"/auditoria/{ej}/explicacion", json={"texto": f"Te recomiendo {otra}."}).json()
    assert r["guardada"] is False


@requiere_java
def test_herramientas_crewai_llaman_a_la_api(cliente):
    """Las @tool usan httpx; aquí el cliente httpx es el TestClient (misma interfaz)."""
    from carga.crew import ClienteAPI, _resumen_oficial, herramientas
    api = ClienteAPI.__new__(ClienteAPI)
    api.http = cliente
    rec = api.post("/recomendar", "prueba", matricula="A001")
    estado = {"ejecucion_id": rec["ejecucion_id"], "oficial": _resumen_oficial(rec),
              "materias_a_validar": ["LIIS2105", "LIIN2104"]}
    fn = herramientas(api, "", estado)
    assert "MATERIAS VÁLIDAS" in fn["consultar_historial_academico"]("A001")
    assert "CargaAvance" in fn["evaluar_carga_academica"]("A001")
    assert "Preferencias interpretadas" in fn["analizar_horarios_y_preferencias"]("A001")
    assert fn["validar_inscripcion"]("A001").startswith("RECHAZADA")
    assert "PROPUESTA GANADORA" in fn["coordinar_carga"]("A001")
    rutas = {l["ruta"] for l in db.llamadas() if l["cliente"].startswith("crewai @tool")}
    assert {"/agentes/historial", "/agentes/carga", "/agentes/horarios", "/validar"} <= rutas


def test_guardia_del_veredicto():
    from carga.crew import _explicacion_fiel
    v = {"aceptada": False, "materias": ["LIIS2105", "LIIN2104"],
         "hallazgos": [{"origen": "HermiT", "materia": "LIIN2104", "motivo": "viola la seriación"}]}
    assert _explicacion_fiel("No puedes inscribir LIIN2104 porque te falta LIIB2104.", v)
    # el caso que vimos con llama3.2: dice que SÍ puede inscribir la materia rechazada
    assert not _explicacion_fiel("Puede inscribirse en LIIS2105, LIIN2104 y LICB2102.", v)
    assert not _explicacion_fiel("La solicitud fue rechazada.", v)          # no nombra la materia
    ok = {"aceptada": True, "materias": ["LIIS2105"], "hallazgos": []}
    assert _explicacion_fiel("Puedes inscribir todas las materias.", ok)
    assert not _explicacion_fiel("La solicitud fue rechazada.", ok)


def test_base_borrada_con_la_api_encendida_se_recrea():
    """Si se borra la base de SQLite con la API corriendo, la siguiente llamada
    recrea las tablas en vez de fallar con 'no such table'."""
    from fastapi.testclient import TestClient
    from carga import config
    from carga.api import app
    with TestClient(app) as c:
        assert c.get("/salud").status_code == 200
        for sufijo in ("", "-wal", "-shm"):
            config.DB.with_name(config.DB.name + sufijo).unlink(missing_ok=True)
        r = c.get("/salud")
        assert r.status_code == 200
        assert c.get("/auditoria").status_code == 200
