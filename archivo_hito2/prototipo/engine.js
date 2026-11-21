/* SemestrIA - motor de recomendación (puerto a JavaScript del motor Python).
 * Misma lógica, mismos nombres y mismos resultados: se verifica en pruebas/cruce_js_python.js.
 * Fechas = milisegundos UTC a medianoche; duraciones = minutos enteros.
 */
(function (root) {
  "use strict";

  const HORAS_POR_CREDITO = 48; // Decreto 1330 de 2019, Art. 2.5.3.2.4.1
  const SEMANAS_PERIODO = 16;
  const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
  const HORAS_BASE = { Taller: 2.0, Laboratorio: 3.0, Proyecto: 6.0, Parcial: 5.0 };
  const FACTOR_DIFICULTAD = { "Fácil": 0.75, Medio: 1.0, "Difícil": 1.5 };
  const RANGO_DIFICULTAD = { "Fácil": 1, Medio: 2, "Difícil": 3 };
  const MARGEN_DIAS = { "Fácil": 0, Medio: 1, "Difícil": 2 };
  const MS_DIA = 86400000;

  function config(over) {
    const c = Object.assign({
      dia_inicio: 7 * 60, dia_fin: 21 * 60, max_horas_dia: 6.0, max_min_tarea_dia: 120,
      bloque_max: 120, bloque_min: 60, paso: 30, usar_huecos: true, hueco_minimo: 60,
    }, over || {});
    c.cap_dia = Math.floor(c.max_horas_dia * 60);
    return c;
  }

  // ---- utilidades de tiempo ----
  const aMin = (s) => { const p = s.split(":"); return Number(p[0]) * 60 + Number(p[1]); };
  const aHHMM = (m) => String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0");
  const fecha = (s) => { const p = s.split("-").map(Number); return Date.UTC(p[0], p[1] - 1, p[2]); };
  const iso = (ms) => { const d = new Date(ms); return d.getUTCFullYear() + "-" + String(d.getUTCMonth() + 1).padStart(2, "0") + "-" + String(d.getUTCDate()).padStart(2, "0"); };
  const ddmm = (ms) => { const d = new Date(ms); return String(d.getUTCDate()).padStart(2, "0") + "/" + String(d.getUTCMonth() + 1).padStart(2, "0"); };
  const weekday = (ms) => (new Date(ms).getUTCDay() + 6) % 7;
  const addDias = (ms, n) => ms + n * MS_DIA;
  const ordinal = (ms) => Math.round(ms / MS_DIA);
  const redondearArriba = (m, paso) => Math.ceil(m / (paso || 30)) * (paso || 30);
  const semanaDelSemestre = (f, inicio) => Math.floor((f - inicio) / MS_DIA / 7) + 1;
  const paridad = (s) => (s % 2 === 0 ? "par" : "impar");
  const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  const cmpTupla = (a, b) => { for (let i = 0; i < a.length; i++) { const c = cmp(a[i], b[i]); if (c) return c; } return 0; };

  // ---- créditos -> tiempo ----
  function creditosDe(materia, datos) {
    const m = datos.materias.find((x) => x.codigo === materia);
    if (!m) throw new Error("Materia desconocida: " + materia);
    return m.creditos;
  }
  const horasTotalesSemana = (cred) => (cred * HORAS_POR_CREDITO) / SEMANAS_PERIODO;

  function contactoSemanalMin(materia, datos) {
    let total = 0;
    for (const b of datos.bloques) {
      if (b.materia !== materia) continue;
      let dur = aMin(b.fin) - aMin(b.inicio);
      const cfg = (datos.labs || {})[materia] || {};
      if (b.tipo === "LAB" && cfg.frecuencia === "quincenal") dur = dur / 2;
      total += dur;
    }
    return total;
  }
  const horasIndependientes = (materia, datos) =>
    Math.max(0, horasTotalesSemana(creditosDe(materia, datos)) - contactoSemanalMin(materia, datos) / 60);

  // ---- horario ----
  function sesionOcurre(b, f, datos) {
    const inicio = fecha(datos.semestre_inicio);
    if (f < inicio) return false;
    if (b.tipo === "LAB") {
      const cfg = (datos.labs || {})[b.materia] || {};
      if (cfg.frecuencia === "quincenal") return paridad(semanaDelSemestre(f, inicio)) === cfg.semanas;
    }
    return true;
  }
  function bloquesDelDia(f, datos) {
    return datos.bloques.filter((b) => b.dia === weekday(f) && sesionOcurre(b, f, datos)).sort((a, b) =>
      cmpTupla([aMin(a.inicio), aMin(a.fin), a.materia], [aMin(b.inicio), aMin(b.fin), b.materia]));
  }
  function dispDia(datos, wd) {
    const v = (datos.disponibilidad || {})[String(wd)] || {};
    return { disponible: v.disponible === undefined ? true : v.disponible, inicio_trabajo: v.inicio_trabajo || null };
  }
  function salidaDelDia(dia, datos) {
    const fines = datos.bloques.filter((b) => b.dia === dia).map((b) => aMin(b.fin));
    return fines.length ? Math.max.apply(null, fines) : null;
  }

  function ventanasLibres(f, datos, cfg, ahora) {
    const disp = dispDia(datos, weekday(f));
    if (!disp.disponible) return [];
    const ocupado = [];
    for (const b of bloquesDelDia(f, datos)) {
      const s = aMin(b.inicio), e = aMin(b.fin);
      if (ocupado.length && s <= ocupado[ocupado.length - 1][1]) ocupado[ocupado.length - 1][1] = Math.max(ocupado[ocupado.length - 1][1], e);
      else ocupado.push([s, e]);
    }
    const iniTrabajo = disp.inicio_trabajo ? aMin(disp.inicio_trabajo) : cfg.dia_inicio;
    const brutas = [];
    let cursor = cfg.dia_inicio;
    for (const se of ocupado) {
      const s = se[0], e = se[1];
      if (Math.min(s, cfg.dia_fin) > cursor) brutas.push([cursor, Math.min(s, cfg.dia_fin), false]);
      cursor = Math.max(cursor, e);
    }
    if (cursor < cfg.dia_fin) brutas.push([cursor, cfg.dia_fin, true]);
    const res = [];
    for (const br of brutas) {
      let s = br[0]; const e = br[1];
      if (br[2]) s = Math.max(s, iniTrabajo);
      else if (!cfg.usar_huecos) continue;
      if (ahora && ahora.fecha === f) s = Math.max(s, redondearArriba(ahora.min, cfg.paso));
      if (e - s >= cfg.hueco_minimo) res.push([s, e]);
    }
    return res;
  }

  // ---- trabajos ----
  const horasEstimadas = (tipo, dif, override) =>
    Math.ceil((override !== undefined && override !== null ? override : HORAS_BASE[tipo] * FACTOR_DIFICULTAD[dif]) * 2) / 2;

  function mkTarea(id, materia, tipo, titulo, due, dif, horas, desde, desdeMin, auto) {
    return { id, materia, tipo, titulo, due, dificultad: dif, min: Math.floor(horasEstimadas(tipo, dif, horas) * 60), desde, desde_min: desdeMin, auto };
  }
  function tareasManuales(datos, hoy) {
    const hechas = datos.hechas || [];
    return (datos.trabajos || []).filter((t) => !hechas.includes(t.id)).map((t) =>
      mkTarea(t.id, t.materia, t.tipo, t.titulo, fecha(t.entrega), t.dificultad, t.horas === undefined ? null : t.horas,
        t.desde ? fecha(t.desde) : hoy, 0, false));
  }
  function tareasAutomaticas(datos, hoy, hasta) {
    const inicio = fecha(datos.semestre_inicio);
    const hechas = new Set(datos.hechas || []);
    const res = [];
    for (let d = addDias(hoy, -14); d <= hasta; d = addDias(d, 1)) {
      for (const b of datos.bloques) {
        if (b.tipo !== "LAB" || b.dia !== weekday(d) || !sesionOcurre(b, d, datos)) continue;
        const cfg = (datos.labs || {})[b.materia];
        if (!cfg || !cfg.dias_entrega) continue;
        const due = addDias(d, cfg.dias_entrega);
        const tid = "lab:" + b.materia + ":" + iso(d);
        if (due < hoy || due > hasta || hechas.has(tid)) continue;
        res.push(mkTarea(tid, b.materia, "Laboratorio", "Informe de laboratorio " + b.materia + " (" + ddmm(d) + ")",
          due, cfg.dificultad, null, d, aMin(b.fin), true));
      }
      for (const materia of Object.keys(datos.entregas_clase || {})) {
        const cfg = datos.entregas_clase[materia];
        if (!cfg.frecuencia || cfg.frecuencia === "ninguna") continue;
        const lecs = datos.bloques.filter((b) => b.materia === materia && b.tipo === "LEC")
          .sort((a, b) => cmpTupla([a.dia, aMin(a.inicio)], [b.dia, aMin(b.inicio)]));
        if (!lecs.length || lecs[0].dia !== weekday(d)) continue;
        if (cfg.frecuencia === "quincenal" && paridad(semanaDelSemestre(d, inicio)) !== cfg.semanas) continue;
        const due = addDias(d, cfg.dias_entrega);
        const tid = "taller:" + materia + ":" + iso(d);
        if (due < hoy || due > hasta || hechas.has(tid)) continue;
        res.push(mkTarea(tid, materia, "Taller", "Taller " + materia + " (" + ddmm(d) + ")", due, cfg.dificultad, null, d, aMin(lecs[0].fin), true));
      }
    }
    return res;
  }
  // Tope de minutos por tarea y día; con la entrega a 1 día o menos se duplica (modo urgente).
  const topeTarea = (t, d, cfg) => (Math.round((t.due - d) / MS_DIA) <= 1 ? cfg.max_min_tarea_dia * 2 : cfg.max_min_tarea_dia);

  function finHorizonte(datos, hoy) {
    const domingo = addDias(hoy, 6 - weekday(hoy));
    let fin = addDias(domingo, 14);
    const hechas = datos.hechas || [];
    for (const t of datos.trabajos || []) {
      if (hechas.includes(t.id)) continue;
      const e = fecha(t.entrega);
      const eDom = addDias(e, 6 - weekday(e));
      if (eDom > fin && (eDom - hoy) / MS_DIA <= 56) fin = eDom;
    }
    return fin;
  }

  function restar(ventana, bloques) {
    let cur = ventana[0]; const e = ventana[1]; const res = [];
    for (const bb of bloques.slice().sort((a, b) => a[0] - b[0])) {
      if (bb[1] <= cur || bb[0] >= e) continue;
      if (bb[0] > cur) res.push([cur, bb[0]]);
      cur = Math.max(cur, bb[1]);
    }
    if (cur < e) res.push([cur, e]);
    return res;
  }
  const r1 = (x) => Math.round(x * 10) / 10;
  const g = (x) => String(x);

  // ---- planificador ----
  function planificar(datos, ahora, over) {
    const cfg = config(over);
    const hoy = ahora.fecha;
    const hasta = finHorizonte(datos, hoy);
    const tareas = tareasManuales(datos, hoy).concat(tareasAutomaticas(datos, hoy, hasta));
    const restante = {};
    tareas.forEach((t) => { restante[t.id] = t.min; });
    const bloques = [];
    const usadoDia = {};
    const usadoTarea = {};
    const ventanasDia = {};

    const prioridad = (t) => [ordinal(addDias(t.due, -MARGEN_DIAS[t.dificultad])), -RANGO_DIFICULTAD[t.dificultad], ordinal(t.due), t.id];
    const motivoTarea = (t, f) => {
      const dias = Math.round((t.due - f) / MS_DIA);
      const margen = MARGEN_DIAS[t.dificultad];
      const extra = margen ? " · " + margen + " día(s) de colchón por dificultad " + t.dificultad : " · dificultad " + t.dificultad;
      const cuando = dias === 0 ? "entrega hoy" : "entrega en " + dias + " día(s) (" + ddmm(t.due) + ")";
      const base = cuando.charAt(0).toUpperCase() + cuando.slice(1) + extra;
      if (dias <= 1) return base + ". Entrega inminente: se permite hasta " + Math.floor(topeTarea(t, f, cfg) / 60) + " h por día en esta tarea.";
      return base + ". Se reparte en bloques de máx. " + Math.floor(cfg.max_min_tarea_dia / 60) + " h por día.";
    };

    // Pasada 1: tareas (EDF con colchón por dificultad)
    for (let d = hoy; d <= hasta; d = addDias(d, 1)) {
      const ventanas = ventanasLibres(d, datos, cfg, ahora);
      ventanasDia[d] = ventanas;
      usadoDia[d] = 0;
      for (const w of ventanas) {
        const e = w[1];
        let cursor = w[0];
        while (e - cursor >= cfg.paso && usadoDia[d] < cfg.cap_dia) {
          let elegido = null;
          const cands = tareas.filter((t) => restante[t.id] > 0 && d <= t.due &&
            (d > t.desde || (d === t.desde && cursor >= t.desde_min)) &&
            (usadoTarea[t.id + "|" + d] || 0) < topeTarea(t, d, cfg));
          cands.sort((a, b) => cmpTupla(prioridad(a), prioridad(b)));
          for (const t of cands) {
            let chunk = Math.min(e - cursor, restante[t.id], topeTarea(t, d, cfg) - (usadoTarea[t.id + "|" + d] || 0), cfg.cap_dia - usadoDia[d], cfg.bloque_max);
            chunk = Math.floor(chunk / cfg.paso) * cfg.paso;
            if (chunk >= cfg.bloque_min || (chunk >= cfg.paso && chunk === restante[t.id])) { elegido = [t, chunk]; break; }
          }
          if (!elegido) { cursor += cfg.paso; continue; }
          const t = elegido[0], chunk = elegido[1];
          bloques.push({ fecha: iso(d), inicio: aHHMM(cursor), fin: aHHMM(cursor + chunk), tipo: "tarea", materia: t.materia,
            titulo: t.titulo, dificultad: t.dificultad, tarea_id: t.id, motivo: motivoTarea(t, d) });
          restante[t.id] -= chunk;
          usadoTarea[t.id + "|" + d] = (usadoTarea[t.id + "|" + d] || 0) + chunk;
          usadoDia[d] += chunk;
          cursor += chunk;
        }
      }
    }

    // Pasada 2: estudio independiente con lo que sobra
    const resumen = {};
    const materias = datos.materias.map((m) => m.codigo);
    for (let lunes = addDias(hoy, -weekday(hoy)); lunes <= hasta; lunes = addDias(lunes, 7)) {
      const diasSem = [0, 1, 2, 3, 4, 5, 6].map((i) => addDias(lunes, i));
      const diasHor = diasSem.filter((x) => x >= hoy && x <= hasta);
      const dispTotal = diasSem.filter((x) => dispDia(datos, weekday(x)).disponible).length;
      const dispRest = diasHor.filter((x) => dispDia(datos, weekday(x)).disponible).length;
      const fraccion = dispTotal ? dispRest / dispTotal : 0;
      const tareasSem = {};
      materias.forEach((m) => { tareasSem[m] = 0; });
      for (const b of bloques) {
        const bf = fecha(b.fecha);
        if (b.tipo === "tarea" && bf >= lunes && bf <= addDias(lunes, 6)) tareasSem[b.materia] += aMin(b.fin) - aMin(b.inicio);
      }
      const faltan = {}, metaTotal = {};
      materias.forEach((m) => {
        const base = Math.trunc(horasIndependientes(m, datos) * 60 * fraccion);
        metaTotal[m] = base;
        faltan[m] = Math.max(0, Math.floor(base / cfg.paso) * cfg.paso - tareasSem[m]);
      });
      for (const x of diasHor) {
        const usadoMatDia = {};
        const ocupados = bloques.filter((b) => b.fecha === iso(x)).map((b) => [aMin(b.inicio), aMin(b.fin)]);
        for (const ventana of ventanasDia[x] || []) {
          for (const seg of restar(ventana, ocupados)) {
            const e = seg[1];
            let cursor = seg[0];
            while (e - cursor >= cfg.paso && usadoDia[x] < cfg.cap_dia) {
              const cand = materias.filter((m) => faltan[m] > 0 && (usadoMatDia[m] || 0) < cfg.max_min_tarea_dia);
              cand.sort((a, b) => cmpTupla([-faltan[a], materias.indexOf(a)], [-faltan[b], materias.indexOf(b)]));
              let elegido = null;
              for (const m of cand) {
                let chunk = Math.min(e - cursor, faltan[m], cfg.max_min_tarea_dia - (usadoMatDia[m] || 0), cfg.cap_dia - usadoDia[x], cfg.bloque_max);
                chunk = Math.floor(chunk / cfg.paso) * cfg.paso;
                if (chunk >= cfg.bloque_min || (chunk >= cfg.paso && chunk === faltan[m])) { elegido = [m, chunk]; break; }
              }
              if (!elegido) { cursor += cfg.paso; continue; }
              const m = elegido[0], chunk = elegido[1];
              const h = horasIndependientes(m, datos);
              bloques.push({ fecha: iso(x), inicio: aHHMM(cursor), fin: aHHMM(cursor + chunk), tipo: "estudio", materia: m,
                titulo: "Estudio independiente · " + m, dificultad: null, tarea_id: null,
                motivo: "Meta semanal de " + m + ": " + creditosDe(m, datos) + " créditos × 3 h − horas en clase = " + h.toFixed(1) + " h de estudio independiente." });
              faltan[m] -= chunk;
              usadoMatDia[m] = (usadoMatDia[m] || 0) + chunk;
              usadoDia[x] += chunk;
              cursor += chunk;
            }
          }
        }
      }
      resumen[iso(lunes)] = {};
      for (const m of materias) {
        let est = 0;
        for (const b of bloques) {
          const bf = fecha(b.fecha);
          if (b.tipo === "estudio" && b.materia === m && bf >= lunes && bf <= addDias(lunes, 6)) est += aMin(b.fin) - aMin(b.inicio);
        }
        resumen[iso(lunes)][m] = { meta_h: r1(metaTotal[m] / 60), tareas_h: r1(tareasSem[m] / 60), estudio_h: r1(est / 60) };
      }
    }

    const advertencias = [];
    for (const t of tareas) {
      if (restante[t.id] > 0) {
        advertencias.push({ tipo: "no_cabe", tarea_id: t.id, titulo: t.titulo, faltan_h: restante[t.id] / 60,
          mensaje: "No alcanza el tiempo libre: faltan " + g(restante[t.id] / 60) + " h para «" + t.titulo + "» antes del " + ddmm(t.due) + "." });
      }
    }
    for (const t of datos.trabajos || []) {
      if (!(datos.hechas || []).includes(t.id) && fecha(t.entrega) < hoy) {
        advertencias.push({ tipo: "vencida", tarea_id: t.id, titulo: t.titulo, faltan_h: 0, mensaje: "«" + t.titulo + "» ya venció (" + ddmm(fecha(t.entrega)) + ")." });
      }
    }
    bloques.sort((a, b) => cmpTupla([a.fecha, a.inicio, a.materia], [b.fecha, b.inicio, b.materia]));
    return {
      bloques, advertencias, resumen,
      tareas: tareas.map((t) => Object.assign({}, t, { due: iso(t.due), desde: iso(t.desde) })),
      horizonte: [iso(hoy), iso(hasta)],
    };
  }

  const API = {
    DIAS, HORAS_BASE, FACTOR_DIFICULTAD, MARGEN_DIAS, HORAS_POR_CREDITO, SEMANAS_PERIODO, config,
    aMin, aHHMM, fecha, iso, ddmm, weekday, addDias, semanaDelSemestre, paridad,
    creditosDe, horasTotalesSemana, contactoSemanalMin, horasIndependientes, sesionOcurre, bloquesDelDia,
    salidaDelDia, ventanasLibres, horasEstimadas, tareasManuales, tareasAutomaticas, planificar,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  else root.SemestrIA = API;
})(typeof window !== "undefined" ? window : this);
