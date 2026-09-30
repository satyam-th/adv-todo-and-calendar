"""
Lightweight Embedded HTTP & REST Server.
Serves modern web dashboard with Full Monthly Calendar Grid and REST API for tasks.db.
Zero external dependencies (uses standard library http.server).
"""

from __future__ import annotations
import os
import time
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import datetime
from typing import Optional

try:
    from app.database import Database
    from app.nepali_calendar import (
        get_dual_calendar, get_bs_month_calendar, get_ad_month_calendar,
        ad_to_bs, bs_to_ad
    )
    from app.countdown import calculate_task_urgency
    from app.parser import parse_quick_command
    from app.config import detect_monitors, AppConfig
    from app.notifier import (
        calculate_routine_status, check_and_notify_routines, test_routine_notification
    )
except ImportError:
    from database import Database
    from nepali_calendar import (
        get_dual_calendar, get_bs_month_calendar, get_ad_month_calendar,
        ad_to_bs, bs_to_ad
    )
    from countdown import calculate_task_urgency
    from parser import parse_quick_command
    from config import detect_monitors, AppConfig
    from notifier import (
        calculate_routine_status, check_and_notify_routines, test_routine_notification
    )

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

_shared_db: Optional[Database] = None

def get_shared_db() -> Database:
    global _shared_db
    if _shared_db is None:
        _shared_db = Database()
    return _shared_db

class DashboardApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def _send_json(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/calendar/dual":
            calendar_data = get_dual_calendar()
            self._send_json(calendar_data)
            return

        elif path == "/api/calendar/month/bs":
            now = datetime.date.today()
            bs_now = ad_to_bs(now.year, now.month, now.day)
            year = int(query.get("year", [bs_now[0]])[0])
            month = int(query.get("month", [bs_now[1]])[0])
            cal_data = get_bs_month_calendar(year, month)
            self._send_json(cal_data)
            return

        elif path == "/api/calendar/month/ad":
            now = datetime.date.today()
            year = int(query.get("year", [now.year])[0])
            month = int(query.get("month", [now.month])[0])
            cal_data = get_ad_month_calendar(year, month)
            self._send_json(cal_data)
            return

        elif path == "/api/tasks":
            db = get_shared_db()
            tasks = db.get_tasks()
            now = datetime.datetime.now()
            enriched = [calculate_task_urgency(t, now) for t in tasks]
            self._send_json(enriched)
            return

        elif path == "/api/notes":
            db = get_shared_db()
            date_param = query.get("date", [None])[0]
            notes = db.get_notes(date_param)
            self._send_json(notes)
            return

        elif path == "/api/diary/dates":
            db = get_shared_db()
            dates = db.get_diary_dates()
            self._send_json(dates)
            return

        elif path == "/api/routines":
            db = get_shared_db()
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            routines = db.get_routines(today_str)
            now = datetime.datetime.now()
            enriched = [calculate_routine_status(r, now) for r in routines]
            self._send_json(enriched)
            return

        elif path == "/api/monitors":
            monitors = detect_monitors()
            self._send_json(monitors)
            return

        elif path == "/api/health":
            self._send_json({"status": "ok", "timestamp": datetime.datetime.now().isoformat()})
            return

        # Fallback to static web files
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(length)
        payload = {}
        if post_data:
            try:
                payload = json.loads(post_data.decode("utf-8"))
            except Exception:
                pass

        db = get_shared_db()

        # Natural Language Quick Command Handler
        if path == "/api/add":
            raw_command = payload.get("command", "")
            if not raw_command:
                self._send_json({"error": "Empty command"}, status=400)
                return

            parsed_res = parse_quick_command(raw_command)
            if parsed_res["type"] == "note":
                note_id = db.create_note(content=parsed_res["content"])
                self._send_json({"type": "note", "id": note_id, "content": parsed_res["content"]}, status=201)
            elif parsed_res["type"] == "routine":
                routine_id = db.create_routine(
                    title=parsed_res["title"],
                    time_str=parsed_res["time_str"],
                    category=parsed_res.get("category", "routine"),
                    notify=parsed_res.get("notify", 1)
                )
                self._send_json({
                    "type": "routine",
                    "id": routine_id,
                    "title": parsed_res["title"],
                    "time_str": parsed_res["time_str"],
                    "category": parsed_res.get("category", "routine")
                }, status=201)
            else:
                task_id = db.create_task(
                    title=parsed_res["title"],
                    start_date=parsed_res["start_date"],
                    end_date=parsed_res["end_date"],
                    priority=parsed_res["priority"],
                    category=parsed_res["category"]
                )
                self._send_json({"type": "task", "id": task_id, "title": parsed_res["title"]}, status=201)
            return

        elif path == "/api/tasks":
            title = payload.get("title", "Untitled Task")
            now = datetime.datetime.now()
            start_d = payload.get("start_date", now.strftime("%Y-%m-%d"))
            end_d = payload.get("end_date", now.strftime("%Y-%m-%d 23:59:59"))
            priority = payload.get("priority", "normal")
            category = payload.get("category", "general")
            notes = payload.get("notes", "")

            task_id = db.create_task(title, start_d, end_d, priority, category, notes)
            self._send_json({"id": task_id, "title": title}, status=201)
            return

        elif path == "/api/notes":
            content = payload.get("content", "")
            date_s = payload.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))
            pinned = 1 if payload.get("is_pinned") else 0
            note_id = db.create_note(content, date_s, pinned)
            self._send_json({"id": note_id, "content": content}, status=201)
            return

        elif path == "/api/routines":
            title = payload.get("title", "Daily Routine")
            time_str = payload.get("time_str", "09:00")
            category = payload.get("category", "routine")
            notify = 1 if payload.get("notify", True) else 0
            days_of_week = payload.get("days_of_week", "0,1,2,3,4,5,6")
            r_id = db.create_routine(title, time_str, category, notify, days_of_week)
            self._send_json({"id": r_id, "title": title, "time_str": time_str, "category": category}, status=201)
            return

        elif path.startswith("/api/routines/") and path.endswith("/test"):
            parts = path.split("/")
            try:
                r_id = int(parts[3])
                r = db.get_routine(r_id)
                if r:
                    test_routine_notification(r["title"], r["time_str"])
                    self._send_json({"success": True, "id": r_id, "title": r["title"]})
                else:
                    self._send_json({"error": "Routine not found"}, status=404)
                return
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
                return

        self._send_json({"error": "Not Found"}, status=404)

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/tasks/") and path.endswith("/toggle"):
            parts = path.split("/")
            try:
                task_id = int(parts[3])
                db = get_shared_db()
                res = db.toggle_task(task_id)
                self._send_json(res)
                return
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
                return

        elif path.startswith("/api/routines/") and path.endswith("/toggle"):
            parts = path.split("/")
            try:
                r_id = int(parts[3])
                db = get_shared_db()
                res = db.toggle_routine_today(r_id)
                self._send_json(res)
                return
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
                return

        elif path.startswith("/api/routines/") and path.endswith("/notify"):
            parts = path.split("/")
            try:
                r_id = int(parts[3])
                db = get_shared_db()
                res = db.toggle_routine_notify(r_id)
                self._send_json(res)
                return
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
                return

        self._send_json({"error": "Not Found"}, status=404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/tasks/"):
            try:
                task_id = int(path.split("/")[-1])
                db = get_shared_db()
                deleted = db.delete_task(task_id)
                self._send_json({"success": deleted, "id": task_id})
                return
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
                return

        if path.startswith("/api/notes/"):
            try:
                note_id = int(path.split("/")[-1])
                db = get_shared_db()
                deleted = db.delete_note(note_id)
                self._send_json({"success": deleted, "id": note_id})
                return
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
                return

        if path.startswith("/api/routines/"):
            try:
                r_id = int(path.split("/")[-1])
                db = get_shared_db()
                deleted = db.delete_routine(r_id)
                self._send_json({"success": deleted, "id": r_id})
                return
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
                return

        self._send_json({"error": "Not Found"}, status=404)

def _start_routine_scheduler():
    def loop():
        db = get_shared_db()
        while True:
            try:
                check_and_notify_routines(db)
            except Exception as e:
                print(f"[RoutineScheduler] Error: {e}")
            time.sleep(10)

    sched_thread = threading.Thread(target=loop, daemon=True)
    sched_thread.start()

def start_server(port: int = 8765, host: str = "127.0.0.1", background: bool = False):
    _start_routine_scheduler()
    server = HTTPServer((host, port), DashboardApiHandler)
    print(f"[Server] Productivity Dashboard server running on http://{host}:{port}")
    if background:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server
    else:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[Server] Shutting down...")
            server.shutdown()
            server.server_close()

if __name__ == "__main__":
    start_server(port=8765, background=False)
