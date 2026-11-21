"""Ensambla prototipo/semestria_prototipo.html (un solo archivo autocontenido).
Uso:  python prototipo/build.py
"""
import json, os
aqui = os.path.dirname(os.path.abspath(__file__))
leer = lambda *p: open(os.path.join(aqui, *p), encoding="utf-8").read()

datos = json.dumps(json.load(open(os.path.join(aqui, "..", "datos", "horario_ejemplo.json"), encoding="utf-8")),
                   ensure_ascii=False).replace("</", "<\\/")
app = leer("app.js").replace("/*__DATA__*/ {}", datos)
html = (leer("index.template.html")
        .replace("/*__CSS__*/", leer("estilos.css"))
        .replace("/*__ENGINE__*/", leer("engine.js"))
        .replace("/*__APP__*/", app))
salida = os.path.join(aqui, "semestria_prototipo.html")
open(salida, "w", encoding="utf-8").write(html)
print(f"OK {salida} ({len(html) / 1024:.0f} KB)")
