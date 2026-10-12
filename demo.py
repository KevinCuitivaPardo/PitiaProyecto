"""Demo en consola: genera el plan recomendado con el horario real del equipo.

Uso:  python demo.py [archivo.json] [YYYY-MM-DD HH:MM]
"""
import sys
from datetime import datetime, date

from motor.semestria import (DIAS, cargar, planificar, fecha, horas_independientes,
                             contacto_semanal_min, horas_totales_semana, creditos_de,
                             semana_del_semestre, paridad)

ruta = sys.argv[1] if len(sys.argv) > 1 else "datos/horario_ejemplo.json"
ahora = datetime.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else datetime(2026, 10, 12, 9, 0)
datos = cargar(ruta)

sem = semana_del_semestre(ahora.date(), fecha(datos["semestre_inicio"]))
print(f"Hoy: {DIAS[ahora.weekday()]} {ahora:%d/%m/%Y %H:%M} - semana {sem} del semestre ({paridad(sem)})\n")

print("== Créditos -> tiempo ==")
print(f"{'Materia':<15}{'Créd':>5}{'Total h/sem':>13}{'En clase':>10}{'Independ.':>11}")
for m in datos["materias"]:
    c = m["codigo"]
    print(f"{c:<15}{creditos_de(c, datos):>5}{horas_totales_semana(creditos_de(c, datos)):>13.1f}"
          f"{contacto_semanal_min(c, datos) / 60:>10.1f}{horas_independientes(c, datos):>11.1f}")

plan = planificar(datos, ahora)
print("\n== Plan recomendado ==")
dia_actual = None
for b in plan["bloques"]:
    if b["fecha"] != dia_actual:
        dia_actual = b["fecha"]
        f = fecha(dia_actual)
        print(f"\n{DIAS[f.weekday()]} {f:%d/%m}")
    marca = "TAREA " if b["tipo"] == "tarea" else "estudio"
    print(f"  {b['inicio']}-{b['fin']}  [{marca}] {b['titulo']}")

print("\n== Advertencias ==")
for a in plan["advertencias"] or [{"mensaje": "Ninguna: todas las tareas caben antes de su entrega."}]:
    print(" -", a["mensaje"])
