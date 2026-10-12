"""Genera escenarios de referencia con el motor Python para cruzarlos con el motor JS.
Uso:  python pruebas/exportar_escenarios.py > /tmp/escenarios.json
"""
import copy, json, os, sys
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from motor.semestria import cargar, planificar

base = cargar(os.path.join(os.path.dirname(__file__), "..", "datos", "horario_ejemplo.json"))

def escenario(nombre, ahora, mod=None):
    d = copy.deepcopy(base)
    if mod:
        mod(d)
    plan = planificar(d, ahora)
    return {"nombre": nombre, "datos": d, "fecha": ahora.date().isoformat(),
            "min": ahora.hour * 60 + ahora.minute, "plan": plan}

def con_hechas(d):
    d["hechas"] = ["m1", "lab:ISIS ARSW:2026-10-09"]

def imposible(d):
    d["trabajos"].append({"id": "x1", "materia": "ISIS ARSW", "tipo": "Proyecto", "titulo": "Entrega imposible",
                          "entrega": "2026-10-13", "dificultad": "Difícil", "horas": 40})

def sin_huecos(d):
    d["disponibilidad"]["6"] = {"disponible": True, "inicio_trabajo": "10:00"}
    d["disponibilidad"]["2"]["inicio_trabajo"] = "18:30"

def mas_creditos(d):
    for m in d["materias"]:
        m["creditos"] += 1

esc = [
    escenario("lunes_9am_semana_par", datetime(2026, 10, 12, 9, 0)),
    escenario("jueves_noche_semana_par", datetime(2026, 10, 15, 18, 40)),
    escenario("lunes_semana_impar", datetime(2026, 10, 19, 7, 0)),
    escenario("con_tareas_hechas", datetime(2026, 10, 12, 9, 0), con_hechas),
    escenario("entrega_imposible", datetime(2026, 10, 12, 9, 0), imposible),
    escenario("domingo_descanso_activado_y_tarde", datetime(2026, 10, 14, 16, 15), sin_huecos),
    escenario("mas_creditos", datetime(2026, 10, 13, 8, 0), mas_creditos),
]
json.dump(esc, sys.stdout, ensure_ascii=False)
