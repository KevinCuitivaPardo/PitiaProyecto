/* SemestrIA - interfaz. El cálculo del plan y los consejos viven en el servidor (motor/). */
const DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const WIZ = [["w_inicio", "Inicio", "Elige tu horario"], ["w_horario", "Horario y créditos", "Revisa y ajusta"],
             ["w_trabajos", "Trabajos", "Parciales y entregas"], ["w_revision", "Listo para empezar", "Revisión final"]];
const SVG = (d, n = 17) => `<svg width="${n}" height="${n}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const CHK = SVG('<path d="M5 12.5l4.5 4.5L19 7.5"/>', 13);
const NAV = [["resumen", SVG('<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z"/>'), "Resumen"],
             ["calendario", SVG('<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>'), "Calendario"],
             ["trabajos", SVG('<rect x="4" y="4" width="7" height="16" rx="1.5"/><rect x="13" y="4" width="7" height="10" rx="1.5"/>'), "Trabajos"],
             ["progreso", SVG('<path d="M5 20V10M12 20V4M19 20v-7"/>'), "Progreso"],
             ["asistente", SVG('<path d="M5 5h14v10H9l-4 4z"/>'), "Asistente"],
             ["ajustes", SVG('<path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/>'), "Ajustes"]];
const PAL = ["#0a6cdb", "#c2477a", "#2f9e6e", "#d98a1c", "#7e57c2", "#1a9aa8", "#d6453d", "#7f8c3a"];
const CAT = { foco: "Hoy", riesgo: "Riesgo", estrategia: "Estrategia", carga: "Carga",
              bienestar: "Bienestar", estudio: "Estudio", progreso: "Progreso" };
const H0 = 7, H1 = 21, HH = 40;                       // rango y alto por hora de la grilla semanal
const KEY = "semestria.v3";

const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const iso = d => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
const fechaDe = s => { const [a, b, c] = s.split("-").map(Number); return new Date(a, b - 1, c); };
const sumaDias = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const lunesDe = d => sumaDias(d, -((d.getDay() + 6) % 7));
const min = h => { const [a, b] = h.split(":").map(Number); return a * 60 + b; };
const horasTxt = m => +(m / 60).toFixed(1) + " h";
const largo = d => d.toLocaleDateString("es-CO", { weekday: "long", day: "numeric", month: "long" });
const corto = d => d.toLocaleDateString("es-CO", { day: "numeric", month: "short" });
const ahoraStr = () => { const n = new Date(); return iso(n) + "T" + String(n.getHours()).padStart(2, "0") + ":" + String(n.getMinutes()).padStart(2, "0"); };
const tint = (hex, k = .86) => { const n = parseInt(hex.slice(1), 16); const m = c => Math.round(c + (255 - c) * k);
  return `rgb(${m(n >> 16)},${m(n >> 8 & 255)},${m(n & 255)})`; };

let S = { datos: null, listo: false, vista: "w_inicio", ahora: null, config: { max_horas_dia: 6, usar_huecos: true },
          offset: 0, cal: "semana", mes: 0, filtro: { materia: "", auto: true }, catf: "todos", visto: {}, chat: [], usarLLM: true };
let plan = null;

let DEMO = false;   // con #demo=... no se toca el almacenamiento del usuario (sirve para capturas)
const guardar = () => { if (DEMO) return; try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* sin almacenamiento */ } };
const hoy = () => fechaDe(S.ahora.slice(0, 10));
const colorDe = m => { const i = S.datos.materias.findIndex(x => x.codigo === m); return PAL[(i < 0 ? 0 : i) % PAL.length]; };
const setAhora = v => { S.ahora = v; guardar(); };

/* ================= datos y plan ================= */
async function modoDemo() {
  const m = location.hash.match(/^#demo=(\w+)/);
  if (!m) return false;
  const v = m[1], listo = ["resumen", "calendario", "mes", "trabajos", "progreso", "asistente", "asistente_perfil", "recomendaciones", "ajustes"].includes(v);
  DEMO = true;
  S.ahora = v === "progreso" ? "2026-10-15T18:00" : "2026-10-12T09:00";   // el jueves ya hay actividad en la semana
  S.config = { max_horas_dia: 6, usar_huecos: true }; S.offset = 0; S.mes = 0; S.visto = {}; S.chat = [];
  S.datos = v === "inicio" ? null : await (await fetch("/api/ejemplo")).json();
  if (S.datos) {
    S.datos.en_curso = ["m1"];
    S.datos.historial = [["Taller", 2, 2.5], ["Taller", 1.5, 2], ["Laboratorio", 4.5, 5], ["Parcial", 7.5, 9]].map(([tipo, b, r]) => ({ tipo, base_h: b, real_h: r }));
    sembrarActividad(S.datos);
  }
  S.listo = listo; S.cal = v === "mes" ? "mes" : "semana";
  S.vista = { inicio: "w_inicio", horario: "w_horario", trabajos_setup: "w_trabajos", revision: "w_revision", mes: "calendario", recomendaciones: "asistente", asistente_perfil: "asistente" }[v] || v;
  if (S.datos) await replanificar(); else render();
  if (v === "asistente" || v === "recomendaciones") await demoChat(false);
  if (v === "asistente_perfil") await demoChat(true);
  return true;
}

async function init() {
  if (await modoDemo()) return;
  try { const g = JSON.parse(localStorage.getItem(KEY)); if (g && g.datos) S = Object.assign(S, g); } catch (e) { /* estado nuevo */ }
  if (!S.ahora) S.ahora = ahoraStr();
  if (S.datos) await replanificar(); else render();
}
async function cargarDatos(datos) {
  S.datos = datos; S.listo = false; S.visto = {}; S.offset = 0; S.vista = "w_horario";
  await replanificar();
}
async function usarEjemplo() {
  S.ahora = "2026-10-12T09:00";   // el horario de prueba corresponde a ese semestre
  await cargarDatos(await (await fetch("/api/ejemplo")).json());
}
async function subirArchivo(f) {
  const box = $("#errs"); box.innerHTML = "";
  try {
    const r = await fetch("/api/importar", { method: "POST", headers: { "Content-Type": "application/json" }, body: await f.text() });
    const j = await r.json();
    if (!r.ok) { box.innerHTML = `<div class="err"><b>No pude leer ese horario:</b><ul>${(j.errores || [j.error || "Archivo no válido"]).map(e => `<li>${esc(e)}</li>`).join("")}</ul></div>`; return; }
    S.ahora = ahoraStr();
    await cargarDatos(j.datos);
  } catch (e) { box.innerHTML = `<div class="err">No pude leer el archivo.</div>`; }
}
function registrarUso() {
  if (!S.datos || DEMO) return;
  const hoyIso = S.ahora.slice(0, 10);
  S.datos.uso = S.datos.uso || [];
  if (!S.datos.uso.includes(hoyIso)) S.datos.uso.push(hoyIso);
}
async function replanificar() {
  registrarUso();
  const r = await fetch("/api/plan", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ datos: S.datos, ahora: S.ahora, config: S.config }) });
  plan = await r.json();
  if (plan.error) { $("#v").innerHTML = `<div class="warn">${esc(plan.error)}</div>`; return; }
  guardar(); render();
}
function setEstado(id, estado) {
  if (estado === "hecho" && estadoDe(id) !== "hecho" && plan.tareas.some(t => t.id === id)) return pedirHoras(id);
  aplicarEstado(id, estado);
}
function pedirHoras(id) {
  const t = plan.tareas.find(x => x.id === id), dlg = $("#dlg");
  if (t.fija) return aplicarEstado(id, "hecho");   // el estudiante fijó las horas: no hay nada que calibrar
  const base = t.base_min / 60;
  dlg.innerHTML = `<form method="dialog"><h3>${esc(t.titulo)}</h3>
    <p class="sub" style="margin:0">Estimamos ${+base.toFixed(1)} h. Si anotas cuánto te tomó de verdad, ajustamos tus próximos trabajos a tu ritmo.</p>
    <div class="fld">Horas reales (opcional)<input type="number" id="hr" min="0.25" step="0.25" autofocus></div>
    <div class="row" style="justify-content:flex-end"><button type="button" class="b g" id="om">Omitir</button><button class="b">Guardar</button></div></form>`;
  dlg.showModal();
  $("#om").onclick = () => { dlg.close(); aplicarEstado(id, "hecho"); };
  dlg.querySelector("form").onsubmit = () => {
    const v = parseFloat($("#hr").value);
    if (v > 0) {
      (S.datos.historial = S.datos.historial || []).push({ id, tipo: t.tipo, materia: t.materia, base_h: base, real_h: v });
      // las horas reales alimentan el progreso; se descuenta lo ya marcado en bloques para no contarlo dos veces
      const ya = (S.datos.sesiones || []).filter(s => s.tarea_id === id).reduce((a, s) => a + s.min, 0);
      if (v * 60 > ya) agregarSesion({ fecha: S.ahora.slice(0, 10), min: Math.round(v * 60 - ya), materia: t.materia, titulo: t.titulo, tipo: t.tipo, tarea_id: id, origen: "horas_reales" });
    }
    aplicarEstado(id, "hecho");
  };
}
function aplicarEstado(id, estado) {
  const d = S.datos;
  d.hechas = d.hechas.filter(x => x !== id); d.en_curso = (d.en_curso || []).filter(x => x !== id);
  d.hechas_fecha = d.hechas_fecha || {};
  if (estado === "hecho") { d.hechas.push(id); d.hechas_fecha[id] = S.ahora.slice(0, 10); } else { delete d.hechas_fecha[id]; if (estado === "curso") d.en_curso.push(id); }
  replanificar();
}
/* sesiones: bloques que el estudiante marca como cumplidos (alimentan Progreso) */
const agregarSesion = s => (S.datos.sesiones = S.datos.sesiones || []).push(s);
const mismoBloque = (s, b) => s.fecha === b.fecha && s.inicio === b.inicio && s.materia === b.materia && s.titulo === b.titulo;
const bloqueCumplido = b => (S.datos.sesiones || []).some(s => mismoBloque(s, b));
function alternarCumplido(j) {
  const b = plan.bloques[j];
  if (bloqueCumplido(b)) S.datos.sesiones = S.datos.sesiones.filter(s => !mismoBloque(s, b));
  else agregarSesion({ fecha: b.fecha, inicio: b.inicio, fin: b.fin, min: min(b.fin) - min(b.inicio), materia: b.materia, titulo: b.titulo, tipo: b.tipo, tarea_id: b.tarea_id, origen: "bloque" });
  replanificar();
}
const estadoDe = id => S.datos.hechas.includes(id) ? "hecho" : (S.datos.en_curso || []).includes(id) ? "curso" : "pend";
const alternarHecho = id => setEstado(id, estadoDe(id) === "hecho" ? "pend" : "hecho");

/* ================= navegación ================= */
function ir(v) {
  if (!S.datos && v !== "w_inicio") return;
  S.visto[S.vista] = true; S.vista = v; guardar(); render(); scrollTo(0, 0);
}
function empezar() { S.listo = true; S.vista = "resumen"; S.offset = 0; guardar(); render(); scrollTo(0, 0); }
function reiniciar() {
  if (!confirm("¿Reiniciar el semestre? Se borra el horario y tus trabajos guardados en este navegador.")) return;
  S.datos = null; S.listo = false; S.vista = "w_inicio"; plan = null; S.visto = {}; guardar(); render();
}

function renderSide() {
  const alta = plan ? plan.consejos.filter(c => c.nivel === "alta").length : 0;
  let h = `<div class="brand">Semestr<span>IA</span></div><div class="tag">Organiza tu semestre</div>`;
  if (S.listo && S.datos) {
    h += NAV.map(([k, ic, t]) => `<button class="nv ${S.vista === k ? "on" : ""}" data-ir="${k}"><span>${ic}</span>${t}${k === "asistente" && alta ? `<span class="badge">${alta}</span>` : ""}</button>`).join("");
  }
  h += `<div class="push"></div><label>Fecha simulada</label><input type="datetime-local" id="ahora" value="${S.ahora || ""}">
        <button class="mini" id="usarhoy">Usar fecha de hoy</button>`;
  if (S.datos) h += `<button class="mini" id="exportar">Descargar mis datos</button>`;
  $("#side").innerHTML = h;
  document.querySelectorAll("[data-ir]").forEach(b => b.onclick = () => ir(b.dataset.ir));
  $("#ahora").onchange = e => { S.ahora = e.target.value; S.offset = 0; if (S.datos) replanificar(); else guardar(); };
  $("#usarhoy").onclick = () => { S.ahora = ahoraStr(); S.offset = 0; if (S.datos) replanificar(); else { guardar(); renderSide(); } };
  if ($("#exportar")) $("#exportar").onclick = () => { const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(S.datos, null, 2)], { type: "application/json" })); a.download = "mi_horario.json"; a.click(); };
}

function pasosHTML() {
  const i = WIZ.findIndex(p => p[0] === S.vista);
  return `<div class="steps">${WIZ.map((p, k) => { const ok = S.visto[p[0]] && k !== i;
    return `<button data-ir="${p[0]}" class="${k === i ? "on" : ""} ${ok ? "ok" : ""}" ${k > 0 && !S.datos ? "disabled" : ""}><b>${ok ? CHK : k + 1}</b>${p[1]}<small>${p[2]}</small></button>`; }).join("")}</div>`;
}
function nav2HTML() {
  const i = WIZ.findIndex(p => p[0] === S.vista);
  if (i < 1 || i > 2) return "";
  return `<div class="nav2">${i > 1 ? `<button class="b g" data-ir="${WIZ[i - 1][0]}">Anterior: ${WIZ[i - 1][1]}</button>` : "<span></span>"}
          <button class="b" data-ir="${WIZ[i + 1][0]}">Siguiente: ${WIZ[i + 1][1]}</button></div>`;
}

function render() {
  $("#det").style.display = "none";
  if (S.datos && !plan) { replanificar(); return; }
  if (!S.datos) S.vista = "w_inicio";
  if (S.vista === "consejos") S.vista = "asistente";       // la sección Recomendaciones ahora es el asistente
  if (S.listo && S.vista.startsWith("w_")) S.vista = "resumen";
  if (!S.listo && !S.vista.startsWith("w_")) S.vista = "w_horario";
  const V = { w_inicio: vInicio, w_horario: () => vHorario(true), w_trabajos: vTrabajos, w_revision: vRevision,
              resumen: vResumen, calendario: vCalendario, trabajos: vTrabajos, progreso: () => vProgreso(), asistente: () => vAsistente(),
              ajustes: () => vHorario(false) };
  renderSide();
  V[S.vista]();
  if (S.vista.startsWith("w_")) {
    $("#v").insertAdjacentHTML("afterbegin", pasosHTML());
    $("#v").insertAdjacentHTML("beforeend", nav2HTML());
  }
  document.querySelectorAll("#v [data-ir]").forEach(b => b.onclick = () => ir(b.dataset.ir));
}

/* ================= 1. inicio ================= */
function vInicio() {
  $("#v").innerHTML = `<div class="hero"><h2>Organiza tu semestre sin que se te junte todo</h2>
  <p class="sub">Parte de tu horario de clases, los créditos de cada materia y tus entregas. SemestrIA arma un plan semanal que explica cada decisión y te da consejos concretos para llegar a tiempo.</p></div>
  <div class="opts">
    <div class="opt" id="drop"><h3>Sube tu horario</h3><p class="sub" style="margin:0 0 12px">Archivo JSON con tus materias y bloques de clase.</p>
      <input type="file" id="file" accept=".json,application/json" hidden><button class="b" id="elegir">Elegir archivo</button>
      <p style="margin:10px 0 0"><small>o arrástralo aquí · <a href="/api/ejemplo" download="mi_horario.json">descargar plantilla</a></small></p></div>
    <div class="opt solid"><h3>Usar horario de prueba</h3><p class="sub" style="margin:0 0 12px">Semestre de ejemplo: 6 materias, laboratorios y 3 entregas.</p><button class="b" id="ej">Probar con el ejemplo</button></div>
    ${S.datos ? `<div class="opt solid"><h3>${S.listo ? "Ir a mi semestre" : "Continuar"}</h3><p class="sub" style="margin:0 0 12px">Ya tienes un horario cargado (${S.datos.materias.length} materias).</p><button class="b g" id="cont">${S.listo ? "Abrir resumen" : "Seguir donde iba"}</button></div>` : ""}
  </div><div id="errs"></div>`;
  $("#ej").onclick = usarEjemplo;
  $("#elegir").onclick = () => $("#file").click();
  $("#file").onchange = e => e.target.files[0] && subirArchivo(e.target.files[0]);
  const dr = $("#drop");
  dr.ondragover = e => { e.preventDefault(); dr.classList.add("drag"); }; dr.ondragleave = () => dr.classList.remove("drag");
  dr.ondrop = e => { e.preventDefault(); dr.classList.remove("drag"); e.dataTransfer.files[0] && subirArchivo(e.dataTransfer.files[0]); };
  if ($("#cont")) $("#cont").onclick = () => S.listo ? ir("resumen") : ir("w_horario");
}

/* ================= 2. horario, créditos, disponibilidad ================= */
function vHorario(wiz) {
  const por = d => S.datos.bloques.map((b, i) => [b, i]).filter(([b]) => b.dia === d).sort((a, b) => min(a[0].inicio) - min(b[0].inicio));
  const M = plan.materias, tot = k => M.reduce((a, m) => a + m[k], 0), disp = S.datos.disponibilidad;
  $("#v").innerHTML = `<h2>${wiz ? "Horario y créditos" : "Ajustes del semestre"}</h2>
  <p class="sub">Revisa tus clases, ajusta créditos y dinos cuándo puedes trabajar. El plan se recalcula con cada cambio.</p>
  <div class="card"><h3>Tus clases</h3><div class="mes" style="grid-template-columns:repeat(7,1fr)">${DIAS.map((n, d) => `<div class="c" style="cursor:default;min-height:90px"><b>${n.slice(0, 3)}</b>${por(d).map(([b, i]) =>
    `<div class="t" style="background:${tint(colorDe(b.materia))};color:#1f2a3a;border-left:3px solid ${colorDe(b.materia)};white-space:normal;padding:2px 5px;margin-top:4px"><b>${esc(b.materia)} ${b.tipo}</b><br>${b.inicio}–${b.fin} <a href="#" data-rm="${i}" title="Quitar clase">×</a></div>`).join("")}</div>`).join("")}</div>
  <form id="nclase" class="row" style="margin-top:14px"><b style="align-self:center">Agregar clase</b>
    <label>Materia<input name="materia" list="mats" required placeholder="Código" style="width:130px"></label><datalist id="mats">${M.map(m => `<option value="${esc(m.codigo)}">`).join("")}</datalist>
    <label>Tipo<select name="tipo"><option>LEC</option><option>LAB</option></select></label>
    <label>Día<select name="dia">${DIAS.map((n, i) => `<option value="${i}">${n}</option>`).join("")}</select></label>
    <label>Inicio<input type="time" name="inicio" required></label><label>Fin<input type="time" name="fin" required></label>
    <button class="b g">Agregar</button></form><div id="errc"></div></div>
  <div class="card"><h3>Créditos y horas de estudio</h3><p class="sub" style="margin-top:-4px">Cada crédito equivale a 48 h en 16 semanas (3 h/semana). Lo que no pasas en clase, lo estudias por tu cuenta.</p>
  <table><tr><th>Materia</th><th>Créditos</th><th class="n">Total/sem</th><th class="n">En clase</th><th class="n">Independiente</th></tr>
  ${M.map(m => `<tr><td><span class="dot" style="background:${colorDe(m.codigo)}"></span><b>${esc(m.codigo)}</b></td><td><button class="b g sm" data-c="${esc(m.codigo)}" data-d="-1">−</button> &nbsp;${m.creditos}&nbsp; <button class="b g sm" data-c="${esc(m.codigo)}" data-d="1">+</button></td>
  <td class="n">${m.total_h.toFixed(1)} h</td><td class="n">${m.clase_h.toFixed(1)} h</td><td class="n"><b>${m.indep_h.toFixed(1)} h</b></td></tr>`).join("")}
  <tr><td><b>Total</b></td><td><b>${M.reduce((a, m) => a + m.creditos, 0)}</b></td><td class="n">${tot("total_h").toFixed(1)} h</td><td class="n">${tot("clase_h").toFixed(1)} h</td><td class="n"><b>${tot("indep_h").toFixed(1)} h</b></td></tr></table></div>
  <div class="card"><h3>Cuándo puedes trabajar</h3>
  <table>${DIAS.map((n, d) => { const x = disp[d] || {}; return `<tr><td style="width:120px"><b>${n}</b></td><td><label><input type="checkbox" data-disp="${d}" ${x.disponible ? "checked" : ""}> Disponible</label></td>
  <td>Empiezo a las <input type="time" data-ini="${d}" value="${x.inicio_trabajo || ""}" ${x.disponible ? "" : "disabled"}></td></tr>`; }).join("")}</table>
  <p><label><input type="checkbox" id="huecos" ${S.config.usar_huecos ? "checked" : ""}> Aprovechar huecos entre clases (1 h o más)</label></p>
  <p><label>Máximo de horas de trabajo por día <input type="number" id="maxh" min="1" max="12" step="0.5" value="${S.config.max_horas_dia}" style="width:70px"></label></p></div>
  ${wiz ? "" : calibracionHTML() + asistenteAjustesHTML()}
  ${wiz ? "" : `<div class="card"><h3>Semestre</h3><div class="row"><button class="b g" data-ir="w_inicio" id="otro">Cargar otro horario</button><button class="b g" id="reini" style="color:var(--bad)">Reiniciar semestre</button></div></div>`}`;
  document.querySelectorAll("[data-rm]").forEach(a => a.onclick = e => { e.preventDefault(); S.datos.bloques.splice(+a.dataset.rm, 1); replanificar(); });
  $("#nclase").onsubmit = e => { e.preventDefault(); const f = Object.fromEntries(new FormData(e.target));
    if (min(f.fin) <= min(f.inicio)) { $("#errc").innerHTML = '<div class="err">La hora de fin debe ser mayor que la de inicio.</div>'; return; }
    if (!S.datos.materias.some(m => m.codigo === f.materia)) S.datos.materias.push({ codigo: f.materia, creditos: 3 });
    S.datos.bloques.push({ materia: f.materia, tipo: f.tipo, dia: +f.dia, inicio: f.inicio, fin: f.fin, salon: "" }); replanificar(); };
  document.querySelectorAll("[data-c]").forEach(b => b.onclick = () => { const m = S.datos.materias.find(x => x.codigo === b.dataset.c); m.creditos = Math.max(1, Math.min(6, m.creditos + +b.dataset.d)); replanificar(); });
  document.querySelectorAll("[data-disp]").forEach(c => c.onchange = () => { const x = disp[c.dataset.disp]; x.disponible = c.checked; x.inicio_trabajo = c.checked ? (x.inicio_trabajo || "14:00") : null; replanificar(); });
  document.querySelectorAll("[data-ini]").forEach(c => c.onchange = () => { disp[c.dataset.ini].inicio_trabajo = c.value || null; replanificar(); });
  $("#huecos").onchange = e => { S.config.usar_huecos = e.target.checked; replanificar(); };
  $("#maxh").onchange = e => { S.config.max_horas_dia = Math.max(1, +e.target.value || 6); replanificar(); };
  if ($("#reini")) $("#reini").onclick = reiniciar;
  if (!wiz) conectarAjustesAsistente();
  if ($("#borrarhist")) $("#borrarhist").onclick = () => { if (confirm("¿Borrar el historial de horas reales?")) { S.datos.historial = []; replanificar(); } };
}

function calibracionHTML() {
  const n = (S.datos.historial || []).length;
  return `<div class="card"><h3>Calibración de estimaciones</h3>
    <p class="sub" style="margin-top:-4px">Aprende de las horas reales que registras al terminar un trabajo. Un factor de 1,00 significa que se usa la estimación base. ${n ? `Tienes ${n} registro(s).` : "Aún no hay registros."}</p>
    <table><tr><th>Tipo de trabajo</th><th class="n">Registros</th><th class="n">Factor aplicado</th></tr>
    ${plan.calibracion.map(c => `<tr><td>${c.tipo}</td><td class="n">${c.registros}</td><td class="n"><b>${c.factor.toFixed(2)}</b></td></tr>`).join("")}</table>
    ${n ? `<p style="margin:12px 0 0"><button class="b g sm" id="borrarhist">Borrar historial</button></p>` : ""}</div>`;
}

/* ================= 3. trabajos (tablero) ================= */
function tituloAuto(id) {
  const [tipo, mat, f] = id.split(":"); const d = fechaDe(f);
  return (tipo === "lab" ? "Informe de laboratorio " : "Taller ") + mat + ` (${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")})`;
}
function listaTrabajos() {
  const h = hoy(), out = [];
  const prog = id => { const bl = plan.bloques.filter(b => b.tarea_id === id); return { h: bl.reduce((a, b) => a + min(b.fin) - min(b.inicio), 0) / 60, sig: bl.find(b => b.fecha >= iso(h)) }; };
  const pend = new Map(plan.tareas.map(t => [t.id, t]));
  S.datos.trabajos.forEach(t => { const p = pend.get(t.id);
    out.push({ id: t.id, titulo: t.titulo, materia: t.materia, tipo: t.tipo, due: t.entrega, dif: t.dificultad, horas: p ? p.min / 60 : t.horas || null, auto: false, estado: estadoDe(t.id), ...prog(t.id), raw: t }); });
  plan.tareas.filter(t => t.auto).forEach(t => out.push({ id: t.id, titulo: t.titulo, materia: t.materia, tipo: t.tipo, due: t.due, dif: t.dificultad, horas: t.min / 60, auto: true, estado: estadoDe(t.id), ...prog(t.id) }));
  S.datos.hechas.filter(id => /^(lab|taller):/.test(id)).forEach(id => { const [, mat, f] = id.split(":");
    out.push({ id, titulo: tituloAuto(id), materia: mat, tipo: id.startsWith("lab") ? "Laboratorio" : "Taller", due: iso(sumaDias(fechaDe(f), 7)), dif: "", horas: null, auto: true, estado: "hecho", h: 0, sig: null }); });
  return out;
}
function dueTxt(due) {
  const n = Math.round((fechaDe(due) - hoy()) / 864e5), f = corto(fechaDe(due));
  if (n < 0) return [`Vencido hace ${-n} d`, "urg"]; if (n === 0) return ["Vence hoy", "urg"]; if (n === 1) return ["Mañana", "urg"];
  return [`En ${n} días · ${f}`, n <= 3 ? "pronto" : ""];
}
function tarjeta(t) {
  const [dt, dc] = t.estado === "hecho" ? [corto(fechaDe(t.due)), ""] : dueTxt(t.due), c = colorDe(t.materia);
  const pct = t.horas ? Math.min(100, Math.round(100 * t.h / t.horas)) : 0;
  const sig = t.sig ? `Próximo: ${DIAS[(fechaDe(t.sig.fecha).getDay() + 6) % 7].slice(0, 3)} ${fechaDe(t.sig.fecha).getDate()} · ${t.sig.inicio}` : "";
  const acts = t.estado === "pend" ? `<button class="b sm" data-st="${esc(t.id)}" data-to="curso">Empezar</button><button class="b g sm" data-st="${esc(t.id)}" data-to="hecho">Hecho</button>`
    : t.estado === "curso" ? `<button class="b sm" data-st="${esc(t.id)}" data-to="hecho">Hecho</button><button class="b g sm" data-st="${esc(t.id)}" data-to="pend">Pausar</button>`
    : `<button class="b g sm" data-st="${esc(t.id)}" data-to="pend">Reabrir</button>`;
  return `<div class="tk ${t.estado === "hecho" ? "hecha" : ""}" style="--c:${c}" draggable="true" data-id="${esc(t.id)}">
    <h4>${esc(t.titulo)}</h4>
    <div class="meta"><span class="mt"><i class="dot" style="background:${c}"></i>${esc(t.materia)}</span><span>${t.tipo}</span>${t.dif ? `<span>· ${t.dif}</span>` : ""}${t.auto ? `<span title="Se genera desde tu horario">· auto</span>` : ""}</div>
    <div class="meta" style="margin-top:6px"><span class="due ${dc}">${dt}</span>${t.horas ? `<span>· ${+t.horas.toFixed(1)} h</span>` : ""}</div>
    ${t.estado !== "hecho" && t.horas ? `<div class="prog"><div class="bar"><i style="width:${pct}%"></i></div></div><div class="meta">${+t.h.toFixed(1)} de ${+t.horas.toFixed(1)} h programadas</div>` : ""}
    ${sig && t.estado !== "hecho" ? `<div class="nx">${sig}</div>` : ""}
    <div class="acts">${acts}${t.auto ? "" : `<button class="b g sm" data-ed="${esc(t.id)}">Editar</button><button class="b g sm" data-del="${esc(t.id)}" style="color:var(--bad)">Quitar</button>`}</div></div>`;
}
function vTrabajos() {
  const f = S.filtro;
  let L = listaTrabajos().filter(t => (!f.materia || t.materia === f.materia) && (f.auto || !t.auto));
  L.sort((a, b) => a.due.localeCompare(b.due));
  const col = e => L.filter(t => t.estado === e), cols = [["pend", "Por hacer"], ["curso", "En curso"], ["hecho", "Hecho"]];
  const horasPend = L.filter(t => t.estado !== "hecho").reduce((a, t) => a + (t.horas || 0), 0);
  $("#v").innerHTML = `<div class="cal-top"><div><h2>Trabajos</h2><p class="sub" style="margin:2px 0 0">Arrastra las tarjetas entre columnas o usa los botones. Los informes y talleres de clase aparecen solos desde tu horario.</p></div><span class="sp"></span>
    <button class="b" id="nuevo">+ Nuevo trabajo</button></div>
  <div class="cal-top"><select id="fmat"><option value="">Todas las materias</option>${S.datos.materias.map(m => `<option ${f.materia === m.codigo ? "selected" : ""}>${esc(m.codigo)}</option>`).join("")}</select>
    <label style="flex-direction:row;align-items:center;gap:6px;font-size:14px;color:var(--ink)"><input type="checkbox" id="fauto" ${f.auto ? "checked" : ""}> Mostrar automáticos</label>
    <span class="sp"></span><span class="chip">${L.filter(t => t.estado !== "hecho").length} pendientes · ${+horasPend.toFixed(1)} h</span></div>
  <div class="board">${cols.map(([e, t]) => `<div class="colm" data-col="${e}"><h3>${t} <span class="chip">${col(e).length}</span></h3>
    ${col(e).slice(0, e === "hecho" ? 12 : 99).map(tarjeta).join("") || `<div class="empty"><small>${e === "pend" ? "Nada pendiente" : "Suelta una tarjeta aquí"}</small></div>`}</div>`).join("")}</div>`;
  $("#fmat").onchange = e => { f.materia = e.target.value; guardar(); render(); };
  $("#fauto").onchange = e => { f.auto = e.target.checked; guardar(); render(); };
  $("#nuevo").onclick = () => formTrabajo();
  document.querySelectorAll("[data-st]").forEach(b => b.onclick = () => setEstado(b.dataset.st, b.dataset.to));
  document.querySelectorAll("[data-ed]").forEach(b => b.onclick = () => formTrabajo(S.datos.trabajos.find(t => t.id === b.dataset.ed)));
  document.querySelectorAll("[data-del]").forEach(b => b.onclick = () => { if (confirm("¿Quitar este trabajo?")) { S.datos.trabajos = S.datos.trabajos.filter(t => t.id !== b.dataset.del); setEstado(b.dataset.del, "pend"); } });
  document.querySelectorAll(".tk").forEach(k => k.ondragstart = e => e.dataTransfer.setData("text/plain", k.dataset.id));
  document.querySelectorAll(".colm").forEach(c => { c.ondragover = e => e.preventDefault(); c.ondrop = e => { e.preventDefault(); const id = e.dataTransfer.getData("text/plain"); if (id) setEstado(id, c.dataset.col); }; });
}
function formTrabajo(t) {
  const dlg = $("#dlg"), n = !t; t = t || { materia: S.datos.materias[0].codigo, tipo: "Parcial", titulo: "", entrega: iso(sumaDias(hoy(), 7)), dificultad: "Medio" };
  dlg.innerHTML = `<form method="dialog" id="ft"><h3>${n ? "Nuevo trabajo" : "Editar trabajo"}</h3>
    <div class="fld">Título<input name="titulo" required value="${esc(t.titulo)}" placeholder="Ej: Parcial 3 de cálculo"></div>
    <div class="row2"><div class="fld">Materia<select name="materia">${S.datos.materias.map(m => `<option ${m.codigo === t.materia ? "selected" : ""}>${esc(m.codigo)}</option>`).join("")}</select></div>
      <div class="fld">Tipo<select name="tipo">${["Parcial", "Proyecto", "Taller", "Laboratorio"].map(x => `<option ${x === t.tipo ? "selected" : ""}>${x}</option>`).join("")}</select></div></div>
    <div class="row2"><div class="fld">Fecha de entrega<input type="date" name="entrega" required value="${t.entrega}"></div>
      <div class="fld">Dificultad<select name="dificultad">${["Fácil", "Medio", "Difícil"].map(x => `<option ${x === t.dificultad ? "selected" : ""}>${x}</option>`).join("")}</select></div></div>
    <div class="fld">Horas estimadas (opcional)<input type="number" name="horas" min="0.5" step="0.5" value="${t.horas || ""}" placeholder="Se calcula por tipo y dificultad"></div>
    <div class="row" style="justify-content:flex-end"><button type="button" class="b g" id="cx">Cancelar</button><button class="b">${n ? "Agregar" : "Guardar"}</button></div></form>`;
  dlg.showModal();
  $("#cx").onclick = () => dlg.close();
  $("#ft").onsubmit = e => { const f = Object.fromEntries(new FormData(e.target)), o = { materia: f.materia, tipo: f.tipo, titulo: f.titulo.trim(), entrega: f.entrega, dificultad: f.dificultad };
    if (f.horas) o.horas = +f.horas;
    if (n) S.datos.trabajos.push({ id: "u" + Date.now(), ...o }); else { delete t.horas; Object.assign(t, o); }
    replanificar(); };
}

/* ================= 4. revisión final (asistente) ================= */
function vRevision() {
  const M = plan.materias, I = plan.indicadores, disp = Object.values(S.datos.disponibilidad).filter(x => x.disponible).length;
  const alta = plan.consejos.filter(c => c.nivel === "alta"), indep = M.reduce((a, m) => a + m.indep_h, 0);
  const ok = S.datos.bloques.length > 0;
  const fila = (b, t, d) => `<div class="check"><i class="${b ? "" : "pend"}">${b ? CHK : ""}</i><div><b>${t}</b><br><span class="mut">${d}</span></div></div>`;
  $("#v").innerHTML = `<h2>Todo listo para empezar</h2><p class="sub">Revisa el resumen. Al empezar, tu horario queda fijado para el semestre y pasas a tu panel con calendario, trabajos y consejos. Podrás ajustarlo cuando quieras en Ajustes.</p>
  <div class="two"><div class="card">
    ${fila(ok, "Horario", `${S.datos.bloques.length} clases de ${M.length} materias · semestre desde ${fechaDe(S.datos.semestre_inicio).toLocaleDateString("es-CO", { day: "numeric", month: "long", year: "numeric" })}`)}
    ${fila(true, "Créditos", `${M.reduce((a, m) => a + m.creditos, 0)} créditos · ${indep.toFixed(1)} h/semana de estudio independiente`)}
    ${fila(disp > 0, "Disponibilidad", `${disp} ${disp === 1 ? "día" : "días"} a la semana · tope de ${S.config.max_horas_dia} h por día`)}
    ${fila(true, "Trabajos", `${S.datos.trabajos.length} agregados por ti + ${plan.tareas.filter(t => t.auto).length} automáticos (laboratorios y talleres)`)}
    ${fila(!plan.advertencias.length, "Plan", plan.advertencias.length ? `${plan.advertencias.length} ${plan.advertencias.length === 1 ? "advertencia" : "advertencias"}: ${esc(plan.advertencias[0].mensaje)}` : `${I.tareas_cubiertas} de ${I.tareas_pendientes} tareas con tiempo asegurado`)}
  </div><div>${plan.consejos.slice(0, 3).map(c => tipHTML(c)).join("")}</div></div>
  <div class="card final"><h3 style="font-size:20px;margin-bottom:6px">${alta.length ? "Tienes puntos por resolver, pero puedes empezar" : "¡Tu semestre está organizado!"}</h3>
    <p class="sub" style="margin-bottom:16px">${alta.length ? "Las recomendaciones urgentes te dicen cómo resolverlos." : "Empieza y revisa tu plan cada día."}</p>
    <button class="b big" id="go" ${ok ? "" : "disabled"}>Empezar mi semestre</button></div>
  <div class="nav2"><button class="b g" data-ir="w_trabajos">Anterior: Trabajos</button><span></span></div>`;
  $("#go").onclick = empezar;
}

/* ================= consejos ================= */
/* tarjeta de recomendación; con `ir` es clicable y abre la conversación del asistente sobre ese tema */
function tipHTML(c, ir) {
  const nom = CAT[c.categoria] || "Consejo", i = plan.consejos.indexOf(c);
  return `<div class="tip ${c.nivel} ${ir ? "click" : ""}" ${ir ? `data-cj="${i}" role="button" tabindex="0"` : ""}><div class="cat">${c.nivel === "alta" ? "Urgente · " : ""}${nom}</div><b>${esc(c.titulo)}</b>
    <p>${esc(c.texto)}</p>${c.accion ? `<p class="do">${esc(c.accion)}</p>` : ""}${ir ? `<span class="hablar">Hablar con el asistente</span>` : ""}</div>`;
}
function conectarTips() {
  document.querySelectorAll("[data-cj]").forEach(el => {
    const abrir = () => { S.pendiente = { accion: { tipo: "consejo", consejo: plan.consejos[+el.dataset.cj] }, etiqueta: plan.consejos[+el.dataset.cj].titulo }; ir("asistente"); };
    el.onclick = abrir; el.onkeydown = e => { if (e.key === "Enter") abrir(); };
  });
}

/* ================= resumen (panel principal) ================= */
function clasesDelDia(f) {
  const ini = fechaDe(S.datos.semestre_inicio);
  return S.datos.bloques.filter(b => {
    if (b.dia !== (f.getDay() + 6) % 7 || f < ini) return false;
    const c = S.datos.labs[b.materia];
    if (b.tipo === "LAB" && c && c.frecuencia === "quincenal") { const w = Math.floor((f - ini) / 864e5 / 7) + 1; return (w % 2 === 0 ? "par" : "impar") === c.semanas; }
    return true; }).sort((a, b) => min(a.inicio) - min(b.inicio));
}
function vResumen() {
  const h = hoy(), I = plan.indicadores, k = iso(h), ini = fechaDe(S.datos.semestre_inicio), sem = Math.floor((h - ini) / 864e5 / 7) + 1;
  const items = [...clasesDelDia(h).map(b => ({ i: b.inicio, f: b.fin, t: `${b.materia} · ${b.tipo}`, m: b.materia, clase: true, s: b.salon })),
                 ...plan.bloques.map((b, j) => ({ b, j })).filter(({ b }) => b.fecha === k).map(({ b, j }) => ({ i: b.inicio, f: b.fin, t: b.titulo, m: b.materia, id: b.tarea_id, tipo: b.tipo, motivo: b.motivo, j }))].sort((a, b) => min(a.i) - min(b.i));
  const prox = listaTrabajos().filter(t => t.estado !== "hecho").sort((a, b) => a.due.localeCompare(b.due)).slice(0, 5);
  const nh = Math.max(0, (S.datos.hechas || []).length), alta = plan.consejos.filter(c => c.nivel === "alta").length;
  $("#v").innerHTML = `<h2>${largo(h).replace(/^./, c => c.toUpperCase())}</h2><p class="sub">Semana ${sem} del semestre (${sem % 2 === 0 ? "par" : "impar"}) · ${I.horas_hoy ? `hoy tienes ${I.horas_hoy} h de trabajo planeado` : "hoy no tienes trabajo planeado"}</p>
  ${plan.advertencias.map(a => `<div class="warn">${esc(a.mensaje)}</div>`).join("")}
  <div class="kpis"><div class="kpi"><b>${I.horas_hoy} h</b><span>de trabajo hoy</span></div><div class="kpi"><b>${I.horas_semana} h</b><span>de trabajo lo que resta de la semana</span></div>
    <div class="kpi ${I.dias_proxima !== null && I.dias_proxima <= 2 ? "alert" : ""}"><b>${I.proxima_entrega ? (I.dias_proxima === 0 ? "hoy" : I.dias_proxima + " d") : "—"}</b><span>${I.proxima_entrega ? "para: " + esc(I.proxima_entrega.titulo) : "sin entregas próximas"}</span></div>
    <div class="kpi"><b>${I.tareas_cubiertas}/${I.tareas_pendientes}</b><span>tareas con tiempo asegurado</span></div>
    <div class="kpi ${alta ? "alert" : ""}"><b>${nh}</b><span>tareas hechas${alta ? ` · ${alta} ${alta === 1 ? "urgente" : "urgentes"}` : ""}</span></div></div>
  <div class="two"><div>
    <div class="card"><h3>Agenda de hoy</h3><div class="hoy-list">${items.map(x => { const c = colorDe(x.m);
      return `<div class="it"><div class="tm">${x.i}–${x.f}</div><span class="dot" style="background:${x.clase ? "#94a3b8" : c}"></span><div style="flex:1"><b>${esc(x.t)}</b><br><small>${x.clase ? "Clase" + (x.s ? " · " + esc(x.s) : "") : esc(x.motivo)}</small></div>
      ${x.j !== undefined ? `<button class="b ${bloqueCumplido(plan.bloques[x.j]) ? "" : "g"} sm" data-cumplido="${x.j}">${bloqueCumplido(plan.bloques[x.j]) ? "Cumplido" : "Marcar cumplido"}</button>` : ""}</div>`; }).join("") || '<div class="empty">Día libre. Descansa o adelanta algo.</div>'}</div></div>
    <div class="card"><h3>Próximas entregas <button class="b g sm" style="float:right" data-ir="trabajos">Ver tablero</button></h3>
      <table>${prox.map(t => { const [dt, dc] = dueTxt(t.due); return `<tr><td><span class="dot" style="background:${colorDe(t.materia)}"></span><b>${esc(t.titulo)}</b><br><small>${esc(t.materia)} · ${t.tipo}${t.estado === "curso" ? " · en curso" : ""}</small></td><td class="n"><b class="due ${dc}">${dt}</b></td></tr>`; }).join("") || '<tr><td class="empty">Sin entregas pendientes</td></tr>'}</table></div>
  </div><aside><h3 style="margin-bottom:10px">Lo más importante ahora</h3>${plan.consejos.slice(0, 3).map(c => tipHTML(c, true)).join("")}<button class="b g" data-ir="asistente" style="width:100%">Abrir el asistente</button></aside></div>`;
  document.querySelectorAll("[data-cumplido]").forEach(b => b.onclick = () => alternarCumplido(+b.dataset.cumplido));
  conectarTips();
}

/* ================= calendario ================= */
function entregasDe(k) {
  return [...plan.tareas.filter(t => t.due === k).map(t => ({ titulo: t.titulo, ok: false })),
          ...S.datos.trabajos.filter(t => t.entrega === k && S.datos.hechas.includes(t.id)).map(t => ({ titulo: t.titulo, ok: true }))];
}
function vCalendario() {
  const h = hoy();
  $("#v").innerHTML = `<div class="cal-top"><h2 style="margin-right:6px">Calendario</h2>
    <div class="seg"><button data-cal="semana" class="${S.cal === "semana" ? "on" : ""}">Semana</button><button data-cal="mes" class="${S.cal === "mes" ? "on" : ""}">Mes</button></div>
    <span class="sp"></span><button class="b g" id="ant" aria-label="Anterior">${SVG('<path d="M15 5l-7 7 7 7"/>', 15)}</button><button class="b g" id="hoyb">Hoy</button><button class="b g" id="sig" aria-label="Siguiente">${SVG('<path d="M9 5l7 7-7 7"/>', 15)}</button></div><div id="calbody"></div>`;
  document.querySelectorAll("[data-cal]").forEach(b => b.onclick = () => { S.cal = b.dataset.cal; guardar(); render(); });
  const mover = n => { if (S.cal === "semana") S.offset += n; else S.mes += n; render(); };
  $("#ant").onclick = () => mover(-1); $("#sig").onclick = () => mover(1); $("#hoyb").onclick = () => { S.offset = 0; S.mes = 0; render(); };
  S.cal === "semana" ? calSemana(h) : calMes(h);
}
function calSemana(h) {
  const lun = sumaDias(lunesDe(h), 7 * S.offset), dias = [...Array(7)].map((_, i) => sumaDias(lun, i)), ini = fechaDe(S.datos.semestre_inicio);
  const sem = Math.floor((lun - ini) / 864e5 / 7) + 1, disp = S.datos.disponibilidad, nowMin = min(S.ahora.slice(11, 16));
  const pos = (i, f) => `top:${Math.max(0, (min(i) - H0 * 60) / 60 * HH)}px;height:${Math.max(18, (min(f) - min(i)) / 60 * HH - 2)}px`;
  const horas = [...Array(H1 - H0)].map((_, i) => `<div>${String(H0 + i).padStart(2, "0")}:00</div>`).join("");
  const cols = dias.map((f, i) => { const k = iso(f), off = disp[i] && !disp[i].disponible;
    const cl = clasesDelDia(f).map(b => `<div class="ev clase" style="${pos(b.inicio, b.fin)};--c:${colorDe(b.materia)}" title="${esc(b.materia)} ${b.tipo} · ${esc(b.salon || "")}"><b>${esc(b.materia)}</b>${b.tipo} · ${b.inicio}${b.salon ? "<br>" + esc(b.salon) : ""}</div>`).join("");
    const pl = plan.bloques.filter(b => b.fecha === k).map(b => { const j = plan.bloques.indexOf(b), hecha = (b.tarea_id && S.datos.hechas.includes(b.tarea_id)) || bloqueCumplido(b), c = colorDe(b.materia);
      return `<div class="ev ${b.tipo} ${hecha ? "hecha" : ""}" data-b="${j}" style="${pos(b.inicio, b.fin)};--c:${c};--bg2:${tint(c, .84)}"><b>${esc(b.tipo === "estudio" ? "Estudio · " + b.materia : b.titulo)}</b>${b.inicio}–${b.fin}</div>`; }).join("");
    const now = k === iso(h) && nowMin >= H0 * 60 && nowMin <= H1 * 60 ? `<div class="now" style="top:${(nowMin - H0 * 60) / 60 * HH}px"></div>` : "";
    return `<div class="tg-col ${off ? "off" : ""} ${k === iso(h) ? "hoy" : ""}">${cl}${pl}${now}</div>`; }).join("");
  const head = dias.map((f, i) => { const k = iso(f), hh = plan.bloques.filter(b => b.fecha === k).reduce((a, b) => a + min(b.fin) - min(b.inicio), 0), ent = entregasDe(k);
    return `<div class="${k === iso(h) ? "hoy" : ""}">${DIAS[i].slice(0, 3)} ${f.getDate()}<small>${(disp[i] && !disp[i].disponible) ? "descanso" : hh ? horasTxt(hh) + " de trabajo" : "&nbsp;"}</small>${ent.slice(0, 2).map(e => `<span class="ent" title="${esc(e.titulo)}">${esc(e.titulo)}</span>`).join("")}</div>`; }).join("");
  const mats = S.datos.materias.map(m => `<span><i style="background:${colorDe(m.codigo)}"></i>${esc(m.codigo)}</span>`).join("");
  $("#calbody").innerHTML = `<p class="sub" style="margin-top:-6px"><span class="chip">Semana ${sem} · ${sem % 2 === 0 ? "par" : "impar"}</span> &nbsp;${corto(lun)} – ${corto(sumaDias(lun, 6))} · toca un bloque para ver por qué está ahí</p>
  <div class="tg" style="--h:${HH}px"><div class="tg-head"><div></div>${head}</div><div class="tg-body"><div class="tg-hours">${horas}</div>${cols}</div></div>
  <div class="leyenda"><span><i style="background:#e9edf3;border:1px solid #94a3b8"></i>Clase</span><span><i style="background:#2563eb"></i>Tarea (sólido)</span><span><i style="border:1px dashed #2563eb"></i>Estudio independiente</span>${mats}</div>`;
  document.querySelectorAll("[data-b]").forEach(el => el.onclick = () => detalle(+el.dataset.b));
}
function calMes(h) {
  const base = new Date(h.getFullYear(), h.getMonth() + S.mes, 1), mesN = base.getMonth(), ini = lunesDe(base), k0 = iso(h);
  const celdas = []; for (let i = 0; i < 42; i++) { const f = sumaDias(ini, i); if (i >= 35 && f.getMonth() !== mesN) break; celdas.push(f); }
  const carga = {}; plan.bloques.forEach(b => carga[b.fecha] = (carga[b.fecha] || 0) + min(b.fin) - min(b.inicio));
  $("#calbody").innerHTML = `<p class="sub" style="margin-top:-6px"><b style="font-size:18px;color:var(--ink)">${base.toLocaleDateString("es-CO", { month: "long", year: "numeric" })}</b> · la barra azul muestra tu carga de trabajo del día; en rojo, las entregas</p>
  <div class="mes">${DIAS.map(d => `<div class="h">${d.slice(0, 3)}</div>`).join("")}${celdas.map(f => { const k = iso(f), e = entregasDe(k), m = carga[k] || 0;
    return `<div class="c ${f.getMonth() !== mesN ? "fuera" : ""} ${k === k0 ? "hoy" : ""}" data-d="${k}"><span class="n">${f.getDate()}</span>${m ? `<div class="ld" title="${horasTxt(m)}"><i style="width:${Math.min(100, m / 360 * 100)}%"></i></div>` : ""}
      ${e.slice(0, 2).map(x => `<span class="t ${x.ok ? "ok" : ""}" title="${esc(x.titulo)}">${esc(x.titulo)}</span>`).join("")}${e.length > 2 ? `<small>+${e.length - 2} más</small>` : ""}</div>`; }).join("")}</div>`;
  document.querySelectorAll("[data-d]").forEach(c => c.onclick = () => { S.offset = Math.round((lunesDe(fechaDe(c.dataset.d)) - lunesDe(h)) / 864e5 / 7); S.cal = "semana"; guardar(); render(); });
}
function detalle(j) {
  const b = plan.bloques[j], d = $("#det"), c = colorDe(b.materia);
  d.innerHTML = `<div class="meta"><span class="mt"><i class="dot" style="background:${c}"></i>${esc(b.materia)}</span> <small>${corto(fechaDe(b.fecha))} · ${b.inicio}–${b.fin}</small></div><h3 style="margin:8px 0 0">${esc(b.titulo)}</h3><p>${esc(b.motivo)}</p>
    <div class="row"><button class="b ${bloqueCumplido(b) ? "g" : ""}" id="cumplido">${bloqueCumplido(b) ? "Quitar cumplido" : "Marcar bloque cumplido"}</button>
      ${b.tarea_id ? `<button class="b g" id="hecho">${estadoDe(b.tarea_id) === "hecho" ? "Reabrir tarea" : "Tarea terminada"}</button>` : ""}<button class="b g" id="cerrar">Cerrar</button></div>`;
  d.style.display = "block"; $("#cerrar").onclick = () => d.style.display = "none";
  $("#cumplido").onclick = () => alternarCumplido(j);
  if (b.tarea_id) $("#hecho").onclick = () => alternarHecho(b.tarea_id);
}

init();
