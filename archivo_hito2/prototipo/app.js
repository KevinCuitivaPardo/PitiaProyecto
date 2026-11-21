/* SemestrIA - prototipo de interfaz. Usa el mismo motor que el código Python (engine.js). */
(function () {
  "use strict";
  const E = window.SemestrIA;
  const EJEMPLO = /*__DATA__*/ {};
  const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const DIAS_CORTO = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"];
  const DIAS = E.DIAS;
  const TIPOS = ["Proyecto", "Parcial", "Laboratorio", "Taller"];
  const DIFS = ["Fácil", "Medio", "Difícil"];
  const ROW = 44, H0 = 7 * 60;
  const MS_DIA = 86400000;
  const PASOS = [
    { t: "Horario", s: "Sube tu horario fijo" },
    { t: "Créditos y disponibilidad", s: "Cuándo puedes trabajar" },
    { t: "Laboratorios y entregas", s: "Frecuencia y plazos" },
    { t: "Trabajos", s: "Proyectos, labs y parciales" },
    { t: "Mi semana", s: "Tu plan recomendado" },
  ];

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const isoLocal = (d) => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  const fmtH = (h) => h.toLocaleString("es-CO", { maximumFractionDigits: 1 }) + " h";
  const fmtFecha = (ms) => DIAS_CORTO[E.weekday(ms)] + " " + new Date(ms).getUTCDate() + " " + MESES[new Date(ms).getUTCMonth()];
  const hhmm12 = (m) => E.aHHMM(m).replace(/^0/, "");
  const hora12 = (m) => { const h = Math.floor(m / 60); return (h % 12 === 0 ? 12 : h % 12) + ":" + String(m % 60).padStart(2, "0") + (h < 12 ? " a. m." : " p. m."); };
  const clone = (o) => JSON.parse(JSON.stringify(o));

  // ------------------------------------------------------------------ estado
  const state = {
    paso: 0, cargado: false, leyendo: false, datos: null, plan: null,
    fechaSim: isoLocal(new Date()), semana: 0, sel: null, msg: "",
    maxH: 6, usarHuecos: true, hechasInfo: {}, form: null, formMsg: "",
  };

  function semilla(hoyMs) {
    const f = (n) => E.iso(E.addDias(hoyMs, n));
    return [
      { id: "m1", materia: "MATE ECDI", tipo: "Parcial", titulo: "Parcial 2 de ECDI", entrega: f(8), dificultad: "Difícil" },
      { id: "m2", materia: "ISIS ARSW", tipo: "Proyecto", titulo: "Proyecto ARSW - entrega 1", entrega: f(11), dificultad: "Medio" },
      { id: "m3", materia: "ISIS PTIA", tipo: "Proyecto", titulo: "Proyecto PTIA - Hito 2", entrega: f(18), dificultad: "Medio", horas: 8 },
    ];
  }

  function iniciar() {
    state.datos = clone(EJEMPLO);
    state.datos.trabajos = semilla(ahora().fecha);
    state.datos.hechas = [];
    state.form = nuevoForm();
  }
  function nuevoForm() {
    return { materia: state.datos.materias[0].codigo, tipo: "Proyecto", titulo: "", entrega: E.iso(E.addDias(ahora().fecha, 7)), dificultad: "Medio", horas: "" };
  }
  function ahora() {
    const n = new Date();
    const real = isoLocal(n);
    return { fecha: E.fecha(state.fechaSim), min: state.fechaSim === real ? n.getHours() * 60 + n.getMinutes() : H0, esReal: state.fechaSim === real };
  }
  function recalcular() {
    state.sel = null;
    state.plan = state.cargado
      ? E.planificar(state.datos, ahora(), E.config({ max_horas_dia: state.maxH, usar_huecos: state.usarHuecos }))
      : null;
  }
  const semanasDisp = () => (state.plan ? Object.keys(state.plan.resumen).sort() : []);
  const lunesDe = (ms) => E.addDias(ms, -E.weekday(ms));

  // ------------------------------------------------------------------ piezas
  function seg(opts, valor, attrs, difColor) {
    return '<div class="seg" role="group">' + opts.map((o) => {
      const v = Array.isArray(o) ? o[0] : o, t = Array.isArray(o) ? o[1] : o;
      return `<button type="button" aria-pressed="${String(v) === String(valor)}" ${attrs} data-v="${esc(v)}" ${difColor ? `data-dif="${esc(v)}"` : ""}>${esc(t)}</button>`;
    }).join("") + "</div>";
  }

  function grid(lunes, o) {
    o = o || {};
    const a = ahora();
    let head = '<div class="hd"></div>', cols = "";
    let horas = '<div class="horas">';
    for (let h = 7; h <= 21; h++) horas += `<span style="top:${(h - 7) * ROW}px">${h}:00</span>`;
    horas += "</div>";
    for (let i = 0; i < 7; i++) {
      const d = E.addDias(lunes, i);
      const disp = state.datos.disponibilidad[String(i)] || {};
      const off = disp.disponible === false;
      const rec = o.rec ? state.plan.bloques.map((b, idx) => ({ b, idx })).filter((x) => x.b.fecha === E.iso(d)) : [];
      const horasDia = rec.reduce((s, x) => s + (E.aMin(x.b.fin) - E.aMin(x.b.inicio)), 0) / 60;
      const sub = o.rec ? (off ? "Descanso" : horasDia ? fmtH(horasDia) : "") : "";
      head += `<div class="hd ${d === a.fecha ? "hoy" : ""} ${off && o.rec ? "off" : ""}"><b>${DIAS_CORTO[i]} ${new Date(d).getUTCDate()}</b><small>${sub}</small></div>`;
      let c = "";
      const clases = o.nominal ? state.datos.bloques.filter((b) => b.dia === i) : E.bloquesDelDia(d, state.datos);
      for (const b of clases) {
        const s = E.aMin(b.inicio), e = E.aMin(b.fin);
        const tipo = b.tipo === "LAB" ? "Laboratorio" : "Clase";
        c += `<div class="blk clase" style="top:${(s - H0) / 60 * ROW}px;height:${(e - s) / 60 * ROW - 2}px" title="${esc(b.materia)} · ${tipo} ${b.inicio}–${b.fin} · ${esc(b.salon)}"><b>${esc(b.materia)}</b><span class="sub2">${tipo} · ${esc(b.salon)}</span></div>`;
      }
      if (!o.nominal) {
        for (const b of state.datos.bloques.filter((x) => x.dia === i && !E.sesionOcurre(x, d, state.datos) && d >= E.fecha(state.datos.semestre_inicio))) {
          const s = E.aMin(b.inicio), e = E.aMin(b.fin);
          c += `<div class="blk fantasma" style="top:${(s - H0) / 60 * ROW}px;height:${(e - s) / 60 * ROW - 2}px"><b>${esc(b.materia)}</b><span class="sub2">Sin laboratorio esta semana</span></div>`;
        }
      }
      for (const x of rec) {
        const b = x.b, s = E.aMin(b.inicio), e = E.aMin(b.fin);
        const cls = b.tipo === "estudio" ? "estudio" : b.dificultad;
        const t = b.tipo === "estudio" ? "Estudio · " + b.materia : b.titulo;
        c += `<button type="button" class="blk rec ${cls}" aria-pressed="${state.sel === x.idx}" data-action="sel" data-i="${x.idx}" style="top:${(s - H0) / 60 * ROW}px;height:${(e - s) / 60 * ROW - 2}px" title="${esc(t)} · ${b.inicio}–${b.fin}"><b>${esc(t)}</b><span class="sub2">${b.inicio}–${b.fin}</span></button>`;
      }
      if (o.rec && d === a.fecha && a.esReal && a.min >= H0 && a.min <= 21 * 60) c += `<div class="ahora" style="top:${(a.min - H0) / 60 * ROW}px" aria-hidden="true"></div>`;
      cols += `<div class="col ${off && o.rec ? "off" : ""}">${c}</div>`;
    }
    return `<div class="gscroll"><div class="g">${head}${horas}${cols}</div></div>`;
  }

  // ------------------------------------------------------------------ pasos
  function paso1() {
    if (!state.cargado && !state.leyendo) {
      return `<div class="drop">
        <h3>Sube tu horario del semestre</h3>
        <p>Es el mismo durante todo el semestre, así que solo lo cargas una vez. SemestrIA reconoce tus materias, si cada bloque es clase o laboratorio, y a qué hora sales cada día.</p>
        <label class="btn primary"><input class="sr" type="file" accept="image/*,.pdf" data-change="subir"> Subir captura o PDF</label>
        <button class="btn ghost" type="button" data-action="usar-ejemplo">Usar el horario de ejemplo</button>
        <p class="nota">Prototipo: la lectura automática de la imagen todavía no está implementada. Al subir un archivo se carga el horario real del equipo (6 materias, 14 bloques).</p>
      </div>`;
    }
    if (state.leyendo) return `<div class="drop"><div class="leyendo" role="status"><span class="spin"></span> Leyendo tu horario…</div></div>`;
    const d = state.datos;
    const chips = d.materias.map((m) => {
      const l = d.bloques.filter((b) => b.materia === m.codigo && b.tipo === "LAB").length, c = d.bloques.filter((b) => b.materia === m.codigo && b.tipo === "LEC").length;
      return `<li class="chip"><b>${esc(m.codigo)}</b> ${c} clase${c === 1 ? "" : "s"}${l ? ` · ${l} laboratorio${l === 1 ? "" : "s"}` : ""}</li>`;
    }).join("");
    return `<div class="card"><h3>Leímos tu horario</h3>
      <p class="sub">Encontramos ${d.materias.length} materias y ${d.bloques.length} bloques por semana. Los verdes son tus clases; revisa que estén bien antes de seguir.</p>
      <ul class="lista" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px">${chips}</ul>
      <div class="wk">${grid(lunesDe(ahora().fecha), { nominal: true, rec: false })}</div>
      <div class="actions"><button class="btn primary" type="button" data-action="ir" data-paso="1">Continuar: créditos y disponibilidad</button>
      <button class="btn ghost" type="button" data-action="reiniciar">Subir otro horario</button></div></div>`;
  }

  function paso2() {
    const d = state.datos;
    let totC = 0, totT = 0, totCl = 0, totI = 0;
    const filas = d.materias.map((m) => {
      const t = E.horasTotalesSemana(m.creditos), cl = E.contactoSemanalMin(m.codigo, d) / 60, ind = Math.max(0, t - cl);
      totC += m.creditos; totT += t; totCl += cl; totI += ind;
      return `<tr><td class="mat">${esc(m.codigo)}</td>
        <td><div class="ctr"><button type="button" aria-label="Menos créditos en ${esc(m.codigo)}" data-action="cred" data-mat="${esc(m.codigo)}" data-d="-1">−</button><b>${m.creditos}</b><button type="button" aria-label="Más créditos en ${esc(m.codigo)}" data-action="cred" data-mat="${esc(m.codigo)}" data-d="1">+</button></div></td>
        <td class="num">${fmtH(t)}</td><td class="num">${fmtH(cl)}</td><td class="num"><b>${fmtH(ind)}</b></td></tr>`;
    }).join("");
    const disp = DIAS.map((nom, i) => {
      const salida = E.salidaDelDia(i, d), v = d.disponibilidad[String(i)] || { disponible: true, inicio_trabajo: null };
      return `<div class="disp"><div><div class="dn">${nom}</div><div class="ds">${salida ? "Sales a las " + hora12(salida) : "No tienes clases"}</div></div>
        <label class="f"><span>Puedo empezar a trabajar a las</span><input type="time" value="${v.inicio_trabajo || ""}" ${v.disponible ? "" : "disabled"} data-change="ini" data-dia="${i}"></label>
        <label class="switch"><input type="checkbox" ${v.disponible ? "checked" : ""} data-change="disp" data-dia="${i}"> Disponible</label></div>`;
    }).join("");
    return `<div class="card"><h3>Créditos de cada materia</h3>
      <p class="sub">Cada crédito equivale a 48 horas de trabajo en el periodo (Decreto 1330 de 2019): 3 horas por semana en 16 semanas. Lo que no pasas en clase, lo estudias por tu cuenta.</p>
      <div class="scroll-x"><table class="tabla"><thead><tr><th>Materia</th><th>Créditos</th><th class="num">Trabajo total</th><th class="num">En clase</th><th class="num">Estudio independiente</th></tr></thead><tbody>${filas}</tbody>
      <tfoot><tr><td>Total</td><td>${totC}</td><td class="num">${fmtH(totT)}</td><td class="num">${fmtH(totCl)}</td><td class="num">${fmtH(totI)}</td></tr></tfoot></table></div></div>
      <div class="card"><h3>Cuándo puedes trabajar</h3>
      <p class="sub">Con tu horario sabemos a qué hora sales cada día. Dinos a qué hora puedes empezar a trabajar después: tiempo para llegar, almorzar o descansar.</p>${disp}
      <div class="q"><label class="switch"><input type="checkbox" ${state.usarHuecos ? "checked" : ""} data-change="huecos"> Aprovechar también los huecos entre clases (de 1 hora o más)</label></div>
      <div class="q"><label class="f" style="max-width:340px"><span>Máximo de horas de trabajo por día</span><input type="number" min="2" max="10" step="0.5" value="${state.maxH}" data-change="maxh"><span class="h">Un tope realista evita planes imposibles de cumplir.</span></label></div>
      <div class="actions"><button class="btn primary" type="button" data-action="ir" data-paso="2">Continuar: laboratorios y entregas</button></div></div>`;
  }

  function paso3() {
    const d = state.datos;
    const sem = E.semanaDelSemestre(ahora().fecha, E.fecha(d.semestre_inicio));
    const cards = d.materias.map((m) => {
      const labs = d.bloques.filter((b) => b.materia === m.codigo && b.tipo === "LAB");
      const lecs = d.bloques.filter((b) => b.materia === m.codigo && b.tipo === "LEC");
      const pills = d.bloques.filter((b) => b.materia === m.codigo).sort((a, b) => a.dia - b.dia)
        .map((b) => `<span class="pill ${b.tipo === "LAB" ? "lab" : ""}">${b.tipo === "LAB" ? "Laboratorio" : "Clase"} ${DIAS_CORTO[b.dia]} ${hhmm12(E.aMin(b.inicio))}–${hhmm12(E.aMin(b.fin))}</span>`).join(" ");
      let q = "";
      const a = `data-mat="${esc(m.codigo)}"`;
      if (labs.length) {
        const c = d.labs[m.codigo] = d.labs[m.codigo] || { frecuencia: "semanal", semanas: null, dias_entrega: 7, dificultad: "Medio" };
        q += `<div class="q"><div class="ql">¿Cada cuánto es el laboratorio?</div>${seg([["semanal", "Cada semana"], ["quincenal", "Cada 15 días"]], c.frecuencia, `data-action="lab" data-campo="frecuencia" ${a}`)}</div>`;
        if (c.frecuencia === "quincenal") q += `<div class="q"><div class="ql">¿En qué semanas tienes laboratorio?</div>${seg([["par", "Semanas pares"], ["impar", "Semanas impares"]], c.semanas, `data-action="lab" data-campo="semanas" ${a}`)}<span class="nota">Esta semana es la ${sem} (${E.paridad(sem)}) del semestre.</span></div>`;
        q += `<div class="q"><label class="f"><span>¿En cuántos días hay que entregar el informe?</span><input type="number" min="1" max="30" value="${c.dias_entrega}" data-change="lab-dias" ${a}></label></div>
              <div class="q"><div class="ql">¿Qué tan difíciles son sus informes?</div>${seg(DIFS, c.dificultad, `data-action="lab" data-campo="dificultad" ${a}`, true)}</div>`;
      }
      if (lecs.length) {
        const c = d.entregas_clase[m.codigo] = d.entregas_clase[m.codigo] || { frecuencia: "ninguna", semanas: null, dias_entrega: 7, dificultad: "Medio" };
        q += `<div class="q"><div class="ql">¿Te dejan talleres o entregas desde la clase?</div>${seg([["ninguna", "No"], ["semanal", "Cada semana"], ["quincenal", "Cada 15 días"]], c.frecuencia, `data-action="ec" data-campo="frecuencia" ${a}`)}</div>`;
        if (c.frecuencia === "quincenal") q += `<div class="q"><div class="ql">¿En qué semanas?</div>${seg([["par", "Semanas pares"], ["impar", "Semanas impares"]], c.semanas, `data-action="ec" data-campo="semanas" ${a}`)}</div>`;
        if (c.frecuencia !== "ninguna") q += `<div class="q"><label class="f"><span>¿En cuántos días hay que entregarlos?</span><input type="number" min="1" max="30" value="${c.dias_entrega}" data-change="ec-dias" ${a}></label></div>
              <div class="q"><div class="ql">¿Qué tan difíciles son?</div>${seg(DIFS, c.dificultad, `data-action="ec" data-campo="dificultad" ${a}`, true)}</div>`;
      }
      return `<div class="card"><h3>${esc(m.codigo)}</h3><div style="margin-top:6px">${pills}</div>${q}</div>`;
    }).join("");
    return `<div class="grid2">${cards}</div><div class="actions"><button class="btn primary" type="button" data-action="ir" data-paso="3">Continuar: trabajos</button></div>`;
  }

  function venceTxt(due) {
    const n = Math.round((E.fecha(due) - ahora().fecha) / MS_DIA);
    return n < 0 ? "vencida" : n === 0 ? "vence hoy" : n === 1 ? "vence mañana" : "vence en " + n + " días";
  }

  function paso4() {
    const f = state.form, d = state.datos;
    const est = E.horasEstimadas(f.tipo, f.dificultad, null);
    const manuales = d.trabajos.filter((t) => !d.hechas.includes(t.id));
    const auto = state.plan ? state.plan.tareas.filter((t) => t.auto).sort((a, b) => (a.due < b.due ? -1 : 1)) : [];
    const fila = (t, quitar) => `<li class="tarea"><span class="dot ${t.dificultad}" style="margin-top:7px"></span><div><div class="tt">${esc(t.titulo)}</div><div class="ts">${esc(t.materia)} · ${t.tipo} · entrega ${fmtFecha(E.fecha(t.entrega || t.due))}</div></div>
      <div class="th">${quitar ? `<button class="btn sm ghost" type="button" data-action="quitar" data-id="${esc(t.id)}">Quitar</button>` : fmtH((t.min !== undefined ? t.min : 0) / 60)}</div></li>`;
    return `<div class="grid2"><div class="card"><h3>Agregar un trabajo</h3>
      <p class="sub">Proyectos, parciales o cualquier entrega que no salga de tus laboratorios y talleres.</p>
      <div style="display:grid;gap:12px">
        <label class="f"><span>Materia</span><select data-change="form" data-campo="materia">${d.materias.map((m) => `<option ${m.codigo === f.materia ? "selected" : ""}>${esc(m.codigo)}</option>`).join("")}</select></label>
        <label class="f"><span>Tipo</span><select data-change="form" data-campo="tipo">${TIPOS.map((t) => `<option ${t === f.tipo ? "selected" : ""}>${t}</option>`).join("")}</select></label>
        <label class="f"><span>Nombre del trabajo</span><input type="text" value="${esc(f.titulo)}" placeholder="Ej. Entrega 2 del proyecto" data-input="form" data-campo="titulo"></label>
        <label class="f"><span>Fecha de entrega</span><input type="date" value="${f.entrega}" data-change="form" data-campo="entrega"></label>
        <div class="q" style="margin-top:0"><div class="ql">Dificultad</div>${seg(DIFS, f.dificultad, 'data-action="form-dif"', true)}</div>
        <label class="f"><span>Horas que crees que te tomará</span><input type="number" min="0.5" max="40" step="0.5" value="${f.horas}" placeholder="${est}" data-input="form" data-campo="horas"><span class="h">Si lo dejas vacío usamos ${fmtH(est)}, según el tipo y la dificultad.</span></label>
      </div>
      <div class="actions"><button class="btn primary" type="button" data-action="add-tarea">Agregar al calendario</button></div>
      ${state.formMsg ? `<div class="ok-msg" role="status">${esc(state.formMsg)}</div>` : ""}</div>
      <div class="card"><h3>Trabajos que agregaste</h3>${manuales.length ? `<ul class="lista">${manuales.map((t) => fila(t, true)).join("")}</ul>` : '<p class="vacio">Todavía no hay trabajos agregados.</p>'}
      <h3 style="margin-top:22px">Generados desde tus respuestas</h3>
      <p class="sub">Los informes de laboratorio y los talleres salen de las preguntas del paso anterior; no tienes que escribirlos.</p>
      ${auto.length ? `<ul class="lista">${auto.slice(0, 10).map((t) => fila(t, false)).join("")}</ul>${auto.length > 10 ? `<p class="nota" style="margin-top:8px">y ${auto.length - 10} más en las próximas semanas.</p>` : ""}` : '<p class="vacio">No hay informes ni talleres pendientes.</p>'}</div></div>
      <div class="actions"><button class="btn primary" type="button" data-action="ir" data-paso="4">Ver mi semana</button></div>`;
  }

  function paso5() {
    const sems = semanasDisp();
    if (state.semana >= sems.length) state.semana = 0;
    const lunesIso = sems[state.semana], lunes = E.fecha(lunesIso), a = ahora();
    const sNum = E.semanaDelSemestre(lunes, E.fecha(state.datos.semestre_inicio));
    const dom = E.addDias(lunes, 6);
    const rango = new Date(lunes).getUTCDate() + (new Date(lunes).getUTCMonth() === new Date(dom).getUTCMonth() ? "" : " " + MESES[new Date(lunes).getUTCMonth()]) + "–" + new Date(dom).getUTCDate() + " " + MESES[new Date(dom).getUTCMonth()];
    const p = state.plan;

    // detalle del bloque seleccionado
    let det = '<p class="vacio">Toca un bloque de la semana para ver por qué se recomienda en ese momento.</p>';
    if (state.sel !== null && p.bloques[state.sel]) {
      const b = p.bloques[state.sel];
      det = `<h3>${esc(b.tipo === "estudio" ? "Estudio · " + b.materia : b.titulo)}</h3>
        <div class="meta">${fmtFecha(E.fecha(b.fecha))}, ${hhmm12(E.aMin(b.inicio))}–${hhmm12(E.aMin(b.fin))} · ${esc(b.materia)}</div>
        <div class="por"><b>Por qué aquí:</b> ${esc(b.motivo)}</div>
        ${b.tipo === "tarea" ? `<div class="actions" style="margin-top:12px"><button class="btn primary sm" type="button" data-action="hecho" data-id="${esc(b.tarea_id)}">Marcar como hecho</button></div>` : ""}`;
    }
    // pendientes
    const pend = p.tareas.slice().sort((x, y) => (x.due < y.due ? -1 : x.due > y.due ? 1 : 0)).filter((t) => E.fecha(t.due) >= lunes);
    const pendHtml = pend.slice(0, 8).map((t) => `<li class="tarea ${E.fecha(t.due) < a.fecha ? "venc" : ""}"><input type="checkbox" aria-label="Marcar «${esc(t.titulo)}» como hecha" data-change="check-hecho" data-id="${esc(t.id)}">
      <div><div class="tt">${esc(t.titulo)}</div><div class="ts"><span class="dot ${t.dificultad}"></span>${t.dificultad} · ${venceTxt(t.due)}</div></div><div class="th">${fmtH(t.min / 60)}</div></li>`).join("");
    const hechas = Object.keys(state.hechasInfo).filter((id) => state.datos.hechas.includes(id));
    const hechasHtml = hechas.length ? `<h3 style="margin-top:16px;font-size:.95rem">Hechas (${hechas.length})</h3><ul class="lista">${hechas.map((id) => `<li class="tarea hecha"><input type="checkbox" checked aria-label="Desmarcar «${esc(state.hechasInfo[id])}»" data-change="check-deshacer" data-id="${esc(id)}"><div><div class="tt">${esc(state.hechasInfo[id])}</div></div><div></div></li>`).join("")}</ul>` : "";
    // carga por materia
    const res = p.resumen[lunesIso] || {};
    const barras = Object.keys(res).map((m) => {
      const r = res[m], tot = r.tareas_h + r.estudio_h, mx = Math.max(r.meta_h, tot, 0.1);
      const sobre = tot > r.meta_h + 0.05;
      return `<div class="barra"><div class="bl"><span>${esc(m)}</span><span class="${sobre ? "sobre" : ""}">${fmtH(tot)} de ${fmtH(r.meta_h)}${sobre ? " · supera la meta" : ""}</span></div><div class="pista" role="img" aria-label="${esc(m)}: ${fmtH(r.tareas_h)} en entregas y ${fmtH(r.estudio_h)} de estudio, meta ${fmtH(r.meta_h)}"><i class="t" style="width:${r.tareas_h / mx * 100}%"></i><i class="e" style="width:${r.estudio_h / mx * 100}%"></i>${sobre ? `<b class="tick" style="left:${r.meta_h / mx * 100}%"></b>` : ""}</div></div>`;
    }).join("");
    const alertas = p.advertencias.map((w) => `<div class="alerta" role="alert">${esc(w.mensaje)}</div>`).join("");

    return `<div class="semana"><div><div class="wk">
        <div class="wk-bar"><div><span class="tit">Semana ${sNum} · ${rango}</span> <span class="chip">${E.paridad(sNum)}</span></div>
          <div class="nav"><button class="btn sm" type="button" data-action="sem" data-d="-1" ${state.semana === 0 ? "disabled" : ""} aria-label="Semana anterior">←</button>
          <button class="btn sm" type="button" data-action="sem-hoy">Esta semana</button>
          <button class="btn sm" type="button" data-action="sem" data-d="1" ${state.semana >= sems.length - 1 ? "disabled" : ""} aria-label="Semana siguiente">→</button></div></div>
        <div class="leyenda"><span><i style="background:var(--clase)"></i>Clases</span><span><i style="background:var(--facil)"></i>Fácil</span><span><i style="background:var(--medio)"></i>Medio</span><span><i style="background:var(--dificil)"></i>Difícil</span><span><i style="background:var(--estudio)"></i>Estudio independiente</span><span><i style="border:1.5px dashed var(--clase-line)"></i>Sin laboratorio esta semana</span></div>
        ${grid(lunes, { rec: true })}</div></div>
      <div class="side">
        ${state.msg ? `<div class="ok-msg" role="status" style="margin:0">${esc(state.msg)}</div>` : ""}
        ${alertas ? `<div>${alertas}</div>` : ""}
        <div class="card det" aria-live="polite">${det}</div>
        <div class="card"><h3>Pendientes</h3><p class="sub">Marca lo que ya entregaste y reorganizamos lo que sigue.</p>
          ${pendHtml ? `<ul class="lista">${pendHtml}</ul>` : '<p class="vacio">No tienes entregas pendientes.</p>'}${pend.length > 8 ? `<p class="nota" style="margin-top:8px">y ${pend.length - 8} más adelante.</p>` : ""}${hechasHtml}</div>
        <div class="card"><h3>Carga de la semana</h3><p class="sub">Entregas y estudio frente a la meta que sale de tus créditos.</p>${barras}</div>
      </div></div>`;
  }

  // ------------------------------------------------------------------ render
  function render() {
    const root = document.getElementById("app");
    const a = ahora();
    const sem = E.semanaDelSemestre(a.fecha, E.fecha(state.datos.semestre_inicio));
    const titulos = ["Tu horario", "Créditos y disponibilidad", "Laboratorios y entregas", "Trabajos", "Tu semana"];
    const sub = [
      "Cargamos tu horario una vez y de ahí sale todo lo demás.",
      "Convertimos los créditos en horas de clase y de estudio, y marcamos cuándo puedes trabajar.",
      "Según el tipo de bloque, preguntamos cada cuánto hay laboratorio y cuándo se entrega.",
      "Agrega lo que no se repite: proyectos, parciales y entregas sueltas.",
      "Así organizamos tus huecos para llegar a todas las entregas sin dejar nada para la última noche.",
    ];
    const rail = `<aside class="rail"><div class="brand">SemestrIA<small>Organiza tu semestre</small></div>
      <ol class="steps">${PASOS.map((p, i) => `<li><button type="button" class="step ${i < state.paso && state.cargado ? "hecho" : ""}" ${i === state.paso ? 'aria-current="step"' : ""} data-action="ir" data-paso="${i}" ${!state.cargado && i > 0 ? "disabled" : ""}>
        <span class="n">${i < state.paso && state.cargado ? "✓" : i + 1}</span><span><span class="t">${p.t}</span><span class="s">${p.s}</span></span></button></li>`).join("")}</ol>
      <div class="sim"><label for="fsim">Simular otra fecha</label><input id="fsim" type="date" value="${state.fechaSim}" data-change="fsim"></div></aside>`;
    let cuerpo = "";
    if (state.paso === 0) cuerpo = paso1();
    else if (state.paso === 1) cuerpo = paso2();
    else if (state.paso === 2) cuerpo = paso3();
    else if (state.paso === 3) cuerpo = paso4();
    else cuerpo = paso5();
    root.innerHTML = `<div class="app">${rail}<main class="main"><div class="head"><div><h2>${titulos[state.paso]}</h2><p>${sub[state.paso]}</p></div>
      <span class="chip">Semana ${sem} del semestre · ${E.paridad(sem)}</span></div>${cuerpo}</main></div>`;
  }

  function ir(n) {
    if (!state.cargado && n > 0) return;
    state.paso = n; state.msg = ""; state.formMsg = "";
    if (n >= 3) recalcular();
    render();
    window.scrollTo(0, 0);
  }

  // ------------------------------------------------------------------ eventos
  const root = document.getElementById("app");
  root.addEventListener("click", (ev) => {
    const el = ev.target.closest("[data-action]");
    if (!el) return;
    const d = state.datos, a = el.dataset;
    switch (a.action) {
      case "ir": ir(Number(a.paso)); return;
      case "usar-ejemplo": cargarEjemplo(); return;
      case "reiniciar": state.cargado = false; state.paso = 0; render(); return;
      case "cred": { const m = d.materias.find((x) => x.codigo === a.mat); m.creditos = Math.min(6, Math.max(1, m.creditos + Number(a.d))); recalcular(); render(); return; }
      case "lab": case "ec": {
        const c = (a.action === "lab" ? d.labs : d.entregas_clase)[a.mat];
        c[a.campo] = a.v;
        if (a.campo === "frecuencia") c.semanas = a.v === "quincenal" ? (c.semanas || "par") : null;
        recalcular(); render(); return;
      }
      case "form-dif": state.form.dificultad = a.v; render(); return;
      case "add-tarea": {
        const f = state.form;
        if (!f.titulo.trim()) { state.formMsg = "Escribe el nombre del trabajo para agregarlo."; render(); return; }
        const t = { id: "u" + Date.now(), materia: f.materia, tipo: f.tipo, titulo: f.titulo.trim(), entrega: f.entrega, dificultad: f.dificultad };
        if (f.horas !== "" && Number(f.horas) > 0) t.horas = Number(f.horas);
        d.trabajos.push(t);
        state.form = Object.assign(nuevoForm(), { materia: f.materia });
        recalcular();
        state.formMsg = "Agregamos «" + t.titulo + "». Ya está en tu semana.";
        render(); return;
      }
      case "quitar": d.trabajos = d.trabajos.filter((t) => t.id !== a.id); recalcular(); state.formMsg = ""; render(); return;
      case "sel": state.sel = Number(a.i); state.msg = ""; render(); return;
      case "hecho": marcarHecho(a.id); return;
      case "sem": state.semana = Math.max(0, Math.min(semanasDisp().length - 1, state.semana + Number(a.d))); state.sel = null; render(); return;
      case "sem-hoy": state.semana = 0; state.sel = null; render(); return;
    }
  });
  root.addEventListener("input", (ev) => {
    const el = ev.target.closest("[data-input]");
    if (el) state.form[el.dataset.campo] = el.value;
  });
  root.addEventListener("change", (ev) => {
    const el = ev.target.closest("[data-change]");
    if (!el) return;
    const d = state.datos, a = el.dataset;
    switch (a.change) {
      case "subir": if (el.files && el.files.length) cargarEjemplo(); return;
      case "ini": d.disponibilidad[a.dia].inicio_trabajo = el.value || null; return;
      case "disp": d.disponibilidad[a.dia].disponible = el.checked; if (el.checked && !d.disponibilidad[a.dia].inicio_trabajo) d.disponibilidad[a.dia].inicio_trabajo = "08:00"; render(); return;
      case "huecos": state.usarHuecos = el.checked; return;
      case "maxh": state.maxH = Math.min(10, Math.max(2, Number(el.value) || 6)); render(); return;
      case "lab-dias": d.labs[a.mat].dias_entrega = Math.max(1, Number(el.value) || 7); return;
      case "ec-dias": d.entregas_clase[a.mat].dias_entrega = Math.max(1, Number(el.value) || 7); return;
      case "form": state.form[a.campo] = el.value; render(); return;
      case "check-hecho": marcarHecho(a.id); return;
      case "check-deshacer": d.hechas = d.hechas.filter((x) => x !== a.id); recalcular(); state.msg = "Volvimos a poner «" + state.hechasInfo[a.id] + "» en tu semana."; render(); return;
      case "fsim": if (el.value) { state.fechaSim = el.value; state.semana = 0; state.sel = null; recalcular(); render(); } return;
    }
  });

  function marcarHecho(id) {
    const t = state.plan.tareas.find((x) => x.id === id);
    state.hechasInfo[id] = t ? t.titulo : id;
    state.datos.hechas.push(id);
    state.sel = null;
    recalcular();
    state.msg = "Listo: «" + state.hechasInfo[id] + "» está hecha. Reorganizamos el resto de tu semana.";
    render();
  }
  function cargarEjemplo() {
    state.leyendo = true; render();
    setTimeout(() => { state.leyendo = false; state.cargado = true; recalcular(); render(); }, 900);
  }

  iniciar();
  render();
  window.__semestria = { state, E, ir, recalcular, render };
})();
