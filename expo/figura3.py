# -*- coding: utf-8 -*-
"""
Fig. 3 del resumen para la Expo: puntuación media por sistema en el
experimento comparativo (mejora 2).

Lee los resultados ya guardados (no vuelve a correr el experimento):
    resultados/experimento_semilla7_llm.csv
y genera, a 300 dpi y 15 cm de ancho (lo que pide una figura impresa):
    expo/fig3_puntuacion_por_sistema.png
    expo/fig3_puntuacion_por_sistema.pdf   (vectorial, por si Word lo acepta)

Uso (con el python del sistema, que trae matplotlib):
    python3 expo/figura3.py
"""
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CSV = RAIZ / "resultados" / "experimento_semilla7_llm.csv"
SALIDA = RAIZ / "expo" / "fig3_puntuacion_por_sistema"

# Nombres cortos para la figura (mismos que la Tabla 1 del resumen)
NOMBRES = {
    "MAS (3 contratistas)": "MAS (3 contratistas)",
    "MAS (1 AgenteCarga, antes de la mejora 1)": "MAS (1 AgenteCarga)",
    "Solo CargaPreferencias": "Solo CargaPreferencias",
    "Solo CargaEquilibrio": "Solo CargaEquilibrio",
    "Solo CargaAvance": "Solo CargaAvance",
    "Monoagente simple (solo requisitos)": "Monoagente simple",
    "LLM solo (llama3.2)": "LLM sin agentes (llama3.2)",
}

# Colores: énfasis (el MAS en azul, el resto en gris) y tinta para textos
ACENTO = "#2a78d6"
GRIS = "#c3c2b7"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
REJILLA = "#e1e0d9"


def leer():
    puntos, invalidas = defaultdict(list), defaultdict(list)
    with open(CSV, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            puntos[fila["sistema"]].append(float(fila["puntuacion"]))
            invalidas[fila["sistema"]].append(int(fila["invalidas"]) > 0)
    return ({s: mean(v) for s, v in puntos.items()},
            {s: 100 * mean(v) for s, v in invalidas.items()}, len(next(iter(puntos.values()))))


def main():
    media, pct_inv, n = leer()
    orden = sorted(media, key=lambda s: media[s])          # el mayor queda arriba
    etiquetas = [NOMBRES.get(s, s) for s in orden]
    valores = [media[s] for s in orden]
    colores = [ACENTO if s == "MAS (3 contratistas)" else GRIS for s in orden]

    plt.rcParams.update({"font.family": "serif",
                         "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
                         "font.size": 9})
    fig, ax = plt.subplots(figsize=(15 / 2.54, 6.2 / 2.54), dpi=300)
    barras = ax.barh(etiquetas, valores, height=0.62, color=colores, zorder=2)

    for b, s, v in zip(barras, orden, valores):
        texto = f"{v:.2f}"
        if pct_inv[s] > 0:
            texto += f"   ({pct_inv[s]:.0f}% de las cargas con materias inválidas)"
        ax.text(v + 1.2, b.get_y() + b.get_height() / 2, texto, va="center", ha="left",
                color=TINTA if s == "MAS (3 contratistas)" else TINTA_2,
                fontweight="bold" if s == "MAS (3 contratistas)" else "normal", fontsize=8.5)

    ax.set_xlim(0, 100)
    ax.set_xlabel("Puntuación media según la función de evaluación (0–100)", color=TINTA_2)
    ax.set_title(f"{n} alumnos sintéticos · plan de estudios real", loc="left",
                 color=TINTA_2, fontsize=8.5)
    ax.grid(axis="x", color=REJILLA, linewidth=0.6, zorder=0)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.tick_params(axis="y", length=0, colors=TINTA)
    ax.tick_params(axis="x", colors=TINTA_2)
    fig.tight_layout()

    for ext in ("png", "pdf"):
        fig.savefig(f"{SALIDA}.{ext}", dpi=300, facecolor="white")
    print("✔", SALIDA.with_suffix(".png").relative_to(RAIZ), "y .pdf")
    for s in reversed(orden):
        print(f"  {NOMBRES.get(s, s):28} {media[s]:6.2f}   inválidas {pct_inv[s]:5.1f}%")


if __name__ == "__main__":
    main()
