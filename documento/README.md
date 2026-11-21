# Documento del proyecto (plantilla LaTeX PTIA - ECI)

Basado en la plantilla institucional. Contenido en `content/` (una sección por archivo), bibliografía en `bibliography/references.bib`.

## Compilar
En **Overleaf**: subir esta carpeta, elegir compilador **XeLaTeX** y abrir `main.tex`. El estilo usa `biblatex` con `biber` y el paquete `minted`; Overleaf los resuelve sin configuración extra.

## Antes de entregar
1. Completar los placeholders (`python documento/verificar_latex.py` los lista): grupo, segundo integrante y fecha en `content/portada.tex`, y nombres y fecha en `content/declaracion.tex`.
2. Confirmar los problemas 2 y 3 de `content/introduccion.tex` y las calificaciones de la tabla de selección en `content/descripcion_problema.tex` (son una propuesta).
3. **Verificar cada referencia** de `bibliography/references.bib` (autores, volumen, páginas, DOI).
4. Revisar el PDF: no se pudo compilar en la máquina donde se redactó; `verificar_latex.py` solo comprueba la estructura (entornos, referencias, citas, imágenes).

## Regenerar cifras, tablas y figuras
Los números del texto salen de la evaluación; no se escriben a mano.

```bash
python pruebas/evaluacion.py --figuras   # resultados/ y documento/img/fig_*.png
python documento/generar_tablas.py       # documento/auto/*.tex
python diseno/capturar.py                # capturas de la interfaz (documento/img/pant_*.png)
python diseno/generar_diagramas.py       # arquitectura y algoritmo
python documento/verificar_latex.py      # revisión estática
```
