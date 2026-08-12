#!/usr/bin/env bash
# =============================================================================
#  Применяет миграции SQLite контент-завода (спека 01).
#  Идемпотентно: пропускает уже применённые (по schema_version).
#  Запускается из контейнера n8n/hermes или вручную: ./migrate.sh
# =============================================================================
set -euo pipefail

DB_PATH="${FACTORY_DB_PATH:-./data/factory.db}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-./infra/db}"

mkdir -p "$(dirname "$DB_PATH")"

echo "→ БД: $DB_PATH"
echo "→ Миграции: $MIGRATIONS_DIR"

# Создаём БД с прагмами, если нет
if [ ! -f "$DB_PATH" ]; then
  echo "→ Создаю новую БД..."
fi

# Применяем миграции по порядку
for sql in "$MIGRATIONS_DIR"/[0-9][0-9][0-9]_*.sql; do
  [ -f "$sql" ] || continue
  ver=$(basename "$sql" | grep -oE '^[0-9]+' | sed 's/^0*//')
  [ -z "$ver" ] && ver=0

  applied=$(sqlite3 "$DB_PATH" \
    "SELECT COUNT(*) FROM schema_version WHERE version=$ver;" 2>/dev/null || echo 0)

  if [ "$applied" -gt 0 ]; then
    echo "  ✓ миграция $ver уже применена"
    continue
  fi

  echo "  → применяю миграцию $ver ($(basename "$sql"))..."
  sqlite3 "$DB_PATH" < "$sql"
  echo "  ✓ миграция $ver применена"
done

echo "→ Готово. Версия схемы:"
sqlite3 "$DB_PATH" "SELECT 'v' || MAX(version) FROM schema_version;"
echo ""
echo "→ Таблицы:"
sqlite3 "$DB_PATH" ".tables"
