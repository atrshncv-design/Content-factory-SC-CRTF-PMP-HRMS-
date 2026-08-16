#!/usr/bin/env python3
"""
Миграция factory.db под волну 5 (авто-режим + верификация в цикле).

Расширяет схему SQLite-БД (python3 + sqlite3, без сторонних зависимостей):

    users.auto_approve     INTEGER  — флаг авто-режима (0/1), default 0
    sessions.quick_payload TEXT     — JSON-пейлоад быстрых/верификационных сценариев

Свойства:
  * Идемпотентность — ALTER выполняется только если колонки нет
    (PRAGMA table_info).
  * Отсутствующая таблица не роняет скрипт — выводится предупреждение.
  * --dry-run только печатает план; --apply применяет (с бэкапом файла БД).
  * Регистрируется в schema_version (version=5) для воспроизводимости.

Использование:
    python3 migrate-client-profiles-v3.py <path/to/factory.db> --dry-run
    python3 migrate-client-profiles-v3.py <path/to/factory.db> --apply
"""

import argparse
import datetime
import os
import shutil
import sqlite3
import sys

MIGRATION_VERSION = 5

# (таблица, колонка, тип, дефолт, комментарий)
MIGRATIONS = [
    ("users", "auto_approve", "INTEGER", "0",
     "флаг авто-режима: 1 — пропускать верификации сценария/видео"),
    ("sessions", "quick_payload", "TEXT", None,
     "JSON-пейлоад быстрых сценариев и верификации"),
]


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


def build_plan(con):
    """Возвращает список действий (kind, sql, params, text)."""
    actions = []
    for table, col, col_type, default, note in MIGRATIONS:
        if not table_exists(con, table):
            actions.append(
                ("skip", None, None,
                 f"[ПРОПУСК] таблица {table!r} отсутствует — колонка "
                 f"{table}.{col} не добавляется"))
            continue
        cols = get_columns(con, table)
        if cols is None:
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
            sql = f'ALTER TABLE "{table}" ADD COLUMN "{col}" {col_type}'
            if default is not None:
                sql += f' NOT NULL DEFAULT {default}'
            actions.append(
                ("add", sql, None,
                 f"[ДОБАВИТЬ] {table}.{col} {col_type}" + (f" DEFAULT {default}" if default else "") + f" — {note}"))
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
            print(f"Миграция v3 (schema_version={MIGRATION_VERSION}) уже применена — no-op.")
            return True

        for kind, sql, params, text in build_plan(con):
            print("  " + text)
            if kind == "add":
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

        # Контроль результата
        ok_users = False
        ok_sessions = False
        cols = get_columns(con, "users")
        if cols is not None:
            ok_users = "auto_approve" in cols
        cols = get_columns(con, "sessions")
        if cols is not None:
            ok_sessions = "quick_payload" in cols
        print(f"Контроль: users.auto_approve — {'OK' if ok_users else 'НЕ добавлена'}; "
              f"sessions.quick_payload — {'OK' if ok_sessions else 'НЕ добавлена'}")
        return ok_users and ok_sessions
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(
        description="Идемпотентная миграция factory.db под волну 5 "
                    "(users.auto_approve + sessions.quick_payload)")
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
