"""Servidor local de SemestrIA (solo biblioteca estándar).

Sirve la interfaz (prototipo/) y expone el motor de recomendación:
  GET  /api/ejemplo   -> horario de ejemplo (datos/horario_ejemplo.json)
  POST /api/importar  -> valida y normaliza un horario subido (JSON)
  POST /api/plan      -> {"datos": {...}, "ahora": "YYYY-MM-DDTHH:MM"} -> plan recomendado

Uso:  python servidor.py [puerto]     (por defecto 8000)
"""
import json
import mimetypes
import os
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from motor.asesor import consejos, indicadores, validar_datos
from motor.semestria import (Config, cargar, contacto_semanal_min, creditos_de, horas_independientes,
                             horas_totales_semana, planificar)

RAIZ = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(RAIZ, "prototipo")
EJEMPLO = os.path.join(RAIZ, "datos", "horario_ejemplo.json")


def resolver_plan(cuerpo: dict) -> dict:
    datos = cuerpo["datos"]
    ahora = datetime.fromisoformat(cuerpo["ahora"])
    c = cuerpo.get("config", {})
    cfg = Config(max_horas_dia=float(c.get("max_horas_dia", 6)), usar_huecos=bool(c.get("usar_huecos", True)))
    plan = planificar(datos, ahora, cfg)
    plan["consejos"] = consejos(datos, plan, ahora)
    plan["indicadores"] = indicadores(datos, plan, ahora)
    plan["materias"] = [{
        "codigo": m["codigo"], "creditos": m["creditos"],
        "total_h": horas_totales_semana(m["creditos"]),
        "clase_h": contacto_semanal_min(m["codigo"], datos) / 60,
        "indep_h": horas_independientes(m["codigo"], datos),
    } for m in datos["materias"]]
    return plan


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        ruta = self.path.split("?")[0]
        if ruta == "/api/ejemplo":
            return self._json(cargar(EJEMPLO))
        if ruta == "/":
            ruta = "/index.html"
        destino = os.path.normpath(os.path.join(WEB, ruta.lstrip("/")))
        if not destino.startswith(WEB) or not os.path.isfile(destino):
            self.send_error(404)
            return
        with open(destino, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", (mimetypes.guess_type(destino)[0] or "text/plain") + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path not in ("/api/plan", "/api/importar"):
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            cuerpo = json.loads(self.rfile.read(n))
            if self.path == "/api/importar":
                datos, errores = validar_datos(cuerpo)
                return self._json({"datos": datos} if datos else {"errores": errores}, 200 if datos else 422)
            self._json(resolver_plan(cuerpo))
        except json.JSONDecodeError:
            self._json({"error": "El archivo no es un JSON válido."}, 400)
        except (KeyError, ValueError, TypeError) as e:
            self._json({"error": f"Datos inválidos: {e}"}, 400)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"SemestrIA en http://localhost:{puerto}  (Ctrl+C para salir)")
    ThreadingHTTPServer(("127.0.0.1", puerto), Handler).serve_forever()
