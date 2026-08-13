#!/usr/bin/env bash
# =============================================================================
# register-tg-commands.sh — регистрирует 28 команд контент-завода в Telegram
# боте через setMyCommands (спека 12, разд. 3).
#
# Зачем: Hermes gateway при каждом подключении к Telegram сам перерегистрирует
# ~60 системных команд (setMyCommands в post-connect housekeeping,
# plugins/platforms/telegram/adapter.py), затирая наши команды. Конфиг-флага
# для отключения авторегистрации в Hermes НЕТ (только command_menu
# max_commands/priority — не кастомный список).
#
# Автозапуск: ExecStartPost в /etc/systemd/system/hermes.service (после старта
# gateway). Также можно запускать вручную:  ~/factory/register-tg-commands.sh
# Скрипт идемпотентен, не фатален (exit 0 всегда — чтобы systemd не считал
# юнит упавшим и не крутил restart-loop).
# =============================================================================
set -u

FACTORY_DIR="/home/ubuntu/factory"
FACTORY_ENV="$FACTORY_DIR/.env"
PAYLOAD="$FACTORY_DIR/tg-commands-25.json"
LOG_TAG="register-tg-commands"
# VK Cloud блокирует основной IP api.telegram.org; 149.154.167.220 записан в
# /etc/hosts и используется Hermes как fallback (TELEGRAM_FALLBACK_IPS).
TG_IP="149.154.167.220"

log() { echo "[$LOG_TAG] $*"; }

# --- Токен (не печатаем) ---
TOKEN=""
if [ -f "$FACTORY_ENV" ]; then
  TOKEN="$(grep -m1 '^TELEGRAM_BOT_TOKEN=' "$FACTORY_ENV" | cut -d= -f2- | tr -d '"' | tr -d "'")"
fi
if [ -z "$TOKEN" ]; then
  log "ERROR: TELEGRAM_BOT_TOKEN not found in $FACTORY_ENV" >&2
  exit 0
fi
if [ ! -f "$PAYLOAD" ]; then
  log "ERROR: payload not found: $PAYLOAD" >&2
  exit 0
fi

API="https://api.telegram.org/bot${TOKEN}"

# --- setMyCommands для одного scope ('default' | 'all_private_chats' | 'all_group_chats') ---
set_commands() {
  local scope="$1"
  if [ "$scope" = "default" ]; then
    curl -s --max-time 25 -X POST "${API}/setMyCommands" \
      -H 'Content-Type: application/json' -d @"$PAYLOAD" \
      --resolve "api.telegram.org:443:${TG_IP}" >/dev/null
  else
    local body
    body="$(python3 -c '
import json, sys
cmds = json.load(open(sys.argv[1]))["commands"]
print(json.dumps({"commands": cmds, "scope": {"type": sys.argv[2]}}, ensure_ascii=False))
' "$PAYLOAD" "$scope")"
    curl -s --max-time 25 -X POST "${API}/setMyCommands" \
      -H 'Content-Type: application/json' -d "$body" \
      --resolve "api.telegram.org:443:${TG_IP}" >/dev/null
  fi
}

# --- Проверка: getMyCommands = ровно наши 28 (все имена, без чужих) ---
verify_ours() {
  local resp total missing
  resp="$(curl -s --max-time 25 "${API}/getMyCommands" --resolve "api.telegram.org:443:${TG_IP}")"
  total="$(printf '%s' "$resp" | python3 -c 'import sys,json; r=json.load(sys.stdin); print(len(r.get("result") or []))' 2>/dev/null || echo 0)"
  missing="$(printf '%s' "$resp" | python3 -c '
import sys, json
want = {"start","help","status","mode","onboard","start_cycle","cancel","topics","competitors","accounts","budget","client","clients","reload_skills","ping","creators","creator","creator_content","audience","transcript","comments","upload_avatar","my_avatars","asset","shorts","product","banner","publish_type"}
got = {c["command"] for c in (json.load(sys.stdin).get("result") or [])}
print(",".join(sorted(want - got)))
' 2>/dev/null || echo "parse-error")"
  [ "$total" = "28" ] && [ -z "$missing" ]
}

# --- Ждём, пока gateway закончит свой housekeeping (перерегистрация ~60 команд
# происходит после коннекта), затем пишем ПОСЛЕДНИМИ и проверяем стабильность ---
log "waiting 20s for Hermes gateway housekeeping to settle..."
sleep 20

registered=0
for attempt in 1 2 3 4 5; do
  set_commands "default"
  set_commands "all_private_chats"
  set_commands "all_group_chats"
  sleep 5
  if verify_ours; then
    sleep 8
    if verify_ours; then
      registered=1
      break
    fi
  fi
  log "attempt $attempt: menu overwritten/incomplete — re-registering"
done

if [ "$registered" = "1" ]; then
  log "OK: all 28 factory commands registered (scopes: default, all_private_chats, all_group_chats)"
  exit 0
fi
log "WARNING: not stable after 5 attempts (Hermes may have re-registered). Re-run: bash $FACTORY_DIR/register-tg-commands.sh" >&2
exit 0
