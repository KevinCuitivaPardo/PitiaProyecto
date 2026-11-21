# Revisión del proyecto hito por hito

Se contrastó lo que había (documento de contexto del Hito 1, proyecto del Hito 2 y este repositorio) contra los
**Lineamientos del Proyecto de PTIA** y la plantilla LaTeX institucional. "Estado" describe lo encontrado; "Corrección"
lo que se hizo en esta entrega.

## Hito 1 — Exploración (semana 5)

| Requisito de los lineamientos | Estado encontrado | Corrección |
|---|---|---|
| 1a. Tres problemas que interesaría resolver | Solo estaba el problema elegido | Sección *Introducción*: tres problemas. **Los problemas 2 y 3 los redacté yo como candidatos: confirmar o reemplazar** (hay un comentario `CONFIRMAR` en el `.tex`) |
| 1b. ¿Por qué como proyecto de PTIA? | No se justificaba qué tipo de IA ni por qué | Sección *Introducción*: planificación, conocimiento y razonamiento, aprendizaje y ética |
| 2. Dos trabajos relacionados por problema (resultados y tecnología) | Ausente | Sección *Trabajos relacionados*, con 6 referencias y tabla resumen. **Verificar cada referencia antes de entregar** |
| 3a. Criterios de selección | Ausente | Sección *Descripción del problema*: 5 criterios ponderados y tabla de selección. **Las calificaciones 1–5 son mi propuesta: ajustarlas con el equipo** |
| 3b. Problema seleccionado | Presente (documento de contexto) | Reformulado con entradas, salida y por qué es difícil |
| 4. Justificación (gran problema e importancia) | Parcial, sin cifras | Con cifras del horario real: 20 créditos = 60 h/semana; 21,8 h en clase; 38,3 h de estudio independiente; 4 entregas en 4 días |
| Formato | `.docx` propio, no la plantilla | Pasado a la plantilla LaTeX (`documento/`) |
| Prototipo en papel y video | No están en el repositorio | **No se pudo revisar** |

## Hito 2 — Problema y avance de la solución (semana 10)

| Requisito | Estado encontrado | Corrección |
|---|---|---|
| 5a-b. Problema que efectivamente se resuelve y por qué es una simplificación adecuada | Solo en el README (limitaciones) | Sección *Alcance y objetivos* con tabla de simplificaciones |
| 5c. Objetivo cuantitativo y cualitativo | **Solo cualitativos** | Ocho criterios de aceptación cuantitativos (OC1–OC8). *Se fijaron al diseñar la evaluación del Hito 3, no en el Hito 2; el documento lo dice* |
| 6a. Estrategia general y justificación | Implícita en el código | Sección *Diseño*: estrategia y tabla de alternativas (optimización, LLM, aprendizaje supervisado) |
| 6b. Dónde está la inteligencia | **Nunca se explicitó** | Conocimiento, razonamiento y aprendizaje, con las fórmulas |
| 6c. Herramienta y justificación | Sin justificar | Justificada (solo biblioteca estándar, reproducible) |
| 6d. Arquitectura | Diagrama del Hito 2 desactualizado | Rehecho para el MVP (`documento/img/arquitectura.png`) |
| 6e. Componente principal | Sin descripción | Planificador: pasos, parámetros, ejemplo real y costo |
| Prototipo de interfaz (navegable) | Bien; la lectura de la imagen del horario estaba **simulada** | Reemplazada por importación JSON validada; la lectura de imágenes se declara fuera de alcance |
| Fuentes del diseño y del código | Sin referencias ni procedencia | Subsección *Fuentes del diseño y del código* y bibliografía |
| Inconsistencia | Motor duplicado en Python y JavaScript, con prueba de cruce | Unificado en Python (ver conclusiones); el original se conserva en `archivo_hito2/` |
| Verificación | 24 pruebas y un solo horario | 45 pruebas y 300 escenarios simulados |

## Hito 3 — Solución y evaluación (semana 16)

| Entregable | Estado |
|---|---|
| Documento: sección 7 *Análisis de resultados* | Hecho: dos mejores casos (CP1, CP3), caso más significativo (comparación con "último momento" en 300 escenarios) y calibración, con secuencia de entradas y salidas esperadas y obtenidas |
| Documento: sección 8 *Conclusiones* | Hecho: 2 aciertos, 2 errores, 3 conclusiones, trabajo futuro |
| Prototipo funcional MVP | Hecho (ver abajo) |
| Fuentes finales del diseño y del código | Hecho: repositorio, anexo del documento y `README.md` |
| Video (máx. 10 min) con resultados y demo | **Pendiente (lo graba el equipo)**: guion en `docs/GUION_VIDEO_HITO3.md` |
| Compilar el PDF | **Pendiente**: no había LaTeX en esta máquina; compilar en Overleaf con XeLaTeX + biber (ver `documento/README.md`) |

### Qué se agregó al MVP

1. **Asistente de 4 pasos con "Empezar mi semestre"**, que fija el horario, y panel con resumen, calendario (semana y mes), tablero de trabajos, progreso, asistente personal y ajustes.
2. **Validación de horarios importados** con mensajes claros.
3. **Recomendaciones concretas** (con fechas y acción), en lugar de consejos genéricos.
4. **Calibración**: al marcar un trabajo como hecho se registran las horas reales; el sistema aprende un factor por tipo de trabajo. Es el componente de aprendizaje, ausente en el Hito 2.
5. **Pruebas**: `test_mvp.py` (validación, recomendaciones, calibración y API HTTP), `test_asistente.py` (progreso, asistente y API del chat) y `evaluacion.py` (casos y simulación).
6. **Asistente personal (chat)**: responde sobre el horario, recomienda 12 métodos de estudio y bienestar con referencias, hace una entrevista de 5 preguntas y arma un plan personal. Las recomendaciones son tarjetas que abren el chat. Capa opcional con un modelo local (Ollama).
7. **Progreso**: horas cumplidas frente a las necesarias, tareas realizadas, mapa de actividad y rachas.
8. **Tipo de IA explicado** (`docs/TIPO_DE_IA.md` y sección «Qué tipo de inteligencia artificial usa SemestrIA» del documento): simbólica con aprendizaje estadístico ligero; sin redes neuronales propias.

### Resultado honesto de la evaluación

Los 8 criterios de aceptación se cumplen, pero la evaluación también muestra límites:

- La estrategia de "último momento" cubre más trabajos (99,7 %) que SemestrIA (98,4 %): es el costo de los topes de bienestar.
- La calibración empeora ~4 % el error de quien ya coincide con la estimación base.
- Todo es sobre un horario real y simulaciones: **no hay evaluación con usuarios**.
