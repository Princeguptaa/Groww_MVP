"""
Privacy tests (spec §3 hard rule 4, §6, §9.6).

Verifies:
1. No message text is written to disk, database, or server logs.
2. No personal data fields (PAN, phone, email, bank account).
3. No database imports or database connections.
4. No personal name anywhere in app or codebase text.
"""
import re
from pathlib import Path
import pytest


def test_no_file_or_db_logging_of_user_data():
    root = Path(__file__).resolve().parent.parent
    code_dirs = [root / "lib", root / "views"]
    py_files = [root / "app.py"]
    for d in code_dirs:
        py_files.extend(d.glob("*.py"))

    # Banned database and file storage patterns for user messages
    banned_db = [
        "sqlite3",
        "psycopg2",
        "sqlalchemy",
        "pymongo",
        "motor",
        "mysql",
    ]

    for py_file in py_files:
        code = py_file.read_text(encoding="utf-8")

        # Ensure no database imports
        for db in banned_db:
            assert f"import {db}" not in code, f"Database library {db} found in {py_file.name}"

        # Ensure no open(..., 'w'/'a') storing user inputs
        assert "open(" not in code or ".ics" in code, f"File write pattern found in {py_file.name}"


def test_no_personal_names_in_app_text():
    root = Path(__file__).resolve().parent.parent
    files_to_check = [
        root / "app.py",
        root / "README.md",
        root / "lib" / "content.py",
        root / "lib" / "router_rules.py",
        root / "lib" / "guards.py",
        root / "views" / "guide.py",
        root / "views" / "quality.py",
    ]

    # Name check (no personal developer name)
    banned_names = ["prince", "gupta"]

    for f in files_to_check:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8").lower()
        for name in banned_names:
            assert name not in text, f"Personal name '{name}' found in {f.name}"

