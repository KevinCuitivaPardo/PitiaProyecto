# SemestrIA (PTIA, Escuela Colombiana de Ingeniería)

Asistente de IA que convierte el **horario fijo**, los **créditos** y los **trabajos** de un estudiante en un plan
semanal explicable (qué trabajar, cuándo y por qué), con recomendaciones concretas y estimaciones que se calibran con
las horas reales que registra la persona.

**Estado: Hito 3 (MVP).** Ver `docs/REVISION_HITOS.md` para la revisión por hitos frente a los lineamientos.

## Ejecutar (Python 3.10+, sin dependencias)
```bash
python servidor.py                                 # abre http://localhost:8000
python demo.py                                     # plan en consola
python -m unittest discover -s pruebas -v          # 73 pruebas automáticas
python pruebas/evaluacion.py --figuras             # evaluación del Hito 3 (resultados/ y figuras)
```
`python diseno/capturar.py` (capturas, requiere Edge o Chrome) y `python diseno/generar_diagramas.py` (requiere matplotlib).

## Flujo de uso
**Asistente de 4 pasos:** 1) subir un horario JSON (validado) o usar el de prueba, 2) revisar horario y créditos,
3) registrar trabajos, 4) revisión final y **Empezar mi semestre** (queda fijado).
**Panel:** Resumen · Calendario (semana y mes) · Trabajos (tablero Por hacer / En curso / Hecho) · **Progreso** (horas cumplidas frente a las necesarias, tareas realizadas, mapa de actividad y rachas) · **Asistente** (chat) · Ajustes (calibración y asistente).

**Asistente.** Las recomendaciones son tarjetas: al tocar una, el chat la explica con pasos, fechas de tu plan, gráficas simples y la evidencia que la respalda. Puedes preguntar por tu horario («¿qué tengo hoy?», «¿voy atrasado?») y por métodos de estudio y bienestar; también te hace cinco preguntas y arma tu plan de estudio personal. Funciona en dos capas: lo que depende de tus datos y de los métodos lo calcula el motor (instantáneo y verificable); las preguntas abiertas las puede redactar un **modelo local con Ollama** si lo tienes instalado (se detecta solo; tus datos no salen del computador; se desactiva en Ajustes o con `SEMESTRIA_SIN_LLM=1`).

**Qué IA usa.** Núcleo simbólico (reglas y planificación heurística EDF) con aprendizaje estadístico ligero (calibración); sin redes neuronales propias. Solo la capa opcional del chat usa un modelo de lenguaje preentrenado local. Detalle en `docs/TIPO_DE_IA.md`.

**Progreso.** Se alimenta de lo que registras: marcar bloques como cumplidos, anotar las horas reales al terminar un trabajo y abrir la aplicación.

## Estructura
| Ruta | Contenido |
|---|---|
| `motor/semestria.py` | Planificador: créditos a horas, huecos, entregas automáticas, EDF con topes de bienestar |
| `motor/calibracion.py` | Factor aprendido de las horas reales (promedio geométrico encogido hacia 1) |
| `motor/asesor.py` | Validación de horarios importados y recomendaciones |
| `motor/asistente.py` | Asistente: intenciones, métodos de estudio con evidencia, entrevista, puente opcional al modelo local |
| `motor/progreso.py` | Estadísticas de progreso y rachas |
| `servidor.py` | Servidor local (biblioteca estándar) y API JSON: `/api/ejemplo`, `/api/importar`, `/api/plan`, `/api/chat`, `/api/chat_llm`, `/api/asistente_estado` |
| `prototipo/` | Interfaz (`index.html`, `app.js`, `asistente.js`, `estilos.css`, `asistente.css`) |
| `datos/horario_ejemplo.json` | Horario real del equipo (los créditos de algunas materias son supuestos) |
| `pruebas/` | `test_motor.py`, `test_mvp.py`, `test_asistente.py` y `evaluacion.py` (casos, simulación y calibración) |
| `resultados/` | Salida de la evaluación (`evaluacion.json`, `evaluacion.md`) |
| `documento/` | Documento del proyecto en la plantilla LaTeX (ver `documento/README.md`) |
| `docs/` | Revisión por hitos, tipo de IA y guion del video |
| `diseno/` | Diagramas y capturas del MVP (`pantallas_mvp/`) y sus scripts |
| `archivo_hito2/` | Prototipo navegable del Hito 2 (con motor en JavaScript), conservado como historial |

## Formato del horario
Ver el anexo del documento o descargar la plantilla desde la pantalla de inicio. Campos obligatorios: `semestre_inicio` y `bloques`.

## Limitaciones conocidas
- Evaluado con un horario real y simulaciones; **no hay evaluación con usuarios**.
- Las horas base por tipo de trabajo y los márgenes por dificultad son supuestos propios (la calibración los corrige con datos del usuario).
- El horario no se lee desde una imagen o PDF: entra como JSON o se arma en la interfaz.
- Los consejos de métodos de estudio vienen de una base propia con referencias a la literatura (verificar las citas antes de usarlas en un trabajo); el modelo local, si se usa, es pequeño y puede equivocarse: sus respuestas van marcadas.
- El estado se guarda en el navegador (localStorage); se puede descargar desde la barra lateral.
