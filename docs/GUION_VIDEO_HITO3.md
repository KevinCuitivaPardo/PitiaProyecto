# Guion del video del Hito 3 (máx. 10 min)

Los lineamientos piden "resultados y demo del MVP". Tiempos sugeridos para dos personas; ensayar una vez con la app abierta.

**Preparación:** `python servidor.py`, abrir http://localhost:8000 en una ventana limpia (o con `#demo=` para datos fijos), zoom del navegador al 110 %, pestaña con `resultados/evaluacion.md` y otra con el PDF.

| Tiempo | Quién | Contenido | En pantalla |
|---|---|---|---|
| 0:00–0:45 | A | El problema: 20 créditos = 60 h/semana, solo 21,8 en clase; 38,3 h de estudio independiente que nadie planea. Cuatro entregas en cuatro días | Diapositiva o sección *Justificación* |
| 0:45–1:45 | B | La solución y dónde está la IA: conocimiento (créditos, dificultad), razonamiento (planificador EDF con topes) y aprendizaje (calibración). Por qué no un LLM: verificable y determinista | Figura de arquitectura |
| 1:45–6:00 | A y B | **Demo del MVP** (ver abajo) | La aplicación |
| 6:00–8:15 | B | Resultados: 8/8 criterios; CP1 y CP3; comparación con "último momento"; calibración | Tablas y figuras del documento |
| 8:15–9:30 | A | Conclusiones: 2 aciertos, 2 errores, límites (sin usuarios reales) y trabajo futuro (piloto) | Sección *Conclusiones* |
| 9:30–10:00 | A y B | Cierre y dónde está el código | Repositorio |

## Demo (1:45–6:00)

1. **Inicio** (15 s): "Subes tu horario o usas el de prueba." Mostrar el archivo inválido (mensaje de error) y luego **Probar con el ejemplo**.
2. **Horario y créditos** (45 s): cambiar los créditos de una materia (ver cómo cambian las horas de estudio); quitar la disponibilidad del sábado.
3. **Trabajos** (30 s): **+ Nuevo trabajo** (un parcial a una semana); ver que aparece en el tablero.
4. **Listo para empezar** (20 s): checklist y **Empezar mi semestre**.
5. **Resumen** (30 s): agenda de hoy, próxima entrega y las recomendaciones principales.
6. **Calendario** (45 s): semana, tocar un bloque y leer el motivo; pasar a **Mes**.
7. **Tablero** (45 s): arrastrar una tarjeta a *En curso*; marcar otra como **Hecho** y escribir las horas reales ("me tomó 4 h").
8. **Recomendaciones** (30 s): leer una con fecha y acción concreta.
9. **Ajustes** (20 s): tabla de calibración con el factor aprendido; ver cómo cambió una estimación.
10. **Caso límite** (20 s): agregar un proyecto de 40 h para mañana y mostrar la advertencia "no alcanza el tiempo" y la recomendación urgente.

## Para decir con honestidad

- Los resultados son con un horario real y simulaciones; **no hay evaluación con usuarios**.
- La estrategia de último momento cubre un poco más de trabajos (99,7 % frente a 98,4 %) porque no tiene topes de bienestar.
- La calibración puede empeorar ligeramente a quien ya coincide con la estimación base.
