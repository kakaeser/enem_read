"""
Migration: fix_schema_constraints.py

Recreates participantes, questoes, and resultados tables with:
  - Proper INTEGER PRIMARY KEY (autoincrement) on all tables
  - FOREIGN KEY constraints with ON DELETE CASCADE
  - Unique constraints and indexes matching the ORM models

Run from the project root:
    python -m backend.migrations.fix_schema_constraints

Safe to run multiple times (checks if migration is already applied).
"""

import sqlite3
import shutil
import os
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database.db")
DB_PATH = os.path.normpath(DB_PATH)


def backup(db_path: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path + f".backup_{ts}"
    shutil.copy2(db_path, backup_path)
    print(f"Backup created: {backup_path}")
    return backup_path


def already_migrated(cur: sqlite3.Cursor) -> bool:
    """Return True if resultados already has a proper INTEGER PRIMARY KEY."""
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='resultados'")
    row = cur.fetchone()
    if row is None:
        return False
    sql = row[0].upper()
    # Old broken schema has 'id INT' without PRIMARY KEY in the column definition
    return "INTEGER NOT NULL" in sql or "INTEGER PRIMARY KEY" in sql


def run():
    print(f"Database: {DB_PATH}")
    backup(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    if already_migrated(cur):
        print("Migration already applied — nothing to do.")
        conn.close()
        return

    print("Applying schema migration...")

    # Enable FK enforcement for this connection
    conn.execute("PRAGMA foreign_keys=OFF")  # OFF during migration to avoid constraint errors

    try:
        # ----------------------------------------------------------------
        # 0. Clean up any partial state from a previous failed run
        # ----------------------------------------------------------------
        for tbl in ("resultados_old", "questoes_old", "participantes_old"):
            cur.execute(f"DROP TABLE IF EXISTS {tbl}")

        # ----------------------------------------------------------------
        # 1. Rename old tables to _old
        # ----------------------------------------------------------------
        cur.execute("ALTER TABLE resultados RENAME TO resultados_old")
        cur.execute("ALTER TABLE questoes RENAME TO questoes_old")
        cur.execute("ALTER TABLE participantes RENAME TO participantes_old")

        # ----------------------------------------------------------------
        # 2. Create new tables with correct schema
        # ----------------------------------------------------------------
        cur.execute("""
            CREATE TABLE participantes (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL REFERENCES exams(exam_id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                presente BOOLEAN DEFAULT 0,
                essay_points FLOAT DEFAULT 0.0
            )
        """)

        cur.execute("""
            CREATE TABLE questoes (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL REFERENCES exams(exam_id) ON DELETE CASCADE,
                numero INTEGER NOT NULL,
                peso INTEGER DEFAULT 1,
                question_correct_answer VARCHAR(10),
                UNIQUE (exam_id, numero)
            )
        """)

        cur.execute("""
            CREATE TABLE resultados (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES participantes(id) ON DELETE CASCADE,
                quest_id INTEGER NOT NULL REFERENCES questoes(id) ON DELETE CASCADE,
                exam_id INTEGER NOT NULL REFERENCES exams(exam_id) ON DELETE CASCADE,
                marked_answer VARCHAR(10),
                confidence_score REAL,
                manually_reviewed BOOLEAN DEFAULT 0,
                UNIQUE (user_id, quest_id)
            )
        """)

        # ----------------------------------------------------------------
        # 3. Copy data from old tables
        # ----------------------------------------------------------------
        cur.execute("""
            INSERT INTO participantes (id, exam_id, nome, presente, essay_points)
            SELECT id, exam_id, nome, presente, essay_points FROM participantes_old
        """)
        p_count = cur.rowcount
        print(f"  Migrated {p_count} participantes rows")

        # Deduplicate: keep the row with the highest id for each (exam_id, numero) pair
        cur.execute("""
            INSERT INTO questoes (id, exam_id, numero, peso, question_correct_answer)
            SELECT id, exam_id, numero, peso, question_correct_answer
            FROM questoes_old
            WHERE id IN (
                SELECT MAX(id) FROM questoes_old GROUP BY exam_id, numero
            )
        """)
        q_count = cur.rowcount
        print(f"  Migrated {q_count} questoes rows (deduplicated)")

        # resultados: skip rows with NULL id or broken FK references
        cur.execute("""
            INSERT INTO resultados (id, user_id, quest_id, exam_id, marked_answer, confidence_score, manually_reviewed)
            SELECT r.id, r.user_id, r.quest_id, r.exam_id, r.marked_answer, r.confidence_score, r.manually_reviewed
            FROM resultados_old r
            WHERE r.id IS NOT NULL
              AND r.user_id IS NOT NULL
              AND r.quest_id IS NOT NULL
              AND r.exam_id IS NOT NULL
              AND EXISTS (SELECT 1 FROM participantes p WHERE p.id = r.user_id)
              AND EXISTS (SELECT 1 FROM questoes q WHERE q.id = r.quest_id)
        """)
        r_count = cur.rowcount
        print(f"  Migrated {r_count} resultados rows")

        # ----------------------------------------------------------------
        # 4. Recreate indexes
        # ----------------------------------------------------------------
        cur.execute("CREATE INDEX IF NOT EXISTS idx_exam_participants ON participantes(exam_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_exam_questions ON questoes(exam_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_exam_responses ON resultados(exam_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_participant_responses ON resultados(user_id)")

        # ----------------------------------------------------------------
        # 5. Drop old tables
        # ----------------------------------------------------------------
        cur.execute("DROP TABLE resultados_old")
        cur.execute("DROP TABLE questoes_old")
        cur.execute("DROP TABLE participantes_old")

        conn.commit()
        print("Migration complete.")

    except Exception as e:
        conn.rollback()
        print(f"Migration FAILED: {e}")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()


if __name__ == "__main__":
    run()
