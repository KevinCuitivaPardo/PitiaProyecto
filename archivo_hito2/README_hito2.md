# SemestrIA – Hito 2 (PTIA, Escuela Colombiana de Ingeniería)

Asistente que convierte el **horario fijo**, los **créditos** y los **trabajos** de un estudiante en un plan semanal
recomendado (qué trabajar, cuándo y por qué).

## Estructura
| Ruta | Contenido |
|---|---|
| `motor/semestria.py` | Motor de recomendación de referencia (Python, solo biblioteca estándar) |
| `prototipo/engine.js` | Réplica idéntica del motor en JavaScript |
| `prototipo/app.js`, `estilos.css`, `index.template.html` | Interfaz de 5 pantallas |
| `prototipo/semestria_prototipo.html` | Prototipo ya ensamblado: se abre con doble clic |
| `datos/horario_ejemplo.json` | Horario real del equipo (los créditos son supuestos: corrígelos) |
| `pruebas/` | Pruebas unitarias, cruce JS↔Python, prueba de interfaz y métricas |
| `diseno/` | Diagramas, capturas y el script que los genera |
| `demo.py` | Plan en consola |

## Cómo ejecutar
```bash
python3 demo.py                                   # plan de ejemplo en consola
python3 -m unittest discover -s pruebas -v        # 24 pruebas del motor
python3 pruebas/exportar_escenarios.py > /tmp/escenarios.json
node pruebas/cruce_js_python.js /tmp/escenarios.json   # JS == Python en 7 escenarios
python3 prototipo/build.py                        # regenera semestria_prototipo.html
python3 pruebas/probar_interfaz.py                # recorre la interfaz en Chromium (requiere playwright)
python3 pruebas/metricas.py                       # métricas del análisis de resultados
python3 diseno/generar_diagramas.py               # requiere matplotlib
```

## Cambiar los datos
Edita `datos/horario_ejemplo.json` (créditos, bloques, `labs`, `entregas_clase`, `disponibilidad`, `trabajos`)
y vuelve a ejecutar `python3 prototipo/build.py` para que el prototipo use tus datos.

## Limitaciones conocidas
- La lectura automática de la imagen del horario está **simulada** en el prototipo.
- Las horas base por tipo de entrega y los colchones por dificultad son **supuestos sin calibrar**.
- Verificado solo con un horario (el del equipo); no hay evaluación con usuarios todavía.
