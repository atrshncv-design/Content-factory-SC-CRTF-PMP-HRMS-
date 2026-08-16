#!/usr/bin/env python3
"""
Миграция factory.db под профили клиентов (тикет 01, spec «Модель данных»).

Расширяет схему SQLite-БД (python3 + sqlite3, без сторонних зависимостей):

    clients.description          TEXT     — «что делает компания» (Q3)
    clients.context_links        TEXT     — JSON-массив строк (Q5)
    clients.context_docs         TEXT     — JSON-массив {name,mime,text,chars} (Q6)
    clients.context_refs         TEXT     — JSON-массив строк (Q8)
    users.active_client_id       INTEGER  — per-чат активный профиль (NULL = нет)
    sessions.profile_draft       TEXT     — черновик интервью (JSON)

Плюс сид владельца:
    INSERT OR IGNORE INTO users (tg_user_id, username, role) VALUES (941296693, 'owner', 'admin')

Свойства:
  * Идемпотентность — перед каждым ALTER проверяется PRAGMA table_info;
    существующие колонки/таблицы пропускаются с сообщением.
  * Отсутствующая таблица (например sessions) не роняет скрипт —
    выводится предупреждение и работа продолжается.
  * --dry-run только печатает план; --apply применяет (с бэкапом файла БД).
  * Применяется на сервере только в деплой-тикете 12; локально — только на копиях.
  * Регистрируется в schema_version (version=3) для воспроизводимости.

Использование:
    python3 migrate-client-profiles.py <path/to/factory.db> --dry-run
    python3 migrate-client-profiles.py <path/to/factory.db> --apply
"""

import argparse
import datetime
import os
import shutil
import sqlite3
import sys

MIGRATION_VERSION = 3
OWNER_TG_ID = 941296693
OWNER_USERNAME = "owner"
OWNER_ROLE = "admin"

# (таблица, колонка, тип, комментарий для плана)
MIGRATIONS = [
    ("clients", "description", "TEXT", "«что делает компания» (Q3)"),
    ("clients", "context_links", "TEXT", "JSON-массив строк (Q5)"),
    ("clients", "context_docs", "TEXT", "JSON-массив {name,mime,text,chars} (Q6)"),
    ("clients", "context_refs", "TEXT", "JSON-массив строк (Q8)"),
    ("users", "active_client_id", "INTEGER", "per-чат активный профиль (NULL = нет)"),
    ("sessions", "profile_draft", "TEXT", "черновик интервью (JSON)"),
]

SEED_SQL = (
    f"INSERT OR IGNORE INTO users (tg_user_id, username, role) "
    f"VALUES ({OWNER_TG_ID}, '{OWNER_USERNAME}', '{OWNER_ROLE}')"
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


def owner_seeded(con):
    row = con.execute(
        "SELECT 1 FROM users WHERE tg_user_id=?", (OWNER_TG_ID,)
    ).fetchone()
    return row is not None


def build_plan(con):
    """Возвращает список действий (kind, sql_or_None, params_or_None, text).

    kind: 'add' — ALTER (реальное изменение),
          'seed' — сид владельца (реальное изменение),
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
    if not table_exists(con, "users"):
        actions.append(
            ("skip", None, None,
             "[ПРОПУСК] таблица 'users' отсутствует — сид владельца не выполняется"))
    elif owner_seeded(con):
        actions.append(
            ("skip", None, None,
             f"[ПРОПУСК] сид владельца уже применён "
             f"(users.tg_user_id={OWNER_TG_ID} существует)"))
    else:
        actions.append(("seed", SEED_SQL,
                        None,
                        f"[СИД] INSERT OR IGNORE владелец "
                        f"tg_user_id={OWNER_TG_ID} username='{OWNER_USERNAME}'"))
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
            print(f"Миграция v1 (schema_version={MIGRATION_VERSION}) уже применена — no-op.")
            return True

        for kind, sql, params, text in build_plan(con):
            print("  " + text)
            if kind in ("add", "seed"):
                pending.append((sql, params))

        if not pending:
            print("\nМиграция не требуется: схема уже актуальна (no-op).")
            # всё равно регистрируем версию, чтобы не перезапускаться
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
        added = 0
        for table, col, _t, _n in MIGRATIONS:
            cols = get_columns(con, table)
            if cols is not None and col in cols:
                added += 1
        print(f"Применено ALTER: {added}/{len(MIGRATIONS)}; сид владельца: "
              f"{'OK' if owner_seeded(con) else 'не выполнен'}")
        return True
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(
        description="Идемпотентная миграция factory.db под профили клиентов")
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
            print(f"РЕЖИМ: DRY-RUN (ничего не меняется)")
            print_plan(actions, db_path)
            return 0
        print("РЕЖИМ: APPLY")
        # apply_migrations сам печатает план и применяет
        return 0 if apply_migrations(db_path) else 1
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
