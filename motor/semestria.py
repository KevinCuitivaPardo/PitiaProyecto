"""SemestrIA - motor de recomendación (prueba de concepto, Hito 2).

Convierte (1) los créditos de cada materia, (2) el horario fijo del semestre,
(3) la disponibilidad real del estudiante y (4) los trabajos registrados en un
plan semanal: qué trabajar, cuándo y por qué.

Enfoque: sistema basado en reglas + heurística de planificación tipo EDF
(Earliest Deadline First) con restricciones de bienestar. Es determinista y
explicable: cada bloque recomendado trae el motivo en lenguaje natural.

Todas las duraciones se manejan en minutos enteros para que el comportamiento
sea reproducible. Las estimaciones se calibran con el tiempo real que registra el estudiante (calibracion.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import math

from .calibracion import factor_calibracion

# --- Constantes de dominio -------------------------------------------------
HORAS_POR_CREDITO = 48      # Decreto 1330 de 2019, Art. 2.5.3.2.4.1
SEMANAS_PERIODO = 16        # semanas del periodo académico
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

HORAS_BASE = {"Taller": 2.0, "Laboratorio": 3.0, "Proyecto": 6.0, "Parcial": 5.0}
FACTOR_DIFICULTAD = {"Fácil": 0.75, "Medio": 1.0, "Difícil": 1.5}
RANGO_DIFICULTAD = {"Fácil": 1, "Medio": 2, "Difícil": 3}
MARGEN_DIAS = {"Fácil": 0, "Medio": 1, "Difícil": 2}  # días de colchón antes de la entrega


@dataclass
class Config:
    dia_inicio: int = 7 * 60          # no recomendar antes de las 7:00
    dia_fin: int = 21 * 60            # ni después de las 21:00
    max_horas_dia: float = 6.0        # tope de trabajo recomendado por día (bienestar)
    max_min_tarea_dia: int = 120      # tope por tarea y por día (obliga a repartir)
    bloque_max: int = 120
    bloque_min: int = 60
    paso: int = 30                    # granularidad
    usar_huecos: bool = True          # aprovechar huecos entre clases
    hueco_minimo: int = 60

    @property
    def cap_dia(self) -> int:
        return int(self.max_horas_dia * 60)


# --- Utilidades de tiempo --------------------------------------------------
def a_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def a_hhmm(minutos: int) -> str:
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def fecha(s: str) -> date:
    return date.fromisoformat(s)


def redondear_arriba(minutos: int, paso: int = 30) -> int:
    return int(math.ceil(minutos / paso) * paso)


def semana_del_semestre(f: date, inicio: date) -> int:
    return (f - inicio).days // 7 + 1


def paridad(semana: int) -> str:
    return "par" if semana % 2 == 0 else "impar"


# --- Créditos -> tiempo ----------------------------------------------------
def creditos_de(materia: str, datos: dict) -> int:
    for m in datos["materias"]:
        if m["codigo"] == materia:
            return m["creditos"]
    raise KeyError(materia)


def horas_totales_semana(creditos: int) -> float:
    """Trabajo total semanal de una materia (clase + independiente)."""
    return creditos * HORAS_POR_CREDITO / SEMANAS_PERIODO


def contacto_semanal_min(materia: str, datos: dict) -> float:
    """Minutos semanales con docente según el horario. Un lab quincenal cuenta la mitad."""
    total = 0.0
    for b in datos["bloques"]:
        if b["materia"] != materia:
            continue
        dur = a_min(b["fin"]) - a_min(b["inicio"])
        cfg = datos.get("labs", {}).get(materia, {})
        if b["tipo"] == "LAB" and cfg.get("frecuencia") == "quincenal":
            dur = dur / 2
        total += dur
    return total


def horas_independientes(materia: str, datos: dict) -> float:
    """Meta semanal de estudio independiente = trabajo total - horas en clase."""
    total = horas_totales_semana(creditos_de(materia, datos))
    return max(0.0, total - contacto_semanal_min(materia, datos) / 60)


# --- Horario ---------------------------------------------------------------
def sesion_ocurre(bloque: dict, f: date, datos: dict) -> bool:
    inicio = fecha(datos["semestre_inicio"])
    if f < inicio:
        return False
    if bloque["tipo"] == "LAB":
        cfg = datos.get("labs", {}).get(bloque["materia"], {})
        if cfg.get("frecuencia") == "quincenal":
            return paridad(semana_del_semestre(f, inicio)) == cfg.get("semanas")
    return True


def bloques_del_dia(f: date, datos: dict) -> list[dict]:
    res = [b for b in datos["bloques"] if b["dia"] == f.weekday() and sesion_ocurre(b, f, datos)]
    return sorted(res, key=lambda b: (a_min(b["inicio"]), a_min(b["fin"]), b["materia"]))


def salida_del_dia(dia: int, datos: dict) -> int | None:
    """Hora (en minutos) en que termina la última clase nominal del día."""
    fines = [a_min(b["fin"]) for b in datos["bloques"] if b["dia"] == dia]
    return max(fines) if fines else None


def ventanas_libres(f: date, datos: dict, cfg: Config, ahora: datetime | None = None):
    """Huecos aprovechables de un día: (inicio, fin) en minutos."""
    disp = datos["disponibilidad"].get(str(f.weekday()), {})
    if not disp.get("disponible", True):
        return []
    ocupado: list[list[int]] = []
    for b in bloques_del_dia(f, datos):
        s, e = a_min(b["inicio"]), a_min(b["fin"])
        if ocupado and s <= ocupado[-1][1]:
            ocupado[-1][1] = max(ocupado[-1][1], e)
        else:
            ocupado.append([s, e])

    ini_trabajo = a_min(disp["inicio_trabajo"]) if disp.get("inicio_trabajo") else cfg.dia_inicio
    brutas: list[tuple[int, int, bool]] = []
    cursor = cfg.dia_inicio
    for s, e in ocupado:
        if min(s, cfg.dia_fin) > cursor:
            brutas.append((cursor, min(s, cfg.dia_fin), False))
        cursor = max(cursor, e)
    if cursor < cfg.dia_fin:
        brutas.append((cursor, cfg.dia_fin, True))  # tras la última clase (o día sin clases)

    res = []
    for s, e, tras_salida in brutas:
        if tras_salida:
            s = max(s, ini_trabajo)  # respeta "a qué hora puedo empezar a trabajar"
        elif not cfg.usar_huecos:
            continue
        if ahora is not None and ahora.date() == f:
            s = max(s, redondear_arriba(ahora.hour * 60 + ahora.minute, cfg.paso))
        if e - s >= cfg.hueco_minimo:
            res.append((s, e))
    return res


# --- Trabajos --------------------------------------------------------------
def horas_estimadas(tipo: str, dificultad: str, override: float | None = None, factor: float = 1.0) -> float:
    """Horas de un trabajo: las que fije el estudiante o (horas base x dificultad x factor aprendido)."""
    horas = override if override is not None else HORAS_BASE[tipo] * FACTOR_DIFICULTAD[dificultad] * factor
    return math.ceil(horas * 2) / 2  # múltiplos de 30 min


def _tarea(id_, materia, tipo, titulo, due, dificultad, horas, desde, desde_min, auto, historial=None):
    """base_min es la estimación sin calibrar (contra la que se mide el tiempo real); fija indica que
    el estudiante dio las horas y por eso no se corrige."""
    return {
        "id": id_, "materia": materia, "tipo": tipo, "titulo": titulo,
        "due": due, "dificultad": dificultad,
        "min": int(horas_estimadas(tipo, dificultad, horas, factor_calibracion(historial or [], tipo)) * 60),
        "base_min": int(horas_estimadas(tipo, dificultad, horas) * 60), "fija": horas is not None,
        "desde": desde, "desde_min": desde_min, "auto": auto,
    }


def tareas_manuales(datos: dict, hoy: date) -> list[dict]:
    res = []
    for t in datos.get("trabajos", []):
        if t["id"] in datos.get("hechas", []):
            continue
        res.append(_tarea(t["id"], t["materia"], t["tipo"], t["titulo"], fecha(t["entrega"]),
                          t["dificultad"], t.get("horas"), fecha(t["desde"]) if t.get("desde") else hoy,
                          0, False, datos.get("historial")))
    return res


def tareas_automaticas(datos: dict, hoy: date, hasta: date) -> list[dict]:
    """Informes de laboratorio y talleres de clase que se derivan de las preguntas de profundización."""
    inicio = fecha(datos["semestre_inicio"])
    hechas = set(datos.get("hechas", []))
    res = []
    d = hoy - timedelta(days=14)
    while d <= hasta:
        # laboratorios
        for b in datos["bloques"]:
            if b["tipo"] != "LAB" or b["dia"] != d.weekday() or not sesion_ocurre(b, d, datos):
                continue
            cfg = datos.get("labs", {}).get(b["materia"])
            if not cfg or not cfg.get("dias_entrega"):
                continue
            due = d + timedelta(days=cfg["dias_entrega"])
            tid = f"lab:{b['materia']}:{d.isoformat()}"
            if due < hoy or due > hasta or tid in hechas:
                continue
            res.append(_tarea(tid, b["materia"], "Laboratorio", f"Informe de laboratorio {b['materia']} ({d.strftime('%d/%m')})",
                              due, cfg["dificultad"], None, d, a_min(b["fin"]), True, datos.get("historial")))
        # talleres que salen de la clase teórica
        for materia, cfg in datos.get("entregas_clase", {}).items():
            if cfg.get("frecuencia") in (None, "ninguna"):
                continue
            lecs = sorted((b for b in datos["bloques"] if b["materia"] == materia and b["tipo"] == "LEC"),
                          key=lambda b: (b["dia"], a_min(b["inicio"])))
            if not lecs or lecs[0]["dia"] != d.weekday():
                continue
            if cfg["frecuencia"] == "quincenal" and paridad(semana_del_semestre(d, inicio)) != cfg.get("semanas"):
                continue
            due = d + timedelta(days=cfg["dias_entrega"])
            tid = f"taller:{materia}:{d.isoformat()}"
            if due < hoy or due > hasta or tid in hechas:
                continue
            res.append(_tarea(tid, materia, "Taller", f"Taller {materia} ({d.strftime('%d/%m')})",
                              due, cfg["dificultad"], None, d, a_min(lecs[0]["fin"]), True, datos.get("historial")))
        d += timedelta(days=1)
    return res


def tope_tarea(t: dict, d: date, cfg: Config) -> int:
    """Tope de minutos por tarea y por día. Con la entrega a 1 día o menos se duplica (modo urgente)."""
    return cfg.max_min_tarea_dia * 2 if (t["due"] - d).days <= 1 else cfg.max_min_tarea_dia


def fin_horizonte(datos: dict, hoy: date) -> date:
    """Domingo de la semana actual + 2 semanas (o hasta la última entrega manual)."""
    domingo = hoy + timedelta(days=6 - hoy.weekday())
    fin = domingo + timedelta(days=14)
    for t in datos.get("trabajos", []):
        if t["id"] not in datos.get("hechas", []):
            e = fecha(t["entrega"])
            e_dom = e + timedelta(days=6 - e.weekday())
            if e_dom > fin and (e_dom - hoy).days <= 56:
                fin = e_dom
    return fin


# --- Planificador ----------------------------------------------------------
def _restar(ventana: tuple[int, int], bloques: list[tuple[int, int]]) -> list[tuple[int, int]]:
    s, e = ventana
    res = []
    cur = s
    for bs, be in sorted(bloques):
        if be <= cur or bs >= e:
            continue
        if bs > cur:
            res.append((cur, bs))
        cur = max(cur, be)
    if cur < e:
        res.append((cur, e))
    return res


def planificar(datos: dict, ahora: datetime, cfg: Config | None = None) -> dict:
    cfg = cfg or Config()
    hoy = ahora.date()
    hasta = fin_horizonte(datos, hoy)
    tareas = tareas_manuales(datos, hoy) + tareas_automaticas(datos, hoy, hasta)
    restante = {t["id"]: t["min"] for t in tareas}
    por_id = {t["id"]: t for t in tareas}

    bloques: list[dict] = []
    usado_dia: dict[date, int] = {}
    usado_tarea: dict[tuple[str, date], int] = {}
    ventanas_dia: dict[date, list[tuple[int, int]]] = {}

    def prioridad(t):
        efectiva = t["due"] - timedelta(days=MARGEN_DIAS[t["dificultad"]])
        return (efectiva.toordinal(), -RANGO_DIFICULTAD[t["dificultad"]], t["due"].toordinal(), t["id"])

    def motivo_tarea(t, f):
        dias = (t["due"] - f).days
        margen = MARGEN_DIAS[t["dificultad"]]
        dif = t["dificultad"].lower()
        if dias == 0:
            cuando = "Se entrega hoy"
        elif dias == 1:
            cuando = f"Se entrega mañana ({t['due'].strftime('%d/%m')})"
        else:
            cuando = f"Se entrega en {dias} días ({t['due'].strftime('%d/%m')})"
        if margen:
            colchon = f"Por su dificultad ({dif}) se planea con {margen} {'día' if margen == 1 else 'días'} de margen."
        else:
            colchon = f"Dificultad {dif}."
        if dias <= 1:
            return f"{cuando}. {colchon} Al ser inminente, se permiten hasta {tope_tarea(t, f, cfg) // 60} h hoy en esta tarea."
        return f"{cuando}. {colchon} Se reparte en bloques de máximo {cfg.max_min_tarea_dia // 60} h por día."

    # Pasada 1: tareas (EDF con colchón por dificultad)
    d = hoy
    while d <= hasta:
        ventanas = ventanas_libres(d, datos, cfg, ahora)
        ventanas_dia[d] = ventanas
        usado_dia[d] = 0
        for s, e in ventanas:
            cursor = s
            while e - cursor >= cfg.paso and usado_dia[d] < cfg.cap_dia:
                elegido = None
                cands = [t for t in tareas if restante[t["id"]] > 0 and d <= t["due"]
                         and (d > t["desde"] or (d == t["desde"] and cursor >= t["desde_min"]))
                         and usado_tarea.get((t["id"], d), 0) < tope_tarea(t, d, cfg)]
                for t in sorted(cands, key=prioridad):
                    chunk = min(e - cursor, restante[t["id"]], tope_tarea(t, d, cfg) - usado_tarea.get((t["id"], d), 0),
                                cfg.cap_dia - usado_dia[d], cfg.bloque_max)
                    chunk = chunk // cfg.paso * cfg.paso
                    if chunk >= cfg.bloque_min or (chunk >= cfg.paso and chunk == restante[t["id"]]):
                        elegido = (t, chunk)
                        break
                if elegido is None:
                    cursor += cfg.paso
                    continue
                t, chunk = elegido
                bloques.append({"fecha": d.isoformat(), "inicio": a_hhmm(cursor), "fin": a_hhmm(cursor + chunk),
                                "tipo": "tarea", "materia": t["materia"], "titulo": t["titulo"],
                                "dificultad": t["dificultad"], "tarea_id": t["id"], "motivo": motivo_tarea(t, d)})
                restante[t["id"]] -= chunk
                usado_tarea[(t["id"], d)] = usado_tarea.get((t["id"], d), 0) + chunk
                usado_dia[d] += chunk
                cursor += chunk
        d += timedelta(days=1)

    # Pasada 2: estudio independiente con lo que sobra, según la meta derivada de los créditos
    resumen: dict[str, dict] = {}
    lunes = hoy - timedelta(days=hoy.weekday())
    materias = [m["codigo"] for m in datos["materias"]]
    while lunes <= hasta:
        dias_sem = [lunes + timedelta(days=i) for i in range(7)]
        dias_hor = [x for x in dias_sem if hoy <= x <= hasta]
        disp_total = sum(1 for x in dias_sem if datos["disponibilidad"].get(str(x.weekday()), {}).get("disponible", True))
        disp_rest = sum(1 for x in dias_hor if datos["disponibilidad"].get(str(x.weekday()), {}).get("disponible", True))
        fraccion = disp_rest / disp_total if disp_total else 0
        tareas_sem = {m: 0 for m in materias}
        for b in bloques:
            if b["tipo"] == "tarea" and lunes <= fecha(b["fecha"]) <= lunes + timedelta(days=6):
                tareas_sem[b["materia"]] += a_min(b["fin"]) - a_min(b["inicio"])
        objetivo = {m: max(0, int(horas_independientes(m, datos) * 60 * fraccion) // cfg.paso * cfg.paso - tareas_sem[m])
                    for m in materias}
        meta_total = {m: int(horas_independientes(m, datos) * 60 * fraccion) for m in materias}
        faltan = dict(objetivo)
        for x in dias_hor:
            usado_mat_dia: dict[str, int] = {}
            ocupados = [(a_min(b["inicio"]), a_min(b["fin"])) for b in bloques if b["fecha"] == x.isoformat()]
            for ventana in ventanas_dia.get(x, []):
                for s, e in _restar(ventana, ocupados):
                    cursor = s
                    while e - cursor >= cfg.paso and usado_dia[x] < cfg.cap_dia:
                        cand = [m for m in materias if faltan[m] > 0 and usado_mat_dia.get(m, 0) < cfg.max_min_tarea_dia]
                        elegido = None
                        for m in sorted(cand, key=lambda m: (-faltan[m], materias.index(m))):
                            chunk = min(e - cursor, faltan[m], cfg.max_min_tarea_dia - usado_mat_dia.get(m, 0),
                                        cfg.cap_dia - usado_dia[x], cfg.bloque_max)
                            chunk = chunk // cfg.paso * cfg.paso
                            if chunk >= cfg.bloque_min or (chunk >= cfg.paso and chunk == faltan[m]):
                                elegido = (m, chunk)
                                break
                        if elegido is None:
                            cursor += cfg.paso
                            continue
                        m, chunk = elegido
                        h = horas_independientes(m, datos)
                        bloques.append({"fecha": x.isoformat(), "inicio": a_hhmm(cursor), "fin": a_hhmm(cursor + chunk),
                                        "tipo": "estudio", "materia": m, "titulo": f"Estudio independiente · {m}",
                                        "dificultad": None, "tarea_id": None,
                                        "motivo": f"Meta semanal de {m}: {creditos_de(m, datos)} créditos × 3 h − horas en clase = {h:.1f} h de estudio independiente."})
                        faltan[m] -= chunk
                        usado_mat_dia[m] = usado_mat_dia.get(m, 0) + chunk
                        usado_dia[x] += chunk
                        cursor += chunk
        resumen[lunes.isoformat()] = {}
        for m in materias:
            plan_estudio = sum(a_min(b["fin"]) - a_min(b["inicio"]) for b in bloques
                               if b["tipo"] == "estudio" and b["materia"] == m
                               and lunes <= fecha(b["fecha"]) <= lunes + timedelta(days=6))
            resumen[lunes.isoformat()][m] = {
                "meta_h": round(meta_total[m] / 60, 1),
                "tareas_h": round(tareas_sem[m] / 60, 1),
                "estudio_h": round(plan_estudio / 60, 1),
            }
        lunes += timedelta(days=7)

    advertencias = []
    for t in tareas:
        if restante[t["id"]] > 0:
            advertencias.append({"tipo": "no_cabe", "tarea_id": t["id"], "titulo": t["titulo"],
                                 "faltan_h": restante[t["id"]] / 60,
                                 "mensaje": f"No alcanza el tiempo libre: faltan {restante[t['id']] / 60:g} h para «{t['titulo']}» antes del {t['due'].strftime('%d/%m')}."})
    for t in datos.get("trabajos", []):
        if t["id"] not in datos.get("hechas", []) and fecha(t["entrega"]) < hoy:
            advertencias.append({"tipo": "vencida", "tarea_id": t["id"], "titulo": t["titulo"], "faltan_h": 0,
                                 "mensaje": f"«{t['titulo']}» ya venció ({fecha(t['entrega']).strftime('%d/%m')})."})

    bloques.sort(key=lambda b: (b["fecha"], b["inicio"], b["materia"]))
    return {"bloques": bloques, "advertencias": advertencias, "resumen": resumen,
            "tareas": [{k: (v.isoformat() if isinstance(v, date) else v) for k, v in t.items()} for t in tareas],
            "horizonte": [hoy.isoformat(), hasta.isoformat()]}


def cargar(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)
