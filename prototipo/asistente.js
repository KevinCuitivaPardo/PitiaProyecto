/* SemestrIA - asistente conversacional y sección Progreso.
   Se carga antes de app.js; usa sus globales (S, plan, esc, iso, SVG...) solo cuando las funciones se ejecutan. */

/* ================= datos de ejemplo para capturas (#demo=) ================= */
function sembrarActividad(d) {
  const min = { 1: 120, 2: 150, 3: 90, 4: 180, 6: 60, 8: 140, 9: 120, 10: 100, 11: 150, 12: 90, 14: 60, 15: 120, 16: 130, 17: 100, 19: 140, 20: 110, 22: 90, 23: 120, 24: 100,
                25: 150, 27: 80, 29: 120, 30: 100, 31: 110, 32: 140, 34: 60, 35: 90, 36: 120, 37: 100, 39: 80, 40: 110 };
  const h = fechaDe(S.ahora.slice(0, 10)), mats = d.materias.map(m => m.codigo);
  d.sesiones = Object.entries(min).map(([k, m]) => ({ fecha: iso(sumaDias(h, -k)), min: m, materia: mats[k % mats.length], titulo: "Estudio", tipo: "estudio", origen: "bloque" }));
  d.uso = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 13].map(i => iso(sumaDias(h, -i)));
  const hechas = { "taller:MATE ECDI:2026-10-06": "2026-10-09", "taller:CIENCBAS ASTO:2026-10-06": "2026-10-10", "lab:ISIS PTIA:2026-09-26": "2026-10-01", "lab:ISIS ARSW:2026-09-25": "2026-09-29",
                   "taller:MATE ECDI:2026-09-29": "2026-10-03", "taller:CIENCBAS ASTO:2026-09-22": "2026-09-25", "taller:MATE ECDI:2026-09-22": "2026-09-26", "lab:ISIS FDSI:2026-09-17": "2026-09-22",
                   "taller:CIENCBAS ASTO:2026-09-15": "2026-09-18", "lab:ISIS ARSW:2026-09-18": "2026-09-21" };
  d.hechas = Object.keys(hechas); d.hechas_fecha = hechas;
}

/* ================= bloques de respuesta del asistente ================= */
function bloqueHTML(b) {
  switch (b.t) {
    case "h": return `<h4 class="bh">${esc(b.txt)}</h4>`;
    case "p": return `<p>${esc(b.txt)}</p>`;
    case "ul": return `<ul>${b.items.map(i => `<li>${esc(i)}</li>`).join("")}</ul>`;
    case "ol": return `<ol class="pasos">${b.items.map(i => `<li>${esc(i)}</li>`).join("")}</ol>`;
    case "kv": return `<dl class="kv">${b.items.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>`;
    case "fechas": return `<div class="linea">${b.items.map(([a, f], i) => `<div class="hito ${i === b.items.length - 1 ? "fin" : ""}"><i></i><b>${esc(a)}</b><span>${esc(f)}</span></div>`).join("")}</div>`;
    case "barras": {
      const max = Math.max(b.limite || 0, ...b.items.map(([, v]) => v), 1);
      return `<div class="mb-wrap"><div class="mb-cols">${b.items.map(([l, v]) => `<div class="mb"><div class="mb-v">${v ? num1(v) : ""}</div><div class="mb-col"><i class="${b.limite && v >= b.limite * .9 ? "alto" : ""}" style="height:${v / max * 100}%"></i></div><div class="mb-l">${esc(l)}</div></div>`).join("")}</div>
        ${b.limite ? `<div class="mb-lim" style="bottom:${20 + b.limite / max * 72}px"><span>tope ${b.limite} ${b.unidad || ""}</span></div>` : ""}</div>`;
    }
    case "ciclo": {
      const seg = [];
      for (let r = 0; r < b.rondas; r++) { seg.push(["w", b.trabajo, b.trabajo + " min"]); seg.push(r === b.rondas - 1 ? ["l", b.largo, b.largo + " min"] : ["p", b.pausa, b.pausa]); }
      return `<div class="ciclo">${seg.map(([k, w, t]) => `<div class="cs ${k}" style="flex:${w}" title="${k === "w" ? "Trabajo" : "Pausa"}">${t}</div>`).join("")}</div>
        <div class="ciclo-l"><span><i class="w"></i>trabajo</span><span><i class="p"></i>pausa corta</span><span><i class="l"></i>pausa larga</span></div>`;
    }
    case "plantilla": return `<div class="plantilla"><p>${esc(b.txt)}</p><button class="b g sm" data-copiar="${esc(b.txt)}">Copiar texto</button></div>`;
    case "evidencia": return `<details class="evid"><summary>Evidencia</summary><ul>${b.items.map(i => `<li>${esc(i)}</li>`).join("")}</ul></details>`;
    default: return "";
  }
}

/* ================= chat ================= */
let CHAT_OCUPADO = false, ESTADO_LLM = null;
const HDR = { "Content-Type": "application/json" };
const planoDe = m => m.txt || (m.bloques || []).filter(b => b.t === "p" || b.t === "h").map(b => b.txt).join(" ");

async function estadoLLM() {
  if (ESTADO_LLM) return ESTADO_LLM;
  try { ESTADO_LLM = await (await fetch("/api/asistente_estado")).json(); } catch (e) { ESTADO_LLM = { disponible: false, modelo: null }; }
  return ESTADO_LLM;
}
const llmActivo = () => !!(ESTADO_LLM && ESTADO_LLM.disponible && S.usarLLM);

function msgHTML(m, ultimo) {
  if (m.rol === "user") return `<div class="m user"><div class="burbuja">${esc(m.txt)}</div></div>`;
  if (m.cargando) return `<div class="m bot"><div class="burbuja pensando"><span></span><span></span><span></span></div></div>`;
  const sug = ultimo && m.sugerencias && m.sugerencias.length ? `<div class="sugs">${m.sugerencias.map((s, i) => `<button class="chipb" data-sug="${i}">${esc(s.texto)}</button>`).join("")}</div>` : "";
  const modelo = m.modelo ? `<div class="modelo">Respuesta redactada por el modelo local (${esc(m.modelo)}). Verifica los datos importantes con tu calendario.</div>` : "";
  return `<div class="m bot"><div class="burbuja">${(m.bloques || []).map(bloqueHTML).join("")}${modelo}</div>${sug}</div>`;
}

function pintarChat() {
  const box = $("#msgs");
  if (!box) return;
  const lastBot = S.chat.map((m, i) => m.rol === "bot" ? i : -1).filter(i => i >= 0).pop();
  box.innerHTML = S.chat.map((m, i) => msgHTML(m, i === lastBot)).join("");
  box.querySelectorAll("[data-sug]").forEach(b => b.onclick = () => {
    const s = S.chat[lastBot].sugerencias[+b.dataset.sug];
    chatEnviar(s.accion.tipo === "mensaje" ? { texto: s.accion.texto, etiqueta: s.texto } : { accion: s.accion, etiqueta: s.texto });
  });
  box.querySelectorAll("[data-copiar]").forEach(b => b.onclick = async () => { try { await navigator.clipboard.writeText(b.dataset.copiar); b.textContent = "Copiado"; } catch (e) { b.textContent = "No se pudo copiar"; } });
  box.scrollTop = box.scrollHeight;
}

async function chatEnviar({ texto, accion, etiqueta }) {
  if (CHAT_OCUPADO) return;
  CHAT_OCUPADO = true;
  await estadoLLM();
  const visible = etiqueta || texto || "";
  if (visible) S.chat.push({ rol: "user", txt: visible });
  const m = { rol: "bot", cargando: true };
  S.chat.push(m);
  pintarChat();
  try {
    const cuerpo = { datos: S.datos, ahora: S.ahora, config: S.config };
    const j = await (await fetch("/api/chat", { method: "POST", headers: HDR, body: JSON.stringify({ ...cuerpo, mensaje: texto || "", accion: accion || null }) })).json();
    if (j.error) throw new Error(j.error);
    if (j.perfil !== undefined) S.datos.perfil = j.perfil;
    Object.assign(m, { bloques: j.bloques, sugerencias: j.sugerencias || [], cargando: false });
    if (j.llm_pendiente && llmActivo() && texto) {            // pregunta abierta: la redacta el modelo local
      m.cargando = true; pintarChat();
      const hist = S.chat.slice(-7, -2).map(x => ({ rol: x.rol === "user" ? "user" : "assistant", txt: planoDe(x) }));
      const r = await (await fetch("/api/chat_llm", { method: "POST", headers: HDR, body: JSON.stringify({ ...cuerpo, mensaje: texto, historial: hist }) })).json();
      if (r.texto) { m.bloques = r.texto.split(/\n{2,}/).map(t => ({ t: "p", txt: t.trim() })).filter(b => b.txt); m.modelo = r.modelo; }
      m.cargando = false;
    }
  } catch (e) {
    console.error("asistente:", e);
    Object.assign(m, { bloques: [{ t: "p", txt: "No pude responder en este momento. Intenta de nuevo." + (DEMO ? " [" + e + "]" : "") }], sugerencias: [], cargando: false });
  }
  S.chat = S.chat.slice(-60);
  CHAT_OCUPADO = false;
  guardar(); pintarChat();
}

async function demoChat(conPerfil) {
  const elegir = v => { const s = S.chat[S.chat.length - 1].sugerencias.find(x => x.accion.valor === v); return chatEnviar({ accion: s.accion, etiqueta: s.texto }); };
  await chatEnviar({ accion: { tipo: "bienvenida" } });
  const cj = plan.consejos.find(c => c.categoria === "estrategia") || plan.consejos[0];
  await chatEnviar({ accion: { tipo: "consejo", consejo: cj }, etiqueta: cj.titulo });
  if (!conPerfil) return chatEnviar({ texto: "¿Cuántas horas trabajo esta semana?" });
  await chatEnviar({ accion: { tipo: "entrevista_iniciar" }, etiqueta: "Hazme preguntas para conocerme" });
  for (const v of ["manana", "releer", "celular", "6a7", "empezar"]) await elegir(v);
}

/* ================= vista del asistente ================= */
async function vAsistente() {
  await estadoLLM();
  const cats = ["todos", ...new Set(plan.consejos.map(c => c.categoria))];
  const L = plan.consejos.filter(c => S.catf === "todos" || c.categoria === S.catf);
  const pie = llmActivo()
    ? `Las preguntas abiertas las responde un modelo local (${esc(ESTADO_LLM.modelo)}) en tu computador; lo demás lo calcula SemestrIA con tus datos.`
    : "Las respuestas se calculan con tus datos y una base de métodos de estudio con evidencia. No usa un modelo de lenguaje.";
  $("#v").innerHTML = `<div class="cal-top"><div><h2>Asistente</h2><p class="sub" style="margin:2px 0 0">Pregunta por tu horario, pide métodos de estudio o toca una recomendación.</p></div><span class="sp"></span>
    <button class="b g sm" id="nueva">Nueva conversación</button></div>
    <div class="asis"><aside class="recs"><h3>Recomendaciones para ti</h3>
      <div class="filtros">${cats.map(k => `<button class="pill ${S.catf === k ? "on" : ""}" data-cat="${k}">${k === "todos" ? "Todos" : (CAT[k] || k)}</button>`).join("")}</div>
      <div class="rec-lista">${L.map(c => `<button class="rec ${c.nivel}" data-rec="${plan.consejos.indexOf(c)}"><span class="cat">${c.nivel === "alta" ? "Urgente · " : ""}${CAT[c.categoria] || "Consejo"}</span><b>${esc(c.titulo)}</b></button>`).join("") || '<div class="empty">Sin recomendaciones en esta categoría.</div>'}</div></aside>
    <section class="chat"><div id="msgs" class="msgs"></div>
      <form id="entrada" class="entrada"><input id="txt" placeholder="Escribe tu pregunta: ¿qué tengo hoy?, ¿cómo estudio para el parcial?..." autocomplete="off"><button class="b">Enviar</button></form>
      <div class="pie-chat">${pie}</div></section></div>`;
  document.querySelectorAll("[data-cat]").forEach(b => b.onclick = () => { S.catf = b.dataset.cat; guardar(); vAsistente(); });
  document.querySelectorAll("[data-rec]").forEach(b => b.onclick = () => { const c = plan.consejos[+b.dataset.rec]; chatEnviar({ accion: { tipo: "consejo", consejo: c }, etiqueta: c.titulo }); });
  $("#nueva").onclick = () => { S.chat = []; guardar(); vAsistente(); };
  $("#entrada").onsubmit = e => { e.preventDefault(); const t = $("#txt").value.trim(); if (!t) return; $("#txt").value = ""; chatEnviar({ texto: t }); };
  pintarChat();
  if (S.pendiente) { const p = S.pendiente; S.pendiente = null; chatEnviar({ accion: p.accion, etiqueta: p.etiqueta }); }
  else if (!S.chat.length && !DEMO) chatEnviar({ accion: { tipo: "bienvenida" } });
  $("#txt").focus({ preventScroll: true });
}

/* ================= ajustes del asistente ================= */
function asistenteAjustesHTML() {
  const p = S.datos.perfil || {}, hay = Object.keys(p).length;
  return `<div class="card"><h3>Asistente</h3>
    <p class="sub" style="margin-top:-4px" id="llmestado">Comprobando si hay un modelo local...</p>
    <label><input type="checkbox" id="usarllm" ${S.usarLLM ? "checked" : ""}> Usar el modelo local para las preguntas abiertas</label>
    <p style="margin:14px 0 0"><b>Tu perfil de estudio</b> <small>(sale de las preguntas del asistente)</small></p>
    <p class="mut" style="margin:4px 0 8px">${hay ? Object.entries(p).map(([k, v]) => `${esc(k)}: ${esc(v)}`).join(" · ") : "Aún no respondes las preguntas del asistente."}</p>
    ${hay ? `<button class="b g sm" id="borrarperfil">Borrar mi perfil</button>` : ""}</div>`;
}
async function conectarAjustesAsistente() {
  const e = await estadoLLM(), el = $("#llmestado");
  if (el) el.textContent = e.disponible ? `Modelo local detectado: ${e.modelo}. Funciona en tu computador, sin enviar tus datos a internet.` : "No se detectó un modelo local (Ollama). El asistente responde con su base de métodos y tus datos.";
  if ($("#usarllm")) $("#usarllm").onchange = ev => { S.usarLLM = ev.target.checked; guardar(); };
  if ($("#borrarperfil")) $("#borrarperfil").onclick = () => { S.datos.perfil = {}; replanificar(); };
}

/* ================= progreso ================= */
const num1 = v => (+(+v).toFixed(1)).toLocaleString("es-CO");
const fmtH = h => num1(h) + " h";

function anillo(pct, grande, color = "var(--pri)") {
  const r = 44, c = 2 * Math.PI * r;
  return `<svg viewBox="0 0 110 110" class="anillo" role="img" aria-label="${grande}"><circle cx="55" cy="55" r="${r}" fill="none" stroke="var(--fill)" stroke-width="10"/>
    <circle cx="55" cy="55" r="${r}" fill="none" stroke="${color}" stroke-width="10" stroke-linecap="round" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - Math.min(100, pct) / 100)}" transform="rotate(-90 55 55)"/>
    <text x="55" y="55" text-anchor="middle" dominant-baseline="central" class="anillo-n">${grande}</text></svg>`;
}

function graficaSemanas(sem) {
  const W = 680, H = 250, m = { l: 38, r: 12, t: 18, b: 32 }, iw = W - m.l - m.r, ih = H - m.t - m.b;
  const nec = sem[0] ? sem[0].necesario_h : 0, tope = Math.max(nec, ...sem.map(s => s.cumplido_h), 1) * 1.15;
  const paso = tope > 40 ? 10 : tope > 20 ? 5 : 2, y = v => m.t + ih * (1 - v / tope), col = iw / sem.length, bw = col * .54;
  let g = "";
  for (let v = 0; v <= tope; v += paso) g += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="#e5e5ea" stroke-width="1"/><text x="${m.l - 8}" y="${y(v)}" text-anchor="end" dominant-baseline="central" class="ax">${v}</text>`;
  sem.forEach((s, i) => {
    const x = m.l + i * col + (col - bw) / 2, actual = i === sem.length - 1, d = fechaDe(s.lunes), h = Math.max(0, y(0) - y(s.cumplido_h));
    g += `<rect x="${x}" y="${y(s.cumplido_h)}" width="${bw}" height="${h}" rx="5" fill="${actual ? "var(--pri)" : "#9bc3f0"}"><title>Semana del ${d.getDate()}/${d.getMonth() + 1}: ${fmtH(s.cumplido_h)} cumplidas, ${s.tareas_hechas} tareas hechas</title></rect>`;
    if (s.cumplido_h) g += `<text x="${x + bw / 2}" y="${y(s.cumplido_h) - 6}" text-anchor="middle" class="ax v">${num1(s.cumplido_h)}</text>`;
    g += `<text x="${x + bw / 2}" y="${H - 10}" text-anchor="middle" class="ax">${d.getDate()}/${d.getMonth() + 1}</text>`;
  });
  g += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(nec)}" y2="${y(nec)}" stroke="#d98a1c" stroke-width="2" stroke-dasharray="6 5"/><text x="${W - m.r}" y="${y(nec) - 7}" text-anchor="end" class="ax meta">Necesario según créditos: ${fmtH(nec)}</text>`;
  return `<svg viewBox="0 0 ${W} ${H}" class="graf" role="img" aria-label="Horas cumplidas por semana frente a las necesarias">${g}</svg>`;
}

function mapaActividad(dias) {
  const pad = (fechaDe(dias[0].fecha).getDay() + 6) % 7, nivel = h => h <= 0 ? 0 : h < 1 ? 1 : h < 2 ? 2 : h < 3 ? 3 : 4;
  const celdas = [...Array(pad).fill(null), ...dias];
  return `<div class="mapa"><div class="mapa-d"><span>L</span><span></span><span>X</span><span></span><span>V</span><span></span><span>D</span></div>
    <div class="mapa-g">${celdas.map(d => d ? `<i class="lv${nivel(d.h)}" title="${corto(fechaDe(d.fecha))}: ${fmtH(d.h)}"></i>` : "<i class='vacio'></i>").join("")}</div></div>
    <div class="mapa-l"><span>menos</span><i class="lv0"></i><i class="lv1"></i><i class="lv2"></i><i class="lv3"></i><i class="lv4"></i><span>más</span></div>`;
}

const puntosSemana = dias => dias.slice(-7).map(d => `<i class="pt ${d.h > 0 ? "on" : ""}" title="${corto(fechaDe(d.fecha))}"></i>`).join("");

function vProgreso() {
  const P = plan.progreso, s = P.semana, T = P.tareas;
  const aviso = P.hay_datos ? "" : `<div class="warn">Aún no hay registros. Marca tus bloques como cumplidos desde Resumen o Calendario, o anota las horas reales al terminar un trabajo, y aquí verás tu avance.</div>`;
  const falta = Math.max(0, s.necesario_h - s.cumplido_h);
  $("#v").innerHTML = `<h2>Progreso</h2><p class="sub">Lo que has cumplido frente a lo que tu semestre necesita. Todo sale de lo que registras en la aplicación.</p>${aviso}
  <div class="kpis">
    <div class="kpi"><b>${fmtH(s.cumplido_h)}</b><span>cumplidas esta semana, de ${fmtH(s.planeado_h)} planeadas</span></div>
    <div class="kpi"><b>${T.hechas}</b><span>tareas realizadas (${T.pct} % del total)</span></div>
    <div class="kpi"><b>${P.racha_estudio} ${P.racha_estudio === 1 ? "día" : "días"}</b><span>de racha de estudio (mejor: ${P.mejor_racha_estudio})</span></div>
    <div class="kpi"><b>${P.racha_uso} ${P.racha_uso === 1 ? "día" : "días"}</b><span>de racha de uso (mejor: ${P.mejor_racha_uso})</span></div></div>
  <div class="prog-grid">
    <div class="card pg-ancho"><h3>Horas cumplidas por semana</h3><p class="sub" style="margin:-6px 0 8px">La línea naranja es el estudio independiente que piden tus créditos cada semana (3 h por crédito menos las horas en clase).</p>${graficaSemanas(P.semanas)}</div>
    <div class="card centro"><h3>Esfuerzo frente a lo necesario</h3>${anillo(s.pct_necesario, s.pct_necesario + " %")}
      <p class="mut" style="margin:10px 0 0;text-align:center">${fmtH(s.cumplido_h)} de ${fmtH(s.necesario_h)} necesarias esta semana${falta ? `. Faltan ${fmtH(falta)}.` : ". Meta cumplida."}</p>
      <p class="mut" style="margin:6px 0 0;text-align:center">${s.pct_planeado} % de lo planeado por el plan.</p></div>
    <div class="card"><h3>Actividad de los últimos 35 días</h3>${mapaActividad(P.dias)}
      <p class="mut" style="margin:10px 0 0">Promedio de los últimos 7 días: ${fmtH(P.promedio_7d_h)} por día. Total registrado: ${fmtH(P.total_h)} en ${P.dias_activos} días.</p></div>
    <div class="card"><h3>Rachas</h3><div class="rachas">
      <div><b>${P.racha_estudio}</b><span>racha de estudio</span><div class="pts">${puntosSemana(P.dias)}</div></div>
      <div><b>${P.racha_uso}</b><span>racha de uso</span><div class="pts">${puntosSemana(P.dias.map(d => ({ ...d, h: (S.datos.uso || []).includes(d.fecha) ? 1 : 0 })))}</div></div></div>
      <p class="mut" style="margin:10px 0 0">Un día cuenta para la racha de estudio si registras bloques cumplidos u horas reales, o terminas un trabajo. La de uso cuenta los días que abres la aplicación. Los puntos son los últimos 7 días.</p></div>
    <div class="card"><h3>Esta semana por materia</h3>${P.por_materia.map(m => `<div class="pm"><div class="pm-t"><span><i class="dot" style="background:${colorDe(m.materia)}"></i>${esc(m.materia)}</span><small>${fmtH(m.cumplido_h)} de ${fmtH(m.meta_h)}</small></div>
      <div class="barra"><i style="width:${m.meta_h ? Math.min(100, m.cumplido_h / m.meta_h * 100) : 0}%;background:${colorDe(m.materia)}"></i></div></div>`).join("")}</div>
    <div class="card"><h3>Tareas realizadas por semana</h3>${tareasSemanas(P.semanas)}
      <p class="mut" style="margin:10px 0 0">${T.hechas} hechas y ${T.pendientes} pendientes en este momento.</p></div>
  </div>`;
}

function tareasSemanas(sem) {
  const max = Math.max(...sem.map(s => s.tareas_hechas), 1);
  return `<div class="mb-wrap"><div class="mb-cols">${sem.map((s, i) => { const d = fechaDe(s.lunes);
    return `<div class="mb"><div class="mb-v">${s.tareas_hechas || ""}</div><div class="mb-col"><i class="${i === sem.length - 1 ? "act" : ""}" style="height:${s.tareas_hechas / max * 100}%"></i></div><div class="mb-l">${d.getDate()}/${d.getMonth() + 1}</div></div>`; }).join("")}</div></div>`;
}
