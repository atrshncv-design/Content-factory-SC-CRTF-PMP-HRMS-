#!/usr/bin/env node
// Fully resolve runData for a specific node in an execution.
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('/home/node/.n8n/database.sqlite');
const id = parseInt(process.argv[2] || '0', 10);
const nodeName = process.argv[3] || '';
if (!id || !nodeName) { console.error('usage: node dump-node.js <executionId> <nodeName>'); process.exit(1); }
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
const runData = rd.runData || {};
const node = runData[nodeName];
if (!node) { console.error('node not found'); process.exit(0); }
console.log(JSON.stringify(node, null, 1).slice(0, 12000));
