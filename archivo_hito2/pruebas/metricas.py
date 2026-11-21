"""Métricas reales del motor sobre el horario del equipo (alimentan el análisis de resultados).
Uso:  python pruebas/metricas.py
"""
import copy, os, sys, time, json
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from motor.semestria import a_min, cargar, planificar, fecha, horas_independientes

base = cargar(os.path.join(os.path.dirname(__file__), "..", "datos", "horario_ejemplo.json"))
ahora = datetime(2026, 10, 12, 9, 0)
plan = planificar(base, ahora)

tareas = plan["tareas"]
completas = [t for t in tareas if sum(a_min(b["fin"]) - a_min(b["inicio"]) for b in plan["bloques"] if b["tarea_id"] == t["id"]) == t["min"]]
por_dia = {}
for b in plan["bloques"]:
    por_dia[b["fecha"]] = por_dia.get(b["fecha"], 0) + a_min(b["fin"]) - a_min(b["inicio"])
parcial = [b for b in plan["bloques"] if b["tarea_id"] == "m1"]
dias_parcial = sorted({b["fecha"] for b in parcial})
h_tareas = sum(a_min(b["fin"]) - a_min(b["inicio"]) for b in plan["bloques"] if b["tipo"] == "tarea") / 60
h_estudio = sum(a_min(b["fin"]) - a_min(b["inicio"]) for b in plan["bloques"] if b["tipo"] == "estudio") / 60

t0 = time.perf_counter()
N = 200
for _ in range(N):
    planificar(base, ahora)
ms = (time.perf_counter() - t0) / N * 1000

m = {
    "bloques": len(plan["bloques"]), "tareas": len(tareas), "tareas_completas": len(completas),
    "pct_tareas": round(100 * len(completas) / len(tareas), 1), "advertencias": len(plan["advertencias"]),
    "max_h_dia": round(max(por_dia.values()) / 60, 1), "dias_con_plan": len(por_dia),
    "parcial_dias": len(dias_parcial), "parcial_fechas": dias_parcial,
    "h_tareas": round(h_tareas, 1), "h_estudio": round(h_estudio, 1),
    "horizonte": plan["horizonte"], "ms_por_plan": round(ms, 2),
    "indep": {mm["codigo"]: round(horas_independientes(mm["codigo"], base), 2) for mm in base["materias"]},
}
print(json.dumps(m, ensure_ascii=False, indent=1))
json.dump(m, open("/tmp/metricas.json", "w"), ensure_ascii=False)
