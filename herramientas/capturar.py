"""Captura las pantallas del MVP con Edge/Chrome en modo headless (sin instalar nada extra).

Uso:  python herramientas/capturar.py
Usa la ruta #demo=<pantalla> de la interfaz: fija la fecha del ejemplo (lunes 12/10/2026 09:00),
no toca el almacenamiento del navegador del usuario y deja los PNG en documento/img/ (pant_*.png).
"""
import os
import shutil
import subprocess
import sys
import tempfile
import socket
import time
import urllib.request

aqui = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(aqui, "..")

NAVEGADORES = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
               r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
               r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
PANTALLAS = [  # nombre de archivo, demo, ancho, alto
    ("01_inicio", "inicio", 1440, 760), ("02_horario_creditos", "horario", 1440, 2250),
    ("03_trabajos_asistente", "trabajos_setup", 1440, 1180), ("04_revision_final", "revision", 1440, 1200),
    ("05_resumen", "resumen", 1440, 1180), ("06_calendario_semana", "calendario", 1440, 860),
    ("07_calendario_mes", "mes", 1440, 860), ("08_trabajos_tablero", "trabajos", 1440, 980),
    ("09_progreso", "progreso", 1440, 1760), ("10_asistente", "asistente", 1440, 1000), ("11_asistente_perfil", "asistente_perfil", 1440, 1000),
    ("12_ajustes", "ajustes", 1440, 2500),
]


def esperar(ruta, limite=60):
    """Edge puede devolver el control antes de terminar de escribir la imagen."""
    fin = time.time() + limite
    while time.time() < fin:
        if os.path.exists(ruta):
            tam = os.path.getsize(ruta)
            time.sleep(0.5)
            if tam > 0 and os.path.getsize(ruta) == tam:
                return
        time.sleep(0.3)
    raise TimeoutError(f"No se generó {ruta}")


def main():
    nav = next((n for n in NAVEGADORES if os.path.exists(n)), None)
    if not nav:
        sys.exit("No encontré Edge ni Chrome.")
    with socket.socket() as sk:                       # puerto libre
        sk.bind(("127.0.0.1", 0))
        puerto = sk.getsockname()[1]
    # el servidor corre en un proceso aparte: así las capturas con chat no dependen de este proceso
    srv = subprocess.Popen([sys.executable, os.path.join(RAIZ, "servidor.py"), str(puerto)], cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           env={**os.environ, "SEMESTRIA_SIN_LLM": "1"})   # capturas deterministas: sin modelo de lenguaje
    base = f"http://127.0.0.1:{puerto}/"
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "api/asistente_estado", timeout=1)
            break
        except OSError:
            time.sleep(0.2)
    destino = os.path.join(aqui, "..", "documento", "img")
    os.makedirs(destino, exist_ok=True)
    perfil = tempfile.mkdtemp(prefix="semestria_perfil_")
    try:
        for nombre, demo, w, h in PANTALLAS:
            png = os.path.join(destino, f"pant_{nombre}.png")
            subprocess.run([nav, "--headless", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={perfil}",
                            f"--window-size={w},{h}", "--virtual-time-budget=90000", f"--screenshot={png}", f"{base}#demo={demo}"],
                           check=True, capture_output=True, timeout=90)
            esperar(png)
            print("ok", nombre)
    finally:
        srv.terminate()
        shutil.rmtree(perfil, ignore_errors=True)


if __name__ == "__main__":
    main()
