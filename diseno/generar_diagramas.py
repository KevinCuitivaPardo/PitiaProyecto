"""Genera los diagramas de diseño (PNG) usados en el documento del Hito 2.
Uso:  python diseno/generar_diagramas.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

aqui = os.path.dirname(os.path.abspath(__file__))
NAVY, SAGE, SAGE_L, AMBER, ROSE, LAV, INK, GREY = "#1E3A5F", "#C6DEAB", "#E4F0D6", "#F7E8C3", "#F7D9D4", "#DFE3F2", "#16202B", "#6B7A89"
plt.rcParams["font.family"] = "DejaVu Sans"


def caja(ax, x, y, w, h, titulo, detalle=None, fc="white", ec=NAVY, tc=INK, bold=True, fs=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=ec, lw=1.4))
    if detalle:
        lineas = titulo.count("\n") + 1
        ax.text(x + w / 2, y + h - 0.2, titulo, ha="center", va="top", fontsize=fs, fontweight="bold" if bold else "normal", color=tc, linespacing=1.15)
        ax.text(x + w / 2, y + h - 0.3 - 0.46 * lineas - 0.18, detalle, ha="center", va="top", fontsize=fs - 1.6, color=GREY if fc == "white" else INK, linespacing=1.4)
    else:
        ax.text(x + w / 2, y + h / 2, titulo, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", color=tc)


def flecha(ax, x1, y1, x2, y2, color=NAVY, rad=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14, color=color, lw=1.5,
                                 connectionstyle=f"arc3,rad={rad}", shrinkA=2, shrinkB=2))


# ------------------------------------------------------------ Figura 1: arquitectura
fig, ax = plt.subplots(figsize=(10, 6.4), dpi=200)
ax.set_xlim(0, 20); ax.set_ylim(0, 12.8); ax.axis("off")

ax.text(0.2, 12.35, "Interfaz (prototipo web: HTML + JavaScript)", fontsize=10.5, fontweight="bold", color=NAVY, va="center")
ax.add_patch(FancyBboxPatch((0.2, 9.0), 19.6, 2.95, boxstyle="round,pad=0.02,rounding_size=0.15", fc="#F2F5F8", ec="#C9D3DD", lw=1))
pant = [("1. Horario", "subir y leer\nlos bloques"), ("2. Créditos y\ndisponibilidad", "hora de salida e\ninicio de trabajo"),
        ("3. Labs y\nentregas", "frecuencia y semanas\npares / impares"), ("4. Trabajos", "proyectos, parciales\ny dificultad"), ("5. Mi semana", "plan, motivos y\nmarcar como hecho")]
for i, (t, d) in enumerate(pant):
    caja(ax, 0.55 + i * 3.88, 9.25, 3.45, 2.45, t, d, fc="white", fs=9.5)
    if i < 4:
        flecha(ax, 0.55 + i * 3.88 + 3.45, 10.47, 0.55 + (i + 1) * 3.88, 10.47)

caja(ax, 0.2, 4.7, 5.3, 3.2, "Modelo de datos (JSON)", "materias y créditos\nbloques LEC / LAB\nlabs y entregas\ndisponibilidad\ntrabajos y tareas hechas", fc=AMBER, fs=10)
flecha(ax, 2.85, 9.0, 2.85, 7.9)
ax.text(3.05, 8.45, "lee y escribe", fontsize=8, color=GREY, va="center")

ax.add_patch(FancyBboxPatch((6.1, 3.7), 13.7, 4.6, boxstyle="round,pad=0.02,rounding_size=0.15", fc="#EAF0F7", ec=NAVY, lw=1.6))
ax.text(6.4, 7.95, "Motor de recomendación (Python · réplica en JavaScript)", fontsize=10.5, fontweight="bold", color=NAVY, va="center")
mods = [("Créditos\n→ horas", "48 h por crédito\nmeta de estudio =\ntotal − clase"), ("Horario\n→ huecos", "paridad de labs,\nsalida y hora de\ninicio de trabajo"),
        ("Entregas\nautomáticas", "informes de lab y\ntalleres según las\nrespuestas"), ("Planificador", "EDF con colchón\npor dificultad,\ntope diario y\nmodo urgente")]
for i, (t, d) in enumerate(mods):
    caja(ax, 6.4 + i * 3.4, 4.0, 3.1, 3.5, t, d, fc="white", fs=9.5)
    if i < 3:
        flecha(ax, 6.4 + i * 3.4 + 3.1, 5.75, 6.4 + (i + 1) * 3.4, 5.75)
flecha(ax, 5.5, 6.3, 6.1, 6.3)

caja(ax, 6.1, 0.4, 13.7, 2.5, "Salida del motor", "bloques recomendados con fecha, hora, materia, dificultad y su motivo\nresumen semanal por materia y advertencias\n(«no alcanza el tiempo», «vencida»)\nSe muestra en la pantalla «Mi semana»", fc=SAGE_L, ec="#7FA35E", fs=10)
flecha(ax, 12.95, 3.7, 12.95, 2.9)

caja(ax, 0.2, 0.4, 5.3, 2.5, "Verificación", "24 pruebas unitarias\ncruce JS ↔ Python (7 escenarios)\nprueba de interfaz en Chromium", fc=ROSE, ec="#C98A82", fs=10)
flecha(ax, 5.5, 1.65, 6.1, 1.65, color="#C98A82")

fig.savefig(os.path.join(aqui, "arquitectura.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)

# ------------------------------------------------------------ Figura 2: algoritmo (serpentina)
fig, ax = plt.subplots(figsize=(10, 6.6), dpi=200)
ax.set_xlim(0, 20); ax.set_ylim(0, 13.2); ax.axis("off")
pasos = [
    ("1", "Leer datos", "horario fijo, créditos,\ndisponibilidad y trabajos"),
    ("2", "Calcular metas", "independiente = créditos × 3 h\n− horas en clase (un lab\nquincenal cuenta la mitad)"),
    ("3", "Entregas automáticas", "un informe por cada sesión de\nlab y un taller por clase,\nsin empezar antes de la sesión"),
    ("4", "Calcular huecos diarios", "complemento de las clases;\ntras la salida, solo desde la\nhora de inicio de trabajo"),
    ("5", "Pasada 1: tareas (EDF)", "orden: fecha límite menos\ncolchón (0/1/2 días según\ndificultad); tope de 2 h por\ntarea y día (4 h si urge)"),
    ("6", "Pasada 2: estudio", "con el tiempo que sobra rellena\nla meta semanal de cada\nmateria (mayor déficit primero)"),
    ("7", "Explicar y advertir", "cada bloque lleva su motivo;\nsi una tarea no cabe, avisa\ncuántas horas faltan"),
]
W, H = 6.0, 3.5
pos = [(0.3, 8.9), (7.0, 8.9), (13.7, 8.9), (13.7, 4.7), (7.0, 4.7), (0.3, 4.7), (0.3, 0.5)]
cols = ["white", "white", "white", "white", AMBER, AMBER, SAGE_L]
for (n, t, d), (x, y), fc in zip(pasos, pos, cols):
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.02,rounding_size=0.14", fc=fc, ec=NAVY, lw=1.4))
    ax.add_patch(plt.Circle((x + 0.65, y + H - 0.7), 0.42, fc=NAVY, ec=NAVY))
    ax.text(x + 0.65, y + H - 0.7, n, color="white", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(x + 1.3, y + H - 0.7, t, ha="left", va="center", fontsize=9.4, fontweight="bold", color=INK)
    ax.text(x + 0.35, y + H - 1.45, d, ha="left", va="top", fontsize=8.6, color=INK, linespacing=1.45)
flecha(ax, 6.3, 10.65, 7.0, 10.65)                 # 1 -> 2
flecha(ax, 13.0, 10.65, 13.7, 10.65)               # 2 -> 3
flecha(ax, 16.7, 8.9, 16.7, 8.2)                   # 3 -> 4
flecha(ax, 13.7, 6.45, 13.0, 6.45)                 # 4 -> 5
flecha(ax, 7.0, 6.45, 6.3, 6.45)                   # 5 -> 6
flecha(ax, 3.3, 4.7, 3.3, 4.0)                     # 6 -> 7
ax.text(10.0, 12.75, "Cada vez que el estudiante marca una tarea como hecha o cambia un dato, se recalcula todo el plan (≈3 ms).",
        ha="center", fontsize=9, color=GREY)
ax.text(7.0, 2.25, "Las pasadas 1 y 2 usan los mismos huecos:\nprimero se ubican las entregas y solo después\nel estudio independiente.", ha="left", va="center", fontsize=9, color=GREY, linespacing=1.5)
fig.savefig(os.path.join(aqui, "algoritmo.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)
print("ok")
