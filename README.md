# SemestrIA

Asistente de IA que convierte el **horario fijo**, los **créditos** y los **trabajos** de un estudiante en un plan semanal explicable (qué trabajar, cuándo y por qué). Incluye un asistente de chat que responde sobre el horario y recomienda métodos de estudio, y una sección de progreso.

Proyecto de curso PTIA, Escuela Colombiana de Ingeniería Julio Garavito. **Estado: Hito 3 (MVP).**

## Inicio rápido

Requiere Python 3.10 o superior. No hay que instalar nada.

```bash
python servidor.py        # abre la aplicación en http://localhost:8000
```

En la pantalla de inicio se sube un horario (JSON) o se usa el de ejemplo, y se sigue el asistente de cuatro pasos hasta **Empezar mi semestre**.

Para ver pantallas con datos de demostración, abre `http://localhost:8000/#demo=progreso` (otros valores: `asistente`, `asistente_perfil`, `calendario`, `trabajos`, `resumen`, `ajustes`).

## Qué hace

| Sección | Para qué sirve |
|---|---|
| Resumen | Agenda de hoy, próximas entregas, indicadores y recomendaciones |
| Calendario | Semana y mes, con clases, tareas, estudio y entregas; cada bloque explica su motivo |
| Trabajos | Tablero Por hacer / En curso / Hecho; al terminar un trabajo se registran las horas reales |
| Progreso | Horas cumplidas frente a las necesarias, tareas realizadas, mapa de actividad y rachas |
| Asistente | Chat: explica las recomendaciones, responde sobre el horario, recomienda métodos de estudio y hace una entrevista de 5 preguntas para armar un plan personal |
| Ajustes | Calibración aprendida y opciones del asistente |

## Qué IA usa

Es un sistema **simbólico** (reglas y planificación heurística EDF) con **aprendizaje estadístico ligero** (la calibración con las horas reales). No usa redes neuronales propias. Solo la capa opcional del chat usa un **modelo de lenguaje local** (Ollama, por ejemplo `qwen2.5:3b`), que redacta respuestas a preguntas abiertas y nunca decide el plan; se desactiva en Ajustes o con `SEMESTRIA_SIN_LLM=1`. Todo corre en tu computador. Detalle en [docs/TIPO_DE_IA.md](docs/TIPO_DE_IA.md).

## Comandos

```bash
python -m unittest discover -s pruebas -v      # 73 pruebas automáticas
python pruebas/evaluacion.py --figuras         # evaluación del Hito 3 (resultados/ y figuras)
python herramientas/demo.py                    # plan en consola
python documento/generar_tablas.py             # tablas y cifras del documento
python herramientas/capturar.py                # capturas de pantalla (requiere Edge o Chrome)
python herramientas/generar_diagramas.py       # diagramas (requiere matplotlib)
```

## Estructura

| Ruta | Contenido |
|---|---|
| `servidor.py` | Servidor local (biblioteca estándar) y API JSON |
| `motor/` | Lógica: `semestria.py` (planificador), `calibracion.py`, `asesor.py` (validación y recomendaciones), `asistente.py` (chat y métodos de estudio), `progreso.py` |
| `prototipo/` | Interfaz web sin dependencias (HTML, CSS y JavaScript) |
| `datos/` | `horario_ejemplo.json`, el horario de ejemplo |
| `pruebas/` | Pruebas unitarias y `evaluacion.py` (casos, simulación y calibración) |
| `resultados/` | Salida de la evaluación (`evaluacion.json`, `evaluacion.md`) |
| `documento/` | Documento del proyecto en la plantilla LaTeX (ver [documento/README.md](documento/README.md)) |
| `docs/` | Revisión por hitos, tipo de IA y guion del video |
| `herramientas/` | Scripts de apoyo: demo en consola, capturas y diagramas |
| `archivo_hito2/` | Prototipo del Hito 2 (con motor en JavaScript), conservado como historial |

API: `GET /api/ejemplo`, `GET /api/asistente_estado`, `POST /api/importar`, `POST /api/plan`, `POST /api/chat`, `POST /api/chat_llm`.

## Formato del horario

Los campos obligatorios son `semestre_inicio` y `bloques`. El formato completo está en el anexo del documento, y la pantalla de inicio permite descargar una plantilla.

## Limitaciones

- Evaluado con un horario real y simulaciones; **no hay evaluación con usuarios**.
- Las horas base por tipo de trabajo y los márgenes por dificultad son supuestos propios; la calibración los corrige con los datos del usuario.
- El horario no se lee desde una imagen o PDF: entra como JSON o se arma en la interfaz.
- Los métodos de estudio vienen de una base propia con referencias a la literatura; el modelo local, si se usa, es pequeño y puede equivocarse, y sus respuestas van marcadas.
- El estado se guarda en el navegador (localStorage) y se puede descargar desde la barra lateral.
- Los créditos de algunas materias del horario de ejemplo son supuestos.
