#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agente de carga académica — Sistema Multiagente con ontología como base de conocimiento.

Uso rápido:
    python main.py diagnostico
    python main.py alumnos
    python main.py recomendar A001
    python main.py recomendar A002 -p "quiero carga ligera, en la tarde y sin viernes"
    python main.py recomendar A003 --sin-llm --razonador
    python main.py crew A001 -p "me interesa IA"           # orquestación con CrewAI
    python main.py demo                                     # los 3 alumnos, sin LLM
    python main.py experimento                              # mejora 2: compara sistemas
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser(description="MAS de recomendación de carga académica")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("poblar", help="(re)genera la ontología poblada desde datos/semilla.py")
    sub.add_parser("alumnos", help="lista los estudiantes de la ontología")
    sub.add_parser("diagnostico", help="revisa Ollama (CPU/GPU) y memoria")
    sub.add_parser("demo", help="ejecuta los 3 alumnos sin LLM (segundos)")
    ex = sub.add_parser("experimento", help="compara el MAS contra otros sistemas (mejora 2)")
    ex.add_argument("-n", type=int, default=20, help="número de alumnos sintéticos")
    ex.add_argument("--semilla", type=int, default=7)
    ex.add_argument("--llm", action="store_true", help="agrega el 'LLM solo' (lento en CPU)")

    for nombre, ayuda in [("recomendar", "MAS en Python puro + LLM mínimo (recomendado)"),
                          ("crew", "misma lógica, orquestada por CrewAI (lento en CPU)")]:
        p = sub.add_parser(nombre, help=ayuda)
        p.add_argument("matricula", help="ej. A001")
        p.add_argument("-p", "--peticion", default="", help="preferencias en lenguaje natural")
        p.add_argument("--sin-llm", action="store_true", help="no usar Ollama (todo por reglas)")
        p.add_argument("--razonador", action="store_true", help="ejecutar HermiT (requiere Java)")
        p.add_argument("-q", "--silencioso", action="store_true", help="no mostrar mensajes del protocolo")
        if nombre == "crew":
            p.add_argument("--proceso", choices=["secuencial", "jerarquico"], default="secuencial")

    a = ap.parse_args()

    if a.cmd == "poblar":
        from carga.poblar import poblar
        poblar()
    elif a.cmd == "alumnos":
        from carga.kb import BaseConocimiento
        kb = BaseConocimiento()
        for m in kb.matriculas():
            e = kb.estudiante(m)
            print(f"{m}  {e.nombre:24} sem {e.semestre}  prom {e.promedio}  "
                  f"aprobadas {len(e.aprobadas):2}  reprobadas {list(e.reprobadas) or '-'}")
    elif a.cmd == "diagnostico":
        from carga.llm import diagnostico
        print("\n".join(diagnostico()))
    elif a.cmd == "demo":
        from carga.kb import BaseConocimiento
        from carga.llm import ClienteLLM
        from carga import sistema
        kb, llm = BaseConocimiento(), ClienteLLM(habilitado=False)
        ejemplos = {"A001": "", "A002": "quiero algo ligero, en la mañana y sin clases el viernes",
                    "A003": "quiero adelantar, en línea, me interesa IA y la nube, no quiero métodos numéricos"}
        for m, txt in ejemplos.items():
            s = sistema.nueva_sesion(m, txt, usar_llm=False, eco=False, kb=kb, llm=llm)
            sistema.correr_contract_net(s)
            sistema.correr_shapley(s)
            sistema.cerrar(s)
    elif a.cmd == "experimento":
        from carga import experimento
        from carga.kb import BaseConocimiento
        from carga.llm import ClienteLLM
        kb = BaseConocimiento()
        llm = ClienteLLM(habilitado=True) if a.llm else None
        if a.llm and not llm.disponible:
            print(f"⚠ Sin LLM: {llm.motivo}. Se corre el experimento sin el 'LLM solo'.")
        filas, resumen = experimento.correr(kb, a.n, a.semilla, llm)
        print("\n" + experimento.tabla_markdown(resumen, a.n, a.semilla))
        for r in experimento.guardar(filas, resumen, a.n, a.semilla):
            print(f" → {r.relative_to(kb_raiz())}")
    elif a.cmd == "recomendar":
        from carga.sistema import recomendar
        recomendar(a.matricula, a.peticion, usar_llm=not a.sin_llm,
                   razonador=a.razonador, eco=not a.silencioso)
    elif a.cmd == "crew":
        from carga.crew import ejecutar_crew
        ejecutar_crew(a.matricula, a.peticion, proceso=a.proceso,
                      usar_llm=not a.sin_llm, razonador=a.razonador)


def kb_raiz():
    from carga import config
    return config.RAIZ


if __name__ == "__main__":
    try:
        main()
    except KeyError as e:
        sys.exit(f"Error: {e.args[0]}")
    except KeyboardInterrupt:
        sys.exit("\nCancelado.")
