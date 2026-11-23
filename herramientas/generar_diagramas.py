"""Genera los diagramas de diseño (PNG) usados en el documento (MVP, Hito 3).\nUso:  python herramientas/generar_diagramas.py\n"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

aqui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "documento", "img")
os.makedirs(aqui, exist_ok=True)
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


# ------------------------------------------------------------ Figura 1: arquitectura del MVP
fig, ax = plt.subplots(figsize=(10, 9.4), dpi=200)
ax.set_xlim(0, 20); ax.set_ylim(0, 19); ax.axis("off")

ax.text(0.2, 18.75, "Navegador (HTML + JavaScript, sin dependencias)", fontsize=10.5, fontweight="bold", color=NAVY, va="center")
ax.add_patch(FancyBboxPatch((0.2, 15.0), 19.6, 3.25, boxstyle="round,pad=0.02,rounding_size=0.15", fc="#F2F5F8", ec="#C9D3DD", lw=1))
caja(ax, 0.55, 15.25, 7.2, 2.75, "Asistente de 4 pasos", "1 Inicio (subir o usar ejemplo)\n2 Horario y créditos · 3 Trabajos\n4 Revisión y «Empezar mi semestre»", fc="white", fs=9.5)
caja(ax, 8.35, 15.25, 11.1, 2.75, "Panel del semestre", "Resumen · Calendario (semana y mes) · Trabajos (tablero)\nProgreso (horas, tareas, esfuerzo, rachas)\nAsistente personal (chat y recomendaciones) · Ajustes", fc="white", fs=9.5)
flecha(ax, 7.75, 16.6, 8.35, 16.6)

ax.text(5.0, 14.5, "JSON sobre HTTP:  /api/importar · /api/plan · /api/chat · /api/chat_llm · /api/ejemplo", ha="left", fontsize=8.4, color=GREY)
flecha(ax, 17.5, 15.0, 17.5, 13.55)

caja(ax, 0.2, 8.1, 4.6, 4.9, "Datos (JSON)", "materias y créditos\nbloques LEC / LAB\nlabs y entregas\ndisponibilidad\ntrabajos y hechas\nhistorial de horas reales\nsesiones y uso (progreso)\nperfil de estudio", fc=AMBER, fs=10)
ax.add_patch(FancyBboxPatch((5.4, 4.3), 14.4, 9.2, boxstyle="round,pad=0.02,rounding_size=0.15", fc="#EAF0F7", ec=NAVY, lw=1.6))
ax.text(5.7, 13.1, "Servidor local + motor (Python, biblioteca estándar)", fontsize=10.5, fontweight="bold", color=NAVY, va="center")
mods = [("Créditos\n→ horas", "48 h por crédito\nmeta de estudio"), ("Horario\n→ huecos", "paridad de labs,\nsalida e inicio\nde trabajo"),
        ("Planificador", "EDF con colchón\npor dificultad,\ntope diario"), ("Calibración", "aprende de las\nhoras reales\n(factor por tipo)"), ("Asesor", "recomendaciones\ncon fecha y\nacción concreta")]
for i, (t, d) in enumerate(mods):
    caja(ax, 5.7 + i * 2.8, 8.55, 2.6, 3.9, t, d, fc="#FBEFD5" if t in ("Calibración", "Asesor") else "white", fs=9.2)
    if i < 4:
        flecha(ax, 5.7 + i * 2.8 + 2.6, 10.5, 5.7 + (i + 1) * 2.8, 10.5)
flecha(ax, 4.8, 10.0, 5.4, 10.0)

caja(ax, 5.7, 4.6, 3.9, 3.25, "Progreso", "horas cumplidas vs.\nnecesarias, tareas,\nrachas de estudio y uso", fc="white", fs=9.2)
caja(ax, 10.0, 4.6, 4.9, 3.25, "Asistente (motor propio)", "intenciones por palabras clave\n12 métodos con evidencia\nentrevista de 5 preguntas", fc="#FBEFD5", fs=9.2)
ax.add_patch(FancyBboxPatch((15.3, 4.6), 4.2, 3.25, boxstyle="round,pad=0.02,rounding_size=0.12", fc="white", ec=GREY, lw=1.4, ls="--"))
ax.text(17.4, 7.65, "Modelo local\n(opcional)", ha="center", va="top", fontsize=9.2, fontweight="bold", color=INK)
ax.text(17.4, 6.45, "Ollama · qwen2.5:3b\n(red neuronal tipo\ntransformer); solo redacta\npreguntas abiertas", ha="center", va="top", fontsize=7.4, color=GREY, linespacing=1.4)
flecha(ax, 14.9, 6.2, 15.3, 6.2, color=GREY)
flecha(ax, 9.6, 6.2, 10.0, 6.2)
flecha(ax, 12.45, 8.55, 12.45, 7.85)

caja(ax, 5.4, 0.3, 14.4, 2.5, "Salida", "bloques con fecha, hora, materia y motivo · advertencias\nresumen semanal · indicadores · recomendaciones\nestadísticas de progreso · respuestas del asistente", fc=SAGE_L, ec="#7FA35E", fs=10)
flecha(ax, 12.6, 4.3, 12.6, 2.8)
caja(ax, 0.2, 0.3, 4.6, 2.5, "Verificación", "74 pruebas automáticas\nevaluación con casos y\nsimulación (300 escenarios)", fc=ROSE, ec="#C98A82", fs=9.5)
flecha(ax, 4.8, 1.55, 5.4, 1.55, color="#C98A82")

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
ax.text(10.0, 12.75, "Cada vez que el estudiante marca una tarea como hecha o cambia un dato, se recalcula todo el plan (≈3 ms por plan).",
        ha="center", fontsize=9, color=GREY)
ax.text(7.0, 2.25, "Las pasadas 1 y 2 usan los mismos huecos:\nprimero se ubican las entregas y solo después\nel estudio independiente.", ha="left", va="center", fontsize=9, color=GREY, linespacing=1.5)
fig.savefig(os.path.join(aqui, "algoritmo.png"), bbox_inches="tight", facecolor="white")
plt.close(fig)
print("ok")
