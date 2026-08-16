#!/usr/bin/env python3
"""Seam tests for infra/db/migrate-client-profiles*.py public interface.

Public surface: each migration is a CLI script
    python3 infra/db/migrate-client-profiles[-v2|-v3].py <db> --dry-run
    python3 infra/db/migrate-client-profiles[-v2|-v3].py <db> --apply

Tests verify that applying v1, v2, v3 to a fresh 001-init DB produces the
server-equivalent schema, and that re-running is idempotent.

Run: python3 -m pytest tests/test_migrations.py -v
"""
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_DIR = os.path.join(ROOT, "infra", "db")


def run_sql_migration(db_path, sql_file):
    with open(sql_file, "rb") as f:
        subprocess.run(["sqlite3", db_path], stdin=f, check=True)


class MigrationTests(unittest.TestCase):
    """End-to-end reproducibility of client-profile migrations."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db = os.path.join(self.tmpdir, "factory.db")
        # Build a reproducible baseline from SQL migrations 001 + 002,
        # then apply Python client-profile migrations on top.
        run_sql_migration(self.db, os.path.join(SQL_DIR, "001_init.sql"))
        run_sql_migration(self.db, os.path.join(SQL_DIR, "002_sessions.sql"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, script):
        return subprocess.run(
            [sys.executable, os.path.join(SQL_DIR, script), self.db, "--apply"],
            capture_output=True, text=True
        )

    def _column_in(self, table, col):
        con = sqlite3.connect(self.db)
        try:
            cols = {r[1] for r in con.execute(f'PRAGMA table_info("{table}")')}
            return col in cols
        finally:
            con.close()

    def _version_in(self, ver):
        con = sqlite3.connect(self.db)
        try:
            row = con.execute(
                "SELECT 1 FROM schema_version WHERE version=?", (ver,)
            ).fetchone()
            return row is not None
        finally:
            con.close()

    def test_v1_adds_client_profile_columns_and_registers_version(self):
        r = self._run("migrate-client-profiles.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self._column_in("clients", "description"))
        self.assertTrue(self._column_in("clients", "context_links"))
        self.assertTrue(self._column_in("clients", "context_docs"))
        self.assertTrue(self._column_in("clients", "context_refs"))
        self.assertTrue(self._column_in("users", "active_client_id"))
        self.assertTrue(self._column_in("sessions", "profile_draft"))
        self.assertTrue(self._version_in(3))

    def test_v2_adds_publish_platforms_profile_questions(self):
        self._run("migrate-client-profiles.py")
        r = self._run("migrate-client-profiles-v2.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self._column_in("clients", "publish_platforms"))
        con = sqlite3.connect(self.db)
        try:
            row = con.execute(
                "SELECT value FROM settings WHERE key='profile_questions'"
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertIn("Как называется компания", row[0])
        finally:
            con.close()
        self.assertTrue(self._version_in(4))

    def test_v3_adds_auto_approve_and_quick_payload(self):
        self._run("migrate-client-profiles.py")
        self._run("migrate-client-profiles-v2.py")
        r = self._run("migrate-client-profiles-v3.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self._column_in("users", "auto_approve"))
        self.assertTrue(self._column_in("sessions", "quick_payload"))
        self.assertTrue(self._version_in(5))

    def test_all_migrations_are_idempotent(self):
        for _ in range(2):
            self.assertEqual(self._run("migrate-client-profiles.py").returncode, 0)
            self.assertEqual(self._run("migrate-client-profiles-v2.py").returncode, 0)
            self.assertEqual(self._run("migrate-client-profiles-v3.py").returncode, 0)
        self.assertTrue(self._version_in(5))


if __name__ == "__main__":
    unittest.main(verbosity=2)
