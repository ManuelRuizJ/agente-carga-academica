# -*- coding: utf-8 -*-
"""AgenteValidador: HermiT en RAM detecta violaciones de seriación."""
import hashlib

from carga import config
from carga.validador import AgenteValidador

from .conftest import requiere_java

VALIDA_A001 = ["LIIS2105", "LIIS2112", "LIIB2104", "LICB2102", "LIIE2104"]   # 32 créditos


@requiere_java
def test_solicitud_valida_es_consistente(kb):
    r = AgenteValidador().validar(kb, "A001", VALIDA_A001)
    assert r.consistente is True
    assert r.aceptada and r.hallazgos == []


@requiere_java
def test_violacion_de_seriacion_es_inconsistente(kb):
    # LIIN2104 requiere LIIB2104, que A001 no ha aprobado
    pedido = VALIDA_A001[:-1] + ["LIIN2104"]
    r = AgenteValidador().validar(kb, "A001", pedido)
    assert r.consistente is False and not r.aceptada
    h = [x for x in r.hallazgos if x.origen == "HermiT"]
    assert len(h) == 1 and h[0].materia == "LIIN2104"
    assert "LIIB2104" in h[0].axioma


@requiere_java
def test_ganadora_del_mas_queda_certificada(sesion_a001):
    assert sesion_a001.validacion.consistente is True
    assert sesion_a001.validacion.aceptada


@requiere_java
def test_inferencia_efimera_no_modifica_la_ontologia(kb):
    antes = hashlib.sha256(config.ONTO_POBLADA.read_bytes()).hexdigest()
    AgenteValidador().validar(kb, "A001", ["LIIN2104"])
    assert hashlib.sha256(config.ONTO_POBLADA.read_bytes()).hexdigest() == antes
    # y la siguiente solicitud no "hereda" la anterior
    assert AgenteValidador().validar(kb, "A001", VALIDA_A001).consistente is True


def test_reglas_fuera_de_owl(kb, monkeypatch):
    """Créditos, materias inexistentes o ya aprobadas se reportan como 'regla'."""
    monkeypatch.setattr(AgenteValidador, "_hermit", staticmethod(lambda *a: (True, 0.0)))
    est = kb.estudiante("A001")
    aprobada = next(iter(est.aprobadas))
    r = AgenteValidador().validar(kb, "A001", ["NOEXISTE", aprobada])
    motivos = {}
    for h in r.hallazgos:
        motivos.setdefault((h.origen, h.materia), []).append(h.motivo)
    assert ("regla", "NOEXISTE") in motivos
    assert any("ya está aprobada" in m for m in motivos[("regla", aprobada)])
    assert ("regla", "carga") in motivos               # muy pocos créditos
    assert not r.aceptada
