"""Pruebas del motor de SemestrIA.  Ejecutar:  python -m unittest discover -s pruebas -v"""
import copy
import os
import sys
import unittest
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from motor.semestria import (Config, a_min, bloques_del_dia, cargar, contacto_semanal_min, creditos_de, fecha,
                             horas_estimadas, horas_independientes, horas_totales_semana, paridad, planificar,
                             semana_del_semestre, sesion_ocurre, tareas_automaticas, ventanas_libres)

RUTA = os.path.join(os.path.dirname(__file__), "..", "datos", "horario_ejemplo.json")
AHORA = datetime(2026, 10, 12, 9, 0)  # lunes, semana 8 (par)


def datos_base():
    return cargar(RUTA)


class TestCreditosATiempo(unittest.TestCase):
    def test_horas_totales_por_credito(self):
        # 48 h por crédito en 16 semanas = 3 h/semana por crédito (Decreto 1330 de 2019)
        self.assertEqual(horas_totales_semana(1), 3.0)
        self.assertEqual(horas_totales_semana(4), 12.0)

    def test_independientes_son_total_menos_clase(self):
        d = datos_base()
        # MATE ECDI: 4 créditos = 12 h/sem; 3 clases de 1.5 h = 4.5 h -> 7.5 h independientes
        self.assertEqual(contacto_semanal_min("MATE ECDI", d), 270)
        self.assertEqual(horas_independientes("MATE ECDI", d), 7.5)

    def test_laboratorio_quincenal_cuenta_la_mitad(self):
        d = datos_base()
        # PTIA: clase 1.5 h + lab quincenal 1.5 h (promedia 0.75 h) = 2.25 h
        self.assertEqual(contacto_semanal_min("ISIS PTIA", d), 135)

    def test_nunca_negativas(self):
        d = datos_base()
        d["materias"][0]["creditos"] = 1  # FDSI tiene 4.5 h de clase > 3 h totales
        self.assertEqual(horas_independientes("ISIS FDSI", d), 0.0)


class TestHorarioYSemanas(unittest.TestCase):
    def test_semana_y_paridad(self):
        d = datos_base()
        sem = semana_del_semestre(AHORA.date(), fecha(d["semestre_inicio"]))
        self.assertEqual(sem, 8)
        self.assertEqual(paridad(sem), "par")

    def test_lab_quincenal_solo_en_semanas_pares(self):
        d = datos_base()
        lab = next(b for b in d["bloques"] if b["materia"] == "ISIS FDSI" and b["tipo"] == "LAB")
        self.assertTrue(sesion_ocurre(lab, date(2026, 10, 15), d))   # semana 8 (par)
        self.assertFalse(sesion_ocurre(lab, date(2026, 10, 22), d))  # semana 9 (impar)

    def test_semana_sin_lab_libera_el_bloque(self):
        d = datos_base()
        par = ventanas_libres(date(2026, 10, 15), d, Config())    # jueves con lab FDSI (7-10)
        impar = ventanas_libres(date(2026, 10, 22), d, Config())  # jueves sin lab
        self.assertEqual(par, [(10 * 60, 13 * 60), (17 * 60, 21 * 60)])
        self.assertEqual(impar, [(7 * 60, 13 * 60), (17 * 60, 21 * 60)])

    def test_inicio_de_trabajo_tras_la_salida(self):
        d = datos_base()
        # martes: sale 16:00, el estudiante empieza a las 17:00 -> no hay ventana 16:00-17:00
        v = ventanas_libres(date(2026, 10, 13), d, Config())
        self.assertEqual(v, [(7 * 60, 11 * 60 + 30), (17 * 60, 21 * 60)])

    def test_dia_de_descanso_sin_ventanas(self):
        self.assertEqual(ventanas_libres(date(2026, 10, 18), datos_base(), Config()), [])


class TestPlanificador(unittest.TestCase):
    def setUp(self):
        self.d = datos_base()
        self.plan = planificar(self.d, AHORA)
        self.cfg = Config()

    def test_ningun_bloque_choca_con_una_clase(self):
        for b in self.plan["bloques"]:
            f = fecha(b["fecha"])
            for c in bloques_del_dia(f, self.d):
                solapa = a_min(b["inicio"]) < a_min(c["fin"]) and a_min(c["inicio"]) < a_min(b["fin"])
                self.assertFalse(solapa, f"{b['titulo']} choca con {c['materia']} el {b['fecha']}")

    def test_ningun_bloque_se_solapa_con_otro(self):
        por_dia = {}
        for b in self.plan["bloques"]:
            por_dia.setdefault(b["fecha"], []).append((a_min(b["inicio"]), a_min(b["fin"])))
        for dia, lista in por_dia.items():
            lista.sort()
            for (s1, e1), (s2, e2) in zip(lista, lista[1:]):
                self.assertLessEqual(e1, s2, f"solape el {dia}")

    def test_respeta_hora_de_inicio_de_trabajo_y_limites_del_dia(self):
        for b in self.plan["bloques"]:
            f = fecha(b["fecha"])
            ini, fin = a_min(b["inicio"]), a_min(b["fin"])
            self.assertGreaterEqual(ini, self.cfg.dia_inicio)
            self.assertLessEqual(fin, self.cfg.dia_fin)
            self.assertNotEqual(f.weekday(), 6, "no debe recomendar trabajo en el día de descanso")
            if f == AHORA.date():
                self.assertGreaterEqual(ini, 9 * 60, "no debe recomendar horas que ya pasaron")

    def test_tope_diario_de_bienestar(self):
        total = {}
        for b in self.plan["bloques"]:
            total[b["fecha"]] = total.get(b["fecha"], 0) + a_min(b["fin"]) - a_min(b["inicio"])
        self.assertTrue(total)
        for dia, minutos in total.items():
            self.assertLessEqual(minutos, self.cfg.cap_dia, f"{dia} excede el tope diario")

    def test_tareas_se_terminan_antes_de_la_entrega(self):
        due = {t["id"]: fecha(t["due"]) for t in self.plan["tareas"]}
        for b in self.plan["bloques"]:
            if b["tipo"] == "tarea":
                self.assertLessEqual(fecha(b["fecha"]), due[b["tarea_id"]])

    def test_las_horas_planeadas_igualan_las_estimadas(self):
        for t in self.plan["tareas"]:
            asignado = sum(a_min(b["fin"]) - a_min(b["inicio"]) for b in self.plan["bloques"] if b["tarea_id"] == t["id"])
            self.assertEqual(asignado, t["min"], t["titulo"])
        self.assertEqual(self.plan["advertencias"], [])

    def test_tarea_dificil_se_reparte_en_varios_dias(self):
        dias = {b["fecha"] for b in self.plan["bloques"] if b["tarea_id"] == "m1"}  # Parcial difícil (7.5 h)
        self.assertGreaterEqual(len(dias), 4)

    def test_prioriza_la_entrega_mas_cercana_con_colchon(self):
        # El parcial difícil (20/10, colchón 2 días) debe aparecer antes que el proyecto PTIA (30/10)
        primer = {}
        for b in self.plan["bloques"]:
            primer.setdefault(b["tarea_id"], b["fecha"] + b["inicio"])
        self.assertLess(primer["m1"], primer["m3"])

    def test_informe_de_lab_no_empieza_antes_de_la_sesion(self):
        auto = tareas_automaticas(self.d, AHORA.date(), date(2026, 11, 1))
        informe = next(t for t in auto if t["id"] == "lab:ISIS ARSW:2026-10-16")
        self.assertEqual(informe["due"], date(2026, 10, 23))
        self.assertEqual(informe["desde"], date(2026, 10, 16))
        for b in self.plan["bloques"]:
            if b["tarea_id"] == informe["id"] and b["fecha"] == "2026-10-16":
                self.assertGreaterEqual(a_min(b["inicio"]), 13 * 60)  # el lab termina 13:00

    def test_estudio_independiente_solo_cubre_el_deficit(self):
        # Las tareas cuentan como trabajo independiente: el estudio extra solo rellena lo que falta de la meta.
        for semana, mats in self.plan["resumen"].items():
            for m, v in mats.items():
                deficit = max(0.0, v["meta_h"] - v["tareas_h"])
                self.assertLessEqual(v["estudio_h"], deficit + 0.5, f"{m} semana {semana}")

    def test_marcar_hecha_libera_el_tiempo(self):
        d = copy.deepcopy(self.d)
        d["hechas"].append("m1")
        plan2 = planificar(d, AHORA)
        self.assertFalse(any(b["tarea_id"] == "m1" for b in plan2["bloques"]))
        self.assertTrue(any(b["tarea_id"] == "m1" for b in self.plan["bloques"]))

    def test_advierte_cuando_no_cabe(self):
        d = copy.deepcopy(self.d)
        d["trabajos"].append({"id": "x1", "materia": "ISIS ARSW", "tipo": "Proyecto", "titulo": "Entrega imposible",
                              "entrega": "2026-10-13", "dificultad": "Difícil", "horas": 40})
        plan2 = planificar(d, AHORA)
        self.assertTrue(any(a["tipo"] == "no_cabe" and a["tarea_id"] == "x1" for a in plan2["advertencias"]))

    def test_modo_urgente_permite_mas_horas_la_vispera(self):
        # Parcial difícil de 7.5 h a 1 día de la entrega: con el tope normal (2 h/día) no cabría.
        d = copy.deepcopy(self.d)
        d["trabajos"] = [t for t in d["trabajos"] if t["id"] == "m1"]
        plan2 = planificar(d, datetime(2026, 10, 19, 7, 0))
        self.assertEqual([a for a in plan2["advertencias"] if a["tarea_id"] == "m1"], [])
        por_dia = {}
        for b in plan2["bloques"]:
            if b["tarea_id"] == "m1":
                por_dia[b["fecha"]] = por_dia.get(b["fecha"], 0) + a_min(b["fin"]) - a_min(b["inicio"])
        self.assertTrue(any(m > 120 for m in por_dia.values()), "debe usar más de 2 h un día de la víspera")
        self.assertLessEqual(max(por_dia.values()), 240)

    def test_determinista(self):
        self.assertEqual(planificar(self.d, AHORA)["bloques"], self.plan["bloques"])


class TestEstimaciones(unittest.TestCase):
    def test_horas_por_tipo_y_dificultad(self):
        self.assertEqual(horas_estimadas("Parcial", "Difícil"), 7.5)
        self.assertEqual(horas_estimadas("Taller", "Fácil"), 1.5)
        self.assertEqual(horas_estimadas("Proyecto", "Medio", 8), 8)


if __name__ == "__main__":
    unittest.main()
