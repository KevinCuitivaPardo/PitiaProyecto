# Qué IA usa SemestrIA y con qué características

Resumen para sustentar el proyecto. La versión formal está en el documento (`documento/content/tipo_ia.tex`).

## En una frase
SemestrIA es un **agente basado en conocimiento y en objetivos** (Russell y Norvig, 2021): **IA simbólica** (reglas y búsqueda heurística) con un **elemento de aprendizaje estadístico ligero**. **No usa redes neuronales para decidir.** La única pieza neuronal es un **modelo de lenguaje preentrenado, opcional y local**, que solo redacta respuestas a preguntas abiertas.

## Métodos por componente
| Componente | Técnica | Familia | ¿Aprende? | ¿Determinista? |
|---|---|---|---|---|
| Estimación de horas y metas | Reglas: créditos a horas (48 h/crédito), horas base por tipo, factor y margen por dificultad | Simbólica | No | Sí |
| Planificador | Búsqueda heurística voraz **EDF** con restricciones duras/blandas y topes de bienestar | Simbólica (planificación) | No | Sí |
| Calibración | Promedio geométrico encogido hacia 1 (K = 3), por tipo de trabajo; equivale a una creencia previa | Aprendizaje estadístico (no neuronal) | **Sí**, con las horas reales del usuario | Sí |
| Asesor | Reglas condición → recomendación con acción | Simbólica | No | Sí |
| Asistente: comprensión | Intención por raíces de palabras sin tildes, con puntaje y desempates | PLN simbólico | No | Sí |
| Asistente: diálogo | Entrevista de 5 preguntas (máquina de estados) que arma un perfil | Simbólica | No (construye perfil) | Sí |
| Asistente: respuesta | Recomendador basado en conocimiento (12 métodos con evidencia) y plantillas con los datos del estudiante | Simbólica | No | Sí |
| Progreso | Estadística descriptiva (horas por semana, porcentajes, rachas) | No es IA estricta | No | Sí |
| Modelo de lenguaje (opcional) | LLM preentrenado tipo *transformer*: por defecto local (Ollama + Qwen2.5 de 3 mil millones de parámetros); opcionalmente un proveedor en la nube con su biblioteca de Python. Solo inferencia | Neuronal, generativa | No (no se entrena ni ajusta) | No |

## ¿Es una red neuronal?
- **El núcleo, no.** Plan, estimaciones, recomendaciones y respuestas sobre horario y métodos salen de reglas y algoritmos legibles y reproducibles.
- **No se entrenó ningún modelo propio**, no hay aprendizaje profundo propio y no se usan datos de otros estudiantes.
- **La capa opcional sí es una red neuronal**, pero ya viene entrenada por terceros, el sistema solo la consulta, por defecto corre en tu computador (sin nube) y no puede tocar el plan. Con `SEMESTRIA_PROVEEDOR=nube` se usa un servicio en la nube: responde mejor y más rápido, pero el resumen de tu agenda y tu pregunta salen de tu computador (la interfaz lo avisa).

## Características
- **Determinista y reproducible:** mismos datos, mismo plan. Solo varía el modelo de lenguaje opcional (temperatura 0,3).
- **Explicable:** cada bloque, recomendación y factor de calibración dice su motivo; los métodos citan su evidencia.
- **Verificable:** 79 pruebas y 300 escenarios simulados (0 violaciones de restricciones duras). Lo que redacta el modelo de lenguaje no se puede verificar así.
- **Sin entrenamiento ni datos externos:** el único aprendizaje es la calibración, anclada en 1, que sirve con pocos registros.
- **Privado por defecto:** todo local, incluida la capa neuronal; solo la opción en la nube envía datos fuera.
- **Rápido y gratuito:** ~3,5 ms por plan; respuestas del motor inmediatas; el modelo local tarda decenas de segundos sin GPU.
- **Degrada con elegancia:** sin Ollama todo funciona; sin historial, el factor de calibración es 1.

## Cómo se controla el modelo de lenguaje
Los modelos generativos pueden afirmar cosas falsas con seguridad (Ji et al., 2023); en una prueba inventó títulos de libros. Por eso:
1. Instrucción restringida: solo horario, organización, métodos de estudio y bienestar; prohíbe inventar fechas, notas, libros o estudios y citar fuentes.
2. Recibe un resumen corto y fijo de los datos del estudiante y debe usar solo eso (idea afín a fundamentar la generación en datos, Lewis et al., 2020, sin base vectorial).
3. No puede mover bloques ni fechas: las restricciones duras viven en el motor.
4. Cada respuesta se marca como «redactada por el modelo local» o «por un modelo en la nube».
5. Se apaga en Ajustes o con `SEMESTRIA_SIN_LLM=1`.

## Por qué esta combinación
Hay restricciones duras (choques, topes de carga) que un generador de texto no puede garantizar y no existen datos para entrenar un modelo propio. Decide un método simbólico verificable, el aprendizaje se limita a lo que se aprende con pocos datos, y el modelo de lenguaje solo conversa donde un error es de bajo riesgo y va advertido.

## Límites que conviene decir en voz alta
- No garantiza el óptimo (heurística).
- Las horas base por tipo y los márgenes por dificultad son supuestos propios.
- La intención se detecta por palabras clave: frases muy distintas a las previstas pasan al modelo de lenguaje (si existe) o reciben una respuesta de ayuda.
- Los métodos de estudio son efectos promedio de estudios publicados, no garantías individuales; verificar las citas antes de usarlas.
- No hay evaluación con usuarios reales.
