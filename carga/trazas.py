# -*- coding: utf-8 -*-
"""
Trace Collector (Proyecto 2, sección 3.2) y registro de mensajes del
Contract Net con performativas estilo FIPA-ACL / KQML:
    cfp · propose · refuse · accept-proposal · reject-proposal · inform
"""
import json
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class Evento:
    timestamp: str
    agent: str
    task: str
    input: str
    output: str
    execution_time: float
    success: bool
    score: float | None = None
    detalles: dict = field(default_factory=dict)


@dataclass
class Mensaje:
    performativa: str
    emisor: str
    receptor: str
    contenido: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class Trazas:
    """Colector de trazas. Con activo=False no registra nada (simulaciones Shapley)."""

    def __init__(self, activo=True, eco=False):
        self.activo = activo
        self.eco = eco                    # imprimir en vivo
        self.eventos: list[Evento] = []
        self.mensajes: list[Mensaje] = []

    def mensaje(self, performativa, emisor, receptor, contenido):
        if not self.activo:
            return
        m = Mensaje(performativa, emisor, receptor, contenido)
        self.mensajes.append(m)
        if self.eco:
            print(f"  [{performativa:^16}] {emisor} → {receptor}: {contenido}")

    @contextmanager
    def tarea(self, agente, tarea, entrada):
        """Uso:  with trazas.tarea("AgenteCarga", "evaluar_carga", "...") as ev: ev['output']=..."""
        registro = {"output": "", "score": None, "detalles": {}}
        t0 = time.perf_counter()
        ok = True
        try:
            yield registro
        except Exception as e:
            ok = False
            registro["output"] = f"ERROR: {e}"
            raise
        finally:
            if self.activo:
                ev = Evento(
                    timestamp=datetime.now().isoformat(timespec="seconds"),
                    agent=agente, task=tarea, input=entrada,
                    output=registro["output"],
                    execution_time=round(time.perf_counter() - t0, 4),
                    success=ok, score=registro["score"], detalles=registro["detalles"])
                self.eventos.append(ev)

    def guardar(self, ruta):
        ruta.parent.mkdir(parents=True, exist_ok=True)
        datos = {"eventos": [asdict(e) for e in self.eventos],
                 "mensajes_contract_net": [asdict(m) for m in self.mensajes]}
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        return ruta
