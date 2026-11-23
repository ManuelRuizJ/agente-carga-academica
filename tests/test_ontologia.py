# -*- coding: utf-8 -*-
"""La ontología poblada tiene el plan real y los axiomas que usa el validador."""


def test_plan_real_cargado(kb):
    assert len(kb.materias) == 79
    assert kb.creditos_min == 24 and kb.creditos_max == 48
    assert set(kb.matriculas()) == {"A001", "A002", "A003"}


def test_prerrequisito_e_inversa(kb):
    # esPrerrequisitoDe es la inversa de tienePrerrequisito (TBox)
    for clave, m in kb.materias.items():
        for p in m.prerrequisitos:
            assert clave in kb.materias[p].desbloquea


def test_un_axioma_por_materia_seriada(kb):
    seriadas = {c for c, m in kb.materias.items() if m.prerrequisitos}
    reglas = {c.name.removeprefix("PropuestaCon_") for c in kb.onto.classes()
              if c.name.startswith("PropuestaCon_")}
    assert reglas == seriadas


def test_kardex_por_sparql(kb):
    est = kb.estudiante("A001")
    assert est.aprobadas and all(c in kb.materias for c in est.aprobadas)
    assert "LIIS2105" in est.reprobadas
