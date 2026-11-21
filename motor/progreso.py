"""SemestrIA - estadísticas de progreso del estudiante.

Se alimentan de lo que el estudiante registra en la interfaz (todo vive en el archivo de datos):
  sesiones      [{fecha, min, materia, titulo, tipo, tarea_id}]  bloques cumplidos o horas reales anotadas
  hechas_fecha  {id_de_tarea: fecha}                              cuándo se terminó cada trabajo
  uso           [fecha, ...]                                      días en que abrió la aplicación

"Necesario" es la meta de estudio independiente que sale de los créditos (3 h por crédito y semana menos las
horas en clase); "planeado" es lo que el plan le propone esa semana; "cumplido" es lo que registró.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from .semestria import fecha, horas_independientes

SEMANAS_GRAFICA = 8
DIAS_MAPA = 35


def _lunes(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _fechas_validas(valores) -> set[date]:
    res = set()
    for v in valores or []:
        try:
            res.add(fecha(v))
        except (TypeError, ValueError):
            pass
    return res


def rachas(dias_activos: set[date], hoy: date) -> tuple[int, int]:
    """(racha actual, mejor racha). La actual no se rompe si hoy todavía no tiene actividad: cuenta desde ayer."""
    d = hoy if hoy in dias_activos else hoy - timedelta(days=1)
    actual = 0
    while d in dias_activos:
        actual += 1
        d -= timedelta(days=1)
    mejor = corrida = 0
    previo = None
    for d in sorted(dias_activos):
        corrida = corrida + 1 if previo and (d - previo).days == 1 else 1
        mejor = max(mejor, corrida)
        previo = d
    return actual, mejor


def estadisticas(datos: dict, plan: dict, ahora: datetime) -> dict:
    hoy = ahora.date()
    sesiones = []
    for s in datos.get("sesiones") or []:
        try:
            fecha(s["fecha"])
            if float(s["min"]) > 0:
                sesiones.append(s)
        except (KeyError, TypeError, ValueError):
            continue
    por_dia: dict[date, float] = defaultdict(float)
    por_materia_sem: dict[str, float] = defaultdict(float)
    lun_actual = _lunes(hoy)
    for s in sesiones:
        d = fecha(s["fecha"])
        por_dia[d] += float(s["min"])
        if _lunes(d) == lun_actual:
            por_materia_sem[s.get("materia", "")] += float(s["min"])

    materias = [m["codigo"] for m in datos.get("materias", [])]
    meta_materia = {m: horas_independientes(m, datos) for m in materias}
    necesario_h = sum(meta_materia.values())

    hechas_f = {k: fecha(v) for k, v in (datos.get("hechas_fecha") or {}).items() if _valida(v)}
    inicio_sem = _lunes(fecha(datos["semestre_inicio"]))
    primera = max(inicio_sem, lun_actual - timedelta(weeks=SEMANAS_GRAFICA - 1))
    semanas = []
    lun = primera
    while lun <= lun_actual:
        fin = lun + timedelta(days=6)
        semanas.append({
            "lunes": lun.isoformat(),
            "cumplido_h": round(sum(m for d, m in por_dia.items() if lun <= d <= fin) / 60, 1),
            "necesario_h": round(necesario_h, 1),
            "tareas_hechas": sum(1 for d in hechas_f.values() if lun <= d <= fin),
        })
        lun += timedelta(days=7)

    fin_sem = lun_actual + timedelta(days=6)
    hechos = {(s["fecha"], s.get("inicio"), s.get("materia"), s.get("titulo")) for s in sesiones if s.get("inicio")}
    restante = sum((_min(b) for b in plan["bloques"] if hoy <= fecha(b["fecha"]) <= fin_sem
                    and (b["fecha"], b["inicio"], b["materia"], b["titulo"]) not in hechos), 0) / 60   # los cumplidos ya están en «cumplido»
    cumplido_sem = semanas[-1]["cumplido_h"] if semanas else 0.0
    planeado_sem = round(cumplido_sem + restante, 1)

    actividad = {d for d, m in por_dia.items() if m > 0} | set(hechas_f.values())
    racha_estudio, mejor_estudio = rachas(actividad, hoy)
    racha_uso, mejor_uso = rachas(_fechas_validas(datos.get("uso")) | ({hoy} if datos.get("uso") else set()), hoy)

    pendientes = len(plan["tareas"])
    hechas = len(datos.get("hechas", []))
    total_h = sum(por_dia.values()) / 60
    dias_act = sum(1 for m in por_dia.values() if m > 0)
    ultimos7 = [por_dia.get(hoy - timedelta(days=i), 0) for i in range(7)]
    return {
        "semana": {
            "cumplido_h": cumplido_sem, "planeado_h": planeado_sem, "necesario_h": round(necesario_h, 1),
            "restante_h": round(restante, 1),
            "pct_planeado": round(100 * cumplido_sem / planeado_sem) if planeado_sem else 0,
            "pct_necesario": round(100 * cumplido_sem / necesario_h) if necesario_h else 0,
        },
        "semanas": semanas,
        "dias": [{"fecha": (hoy - timedelta(days=i)).isoformat(), "h": round(por_dia.get(hoy - timedelta(days=i), 0) / 60, 2)}
                 for i in range(DIAS_MAPA - 1, -1, -1)],
        "por_materia": [{"materia": m, "cumplido_h": round(por_materia_sem.get(m, 0) / 60, 1), "meta_h": round(meta_materia[m], 1)} for m in materias],
        "tareas": {"hechas": hechas, "pendientes": pendientes, "pct": round(100 * hechas / (hechas + pendientes)) if hechas + pendientes else 0},
        "racha_estudio": racha_estudio, "mejor_racha_estudio": mejor_estudio,
        "racha_uso": racha_uso, "mejor_racha_uso": mejor_uso,
        "total_h": round(total_h, 1), "dias_activos": dias_act,
        "promedio_dia_activo_h": round(total_h / dias_act, 1) if dias_act else 0.0,
        "promedio_7d_h": round(sum(ultimos7) / 60 / 7, 1),
        "hay_datos": bool(sesiones or hechas_f),
    }


def _valida(v) -> bool:
    try:
        fecha(v)
        return True
    except (TypeError, ValueError):
        return False


def _min(b) -> int:
    h, m = b["inicio"].split(":")
    h2, m2 = b["fin"].split(":")
    return (int(h2) * 60 + int(m2)) - (int(h) * 60 + int(m))
