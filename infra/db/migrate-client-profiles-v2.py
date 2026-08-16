#!/usr/bin/env python3
"""
Миграция factory.db под волну 2 профилей клиентов (тикет 13, spec «Волна 2»).

Расширяет схему SQLite-БД (python3 + sqlite3, без сторонних зависимостей):

    clients.publish_platforms TEXT — JSON-массив дефолтных платформ публикации

Плюс сид вопросов интервью:
    INSERT OR IGNORE INTO settings (key, value, updated_at)
    VALUES ('profile_questions', '<JSON-массив 8 дефолтных вопросов>',
            datetime('now'))

Дефолтные формулировки 8 вопросов взяты дословно из jsCode ноды 'PFN Qlist'
воркфлоу wf-tg-bot (.scratch/client-profiles/fixes/wf-tg-bot.json).

Свойства:
  * Идемпотентность — ALTER выполняется только если колонки нет
    (PRAGMA table_info); сид — только если ключа profile_questions ещё нет
    в settings (INSERT OR IGNORE — страховка).
  * Отсутствующая таблица/колонка не роняет скрипт — выводится
    предупреждение и работа продолжается.
  * --dry-run только печатает план; --apply применяет (с бэкапом файла БД).
  * Применяется на сервере только в деплой-тикете 21; локально — только
    на копиях (к data/factory.db в репо и на сервере НЕ применять).
  * Регистрируется в schema_version (version=4) для воспроизводимости.

Использование:
    python3 migrate-client-profiles-v2.py <path/to/factory.db> --dry-run
    python3 migrate-client-profiles-v2.py <path/to/factory.db> --apply
"""

import argparse
import datetime
import json
import os
import shutil
import sqlite3
import sys

MIGRATION_VERSION = 4

# --- Дефолтные вопросы интервью: дословно из PFN Qlist (wf-tg-bot.json) ---
DEFAULT_QUESTIONS = [
    "📛 Как называется компания?",
    "🎯 Какая ниша у компании?",
    "📝 Что делает компания?",
    "👥 Кто целевая аудитория?",
    "🔗 Пришли ссылки на ресурсы компании — по одной, потом нажми «Готово»",
    "📄 Пришли документы компании — файлом или ссылкой, по одному, потом нажми «Готово»",
    "🎙️ Какой тон общения у компании?",
    "🔄 Референсы и конкуренты — по одному в строке",
]
QUESTIONS_JSON = json.dumps(DEFAULT_QUESTIONS, ensure_ascii=False)
PROFILE_QUESTIONS_KEY = "profile_questions"

# (таблица, колонка, тип, комментарий для плана)
MIGRATIONS = [
    ("clients", "publish_platforms", "TEXT",
     "JSON-массив дефолтных платформ публикации (волна 2)"),
]

SEED_SQL = (
    "INSERT OR IGNORE INTO settings (key, value, updated_at) "
    "VALUES (?, ?, datetime('now'))"
)


def get_columns(con, table):
    """Возвращает set имён колонок таблицы или None, если таблицы нет."""
    try:
        rows = con.execute(f'PRAGMA table_info("{table}")').fetchall()
    except sqlite3.Error:
        return None
    if not rows:
        return None
    return {r[1] for r in rows}


def table_exists(con, table):
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def schema_version_applied(con, version):
    if not table_exists(con, "schema_version"):
        return False
    row = con.execute(
        "SELECT 1 FROM schema_version WHERE version=?", (version,)
    ).fetchone()
    return row is not None


def questions_seeded(con):
    """True, если profile_questions уже есть в settings (сид применён)."""
    row = con.execute(
        "SELECT 1 FROM settings WHERE key=?", (PROFILE_QUESTIONS_KEY,)
    ).fetchone()
    return row is not None


def build_plan(con):
    """Возвращает список действий (kind, sql, params, text).

    kind: 'add' — ALTER (реальное изменение),
          'seed' — сид вопросов (реальное изменение),
          'skip' — уже есть / таблицы нет (no-op).
    """
    actions = []
    for table, col, col_type, note in MIGRATIONS:
        if not table_exists(con, table):
            actions.append(
                ("skip", None, None,
                 f"[ПРОПУСК] таблица {table!r} отсутствует — колонка "
                 f"{table}.{col} не добавляется"))
            continue
        cols = get_columns(con, table)
        if cols is None:  # таблица исчезла между проверками — перестраховка
            actions.append(
                ("skip", None, None,
                 f"[ПРОПУСК] таблица {table!r} недоступна — колонка "
                 f"{table}.{col} не добавляется"))
            continue
        if col in cols:
            actions.append(
                ("skip", None, None,
                 f"[ПРОПУСК] колонка {table}.{col} уже существует"))
        else:
            actions.append(
                ("add", f'ALTER TABLE "{table}" ADD COLUMN "{col}" {col_type}',
                 None,
                 f"[ДОБАВИТЬ] {table}.{col} {col_type} — {note}"))
    # Сид profile_questions
    if not table_exists(con, "settings"):
        actions.append(
            ("skip", None, None,
             "[ПРОПУСК] таблица 'settings' отсутствует — сид "
             "'profile_questions' не выполняется"))
    else:
        settings_cols = get_columns(con, "settings")
        if settings_cols is None or "key" not in settings_cols:
            actions.append(
                ("skip", None, None,
                 "[ПРОПУСК] в таблице 'settings' нет колонки 'key' — сид "
                 "'profile_questions' не выполняется"))
        elif questions_seeded(con):
            actions.append(
                ("skip", None, None,
                 f"[ПРОПУСК] сид уже применён (settings.key="
                 f"'{PROFILE_QUESTIONS_KEY}' существует)"))
        else:
            actions.append(
                ("seed", SEED_SQL, (PROFILE_QUESTIONS_KEY, QUESTIONS_JSON),
                 f"[СИД] settings.{PROFILE_QUESTIONS_KEY} = {QUESTIONS_JSON}"))
    return actions


def print_plan(actions, db_path):
    print(f"План миграции для {db_path}:")
    if not actions:
        print("  (пусто)")
        return
    for _kind, _sql, _params, text in actions:
        print("  " + text)


def make_backup(db_path):
    """Копия файла БД рядом с оригиналом: <db>.bak.<timestamp>."""
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = f"{db_path}.bak.{ts}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def apply_migrations(db_path):
    pending = []
    con = sqlite3.connect(db_path)
    try:
        if schema_version_applied(con, MIGRATION_VERSION):
            print(f"Миграция v2 (schema_version={MIGRATION_VERSION}) уже применена — no-op.")
            return True

        for kind, sql, params, text in build_plan(con):
            print("  " + text)
            if kind in ("add", "seed"):
                pending.append((sql, params))

        if not pending:
            print("\nМиграция не требуется: схема уже актуальна (no-op).")
            con.execute(
                "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                (MIGRATION_VERSION,),
            )
            con.commit()
            return True

        backup_path = make_backup(db_path)
        print(f"\nБэкап создан: {backup_path}")

        for sql, params in pending:
            if params is None:
                con.execute(sql)
            else:
                con.execute(sql, params)

        con.execute(
            "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
            (MIGRATION_VERSION,),
        )
        con.commit()

        # Контроль результата после применения
        cols = get_columns(con, "clients")
        alt_ok = cols is not None and "publish_platforms" in cols
        seed_ok = table_exists(con, "settings") and questions_seeded(con)
        print(f"\nКонтроль: clients.publish_platforms — "
              f"{'OK' if alt_ok else 'НЕ добавлена'}; "
              f"сид settings.{PROFILE_QUESTIONS_KEY} — "
              f"{'OK' if seed_ok else 'не выполнен'}")
        return True
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(
        description="Идемпотентная миграция factory.db под волну 2 "
                    "(publish_platforms + profile_questions)")
    parser.add_argument("db", help="путь к SQLite-файлу factory.db")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="только показать план, ничего не менять")
    mode.add_argument("--apply", action="store_true",
                      help="применить миграцию (с бэкапом файла БД)")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.error("укажите --dry-run (план) или --apply (применение)")

    if not os.path.isfile(args.db):
        print(f"ОШИБКА: файл БД не найден: {args.db}", file=sys.stderr)
        return 1

    db_path = os.path.abspath(args.db)

    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        con.execute("SELECT 1 FROM sqlite_master LIMIT 1")
        con.close()
    except sqlite3.Error as e:
        print(f"ОШИБКА: {db_path} не является читаемой SQLite-БД: {e}",
              file=sys.stderr)
        return 1

    con = sqlite3.connect(db_path)
    try:
        actions = build_plan(con)
        print(f"factory.db: {db_path}")
        if args.dry_run:
            print("РЕЖИМ: DRY-RUN (ничего не меняется)")
            print_plan(actions, db_path)
            return 0
        print("РЕЖИМ: APPLY")
        return 0 if apply_migrations(db_path) else 1
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
