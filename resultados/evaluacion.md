# Evaluación del MVP de SemestrIA

Generado por `pruebas/evaluacion.py` (semilla 2026).

## A. Casos de prueba

### CP1. Semana base del estudiante

**Entrada:** Horario real del estudiante (6 materias, 14 bloques), 3 trabajos registrados, lunes 12/10/2026 09:00 (semana 8, par).

| Comprobación | Esperado | Obtenido | |
|---|---|---|---|
| Tareas con tiempo asegurado | 15 de 15 | 15 de 15 | OK |
| Violaciones de restricciones duras | 0 | 0 | OK |
| Máximo de horas en un día | <= 6 h | 6 h | OK |
| Parcial difícil (entrega 20/10) termina con >= 2 días de colchón | último bloque <= 18/10 | último bloque 16/10 | OK |
| Advertencias de tiempo | 0 | 0 | OK |

### CP2. Entrega imposible

**Entrada:** Caso base + un proyecto difícil de 40 h que se entrega mañana (13/10).

| Comprobación | Esperado | Obtenido | |
|---|---|---|---|
| Advertencia «no alcanza el tiempo» para el proyecto | 1 advertencia | 1 advertencia(s) | OK |
| Horas asignadas + horas que faltan = 40 h | 40 h | 8 + 32 = 40 h | OK |
| Se respeta el tope diario pese a la presión | 0 violaciones | 0 violaciones | OK |
| Los demás trabajos registrados siguen cubiertos | 3 de 3 | 3 de 3 | OK |

### CP3. Marcar tareas como hechas reacomoda el plan

**Entrada:** Caso base; el estudiante marca como hechos el Parcial 2 de ECDI y el informe de laboratorio de ARSW (09/10).

| Comprobación | Esperado | Obtenido | |
|---|---|---|---|
| Desaparecen los bloques de las tareas hechas | 0 bloques | 0 bloques | OK |
| Baja el trabajo en tareas | < 53.5 h | 41.5 h | OK |
| El tiempo liberado pasa a estudio independiente | > 53 h | 64.5 h | OK |
| Las demás tareas siguen cubiertas | 13 de 13 | 13 de 13 | OK |

### CP4. Se respeta un día sin disponibilidad

**Entrada:** Caso base pero el sábado deja de estar disponible.

| Comprobación | Esperado | Obtenido | |
|---|---|---|---|
| Bloques el sábado | 0 | 0 | OK |
| Violaciones de restricciones duras | 0 | 0 | OK |
| Tareas cubiertas o advertidas (sin fallas silenciosas) | 100 % | 15 cubiertas, 0 advertidas de 15 | OK |

### CP5. La calibración ajusta las estimaciones

**Entrada:** Caso base; el estudiante registró 5 talleres que estimados en 2 h le tomaron 3 h (razón 1,5).

| Comprobación | Esperado | Obtenido | |
|---|---|---|---|
| Sin historial el factor es 1 (el plan no cambia) | 1,00 | 1.00 | OK |
| Con 5 registros el factor se acerca a 1,5 sin igualarlo | entre 1,30 y 1,50 | 1.42 | OK |
| Aumentan los minutos asignados a talleres | > 630 min | 990 min | OK |
| Los trabajos con horas fijadas por el estudiante no cambian | 480 min (PTIA) | 480 min | OK |

### CP6. El asistente responde con los datos del estudiante

**Entrada:** Caso base, sin modelo de lenguaje: preguntas «¿Qué tengo hoy?», «¿cuándo es mi parcial?», «¿cómo estudio para el parcial de ECDI?», una pregunta fuera de tema y la entrevista de cinco preguntas.

| Comprobación | Esperado | Obtenido | |
|---|---|---|---|
| «¿Qué tengo hoy?» muestra la clase y el bloque reales del lunes 12/10 | 09:00–11:00 y Taller MATE ECDI | ambos presentes | OK |
| «¿Cuándo es mi parcial?» pone primero el parcial con su fecha | Parcial 2 de ECDI, 20/10 | Parcial 2 de ECDI, 20/10 | OK |
| El plan de repasos termina en la fecha de la entrega | martes 20/10 | martes 20/10 | OK |
| Una pregunta fuera de tema no se inventa | «No tengo una respuesta segura» | sin respuesta inventada | OK |
| La entrevista arma el plan personal y pone primero el sueño (duerme menos de 6 h) | Dormir como parte del estudio | primero | OK |
| Cada recomendación se puede explicar en el chat | 11 de 11 | 11 de 11 | OK |

## B. Simulación

- Escenarios aleatorios: 300; trabajos planificados: 3162.
- Violaciones de restricciones duras: **0** 
- Trabajos con tiempo asegurado: 98.4 % (257 de 300 escenarios completos; 43 con advertencia).
- Tiempo por plan: media 3.37 ms, p95 4.86 ms, máximo 8.58 ms.

| Métrica | Último momento | SemestrIA |
|---|---|---|
| Trabajos cubiertos (%) | 99.7 | 98.4 |
| Días > 6 h por escenario | 1.71 | 0.0 |
| Máx. horas en un día (media) | 8.35 | 5.84 |
| Terminados el día de la entrega (%) | 90.1 | 5.1 |
| Anticipación media (días) | 0.15 | 7.53 |

## C. Calibración

200 usuarios simulados por ritmo, 12 trabajos cada uno; error medido desde el trabajo 6.

| Ritmo real | Error base (h) | Error calibrado (h) | Reducción |
|---|---|---|---|
| 0.6× | 1.69 | 0.52 | 69.0 % |
| 0.8× | 0.94 | 0.64 | 32.1 % |
| 1× | 0.7 | 0.73 | -4.3 % |
| 1.3× | 1.48 | 0.97 | 34.9 % |
| 1.6× | 2.78 | 1.31 | 52.8 % |
| 2× | 4.57 | 1.74 | 61.9 % |

Reducción media: 51.4 % (solo usuarios con ritmo distinto de 1×: 50.1 %).