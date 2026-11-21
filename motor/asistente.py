"""SemestrIA - asistente personal.

Responde preguntas sobre el horario y el plan del estudiante, explica cada recomendación, le hace preguntas para
conocer cómo estudia y le propone métodos de estudio y de bienestar con su evidencia.

Diseño híbrido:
  * Todo lo que depende de los datos del estudiante (agenda, entregas, horas, rachas) y de los métodos de estudio
    lo calcula este módulo a partir del plan: es instantáneo, verificable y no inventa fechas.
  * Si la pregunta no la reconoce y hay un modelo local (Ollama) disponible, `consultar_llm` redacta una respuesta
    con un contexto acotado; el modelo no recibe nada que salga del computador y su texto se marca como tal.

Las respuestas son listas de bloques que la interfaz dibuja: p (párrafo), h (título), ul/ol (listas), kv (datos),
fechas (línea de fechas), barras (gráfica simple), ciclo (bloques de enfoque y pausa), plantilla (texto para copiar)
y evidencia (referencias).
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

from .asesor import consejos
from .calibracion import resumen_calibracion
from .progreso import estadisticas
from .semestria import (DIAS, Config, _restar, a_hhmm, a_min, bloques_del_dia, contacto_semanal_min, fecha,
                        horas_independientes, horas_totales_semana, ventanas_libres)

# ----------------------------------------------------------------------------- utilidades
DIAS_CORTOS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _dia(f: date) -> str:
    return f"{DIAS[f.weekday()].lower()} {f.day}/{f.month:02d}"


def _h(minutos: float) -> str:
    return f"{minutos / 60:g} h".replace(".", ",")


def P(txt): return {"t": "p", "txt": txt}
def H(txt): return {"t": "h", "txt": txt}
def UL(items): return {"t": "ul", "items": items}
def OL(items): return {"t": "ol", "items": items}
def KV(items): return {"t": "kv", "items": [[a, b] for a, b in items]}
def FECHAS(items): return {"t": "fechas", "items": [[a, b] for a, b in items]}
def BARRAS(items, unidad="h", limite=None): return {"t": "barras", "items": [[a, b] for a, b in items], "unidad": unidad, "limite": limite}
def CICLO(trabajo, pausa, rondas, largo=20): return {"t": "ciclo", "trabajo": trabajo, "pausa": pausa, "rondas": rondas, "largo": largo}
def PLANTILLA(txt): return {"t": "plantilla", "txt": txt}
def EVID(refs): return {"t": "evidencia", "items": refs}


def SUG(etiqueta, tipo="mensaje", **extra):
    return {"texto": etiqueta, "accion": {"tipo": tipo, **extra}}


REF = {
    "dunlosky": "Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J. y Willingham, D. T. (2013). Improving students' learning with effective learning techniques. Psychological Science in the Public Interest, 14(1), 4-58.",
    "roediger": "Roediger, H. L. y Karpicke, J. D. (2006). Test-enhanced learning: taking memory tests improves long-term retention. Psychological Science, 17(3), 249-255.",
    "cepeda": "Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T. y Rohrer, D. (2006). Distributed practice in verbal recall tasks: a review and quantitative synthesis. Psychological Bulletin, 132(3), 354-380.",
    "rohrer": "Rohrer, D. y Taylor, K. (2007). The shuffling of mathematics problems improves learning. Instructional Science, 35, 481-498.",
    "chi": "Chi, M. T. H., de Leeuw, N., Chiu, M.-H. y LaVancher, C. (1994). Eliciting self-explanations improves understanding. Cognitive Science, 18(3), 439-477.",
    "ariga": "Ariga, A. y Lleras, A. (2011). Brief and rare mental breaks keep you focused. Cognition, 118(3), 439-443.",
    "gollwitzer": "Gollwitzer, P. M. y Sheeran, P. (2006). Implementation intentions and goal achievement: a meta-analysis of effects and processes. Advances in Experimental Social Psychology, 38, 69-119.",
    "steel": "Steel, P. (2007). The nature of procrastination: a meta-analytic and theoretical review of quintessential self-regulatory failure. Psychological Bulletin, 133(1), 65-94.",
    "curcio": "Curcio, G., Ferrara, M. y De Gennaro, L. (2006). Sleep loss, learning capacity and academic performance. Sleep Medicine Reviews, 10(5), 323-337.",
    "hillman": "Hillman, C. H., Erickson, K. I. y Kramer, A. F. (2008). Be smart, exercise your heart: exercise effects on brain and cognition. Nature Reviews Neuroscience, 9, 58-65.",
    "ward": "Ward, A. F., Duke, K., Gneezy, A. y Bos, M. W. (2017). Brain drain: the mere presence of one's own smartphone reduces available cognitive capacity. Journal of the Association for Consumer Research, 2(2), 140-154.",
    "ramirez": "Ramirez, G. y Beilock, S. L. (2011). Writing about testing worries boosts exam performance in the classroom. Science, 331(6014), 211-213.",
}


# ----------------------------------------------------------------------------- contexto
class Ctx:
    """Datos del estudiante y su plan, con las consultas que usa el asistente."""

    def __init__(self, datos: dict, plan: dict, ahora: datetime, cfg: Config | None = None):
        self.datos, self.plan, self.ahora = datos, plan, ahora
        self.hoy = ahora.date()
        self.cfg = cfg or Config()
        self._consejos = None
        self._prog = None

    @property
    def consejos(self):
        if self._consejos is None:
            self._consejos = consejos(self.datos, self.plan, self.ahora)
        return self._consejos

    @property
    def progreso(self):
        if self._prog is None:
            self._prog = estadisticas(self.datos, self.plan, self.ahora)
        return self._prog

    def bloques(self, d: date):
        return [b for b in self.plan["bloques"] if b["fecha"] == d.isoformat()]

    def clases(self, d: date):
        return bloques_del_dia(d, self.datos)

    def tareas(self):
        return sorted(self.plan["tareas"], key=lambda t: (t["due"], t["id"]))

    def asignado_min(self, tid: str) -> int:
        return sum(a_min(b["fin"]) - a_min(b["inicio"]) for b in self.plan["bloques"] if b["tarea_id"] == tid)

    def fechas_tarea(self, tid: str):
        return sorted({fecha(b["fecha"]) for b in self.plan["bloques"] if b["tarea_id"] == tid})

    def materia_en(self, texto: str):
        n = _norm(texto)
        for m in self.datos["materias"]:
            c = _norm(m["codigo"])
            if c in n:
                return m["codigo"]
        for m in self.datos["materias"]:
            for tok in _norm(m["codigo"]).split():
                if len(tok) >= 4 and tok not in ("isis", "mate", "cien") and re.search(r"\b" + re.escape(tok), n):
                    return m["codigo"]
        return None

    def prueba_principal(self, tid: str | None = None):
        ts = self.tareas()
        if tid:
            for t in ts:
                if t["id"] == tid:
                    return t
        for tipo in ("Parcial", "Proyecto"):
            for t in ts:
                if t["tipo"] == tipo and not t["auto"]:
                    return t
        return ts[0] if ts else None

    def horas_dia(self, d: date) -> float:
        return sum(a_min(b["fin"]) - a_min(b["inicio"]) for b in self.bloques(d)) / 60

    def huecos_libres(self, d: date):
        """Huecos del día que el plan todavía no usa."""
        ocupados = [(a_min(b["inicio"]), a_min(b["fin"])) for b in self.bloques(d)]
        res = []
        for v in ventanas_libres(d, self.datos, self.cfg, self.ahora if d == self.hoy else None):
            res += _restar(v, ocupados)
        return [(s, e) for s, e in res if e - s >= 60]


# ----------------------------------------------------------------------------- métodos de estudio
def _repasos(hoy: date, due: date) -> list[date]:
    cand = [hoy + timedelta(days=k) for k in (0, 1, 3, 7)]
    res = [d for d in cand if d < due]
    if len(res) < 2 and due - timedelta(days=1) not in res and due - timedelta(days=1) >= hoy:
        res.append(due - timedelta(days=1))
    return sorted(set(res))


def _aplicar_espaciado(c: Ctx, perfil):
    t = c.prueba_principal()
    if not t:
        return [P("Cuando registres un parcial o un proyecto te propongo las fechas exactas de repaso.")]
    due = fecha(t["due"])
    rep = _repasos(c.hoy, due)
    items = [(f"Repaso {i + 1}", _dia(d)) for i, d in enumerate(rep)] + [("Entrega", _dia(due))]
    return [P(f"Aplicado a «{t['titulo']}» ({t['materia']}), que se entrega el {_dia(due)}:"), FECHAS(items),
            P("Cada repaso dura 20 a 30 minutos y es corto a propósito: lo importante es volver varias veces, no estudiar más tiempo.")]


def _aplicar_recuperacion(c: Ctx, perfil):
    t = c.prueba_principal()
    if not t:
        return []
    fs = c.fechas_tarea(t["id"])
    if not fs:
        return []
    return [P(f"Aplicado a «{t['titulo']}»: cierra cada uno de tus bloques de estudio ({', '.join(_dia(d) for d in fs[:4])}) con 5 a 10 minutos de autoevaluación, y deja el penúltimo bloque para un simulacro completo con tiempo.")]


def _aplicar_pomodoro(c: Ctx, perfil):
    mejor = None
    for d in (c.hoy + timedelta(days=i) for i in range(0, 3)):
        for b in c.bloques(d):
            dur = a_min(b["fin"]) - a_min(b["inicio"])
            if dur >= 90 and (mejor is None or dur > mejor[1]):
                mejor = (b, dur, d)
    if not mejor:
        return []
    b, dur, d = mejor
    rondas = max(1, dur // 60)
    return [P(f"Aplicado a tu próximo bloque largo: {_dia(d)} de {b['inicio']} a {b['fin']} ({b['titulo']}). Son {_h(dur)}: parte el bloque en {rondas} ronda(s) de 50 minutos con 10 de pausa.")]


def _aplicar_si_entonces(c: Ctx, perfil):
    frases = []
    for d in (c.hoy + timedelta(days=i) for i in range(0, 5)):
        for b in c.bloques(d)[:1]:
            if b["tipo"] == "tarea" and d >= c.hoy:
                frases.append(f"Si es {_dia(d)} a las {b['inicio']}, entonces abro «{b['titulo']}» y trabajo el primer paso.")
        if len(frases) == 3:
            break
    return [P("Aplicado a tus próximos bloques, tres frases listas para usar:"), UL(frases)] if frases else []


def _aplicar_sueno(c: Ctx, perfil):
    tarde = []
    for d in (c.hoy + timedelta(days=i) for i in range(0, 7)):
        bl = c.bloques(d)
        if bl:
            fin = max(a_min(b["fin"]) for b in bl)
            if fin >= 20 * 60 + 30:
                tarde.append((d, fin))
    if not tarde:
        return [P("Tu plan actual no te deja estudiando tarde en la noche: mantén esa regla.")]
    return [P("Estos días tu plan termina tarde; si puedes, mueve un bloque a un hueco del día:"), UL([f"{_dia(d)}: termina a las {a_hhmm(fin)}" for d, fin in tarde[:4]])]


def _aplicar_celular(c: Ctx, perfil):
    b = next((b for d in (c.hoy + timedelta(days=i) for i in range(0, 3)) for b in c.bloques(d) if b["tipo"] == "tarea"), None)
    return [P(f"Pruébalo desde tu próximo bloque de tarea: «{b['titulo']}», el {_dia(fecha(b['fecha']))} a las {b['inicio']}.")] if b else []


TECNICAS = {
    "recuperacion": {
        "nombre": "Práctica de recuperación (autoevaluación)",
        "que": "En lugar de releer, cierras el material y tratas de recordar o resolver sin mirar; después compruebas qué falló.",
        "porque": "Recordar activamente fortalece la memoria más que volver a leer, y en las revisiones sobre técnicas de estudio es de las de mayor utilidad.",
        "pasos": ["Estudia un tema durante 20 a 30 minutos.", "Cierra el material y escribe o di en voz alta todo lo que recuerdes.", "Compara con el material y marca lo que faltó o estaba mal.", "Vuelve solo sobre lo que falló y repítelo al día siguiente."],
        "evid": ["roediger", "dunlosky"], "aplicar": _aplicar_recuperacion},
    "espaciado": {
        "nombre": "Repetición espaciada",
        "que": "Repartir los repasos en varios días, con intervalos que van creciendo, en vez de estudiar todo de una sola vez.",
        "porque": "Con el mismo tiempo total, repasar en sesiones separadas produce mejor retención que concentrarlo en una sola sesión.",
        "pasos": ["Primer repaso el mismo día que ves el tema.", "Segundo repaso al día siguiente.", "Tercero a los 3 o 4 días.", "Cuarto a la semana, o la víspera de la prueba."],
        "evid": ["cepeda", "dunlosky"], "aplicar": _aplicar_espaciado},
    "intercalado": {
        "nombre": "Práctica intercalada",
        "que": "Mezclar tipos de problemas o temas dentro de una misma sesión en lugar de repetir un solo tipo en bloque.",
        "porque": "Te obliga a decidir qué método usar en cada problema, que es lo que se necesita en un parcial; en matemáticas mejoró los resultados de pruebas posteriores.",
        "pasos": ["Haz una lista de 3 o 4 tipos de ejercicio del tema.", "Resuelve uno de cada tipo y rota, sin agotar uno antes de pasar al siguiente.", "Anota qué señal del enunciado te indicó el método.", "Termina con un mixto cronometrado."],
        "evid": ["rohrer", "dunlosky"], "aplicar": None},
    "autoexplicacion": {
        "nombre": "Autoexplicación (técnica Feynman)",
        "que": "Explicarte el tema, en voz alta o por escrito y con palabras simples, como si se lo enseñaras a alguien que no sabe nada de él.",
        "porque": "Al generar tus propias explicaciones notas dónde no entiendes; quienes se autoexplican suelen comprender mejor el material.",
        "pasos": ["Elige un concepto.", "Explícalo sin mirar apuntes durante 2 o 3 minutos.", "Marca dónde te trabaste o recurriste a jerga.", "Vuelve al material solo para esos huecos y repite."],
        "evid": ["chi", "dunlosky"], "aplicar": None},
    "pomodoro": {
        "nombre": "Bloques de enfoque con pausas",
        "que": "Trabajar en bloques de 25 a 50 minutos con pausas cortas y una pausa larga cada tres o cuatro bloques.",
        "porque": "Las pausas breves ayudan a sostener la atención en tareas largas. La duración exacta (la técnica Pomodoro usa 25 y 5) es una convención útil, no una regla científica.",
        "pasos": ["Define qué harás en el bloque: una sola cosa.", "Pon un temporizador y evita interrupciones.", "Haz una pausa de 5 a 10 minutos lejos de la pantalla.", "Cada 3 o 4 bloques, pausa de 20 a 30 minutos."],
        "visual": CICLO(50, 10, 3), "evid": ["ariga"], "aplicar": _aplicar_pomodoro},
    "si_entonces": {
        "nombre": "Planes «si... entonces...»",
        "que": "Decidir de antemano cuándo, dónde y cómo vas a empezar: «si es martes a las 7:00, entonces abro el taller en la biblioteca».",
        "porque": "Atar la acción a una señal concreta reduce la dependencia de la motivación del momento; un metaanálisis encontró efectos de tamaño medio a grande para lograr metas.",
        "pasos": ["Elige la tarea y el primer paso.", "Define la señal: día, hora y lugar.", "Escribe la frase «si... entonces...».", "Ejecútala sin renegociar en el momento."],
        "evid": ["gollwitzer"], "aplicar": _aplicar_si_entonces},
    "procrastinacion": {
        "nombre": "Cómo arrancar cuando se posterga",
        "que": "Hacer la tarea más pequeña, más concreta y más cercana en el tiempo, para que empezar cueste menos.",
        "porque": "La procrastinación aumenta cuando la tarea resulta desagradable y lejana; reducir ese costo de arranque ayuda a empezar.",
        "pasos": ["Reduce: define un primer paso de 5 minutos.", "Acerca: el plan ya te pone el primer bloque en el calendario; ve a él.", "Quita fricción: deja el material abierto desde la noche anterior.", "Cierra la sesión anotando cuál es el siguiente paso."],
        "evid": ["steel"], "aplicar": _aplicar_si_entonces},
    "sueno": {
        "nombre": "Dormir como parte del estudio",
        "que": "Proteger el sueño es parte de la preparación, no un lujo que se sacrifica.",
        "porque": "La falta de sueño se asocia con peor rendimiento académico y menor capacidad de aprender. Las sociedades de medicina del sueño recomiendan 7 horas o más para adultos.",
        "pasos": ["Apunta a 7 horas o más cada noche.", "Mantén una hora de levantarte parecida entre semana y fin de semana.", "Baja pantallas intensas 30 a 60 minutos antes de dormir.", "No trasnoches para estudiar: mueve el bloque a un hueco del día."],
        "evid": ["curcio"], "aplicar": _aplicar_sueno},
    "ejercicio": {
        "nombre": "Movimiento y pausas activas",
        "que": "Actividad física regular y pausas en las que te levantas y te mueves.",
        "porque": "La actividad física se asocia con mejoras en la atención y en funciones cognitivas, y ayuda a manejar el estrés.",
        "pasos": ["Camina 10 minutos en tus pausas largas.", "Busca unos 30 minutos de actividad moderada varias veces por semana.", "Ponlo en el calendario como si fuera una clase."],
        "evid": ["hillman"], "aplicar": None},
    "celular": {
        "nombre": "Distracciones: el celular fuera de la vista",
        "que": "Dejar el celular lejos de tu campo de visión mientras estudias.",
        "porque": "En experimentos, la sola presencia del celular redujo la capacidad cognitiva disponible, incluso estando apagado.",
        "pasos": ["Pon el celular en la mochila o en otra habitación durante el bloque.", "Activa «no molestar» y apaga las notificaciones de redes.", "Revísalo en la pausa, no en medio del bloque.", "En el computador, cierra las pestañas que no sean de la tarea."],
        "evid": ["ward"], "aplicar": _aplicar_celular},
    "ansiedad": {
        "nombre": "Manejar los nervios antes de una prueba",
        "que": "Escribir durante unos 10 minutos tus preocupaciones sobre la prueba justo antes de presentarla.",
        "porque": "En un estudio con estudiantes, escribir sobre las preocupaciones antes de un examen mejoró el desempeño de quienes sentían más ansiedad.",
        "pasos": ["Diez minutos antes, escribe lo que te preocupa de la prueba.", "Respira lento un par de minutos (inhala contando 4, exhala contando 6).", "Haz un simulacro previo en condiciones parecidas a las reales.", "Duerme bien la víspera y llega con tiempo."],
        "nota": "Si los nervios son intensos o frecuentes, busca apoyo en bienestar universitario o con un profesional de salud: este consejo no lo reemplaza.",
        "evid": ["ramirez"], "aplicar": None},
    "relectura": {
        "nombre": "Qué evitar: releer y subrayar",
        "que": "Releer varias veces y subrayar dan sensación de dominio, pero rinden poco.",
        "porque": "En la revisión de técnicas de estudio, releer y resaltar quedaron entre las de utilidad baja frente a la autoevaluación y el repaso espaciado.",
        "pasos": ["Sustituye la segunda relectura por una autoevaluación.", "Si subrayas, hazlo después de entender y úsalo para escribir preguntas.", "Convierte tus apuntes en preguntas que puedas responder sin mirarlos."],
        "evid": ["dunlosky"], "aplicar": None},
}

CLAVES_TECNICA = {
    "espaciado": ["espaci", "repaso", "repasar", "repeticion", "curva del olvido", "olvid", "retener", "retencion", "memoriz"],
    "recuperacion": ["autoevalu", "recuperacion", "simulacro", "practica", "flashcard", "tarjetas", "quiz", "preguntas de practica"],
    "intercalado": ["intercal", "mezclar", "ejercicios", "problemas", "matematica", "calculo"],
    "autoexplicacion": ["feynman", "autoexplic", "explicar", "entender", "comprender", "comprension"],
    "pomodoro": ["pomodoro", "pausa", "descanso", "concentr", "enfoque", "atencion", "cansanc", "bloques de"],
    "si_entonces": ["si entonces", "intencion", "habito", "rutina", "constancia", "disciplina", "motivacion"],
    "procrastinacion": ["procrastin", "pereza", "postergo", "aplazo", "empezar", "arrancar", "flojera", "dejo todo", "ultimo momento"],
    "sueno": ["sueno", "dormir", "duermo", "trasnoch", "desvelo", "insomnio", "cansad", "agotad"],
    "ejercicio": ["deporte", "caminar", "actividad fisica", "gimnasio", "ejercicio fisico", "ejercitar"],
    "celular": ["celular", "redes", "distra", "telefono", "tiktok", "instagram", "whatsapp", "notificacion", "youtube"],
    "ansiedad": ["ansied", "nervio", "estres", "panico", "bloqueo", "miedo", "angustia", "presion"],
    "relectura": ["releer", "subray", "resumen", "resumir", "apuntes", "resaltar"],
}


def tecnica_bloques(tid: str, c: Ctx, perfil: dict | None = None) -> list[dict]:
    t = TECNICAS[tid]
    out = [H(t["nombre"]), P(t["que"]), P("Por qué funciona: " + t["porque"])]
    if t.get("visual"):
        out.append(t["visual"])
    out += [P("Cómo hacerlo:"), OL(t["pasos"])]
    if t.get("aplicar"):
        out += t["aplicar"](c, perfil or {})
    if t.get("nota"):
        out.append(P(t["nota"]))
    out.append(EVID([REF[k] for k in t["evid"]]))
    return out


def sugerencias_tecnica(excluir: str | None = None, n: int = 3):
    orden = ["espaciado", "recuperacion", "pomodoro", "si_entonces", "sueno", "celular", "intercalado", "autoexplicacion"]
    return [SUG(TECNICAS[k]["nombre"], "tecnica", id=k) for k in orden if k != excluir][:n]


# ----------------------------------------------------------------------------- entrevista
PREGUNTAS = [
    ("momento", "¿En qué momento del día sientes que rindes más?",
     [("Por la mañana", "manana"), ("Por la tarde", "tarde"), ("Por la noche", "noche"), ("Me varía", "varia")]),
    ("estilo", "¿Cómo sueles estudiar para una prueba?",
     [("Releo y subrayo", "releer"), ("Hago resúmenes", "resumir"), ("Resuelvo ejercicios", "ejercicios"), ("Explico a otros", "explicar"), ("Memorizo", "memorizar")]),
    ("distraccion", "¿Qué es lo que más te distrae al estudiar?",
     [("El celular y las redes", "celular"), ("Ruido o gente", "ruido"), ("El cansancio", "cansancio"), ("Preocupaciones o nervios", "nervios"), ("Casi nada", "nada")]),
    ("sueno", "¿Cuántas horas duermes en promedio?",
     [("Menos de 6", "menos6"), ("Entre 6 y 7", "6a7"), ("Entre 7 y 8", "7a8"), ("Más de 8", "mas8")]),
    ("reto", "¿Cuál es tu mayor reto hoy?",
     [("Empezar a tiempo", "empezar"), ("Mantener la concentración", "concentracion"), ("Recordar lo que estudié", "recordar"), ("Los nervios en exámenes", "nervios"), ("Organizar mi tiempo", "organizar")]),
]
ETIQUETA = {c: {v: l for l, v in ops} for c, _, ops in PREGUNTAS}
NOMBRES_CAMPO = {"momento": "Mejor momento", "estilo": "Cómo estudias", "distraccion": "Qué te distrae", "sueno": "Sueño", "reto": "Mayor reto"}


def _pregunta(i: int, c: Ctx, previo: str | None = None) -> dict:
    campo, texto, ops = PREGUNTAS[i]
    intro = [P(previo)] if previo else []
    return {"bloques": intro + [P(f"Pregunta {i + 1} de {len(PREGUNTAS)}: {texto}")],
            "sugerencias": [SUG(l, "perfil", campo=campo, valor=v) for l, v in ops], "perfil_pendiente": True}


def tecnicas_para(perfil: dict) -> list[tuple[str, str]]:
    """(técnica, razón) ordenadas por prioridad según el perfil."""
    res: list[tuple[str, str]] = []

    def add(t, razon):
        if t not in [x for x, _ in res]:
            res.append((t, razon))

    if perfil.get("sueno") == "menos6":
        add("sueno", "duermes menos de 6 horas: es lo primero que más rendimiento te devolvería")
    reto = perfil.get("reto")
    if reto == "empezar":
        add("procrastinacion", "tu mayor reto es empezar a tiempo")
        add("si_entonces", "convierte el plan en una señal concreta para arrancar")
    if reto == "concentracion":
        add("pomodoro", "tu mayor reto es la concentración")
    if reto == "recordar":
        add("espaciado", "tu reto es recordar lo estudiado")
        add("recuperacion", "recordar mejora cuando practicas recordar")
    if reto == "nervios" or perfil.get("distraccion") == "nervios":
        add("ansiedad", "los nervios te afectan en las pruebas")
    if perfil.get("distraccion") == "celular":
        add("celular", "el celular es lo que más te distrae")
    if perfil.get("distraccion") == "cansancio":
        add("sueno", "el cansancio te distrae")
        add("ejercicio", "las pausas activas ayudan con el cansancio")
    if perfil.get("distraccion") == "ruido":
        add("pomodoro", "elegir un bloque definido y un lugar tranquilo reduce la interferencia")
    estilo = perfil.get("estilo")
    if estilo in ("releer", "resumir", "memorizar"):
        add("recuperacion", f"hoy {'relees' if estilo == 'releer' else 'resumes' if estilo == 'resumir' else 'memorizas'}; cambiarlo por autoevaluación rinde más")
        add("espaciado", "repartir los repasos mejora la retención")
    if estilo == "ejercicios":
        add("intercalado", "ya resuelves ejercicios: mezclarlos entrena a elegir el método")
        add("espaciado", "repasar los tipos de problema en varios días")
    if estilo == "explicar":
        add("autoexplicacion", "ya explicas a otros: es una de las mejores formas de detectar huecos")
        add("espaciado", "repartir esas explicaciones en el tiempo")
    if reto == "organizar":
        add("si_entonces", "te ayuda a ligar el plan a horas concretas")
    add("espaciado", "es la base de cualquier preparación para parciales")
    add("recuperacion", "complementa el repaso con autoevaluación")
    return res[:5]


def plan_personal(perfil: dict, c: Ctx) -> dict:
    tecs = tecnicas_para(perfil)
    out = [H("Tu plan de estudio personal"),
           KV([(NOMBRES_CAMPO[k], ETIQUETA[k].get(perfil.get(k), "-")) for k in NOMBRES_CAMPO if perfil.get(k)]),
           P("Con lo que me contaste, estos son los métodos que más te convienen, en orden de prioridad:")]
    for i, (t, razon) in enumerate(tecs, 1):
        out += [P(f"{i}. {TECNICAS[t]['nombre']}: {razon}.")]
    momento = perfil.get("momento")
    rangos = {"manana": (0, 12 * 60), "tarde": (12 * 60, 18 * 60), "noche": (18 * 60, 24 * 60)}
    if momento in rangos:
        lo, hi = rangos[momento]
        difs = []
        for d in (c.hoy + timedelta(days=i) for i in range(0, 7)):
            for b in c.bloques(d):
                if b["tipo"] == "tarea" and lo <= a_min(b["inicio"]) < hi and b["dificultad"] in ("Difícil", "Medio"):
                    difs.append(f"{_dia(d)} {b['inicio']}: {b['titulo']}")
        out += [H("Tus mejores horas"), P(f"Dices que rindes más {ETIQUETA['momento'][momento].lower()}. Estos bloques de tu plan caen en ese momento: reserva en ellos lo más difícil.") if difs
                else P(f"Dices que rindes más {ETIQUETA['momento'][momento].lower()}, pero tu plan casi no tiene bloques de tareas exigentes en ese momento. Si puedes, mueve los trabajos difíciles hacia allá desde Ajustes (hora de inicio de trabajo).")]
        if difs:
            out.append(UL(difs[:5]))
    out.append(P("Toca un método para ver cómo aplicarlo a tu semana."))
    return {"bloques": out, "sugerencias": [SUG(TECNICAS[t]["nombre"], "tecnica", id=t) for t, _ in tecs[:4]] + [SUG("Volver a empezar las preguntas", "entrevista_iniciar")],
            "perfil_completo": True}


# ----------------------------------------------------------------------------- recomendaciones -> conversación
def expandir_consejo(cj: dict, c: Ctx) -> dict:
    cat, tid = cj.get("categoria"), cj.get("tarea_id")
    out = [H(cj["titulo"]), P(cj["texto"])]
    if cj.get("accion"):
        out.append(P("Qué hacer: " + cj["accion"]))
    sug = []
    t = next((x for x in c.plan["tareas"] if x["id"] == tid), None) if tid else None

    if cat == "foco":
        hoy_b = c.bloques(c.hoy)
        if hoy_b:
            out += [P("Tu día, bloque por bloque:"), KV([(f"{b['inicio']}–{b['fin']}", b["titulo"]) for b in hoy_b])]
            largo = max(hoy_b, key=lambda b: a_min(b["fin"]) - a_min(b["inicio"]))
            out += [P(f"Para sostener el enfoque en el más largo ({largo['inicio']}–{largo['fin']}), trabájalo así:"), CICLO(50, 10, max(1, (a_min(largo['fin']) - a_min(largo['inicio'])) // 60))]
        sug += [SUG("Cómo evito distraerme con el celular", "tecnica", id="celular"), SUG("Cómo empiezo cuando me da pereza", "tecnica", id="procrastinacion")]
    elif cat == "riesgo":
        if t:
            asig = c.asignado_min(t["id"])
            out += [KV([("Entrega", _dia(fecha(t["due"]))), ("Dificultad", t["dificultad"]), ("Horas estimadas", _h(t["min"])), ("Horas con tiempo asignado", _h(asig)), ("Horas sin ubicar", _h(max(0, t["min"] - asig)))])]
        out += [P("Opciones, de la menos a la más costosa:"), OL(["Libera tiempo: mueve o marca como hechas las tareas que ya terminaste.", "Amplía tu disponibilidad: habilita un día de descanso o adelanta la hora de inicio de trabajo.", "Negocia: pide un alcance menor o una prórroga con anticipación, no el último día."])]
        if t:
            out += [P("Mensaje base para el profesor (edítalo con tus datos):"),
                    PLANTILLA(f"Buenas, profesor(a). Le escribo por «{t['titulo']}» de {t['materia']}, que se entrega el {_dia(fecha(t['due']))}. Estimo que necesito cerca de {_h(t['min'])} y, con mi carga de estas semanas, no alcanzo a completarlo con la calidad que quisiera. ¿Sería posible acordar una prórroga o ajustar el alcance? Puedo enviarle hoy un avance de lo que ya tengo. Gracias.")]
        sug += [SUG("Cómo priorizo mis entregas", "mensaje", texto="¿Cuáles son mis próximas entregas?")]
    elif cat == "estrategia":
        if t and t["tipo"] == "Parcial":
            out += _aplicar_espaciado(c, {}) + _aplicar_recuperacion(c, {})
            sug += [SUG("Qué es la repetición espaciada", "tecnica", id="espaciado"), SUG("Cómo hago la autoevaluación", "tecnica", id="recuperacion")]
        elif t and t["tipo"] in ("Proyecto", "Taller"):
            fs = c.fechas_tarea(t["id"])
            if len(fs) >= 3:
                out += [P("Un reparto en hitos sobre los días que el plan ya te asignó:"), FECHAS([("Diseño", _dia(fs[0])), ("Núcleo", _dia(fs[len(fs) // 2])), ("Pruebas", _dia(fs[-1])), ("Entrega", _dia(fecha(t["due"])))]),
                        UL(["Primer bloque: define el alcance, las tareas y quién hace qué.", "Bloque intermedio: deja funcionando lo esencial, aunque sea feo.", "Último bloque: pruebas, documentación y revisión; no agregues funciones nuevas."])]
            sug += [SUG("Cómo empiezo sin procrastinar", "tecnica", id="procrastinacion")]
        else:
            out += [P("Escribe un borrador de resultados y preguntas la misma noche de la práctica, mientras recuerdas lo que pasó; después solo pulirás.")]
            sug += [SUG("Planes si-entonces", "tecnica", id="si_entonces")]
    elif cat == "carga":
        dias = [(c.hoy + timedelta(days=i)) for i in range(0, 10)]
        out += [P("Horas de trabajo planeadas en los próximos 10 días:"), BARRAS([(f"{DIAS_CORTOS[d.weekday()]} {d.day}", round(c.horas_dia(d), 1)) for d in dias], "h", 6),
                P("Las barras que tocan el tope son los días de mayor presión: ahí conviene no agregar nada y, si puedes, adelantar desde los días más livianos.")]
        sug += [SUG("Bloques de enfoque con pausas", "tecnica", id="pomodoro"), SUG("Cuidar el sueño en semanas pesadas", "tecnica", id="sueno")]
    elif cat == "bienestar":
        out += tecnica_bloques("sueno", c)[2:5] + [P("Y mientras tanto, mueve el cuerpo:")] + tecnica_bloques("ejercicio", c)[3:5]
        sug += [SUG("Cómo manejo los nervios", "tecnica", id="ansiedad"), SUG("Bloques de enfoque con pausas", "tecnica", id="pomodoro")]
    elif cat == "estudio":
        ms = [(m["materia"], m["cumplido_h"], m["meta_h"]) for m in c.progreso["por_materia"]]
        out += [P("Tu meta semanal de estudio independiente por materia (según créditos):"), BARRAS([(m, meta) for m, _, meta in ms], "h")]
        out += tecnica_bloques("recuperacion", c)[3:6]
        sug += [SUG("Repetición espaciada", "tecnica", id="espaciado")]
    elif cat == "progreso":
        p = c.progreso
        out += [KV([("Tareas hechas", str(p["tareas"]["hechas"])), ("Racha de estudio", f"{p['racha_estudio']} días"), ("Horas esta semana", _h(p["semana"]["cumplido_h"] * 60))])]
        sug += [SUG("Ver mi progreso", "mensaje", texto="¿Cómo voy de progreso y racha?")]
    sug += [SUG("Hazme preguntas para conocerme", "entrevista_iniciar")]
    return {"bloques": out, "sugerencias": sug[:4]}


# ----------------------------------------------------------------------------- preguntas sobre los datos
def r_hoy(c: Ctx, dia: date | None = None) -> dict:
    d = dia or c.hoy
    cl, bl = c.clases(d), c.bloques(d)
    nombre = "hoy" if d == c.hoy else "mañana" if d == c.hoy + timedelta(days=1) else _dia(d)
    out = [H(f"Tu agenda de {nombre} ({_dia(d)})")]
    out += [P("Clases:"), KV([(f"{b['inicio']}–{b['fin']}", f"{b['materia']} {b['tipo']}" + (f" · {b['salon']}" if b.get("salon") else "")) for b in cl])] if cl else [P("No tienes clases.")]
    if bl:
        out += [P("Trabajo planeado:"), KV([(f"{b['inicio']}–{b['fin']}", b["titulo"]) for b in bl]), P(f"En total son {_h(sum(a_min(b['fin']) - a_min(b['inicio']) for b in bl))} de trabajo fuera de clase.")]
    else:
        out.append(P("No tienes trabajo planeado: es un buen día para adelantar o descansar."))
    return {"bloques": out, "sugerencias": [SUG("¿Cuáles son mis próximas entregas?", "mensaje", texto="¿Cuáles son mis próximas entregas?"), SUG("Cómo aprovecho mejor el día", "consejo_foco")]}


def r_ahora(c: Ctx) -> dict:
    ahora_min = c.ahora.hour * 60 + c.ahora.minute
    for k in range(0, 3):
        d = c.hoy + timedelta(days=k)
        eventos = [(a_min(b["inicio"]), a_min(b["fin"]), f"{b['materia']} {b['tipo']} (clase)") for b in c.clases(d)] + \
                  [(a_min(b["inicio"]), a_min(b["fin"]), b["titulo"]) for b in c.bloques(d)]
        for s, e, titulo in sorted(eventos):
            if k > 0 or e > ahora_min:
                estado = "Ahora" if k == 0 and s <= ahora_min < e else "Lo siguiente"
                return {"bloques": [H(estado + ": " + titulo), P(f"{_dia(d)} de {a_hhmm(s)} a {a_hhmm(e)}.")], "sugerencias": [SUG("Ver mi agenda de hoy", "mensaje", texto="¿Qué tengo hoy?")]}
    return {"bloques": [P("No encuentro nada próximo en tu agenda.")], "sugerencias": []}


def r_entregas(c: Ctx, preferir: str | None = None) -> dict:
    ts = [t for t in c.tareas() if fecha(t["due"]) >= c.hoy]
    if preferir:
        ts = sorted(ts, key=lambda t: (t["tipo"] != preferir, t["due"]))
    ts = ts[:5]
    if not ts:
        return {"bloques": [P("No tienes entregas pendientes.")], "sugerencias": []}
    filas = []
    for t in ts:
        dias = (fecha(t["due"]) - c.hoy).days
        cuando = "hoy" if dias == 0 else "mañana" if dias == 1 else f"en {dias} días"
        filas.append((t["titulo"], f"{_dia(fecha(t['due']))} ({cuando}) · {_h(t['min'])} · {t['dificultad']}"))
    out = [H("Tus próximas entregas"), KV(filas)]
    cerca = [t for t in ts if (fecha(t["due"]) - c.hoy).days <= 2]
    if cerca:
        out.append(P(f"Las más urgentes: {', '.join(t['titulo'] for t in cerca)}. Si alguna no te cabe, pídeme que te ayude a priorizar."))
    return {"bloques": out, "sugerencias": [SUG("¿Voy bien de tiempo?", "mensaje", texto="¿Voy atrasado o alcanzo todo?"), SUG("Cómo me preparo para el parcial", "tecnica", id="espaciado")]}


def r_semana(c: Ctx) -> dict:
    lun = c.hoy - timedelta(days=c.hoy.weekday())
    dias = [lun + timedelta(days=i) for i in range(7)]
    horas = [(f"{DIAS_CORTOS[d.weekday()]} {d.day}", round(c.horas_dia(d), 1)) for d in dias]
    total = sum(h for _, h in horas)
    out = [H("Trabajo planeado esta semana"), BARRAS(horas, "h", 6),
           P(f"Desde hoy son {_h(total * 60)} de trabajo fuera de clase repartidas en la semana, con un tope de {c.cfg.max_horas_dia:g} horas por día.")]
    necesario = sum(horas_independientes(m["codigo"], c.datos) for m in c.datos["materias"])
    out.append(P(f"Según tus créditos, tu meta de estudio independiente es de {_h(necesario * 60)} por semana en total."))
    return {"bloques": out, "sugerencias": [SUG("Ver mi progreso", "mensaje", texto="¿Cómo voy de progreso y racha?"), SUG("Cuándo tengo huecos libres", "mensaje", texto="¿Cuándo tengo tiempo libre?")]}


def r_materia(c: Ctx, materia: str) -> dict:
    cl = sorted([b for b in c.datos["bloques"] if b["materia"] == materia], key=lambda b: (b["dia"], a_min(b["inicio"])))
    cred = next(m["creditos"] for m in c.datos["materias"] if m["codigo"] == materia)
    out = [H(materia), KV([("Créditos", str(cred)), ("Trabajo total por semana", _h(horas_totales_semana(cred) * 60)), ("En clase", _h(contacto_semanal_min(materia, c.datos))), ("Estudio independiente", _h(horas_independientes(materia, c.datos) * 60))]),
           P("Tus clases:"), KV([(f"{DIAS[b['dia']]} {b['inicio']}–{b['fin']}", f"{b['tipo']}" + (f" · {b['salon']}" if b.get("salon") else "")) for b in cl])]
    ts = [t for t in c.tareas() if t["materia"] == materia][:4]
    if ts:
        out += [P("Lo pendiente de esta materia:"), KV([(t["titulo"], f"entrega {_dia(fecha(t['due']))}") for t in ts])]
    return {"bloques": out, "sugerencias": [SUG("Cómo estudio esta materia", "mensaje", texto="¿Cómo debería estudiar?"), SUG("¿Cuáles son mis próximas entregas?", "mensaje", texto="¿Cuáles son mis próximas entregas?")]}


def r_libre(c: Ctx) -> dict:
    filas = []
    for i in range(0, 6):
        d = c.hoy + timedelta(days=i)
        hs = c.huecos_libres(d)
        if hs:
            s, e = max(hs, key=lambda x: x[1] - x[0])
            filas.append((_dia(d), f"{a_hhmm(s)}–{a_hhmm(e)} ({_h(e - s)})"))
    out = [H("Tus huecos libres")]
    out += [P("Tu mayor tiempo sin usar en el plan, por día:"), KV(filas), P("Si vas bien con las entregas, usa uno de estos huecos para adelantar la tarea con la fecha más cercana.")] if filas else [P("Con tu disponibilidad actual el plan ya usa casi todo el tiempo libre.")]
    return {"bloques": out, "sugerencias": [SUG("Cómo uso mejor mis huecos", "tecnica", id="si_entonces")]}


def r_estado(c: Ctx) -> dict:
    adv = c.plan["advertencias"]
    altas = [x for x in c.consejos if x["nivel"] == "alta"]
    t = c.plan["tareas"]
    cub = sum(1 for x in t if c.asignado_min(x["id"]) >= x["min"])
    out = [H("¿Voy bien de tiempo?")]
    if adv:
        out += [P(f"Hay {len(adv)} cosa(s) que no te caben:"), UL([a["mensaje"] for a in adv])]
    else:
        out.append(P(f"Sí: todas tus {len(t)} tareas pendientes tienen su tiempo asegurado antes de la entrega."))
    sin_colchon = [x for x in c.consejos if x["titulo"].startswith("Sin colchón")]
    if sin_colchon:
        out.append(P("Ojo con el margen: " + "; ".join(x["titulo"] for x in sin_colchon) + "."))
    out.append(KV([("Tareas con tiempo asegurado", f"{cub} de {len(t)}"), ("Alertas urgentes", str(len(altas)))]))
    sug = [SUG(x["titulo"], "consejo", consejo=x) for x in altas[:2]] or [SUG("Ver mis recomendaciones", "mensaje", texto="¿Qué me recomiendas?")]
    return {"bloques": out, "sugerencias": sug}


def r_creditos(c: Ctx) -> dict:
    filas = [(m["codigo"], f"{m['creditos']} créditos · {_h(horas_totales_semana(m['creditos']) * 60)} por semana · {_h(horas_independientes(m['codigo'], c.datos) * 60)} de estudio propio") for m in c.datos["materias"]]
    return {"bloques": [H("Créditos y horas"), P("Un crédito equivale a 48 horas de trabajo en 16 semanas, es decir, 3 horas por semana. Lo que no pasas en clase es estudio independiente."), KV(filas)], "sugerencias": [SUG("Ver el trabajo planeado de esta semana", "mensaje", texto="¿Cuántas horas trabajo esta semana?")]}


def r_progreso(c: Ctx) -> dict:
    p = c.progreso
    if not p["hay_datos"]:
        return {"bloques": [H("Tu progreso"), P("Todavía no tienes sesiones registradas. Marca tus bloques como cumplidos o anota las horas reales al terminar un trabajo, y aquí verás tu avance y tu racha.")], "sugerencias": []}
    out = [H("Tu progreso"), KV([("Horas esta semana", f"{_h(p['semana']['cumplido_h'] * 60)} de {_h(p['semana']['planeado_h'] * 60)} planeadas"), ("Racha de estudio", f"{p['racha_estudio']} días (mejor: {p['mejor_racha_estudio']})"), ("Racha de uso", f"{p['racha_uso']} días"), ("Tareas hechas", f"{p['tareas']['hechas']} ({p['tareas']['pct']}% del total)")]),
           P("Horas cumplidas por semana:"), BARRAS([(f"{fecha(s['lunes']).day}/{fecha(s['lunes']).month}", s["cumplido_h"]) for s in p["semanas"]], "h")]
    return {"bloques": out, "sugerencias": [SUG("Cómo mantengo la racha", "tecnica", id="si_entonces")]}


def r_calibracion(c: Ctx) -> dict:
    t = resumen_calibracion(c.datos.get("historial", []), ["Taller", "Laboratorio", "Proyecto", "Parcial"])
    n = len(c.datos.get("historial", []))
    out = [H("Cuánto te toma cada trabajo"), P("Las horas por tipo de trabajo son estimaciones. Cuando terminas un trabajo y anotas cuánto tardaste, aprendo tu ritmo y ajusto los próximos." + (f" Llevas {n} registro(s)." if n else " Aún no tienes registros."))]
    out.append(KV([(x["tipo"], f"factor {x['factor']:.2f}".replace(".", ",") + f" ({x['registros']} registros)") for x in t]))
    return {"bloques": out, "sugerencias": []}


def r_metodos(c: Ctx, perfil: dict) -> dict:
    out = [H("Métodos de estudio con mejor respaldo"), P("De las técnicas revisadas en la literatura, estas son las que más rinden. Toca una para ver cómo aplicarla a tu semana:"),
           UL([f"{TECNICAS[k]['nombre']}: {TECNICAS[k]['que']}" for k in ("espaciado", "recuperacion", "intercalado", "autoexplicacion")]),
           P("Si quieres que te recomiende los más adecuados para ti, respóndeme unas preguntas."), EVID([REF["dunlosky"]])]
    return {"bloques": out, "sugerencias": [SUG("Hazme preguntas para conocerme", "entrevista_iniciar")] + sugerencias_tecnica(None, 3)}


def r_preparar(c: Ctx, materia: str | None) -> dict:
    cand = [t for t in c.tareas() if t["tipo"] in ("Parcial", "Proyecto") and not t["auto"] and (not materia or t["materia"] == materia)]
    t = cand[0] if cand else c.prueba_principal()
    if not t:
        return r_metodos(c, {})
    due = fecha(t["due"])
    dias = (due - c.hoy).days
    out = [H(f"Cómo preparar «{t['titulo']}»"), P(f"Se entrega el {_dia(due)} (en {dias} días) y su dificultad es {t['dificultad'].lower()}; el plan le reserva {_h(c.asignado_min(t['id']))} de estudio."),
           P("Combina dos métodos con buena evidencia: repartir los repasos y practicar recordando.")]
    out += _aplicar_espaciado(c, {}) + _aplicar_recuperacion(c, {})
    out += [P("Y trabaja cada bloque con este ritmo:"), CICLO(50, 10, 2), EVID([REF["cepeda"], REF["roediger"], REF["dunlosky"]])]
    return {"bloques": out, "sugerencias": [SUG("Repetición espaciada", "tecnica", id="espaciado"), SUG("Autoevaluación paso a paso", "tecnica", id="recuperacion"), SUG("Manejar los nervios", "tecnica", id="ansiedad")]}


def r_bienestar(c: Ctx) -> dict:
    out = [H("Bienestar y carga de estudio"), P("Estudiar más horas no ayuda si llegas cansado: el sueño, el movimiento y las pausas hacen parte del rendimiento."), UL([TECNICAS["sueno"]["nombre"] + ": " + TECNICAS["sueno"]["que"], TECNICAS["ejercicio"]["nombre"] + ": " + TECNICAS["ejercicio"]["que"], TECNICAS["pomodoro"]["nombre"] + ": " + TECNICAS["pomodoro"]["que"]]),
           EVID([REF["curcio"], REF["hillman"], REF["ariga"]])]
    return {"bloques": out, "sugerencias": [SUG("Cuidar el sueño", "tecnica", id="sueno"), SUG("Cómo manejo los nervios", "tecnica", id="ansiedad"), SUG("Movimiento y pausas activas", "tecnica", id="ejercicio")]}


def r_ayuda(c: Ctx) -> dict:
    return {"bloques": [H("En qué te puedo ayudar"), UL(["Tu agenda: qué tienes hoy o mañana, qué sigue, tus próximas entregas y tus huecos libres.", "Tu carga: cuántas horas trabajas esta semana, si vas bien de tiempo y cuánto te toca estudiar por materia.", "Métodos de estudio y bienestar: cómo preparar un parcial, concentrarte, recordar mejor, dormir y manejar los nervios.", "Tu progreso: horas cumplidas, tareas hechas y rachas.", "Conocerte: te hago unas preguntas y te armo un plan de estudio personal."]), P("Escríbeme con tus palabras o toca una de las opciones.")],
            "sugerencias": [SUG("¿Qué tengo hoy?", "mensaje", texto="¿Qué tengo hoy?"), SUG("Hazme preguntas para conocerme", "entrevista_iniciar"), SUG("¿Cuáles son mis próximas entregas?", "mensaje", texto="¿Cuáles son mis próximas entregas?")]}


def bienvenida(c: Ctx) -> dict:
    hoy_b = c.bloques(c.hoy)
    primera = f"Hoy tienes {len(hoy_b)} bloque(s) de trabajo ({_h(sum(a_min(b['fin']) - a_min(b['inicio']) for b in hoy_b))})." if hoy_b else "Hoy no tienes trabajo planeado."
    entrega = next((t for t in c.tareas() if fecha(t["due"]) >= c.hoy), None)
    seg = f" Tu próxima entrega es «{entrega['titulo']}» el {_dia(fecha(entrega['due']))}." if entrega else ""
    return {"bloques": [P("Hola, soy tu asistente. " + primera + seg), P("Puedo resolver dudas sobre tu horario, explicarte cada recomendación y proponerte métodos de estudio. Para recomendarte bien, también puedo hacerte unas preguntas.")],
            "sugerencias": [SUG("Hazme preguntas para conocerme", "entrevista_iniciar"), SUG("¿Qué tengo hoy?", "mensaje", texto="¿Qué tengo hoy?"), SUG("¿Voy bien de tiempo?", "mensaje", texto="¿Voy atrasado o alcanzo todo?")]}


# ----------------------------------------------------------------------------- intención
INTENCIONES = [
    ("entrevista", ["hazme preguntas", "conoceme", "conocerme", "personaliza", "mi perfil", "entrevista", "que metodo me conviene", "que tecnica me conviene"]),
    ("ayuda", ["ayuda", "que puedes", "que sabes", "como funciona", "que haces", "opciones"]),
    ("ahora", ["ahora mismo", "que sigue", "lo siguiente", "que toca ahora", "ahora"]),
    ("manana", ["manana"]),
    ("hoy", ["hoy", "mi dia", "agenda"]),
    ("entregas", ["entrega", "proxim", "fecha limite", "pendiente", "para cuando", "cuando es el"]),
    ("estado", ["atrasad", "retraso", "alcanzo", "voy bien", "no cabe", "riesgo", "llego a tiempo", "voy a llegar"]),
    ("semana", ["esta semana", "semana", "cuantas horas", "cuanto trabajo", "carga de"]),
    ("libre", ["libre", "hueco", "disponible", "adelantar", "tiempo para"]),
    ("creditos", ["credito", "horas por credito", "cuanto debo estudiar", "estudio independiente"]),
    ("progreso", ["racha", "progreso", "avance", "cuanto he estudiado", "estadistica", "como voy"]),
    ("calibracion", ["demoro", "tardo", "estimacion", "cuanto me toma", "calibra"]),
    ("bienestar", ["bienestar", "salud mental", "agotad", "burnout", "sobrecarg", "descansar"]),
    ("metodos", ["como estudio", "como estudiar", "como debo estudiar", "como deberia estudiar", "metodo", "tecnica", "estrategia", "tips", "estudiar mejor", "aprender mejor", "recomienda"]),
    ("saludo", ["hola", "buenas", "hey", "buenos dias", "buenas tardes", "buenas noches"]),
    ("gracias", ["gracias", "genial", "perfecto", "listo"]),
]


def _puntaje(n: str, claves: list[str]) -> int:
    return sum(1 for k in claves if re.search(r"\b" + re.escape(k), n))


def detectar(mensaje: str, c: Ctx) -> tuple[str, str | None]:
    n = _norm(mensaje)
    mejor_t, mejor_s = None, 0
    for t, claves in CLAVES_TECNICA.items():
        s = _puntaje(n, claves)
        if s > mejor_s:
            mejor_t, mejor_s = t, s
    mejor_i, mejor_si = None, 0
    for i, claves in INTENCIONES:
        s = _puntaje(n, claves)
        if s > mejor_si:
            mejor_i, mejor_si = i, s
    materia = c.materia_en(mensaje)
    if mejor_i == "entrevista":
        return "entrevista", None
    if re.search(r"\b(parcial|examen|prueba|quiz)", n):
        if re.search(r"\b(estudi|prepar|repas|como|ayuda)", n):
            return "preparar", materia
        if mejor_i in (None, "entregas") and mejor_t is None:
            return "entregas_parcial", None
    if materia and mejor_i not in ("entregas", "estado", "metodos") and mejor_t is None:
        return "materia", materia
    if mejor_t and (mejor_s > mejor_si or (mejor_s == mejor_si and mejor_i not in ("hoy", "manana", "ahora"))):
        return "tecnica", mejor_t
    if mejor_i:
        return mejor_i, None
    if mejor_t:
        return "tecnica", mejor_t
    if materia:
        return "materia", materia
    return "desconocido", None


# ----------------------------------------------------------------------------- punto de entrada
def responder(datos: dict, plan: dict, ahora: datetime, mensaje: str = "", accion: dict | None = None,
              llm_activo: bool = False, cfg: Config | None = None) -> dict:
    """Devuelve {bloques, sugerencias, [perfil], [llm_pendiente]}. `accion` viene de los botones de la interfaz."""
    c = Ctx(datos, plan, ahora, cfg)
    perfil = dict(datos.get("perfil") or {})
    accion = accion or {}
    tipo = accion.get("tipo")

    if tipo == "bienvenida":
        return bienvenida(c)
    if tipo == "consejo" and accion.get("consejo"):
        return expandir_consejo(accion["consejo"], c)
    if tipo == "consejo_foco":
        cj = next((x for x in c.consejos if x["categoria"] == "foco"), {"categoria": "foco", "titulo": "Tu día", "texto": "Así se ve tu día.", "accion": ""})
        return expandir_consejo(cj, c)
    if tipo == "tecnica" and accion.get("id") in TECNICAS:
        k = accion["id"]
        return {"bloques": tecnica_bloques(k, c, perfil), "sugerencias": sugerencias_tecnica(k, 2) + [SUG("Hazme preguntas para conocerme", "entrevista_iniciar")]}
    if tipo == "entrevista_iniciar":
        return {**_pregunta(0, c, "Te haré cinco preguntas cortas. Con tus respuestas te propongo los métodos que más te convienen."), "perfil": {}, "reiniciar_perfil": True}
    if tipo == "perfil" and accion.get("campo") in ETIQUETA and accion.get("valor") in ETIQUETA[accion["campo"]]:
        perfil[accion["campo"]] = accion["valor"]
        idx = [p[0] for p in PREGUNTAS].index(accion["campo"]) + 1
        if idx < len(PREGUNTAS):
            r = _pregunta(idx, c)
        else:
            r = plan_personal(perfil, c)
        r["perfil"] = perfil
        return r

    texto = (mensaje or "").strip()
    if not texto:
        return bienvenida(c)
    intencion, extra = detectar(texto, c)
    if intencion == "entrevista":
        return {**_pregunta(0, c, "Te haré cinco preguntas cortas. Con tus respuestas te propongo los métodos que más te convienen."), "perfil": {}, "reiniciar_perfil": True}
    if intencion == "tecnica":
        return {"bloques": tecnica_bloques(extra, c, perfil), "sugerencias": sugerencias_tecnica(extra, 2) + [SUG("Hazme preguntas para conocerme", "entrevista_iniciar")]}
    if intencion == "materia":
        return r_materia(c, extra)
    if intencion == "hoy":
        return r_hoy(c)
    if intencion == "manana":
        return r_hoy(c, c.hoy + timedelta(days=1))
    simples = {"ahora": r_ahora, "entregas": r_entregas, "estado": r_estado, "semana": r_semana, "libre": r_libre, "creditos": r_creditos,
               "progreso": r_progreso, "calibracion": r_calibracion, "bienestar": r_bienestar, "ayuda": r_ayuda}
    if intencion in simples:
        return simples[intencion](c)
    if intencion == "entregas_parcial":
        return r_entregas(c, "Parcial")
    if intencion == "preparar":
        return r_preparar(c, extra)
    if intencion == "metodos":
        return r_metodos(c, perfil)
    if intencion == "saludo":
        return bienvenida(c)
    if intencion == "gracias":
        return {"bloques": [P("Con gusto. Si quieres, seguimos con tu plan de estudio.")], "sugerencias": [SUG("Hazme preguntas para conocerme", "entrevista_iniciar"), SUG("¿Qué tengo hoy?", "mensaje", texto="¿Qué tengo hoy?")]}
    r = {"bloques": [P("No tengo una respuesta segura para eso con los datos de tu horario."), P("Puedo ayudarte con tu agenda, tus entregas, tu carga de la semana, métodos de estudio y bienestar.")],
         "sugerencias": [SUG("¿Qué puedes hacer?", "mensaje", texto="¿Qué puedes hacer?"), SUG("¿Qué tengo hoy?", "mensaje", texto="¿Qué tengo hoy?"), SUG("Hazme preguntas para conocerme", "entrevista_iniciar")]}
    if llm_activo:
        r["llm_pendiente"] = True
    return r


# ----------------------------------------------------------------------------- modelo local (opcional)
OLLAMA = os.environ.get("SEMESTRIA_OLLAMA", "http://127.0.0.1:11434")


def llm_estado() -> dict:
    """Si hay un modelo local disponible. Se desactiva con SEMESTRIA_SIN_LLM=1."""
    if os.environ.get("SEMESTRIA_SIN_LLM"):
        return {"disponible": False, "modelo": None}
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=0.6) as r:
            modelos = [m["name"] for m in json.load(r).get("models", [])]
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return {"disponible": False, "modelo": None}
    pref = os.environ.get("SEMESTRIA_MODELO")
    modelo = pref if pref in modelos else next((m for m in modelos if "qwen" in m or "llama" in m), modelos[0] if modelos else None)
    return {"disponible": bool(modelo), "modelo": modelo}


def contexto_texto(c: Ctx) -> str:
    """Resumen acotado de los datos del estudiante: es lo único que ve el modelo."""
    lineas = [f"Hoy es {_dia(c.hoy)}, {c.ahora:%H:%M}."]
    lineas.append("Materias: " + "; ".join(f"{m['codigo']} ({m['creditos']} créditos)" for m in c.datos["materias"]) + ".")
    for k, nombre in ((0, "Hoy"), (1, "Mañana")):
        d = c.hoy + timedelta(days=k)
        partes = [f"{b['inicio']}-{b['fin']} {b['materia']} {b['tipo']}" for b in c.clases(d)] + [f"{b['inicio']}-{b['fin']} trabajo: {b['titulo']}" for b in c.bloques(d)]
        lineas.append(f"{nombre}: " + (", ".join(partes) if partes else "sin actividades") + ".")
    ent = [f"{t['titulo']} ({_dia(fecha(t['due']))}, {t['dificultad']})" for t in c.tareas() if fecha(t["due"]) >= c.hoy][:4]
    lineas.append("Próximas entregas: " + ("; ".join(ent) if ent else "ninguna") + ".")
    if c.datos.get("perfil"):
        lineas.append("Perfil del estudiante: " + ", ".join(f"{NOMBRES_CAMPO[k]}={ETIQUETA[k].get(v, v)}" for k, v in c.datos["perfil"].items() if k in NOMBRES_CAMPO) + ".")
    return " ".join(lineas)


def consultar_llm(c: Ctx, pregunta: str, historial: list[dict] | None = None, timeout: int = 90) -> dict:
    est = llm_estado()
    if not est["disponible"]:
        return {"texto": None, "modelo": None}
    sistema = ("Eres el asistente académico de SemestrIA. Responde siempre en español, de forma breve (máximo 110 palabras) y cálida. "
               "Solo ayudas con: el horario y las entregas del estudiante, organización del tiempo, métodos de estudio y bienestar académico. "
               "Si la pregunta es de otro tema, responde en una frase que solo puedes ayudar con eso y ofrece alguna de esas opciones. "
               "Usa SOLO los datos del contexto para hablar del horario, las entregas o las fechas; si algo no está en el contexto, di que no lo sabes. "
               "Nunca inventes fechas, notas, libros, estudios ni datos, y no cites fuentes concretas. "
               "Para consejos de estudio usa principios generales (autoevaluación, repaso espaciado, pausas, sueño, planear el primer paso). "
               "No des consejos médicos. Contexto: " + contexto_texto(c))
    msgs = [{"role": "system", "content": sistema}]
    for m in (historial or [])[-4:]:
        if m.get("rol") in ("user", "assistant") and isinstance(m.get("txt"), str):
            msgs.append({"role": m["rol"], "content": m["txt"][:600]})
    msgs.append({"role": "user", "content": pregunta[:800]})
    cuerpo = {"model": est["modelo"], "stream": False, "messages": msgs, "options": {"temperature": 0.3, "num_predict": 220}}
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(cuerpo).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            texto = json.load(r)["message"]["content"].strip()
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        return {"texto": None, "modelo": est["modelo"]}
    return {"texto": texto or None, "modelo": est["modelo"]}
