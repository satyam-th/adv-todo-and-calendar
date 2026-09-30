"""
Database module managing embedded SQLite database (tasks.db).
Stores tasks, deadlines, multi-day intervals, day-specific notes, and user settings.
"""

import os
import re
import sqlite3
import datetime
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tasks.db")

def normalize_routine_time(time_input: str) -> str:
    """Normalize user time inputs ('8am', '8:30', '14:30', '2pm') to HH:MM format."""
    s = str(time_input).strip().lower()
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", s)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        meridiem = m.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    return "09:00"

class Database:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        # WAL mode for high responsiveness and concurrent UI / server access
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        try:
            yield conn
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'normal',
                category TEXT NOT NULL DEFAULT 'general',
                is_completed INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                notes TEXT DEFAULT ''
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                content TEXT NOT NULL,
                is_pinned INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS routines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                time_str TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'routine',
                days_of_week TEXT NOT NULL DEFAULT '0,1,2,3,4,5,6',
                notify INTEGER NOT NULL DEFAULT 1,
                notify_offset_minutes INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS routine_completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                routine_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                UNIQUE(routine_id, date),
                FOREIGN KEY(routine_id) REFERENCES routines(id) ON DELETE CASCADE
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS routine_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                routine_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                notified_at TEXT NOT NULL,
                UNIQUE(routine_id, date),
                FOREIGN KEY(routine_id) REFERENCES routines(id) ON DELETE CASCADE
            );
            """)

            # Seed default tasks if brand new database
            cursor.execute("SELECT COUNT(*) FROM tasks;")
            count = cursor.fetchone()[0]
            if count == 0:
                self._seed_initial_data(cursor)

            cursor.execute("SELECT COUNT(*) FROM routines;")
            routine_count = cursor.fetchone()[0]
            if routine_count == 0:
                self._seed_initial_routines(cursor)
            conn.commit()

    def _seed_initial_routines(self, cursor: sqlite3.Cursor):
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        initial_routines = [
            ("Morning Planning & Standup", "09:00", "work", 1),
            ("Lunch Break & Hydration", "13:00", "health", 1),
            ("Code Review & Daily Sync", "16:30", "dev", 1),
            ("Daily Wrap-up & Tomorrow Goals", "18:30", "routine", 1),
        ]
        for title, time_str, category, notify in initial_routines:
            cursor.execute("""
            INSERT INTO routines (title, time_str, category, days_of_week, notify, notify_offset_minutes, is_active, created_at)
            VALUES (?, ?, ?, '0,1,2,3,4,5,6', ?, 0, 1, ?);
            """, (title, time_str, category, notify, now_str))

    def _seed_initial_data(self, cursor: sqlite3.Cursor):
        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # 1. Spanning multi-day project
        start_proj = today_str
        end_proj = (now + datetime.timedelta(days=12)).strftime("%Y-%m-%d 23:59:59")

        # 2. Approaching deadline (2 days away)
        end_review = (now + datetime.timedelta(days=2, hours=4)).strftime("%Y-%m-%d %H:%M:%S")

        # 3. Critical urgency (< 24 hours)
        end_urgent = (now + datetime.timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")

        # 4. Healthy buffer (> 3 days)
        end_healthy = (now + datetime.timedelta(days=7)).strftime("%Y-%m-%d 18:00:00")

        initial_tasks = [
            ("Finish project", start_proj, end_proj, "urgent", "project", 0, "Sprint deliverables & documentation"),
            ("Submit client milestone report", today_str, end_urgent, "urgent", "work", 0, "Final deck review before 4pm meeting"),
            ("Code review & merge staging PRs", today_str, end_review, "high", "dev", 0, "Review architecture changes for dual-screen"),
            ("System backup & archive sync", today_str, end_healthy, "normal", "general", 0, "Regular bi-weekly database backup")
        ]

        for title, start_d, end_d, prio, cat, comp, notes in initial_tasks:
            cursor.execute("""
            INSERT INTO tasks (title, start_date, end_date, priority, category, is_completed, created_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (title, start_d, end_d, prio, cat, comp, now_str, notes))

        initial_notes = [
            (today_str, "Today's Focus: Keep desktop productivity dashboard running on Screen 2. Monitor critical project deadlines.", 1, now_str, now_str),
            (today_str, "Sync with engineering team regarding Bikram Sambat date accuracy algorithm.", 0, now_str, now_str)
        ]

        for dt, content, pinned, c_at, u_at in initial_notes:
            cursor.execute("""
            INSERT INTO notes (date, content, is_pinned, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?);
            """, (dt, content, pinned, c_at, u_at))

    # --- Task Operations ---
    def create_task(self, title: str, start_date: str, end_date: str,
                    priority: str = "normal", category: str = "general",
                    notes: str = "") -> int:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO tasks (title, start_date, end_date, priority, category, is_completed, created_at, notes)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?);
            """, (title.strip(), start_date, end_date, priority.lower(), category.lower(), now_str, notes.strip()))
            conn.commit()
            return cursor.lastrowid

    def get_tasks(self, filter_type: str = "all") -> List[Dict[str, Any]]:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if filter_type == "completed":
                query = "SELECT * FROM tasks WHERE is_completed = 1 ORDER BY completed_at DESC, id DESC"
                cursor.execute(query)
            elif filter_type == "active":
                query = "SELECT * FROM tasks WHERE is_completed = 0 AND start_date <= ? ORDER BY end_date ASC"
                cursor.execute(query, (now_str,))
            elif filter_type == "urgent":
                cutoff_str = (datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d 23:59:59")
                query = "SELECT * FROM tasks WHERE is_completed = 0 AND (priority = 'urgent' OR priority = 'high' OR end_date <= ?) ORDER BY end_date ASC"
                cursor.execute(query, (cutoff_str,))
            else:
                # All: uncompleted first sorted by end_date, then completed
                query = "SELECT * FROM tasks ORDER BY is_completed ASC, end_date ASC"
                cursor.execute(query)

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?;", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def toggle_task(self, task_id: int) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_completed FROM tasks WHERE id = ?;", (task_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Task {task_id} not found")

            new_state = 0 if row["is_completed"] == 1 else 1
            completed_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_state == 1 else None

            cursor.execute("""
            UPDATE tasks SET is_completed = ?, completed_at = ? WHERE id = ?;
            """, (new_state, completed_at, task_id))
            conn.commit()
            return {"id": task_id, "is_completed": new_state, "completed_at": completed_at}

    def update_task(self, task_id: int, **kwargs) -> bool:
        allowed = {"title", "start_date", "end_date", "priority", "category", "notes"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        fields = [f"{k} = ?" for k in updates.keys()]
        values = list(updates.values()) + [task_id]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?;", values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_task(self, task_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    # --- Day-Specific Notes Operations ---
    def create_note(self, content: str, date_str: Optional[str] = None, is_pinned: int = 0) -> int:
        now = datetime.datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        if not date_str:
            date_str = now.strftime("%Y-%m-%d")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO notes (date, content, is_pinned, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?);
            """, (date_str, content.strip(), is_pinned, now_str, now_str))
            conn.commit()
            return cursor.lastrowid

    def get_notes(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if date_str:
                cursor.execute("""
                SELECT * FROM notes WHERE date = ? ORDER BY is_pinned DESC, id DESC;
                """, (date_str,))
            else:
                cursor.execute("""
                SELECT * FROM notes ORDER BY is_pinned DESC, date DESC, id DESC;
                """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_note(self, note_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?;", (note_id,))
            conn.commit()
            return cursor.rowcount > 0

    def update_note(self, note_id: int, content: str) -> bool:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE notes SET content = ?, updated_at = ? WHERE id = ?;
            """, (content.strip(), now_str, note_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_diary_dates(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT date, COUNT(*) as count, MAX(created_at) as last_updated
            FROM notes
            GROUP BY date
            ORDER BY date DESC;
            """)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # --- Daily Routine Operations ---
    def create_routine(self, title: str, time_str: str, category: str = "routine",
                       notify: int = 1, days_of_week: str = "0,1,2,3,4,5,6",
                       notify_offset_minutes: int = 0, is_active: int = 1) -> int:
        norm_time = normalize_routine_time(time_str)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO routines (title, time_str, category, days_of_week, notify, notify_offset_minutes, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (title.strip(), norm_time, category.strip().lower(), days_of_week, 1 if notify else 0, notify_offset_minutes, 1 if is_active else 0, now_str))
            conn.commit()
            return cursor.lastrowid

    def get_routines(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        if not date_str:
            date_str = datetime.date.today().strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT r.*,
                   CASE WHEN rc.id IS NOT NULL THEN 1 ELSE 0 END AS is_completed_today,
                   rc.completed_at,
                   CASE WHEN rn.id IS NOT NULL THEN 1 ELSE 0 END AS has_notified_today,
                   rn.notified_at
            FROM routines r
            LEFT JOIN routine_completions rc ON r.id = rc.routine_id AND rc.date = ?
            LEFT JOIN routine_notifications rn ON r.id = rn.routine_id AND rn.date = ?
            ORDER BY r.time_str ASC, r.id ASC;
            """, (date_str, date_str))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_routine(self, routine_id: int, date_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not date_str:
            date_str = datetime.date.today().strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT r.*,
                   CASE WHEN rc.id IS NOT NULL THEN 1 ELSE 0 END AS is_completed_today,
                   rc.completed_at,
                   CASE WHEN rn.id IS NOT NULL THEN 1 ELSE 0 END AS has_notified_today,
                   rn.notified_at
            FROM routines r
            LEFT JOIN routine_completions rc ON r.id = rc.routine_id AND rc.date = ?
            LEFT JOIN routine_notifications rn ON r.id = rn.routine_id AND rn.date = ?
            WHERE r.id = ?;
            """, (date_str, date_str, routine_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def toggle_routine_today(self, routine_id: int, date_str: Optional[str] = None) -> Dict[str, Any]:
        if not date_str:
            date_str = datetime.date.today().strftime("%Y-%m-%d")
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM routine_completions WHERE routine_id = ? AND date = ?;", (routine_id, date_str))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("DELETE FROM routine_completions WHERE routine_id = ? AND date = ?;", (routine_id, date_str))
                new_status = 0
                completed_at = None
            else:
                cursor.execute("""
                INSERT INTO routine_completions (routine_id, date, completed_at)
                VALUES (?, ?, ?);
                """, (routine_id, date_str, now_str))
                new_status = 1
                completed_at = now_str
            conn.commit()
            return {"id": routine_id, "is_completed_today": new_status, "completed_at": completed_at, "date": date_str}

    def toggle_routine_notify(self, routine_id: int) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT notify FROM routines WHERE id = ?;", (routine_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Routine {routine_id} not found")
            new_val = 0 if row["notify"] == 1 else 1
            cursor.execute("UPDATE routines SET notify = ? WHERE id = ?;", (new_val, routine_id))
            conn.commit()
            return {"id": routine_id, "notify": new_val}

    def toggle_routine_active(self, routine_id: int) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_active FROM routines WHERE id = ?;", (routine_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Routine {routine_id} not found")
            new_val = 0 if row["is_active"] == 1 else 1
            cursor.execute("UPDATE routines SET is_active = ? WHERE id = ?;", (new_val, routine_id))
            conn.commit()
            return {"id": routine_id, "is_active": new_val}

    def update_routine(self, routine_id: int, **kwargs) -> bool:
        allowed = {"title", "time_str", "category", "days_of_week", "notify", "notify_offset_minutes", "is_active"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        if "time_str" in updates:
            updates["time_str"] = normalize_routine_time(updates["time_str"])
        fields = [f"{k} = ?" for k in updates.keys()]
        values = list(updates.values()) + [routine_id]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE routines SET {', '.join(fields)} WHERE id = ?;", values)
            conn.commit()
            return cursor.rowcount > 0

    def delete_routine(self, routine_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM routine_completions WHERE routine_id = ?;", (routine_id,))
            cursor.execute("DELETE FROM routine_notifications WHERE routine_id = ?;", (routine_id,))
            cursor.execute("DELETE FROM routines WHERE id = ?;", (routine_id,))
            conn.commit()
            return cursor.rowcount > 0

    def record_routine_notification(self, routine_id: int, date_str: Optional[str] = None) -> bool:
        if not date_str:
            date_str = datetime.date.today().strftime("%Y-%m-%d")
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO routine_notifications (routine_id, date, notified_at)
            VALUES (?, ?, ?)
            ON CONFLICT(routine_id, date) DO UPDATE SET notified_at = excluded.notified_at;
            """, (routine_id, date_str, now_str))
            conn.commit()
            return True

    def has_routine_been_notified(self, routine_id: int, date_str: Optional[str] = None) -> bool:
        if not date_str:
            date_str = datetime.date.today().strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM routine_notifications WHERE routine_id = ? AND date = ?;", (routine_id, date_str))
            return cursor.fetchone() is not None

    # --- Settings Operations ---
    def get_setting(self, key: str, default: Any = None) -> Any:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?;", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value;
            """, (key, str(value)))
            conn.commit()

if __name__ == "__main__":
    db = Database()
    tasks = db.get_tasks()
    print(f"Database initialized at: {db.db_path}")
    print(f"Loaded {len(tasks)} sample tasks:")
    for t in tasks:
        print(f"  [{t['priority'].upper()}] {t['title']} ({t['start_date']} -> {t['end_date']})")
    notes = db.get_notes()
    print(f"Loaded {len(notes)} notes.")
