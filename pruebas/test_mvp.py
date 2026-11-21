"""Pruebas del MVP: validación de horarios, recomendaciones, calibración y API HTTP.
Ejecutar:  python -m unittest discover -s pruebas -v
"""
import copy
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from motor.asesor import consejos, indicadores, validar_datos
from motor.calibracion import F_MAX, F_MIN, factor_calibracion, factor_global
from motor.semestria import cargar, planificar
from servidor import Handler

RUTA = os.path.join(os.path.dirname(__file__), "..", "datos", "horario_ejemplo.json")
AHORA = datetime(2026, 10, 12, 9, 0)


def base():
    return cargar(RUTA)


class TestValidacion(unittest.TestCase):
    def test_el_ejemplo_es_valido(self):
        datos, errores = validar_datos(base())
        self.assertEqual(errores, [])
        self.assertEqual(len(datos["materias"]), 6)

    def test_rellena_valores_por_defecto(self):
        datos, errores = validar_datos({"semestre_inicio": "2026-08-24",
                                        "bloques": [{"materia": "X", "dia": 0, "inicio": "08:00", "fin": "09:30"}]})
        self.assertEqual(errores, [])
        self.assertEqual(datos["bloques"][0]["tipo"], "LEC")
        self.assertEqual(datos["materias"], [{"codigo": "X", "creditos": 3}])   # materia detectada desde el horario
        self.assertEqual(len(datos["disponibilidad"]), 7)
        self.assertEqual(datos["historial"], [])

    def test_rechaza_entradas_invalidas(self):
        casos = [
            ([], "objeto JSON"),
            ({"semestre_inicio": "ayer", "bloques": [{"materia": "X", "dia": 0, "inicio": "08:00", "fin": "09:00"}]}, "semestre_inicio"),
            ({"semestre_inicio": "2026-08-24", "bloques": []}, "bloques"),
            ({"semestre_inicio": "2026-08-24", "bloques": [{"materia": "X", "dia": 9, "inicio": "08:00", "fin": "09:00"}]}, "Bloque #1"),
            ({"semestre_inicio": "2026-08-24", "bloques": [{"materia": "X", "dia": 0, "inicio": "10:00", "fin": "09:00"}]}, "Bloque #1"),
        ]
        for entrada, texto in casos:
            datos, errores = validar_datos(entrada)
            self.assertIsNone(datos)
            self.assertTrue(any(texto in e for e in errores), (entrada, errores))

    def test_rechaza_trabajo_de_materia_desconocida(self):
        d = base()
        d["trabajos"].append({"id": "z", "materia": "NO EXISTE", "tipo": "Parcial", "titulo": "?", "entrega": "2026-10-30", "dificultad": "Medio"})
        datos, errores = validar_datos(d)
        self.assertIsNone(datos)
        self.assertTrue(any("Trabajo inválido" in e for e in errores))


class TestRecomendaciones(unittest.TestCase):
    def setUp(self):
        self.d = base()
        self.plan = planificar(self.d, AHORA)

    def test_estructura_de_cada_consejo(self):
        for c in consejos(self.d, self.plan, AHORA):
            self.assertIn(c["nivel"], ("alta", "media", "info"))
            self.assertTrue(c["titulo"] and c["texto"])
            self.assertIn("accion", c)

    def test_el_foco_de_hoy_va_primero_y_nombra_la_hora(self):
        primero = consejos(self.d, self.plan, AHORA)[0]
        self.assertEqual(primero["categoria"], "foco")
        self.assertIn("09:00", primero["texto"])

    def test_tarea_imposible_genera_consejo_urgente_primero_entre_los_urgentes(self):
        self.d["trabajos"].append({"id": "x1", "materia": "ISIS ARSW", "tipo": "Proyecto", "titulo": "Imposible",
                                   "entrega": "2026-10-13", "dificultad": "Difícil", "horas": 40})
        plan = planificar(self.d, AHORA)
        altas = [c for c in consejos(self.d, plan, AHORA) if c["nivel"] == "alta"]
        self.assertEqual(len(altas), 1)
        self.assertEqual(altas[0]["tarea_id"], "x1")
        self.assertIn("Elige una", altas[0]["accion"])

    def test_trabajo_vencido(self):
        self.d["trabajos"].append({"id": "v1", "materia": "ISIS ARSW", "tipo": "Taller", "titulo": "Viejo",
                                   "entrega": "2026-10-01", "dificultad": "Fácil"})
        altas = [c for c in consejos(self.d, planificar(self.d, AHORA), AHORA) if c["nivel"] == "alta"]
        self.assertTrue(any("Vencido" in c["titulo"] for c in altas))

    def test_calibracion_solo_aparece_con_suficientes_registros(self):
        sin = [c["titulo"] for c in consejos(self.d, self.plan, AHORA)]
        self.assertTrue(any("Registra cuánto" in t for t in sin))
        self.d["historial"] = [{"tipo": "Taller", "base_h": 2, "real_h": 3} for _ in range(4)]
        con = [c["titulo"] for c in consejos(self.d, planificar(self.d, AHORA), AHORA)]
        self.assertTrue(any("más de lo estimado" in t for t in con))

    def test_indicadores(self):
        i = indicadores(self.d, self.plan, AHORA)
        self.assertEqual(i["tareas_pendientes"], i["tareas_cubiertas"])
        self.assertEqual(i["proxima_entrega"]["titulo"], "Parcial 2 de ECDI")
        self.assertEqual(i["dias_proxima"], 8)


class TestCalibracion(unittest.TestCase):
    def test_sin_historial_el_factor_es_uno(self):
        self.assertEqual(factor_calibracion([], "Taller"), 1.0)
        self.assertEqual(factor_global([]), 1.0)

    def test_converge_hacia_la_razon_observada_sin_igualarla(self):
        h = [{"tipo": "Taller", "base_h": 2, "real_h": 3}] * 5
        f = factor_calibracion(h, "Taller")
        self.assertTrue(1.3 < f < 1.5)
        mas = factor_calibracion(h * 10, "Taller")
        self.assertTrue(f < mas < 1.5)          # más datos -> más cerca de 1,5

    def test_acotado(self):
        self.assertEqual(factor_calibracion([{"tipo": "Taller", "base_h": 1, "real_h": 9}] * 200, "Taller"), F_MAX)
        self.assertEqual(factor_calibracion([{"tipo": "Taller", "base_h": 9, "real_h": 1}] * 200, "Taller"), F_MIN)

    def test_ignora_registros_invalidos(self):
        basura = [{"tipo": "Taller", "base_h": 0, "real_h": 2}, {"tipo": "Taller", "base_h": "x", "real_h": 2},
                  {"tipo": "Taller", "base_h": 1, "real_h": 100}, {"tipo": "Taller"}, {"tipo": "Taller", "base_h": 2, "real_h": -1}]
        self.assertEqual(factor_calibracion(basura, "Taller"), 1.0)

    def test_un_tipo_sin_datos_hereda_la_tendencia_global_pero_menos(self):
        h = [{"tipo": "Taller", "base_h": 2, "real_h": 4}] * 6
        self.assertTrue(1.0 < factor_calibracion(h, "Parcial") < factor_calibracion(h, "Taller"))

    def test_afecta_al_plan_pero_no_a_horas_fijadas(self):
        d = base()
        sin = {t["id"]: t["min"] for t in planificar(d, AHORA)["tareas"]}
        d["historial"] = [{"tipo": t, "base_h": 2, "real_h": 3} for t in ("Taller", "Parcial", "Laboratorio", "Proyecto")] * 3
        con = {t["id"]: t["min"] for t in planificar(d, AHORA)["tareas"]}
        self.assertGreater(con["m1"], sin["m1"])      # parcial con horas estimadas por el sistema
        self.assertEqual(con["m3"], sin["m3"])        # proyecto con horas fijadas por el estudiante


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def pedir(self, ruta, cuerpo=None):
        req = urllib.request.Request(self.url + ruta, data=None if cuerpo is None else (cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode()),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_flujo_completo(self):
        st, cuerpo = self.pedir("/api/ejemplo")
        self.assertEqual(st, 200)
        st, cuerpo = self.pedir("/api/importar", json.loads(cuerpo))
        self.assertEqual(st, 200)
        datos = json.loads(cuerpo)["datos"]
        st, cuerpo = self.pedir("/api/plan", {"datos": datos, "ahora": "2026-10-12T09:00", "config": {"max_horas_dia": 6, "usar_huecos": True}})
        self.assertEqual(st, 200)
        plan = json.loads(cuerpo)
        for k in ("bloques", "advertencias", "consejos", "indicadores", "materias", "calibracion", "tareas", "resumen"):
            self.assertIn(k, plan)
        self.assertEqual(len(plan["bloques"]), 67)

    def test_importar_invalido_da_422_con_errores(self):
        st, cuerpo = self.pedir("/api/importar", {"semestre_inicio": "x", "bloques": []})
        self.assertEqual(st, 422)
        self.assertTrue(json.loads(cuerpo)["errores"])

    def test_json_malformado_da_400(self):
        st, cuerpo = self.pedir("/api/importar", b"no es json")
        self.assertEqual(st, 400)
        self.assertIn("JSON", json.loads(cuerpo)["error"])

    def test_plan_sin_datos_da_400(self):
        st, _ = self.pedir("/api/plan", {"ahora": "2026-10-12T09:00"})
        self.assertEqual(st, 400)

    def test_la_interfaz_se_sirve_y_no_se_sale_de_la_carpeta(self):
        st, cuerpo = self.pedir("/")
        self.assertEqual(st, 200)
        self.assertIn(b"SemestrIA", cuerpo)
        for ruta in ("/app.js", "/estilos.css"):
            self.assertEqual(self.pedir(ruta)[0], 200)
        self.assertEqual(self.pedir("/../servidor.py")[0], 404)
        self.assertEqual(self.pedir("/..%2fservidor.py")[0], 404)


if __name__ == "__main__":
    unittest.main()
