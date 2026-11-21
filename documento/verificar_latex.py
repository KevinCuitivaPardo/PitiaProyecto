"""Revisión estática del documento LaTeX (útil cuando no hay compilador a mano).

Comprueba: entornos y llaves balanceados, \\ref sin \\label, citas sin entrada en el .bib,
macros de cifras sin definir, imágenes y \\input inexistentes, y placeholders pendientes.
Uso:  python documento/verificar_latex.py
"""
import glob
import os
import re
import sys
from collections import Counter

os.chdir(os.path.dirname(os.path.abspath(__file__)))
archivos = sorted(glob.glob("content/*.tex") + glob.glob("anexos/*.tex") + glob.glob("auto/*.tex") + ["main.tex"])
texto = {f.replace(os.sep, "/"): open(f, encoding="utf-8").read() for f in archivos}
sin_comentarios = lambda s: re.sub(r"(?<!\\)%.*", "", s)
problemas = []

for f, t in texto.items():
    t = sin_comentarios(t)
    b, e = Counter(re.findall(r"\\begin\{(\w+\*?)\}", t)), Counter(re.findall(r"\\end\{(\w+\*?)\}", t))
    for k in set(b) | set(e):
        if b[k] != e[k]:
            problemas.append(f"{f}: entorno «{k}» abre {b[k]} y cierra {e[k]}")
    abre, cierra = len(re.findall(r"(?<!\\)\{", t)), len(re.findall(r"(?<!\\)\}", t))
    if abre != cierra:
        problemas.append(f"{f}: llaves desbalanceadas ({abre} abren, {cierra} cierran)")

todo = sin_comentarios("\n".join(texto.values()))
labels = set(re.findall(r"\\label\{([^}]+)\}", todo))
refs = set(re.findall(r"\\(?:ref|nameref)\{([^}]+)\}", todo))
problemas += [f"\\ref sin \\label: {r}" for r in sorted(refs - labels)]

bib = open("bibliography/references.bib", encoding="utf-8").read()
claves = set(re.findall(r"@\w+\{([^,]+),", bib))
citas = {k.strip() for m in re.findall(r"\\(?:parencite|textcite|cite)\{([^}]+)\}", todo) for k in m.split(",")}
problemas += [f"cita sin entrada en el .bib: {c}" for c in sorted(citas - claves)]

macros = set(re.findall(r"\\newcommand\{\\(\w+)\}", texto["auto/numeros.tex"]))
problemas += [f"macro de cifra sin definir: \\{m}" for m in sorted(set(re.findall(r"\\(res[A-Z]\w*)", todo)) - macros)]
problemas += [f"imagen inexistente: {i}" for i in sorted(set(re.findall(r"includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", todo))) if not os.path.exists(i)]
problemas += [f"\\input inexistente: {i}" for i in re.findall(r"\\input\{([^}]+)\}", todo) if not (os.path.exists(i) or os.path.exists(i + ".tex"))]

pendientes = sorted({m for t in texto.values() for m in re.findall(r"\[[^\]\n]*(?:N\.º|Nombre|día|mes)[^\]\n]*\]", t)})
print("Entradas del .bib sin citar:", sorted(claves - citas) or "ninguna")
print("Placeholders por completar:", pendientes or "ninguno")
print("PROBLEMAS:" if problemas else "Sin problemas estructurales.")
for p in problemas:
    print(" -", p)
sys.exit(1 if problemas else 0)
