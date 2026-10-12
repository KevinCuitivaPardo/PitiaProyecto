// Verifica que el motor JS (prototipo) produce EXACTAMENTE el mismo plan que el motor Python
// en varios escenarios.   Uso:
//   python pruebas/exportar_escenarios.py > /tmp/escenarios.json && node pruebas/cruce_js_python.js /tmp/escenarios.json
const assert = require("assert");
const fs = require("fs");
const E = require("../prototipo/engine.js");

const escenarios = JSON.parse(fs.readFileSync(process.argv[2] || "/tmp/escenarios.json", "utf8"));
let total = 0;
for (const esc of escenarios) {
  const plan = E.planificar(esc.datos, { fecha: E.fecha(esc.fecha), min: esc.min });
  const ref = esc.plan;
  assert.deepStrictEqual(plan.bloques, ref.bloques, `${esc.nombre}: bloques distintos`);
  assert.deepStrictEqual(plan.advertencias, ref.advertencias, `${esc.nombre}: advertencias distintas`);
  assert.deepStrictEqual(plan.horizonte, ref.horizonte, `${esc.nombre}: horizonte distinto`);
  const ord = (a) => a.map((t) => Object.assign({}, t)).sort((x, y) => (x.id < y.id ? -1 : 1));
  assert.deepStrictEqual(ord(plan.tareas), ord(ref.tareas), `${esc.nombre}: tareas distintas`);
  for (const sem of Object.keys(ref.resumen)) for (const m of Object.keys(ref.resumen[sem]))
    for (const k of ["meta_h", "tareas_h", "estudio_h"])
      assert.ok(Math.abs(plan.resumen[sem][m][k] - ref.resumen[sem][m][k]) <= 0.1 + 1e-9, `${esc.nombre}: resumen ${sem} ${m} ${k}`);
  total += plan.bloques.length;
  console.log(`  ok  ${esc.nombre.padEnd(36)} ${String(plan.bloques.length).padStart(3)} bloques, ${plan.advertencias.length} advertencia(s)`);
}
console.log(`\nOK: el motor JS coincide con Python en ${escenarios.length} escenarios (${total} bloques comparados).`);
