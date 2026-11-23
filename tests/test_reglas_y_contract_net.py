# -*- coding: utf-8 -*-
"""Reglas académicas, Contract Net y propiedades de los valores de Shapley."""
import pytest

from carga.contract_net import ESPECIALISTAS, ejecutar
from carga.evaluacion import analizar_elegibilidad, conflictos
from carga.trazas import Trazas


@pytest.mark.parametrize("matricula", ["A001", "A002", "A003"])
def test_elegibles_respetan_seriacion(kb, matricula):
    est = kb.estudiante(matricula)
    elegibles, descartadas = analizar_elegibilidad(kb, est)
    for c in elegibles:
        assert c not in est.aprobadas
        assert all(p in est.aprobadas for p in kb.materias[c].prerrequisitos)
        assert c in kb.ofertadas
    assert not set(elegibles) & set(descartadas)


@pytest.mark.parametrize("matricula", ["A001", "A002", "A003"])
def test_ganadora_valida(kb, matricula):
    from carga.preferencias import construir_preferencias
    est = kb.estudiante(matricula)
    prefs = construir_preferencias(est, kb.materias, "", None)
    elegibles, _ = analizar_elegibilidad(kb, est)
    res = ejecutar(kb, est, prefs, elegibles)
    g = res.ganadora
    assert res.estado == "exito" and g is not None
    assert kb.creditos_min <= g.creditos(kb) <= kb.creditos_max
    assert set(g.materias) <= set(elegibles)
    assert conflictos(kb, g.grupos) == []
    assert g.puntuacion == max(p.puntuacion for p in res.propuestas)


def test_protocolo_fipa(kb):
    from carga.preferencias import construir_preferencias
    est = kb.estudiante("A002")
    prefs = construir_preferencias(est, kb.materias, "", None)
    tr = Trazas()
    res = ejecutar(kb, est, prefs, analizar_elegibilidad(kb, est)[0], trazas=tr)
    perf = [m.performativa for m in tr.mensajes]
    assert perf[0] == "cfp"
    assert perf.count("accept-proposal") == 1
    assert perf.count("reject-proposal") == len(res.propuestas) - 1
    assert perf[-1] == "inform"


def test_shapley_eficiencia(sesion_a001):
    """Σ φ_i = v(N): los valores reparten exactamente la puntuación final."""
    s = sesion_a001
    total = s.v[frozenset(ESPECIALISTAS)]
    assert sum(s.phi.values()) == pytest.approx(total, abs=0.05)
    assert total == pytest.approx(s.resultado.ganadora.puntuacion, abs=0.01)


def test_shapley_coalicion_vacia(sesion_a001):
    assert sesion_a001.v[frozenset()] == 0
    assert len(sesion_a001.v) == 8                    # 2^3 coaliciones


def test_shapley_contratistas_eficiencia(sesion_a001):
    s = sesion_a001
    from carga.contract_net import CONTRATISTAS
    assert sum(s.phi_c.values()) == pytest.approx(s.v_c[frozenset(CONTRATISTAS)], abs=0.05)


@pytest.mark.parametrize("texto, esperado", [
    ("quiero llevar 60 creditos", 60),
    ("unos 52 créditos por favor", 52),
    ("quiero 70 créditos", 60),          # se ajusta al máximo institucional
    ("solo 10 creditos", 24),            # y al mínimo
])
def test_meta_explicita_de_creditos(kb, texto, esperado):
    from carga.preferencias import construir_preferencias
    est = kb.estudiante("A001")
    p = construir_preferencias(est, kb.materias, texto, None, (kb.creditos_min, kb.creditos_max))
    assert p["creditos_objetivo"] == esperado
    assert p["max_materias"] >= -(-esperado // 6)


def test_pedir_60_creditos_da_carga_sin_choques(kb):
    from carga import sistema
    for m in ("A001", "A002"):
        s = sistema.nueva_sesion(m, "quiero llevar 60 creditos", usar_llm=False, eco=False, kb=kb)
        g = sistema.correr_contract_net(s).ganadora
        assert conflictos(kb, g.grupos) == []
        assert kb.creditos_min <= g.creditos(kb) <= kb.creditos_max
        assert g.creditos(kb) > 40           # más que una carga normal
