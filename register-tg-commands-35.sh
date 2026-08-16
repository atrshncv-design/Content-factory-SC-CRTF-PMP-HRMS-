#!/usr/bin/env bash
# =============================================================================
# register-tg-commands-35.sh — регистрирует 33 команды контент-завода в Telegram
# боте через setMyCommands (3 формата 16.08: asset/product/banner удалены).
# Копия register-tg-commands.sh с tg-commands-35.json и verify на 33.
# Идемпотентен, exit 0 всегда.
# =============================================================================
set -u

FACTORY_DIR="/home/ubuntu/factory"
FACTORY_ENV="$FACTORY_DIR/.env"
PAYLOAD="$FACTORY_DIR/tg-commands-35.json"
LOG_TAG="register-tg-commands"
TG_IP="149.154.167.220"

log() { echo "[$LOG_TAG] $*"; }

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

verify_ours() {
  local resp total missing
  resp="$(curl -s --max-time 25 "${API}/getMyCommands" --resolve "api.telegram.org:443:${TG_IP}")"
  total="$(printf '%s' "$resp" | python3 -c 'import sys,json; r=json.load(sys.stdin); print(len(r.get("result") or []))' 2>/dev/null || echo 0)"
  missing="$(printf '%s' "$resp" | python3 -c '
import sys, json
want = {"start","menu","instruction","help","status","mode","onboard","start_cycle","url2video","shorts","cancel","topics","competitors","accounts","budget","client","clients","reload_skills","ping","creators","creator","creator_content","audience","transcript","comments","upload_avatar","my_avatars","publish_type","profile","profiles","add_operator","operators","avatar_video"}
got = {c["command"] for c in (json.load(sys.stdin).get("result") or [])}
print(",".join(sorted(want - got)))
' 2>/dev/null || echo "parse-error")"
  [ "$total" = "33" ] && [ -z "$missing" ]
}

log "waiting 20s for housekeeping to settle..."
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
  log "OK: all 33 factory commands registered (scopes: default, all_private_chats, all_group_chats)"
  exit 0
fi
log "WARNING: not stable after 5 attempts. Re-run: bash $FACTORY_DIR/register-tg-commands-35.sh" >&2
exit 0
