#!/usr/bin/env node
// Unfold an n8n execution: resolve the flatted refs in execution_data and print
// what each node actually OUTPUT (json per node) — beyond the OK/error summary
// of inspect-execution.js. Use when a node "succeeds" but produces wrong data
// (e.g. an UPDATE that returns changes:0, or a branch that silently falls through).
//
// Usage:
//   docker cp unfold-execution.js factory-n8n:/tmp/
//   docker exec factory-n8n node /tmp/unfold-execution.js <executionId>
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('/home/node/.n8n/database.sqlite');
const id = parseInt(process.argv[2] || '0', 10);
if (!id) { console.error('usage: node unfold-execution.js <executionId>'); process.exit(1); }

const row = db.prepare('SELECT data FROM execution_data WHERE executionId=?').get(id);
if (!row) { console.error('NO execution_data row (stuck running? -> check docker logs <n8n>)'); process.exit(0); }

const g = JSON.parse(row.data);
const root = Array.isArray(g) ? g[0] : g;
const seen = new WeakSet();
function ref(r, depth = 0) {
  if (typeof r === 'string' && g[r] !== undefined) return ref(g[r], depth + 1);
  if (Array.isArray(r)) return r.map(x => ref(x, depth + 1));
  if (r && typeof r === 'object') {
    if (depth > 40 || seen.has(r)) return '[cycle]';
    seen.add(r);
    const o = {};
    for (const k of Object.keys(r)) o[k] = ref(r[k], depth + 1);
    seen.delete(r);
    return o;
  }
  return r;
}

const resultData = ref(root.resultData) || {};
const runData = resultData.runData || {};
for (const k of Object.keys(runData)) {
  const arr = runData[k];
  const first = Array.isArray(arr) && arr.length ? arr[0] : null;
  if (!first) continue;
  const status = first.executionStatus || '?';
  const main = first.data && first.data.main;
  let out = '(no output data)';
  if (main && main[0]) {
    const items = main[0].map(it => (it && it.json) || null);
    out = JSON.stringify(items).slice(0, 2000);
  }
  console.log('=== ' + k + ' [' + status + '] ===');
  console.log(out);
  console.log();
}
