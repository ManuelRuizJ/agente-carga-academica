# -*- coding: utf-8 -*-
"""Configuración central. Todo se puede cambiar con variables de entorno."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_ONTO = RAIZ / "ontologia"
DIR_SALIDAS = RAIZ / "salidas"

ONTO_BASE = DIR_ONTO / "P2_ontologia_carga_academica.owx"      # TBox original (Proyecto 2)
ONTO_POBLADA = DIR_ONTO / "carga_academica_poblada.owl"         # TBox + ABox (generada)
NS = "http://www.ibero.mx/ontologias/carga-academica#"

# ---------------------------------------------------------------- LLM local
# Se usa un servidor de Ollama propio en el puerto 11435 levantado con
# ./iniciar_ollama_cpu.sh (GPU desactivada). Si no existe, se intenta 11434.
OLLAMA_URLS = [u for u in [os.getenv("OLLAMA_URL"),
                           "http://127.0.0.1:11435",
                           "http://127.0.0.1:11434"] if u]
MODELO = os.getenv("MODELO_LLM", "llama3.2")          # 3B: ~2 GB de RAM
# Pocos hilos: menos pico de consumo eléctrico y de temperatura (con 6 hilos
# la laptop llegó a apagarse en batería). 4 basta para llama3.2 (3B).
HILOS_LLM = int(os.getenv("HILOS_LLM", max(2, min(4, (os.cpu_count() or 4) // 2))))
CTX_LLM = int(os.getenv("CTX_LLM", "4096"))
TIMEOUT_LLM = int(os.getenv("TIMEOUT_LLM", "240"))

# ---------------------------------------------------------------- Evaluación
# Pesos de la función de evaluación del Proyecto 2 (sección 2.2)
PESOS = {
    "avance_academico": 0.30,
    "compatibilidad_horario": 0.25,
    "carga_equilibrada": 0.25,
    "preferencias": 0.20,
}

# Traducción de "tipo de carga" a metas concretas
# Calibrado al plan real de la Ibero (materias de 2 a 8 créditos, ~6 en
# promedio; el semestre ideal carga 32-42 créditos en 6-8 materias).
CARGA_TIPO = {
    "ligera": {"creditos": 30, "max_materias": 5, "max_dificiles": 2},
    "normal": {"creditos": 40, "max_materias": 7, "max_dificiles": 3},
    "pesada": {"creditos": 48, "max_materias": 8, "max_dificiles": 4},
}

# El plan real trae muchas optativas (13 de Reflexión Universitaria, 10 del
# Área Menor): sin un tope, una carga "pesada" se llena de optativas.
MAX_OPTATIVAS = 2         # optativas por periodo como máximo

TOP_COMBINACIONES = 6     # propuestas que el AgenteCarga envía en el Contract Net
MAX_CANDIDATAS = 12       # materias candidatas que se combinan como máximo
