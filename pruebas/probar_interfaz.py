"""Recorre la interfaz en un navegador real (Chromium) y captura cada pantalla.
Uso:  python pruebas/probar_interfaz.py [carpeta_capturas]
Falla si hay errores de consola o si el flujo no se comporta como se espera.
"""
import os, sys
from playwright.sync_api import sync_playwright

aqui = os.path.dirname(os.path.abspath(__file__))
html = "file://" + os.path.abspath(os.path.join(aqui, "..", "prototipo", "semestria_prototipo.html"))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(aqui, "..", "diseno", "pantallas")
os.makedirs(out, exist_ok=True)
errores = []

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="es-CO")
    pg = ctx.new_page()
    # Se ignora la descarga de tipografías (Google Fonts): el sandbox no tiene internet y hay fuentes de respaldo.
    pg.on("console", lambda m: errores.append(("console." + m.type, m.text)) if m.type in ("error", "warning") and "ERR_NAME_NOT_RESOLVED" not in m.text else None)
    pg.on("pageerror", lambda e: errores.append(("pageerror", str(e))))
    # fijar el reloj del navegador al lunes 12 oct 2026, 9:00 (la fecha de entrega de este trabajo)
    pg.clock.install(time="2026-10-12T09:00:00")
    pg.goto(html)
    pg.wait_for_selector(".drop")
    pg.screenshot(path=f"{out}/1_horario_subir.png")

    assert pg.locator(".step:not([disabled])").count() == 1, "antes de subir el horario solo el paso 1 debe estar activo"
    pg.click("[data-action=usar-ejemplo]")
    pg.clock.run_for(1200)
    pg.wait_for_selector(".wk")
    assert pg.locator(".blk.clase").count() == 14, "debe mostrar los 14 bloques de clase"
    pg.screenshot(path=f"{out}/1_horario_leido.png")

    pg.click("text=Continuar: créditos y disponibilidad")
    pg.wait_for_selector(".tabla")
    assert "20" in pg.inner_text(".tabla tfoot"), "total de créditos = 20"
    pg.click("[data-action=cred][data-mat='MATE ECDI'][data-d='1']")
    assert "5" in pg.inner_text(".tabla tbody tr:nth-child(5)"), "ECDI sube a 5 créditos"
    pg.click("[data-action=cred][data-mat='MATE ECDI'][data-d='-1']")
    pg.screenshot(path=f"{out}/2_creditos_disponibilidad.png", full_page=True)

    pg.click("text=Continuar: laboratorios y entregas")
    pg.wait_for_selector(".grid2 .card")
    pg.click("[data-action=lab][data-mat='ISIS ARSW'][data-campo=frecuencia][data-v=quincenal]")
    assert "Semanas pares" in pg.inner_text("body") and pg.locator("text=Esta semana es la 8 (par)").count() >= 1
    pg.click("[data-action=lab][data-mat='ISIS ARSW'][data-campo=frecuencia][data-v=semanal]")
    pg.screenshot(path=f"{out}/3_laboratorios_entregas.png", full_page=True)

    pg.click("text=Continuar: trabajos")
    pg.wait_for_selector("text=Agregar un trabajo")
    pg.click("text=Agregar al calendario")
    assert pg.locator("text=Escribe el nombre del trabajo").count() == 1, "debe validar el nombre vacío"
    pg.fill("input[data-campo=titulo]", "Entrega 2 del proyecto")
    pg.select_option("select[data-campo=materia]", "ISIS ARSW")
    pg.click("[data-action=form-dif][data-v='Difícil']")
    pg.click("text=Agregar al calendario")
    assert pg.locator("text=Agregamos «Entrega 2 del proyecto»").count() == 1
    pg.screenshot(path=f"{out}/4_trabajos.png", full_page=True)

    pg.click("text=Ver mi semana")
    pg.wait_for_selector(".g")
    n_rec = pg.locator(".blk.rec").count()
    assert n_rec > 10, f"debe haber bloques recomendados, hay {n_rec}"
    pg.screenshot(path=f"{out}/5_semana.png", full_page=True)

    # detalle explicable
    pg.locator(".blk.rec").first.click()
    assert "Por qué aquí" in pg.inner_text(".det")
    titulo = pg.inner_text(".det h3")
    pg.screenshot(path=f"{out}/5_semana_detalle.png", full_page=True)

    # marcar como hecho desde el detalle y desde la lista
    pg.click(".det [data-action=hecho]")
    visibles = [t.strip() for t in pg.locator(".blk.rec b").all_inner_texts()]
    assert titulo not in visibles, f"«{titulo}» debe desaparecer del calendario al marcarla como hecha"
    assert pg.locator("text=Hechas (1)").count() == 1
    pg.screenshot(path=f"{out}/5_semana_hecha.png", full_page=True)
    pg.click(".hecha input")  # deshacer
    assert pg.locator("text=Hechas (").count() == 0

    # semana siguiente: laboratorio quincenal de FDSI no ocurre (semana impar) -> bloque fantasma
    pg.click("[aria-label='Semana siguiente']")
    assert pg.locator(".blk.fantasma").count() >= 1, "en la semana 9 debe verse 'sin laboratorio'"
    pg.screenshot(path=f"{out}/5_semana_siguiente.png", full_page=True)

    # móvil
    m = b.new_context(viewport={"width": 390, "height": 844}, locale="es-CO").new_page()
    m.clock.install(time="2026-10-12T09:00:00")
    m.goto(html)
    m.click("[data-action=usar-ejemplo]"); m.clock.run_for(1200); m.wait_for_selector(".wk")
    m.evaluate("window.__semestria.ir(4)")
    m.wait_for_selector(".g")
    ancho = m.evaluate("document.documentElement.scrollWidth")
    assert ancho <= 392, f"la página no debe desbordar horizontalmente en móvil (scrollWidth={ancho})"
    m.screenshot(path=f"{out}/m_semana.png")
    b.close()

if errores:
    print("ERRORES:", errores); sys.exit(1)
print("OK: flujo completo de la interfaz verificado, sin errores de consola")
