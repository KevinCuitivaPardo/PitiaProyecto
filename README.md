# SemestrIA (PitiaProyecto)
Proyecto IA de ayuda para organizar el tiempo del estudiante, teniendo en cuenta talleres, laboratorios y parciales.

Convierte créditos + horario fijo + disponibilidad + trabajos en un plan semanal explicable
(reglas + heurística EDF con topes de bienestar).

## Uso
```bash
python servidor.py          # abre http://localhost:8000
python demo.py              # plan en consola
python -m unittest pruebas.test_motor
```

## Flujo de uso
**Configuración (asistente de 4 pasos)**
1. **Inicio** – subes tu horario (JSON, se valida) o usas el de prueba.
2. **Horario y créditos** – revisas/agregas clases, ajustas créditos, disponibilidad y tope diario.
3. **Trabajos** – agregas parciales y proyectos; los labs y talleres salen solos del horario.
4. **Listo para empezar** – checklist de revisión y botón **Empezar mi semestre**: el horario queda fijado.

**Panel del semestre (después de empezar)**
- **Resumen**: agenda de hoy, indicadores, próximas entregas y los consejos más importantes.
- **Calendario**: semana con grilla de horas (clases, tareas, estudio, entregas, línea de "ahora") y vista de mes con carga diaria.
- **Trabajos**: tablero Por hacer / En curso / Hecho (arrastrar, filtrar, crear y editar) con progreso programado y próximo bloque.
- **Consejos**: por categoría (foco, riesgo, estrategia, carga, bienestar, estudio, progreso), cada uno con "qué pasa" y "qué hacer".
- **Ajustes**: editar horario/créditos/disponibilidad, cargar otro horario o reiniciar.

## Estructura
- `motor/semestria.py` – motor de recomendación (Python, sin dependencias)
- `motor/asesor.py` – validación de horarios importados + consejos basados en reglas
- `servidor.py` – servidor local (stdlib) con `/api/plan` y `/api/ejemplo`
- `prototipo/` – interfaz (`index.html`, `app.js`, `estilos.css`)
- `datos/horario_ejemplo.json` – horario de ejemplo
- `pruebas/` – tests del motor, métricas, y scripts opcionales (`probar_interfaz.py` requiere playwright; `cruce_js_python.js` requiere un `prototipo/engine.js` que aún no existe)
- `diseno/` – capturas de referencia y `generar_diagramas.py` (requiere matplotlib)
