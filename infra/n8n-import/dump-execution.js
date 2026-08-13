#!/usr/bin/env node
// Dump all node outputs of an n8n execution (all main outputs per node), resolving flatted refs.
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('/home/node/.n8n/database.sqlite');
const id = parseInt(process.argv[2] || '0', 10);
if (!id) { console.error('usage: node dump-execution.js <executionId>'); process.exit(1); }
const row = db.prepare('SELECT data FROM execution_data WHERE executionId=?').get(id);
if (!row) { console.error('NO execution_data row'); process.exit(0); }
const g = JSON.parse(row.data);
const root = Array.isArray(g) ? g[0] : g;
const seen = new WeakSet();
function ref(r, d = 0) {
  if (typeof r === 'string' && g[r] !== undefined) return ref(g[r], d + 1);
  if (Array.isArray(r)) return r.map(x => ref(x, d + 1));
  if (r && typeof r === 'object') {
    if (d > 30 || seen.has(r)) return '[cycle]';
    seen.add(r);
    const o = {};
    for (const k of Object.keys(r)) o[k] = ref(r[k], d + 1);
    seen.delete(r);
    return o;
  }
  return r;
}
const rd = ref(root.resultData) || {};
console.log('error:', JSON.stringify(rd.error));
console.log('lastNodeExecuted:', rd.lastNodeExecuted);
const runData = rd.runData || {};
for (const k of Object.keys(runData)) {
  const first = Array.isArray(runData[k]) && runData[k].length ? runData[k][0] : null;
  if (!first) continue;
  console.log('===' + k + ' [' + (first.executionStatus || '?') + ']===');
  const main = first.data && first.data.main;
  if (main) {
    main.forEach((m, i) => {
      const items = (m || []).map(it => JSON.stringify(it && it.json));
      console.log(' out[' + i + ']: ' + JSON.stringify(items).slice(0, 800));
    });
  }
}
