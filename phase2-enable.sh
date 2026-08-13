#!/usr/bin/env bash
# =============================================================================
# phase2-enable.sh — Фаза 2: подстановка реальных ключей платных API
# (scrapecreators / creatify / postmypost) в ~/factory/.env вместо
# PLACEHOLDER_UNTIL_TOMORROW и пересоздание контейнера n8n.
#
# Использование:
#   ./phase2-enable.sh --dry-run --scrapecreators=KEY --creatify-id=ID \
#       --creatify-key=KEY --postmypost-token=TOKEN --postmypost-project=ID
#
# Без --dry-run: показывает diff (замаскированный), запрашивает подтверждение,
# применяет изменения (python3, точная замена по KEY=) и пересоздаёт n8n.
# Реальный запуск с ключами — только когда ключи получены от поставщиков.
# =============================================================================
set -uo pipefail

ENV_FILE="$HOME/factory/.env"
COMPOSE_DIR="$HOME/factory"

DRY_RUN=0
declare -a ORDER=()       # ENV-ключи (порядок вывода)
declare -a VALS=()        # значения, параллельный массив

usage() {
    cat <<'EOF'
Использование: phase2-enable.sh [--dry-run] \
    --scrapecreators=KEY --creatify-id=ID --creatify-key=KEY \
    --postmypost-token=TOKEN --postmypost-project=ID

Флаги:
  --dry-run                 показать план замены БЕЗ записи в .env
  --scrapecreators=KEY      SCRAPECREATORS_API_KEY  (x-api-key)
  --creatify-id=ID          CREATIFY_API_ID         (X-API-ID)
  --creatify-key=KEY        CREATIFY_API_KEY        (X-API-KEY)
  --postmypost-token=TOKEN  POSTMYPOST_TOKEN        (Bearer token)
  --postmypost-project=ID   POSTMYPOST_PROJECT_ID

Пример (проверка без записи):
  ./phase2-enable.sh --dry-run --scrapecreators=sk-TEST123 \
      --creatify-id=TEST --creatify-key=TEST \
      --postmypost-token=TEST --postmypost-project=123
EOF
    exit 1
}

add_value() {
    local env_key="$1" val="$2" flag="$3"
    if [ -z "$val" ]; then
        echo "ОШИБКА: для --${flag} передано пустое значение" >&2
        exit 1
    fi
    ORDER+=("$env_key")
    VALS+=("$val")
}

# --- разбор аргументов ---
[ $# -eq 0 ] && usage
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        --scrapecreators=*)       add_value SCRAPECREATORS_API_KEY "${1#*=}" scrapecreators ;;
        --creatify-id=*)          add_value CREATIFY_API_ID       "${1#*=}" creatify-id ;;
        --creatify-key=*)         add_value CREATIFY_API_KEY      "${1#*=}" creatify-key ;;
        --postmypost-token=*)     add_value POSTMYPOST_TOKEN      "${1#*=}" postmypost-token ;;
        --postmypost-project=*)   add_value POSTMYPOST_PROJECT_ID "${1#*=}" postmypost-project ;;
        *) echo "Неизвестный аргумент: $1" >&2; usage ;;
    esac
    shift
done
[ ${#ORDER[@]} -eq 0 ] && usage
[ -f "$ENV_FILE" ] || { echo "ОШИБКА: не найден $ENV_FILE" >&2; exit 1; }

# --- сборка пар для python (key value key value ...) ---
PAIRS=()
for i in "${!ORDER[@]}"; do
    PAIRS+=("${ORDER[$i]}" "${VALS[$i]}")
done

# --- python-логика: чтение .env, план замен, применение (mode=plan|apply) ---
PY_FILE="$(mktemp /tmp/phase2-enable-XXXXXX.py)" || exit 1
cat > "$PY_FILE" <<'PYEOF'
import re, sys

MODE = sys.argv[1]
ENV_FILE = sys.argv[2]
raw = sys.argv[3:]
pairs = list(zip(raw[0::2], raw[1::2]))
PLACEHOLDER = "PLACEHOLDER_UNTIL_TOMORROW"

def mask(v):
    n = len(v)
    if n >= 9:
        return v[:4] + "***" + v[-4:]
    if n >= 5:
        return v[:2] + "***" + v[-2:]
    return "[%s chars]" % n

with open(ENV_FILE, "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

cur = {}
for ln in lines:
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", ln)
    if m:
        cur.setdefault(m.group(1), m.group(2))

changes = {}
for k, v in pairs:
    old = cur.get(k)
    if old == v:
        if MODE == "plan":
            print(k, "SAME", mask(old), "", sep="\t")
    elif old and old != PLACEHOLDER:
        if MODE == "plan":
            print(k, "OTHER", mask(old), "", sep="\t")
    else:
        if MODE == "plan":
            print(k, "CHANGE", mask(PLACEHOLDER), mask(v), sep="\t")
        changes[k] = v

if MODE == "apply":
    if not changes:
        print("NO_CHANGES")
        sys.exit(0)
    present = set()
    new_lines = []
    for ln in lines:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", ln)
        if m and m.group(1) in changes:
            present.add(m.group(1))
            new_lines.append(m.group(1) + "=" + changes[m.group(1)])
        else:
            new_lines.append(ln)
    for k, v in changes.items():
        if k not in present:
            new_lines.append(k + "=" + v)
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")
    print("APPLIED")
PYEOF

# --- план замен: python читает .env, НИЧЕГО не пишет (mode=plan) ---
PLAN="$(python3 "$PY_FILE" plan "$ENV_FILE" "${PAIRS[@]}")" || {
    echo "ОШИБКА: не удалось прочитать $ENV_FILE" >&2; rm -f "$PY_FILE"; exit 1; }

if [ "$DRY_RUN" -eq 1 ]; then
    echo "=== DRY RUN: план замены ($ENV_FILE) — запись НЕ производится ==="
else
    echo "=== План замены ($ENV_FILE) ==="
fi

CHANGES=0
while IFS= read -r line; do
    IFS=$'\t' read -r k st oldm newm <<< "$line"
    case "$st" in
        CHANGE) printf '  %-22s %-18s -> %s\n' "$k" "$oldm" "$newm"; CHANGES=$((CHANGES+1)) ;;
        SAME)   printf '  %-22s уже установлено (%s) — пропуск\n' "$k" "$oldm" ;;
        OTHER)  printf '  %-22s уже заполнено (%s), не placeholder — пропуск (менять вручную)\n' "$k" "$oldm" ;;
    esac
done <<< "$PLAN"

if [ "$CHANGES" -eq 0 ]; then
    echo "Менять нечего: все переданные ключи уже актуальны."
    rm -f "$PY_FILE"
    exit 0
fi

if [ "$DRY_RUN" -eq 1 ]; then
    echo ""
    echo "DRY RUN: в $ENV_FILE ничего не записано."
    rm -f "$PY_FILE"
    exit 0
fi

# --- подтверждение ---
echo ""
read -r -p "Применить $CHANGES замен(ы)? [y/N] " ans
case "$ans" in
    y|Y|yes|YES|д|Д|да|ДА) ;;
    *) echo "Отменено, изменения не внесены."; rm -f "$PY_FILE"; exit 1 ;;
esac

# --- применение (python3: точная замена по KEY=, спецсимволы ключей безопасны) ---
RESULT="$(python3 "$PY_FILE" apply "$ENV_FILE" "${PAIRS[@]}")" || {
    echo "ОШИБКА: применение не удалось" >&2; rm -f "$PY_FILE"; exit 1; }
rm -f "$PY_FILE"
if [ "$RESULT" != "APPLIED" ]; then
    echo "ОШИБКА: нечего применять (${RESULT})" >&2
    exit 1
fi

chmod 600 "$ENV_FILE"
PERMS="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || stat -f '%Lp' "$ENV_FILE")"
echo "OK: $ENV_FILE обновлён, права $PERMS"

# --- пересоздание контейнера n8n, чтобы env подхватился ---
echo "Пересоздаю контейнер n8n..."
(cd "$COMPOSE_DIR" && docker compose up -d n8n) || { echo "ОШИБКА: docker compose up -d n8n не удался" >&2; exit 1; }

cat <<'EOF'

=== ДАЛЬШЕ ВРУЧНУЮ (n8n UI) ===
Обнови Credentials в n8n UI: https://assessment-fossil-assignments-alice.trycloudflare.com
(Settings → Credentials):
  - scrapecreators: x-api-key
  - creatify: X-API-ID + X-API-KEY
  - postmypost: Bearer token
Затем Switch-ноды уйдут в real-ветку автоматически.
EOF
echo ""
echo "Готово: фаза 2 включена."
