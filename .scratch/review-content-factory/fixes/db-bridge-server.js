#!/usr/bin/env node
/**
 * factory-db-bridge — минимальный HTTP-мост к factory.db для n8n.
 * Слушает docker0 (172.17.0.1:8787) — доступен только контейнерам, не снаружи.
 *
 * API:
 *   GET  /health            -> {ok:true}
 *   POST /query             -> {ok, rows?} | {ok, changes?, lastInsertRowid?}
 *     body: { sql: string, params?: array|object }
 *   POST /exec              -> как /query, но для INSERT/UPDATE/DELETE
 *
 * Безопасность:
 *   - заголовок X-BRIDGE-TOKEN (сверяется с env FACTORY_DB_BRIDGE_TOKEN)
 *   - FAIL-CLOSED: пустой/отсутствующий FACTORY_DB_BRIDGE_TOKEN ->
 *     500 {ok:false, error:'bridge not configured'} (запросы НЕ пропускаются)
 *   - bind docker0 172.17.0.1:8787 (НЕ 0.0.0.0!) — доступен контейнерам
 *     (host.docker.internal) и хосту (172.17.0.1), не снаружи
 *   - только один statement за запрос (запрет ;-инъекций)
 *   - только SELECT/INSERT/UPDATE/DELETE/PRAGMA/REPLACE/ATTACH-безопасные
 */
'use strict';
const http = require('node:http');
const { DatabaseSync } = require('node:sqlite');
const fs = require('node:fs');
const crypto = require('node:crypto');

const PORT = parseInt(process.env.BRIDGE_PORT || '8787', 10);
// Безопасность (FIX-16): НЕ слушать 0.0.0.0 (все интерфейсы, включая публичный).
// По докстрингу мост живёт на docker0 172.17.0.1:8787: доступен n8n-контейнеру
// (host.docker.internal = 172.17.0.1) и с хоста (172.17.0.1), но не снаружи.
// Для запуска в bridge-контейнере нужен network_mode: host (172.17.0.1 не является
// локальным адресом внутри обычного контейнера). BRIDGE_HOST=127.0.0.1 — только
// если доступ из контейнеров не требуется.
const HOST = process.env.BRIDGE_HOST || '172.17.0.1';
const DB_PATH = process.env.FACTORY_DB_PATH || '/var/data/factory.db';
const TOKEN = process.env.FACTORY_DB_BRIDGE_TOKEN || '';

const db = new DatabaseSync(DB_PATH);
db.exec('PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000; PRAGMA foreign_keys=ON;');

const ALLOWED_PREFIXES = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'PRAGMA', 'WITH'];

function allowed(sql) {
  const trimmed = sql.trim().toUpperCase();
  return ALLOWED_PREFIXES.some((p) => trimmed.startsWith(p));
}

function singleStatement(sql) {
  // наивная, но рабочая проверка: без токенов внутри строк/кавычек считаем ';'
  let inStr = null;
  for (let i = 0; i < sql.length; i++) {
    const ch = sql[i];
    if (inStr) {
      if (ch === inStr && sql[i - 1] !== '\\') inStr = null;
      continue;
    }
    if (ch === "'" || ch === '"' || ch === '`') inStr = ch;
    else if (ch === ';' && i !== sql.length - 1) return false;
  }
  return true;
}

function handleQuery(body, res) {
  const _end = res.end.bind(res);
  res.end = (payload) => { if (typeof payload === 'string' && payload.length < 500) console.log('DB-BRIDGE RES', payload.slice(0, 300)); return _end(payload); };
  if (!body || typeof body.sql !== 'string' || !body.sql.trim()) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: false, error: 'sql required' }));
    return;
  }
  console.log('DB-BRIDGE REQ', JSON.stringify({sql: body.sql, params: body.params}).slice(0, 400));
  const sql = body.sql.trim();
  if (!allowed(sql)) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: false, error: 'statement type not allowed' }));
    return;
  }
  if (!singleStatement(sql)) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: false, error: 'multiple statements not allowed' }));
    return;
  }
  try {
    const stmt = db.prepare(sql);
    const params = Array.isArray(body.params) ? body.params
      : (body.params && typeof body.params === 'object') ? body.params
      : [];
    const isWrite = /^(INSERT|UPDATE|DELETE|REPLACE|WITH)/i.test(sql);
    if (isWrite) {
      const r = stmt.run(...(Array.isArray(params) ? params : [params]));
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, changes: Number(r.changes), lastInsertRowid: Number(r.lastInsertRowid) }));
    } else {
      const rows = stmt.all(...(Array.isArray(params) ? params : [params]));
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, rows }));
    }
  } catch (e) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: false, error: String(e.message || e) }));
  }
}

const server = http.createServer((req, res) => {
  // CORS/OPTIONS не нужен (сервер-сервер)
  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, db: DB_PATH }));
    return;
  }
  if (req.method !== 'POST' || req.url !== '/query') {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: false, error: 'not found' }));
    return;
  }
  // FIX-16: fail-open -> fail-closed. Раньше `if (TOKEN) {…}` пропускал запросы
  // без токена при пустом FACTORY_DB_BRIDGE_TOKEN (полный read/write factory.db
  // без аутентификации). Теперь пустой токен = мост не сконфигурирован: 500,
  // запросы НЕ пропускаются никогда.
  if (!TOKEN) {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: false, error: 'bridge not configured' }));
    return;
  }
  const got = req.headers['x-bridge-token'] || '';
  const a = Buffer.from(String(got));
  const b = Buffer.from(TOKEN);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
    res.writeHead(401, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: false, error: 'unauthorized' }));
    return;
  }
  let raw = '';
  req.on('data', (c) => { raw += c; if (raw.length > 256 * 1024) req.destroy(); });
  req.on('end', () => {
    try {
      handleQuery(JSON.parse(raw || '{}'), res);
    } catch (e) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: false, error: 'invalid json: ' + String(e.message) }));
    }
  });
});

server.listen(PORT, HOST, () => {
  console.log(`factory-db-bridge listening on ${HOST}:${PORT} -> ${DB_PATH}`);
});
