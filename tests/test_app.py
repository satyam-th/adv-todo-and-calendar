"""
Complete Test Suite for Apex Productivity Dashboard.
Verifies Bikram Sambat conversions, SQLite CRUD, Natural Language parser, and Urgency engine.
"""

import os
import sys
import unittest
import datetime

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.nepali_calendar import (
    ad_to_bs, bs_to_ad, to_devanagari_num, get_dual_calendar,
    get_bs_month_calendar, get_ad_month_calendar
)
from app.database import Database, normalize_routine_time
from app.parser import parse_quick_command, parse_single_date
from app.countdown import calculate_task_urgency
from app.config import AppConfig, detect_monitors
from app.notifier import (
    calculate_routine_status, check_and_notify_routines,
    format_time_12h, test_routine_notification
)

class TestNepaliCalendar(unittest.TestCase):
    def test_current_date_conversion(self):
        # 2026-09-08 AD is 2083 Bhadra 23 BS
        dt = datetime.date(2026, 9, 8)
        bs = ad_to_bs(dt)
        self.assertEqual(bs["year"], 2083)
        self.assertEqual(bs["month"], 5)
        self.assertEqual(bs["day"], 23)
        self.assertEqual(bs["month_name_en"], "Bhadra")
        self.assertEqual(bs["formatted_en"], "23 Bhadra 2083")
        self.assertEqual(bs["year_np"], "२०८३")
        self.assertEqual(bs["day_np"], "२३")

    def test_roundtrip_conversion(self):
        # BS -> AD -> BS
        ad_date = bs_to_ad(2083, 5, 23)
        self.assertEqual(ad_date, datetime.date(2026, 9, 8))

        bs_converted = ad_to_bs(ad_date)
        self.assertEqual((bs_converted["year"], bs_converted["month"], bs_converted["day"]), (2083, 5, 23))

    def test_anchor_date(self):
        # 1975-01-01 BS = 1918-04-13 AD
        ad = bs_to_ad(1975, 1, 1)
        self.assertEqual(ad, datetime.date(1918, 4, 13))
        bs = ad_to_bs(datetime.date(1918, 4, 13))
        self.assertEqual((bs["year"], bs["month"], bs["day"]), (1975, 1, 1))

    def test_devanagari_numbers(self):
        self.assertEqual(to_devanagari_num(2083), "२०८३")
        self.assertEqual(to_devanagari_num(23), "२३")

    def test_dual_calendar_structure(self):
        dual = get_dual_calendar(datetime.datetime(2026, 9, 8, 9, 0, 0))
        self.assertIn("ad", dual)
        self.assertIn("bs", dual)
        self.assertEqual(dual["ad"]["year"], 2026)
        self.assertEqual(dual["bs"]["year"], 2083)

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "/tmp/test_tasks.db"
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = Database(self.test_db_path)

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_task_lifecycle(self):
        tid = self.db.create_task(
            title="Deploy release",
            start_date="2026-09-08",
            end_date="2026-09-20 23:59:59",
            priority="urgent",
            category="work"
        )
        task = self.db.get_task(tid)
        self.assertIsNotNone(task)
        self.assertEqual(task["title"], "Deploy release")
        self.assertEqual(task["priority"], "urgent")
        self.assertEqual(task["is_completed"], 0)

        # Toggle completion
        res = self.db.toggle_task(tid)
        self.assertEqual(res["is_completed"], 1)
        task = self.db.get_task(tid)
        self.assertEqual(task["is_completed"], 1)

        self.assertTrue(self.db.delete_task(tid))
        self.assertIsNone(self.db.get_task(tid))

    def test_active_and_urgent_filtering(self):
        now = datetime.datetime.now()
        # Task 1: active task started today
        t1 = self.db.create_task("Active today", (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d 09:00:00"), (now + datetime.timedelta(days=5)).strftime("%Y-%m-%d 23:59:59"), "normal")
        # Task 2: future task starting in 5 days
        t2 = self.db.create_task("Future task", (now + datetime.timedelta(days=5)).strftime("%Y-%m-%d 00:00:00"), (now + datetime.timedelta(days=10)).strftime("%Y-%m-%d 23:59:59"), "normal")
        # Task 3: urgent task started today
        t3 = self.db.create_task("Urgent task", (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d 09:00:00"), (now + datetime.timedelta(days=2)).strftime("%Y-%m-%d 23:59:59"), "urgent")

        active_tasks = self.db.get_tasks("active")
        active_ids = [t["id"] for t in active_tasks]
        self.assertIn(t1, active_ids)
        self.assertIn(t3, active_ids)
        self.assertNotIn(t2, active_ids, "Future task starting 5 days later must not be in active tasks")

        urgent_tasks = self.db.get_tasks("urgent")
        urgent_ids = [t["id"] for t in urgent_tasks]
        self.assertIn(t3, urgent_ids, "Urgent task must be in urgent tasks")

        all_tasks = self.db.get_tasks("all")
        all_ids = [t["id"] for t in all_tasks]
        self.assertIn(t1, all_ids)
        self.assertIn(t2, all_ids, "Future task must be shown in all tasks")
        self.assertIn(t3, all_ids)

    def test_notes_lifecycle(self):
        nid = self.db.create_note("Test note contents", "2026-09-08", is_pinned=1)
        notes = self.db.get_notes("2026-09-08")
        self.assertTrue(any(n["id"] == nid for n in notes))

        self.assertTrue(self.db.delete_note(nid))
        notes_after = self.db.get_notes("2026-09-08")
        self.assertFalse(any(n["id"] == nid for n in notes_after))

class TestParser(unittest.TestCase):
    def setUp(self):
        self.now = datetime.datetime(2026, 9, 8, 9, 0, 0)

    def test_range_and_priority_parsing(self):
        cmd = "Finish project from Sept 8 to Sept 20 #urgent"
        res = parse_quick_command(cmd, now=self.now)
        self.assertEqual(res["type"], "task")
        self.assertEqual(res["title"], "Finish project")
        self.assertEqual(res["priority"], "urgent")
        self.assertTrue(res["start_date"].startswith("2026-09-08"))
        self.assertTrue(res["end_date"].startswith("2026-09-20"))

    def test_deadline_and_category_parsing(self):
        cmd = "Submit tax report by Sept 12 #high @finance"
        res = parse_quick_command(cmd, now=self.now)
        self.assertEqual(res["type"], "task")
        self.assertEqual(res["title"], "Submit tax report")
        self.assertEqual(res["priority"], "high")
        self.assertEqual(res["category"], "finance")
        self.assertTrue(res["end_date"].startswith("2026-09-12"))

    def test_note_command(self):
        cmd = "/note Standup sync: all migrations completed"
        res = parse_quick_command(cmd, now=self.now)
        self.assertEqual(res["type"], "note")
        self.assertEqual(res["content"], "Standup sync: all migrations completed")

class TestCountdownUrgency(unittest.TestCase):
    def setUp(self):
        self.now = datetime.datetime(2026, 9, 8, 12, 0, 0)

    def test_critical_urgency(self):
        # 6 hours left -> Critical (< 24h)
        end_str = (self.now + datetime.timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
        task = {"id": 1, "title": "Urgent bug", "start_date": "2026-09-08", "end_date": end_str, "is_completed": 0}
        res = calculate_task_urgency(task, self.now)
        self.assertEqual(res["urgency"], "critical")
        self.assertIn("badge-critical", res["badge_class"])
        self.assertIn("left!", res["badge_text"])

    def test_warning_urgency(self):
        # 2 days left -> Warning (1 to 3 days)
        end_str = (self.now + datetime.timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        task = {"id": 2, "title": "Review PR", "start_date": "2026-09-08", "end_date": end_str, "is_completed": 0}
        res = calculate_task_urgency(task, self.now)
        self.assertEqual(res["urgency"], "warning")
        self.assertEqual(res["badge_text"], "2 days left")

    def test_healthy_urgency(self):
        # 10 days left -> Healthy (> 3 days)
        end_str = (self.now + datetime.timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        task = {"id": 3, "title": "Project sprint", "start_date": "2026-09-08", "end_date": end_str, "is_completed": 0}
        res = calculate_task_urgency(task, self.now)
        self.assertEqual(res["urgency"], "healthy")
        self.assertEqual(res["badge_text"], "10 days left")

    def test_overdue_urgency(self):
        # Past deadline
        end_str = (self.now - datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        task = {"id": 4, "title": "Past task", "start_date": "2026-09-07", "end_date": end_str, "is_completed": 0}
        res = calculate_task_urgency(task, self.now)
        self.assertEqual(res["urgency"], "overdue")

    def test_range_support(self):
        task = {
            "id": 5,
            "title": "Multi-day project",
            "start_date": "2026-09-08 00:00:00",
            "end_date": "2026-09-20 23:59:59",
            "is_completed": 0
        }
        res = calculate_task_urgency(task, self.now)
        self.assertTrue(res["is_multi_day"])
        self.assertEqual(res["range_tag"], "Sep 08 → Sep 20")
        self.assertTrue(res["is_active_range"])

    def test_upcoming_task(self):
        # Starts 5 days in the future
        start_str = (self.now + datetime.timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
        end_str = (self.now + datetime.timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        task = {
            "id": 6,
            "title": "Account exam",
            "start_date": start_str,
            "end_date": end_str,
            "priority": "normal",
            "is_completed": 0
        }
        res = calculate_task_urgency(task, self.now)
        self.assertTrue(res["is_upcoming"])
        self.assertFalse(res["is_active"])
        self.assertIn("Starts in 5 days", res["countdown_text"])
        self.assertEqual(res["badge_class"], "badge-upcoming")

    def test_urgent_priority_with_future_deadline(self):
        # 5 days left, but priority is urgent
        start_str = self.now.strftime("%Y-%m-%d %H:%M:%S")
        end_str = (self.now + datetime.timedelta(days=5)).strftime("%Y-%m-%d 23:59:59")
        task = {
            "id": 7,
            "title": "DCN exam",
            "start_date": start_str,
            "end_date": end_str,
            "priority": "urgent",
            "is_completed": 0
        }
        res = calculate_task_urgency(task, self.now)
        self.assertFalse(res["is_upcoming"])
        self.assertTrue(res["is_active"])
        self.assertTrue(res["is_urgent"])
        self.assertEqual(res["urgency"], "critical")
        self.assertIn("badge-critical", res["badge_class"])
        self.assertIn("Urgent", res["badge_text"])

class TestCalendarGrid(unittest.TestCase):
    def test_full_monthly_calendar_generation(self):
        test_today = datetime.date(2026, 9, 8)
        # Test BS monthly grid for Bhadra 2083
        bs_cal = get_bs_month_calendar(2083, 5, today=test_today)
        self.assertEqual(bs_cal["month_name_en"], "Bhadra")
        self.assertEqual(bs_cal["total_days"], 31)
        self.assertEqual(len(bs_cal["cells"]), 32) # 1 leading empty + 31 days

        # Verify today (Bhadra 23, 2083) is marked is_today
        today_cell = [c for c in bs_cal["cells"] if c and c.get("is_today")]
        self.assertTrue(len(today_cell) > 0)
        self.assertEqual(today_cell[0]["bs_day"], 23)
        self.assertEqual(today_cell[0]["ad_day"], 8)

        # Test AD monthly grid for September 2026
        ad_cal = get_ad_month_calendar(2026, 9, today=test_today)
        self.assertEqual(ad_cal["month_name"], "September")
        self.assertEqual(ad_cal["total_days"], 30)
        today_ad_cell = [c for c in ad_cal["cells"] if c and c.get("is_today")]
        self.assertTrue(len(today_ad_cell) > 0)
        self.assertEqual(today_ad_cell[0]["ad_day"], 8)
        self.assertEqual(today_ad_cell[0]["bs_day"], 23)

class TestRoutines(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "/tmp/test_routines_unit.db"
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = Database(self.test_db_path)

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_routine_crud_lifecycle(self):
        # Create
        rid = self.db.create_routine("Morning Meditation", "07:30", "health", notify=1)
        self.assertIsNotNone(rid)

        # Retrieve
        routines = self.db.get_routines()
        match = [r for r in routines if r["id"] == rid]
        self.assertEqual(len(match), 1)
        r = match[0]
        self.assertEqual(r["title"], "Morning Meditation")
        self.assertEqual(r["time_str"], "07:30")
        self.assertEqual(r["category"], "health")
        self.assertEqual(r["is_completed_today"], 0)
        self.assertEqual(r["notify"], 1)

        # Toggle completed today
        res = self.db.toggle_routine_today(rid)
        self.assertEqual(res["is_completed_today"], 1)
        r_after = self.db.get_routine(rid)
        self.assertEqual(r_after["is_completed_today"], 1)

        # Toggle again -> incomplete
        res2 = self.db.toggle_routine_today(rid)
        self.assertEqual(res2["is_completed_today"], 0)

        # Toggle notification
        res_notify = self.db.toggle_routine_notify(rid)
        self.assertEqual(res_notify["notify"], 0)

        # Delete
        self.assertTrue(self.db.delete_routine(rid))
        self.assertIsNone(self.db.get_routine(rid))

    def test_normalize_routine_time(self):
        self.assertEqual(normalize_routine_time("8:30"), "08:30")
        self.assertEqual(normalize_routine_time("08:30"), "08:30")
        self.assertEqual(normalize_routine_time("9am"), "09:00")
        self.assertEqual(normalize_routine_time("9:15am"), "09:15")
        self.assertEqual(normalize_routine_time("2pm"), "14:00")
        self.assertEqual(normalize_routine_time("4:45pm"), "16:45")
        self.assertEqual(normalize_routine_time("18:00"), "18:00")

    def test_routine_parser(self):
        now = datetime.datetime(2026, 9, 20, 9, 0, 0)
        cmd1 = "/routine 08:30 Morning Workout #health"
        res1 = parse_quick_command(cmd1, now=now)
        self.assertEqual(res1["type"], "routine")
        self.assertEqual(res1["title"], "Morning Workout")
        self.assertEqual(res1["time_str"], "08:30")
        self.assertEqual(res1["category"], "health")

        cmd2 = "routine: at 3pm Afternoon Coffee Break @work"
        res2 = parse_quick_command(cmd2, now=now)
        self.assertEqual(res2["type"], "routine")
        self.assertEqual(res2["title"], "Afternoon Coffee Break")
        self.assertEqual(res2["time_str"], "15:00")
        self.assertEqual(res2["category"], "work")

        cmd3 = "/routine 10:00 Daily Team Standup"
        res3 = parse_quick_command(cmd3, now=now)
        self.assertEqual(res3["type"], "routine")
        self.assertEqual(res3["title"], "Daily Team Standup")
        self.assertEqual(res3["time_str"], "10:00")
        self.assertEqual(res3["category"], "routine")

    def test_routine_status_and_notification(self):
        now = datetime.datetime(2026, 9, 20, 9, 0, 0)

        # 1. Routine due right now
        r_due = {"id": 1, "title": "Standup", "time_str": "09:00", "category": "work", "is_completed_today": 0}
        st_due = calculate_routine_status(r_due, now=now)
        self.assertEqual(st_due["status"], "due_now")
        self.assertTrue(st_due["is_due_now"])
        self.assertIn("Due Now", st_due["badge_text"])

        # 2. Routine upcoming later today
        r_up = {"id": 2, "title": "Lunch", "time_str": "12:30", "category": "health", "is_completed_today": 0}
        st_up = calculate_routine_status(r_up, now=now)
        self.assertEqual(st_up["status"], "upcoming")
        self.assertIn("3h 30m", st_up["badge_text"])

        # 3. Notification dispatch and duplicate prevention
        rid = self.db.create_routine("Morning Stretch", "09:00", "health", notify=1)
        notified = check_and_notify_routines(self.db, now=now)
        self.assertTrue(any(n["id"] == rid for n in notified))

        # Check that it won't notify again on the same day
        notified_again = check_and_notify_routines(self.db, now=now)
        self.assertFalse(any(n["id"] == rid for n in notified_again))

    def test_routine_subfilter_completion_rule(self):
        """
        User explicit requirement:
        'if daily routine task complete then that should not show in all'
        """
        now = datetime.datetime(2026, 9, 20, 9, 0, 0)
        today_str = now.strftime("%Y-%m-%d")

        r1 = self.db.create_routine("Yoga", "07:00", "health")
        r2 = self.db.create_routine("Standup", "09:00", "work")
        r3 = self.db.create_routine("Reading", "21:00", "study")

        # Mark r1 as completed today
        self.db.toggle_routine_today(r1, today_str)

        all_routines = self.db.get_routines(today_str)
        enriched = [calculate_routine_status(r, now) for r in all_routines]

        # Rule implementation test:
        uncompleted_in_all = [r for r in enriched if not r.get("is_completed_today")]
        completed_in_done = [r for r in enriched if r.get("is_completed_today")]

        # r1 is completed, so it MUST NOT be in 'All'
        self.assertFalse(any(r["id"] == r1 for r in uncompleted_in_all))
        # r2 and r3 are uncompleted, so they MUST be in 'All'
        self.assertTrue(any(r["id"] == r2 for r in uncompleted_in_all))
        self.assertTrue(any(r["id"] == r3 for r in uncompleted_in_all))

        # r1 MUST be in 'Done'
        self.assertTrue(any(r["id"] == r1 for r in completed_in_done))
        self.assertEqual(len(completed_in_done), 1)

    def test_diary_date_queries(self):
        # Create notes across multiple dates
        self.db.create_note("Thought 1", date_str="2026-09-18")
        self.db.create_note("Thought 2", date_str="2026-09-18")
        self.db.create_note("Thought 3", date_str="2026-09-19")
        self.db.create_note("Thought 4", date_str="2026-09-25")

        # Query by date
        notes_18 = self.db.get_notes(date_str="2026-09-18")
        self.assertEqual(len(notes_18), 2)
        self.assertTrue(all(n["date"] == "2026-09-18" for n in notes_18))

        notes_19 = self.db.get_notes(date_str="2026-09-19")
        self.assertEqual(len(notes_19), 1)
        self.assertEqual(notes_19[0]["content"], "Thought 3")

        # Query distinct diary dates
        diary_dates = self.db.get_diary_dates()
        dates_map = {d["date"]: d["count"] for d in diary_dates}
        self.assertIn("2026-09-18", dates_map)
        self.assertEqual(dates_map["2026-09-18"], 2)
        self.assertEqual(dates_map["2026-09-19"], 1)
        self.assertEqual(dates_map["2026-09-25"], 1)

    def test_server_diary_and_routine_endpoints(self):
        from app.server import start_server
        import urllib.request
        import json

        port = 8769
        srv = start_server(port=port, host="127.0.0.1", background=True)
        try:
            # 1. Test GET /api/diary/dates
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/diary/dates")
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode())
                self.assertIsInstance(data, list)

            # 2. Test POST /api/notes with date
            body = json.dumps({"content": "HTTP server diary test", "date": "2026-09-22"}).encode()
            post_req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/notes",
                data=body,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(post_req) as resp:
                self.assertEqual(resp.status, 201)

            # 3. Test GET /api/notes?date=2026-09-22
            get_req = urllib.request.Request(f"http://127.0.0.1:{port}/api/notes?date=2026-09-22")
            with urllib.request.urlopen(get_req) as resp:
                self.assertEqual(resp.status, 200)
                notes = json.loads(resp.read().decode())
                self.assertTrue(any(n["content"] == "HTTP server diary test" for n in notes))

            # 4. Test GET /api/routines
            r_req = urllib.request.Request(f"http://127.0.0.1:{port}/api/routines")
            with urllib.request.urlopen(r_req) as resp:
                self.assertEqual(resp.status, 200)
                routines = json.loads(resp.read().decode())
                self.assertIsInstance(routines, list)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_task_urgency_rollover_and_yesterday(self):
        from app.countdown import calculate_task_urgency
        now = datetime.datetime(2026, 9, 29, 12, 0, 0)

        # 1. Overdue from yesterday (deadline 2026-09-28 18:00:00)
        t_yesterday = {
            "id": 101,
            "title": "Yesterday task",
            "start_date": "2026-09-25 00:00:00",
            "end_date": "2026-09-28 18:00:00",
            "priority": "normal",
            "category": "work",
            "is_completed": 0
        }
        res_y = calculate_task_urgency(t_yesterday, now=now)
        self.assertTrue(res_y["is_overdue"])
        self.assertTrue(res_y["is_from_yesterday"])
        self.assertEqual(res_y["overdue_days"], 1)
        self.assertEqual(res_y["overdue_label"], "Remaining from yesterday (-1d)")
        self.assertEqual(res_y["urgency"], "overdue")

        # 2. Overdue from 3 days ago (deadline 2026-09-26 18:00:00)
        t_past = {
            "id": 102,
            "title": "Old task",
            "start_date": "2026-09-20 00:00:00",
            "end_date": "2026-09-26 18:00:00",
            "priority": "normal",
            "category": "work",
            "is_completed": 0
        }
        res_p = calculate_task_urgency(t_past, now=now)
        self.assertTrue(res_p["is_overdue"])
        self.assertFalse(res_p["is_from_yesterday"])
        self.assertEqual(res_p["overdue_days"], 3)
        self.assertEqual(res_p["overdue_label"], "Remaining from -3d")

        # 3. Active task due tomorrow
        t_active = {
            "id": 103,
            "title": "Tomorrow task",
            "start_date": "2026-09-28 00:00:00",
            "end_date": "2026-09-30 18:00:00",
            "priority": "normal",
            "category": "work",
            "is_completed": 0
        }
        res_a = calculate_task_urgency(t_active, now=now)
        self.assertFalse(res_a["is_overdue"])
        self.assertEqual(res_a["overdue_days"], 0)
        self.assertEqual(res_a["overdue_label"], "")

    def test_task_completed_lifecycle_and_all_filtering(self):
        from app.countdown import calculate_task_urgency
        now = datetime.datetime(2026, 9, 29, 12, 0, 0)
        today_str = "2026-09-29"
        yesterday_str = "2026-09-28"

        # 1. Task completed today
        t_done_today = {
            "id": 201,
            "title": "Done today",
            "start_date": "2026-09-28 09:00:00",
            "end_date": "2026-09-29 18:00:00",
            "priority": "normal",
            "category": "work",
            "is_completed": 1,
            "completed_at": "2026-09-29 10:30:00"
        }
        res_dt = calculate_task_urgency(t_done_today, now=now)
        self.assertTrue(res_dt["is_completed_today"])

        # 2. Task completed yesterday
        t_done_yesterday = {
            "id": 202,
            "title": "Done yesterday",
            "start_date": "2026-09-27 09:00:00",
            "end_date": "2026-09-28 18:00:00",
            "priority": "normal",
            "category": "work",
            "is_completed": 1,
            "completed_at": "2026-09-28 16:00:00"
        }
        res_dy = calculate_task_urgency(t_done_yesterday, now=now)
        self.assertFalse(res_dy["is_completed_today"])

        # 3. Uncompleted overdue task
        t_overdue = {
            "id": 203,
            "title": "Incomplete task from yesterday",
            "start_date": "2026-09-27 09:00:00",
            "end_date": "2026-09-28 18:00:00",
            "priority": "normal",
            "category": "work",
            "is_completed": 0,
            "completed_at": None
        }
        res_od = calculate_task_urgency(t_overdue, now=now)

        all_tasks = [res_dt, res_dy, res_od]

        # Verify "All" view filter rule:
        # Uncompleted tasks + tasks completed TODAY.
        # Tasks completed yesterday or earlier must be excluded from "All".
        filtered_all = [
            t for t in all_tasks
            if not t["is_completed"] or t.get("is_completed_today") or ((t.get("completed_at") or "").startswith(today_str))
        ]
        self.assertEqual(len(filtered_all), 2)
        self.assertIn(res_dt, filtered_all, "Today's completed task must appear in All")
        self.assertIn(res_od, filtered_all, "Incomplete rollover task must appear in All")
        self.assertNotIn(res_dy, filtered_all, "Yesterday's completed task must NOT appear in All")

        # Verify Done filter: both completed tasks appear in Done
        done_tasks = [t for t in all_tasks if t["is_completed"]]
        self.assertEqual(len(done_tasks), 2)
        self.assertIn(res_dt, done_tasks)
        self.assertIn(res_dy, done_tasks)

        # Verify calendar day click for yesterday (2026-09-28):
        # Shows tasks active or completed on that day!
        filtered_yesterday = [
            t for t in all_tasks
            if ((t.get("start_date") or "")[:10] <= yesterday_str <= (t.get("end_date") or "9999-99-99")[:10])
            or ((t.get("completed_at") or "").startswith(yesterday_str))
            or ((t.get("end_date") or "")[:10] == yesterday_str)
        ]
        self.assertIn(res_dy, filtered_yesterday, "Yesterday's completed task must show when clicking yesterday on calendar")
        self.assertIn(res_od, filtered_yesterday, "Yesterday's incomplete task must show when clicking yesterday on calendar")

    def test_today_focus_routines_and_tasks_filtering(self):
        from app.notifier import calculate_routine_status
        from app.countdown import calculate_task_urgency
        now = datetime.datetime(2026, 9, 29, 12, 0, 0)
        today_str = "2026-09-29"

        # 1. Routines: 1 completed today, 1 uncompleted today
        r1_id = self.db.create_routine("Morning meditation", "07:00", "mindfulness")
        r2_id = self.db.create_routine("Evening reading", "21:00", "study")

        # Mark r1 completed today
        self.db.toggle_routine_today(r1_id, date_str=today_str)

        routines = self.db.get_routines(today_str)
        enriched_routines = [calculate_routine_status(r, now) for r in routines]
        remaining_routines = [r for r in enriched_routines if not r.get("is_completed_today")]

        remaining_ids = [r["id"] for r in remaining_routines]
        self.assertIn(r2_id, remaining_ids)
        self.assertNotIn(r1_id, remaining_ids)
        self.assertFalse(any(r["id"] == r1_id for r in remaining_routines))

        # 2. Tasks: Incomplete rollover from yesterday + Incomplete active today + Completed task
        t_roll_id = self.db.create_task("Fix bug from yesterday", "2026-09-27", "2026-09-28")
        t_active_id = self.db.create_task("Write docs today", "2026-09-29", "2026-09-29")
        t_done_id = self.db.create_task("Old done task", "2026-09-25", "2026-09-26")
        self.db.toggle_task(t_done_id)

        all_raw_tasks = self.db.get_tasks()
        enriched_tasks = [calculate_task_urgency(t, now) for t in all_raw_tasks]

        today_tasks = []
        for t in enriched_tasks:
            if t.get("is_completed"):
                continue
            ends = (t.get("end_date") or "")[:10]
            starts = (t.get("start_date") or "")[:10]
            is_past_due = (ends < today_str) or (t.get("seconds_remaining", 0) < 0)
            is_active_today = (starts <= today_str <= ends)
            if is_past_due or is_active_today:
                today_tasks.append(t)

        today_task_ids = [t["id"] for t in today_tasks]
        self.assertIn(t_roll_id, today_task_ids, "Rollover task from yesterday must appear in Today view")
        self.assertIn(t_active_id, today_task_ids, "Active task today must appear in Today view")
        self.assertNotIn(t_done_id, today_task_ids, "Completed task must NOT appear in Today remaining tasks")

if __name__ == "__main__":
    unittest.main()

