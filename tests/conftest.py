# -*- coding: utf-8 -*-
import shutil
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from carga import config  # noqa: E402

HAY_JAVA = shutil.which("java") is not None
requiere_java = pytest.mark.skipif(not HAY_JAVA, reason="HermiT necesita Java")


@pytest.fixture(autouse=True)
def db_temporal(tmp_path, monkeypatch):
    """Cada prueba usa su propia base SQLite: nunca toca salidas/carga.db."""
    monkeypatch.setattr(config, "DB", tmp_path / "prueba.db")
    from carga import db
    db.inicializar()
    return config.DB


@pytest.fixture(scope="session")
def kb():
    from carga.kb import BaseConocimiento
    return BaseConocimiento()


@pytest.fixture(scope="session")
def sesion_a001(kb):
    """Una ejecución completa del MAS para A001 (sin LLM), reutilizada por varias pruebas."""
    from carga import sistema
    from carga.llm import ClienteLLM
    s = sistema.nueva_sesion("A001", "", usar_llm=False, eco=False, kb=kb, llm=ClienteLLM(habilitado=False))
    sistema.correr_contract_net(s)
    if HAY_JAVA:
        sistema.correr_validacion(s)
    sistema.correr_shapley(s)
    return s
