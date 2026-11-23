"""Evaluación del MVP de SemestrIA (Hito 3). Genera los números que usa el documento.

Uso:  python pruebas/evaluacion.py            -> resultados/evaluacion.json, resultados/evaluacion.md
      python pruebas/evaluacion.py --figuras  -> además, documento/img/fig_*.png (requiere matplotlib)

Tres bloques:
  A. Casos de prueba con entradas y salidas esperadas vs. obtenidas (datos reales del estudiante).
  B. Simulación de N escenarios aleatorios: (1) verificación de restricciones duras del plan y
     (2) comparación contra una estrategia de "último momento" sin topes ni colchón.
  C. Calibración: usuarios simulados con distinto ritmo real; error de estimación con y sin aprendizaje.
Todo es determinista (semilla fija) para que los resultados se puedan reproducir.
"""
from __future__ import annotations

import copy
import json
import math
import os
import random
import statistics
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(QUI, ".."))

from motor.calibracion import factor_calibracion
from motor.semestria import (Config, FACTOR_DIFICULTAD, HORAS_BASE, MARGEN_DIAS, _restar, a_hhmm, a_min, bloques_del_dia,
                             cargar, fecha, planificar, ventanas_libres)

SEMILLA = 2026
N_ESCENARIOS = 300
N_USUARIOS = 200
AHORA = datetime(2026, 10, 12, 9, 0)
BASE = cargar(os.path.join(QUI, "..", "datos", "horario_ejemplo.json"))
CFG = Config()


# ---------------------------------------------------------------- utilidades
def minutos(b):
    return a_min(b["fin"]) - a_min(b["inicio"])


def por_dia(plan, solo_tareas=False):
    d = defaultdict(int)
    for b in plan["bloques"]:
        if solo_tareas and b["tipo"] != "tarea":
            continue
        d[b["fecha"]] += minutos(b)
    return d


def asignado_por_tarea(plan):
    d = defaultdict(int)
    for b in plan["bloques"]:
        if b["tarea_id"]:
            d[b["tarea_id"]] += minutos(b)
    return d


def violaciones(datos, plan, ahora, cfg=CFG):
    """Cuenta violaciones de restricciones duras. Un plan correcto tiene todas en 0."""
    v = defaultdict(int)
    tareas = {t["id"]: t for t in plan["tareas"]}
    asignado = asignado_por_tarea(plan)
    por_f = defaultdict(list)
    for b in plan["bloques"]:
        por_f[b["fecha"]].append(b)
    for f, bl in por_f.items():
        dia = fecha(f)
        disp = datos["disponibilidad"].get(str(dia.weekday()), {})
        clases = [(a_min(c["inicio"]), a_min(c["fin"])) for c in bloques_del_dia(dia, datos)]
        if sum(minutos(b) for b in bl) > cfg.cap_dia:
            v["tope_diario"] += 1
        if not disp.get("disponible", True):
            v["dia_no_disponible"] += len(bl)
        ordenados = sorted(bl, key=lambda b: a_min(b["inicio"]))
        for i, b in enumerate(ordenados):
            s, e = a_min(b["inicio"]), a_min(b["fin"])
            if any(s < ce and cs < e for cs, ce in clases):
                v["choque_con_clase"] += 1
            if s < cfg.dia_inicio or e > cfg.dia_fin:
                v["fuera_de_horario"] += 1
            if dia == ahora.date() and s < ahora.hour * 60 + ahora.minute:
                v["antes_de_ahora"] += 1
            if i and s < a_min(ordenados[i - 1]["fin"]):
                v["solapamiento_entre_bloques"] += 1
            if b["tarea_id"] and dia > fecha(tareas[b["tarea_id"]]["due"]):
                v["despues_de_la_entrega"] += 1
    for tid, t in tareas.items():
        if asignado.get(tid, 0) > t["min"]:
            v["sobreasignacion"] += 1
    sin_aviso = {a["tarea_id"] for a in plan["advertencias"]}
    for tid, t in tareas.items():
        if asignado.get(tid, 0) < t["min"] and tid not in sin_aviso:
            v["falla_silenciosa"] += 1
    return dict(v)


# ------------------------------------------------- estrategia de comparación
def ultimo_momento(datos, ahora, plan, cfg=CFG):
    """Estrategia de referencia: cada trabajo se hace lo más tarde posible (hacia atrás desde la entrega),
    sin tope diario ni colchón. Es lo que hace quien 'deja todo para el final'. Usa los mismos huecos libres."""
    hoy = ahora.date()
    usados = defaultdict(list)
    bloques, asignado = [], {}
    for t in sorted(plan["tareas"], key=lambda t: (t["due"], t["id"])):
        due, desde, falta = fecha(t["due"]), fecha(t["desde"]), t["min"]
        d = due
        while d >= max(desde, hoy) and falta > 0:
            libres = []
            for w in ventanas_libres(d, datos, cfg, ahora):
                libres += _restar(w, usados[d])
            for s, e in sorted(libres, reverse=True):
                if d == desde:
                    s = max(s, t["desde_min"])
                if e - s < cfg.paso:
                    continue
                toma = min(falta, (e - s) // cfg.paso * cfg.paso)
                if toma <= 0:
                    continue
                bloques.append((d.isoformat(), e - toma, e, t["id"]))
                usados[d].append((e - toma, e))
                falta -= toma
                if falta <= 0:
                    break
            d -= timedelta(days=1)
        asignado[t["id"]] = t["min"] - falta
    return bloques, asignado


def metricas(bloques, tareas, cfg=CFG):
    """bloques: [(fecha_iso, ini_min, fin_min, tarea_id)]. Solo trabajo en tareas (no estudio libre)."""
    por_f, ult, asig = defaultdict(int), {}, defaultdict(int)
    for f, s, e, tid in bloques:
        por_f[f] += e - s
        asig[tid] += e - s
        ult[tid] = max(ult.get(tid, f), f)
    cubiertas = [t for t in tareas if asig.get(t["id"], 0) >= t["min"]]
    sin_colchon = [t for t in cubiertas if ult[t["id"]] == t["due"]]
    anticip = [(fecha(t["due"]) - fecha(ult[t["id"]])).days for t in cubiertas]
    return {
        "tareas": len(tareas), "cubiertas": len(cubiertas),
        "max_h_dia": max(por_f.values(), default=0) / 60,
        "dias_sobrecargados": sum(1 for m in por_f.values() if m > cfg.cap_dia),
        "sin_colchon": len(sin_colchon),
        "anticipacion_media_dias": statistics.mean(anticip) if anticip else 0.0,
    }


def de_plan(plan):
    return [(b["fecha"], a_min(b["inicio"]), a_min(b["fin"]), b["tarea_id"]) for b in plan["bloques"] if b["tipo"] == "tarea"]


# ------------------------------------------------------ escenarios aleatorios
def escenario(rng):
    k = rng.randint(4, 7)
    codigos = [f"MAT{i + 1}" for i in range(k)]
    bloques = []

    def libre(dia, s, e):
        return all(not (b["dia"] == dia and a_min(b["inicio"]) < e and s < a_min(b["fin"])) for b in bloques)

    for c in codigos:
        for _ in range(rng.randint(1, 3)):
            for _ in range(20):
                dia, s = rng.randint(0, 4), rng.choice(range(7 * 60, 17 * 60 + 1, 30))
                if libre(dia, s, s + 90):
                    bloques.append({"materia": c, "tipo": "LEC", "dia": dia, "inicio": f"{a_hhmm(s)}", "fin": a_hhmm(s + 90), "salon": ""})
                    break
    labs = {}
    for c in rng.sample(codigos, rng.randint(0, 2)):
        for _ in range(20):
            dia, s = rng.randint(0, 4), rng.choice(range(7 * 60, 15 * 60 + 1, 30))
            if libre(dia, s, s + 120):
                bloques.append({"materia": c, "tipo": "LAB", "dia": dia, "inicio": a_hhmm(s), "fin": a_hhmm(s + 120), "salon": ""})
                semanal = rng.random() < 0.5
                labs[c] = {"frecuencia": "semanal" if semanal else "quincenal", "semanas": None if semanal else rng.choice(["par", "impar"]),
                           "dias_entrega": 7, "dificultad": rng.choice(["Fácil", "Medio", "Difícil"])}
                break
    entregas = {c: {"frecuencia": "semanal", "semanas": None, "dias_entrega": 7, "dificultad": rng.choice(["Fácil", "Medio"])}
                for c in rng.sample(codigos, rng.randint(0, 2))}
    disp = {str(d): {"disponible": True, "inicio_trabajo": f"{rng.randint(14, 18)}:00"} for d in range(5)}
    disp["5"] = {"disponible": rng.random() < 0.5, "inicio_trabajo": "09:00"}
    disp["6"] = {"disponible": rng.random() < 0.3, "inicio_trabajo": "10:00"}
    for d in ("5", "6"):
        if not disp[d]["disponible"]:
            disp[d]["inicio_trabajo"] = None
    ahora = datetime(2026, 10, 12, rng.randint(7, 18), rng.choice([0, 15, 30, 45])) + timedelta(days=rng.randint(0, 6))
    trabajos = []
    for i in range(rng.randint(2, 7)):
        t = {"id": f"t{i}", "materia": rng.choice(codigos), "tipo": rng.choice(["Parcial", "Proyecto", "Taller", "Laboratorio"]),
             "titulo": f"Trabajo {i}", "entrega": (ahora.date() + timedelta(days=rng.randint(2, 28))).isoformat(),
             "dificultad": rng.choice(["Fácil", "Medio", "Difícil"])}
        if rng.random() < 0.3:
            t["horas"] = rng.choice([2, 4, 6, 8, 12])
        trabajos.append(t)
    datos = {"semestre_inicio": "2026-08-24", "materias": [{"codigo": c, "creditos": rng.randint(2, 4)} for c in codigos],
             "bloques": bloques, "labs": labs, "entregas_clase": entregas, "disponibilidad": disp, "trabajos": trabajos, "hechas": []}
    return datos, ahora


def bloque_simulacion():
    rng = random.Random(SEMILLA)
    viol = defaultdict(int)
    agg = {"edf": defaultdict(float), "ultimo": defaultdict(float)}
    t_plan, completos, con_aviso, tareas_tot, tareas_cub = [], 0, 0, 0, 0
    for _ in range(N_ESCENARIOS):
        datos, ahora = escenario(rng)
        t0 = time.perf_counter()
        plan = planificar(datos, ahora)
        t_plan.append((time.perf_counter() - t0) * 1000)
        for k, n in violaciones(datos, plan, ahora).items():
            viol[k] += n
        m_e = metricas(de_plan(plan), plan["tareas"])
        bl, asig = ultimo_momento(datos, ahora, plan)
        m_u = metricas(bl, plan["tareas"])
        for nombre, m in (("edf", m_e), ("ultimo", m_u)):
            for k, x in m.items():
                agg[nombre][k] += x
            agg[nombre]["escenarios"] += 1
        tareas_tot += m_e["tareas"]
        tareas_cub += m_e["cubiertas"]
        completos += m_e["cubiertas"] == m_e["tareas"]
        con_aviso += bool(plan["advertencias"])
    n = N_ESCENARIOS
    res = {
        "escenarios": n, "violaciones": dict(viol), "violaciones_total": sum(viol.values()),
        "tareas_totales": tareas_tot, "tareas_cubiertas": tareas_cub,
        "pct_tareas_cubiertas": round(100 * tareas_cub / tareas_tot, 1),
        "escenarios_completos": completos, "escenarios_con_advertencia": con_aviso,
        "ms_por_plan_media": round(statistics.mean(t_plan), 2), "ms_por_plan_p95": round(sorted(t_plan)[int(0.95 * n) - 1], 2),
        "ms_por_plan_max": round(max(t_plan), 2),
    }
    for nombre in ("edf", "ultimo"):
        a = agg[nombre]
        res[nombre] = {
            "dias_sobrecargados_total": int(a["dias_sobrecargados"]),
            "dias_sobrecargados_por_escenario": round(a["dias_sobrecargados"] / n, 2),
            "max_h_dia_media": round(a["max_h_dia"] / n, 2),
            "sin_colchon_total": int(a["sin_colchon"]),
            "pct_sin_colchon": round(100 * a["sin_colchon"] / max(1, a["cubiertas"]), 1),
            "anticipacion_media_dias": round(a["anticipacion_media_dias"] / n, 2),
            "pct_cubiertas": round(100 * a["cubiertas"] / a["tareas"], 1),
        }
    return res


# --------------------------------------------------------------- casos de prueba
def horas(b_list):
    return sum(minutos(b) for b in b_list) / 60


def caso_semana_base():
    datos = copy.deepcopy(BASE)
    plan = planificar(datos, AHORA)
    asig, tareas = asignado_por_tarea(plan), {t["id"]: t for t in plan["tareas"]}
    cub = sum(1 for t in plan["tareas"] if asig.get(t["id"], 0) >= t["min"])
    dias = por_dia(plan)
    parcial = [b for b in plan["bloques"] if b["tarea_id"] == "m1"]
    v = violaciones(datos, plan, AHORA)
    ult_parcial = max(b["fecha"] for b in parcial)
    return {
        "id": "CP1", "nombre": "Semana base del estudiante",
        "entrada": "Horario real del estudiante (6 materias, 14 bloques), 3 trabajos registrados, lunes 12/10/2026 09:00 (semana 8, par).",
        "chequeos": [
            ("Tareas con tiempo asegurado", f"{len(plan['tareas'])} de {len(plan['tareas'])}", f"{cub} de {len(plan['tareas'])}", cub == len(plan["tareas"])),
            ("Violaciones de restricciones duras", "0", str(sum(v.values())), sum(v.values()) == 0),
            ("Máximo de horas en un día", "<= 6 h", f"{max(dias.values()) / 60:g} h", max(dias.values()) <= CFG.cap_dia),
            ("Parcial difícil (entrega 20/10) termina con >= 2 días de colchón", "último bloque <= 18/10", f"último bloque {fecha(ult_parcial).strftime('%d/%m')}", fecha(ult_parcial) <= fecha("2026-10-20") - timedelta(days=2)),
            ("Advertencias de tiempo", "0", str(len(plan["advertencias"])), not plan["advertencias"]),
        ],
        "datos_extra": {"bloques": len(plan["bloques"]), "horas_tareas": round(horas([b for b in plan["bloques"] if b["tipo"] == "tarea"]), 1),
                        "horas_estudio": round(horas([b for b in plan["bloques"] if b["tipo"] == "estudio"]), 1),
                        "carga_por_dia_h": {k: round(m / 60, 1) for k, m in sorted(dias.items())}},
    }


def caso_imposible():
    datos = copy.deepcopy(BASE)
    datos["trabajos"].append({"id": "x1", "materia": "ISIS ARSW", "tipo": "Proyecto", "titulo": "Entrega imposible",
                              "entrega": "2026-10-13", "dificultad": "Difícil", "horas": 40})
    plan = planificar(datos, AHORA)
    asig = asignado_por_tarea(plan)
    adv = [a for a in plan["advertencias"] if a["tarea_id"] == "x1"]
    v = violaciones(datos, plan, AHORA)
    otras = [t for t in plan["tareas"] if t["id"] in ("m1", "m2", "m3")]
    otras_ok = sum(1 for t in otras if asig.get(t["id"], 0) >= t["min"])
    return {
        "id": "CP2", "nombre": "Entrega imposible",
        "entrada": "Caso base + un proyecto difícil de 40 h que se entrega mañana (13/10).",
        "chequeos": [
            ("Advertencia «no alcanza el tiempo» para el proyecto", "1 advertencia", f"{len(adv)} advertencia(s)", len(adv) == 1),
            ("Horas asignadas + horas que faltan = 40 h", "40 h", f"{asig.get('x1', 0) / 60:g} + {adv[0]['faltan_h']:g} = {asig.get('x1', 0) / 60 + adv[0]['faltan_h']:g} h" if adv else "sin dato", bool(adv) and abs(asig.get("x1", 0) / 60 + adv[0]["faltan_h"] - 40) < 1e-9),
            ("Se respeta el tope diario pese a la presión", "0 violaciones", f"{sum(v.values())} violaciones", sum(v.values()) == 0),
            ("Los demás trabajos registrados siguen cubiertos", f"{len(otras)} de {len(otras)}", f"{otras_ok} de {len(otras)}", otras_ok == len(otras)),
        ],
        "datos_extra": {"horas_asignadas_x1": asig.get("x1", 0) / 60, "faltan_h": adv[0]["faltan_h"] if adv else None},
    }


def caso_hechas():
    antes = planificar(copy.deepcopy(BASE), AHORA)
    datos = copy.deepcopy(BASE)
    datos["hechas"] = ["m1", "lab:ISIS ARSW:2026-10-09"]
    despues = planificar(datos, AHORA)
    asig = asignado_por_tarea(despues)
    quedan = [t for t in despues["tareas"] if asig.get(t["id"], 0) >= t["min"]]
    h_t = lambda p: horas([b for b in p["bloques"] if b["tipo"] == "tarea"])
    h_e = lambda p: horas([b for b in p["bloques"] if b["tipo"] == "estudio"])
    return {
        "id": "CP3", "nombre": "Marcar tareas como hechas reacomoda el plan",
        "entrada": "Caso base; el estudiante marca como hechos el Parcial 2 de ECDI y el informe de laboratorio de ARSW (09/10).",
        "chequeos": [
            ("Desaparecen los bloques de las tareas hechas", "0 bloques", f"{sum(1 for b in despues['bloques'] if b['tarea_id'] in datos['hechas'])} bloques", not any(b["tarea_id"] in datos["hechas"] for b in despues["bloques"])),
            ("Baja el trabajo en tareas", f"< {h_t(antes):g} h", f"{h_t(despues):g} h", h_t(despues) < h_t(antes)),
            ("El tiempo liberado pasa a estudio independiente", f"> {h_e(antes):g} h", f"{h_e(despues):g} h", h_e(despues) > h_e(antes)),
            ("Las demás tareas siguen cubiertas", f"{len(despues['tareas'])} de {len(despues['tareas'])}", f"{len(quedan)} de {len(despues['tareas'])}", len(quedan) == len(despues["tareas"])),
        ],
        "datos_extra": {"antes": {"tareas_h": round(h_t(antes), 1), "estudio_h": round(h_e(antes), 1)},
                        "despues": {"tareas_h": round(h_t(despues), 1), "estudio_h": round(h_e(despues), 1)}},
    }


def caso_disponibilidad():
    datos = copy.deepcopy(BASE)
    datos["disponibilidad"]["5"] = {"disponible": False, "inicio_trabajo": None}
    plan = planificar(datos, AHORA)
    asig = asignado_por_tarea(plan)
    sabados = [b for b in plan["bloques"] if fecha(b["fecha"]).weekday() == 5]
    cub = sum(1 for t in plan["tareas"] if asig.get(t["id"], 0) >= t["min"])
    base = planificar(copy.deepcopy(BASE), AHORA)
    return {
        "id": "CP4", "nombre": "Se respeta un día sin disponibilidad",
        "entrada": "Caso base pero el sábado deja de estar disponible.",
        "chequeos": [
            ("Bloques el sábado", "0", str(len(sabados)), len(sabados) == 0),
            ("Violaciones de restricciones duras", "0", str(sum(violaciones(datos, plan, AHORA).values())), sum(violaciones(datos, plan, AHORA).values()) == 0),
            ("Tareas cubiertas o advertidas (sin fallas silenciosas)", "100 %", f"{cub} cubiertas, {len(plan['advertencias'])} advertidas de {len(plan['tareas'])}", cub + len(plan["advertencias"]) >= len(plan["tareas"])),
        ],
        "datos_extra": {"bloques_con_sabado": len(base["bloques"]), "bloques_sin_sabado": len(plan["bloques"])},
    }


def caso_calibracion():
    sin = planificar(copy.deepcopy(BASE), AHORA)
    datos = copy.deepcopy(BASE)
    datos["historial"] = [{"tipo": "Taller", "base_h": 2.0, "real_h": 3.0} for _ in range(5)]
    con = planificar(datos, AHORA)
    mt = lambda p: sum(t["min"] for t in p["tareas"] if t["tipo"] == "Taller")
    f = factor_calibracion(datos["historial"], "Taller")
    return {
        "id": "CP5", "nombre": "La calibración ajusta las estimaciones",
        "entrada": "Caso base; el estudiante registró 5 talleres que estimados en 2 h le tomaron 3 h (razón 1,5).",
        "chequeos": [
            ("Sin historial el factor es 1 (el plan no cambia)", "1,00", f"{factor_calibracion([], 'Taller'):.2f}", factor_calibracion([], "Taller") == 1.0),
            ("Con 5 registros el factor se acerca a 1,5 sin igualarlo", "entre 1,30 y 1,50", f"{f:.2f}", 1.3 <= f <= 1.5),
            ("Aumentan los minutos asignados a talleres", f"> {mt(sin)} min", f"{mt(con)} min", mt(con) > mt(sin)),
            ("Los trabajos con horas fijadas por el estudiante no cambian", "480 min (PTIA)", f"{next(t['min'] for t in con['tareas'] if t['id'] == 'm3')} min", next(t["min"] for t in con["tareas"] if t["id"] == "m3") == 480),
        ],
        "datos_extra": {"factor_taller": round(f, 3)},
    }


def _texto_respuesta(r):
    out = []
    for b in r["bloques"]:
        if "txt" in b:
            out.append(b["txt"])
        for it in b.get("items", []):
            out.append(" ".join(it) if isinstance(it, list) else str(it))
    return "\n".join(out)


def caso_asistente():
    """CP6: el asistente responde con los datos del estudiante, sin modelo de lenguaje y sin inventar."""
    os.environ["SEMESTRIA_SIN_LLM"] = "1"
    from motor.asesor import consejos
    from motor.asistente import PREGUNTAS, Ctx, expandir_consejo, responder, tecnicas_para
    datos = copy.deepcopy(BASE)
    plan = planificar(datos, AHORA)

    def ask(msg="", accion=None, d=None):
        return responder(d or datos, plan, AHORA, msg, accion, llm_activo=False)

    hoy = _texto_respuesta(ask("¿Qué tengo hoy?"))
    parcial = ask("¿cuándo es mi parcial?")
    primera = parcial["bloques"][1]["items"][0][0]
    prep = ask("¿cómo estudio para el parcial de ECDI?")
    linea = next(b for b in prep["bloques"] if b["t"] == "fechas")["items"]
    fuera = ask("¿quién ganó el mundial?")
    respuestas = {"momento": "manana", "estilo": "releer", "distraccion": "celular", "sueno": "menos6", "reto": "empezar"}
    perfil, r = {}, ask(accion={"tipo": "entrevista_iniciar"})
    for campo, _, _ in PREGUNTAS:
        r = ask(accion={"tipo": "perfil", "campo": campo, "valor": respuestas[campo]}, d={**datos, "perfil": perfil})
        perfil = r["perfil"]
    t_plan = _texto_respuesta(r)
    c = Ctx(datos, plan, AHORA)
    lista = consejos(datos, plan, AHORA)
    expandidas = [expandir_consejo(cj, c) for cj in lista]
    return {
        "id": "CP6", "nombre": "El asistente responde con los datos del estudiante",
        "entrada": "Caso base, sin modelo de lenguaje: preguntas «¿Qué tengo hoy?», «¿cuándo es mi parcial?», «¿cómo estudio para el parcial de ECDI?», una pregunta fuera de tema y la entrevista de cinco preguntas.",
        "chequeos": [
            ("«¿Qué tengo hoy?» muestra la clase y el bloque reales del lunes 12/10", "09:00–11:00 y Taller MATE ECDI", "ambos presentes" if "09:00–11:00" in hoy and "Taller MATE ECDI" in hoy else "faltan", "09:00–11:00" in hoy and "Taller MATE ECDI" in hoy),
            ("«¿Cuándo es mi parcial?» pone primero el parcial con su fecha", "Parcial 2 de ECDI, 20/10", f"{primera}, {'20/10' if '20/10' in _texto_respuesta(parcial) else 'sin fecha'}", primera == "Parcial 2 de ECDI" and "20/10" in _texto_respuesta(parcial)),
            ("El plan de repasos termina en la fecha de la entrega", "martes 20/10", linea[-1][1], linea[-1][1] == "martes 20/10"),
            ("Una pregunta fuera de tema no se inventa", "«No tengo una respuesta segura»", "sin respuesta inventada" if "No tengo una respuesta segura" in _texto_respuesta(fuera) and "llm_pendiente" not in fuera else "respondió", "No tengo una respuesta segura" in _texto_respuesta(fuera) and "llm_pendiente" not in fuera),
            ("La entrevista arma el plan personal y pone primero el sueño (duerme menos de 6 h)", "Dormir como parte del estudio", "primero" if tecnicas_para(perfil)[0][0] == "sueno" else "no es el primero", r.get("perfil_completo") is True and "Tu plan de estudio personal" in t_plan and tecnicas_para(perfil)[0][0] == "sueno" and "Dormir como parte del estudio" in t_plan),
            ("Cada recomendación se puede explicar en el chat", f"{len(lista)} de {len(lista)}", f"{sum(1 for e in expandidas if len(e['bloques']) >= 3)} de {len(lista)}", bool(lista) and all(len(e["bloques"]) >= 3 for e in expandidas)),
        ],
        "datos_extra": {"recomendaciones": len(lista)},
    }


# ------------------------------------------------------------------ calibración
def bloque_calibracion():
    rng = random.Random(SEMILLA + 1)
    tipos = list(HORAS_BASE)
    res = {}
    todos_est, todos_cal = [], []
    curva_est, curva_cal = defaultdict(list), defaultdict(list)
    for m in (0.6, 0.8, 1.0, 1.3, 1.6, 2.0):
        e_est, e_cal = [], []
        for _ in range(N_USUARIOS):
            hist = []
            for i in range(12):
                tipo, dif = rng.choice(tipos), rng.choice(list(FACTOR_DIFICULTAD))
                base = HORAS_BASE[tipo] * FACTOR_DIFICULTAD[dif]
                real = base * m * math.exp(rng.gauss(0, 0.2))
                pred = base * factor_calibracion(hist, tipo)
                curva_est[(m, i)].append(abs(base - real))
                curva_cal[(m, i)].append(abs(pred - real))
                if i >= 5:
                    e_est.append(abs(base - real))
                    e_cal.append(abs(pred - real))
                hist.append({"tipo": tipo, "base_h": base, "real_h": real})
        res[str(m)] = {"mae_sin_h": round(statistics.mean(e_est), 2), "mae_con_h": round(statistics.mean(e_cal), 2),
                       "reduccion_pct": round(100 * (1 - statistics.mean(e_cal) / statistics.mean(e_est)), 1)}
        todos_est += e_est
        todos_cal += e_cal
    sesgados = [r["reduccion_pct"] for k, r in res.items() if k != "1.0"]
    return {"usuarios_por_ritmo": N_USUARIOS, "trabajos_por_usuario": 12, "se_mide_desde_el_trabajo": 6,
            "por_ritmo": res, "reduccion_media_pct": round(100 * (1 - statistics.mean(todos_cal) / statistics.mean(todos_est)), 1),
            "reduccion_media_sesgados_pct": round(statistics.mean(sesgados), 1),
            "_curva": {f"{m}|{i}": [statistics.mean(curva_est[(m, i)]), statistics.mean(curva_cal[(m, i)])] for (m, i) in curva_est}}


# ------------------------------------------------------------------------ salida
def figuras(sim, cal, casos):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans"})
    azul, gris = "#0a6cdb", "#a1a1a6"
    out = os.path.join(QUI, "..", "documento", "img")
    os.makedirs(out, exist_ok=True)

    fig, ax = plt.subplots(1, 3, figsize=(10, 3.2))
    for a, (clave, tit) in zip(ax, [("dias_sobrecargados_por_escenario", "Días con más de 6 h\n(por escenario)"),
                                    ("pct_sin_colchon", "Trabajos terminados el mismo\ndía de la entrega (%)"),
                                    ("max_h_dia_media", "Máximo de horas en un día\n(promedio)")]):
        v = [sim["ultimo"][clave], sim["edf"][clave]]
        b = a.bar(["Último\nmomento", "SemestrIA"], v, color=[gris, azul], width=.55)
        a.bar_label(b, fmt="%.1f", padding=2)
        a.set_title(tit, fontsize=10)
        a.set_ylim(0, max(v) * 1.25 if max(v) else 1)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_comparacion.png"), dpi=200)
    plt.close(fig)

    ritmos = list(cal["por_ritmo"])
    fig, a = plt.subplots(figsize=(6.5, 3.2))
    x = range(len(ritmos))
    a.bar([i - .2 for i in x], [cal["por_ritmo"][r]["mae_sin_h"] for r in ritmos], .4, color=gris, label="Estimación base")
    a.bar([i + .2 for i in x], [cal["por_ritmo"][r]["mae_con_h"] for r in ritmos], .4, color=azul, label="Con calibración")
    a.set_xticks(list(x), [f"{float(r):g}×" for r in ritmos])
    a.set_xlabel("Ritmo real del estudiante respecto a la estimación base")
    a.set_ylabel("Error absoluto medio (h)")
    a.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_calibracion.png"), dpi=200)
    plt.close(fig)

    carga = casos[0]["datos_extra"]["carga_por_dia_h"]
    fig, a = plt.subplots(figsize=(7, 3))
    a.bar([f"{fecha(k).strftime('%d/%m')}" for k in carga], list(carga.values()), color=azul, width=.6)
    a.axhline(6, color="#d70015", lw=1, ls="--")
    a.text(0, 6.15, "tope diario (6 h)", color="#d70015", fontsize=9)
    a.set_ylabel("Horas de trabajo planeadas")
    a.tick_params(axis="x", rotation=60)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_carga_dia.png"), dpi=200)
    plt.close(fig)


def markdown(r):
    L = ["# Evaluación del MVP de SemestrIA", "", f"Generado por `pruebas/evaluacion.py` (semilla {SEMILLA}).", ""]
    L += ["## A. Casos de prueba", ""]
    for c in r["casos"]:
        L += [f"### {c['id']}. {c['nombre']}", "", f"**Entrada:** {c['entrada']}", "", "| Comprobación | Esperado | Obtenido | |", "|---|---|---|---|"]
        L += [f"| {a} | {b} | {c_} | {'OK' if ok else 'FALLA'} |" for a, b, c_, ok in c["chequeos"]]
        L += [""]
    s = r["simulacion"]
    L += ["## B. Simulación", "", f"- Escenarios aleatorios: {s['escenarios']}; trabajos planificados: {s['tareas_totales']}.",
          f"- Violaciones de restricciones duras: **{s['violaciones_total']}** {s['violaciones'] or ''}",
          f"- Trabajos con tiempo asegurado: {s['pct_tareas_cubiertas']} % ({s['escenarios_completos']} de {s['escenarios']} escenarios completos; {s['escenarios_con_advertencia']} con advertencia).",
          f"- Tiempo por plan: media {s['ms_por_plan_media']} ms, p95 {s['ms_por_plan_p95']} ms, máximo {s['ms_por_plan_max']} ms.", "",
          "| Métrica | Último momento | SemestrIA |", "|---|---|---|"]
    for k, nombre in [("pct_cubiertas", "Trabajos cubiertos (%)"), ("dias_sobrecargados_por_escenario", "Días > 6 h por escenario"),
                      ("max_h_dia_media", "Máx. horas en un día (media)"), ("pct_sin_colchon", "Terminados el día de la entrega (%)"),
                      ("anticipacion_media_dias", "Anticipación media (días)")]:
        L.append(f"| {nombre} | {s['ultimo'][k]} | {s['edf'][k]} |")
    c = r["calibracion"]
    L += ["", "## C. Calibración", "", f"{c['usuarios_por_ritmo']} usuarios simulados por ritmo, {c['trabajos_por_usuario']} trabajos cada uno; error medido desde el trabajo {c['se_mide_desde_el_trabajo']}.", "",
          "| Ritmo real | Error base (h) | Error calibrado (h) | Reducción |", "|---|---|---|---|"]
    L += [f"| {float(k):g}× | {v['mae_sin_h']} | {v['mae_con_h']} | {v['reduccion_pct']} % |" for k, v in c["por_ritmo"].items()]
    L += ["", f"Reducción media: {c['reduccion_media_pct']} % (solo usuarios con ritmo distinto de 1×: {c['reduccion_media_sesgados_pct']} %)."]
    return "\n".join(L)


def main():
    casos = [caso_semana_base(), caso_imposible(), caso_hechas(), caso_disponibilidad(), caso_calibracion(), caso_asistente()]
    sim, cal = bloque_simulacion(), bloque_calibracion()
    curva = cal.pop("_curva")
    r = {"casos": casos, "simulacion": sim, "calibracion": cal}
    os.makedirs(os.path.join(QUI, "..", "resultados"), exist_ok=True)
    json.dump(r, open(os.path.join(QUI, "..", "resultados", "evaluacion.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(QUI, "..", "resultados", "evaluacion.md"), "w", encoding="utf-8").write(markdown(r))
    if "--figuras" in sys.argv:
        figuras(sim, cal, casos)
    fallas = [(c["id"], a) for c in casos for a, _, _, ok in c["chequeos"] if not ok]
    print(markdown(r))
    print("\nComprobaciones fallidas:", fallas or "ninguna")
    return 1 if fallas or sim["violaciones_total"] else 0


if __name__ == "__main__":
    sys.exit(main())
