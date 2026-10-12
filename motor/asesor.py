"""SemestrIA - validación de horarios importados y consejos sobre el plan.

Los consejos son reglas explicables (no un modelo generativo): cada uno dice qué se
detectó en el plan, por qué importa y qué hacer. Nivel: "alta" (actuar ya), "media", "info".
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, timedelta

from .semestria import DIAS, a_min, fecha

HHMM = re.compile(r"^\d{1,2}:\d{2}$")
TIPOS_TRABAJO = {"Taller", "Laboratorio", "Proyecto", "Parcial"}
DIFICULTADES = {"Fácil", "Medio", "Difícil"}


# --- Validación ------------------------------------------------------------
def validar_datos(d) -> tuple[dict | None, list[str]]:
    """Normaliza un horario importado. Devuelve (datos, errores); si hay errores, datos es None."""
    errores: list[str] = []
    if not isinstance(d, dict):
        return None, ["El archivo debe ser un objeto JSON."]
    out = {
        "semestre_inicio": d.get("semestre_inicio"),
        "materias": d.get("materias") or [],
        "bloques": d.get("bloques") or [],
        "labs": d.get("labs") or {},
        "entregas_clase": d.get("entregas_clase") or {},
        "disponibilidad": d.get("disponibilidad") or {},
        "trabajos": d.get("trabajos") or [],
        "hechas": d.get("hechas") or [],
        "en_curso": d.get("en_curso") or [],
    }
    try:
        fecha(out["semestre_inicio"])
    except (TypeError, ValueError):
        errores.append("Falta «semestre_inicio» (formato AAAA-MM-DD).")
    if not out["bloques"]:
        errores.append("El horario no tiene bloques de clase.")
    codigos = set()
    for m in out["materias"]:
        if not isinstance(m, dict) or "codigo" not in m:
            errores.append("Cada materia necesita «codigo» y «creditos».")
            continue
        m["creditos"] = int(m.get("creditos") or 3)
        codigos.add(m["codigo"])
    for i, b in enumerate(out["bloques"], 1):
        try:
            assert HHMM.match(b["inicio"]) and HHMM.match(b["fin"]) and a_min(b["inicio"]) < a_min(b["fin"])
            assert int(b["dia"]) in range(7) and b["materia"]
            b["dia"] = int(b["dia"])
            b.setdefault("tipo", "LEC")
            if b["materia"] not in codigos:   # materia que solo aparece en el horario
                out["materias"].append({"codigo": b["materia"], "creditos": 3})
                codigos.add(b["materia"])
        except (KeyError, AssertionError, ValueError, TypeError):
            errores.append(f"Bloque #{i} inválido (materia, dia 0-6, inicio < fin en HH:MM).")
    for k in range(7):
        out["disponibilidad"].setdefault(str(k), {"disponible": k != 6, "inicio_trabajo": "14:00" if k != 6 else None})
    for t in out["trabajos"]:
        try:
            fecha(t["entrega"])
            t.setdefault("id", f"u{abs(hash(t['titulo'])) % 10**8}")
            t.setdefault("tipo", "Taller")
            t.setdefault("dificultad", "Medio")
            if t["tipo"] not in TIPOS_TRABAJO or t["dificultad"] not in DIFICULTADES:
                raise ValueError
            if t["materia"] not in codigos:
                raise ValueError
        except (KeyError, ValueError, TypeError):
            errores.append(f"Trabajo inválido: {t.get('titulo', t)!r}.")
    return (None, errores) if errores else (out, [])


# --- Consejos --------------------------------------------------------------
def _min(b) -> int:
    return a_min(b["fin"]) - a_min(b["inicio"])


def _dia(f: date) -> str:
    return f"{DIAS[f.weekday()].lower()} {f.day}/{f.month:02d}"


def _hrs(m: float) -> str:
    return f"{m / 60:g} h"


def consejos(datos: dict, plan: dict, ahora: datetime) -> list[dict]:
    """Consejos concretos sobre el plan. Cada uno trae: nivel, categoria, titulo,
    texto (qué pasa y por qué) y accion (qué hacer ahora)."""
    hoy = ahora.date()
    res: list[dict] = []

    def add(nivel, categoria, titulo, texto, accion="", **extra):
        res.append({"nivel": nivel, "categoria": categoria, "titulo": titulo, "texto": texto, "accion": accion, **extra})

    bloques = plan["bloques"]
    tareas = {t["id"]: t for t in plan["tareas"]}
    por_dia: dict[str, int] = defaultdict(int)
    por_tarea: dict[str, list[dict]] = defaultdict(list)
    for b in bloques:
        por_dia[b["fecha"]] += _min(b)
        if b["tarea_id"]:
            por_tarea[b["tarea_id"]].append(b)
    hechas = set(datos.get("hechas", []))

    # 1. Foco de hoy
    de_hoy = [b for b in bloques if b["fecha"] == hoy.isoformat()]
    if de_hoy:
        total = sum(_min(b) for b in de_hoy)
        primero = de_hoy[0]
        add("info", "foco", f"Hoy: {len(de_hoy)} {'bloque' if len(de_hoy) == 1 else 'bloques'} de trabajo, {_hrs(total)}",
            f"Empiezas a las {primero['inicio']} con «{primero['titulo']}». {primero['motivo']}",
            "Arranca el primer bloque a la hora y deja el celular fuera de la mesa; lo difícil primero.")
    else:
        sig = next((b for b in bloques if b["fecha"] > hoy.isoformat()), None)
        if sig:
            add("info", "foco", "Hoy no tienes bloques",
                f"Tu siguiente bloque es el {_dia(fecha(sig['fecha']))} a las {sig['inicio']}: «{sig['titulo']}».",
                "Si tienes energía, adelanta 1 h de esa tarea: cada hora adelantada es colchón para imprevistos.")

    # 2. Lo que no cabe / vencido
    libres_off = [DIAS[int(k)] for k, v in datos["disponibilidad"].items() if not v.get("disponible")]
    for a in plan["advertencias"]:
        if a["tipo"] == "no_cabe":
            t = tareas.get(a["tarea_id"], {})
            opciones = []
            if libres_off:
                opciones.append(f"habilitar el {libres_off[0].lower()} como día de trabajo")
            opciones.append("subir el tope diario a 7–8 h solo esta semana")
            opciones.append("pedir al profesor un alcance menor o una prórroga")
            plazo = fecha(t["due"]).strftime("%d/%m") if t else "su plazo"
            add("alta", "riesgo", f"No te alcanza el tiempo: {a['titulo']}",
                f"Faltan {a['faltan_h']:g} h sin ubicar antes del {plazo}; tus huecos ya están ocupados "
                f"por tareas que vencen antes o el mismo día.",
                "Elige una: " + "; ".join(opciones) + ".", tarea_id=a["tarea_id"])
        elif a["tipo"] == "vencida":
            add("alta", "riesgo", f"Vencido: {a['titulo']}", a["mensaje"],
                "Escribe hoy al profesor para acordar entrega tardía; avisar a tiempo suele costar menos que no entregar. "
                "Si ya lo entregaste, márcalo como hecho.", tarea_id=a["tarea_id"])

    # 3. Colchón y planes por tarea (solo trabajos manuales pendientes)
    for tid, t in tareas.items():
        if t["auto"] or tid not in por_tarea:
            continue
        fechas = sorted(fecha(b["fecha"]) for b in por_tarea[tid])
        primero, ultimo, due = fechas[0], fechas[-1], fecha(t["due"])
        horas = t["min"] / 60
        if (due - ultimo).days <= 0 and t["dificultad"] != "Fácil" and horas >= 2:
            add("media", "riesgo", f"Sin colchón: {t['titulo']}",
                f"Tu último bloque cae el mismo {_dia(due)} de la entrega: cualquier imprevisto te deja sin margen.",
                "Mueve 1–2 h a un día anterior o libera tiempo marcando como hechas las tareas que ya terminaste.",
                materia=t["materia"], tarea_id=tid)
        if t["tipo"] == "Parcial" and horas >= 3:
            sim = fechas[-2] if len(fechas) > 1 else ultimo
            add("media", "estrategia", f"Parcial de {t['materia']}: plan de estudio",
                f"Tienes {_hrs(t['min'])} repartidas desde el {_dia(primero)} hasta el {_dia(ultimo)}.",
                f"Al inicio resume y haz ejercicios; el {_dia(sim)} haz un simulacro cronometrado con parciales pasados "
                f"y dedica el último bloque a repasar solo lo que fallaste.",
                materia=t["materia"], tarea_id=tid)
        elif t["tipo"] in ("Proyecto", "Taller") and horas >= 6 and len(fechas) >= 3:
            n = len(fechas)
            add("media", "estrategia", f"Divide en hitos: {t['titulo']}",
                f"Son {_hrs(t['min'])} en {n} días de trabajo; si lo dejas para el final, un error de diseño te costará días.",
                f"{_dia(primero)}: diseño y reparto de tareas · {_dia(fechas[n // 2])}: el núcleo funcionando · "
                f"{_dia(ultimo)}: pruebas y documentación. Termina el núcleo al menos 2 días antes del {due.strftime('%d/%m')}.",
                materia=t["materia"], tarea_id=tid)

    # 4. Concentración de entregas
    entregas = sorted((fecha(t["due"]), t["titulo"]) for t in tareas.values() if fecha(t["due"]) >= hoy)
    for d0, _ in entregas:
        grupo = [x for x in entregas if d0 <= x[0] <= d0 + timedelta(days=3)]
        if len(grupo) >= 4:
            nombres = ", ".join(f"{n} ({d.strftime('%d/%m')})" for d, n in grupo[:5])
            add("media", "carga", f"{len(grupo)} entregas en 4 días",
                f"Del {_dia(d0)} al {_dia(d0 + timedelta(days=3))} coinciden: {nombres}.",
                "Adelanta lo más corto en los días previos y avisa con tiempo si algo no sale: ahí se acumula el estrés.")
            break

    # 5. Carga por semana y días seguidos pesados
    semanas: dict[str, int] = defaultdict(int)
    for d, m in por_dia.items():
        f = fecha(d)
        semanas[(f - timedelta(days=f.weekday())).isoformat()] += m
    if semanas:
        pico, minutos = max(semanas.items(), key=lambda kv: kv[1])
        if minutos >= 30 * 60:
            add("media", "carga", f"Semana pesada: la del {fecha(pico).strftime('%d/%m')}",
                f"Tendrás {_hrs(minutos)} de trabajo fuera de clase, la semana más cargada del plan.",
                "Si puedes, adelanta 3–4 h desde la semana anterior para que esta no te sorprenda.")
    cargados = sorted(fecha(d) for d, m in por_dia.items() if m >= 6 * 60 * 0.9)
    racha, maxrac, fin_rac, prev = 0, 0, None, None
    for f in cargados:
        racha = racha + 1 if prev and (f - prev).days == 1 else 1
        if racha > maxrac:
            maxrac, fin_rac = racha, f
        prev = f
    if maxrac >= 3:
        add("media", "bienestar", f"{maxrac} días seguidos casi al tope",
            f"Tendrás jornadas de unas 6 h hasta el {_dia(fin_rac)}; el rendimiento cae cuando se acumula el cansancio.",
            "Pausa de 10 min cada 50 min, duerme 7 h y no recortes la comida: terminas antes rindiendo más.")
    disp = datos["disponibilidad"]
    if all(disp.get(str(i), {}).get("disponible") for i in range(7)):
        add("info", "bienestar", "Reserva un día libre", "Marcaste los 7 días como disponibles.",
            "Deja al menos uno sin trabajo académico: el descanso mejora lo que retienes.")

    # 6. Estudio independiente de la semana
    lunes = (hoy - timedelta(days=hoy.weekday())).isoformat()
    flojas = [(m, r) for m, r in (plan["resumen"].get(lunes) or {}).items()
              if r["meta_h"] >= 2 and (r["tareas_h"] + r["estudio_h"]) < 0.7 * r["meta_h"]]
    if flojas:
        det = "; ".join(f"{m}: {r['tareas_h'] + r['estudio_h']:g} de {r['meta_h']:g} h" for m, r in flojas)
        add("media", "estudio", "Estudio por debajo de la meta esta semana",
            f"Según tus créditos te falta: {det}. Las tareas con entrega cercana consumen el tiempo libre.",
            "Repasa 20 min justo después de cada clase de esas materias: es poco tiempo y evita la deuda de estudio.")

    # 7. Laboratorios con informe pendiente
    for tid, t in tareas.items():
        if t["tipo"] == "Laboratorio" and t["auto"] and tid in por_tarea:
            ini = min(fecha(b["fecha"]) for b in por_tarea[tid])
            if (ini - fecha(t["desde"])).days >= 3:
                add("info", "estrategia", f"Informe de {t['materia']}: empieza con el lab fresco",
                    f"El plan lo ubica el {_dia(ini)}, varios días después de la práctica.",
                    "Esa misma noche escribe un borrador de resultados y preguntas; después solo pulirás.",
                    materia=t["materia"], tarea_id=tid)
                break

    # 8. Progreso y cierre
    if hechas:
        add("info", "progreso", f"Llevas {len(hechas)} {'tarea hecha' if len(hechas) == 1 else 'tareas hechas'}",
            "Cada tarea cerrada libera tiempo en el plan para lo que sigue.",
            "Sigue marcándolas apenas las entregues para que el plan se reacomode.")
    if not any(r["nivel"] == "alta" for r in res):
        add("info", "progreso", "Todo cabe antes de su entrega", "No hay conflictos de tiempo en el horizonte del plan.",
            "Respeta los bloques y revisa el plan cada lunes: se recalcula con lo nuevo que agregues.")
    orden = {"alta": 0, "media": 1, "info": 2}
    return sorted(res, key=lambda c: (c["categoria"] != "foco", orden[c["nivel"]]))


def indicadores(datos: dict, plan: dict, ahora: datetime) -> dict:
    hoy = ahora.date()
    ids = [t["id"] for t in plan["tareas"]]
    cubiertas = {t["id"] for t in plan["tareas"]
                 if sum(_min(b) for b in plan["bloques"] if b["tarea_id"] == t["id"]) >= t["min"]}
    manuales = [t for t in datos["trabajos"] if t["id"] not in datos["hechas"]]
    prox = sorted((fecha(t["entrega"]), t["titulo"]) for t in manuales if fecha(t["entrega"]) >= hoy)
    fin_sem = hoy + timedelta(days=6 - hoy.weekday())
    sem_h = sum(_min(b) for b in plan["bloques"] if hoy <= fecha(b["fecha"]) <= fin_sem) / 60
    hoy_h = sum(_min(b) for b in plan["bloques"] if b["fecha"] == hoy.isoformat()) / 60
    return {
        "tareas_pendientes": len(ids),
        "tareas_cubiertas": len(cubiertas),
        "horas_semana": round(sem_h, 1),
        "horas_hoy": round(hoy_h, 1),
        "hechas": len(datos["hechas"]),
        "proxima_entrega": {"fecha": prox[0][0].isoformat(), "titulo": prox[0][1]} if prox else None,
        "dias_proxima": (prox[0][0] - hoy).days if prox else None,
    }
