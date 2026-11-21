"""Convierte resultados/evaluacion.json en tablas y macros de LaTeX (documento/auto/).
Así los números del texto del documento salen siempre de la última evaluación y no se transcriben a mano.

Uso:  python pruebas/evaluacion.py --figuras && python documento/generar_tablas.py
"""
import io
import json
import os
import re
import sys
import unittest

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.join(aqui, "..")
sys.path.insert(0, raiz)
R = json.load(open(os.path.join(raiz, "resultados", "evaluacion.json"), encoding="utf-8"))
SIM, CAL = R["simulacion"], R["calibracion"]
AUTO = os.path.join(aqui, "auto")
os.makedirs(AUTO, exist_ok=True)


def tex(s):
    s = re.sub(r"(?<=\d)\.(?=\d)", ",", str(s))                      # decimales a la española
    s = s.replace("\\", "\\textbackslash{}")
    for ch in "&%$#_":
        s = s.replace(ch, "\\" + ch)
    s = s.replace("<=", "$\\leq$").replace(">=", "$\\geq$").replace(" < ", " $<$ ").replace(" > ", " $>$ ")
    s = re.sub(r"^<\s", "$<$ ", s)
    s = s.replace("×", "$\\times$").replace("→", "$\\rightarrow$")
    return s


def escribir(nombre, contenido):
    with open(os.path.join(AUTO, nombre), "w", encoding="utf-8") as f:
        f.write(contenido)


COL = r">{\raggedright\arraybackslash}X >{\raggedright\arraybackslash}p{3.3cm} >{\raggedright\arraybackslash}p{3.3cm} c"


def tabla_caso(c):
    filas = "\n".join(f"{tex(a)} & {tex(b)} & {tex(o)} & {'Sí' if ok else 'No'} \\\\" for a, b, o, ok in c["chequeos"])
    return (f"\\textbf{{Entrada.}} {tex(c['entrada'])}\n\n\\begin{{table}}[H]\n\\centering\\small\n"
            f"\\caption{{Caso {c['id']}: {tex(c['nombre'])}}}\\label{{tab:{c['id'].lower()}}}\n"
            f"\\begin{{tabularx}}{{\\textwidth}}{{{COL}}}\n\\toprule\nComprobación & Esperado & Obtenido & ¿Cumple? \\\\\n\\midrule\n{filas}\n"
            "\\bottomrule\n\\end{tabularx}\n\\end{table}\n")


# ---- número de pruebas automáticas y resultado
suite = unittest.defaultTestLoader.discover(os.path.join(raiz, "pruebas"), pattern="test_*.py")
res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
n_pruebas, n_fallas = res.testsRun, len(res.failures) + len(res.errors)

for c in R["casos"]:
    escribir(f"tabla_{c['id'].lower()}.tex", tabla_caso(c))

E, U = SIM["edf"], SIM["ultimo"]
red_colchon = 100 * (1 - E["pct_sin_colchon"] / U["pct_sin_colchon"])
filas = [("Trabajos con tiempo asegurado (\\%)", U["pct_cubiertas"], E["pct_cubiertas"]),
         ("Días con más de 6 h de trabajo, por escenario", U["dias_sobrecargados_por_escenario"], E["dias_sobrecargados_por_escenario"]),
         ("Máximo de horas en un día (promedio)", U["max_h_dia_media"], E["max_h_dia_media"]),
         ("Trabajos terminados el mismo día de la entrega (\\%)", U["pct_sin_colchon"], E["pct_sin_colchon"]),
         ("Anticipación media respecto a la entrega (días)", U["anticipacion_media_dias"], E["anticipacion_media_dias"])]
escribir("tabla_comparacion.tex", "\\begin{table}[H]\n\\centering\\small\n\\caption{Comparación contra la estrategia de último momento (" + str(SIM["escenarios"]) +
         " escenarios)}\\label{tab:comparacion}\n\\begin{tabular}{lrr}\n\\toprule\nMétrica & Último momento & SemestrIA \\\\\n\\midrule\n" +
         "\n".join(f"{n} & {tex(u)} & {tex(e)} \\\\" for n, u, e in filas) + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")

escribir("tabla_calibracion.tex", "\\begin{table}[H]\n\\centering\\small\n\\caption{Error de estimación con y sin calibración (usuarios simulados)}\\label{tab:calibracion}\n"
         "\\begin{tabular}{rrrr}\n\\toprule\nRitmo real vs. base & Error base (h) & Error calibrado (h) & Reducción \\\\\n\\midrule\n" +
         "\n".join(f"{float(k):g}$\\times$ & {tex(v['mae_sin_h'])} & {tex(v['mae_con_h'])} & {tex(v['reduccion_pct'])}\\,\\% \\\\" for k, v in CAL["por_ritmo"].items()) +
         "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n")

sesgados = [CAL["por_ritmo"][k]["reduccion_pct"] for k in ("0.6", "0.8", "1.3", "1.6", "2.0")]
objetivos = [
    ("OC1", "Restricciones duras violadas en los escenarios simulados", "0", f"{sum(SIM['violaciones'].values())}", sum(SIM["violaciones"].values()) == 0),
    ("OC2", "Fallas silenciosas (trabajo sin tiempo completo y sin advertencia)", "0", f"{SIM['violaciones'].get('falla_silenciosa', 0)}", SIM["violaciones"].get("falla_silenciosa", 0) == 0),
    ("OC3", "Tiempo de planificación, percentil 95", "<= 100 ms", f"{SIM['ms_por_plan_p95']} ms", SIM["ms_por_plan_p95"] <= 100),
    ("OC4", "Días con más de 6 h de trabajo (vs. último momento)", "0", f"{E['dias_sobrecargados_total']}", E["dias_sobrecargados_total"] == 0),
    ("OC5", "Reducción de trabajos terminados el día de la entrega", ">= 50 %", f"{red_colchon:.1f} %", red_colchon >= 50),
    ("OC6", "Trabajos con tiempo asegurado en escenarios aleatorios", ">= 95 %", f"{SIM['pct_tareas_cubiertas']} %", SIM["pct_tareas_cubiertas"] >= 95),
    ("OC7", "Reducción del error de estimación (ritmo real distinto de la base en al menos 20 %)", ">= 25 %", f"{min(sesgados)} % a {max(sesgados)} %", min(sesgados) >= 25),
    ("OC8", "Pruebas automáticas que pasan", "100 %", f"{n_pruebas - n_fallas} de {n_pruebas}", n_fallas == 0),
]
escribir("tabla_objetivos.tex", "\\begin{table}[H]\n\\centering\\small\n\\caption{Cumplimiento de los criterios de aceptación del MVP}\\label{tab:objetivos}\n"
         "\\begin{tabularx}{\\textwidth}{l >{\\raggedright\\arraybackslash}X r r c}\n\\toprule\n & Criterio & Umbral & Resultado & ¿Cumple? \\\\\n\\midrule\n" +
         "\n".join(f"{i} & {tex(c)} & {tex(u)} & {tex(r)} & {'Sí' if ok else 'No'} \\\\" for i, c, u, r, ok in objetivos) +
         "\n\\bottomrule\n\\end{tabularx}\n\\end{table}\n")

# ---- ejemplo del plan real (caso base): primeros días
from datetime import datetime
from motor.semestria import cargar, fecha, planificar
_plan = planificar(cargar(os.path.join(raiz, "datos", "horario_ejemplo.json")), datetime(2026, 10, 12, 9, 0))
_dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_filas = []
for b in [b for b in _plan["bloques"] if b["fecha"] in ("2026-10-12", "2026-10-13")]:
    f = fecha(b["fecha"])
    _filas.append(f"{_dias[f.weekday()]} {f.day}/{f.month:02d} & {b['inicio']}--{b['fin']} & {tex(b['titulo'])} & {tex(b['motivo'])} \\\\")
_COLP = r">{\raggedright\arraybackslash}p{4.6cm} >{\raggedright\arraybackslash}X"
_cuerpo = "\n".join(_filas)
escribir("tabla_ejemplo_plan.tex",
         "\\begin{table}[H]\n\\centering\\footnotesize\n"
         "\\caption{Ejemplo del plan generado para el lunes 12 y el martes 13 de octubre (caso base); cada bloque lleva su motivo}\\label{tab:ejemplo}\n"
         "\\begin{tabularx}{\\textwidth}{l l " + _COLP + "}\n\\toprule\nDía & Hora & Bloque & Motivo \\\\\n\\midrule\n"
         + _cuerpo + "\n\\bottomrule\n\\end{tabularx}\n\\end{table}\n")

tasa = lambda a, b: f"{a:.1f}".replace(".", ",")
macros = {
    "resEscenarios": SIM["escenarios"], "resTareas": SIM["tareas_totales"], "resPctCub": tasa(SIM["pct_tareas_cubiertas"], 0),
    "resPctCubUlt": tasa(U["pct_cubiertas"], 0), "resViol": sum(SIM["violaciones"].values()),
    "resCompletos": SIM["escenarios_completos"], "resConAdv": SIM["escenarios_con_advertencia"],
    "resMsMedia": str(SIM["ms_por_plan_media"]).replace(".", ","), "resMsPNov": str(SIM["ms_por_plan_p95"]).replace(".", ","),
    "resMsMax": str(SIM["ms_por_plan_max"]).replace(".", ","),
    "resDiasSobreUlt": str(U["dias_sobrecargados_por_escenario"]).replace(".", ","), "resDiasSobreEdf": str(E["dias_sobrecargados_por_escenario"]).replace(".", ","),
    "resMaxUlt": str(U["max_h_dia_media"]).replace(".", ","), "resMaxEdf": str(E["max_h_dia_media"]).replace(".", ","),
    "resColUlt": str(U["pct_sin_colchon"]).replace(".", ","), "resColEdf": str(E["pct_sin_colchon"]).replace(".", ","),
    "resRedCol": f"{red_colchon:.0f}", "resAntUlt": str(U["anticipacion_media_dias"]).replace(".", ","), "resAntEdf": str(E["anticipacion_media_dias"]).replace(".", ","),
    "resRedCalMedia": str(CAL["reduccion_media_pct"]).replace(".", ","), "resRedCalSes": str(CAL["reduccion_media_sesgados_pct"]).replace(".", ","),
    "resCalUno": str(CAL["por_ritmo"]["1.0"]["reduccion_pct"]).replace(".", ","),
    "resCalUnoAbs": str(abs(CAL["por_ritmo"]["1.0"]["reduccion_pct"])).replace(".", ","),
    "resUsuarios": CAL["usuarios_por_ritmo"], "resPruebas": n_pruebas,
    "resFactorTaller": str(R["casos"][4]["datos_extra"]["factor_taller"]).replace(".", ","),
    "resBloquesBase": R["casos"][0]["datos_extra"]["bloques"], "resHTareasBase": str(R["casos"][0]["datos_extra"]["horas_tareas"]).replace(".", ","),
    "resHEstudioBase": str(R["casos"][0]["datos_extra"]["horas_estudio"]).replace(".", ","),
    "resFaltanImposible": str(R["casos"][1]["datos_extra"]["faltan_h"]).replace(".", ","),
}
escribir("numeros.tex", "% Generado por documento/generar_tablas.py: no editar a mano.\n" +
         "\n".join(f"\\newcommand{{\\{k}}}{{{v}}}".replace("resMsPNov", "resMsPNov") for k, v in macros.items()) + "\n")
print(f"ok: {n_pruebas} pruebas ({n_fallas} fallas); objetivos cumplidos: {sum(o[4] for o in objetivos)}/{len(objetivos)}")
