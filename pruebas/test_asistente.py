"""Pruebas del asistente personal y del progreso. Se ejecutan sin modelo de lenguaje (SEMESTRIA_SIN_LLM=1).
Ejecutar:  python -m unittest discover -s pruebas -v
"""
import json
import os
import sys
import threading
import unittest
import urllib.request
from datetime import date, datetime, timedelta
from http.server import ThreadingHTTPServer

os.environ["SEMESTRIA_SIN_LLM"] = "1"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from motor.asistente import (PREGUNTAS, TECNICAS, Ctx, _repasos, detectar, expandir_consejo, llm_estado, responder,
                             tecnicas_para)
from motor.asesor import consejos, validar_datos
from motor.progreso import estadisticas, rachas
from motor.semestria import cargar, planificar
from servidor import Handler

RUTA = os.path.join(os.path.dirname(__file__), "..", "datos", "horario_ejemplo.json")
AHORA = datetime(2026, 10, 12, 9, 0)


def preparar(datos=None):
    d = datos or cargar(RUTA)
    return d, planificar(d, AHORA)


def textos(r):
    """Todo el texto de una respuesta, para buscar contenido."""
    out = []
    for b in r["bloques"]:
        for k in ("txt",):
            if k in b:
                out.append(b[k])
        for it in b.get("items", []):
            out.append(" ".join(it) if isinstance(it, list) else str(it))
    return "\n".join(out)


class TestProgreso(unittest.TestCase):
    def test_racha_actual_y_mejor(self):
        hoy = date(2026, 10, 12)
        dias = {hoy - timedelta(days=i) for i in (0, 1, 2)} | {hoy - timedelta(days=i) for i in (6, 7, 8, 9, 10)}
        self.assertEqual(rachas(dias, hoy), (3, 5))

    def test_la_racha_no_se_rompe_si_hoy_aun_no_tiene_actividad(self):
        hoy = date(2026, 10, 12)
        self.assertEqual(rachas({hoy - timedelta(days=1), hoy - timedelta(days=2)}, hoy)[0], 2)
        self.assertEqual(rachas({hoy - timedelta(days=2)}, hoy)[0], 0)      # ayer sin actividad: se rompió

    def test_sin_registros(self):
        d, p = preparar()
        e = estadisticas(d, p, AHORA)
        self.assertFalse(e["hay_datos"])
        self.assertEqual(e["semana"]["cumplido_h"], 0)
        self.assertEqual(e["racha_estudio"], 0)

    def test_acumula_horas_por_semana_y_materia(self):
        d, p = preparar()
        d["sesiones"] = [{"fecha": "2026-10-12", "min": 120, "materia": "MATE ECDI"}, {"fecha": "2026-10-13", "min": 60, "materia": "MATE ECDI"},
                         {"fecha": "2026-10-05", "min": 90, "materia": "ISIS ARSW"}, {"fecha": "basura", "min": 30}, {"fecha": "2026-10-06", "min": -5}]
        d["hechas_fecha"] = {"m1": "2026-10-12"}
        d["hechas"] = ["m1"]
        d["uso"] = ["2026-10-10", "2026-10-11", "2026-10-12"]
        e = estadisticas(d, p, AHORA)
        self.assertEqual(e["semana"]["cumplido_h"], 3.0)
        self.assertEqual(e["semanas"][-1]["tareas_hechas"], 1)
        self.assertEqual(e["semanas"][-2]["cumplido_h"], 1.5)
        self.assertEqual(next(m for m in e["por_materia"] if m["materia"] == "MATE ECDI")["cumplido_h"], 3.0)
        self.assertEqual(e["racha_uso"], 3)
        self.assertEqual(e["total_h"], 4.5)
        self.assertEqual(len(e["dias"]), 35)
        self.assertEqual(e["dias"][-1]["h"], 2.0)
        self.assertTrue(e["hay_datos"])

    def test_porcentajes_y_necesario(self):
        d, p = preparar()
        d["sesiones"] = [{"fecha": "2026-10-12", "min": 60, "materia": "MATE ECDI"}]
        e = estadisticas(d, p, AHORA)
        self.assertAlmostEqual(e["semana"]["necesario_h"], 38.2, delta=0.1)        # 20 créditos x 3 h - clases
        self.assertGreater(e["semana"]["planeado_h"], e["semana"]["cumplido_h"])
        self.assertEqual(e["semana"]["pct_necesario"], round(100 * 1 / e["semana"]["necesario_h"]))

    def test_validar_conserva_los_datos_de_progreso(self):
        d = cargar(RUTA)
        d.update({"sesiones": [{"fecha": "2026-10-12", "min": 30}], "hechas_fecha": {"m1": "2026-10-12"}, "uso": ["2026-10-12"], "perfil": {"momento": "manana"}})
        out, err = validar_datos(d)
        self.assertEqual(err, [])
        for k in ("sesiones", "hechas_fecha", "uso", "perfil"):
            self.assertIn(k, out)


class TestAsistente(unittest.TestCase):
    def setUp(self):
        self.d, self.p = preparar()

    def r(self, msg="", accion=None, llm=False):
        return responder(self.d, self.p, AHORA, msg, accion, llm_activo=llm)

    def test_agenda_de_hoy_con_datos_reales(self):
        t = textos(self.r("¿Qué tengo hoy?"))
        self.assertIn("09:00–11:00", t)
        self.assertIn("Taller MATE ECDI", t)
        self.assertEqual(textos(self.r("que tengo hoy")), t)               # sin tildes ni signos da lo mismo

    def test_manana_muestra_las_clases_de_manana(self):
        t = textos(self.r("¿y mañana?"))
        self.assertIn("martes 13/10", t)
        self.assertIn("ISIS ARSW LEC", t)

    def test_entregas_y_parcial(self):
        t = textos(self.r("¿cuándo es mi parcial?"))
        self.assertIn("Parcial 2 de ECDI", t)
        self.assertIn("20/10", t)
        primera = self.r("¿cuándo es mi parcial?")["bloques"][1]["items"][0][0]
        self.assertEqual(primera, "Parcial 2 de ECDI")                      # el parcial va primero

    def test_materia(self):
        t = textos(self.r("¿cuándo tengo clase de ECDI?"))
        self.assertIn("MATE ECDI", t)
        self.assertIn("Jueves 14:30–16:00", t)

    def test_semana_incluye_grafica(self):
        r = self.r("¿cuántas horas trabajo esta semana?")
        barras = next(b for b in r["bloques"] if b["t"] == "barras")
        self.assertEqual(len(barras["items"]), 7)
        self.assertLessEqual(max(v for _, v in barras["items"]), 6)

    def test_estado_dice_la_verdad(self):
        self.assertIn("Sí: todas", textos(self.r("¿voy atrasado?")))
        self.d["trabajos"].append({"id": "x1", "materia": "ISIS ARSW", "tipo": "Proyecto", "titulo": "Imposible", "entrega": "2026-10-13", "dificultad": "Difícil", "horas": 40})
        self.p = planificar(self.d, AHORA)
        t = textos(self.r("¿voy atrasado?"))
        self.assertIn("no alcanza", t.lower())
        self.assertNotIn("Sí: todas", t)

    def test_metodos_tienen_evidencia_y_pasos(self):
        for k in TECNICAS:
            r = self.r(accion={"tipo": "tecnica", "id": k})
            tipos = [b["t"] for b in r["bloques"]]
            self.assertIn("ol", tipos, k)
            self.assertIn("evidencia", tipos, k)

    def test_deteccion_de_temas(self):
        c = Ctx(self.d, self.p, AHORA)
        casos = {"me da pereza empezar": "procrastinacion", "me distrae el celular": "celular", "no duermo bien": "sueno",
                 "tengo nervios en los examenes": "ansiedad", "cómo hago repaso espaciado": "espaciado", "quiero hacer pausas": "pomodoro"}
        for msg, esperado in casos.items():
            self.assertEqual(detectar(msg, c), ("tecnica", esperado), msg)

    def test_parcial_con_ansiedad_va_a_ansiedad_no_a_entregas(self):
        self.assertEqual(detectar("me da ansiedad el examen", Ctx(self.d, self.p, AHORA)), ("tecnica", "ansiedad"))

    def test_preparar_parcial_aplica_los_metodos_con_fechas(self):
        r = self.r("¿cómo estudio para el parcial de ECDI?")
        t = textos(r)
        self.assertIn("Parcial 2 de ECDI", t)
        fechas = next(b for b in r["bloques"] if b["t"] == "fechas")
        self.assertEqual(fechas["items"][-1][1], "martes 20/10")

    def test_los_repasos_nunca_pasan_de_la_entrega(self):
        for dias in (1, 2, 4, 10, 30):
            due = date(2026, 10, 12) + timedelta(days=dias)
            rep = _repasos(date(2026, 10, 12), due)
            self.assertTrue(rep and all(x < due for x in rep), (dias, rep))
            self.assertEqual(rep, sorted(set(rep)))

    def test_cada_recomendacion_se_puede_expandir(self):
        self.d["historial"] = [{"tipo": "Taller", "base_h": 2, "real_h": 3}] * 4
        self.d["hechas"] = ["m2"]
        self.p = planificar(self.d, AHORA)
        c = Ctx(self.d, self.p, AHORA)
        lista = consejos(self.d, self.p, AHORA)
        self.assertGreaterEqual(len(lista), 5)
        for cj in lista:
            r = expandir_consejo(cj, c)
            self.assertEqual(r["bloques"][0], {"t": "h", "txt": cj["titulo"]})
            self.assertTrue(len(r["bloques"]) >= 3, cj["titulo"])
            self.assertTrue(r["sugerencias"])

    def test_recomendacion_de_riesgo_trae_mensaje_para_el_profesor(self):
        self.d["trabajos"].append({"id": "x1", "materia": "ISIS ARSW", "tipo": "Proyecto", "titulo": "Imposible", "entrega": "2026-10-13", "dificultad": "Difícil", "horas": 40})
        self.p = planificar(self.d, AHORA)
        cj = next(x for x in consejos(self.d, self.p, AHORA) if x["nivel"] == "alta")
        r = self.r(accion={"tipo": "consejo", "consejo": cj})
        pl = next(b for b in r["bloques"] if b["t"] == "plantilla")
        self.assertIn("Imposible", pl["txt"])
        self.assertIn("40 h", pl["txt"])

    def test_entrevista_completa(self):
        r = self.r(accion={"tipo": "entrevista_iniciar"})
        self.assertIn("Pregunta 1 de 5", textos(r))
        perfil = {}
        respuestas = {"momento": "manana", "estilo": "releer", "distraccion": "celular", "sueno": "menos6", "reto": "empezar"}
        for i, (campo, _, ops) in enumerate(PREGUNTAS):
            valores = [s["accion"]["valor"] for s in r["sugerencias"]]
            self.assertIn(respuestas[campo], valores)
            self.d["perfil"] = perfil
            r = self.r(accion={"tipo": "perfil", "campo": campo, "valor": respuestas[campo]})
            perfil = r["perfil"]
        self.assertTrue(r.get("perfil_completo"))
        self.assertEqual(perfil, respuestas)
        t = textos(r)
        self.assertIn("Tu plan de estudio personal", t)
        self.assertIn("Dormir como parte del estudio", t)                  # duerme menos de 6 h: va primero
        self.assertIn("Tus mejores horas", t)

    def test_tecnicas_para_prioriza_segun_perfil(self):
        self.assertEqual(tecnicas_para({"sueno": "menos6", "reto": "recordar"})[0][0], "sueno")
        self.assertEqual(tecnicas_para({"reto": "concentracion", "sueno": "7a8"})[0][0], "pomodoro")
        t = [x for x, _ in tecnicas_para({"estilo": "releer"})]
        self.assertIn("recuperacion", t)
        self.assertEqual(len(t), len(set(t)))

    def test_valores_de_perfil_invalidos_se_ignoran(self):
        r = self.r(accion={"tipo": "perfil", "campo": "momento", "valor": "inventado"})
        self.assertNotIn("perfil", r)

    def test_pregunta_desconocida_no_inventa(self):
        r = self.r("¿quién ganó el mundial?")
        self.assertIn("No tengo una respuesta segura", textos(r))
        self.assertNotIn("llm_pendiente", r)
        self.assertTrue(self.r("¿quién ganó el mundial?", llm=True)["llm_pendiente"])

    def test_bienvenida_y_ayuda(self):
        self.assertIn("próxima entrega", textos(self.r()))
        self.assertIn("En qué te puedo ayudar", textos(self.r("¿qué puedes hacer?")))

    def test_el_modelo_solo_recibe_un_resumen_acotado(self):
        from motor.asistente import contexto_texto
        self.d["perfil"] = {"momento": "manana"}
        t = contexto_texto(Ctx(self.d, self.p, AHORA))
        self.assertIn("Hoy es lunes 12/10", t)
        self.assertIn("Parcial 2 de ECDI", t)
        self.assertIn("Mejor momento=Por la mañana", t)
        self.assertNotIn("C C1-203", t)                  # no se envían salones ni el JSON completo
        self.assertLess(len(t), 2500)

    def test_sin_modelo_local_el_estado_es_no_disponible(self):
        self.assertEqual(llm_estado(), {"disponible": False, "modelo": None})


class TestAPIAsistente(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def post(self, ruta, cuerpo):
        req = urllib.request.Request(self.url + ruta, data=json.dumps(cuerpo).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def test_chat_y_estado(self):
        d = cargar(RUTA)
        base = {"datos": d, "ahora": "2026-10-12T09:00"}
        st, r = self.post("/api/chat", {**base, "mensaje": "¿Qué tengo hoy?"})
        self.assertEqual(st, 200)
        self.assertIn("09:00–11:00", textos(r))
        st, r = self.post("/api/chat", {**base, "accion": {"tipo": "entrevista_iniciar"}})
        self.assertEqual(st, 200)
        self.assertEqual(len(r["sugerencias"]), 4)
        st, r = self.post("/api/chat_llm", {**base, "mensaje": "hola"})
        self.assertEqual((st, r["texto"]), (200, None))                      # sin modelo local no inventa nada
        st, _ = self.post("/api/chat_llm", {**base, "mensaje": ""})
        self.assertEqual(st, 400)
        with urllib.request.urlopen(self.url + "/api/asistente_estado") as resp:
            self.assertFalse(json.load(resp)["disponible"])

    def test_plan_incluye_progreso(self):
        st, p = self.post("/api/plan", {"datos": cargar(RUTA), "ahora": "2026-10-12T09:00"})
        self.assertEqual(st, 200)
        self.assertIn("progreso", p)
        self.assertEqual(len(p["progreso"]["semanas"]), 8)


if __name__ == "__main__":
    unittest.main()
