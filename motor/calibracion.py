"""SemestrIA - calibración de estimaciones a partir de la experiencia del estudiante.

Las horas base por tipo de trabajo y los factores de dificultad son supuestos. Cuando el estudiante
marca un trabajo como hecho puede registrar cuántas horas le tomó de verdad; con esos ejemplos el
sistema aprende un factor multiplicativo por tipo de trabajo y lo aplica a las estimaciones futuras.

Método (explicable y estable con pocos datos): promedio geométrico de las razones real/estimado,
encogido hacia 1 con un a priori de K_PRIOR observaciones, primero a nivel global y luego por tipo:

    f_global = exp( n * media(ln r) / (n + K) )
    f_tipo   = exp( (n_t * media_t(ln r) + K * ln f_global) / (n_t + K) )     acotado a [F_MIN, F_MAX]

Con 0 registros el factor es exactamente 1 (el plan no cambia); a medida que hay datos, se acerca a
la razón observada. La razón se mide contra la estimación base (sin calibrar) para no acumular correcciones.
"""
from __future__ import annotations

import math

K_PRIOR = 3          # observaciones "virtuales" que anclan el factor en 1
F_MIN, F_MAX = 0.5, 2.0
MIN_RAZON, MAX_RAZON = 0.1, 10.0   # descarta registros absurdos (errores de captura)


def _razones(historial: list[dict]) -> list[tuple[str, float]]:
    res = []
    for h in historial or []:
        try:
            est, real = float(h["base_h"]), float(h["real_h"])
        except (KeyError, TypeError, ValueError):
            continue
        if est > 0 and real > 0 and MIN_RAZON <= real / est <= MAX_RAZON:
            res.append((h.get("tipo", ""), math.log(real / est)))
    return res


def factor_global(historial: list[dict]) -> float:
    r = _razones(historial)
    if not r:
        return 1.0
    n = len(r)
    return min(F_MAX, max(F_MIN, math.exp(sum(x for _, x in r) / n * n / (n + K_PRIOR))))


def factor_calibracion(historial: list[dict], tipo: str | None = None) -> float:
    """Factor multiplicativo para las estimaciones de `tipo` (o global si tipo es None)."""
    r = _razones(historial)
    if not r:
        return 1.0
    g = factor_global(historial)
    if tipo is None:
        return g
    xs = [x for t, x in r if t == tipo]
    n = len(xs)
    f = math.exp((sum(xs) + K_PRIOR * math.log(g)) / (n + K_PRIOR))
    return min(F_MAX, max(F_MIN, f))


def resumen_calibracion(historial: list[dict], tipos: list[str]) -> list[dict]:
    """Tabla para mostrar al usuario: por tipo, cuántos registros y qué factor se aplica."""
    r = _razones(historial)
    return [{"tipo": t, "registros": sum(1 for tt, _ in r if tt == t),
             "factor": round(factor_calibracion(historial, t), 2)} for t in tipos]
