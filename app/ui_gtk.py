"""
Native GTK4 Desktop Widget & Productivity Sidebar for Linux (X11/Wayland).
Featuring Full Monthly Calendar Grid (Left) + Task & Deadline Sidebar (Right).
Tailored for dual-screen setups with instant monitor switching and safety margins.
"""

from __future__ import annotations
import os
import sys
import ctypes
import datetime
from typing import Optional, List, Dict, Any

os.environ["GTK_THEME"] = "Adwaita:dark"

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
try:
    gi.require_version("GdkX11", "4.0")
    from gi.repository import GdkX11
    HAS_GDK_X11 = True
except Exception:
    HAS_GDK_X11 = False

from gi.repository import Gtk, Gdk, GLib, Pango

try:
    from app.database import Database
    from app.nepali_calendar import (
        get_dual_calendar, get_bs_month_calendar, get_ad_month_calendar,
        to_devanagari_num, ad_to_bs, bs_to_ad
    )
    from app.countdown import calculate_task_urgency
    from app.parser import parse_quick_command
    from app.config import AppConfig, detect_monitors
    from app.notifier import (
        calculate_routine_status, check_and_notify_routines,
        test_routine_notification, format_time_12h
    )
except ImportError:
    from database import Database
    from nepali_calendar import (
        get_dual_calendar, get_bs_month_calendar, get_ad_month_calendar,
        to_devanagari_num, ad_to_bs, bs_to_ad
    )
    from countdown import calculate_task_urgency
    from parser import parse_quick_command
    from config import detect_monitors, AppConfig
    from notifier import (
        calculate_routine_status, check_and_notify_routines,
        test_routine_notification, format_time_12h
    )

STYLE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles", "style.css")


class XClientMessageEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
        ("message_type", ctypes.c_ulong),
        ("format", ctypes.c_int),
        ("data", ctypes.c_long * 5)
    ]

class XEvent(ctypes.Union):
    _fields_ = [
        ("type", ctypes.c_int),
        ("xclient", XClientMessageEvent),
        ("pad", ctypes.c_long * 24)
    ]
class DashboardWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application, config: AppConfig):
        super().__init__(application=app, title="Apex Productivity Dashboard")
        self.config = config
        self.db = Database()
        self.current_filter = "all"
        self.current_routine_filter = "all"
        self.current_view = "today"  # "today", "tasks", "routines", or "notes" (diary)
        self.calendar_mode = config.get("calendar_mode", "bs")  # "bs" or "ad"
        self.selected_calendar_date: Optional[str] = None
        self.selected_diary_date = datetime.date.today().strftime("%Y-%m-%d")
        self.showing_diary_history = False

        # Current viewing month for calendar
        today = datetime.date.today()
        today_bs = ad_to_bs(today)
        self.view_bs_year = today_bs["year"]
        self.view_bs_month = today_bs["month"]
        self.view_ad_year = today.year
        self.view_ad_month = today.month

        self.current_screen = config.get("target_screen", 2)
        self.task_card_widgets: Dict[int, Dict[str, Any]] = {}
        self.routine_card_widgets: Dict[int, Dict[str, Any]] = {}
        self.today_task_widgets: Dict[int, Dict[str, Any]] = {}
        self.today_routine_widgets: Dict[int, Dict[str, Any]] = {}
        self.routine_filter_buttons: Dict[str, Gtk.Button] = {}

        self.set_css_name("window")
        self.add_css_class("dashboard-window")

        borderless = self.config.get("borderless", False)
        self.set_decorated(not borderless)

        # Build Main UI
        self.build_ui()

        # Keyboard shortcuts
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

        # 1-second timer loop for clock & live countdowns
        GLib.timeout_add_seconds(1, self.on_second_tick)

    def build_ui(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.main_box.add_css_class("main-box")
        self.set_child(self.main_box)

        # 1. Top Universal Dual-Calendar Header with Monitor Switcher
        self.build_calendar_header()

        # 2. Main Two-Column Split Body
        self.split_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.split_box.set_vexpand(True)
        self.split_box.add_css_class("split-body-box")
        self.main_box.append(self.split_box)

        # 2a. Left Column: Full Monthly Calendar Grid
        self.calendar_pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.calendar_pane.set_hexpand(True)
        self.calendar_pane.add_css_class("calendar-main-pane")
        self.split_box.append(self.calendar_pane)
        self.build_full_monthly_calendar()

        # 2b. Right Column: Dynamic Task & Deadline Sidebar
        self.sidebar_pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.sidebar_pane.add_css_class("sidebar-pane")
        self.split_box.append(self.sidebar_pane)
        self.build_task_sidebar()

        # Load initial data
        self.refresh_calendar_grid()
        self.refresh_today()
        self.refresh_tasks()
        self.refresh_routines()
        self.refresh_notes()
        self.switch_view("today")

    # --- Header with Monitor Switcher ---
    def build_calendar_header(self):
        header_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_card.add_css_class("header-box")

        # AD Info
        ad_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        ad_tag = Gtk.Label(label="GREGORIAN (AD)", xalign=0)
        ad_tag.add_css_class("calendar-sub")
        self.ad_date_label = Gtk.Label(label="", xalign=0)
        self.ad_date_label.add_css_class("calendar-title-ad")
        self.ad_sub_label = Gtk.Label(label="", xalign=0)
        self.ad_sub_label.add_css_class("calendar-sub")
        ad_box.append(ad_tag)
        ad_box.append(self.ad_date_label)
        ad_box.append(self.ad_sub_label)
        header_card.append(ad_box)

        # Center: Live Monospace Clock + Screen Switcher Button
        center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        center_box.set_valign(Gtk.Align.CENTER)
        center_box.set_hexpand(True)
        center_box.set_halign(Gtk.Align.CENTER)

        self.clock_label = Gtk.Label(label="--:--:--")
        self.clock_label.add_css_class("calendar-time")
        center_box.append(self.clock_label)

        # Screen Switcher Button
        other_screen = 1 if self.current_screen == 2 else 2
        self.btn_switch_screen = Gtk.Button(label=f"🖥 Move to Screen {other_screen}")
        self.btn_switch_screen.add_css_class("screen-switch-btn")
        self.btn_switch_screen.connect("clicked", self.on_switch_screen_clicked)
        center_box.append(self.btn_switch_screen)

        header_card.append(center_box)

        # BS Info
        bs_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        bs_tag = Gtk.Label(label="BIKRAM SAMBAT (BS)", xalign=1)
        bs_tag.add_css_class("calendar-sub")
        self.bs_date_label = Gtk.Label(label="", xalign=1)
        self.bs_date_label.add_css_class("calendar-title-bs")
        self.bs_sub_label = Gtk.Label(label="", xalign=1)
        self.bs_sub_label.add_css_class("calendar-sub")
        bs_box.append(bs_tag)
        bs_box.append(self.bs_date_label)
        bs_box.append(self.bs_sub_label)
        header_card.append(bs_box)

        self.main_box.append(header_card)
        self.update_calendar_header()

    def update_calendar_header(self):
        dual = get_dual_calendar()
        self.ad_date_label.set_text(dual["ad"]["formatted_short"])
        self.ad_sub_label.set_text(dual["ad"]["weekday"])
        self.clock_label.set_text(dual["ad"]["time_12h"])
        self.bs_date_label.set_text(f"{dual['bs']['formatted_en']} BS")
        self.bs_sub_label.set_text(f"{dual['bs']['formatted_np']} • {dual['bs']['ritu_en']}")

    def on_switch_screen_clicked(self, btn):
        self.current_screen = 1 if self.current_screen == 2 else 2
        self.config.set("target_screen", self.current_screen)
        position_window_on_screen(self, self.config, target_screen=self.current_screen)
        other = 1 if self.current_screen == 2 else 2
        self.btn_switch_screen.set_label(f"🖥 Move to Screen {other}")

    # --- LEFT PANE: Full Monthly Calendar Grid ---
    def build_full_monthly_calendar(self):
        # Navigation Bar
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        nav_box.add_css_class("calendar-nav-toolbar")

        # Prev Month Button
        btn_prev = Gtk.Button(label="◀ Prev")
        btn_prev.add_css_class("cal-nav-btn")
        btn_prev.connect("clicked", self.on_cal_prev_month)
        nav_box.append(btn_prev)

        # Today Button
        btn_today = Gtk.Button(label="Today")
        btn_today.add_css_class("cal-nav-btn")
        btn_today.connect("clicked", self.on_cal_today)
        nav_box.append(btn_today)

        # Next Month Button
        btn_next = Gtk.Button(label="Next ▶")
        btn_next.add_css_class("cal-nav-btn")
        btn_next.connect("clicked", self.on_cal_next_month)
        nav_box.append(btn_next)

        # Month Title & Subtitle
        self.cal_month_title = Gtk.Label(xalign=0)
        self.cal_month_title.add_css_class("calendar-month-title")
        self.cal_month_title.set_hexpand(True)
        nav_box.append(self.cal_month_title)

        # Toggle Calendar Mode (BS vs AD)
        self.btn_toggle_cal_mode = Gtk.Button(label="Nepali (BS)")
        self.btn_toggle_cal_mode.add_css_class("cal-nav-btn")
        self.btn_toggle_cal_mode.connect("clicked", self.on_toggle_cal_mode)
        nav_box.append(self.btn_toggle_cal_mode)

        self.calendar_pane.append(nav_box)

        # 7-Column Weekday Headers (Sunday to Saturday)
        self.weekday_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.calendar_pane.append(self.weekday_box)

        # Calendar 6x7 Grid Container
        self.cal_grid = Gtk.Grid()
        self.cal_grid.set_column_homogeneous(True)
        self.cal_grid.set_row_homogeneous(True)
        self.cal_grid.set_vexpand(True)
        self.cal_grid.set_hexpand(True)
        self.calendar_pane.append(self.cal_grid)

    def on_cal_prev_month(self, btn):
        if self.calendar_mode == "bs":
            if self.view_bs_month == 1:
                self.view_bs_month = 12
                self.view_bs_year -= 1
            else:
                self.view_bs_month -= 1
        else:
            if self.view_ad_month == 1:
                self.view_ad_month = 12
                self.view_ad_year -= 1
            else:
                self.view_ad_month -= 1
        self.refresh_calendar_grid()

    def on_cal_next_month(self, btn):
        if self.calendar_mode == "bs":
            if self.view_bs_month == 12:
                self.view_bs_month = 1
                self.view_bs_year += 1
            else:
                self.view_bs_month += 1
        else:
            if self.view_ad_month == 12:
                self.view_ad_month = 1
                self.view_ad_year += 1
            else:
                self.view_ad_month += 1
        self.refresh_calendar_grid()

    def on_cal_today(self, btn):
        today = datetime.date.today()
        today_bs = ad_to_bs(today)
        self.view_bs_year = today_bs["year"]
        self.view_bs_month = today_bs["month"]
        self.view_ad_year = today.year
        self.view_ad_month = today.month
        self.refresh_calendar_grid()

    def on_toggle_cal_mode(self, btn):
        self.calendar_mode = "ad" if self.calendar_mode == "bs" else "bs"
        self.config.set("calendar_mode", self.calendar_mode)
        self.btn_toggle_cal_mode.set_label("Nepali (BS)" if self.calendar_mode == "bs" else "English (AD)")
        self.refresh_calendar_grid()

    def refresh_calendar_grid(self):
        # Update weekday headers
        while child := self.weekday_box.get_first_child():
            self.weekday_box.remove(child)

        weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        weekdays_np = ["आइत", "सोम", "मङ्गल", "बुध", "बिहि", "शुक्र", "शनि"]

        for idx, (en, np) in enumerate(zip(weekdays, weekdays_np)):
            lbl = Gtk.Label(label=f"{en} ({np})")
            lbl.set_hexpand(True)
            lbl.add_css_class("cal-weekday-header")
            if idx == 6:  # Saturday weekend in Nepal
                lbl.add_css_class("cal-weekday-sat")
            self.weekday_box.append(lbl)

        # Clear grid cells
        for row in range(6):
            for col in range(7):
                if item := self.cal_grid.get_child_at(col, row):
                    self.cal_grid.remove(item)

        # Fetch all tasks and diary dates to mark indicators on calendar days
        all_tasks = self.db.get_tasks()
        diary_dates = {d["date"] for d in self.db.get_diary_dates()}

        if self.calendar_mode == "bs":
            cal_data = get_bs_month_calendar(self.view_bs_year, self.view_bs_month)
            title_text = f"📅 {cal_data['month_name_en']} {cal_data['year_bs']} BS ({cal_data['month_name_np']} {cal_data['year_np']})  <span size='small' color='#94a3b8'>• {cal_data['ad_span']}</span>"
            self.cal_month_title.set_markup(title_text)
            cells = cal_data["cells"]
        else:
            cal_data = get_ad_month_calendar(self.view_ad_year, self.view_ad_month)
            title_text = f"📅 {cal_data['month_name']} {cal_data['year_ad']} AD  <span size='small' color='#94a3b8'>• {cal_data['bs_span']}</span>"
            self.cal_month_title.set_markup(title_text)
            cells = cal_data["cells"]

        # Populate 6x7 Grid
        for i in range(42):
            col = i % 7
            row = i // 7

            if i < len(cells) and cells[i] is not None:
                cell_data = cells[i]
                cell_widget = self.create_calendar_day_cell(cell_data, all_tasks, diary_dates)
                self.cal_grid.attach(cell_widget, col, row, 1, 1)
            else:
                # Empty cell
                empty_box = Gtk.Box()
                empty_box.add_css_class("cal-day-cell")
                empty_box.add_css_class("empty")
                self.cal_grid.attach(empty_box, col, row, 1, 1)

    def create_calendar_day_cell(self, cell_data: Dict[str, Any], tasks: List[Dict[str, Any]], diary_dates: set[str] = set()) -> Gtk.Box:
        cell_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        cell_box.add_css_class("cal-day-cell")

        is_today = cell_data.get("is_today", False)
        is_sat = cell_data.get("is_saturday", False)
        ad_iso = cell_data.get("ad_date_iso", "")
        is_selected = (self.selected_calendar_date == ad_iso)

        if is_today:
            cell_box.add_css_class("today")
        if is_sat:
            cell_box.add_css_class("saturday")
        if is_selected:
            cell_box.add_css_class("selected")

        # Day Number Row (Primary large number + Dual secondary number)
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        if self.calendar_mode == "bs":
            primary_str = str(cell_data["bs_day"])
            secondary_str = f"{cell_data['ad_month']} {cell_data['ad_day']}"
        else:
            primary_str = str(cell_data["ad_day"])
            secondary_str = f"{cell_data.get('bs_month_name', '')[:3]} {cell_data.get('bs_day', '')}"

        primary_lbl = Gtk.Label(label=primary_str, xalign=0)
        primary_lbl.add_css_class("cal-primary-num")
        if is_today:
            primary_lbl.add_css_class("today-text")
        elif is_sat:
            primary_lbl.add_css_class("sat-text")
        primary_lbl.set_hexpand(True)
        top_row.append(primary_lbl)

        dual_lbl = Gtk.Label(label=secondary_str, xalign=1)
        dual_lbl.add_css_class("cal-dual-num")
        top_row.append(dual_lbl)

        cell_box.append(top_row)

        # Check for tasks matching this date (either deadline falls on this day or range spans this day)
        # Check for tasks matching this date (either active/due on this day, or completed on this day)
        matching_tasks = []
        matching_done = []
        for t in tasks:
            start_d = (t.get("start_date") or "")[:10]
            end_d = (t.get("end_date") or "")[:10]
            completed_d = (t.get("completed_at") or "")[:10]
            if t.get("is_completed"):
                if completed_d == ad_iso:
                    matching_done.append(t)
            else:
                if start_d <= ad_iso <= end_d:
                    matching_tasks.append(t)

        if matching_tasks:
            count = len(matching_tasks)
            first_title = matching_tasks[0]["title"]
            has_urgent = any(t.get("priority") in ("urgent", "high") or t.get("is_urgent") for t in matching_tasks)
            p_text = f"• {first_title[:12]}..." if count == 1 else f"• {count} tasks"
            task_tag = Gtk.Label(label=p_text, xalign=0)
            task_tag.add_css_class("cal-task-indicator")
            if has_urgent:
                task_tag.set_markup(f"<span color='#ef4444'><b>{GLib.markup_escape_text(p_text)}</b></span>")
            cell_box.append(task_tag)

        if matching_done:
            count = len(matching_done)
            done_tag = Gtk.Label(label=f"✓ {count} done", xalign=0)
            done_tag.add_css_class("cal-done-indicator")
            done_tag.set_markup(f"<span color='#10b981'><b>✓ {count} done</b></span>")
            cell_box.append(done_tag)

        # Check for diary entries on this date
        if ad_iso in diary_dates:
            diary_tag = Gtk.Label(label="📔 Diary", xalign=0)
            diary_tag.add_css_class("cal-diary-indicator")
            cell_box.append(diary_tag)

        # Click gesture to open task creator or navigate diary for this date
        click_gesture = Gtk.GestureClick()
        click_gesture.connect("released", lambda g, n, x, y, dt_iso=ad_iso: self.on_calendar_cell_clicked(dt_iso))
        cell_box.add_controller(click_gesture)

        return cell_box

    def on_calendar_cell_clicked(self, date_iso: str):
        if self.selected_calendar_date == date_iso:
            self.selected_calendar_date = None
        else:
            self.selected_calendar_date = date_iso
            self.selected_diary_date = date_iso

        self.refresh_calendar_grid()

        if self.current_view == "notes":
            self.refresh_notes()
        else:
            self.switch_view("tasks")
            self.refresh_tasks()

    # --- RIGHT PANE: Tasks & Deadlines Sidebar ---
    def build_task_sidebar(self):
        # 1. View Switcher Bar (Tasks / Routines / Notes)
        view_switcher_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        view_switcher_box.add_css_class("view-switcher-box")

        self.btn_view_today = Gtk.Button(label="⭐ Today")
        self.btn_view_today.add_css_class("view-tab-btn")
        self.btn_view_today.add_css_class("active")
        self.btn_view_today.connect("clicked", lambda b: self.switch_view("today"))
        view_switcher_box.append(self.btn_view_today)

        self.btn_view_tasks = Gtk.Button(label="✓ Tasks")
        self.btn_view_tasks.add_css_class("view-tab-btn")
        self.btn_view_tasks.connect("clicked", lambda b: self.switch_view("tasks"))
        view_switcher_box.append(self.btn_view_tasks)

        self.btn_view_routines = Gtk.Button(label="⏰ Routines")
        self.btn_view_routines.add_css_class("view-tab-btn")
        self.btn_view_routines.connect("clicked", lambda b: self.switch_view("routines"))
        view_switcher_box.append(self.btn_view_routines)

        self.btn_view_notes = Gtk.Button(label="📔 Diary")
        self.btn_view_notes.add_css_class("view-tab-btn")
        self.btn_view_notes.connect("clicked", lambda b: self.switch_view("notes"))
        view_switcher_box.append(self.btn_view_notes)

        self.sidebar_pane.append(view_switcher_box)

        # 2a. Task Filter Row (Filters + "+ New Task" button)
        self.task_filter_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        self.task_filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.task_filter_box.add_css_class("filter-box")
        self.task_filter_box.set_hexpand(True)

        self.filter_buttons = {}
        filters = [
            ("all", "All"),
            ("active", "Active"),
            ("urgent", "Urgent"),
            ("completed", "Done")
        ]
        for f_key, f_label in filters:
            btn = Gtk.Button(label=f_label)
            btn.add_css_class("filter-btn")
            if f_key == self.current_filter:
                btn.add_css_class("active")
            btn.connect("clicked", self.on_filter_clicked, f_key)
            self.task_filter_box.append(btn)
            self.filter_buttons[f_key] = btn

        self.task_filter_bar.append(self.task_filter_box)

        # "+ New Task" visual creator launcher
        new_task_btn = Gtk.Button(label="+ New")
        new_task_btn.add_css_class("quick-submit-btn")
        new_task_btn.set_tooltip_text("Open visual task creator form")
        new_task_btn.connect("clicked", lambda b: self.show_task_creator(self.selected_calendar_date))
        self.task_filter_bar.append(new_task_btn)

        self.sidebar_pane.append(self.task_filter_bar)

        # 2b. Date Filter Banner (Shown when calendar date is selected)
        self.date_filter_banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.date_filter_banner.add_css_class("selected-date-banner")
        self.date_filter_banner.set_visible(False)

        self.date_filter_lbl = Gtk.Label(xalign=0)
        self.date_filter_lbl.add_css_class("selected-date-lbl")
        self.date_filter_lbl.set_hexpand(True)
        self.date_filter_banner.append(self.date_filter_lbl)

        btn_add_date_task = Gtk.Button(label="+ Add Task")
        btn_add_date_task.add_css_class("quick-submit-btn")
        btn_add_date_task.connect("clicked", lambda b: self.show_task_creator(self.selected_calendar_date))
        self.date_filter_banner.append(btn_add_date_task)

        btn_clear_date_filter = Gtk.Button(label="✕ All")
        btn_clear_date_filter.add_css_class("diary-nav-btn")
        btn_clear_date_filter.connect("clicked", self.clear_calendar_selection)
        self.date_filter_banner.append(btn_clear_date_filter)

        self.sidebar_pane.append(self.date_filter_banner)

        # 2b. Routine Sub-Filter Bar (All, Urgent, Done)
        self.routine_filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.routine_filter_box.add_css_class("filter-box")
        self.routine_filter_box.set_visible(False)

        self.routine_filter_buttons = {}
        routine_filters = [
            ("all", "All"),
            ("urgent", "Urgent"),
            ("completed", "Done")
        ]
        for rf_key, rf_label in routine_filters:
            btn = Gtk.Button(label=rf_label)
            btn.add_css_class("filter-btn")
            if rf_key == self.current_routine_filter:
                btn.add_css_class("active")
            btn.connect("clicked", self.on_routine_filter_clicked, rf_key)
            self.routine_filter_box.append(btn)
            self.routine_filter_buttons[rf_key] = btn

        self.sidebar_pane.append(self.routine_filter_box)

        # 2c. Visual Task Creator Form
        self.task_creator_box = self.build_task_creator()
        self.sidebar_pane.append(self.task_creator_box)

        # 3. Content Stack (Today vs Tasks vs Routines vs Notes)
        self.content_stack = Gtk.Stack()
        self.content_stack.set_vexpand(True)
        self.content_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.sidebar_pane.append(self.content_stack)

        # 3a. Today Focus View
        self.today_page_box = self.build_today_page()
        self.content_stack.add_named(self.today_page_box, "today")

        # 3b. Tasks Scrolled View
        self.tasks_scroll = Gtk.ScrolledWindow()
        self.tasks_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.tasks_scroll.add_css_class("tasks-scroll")
        self.tasks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.tasks_scroll.set_child(self.tasks_box)
        self.content_stack.add_named(self.tasks_scroll, "tasks")

        # 3b. Routines View
        self.routines_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.build_routines_page()
        self.content_stack.add_named(self.routines_page_box, "routines")

        # 3c. Notes Scrolled View
        self.notes_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.build_notes_page()
        self.content_stack.add_named(self.notes_page_box, "notes")

        # 4. Quick Input Bar
        self.build_quick_input_bar()

    def build_task_creator(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.add_css_class("task-creator-box")
        box.set_visible(False)

        # Header row
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label="➕ Create New Task", xalign=0)
        lbl.add_css_class("creator-header-lbl")
        lbl.set_hexpand(True)
        header.append(lbl)

        close_btn = Gtk.Button(label="✕")
        close_btn.add_css_class("delete-btn")
        close_btn.connect("clicked", lambda b: self.task_creator_box.set_visible(False))
        header.append(close_btn)
        box.append(header)

        # Title entry
        self.creator_title_entry = Gtk.Entry()
        self.creator_title_entry.set_placeholder_text("Task title / objective...")
        self.creator_title_entry.add_css_class("quick-entry")
        self.creator_title_entry.connect("activate", self.on_submit_task_creator)
        box.append(self.creator_title_entry)

        # Date range row
        dates_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        start_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        start_box.set_hexpand(True)
        start_lbl = Gtk.Label(label="Start Date (AD)", xalign=0)
        start_lbl.add_css_class("calendar-sub")
        start_box.append(start_lbl)
        self.creator_start_entry = Gtk.Entry()
        self.creator_start_entry.set_placeholder_text("YYYY-MM-DD")
        self.creator_start_entry.add_css_class("quick-entry")
        start_box.append(self.creator_start_entry)
        dates_row.append(start_box)

        end_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        end_box.set_hexpand(True)
        end_lbl = Gtk.Label(label="Deadline Date (AD)", xalign=0)
        end_lbl.add_css_class("calendar-sub")
        end_box.append(end_lbl)
        self.creator_end_entry = Gtk.Entry()
        self.creator_end_entry.set_placeholder_text("YYYY-MM-DD")
        self.creator_end_entry.add_css_class("quick-entry")
        end_box.append(self.creator_end_entry)
        dates_row.append(end_box)

        box.append(dates_row)

        # Priority & Category row
        meta_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        prio_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        prio_lbl = Gtk.Label(label="Priority", xalign=0)
        prio_lbl.add_css_class("calendar-sub")
        prio_box.append(prio_lbl)
        self.creator_prio_dropdown = Gtk.DropDown.new_from_strings(["normal", "urgent", "high", "low"])
        self.creator_prio_dropdown.set_selected(0)
        self.creator_prio_dropdown.add_css_class("quick-entry")
        prio_box.append(self.creator_prio_dropdown)
        meta_row.append(prio_box)

        cat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        cat_box.set_hexpand(True)
        cat_lbl = Gtk.Label(label="Category / Tag", xalign=0)
        cat_lbl.add_css_class("calendar-sub")
        cat_box.append(cat_lbl)
        self.creator_cat_entry = Gtk.Entry()
        self.creator_cat_entry.set_placeholder_text("work, study, personal...")
        self.creator_cat_entry.set_text("work")
        self.creator_cat_entry.add_css_class("quick-entry")
        cat_box.append(self.creator_cat_entry)
        meta_row.append(cat_box)

        box.append(meta_row)

        # Action buttons row
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_row.set_halign(Gtk.Align.END)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.add_css_class("diary-nav-btn")
        cancel_btn.connect("clicked", lambda b: self.task_creator_box.set_visible(False))
        btn_row.append(cancel_btn)

        save_btn = Gtk.Button(label="✓ Save Task")
        save_btn.add_css_class("quick-submit-btn")
        save_btn.connect("clicked", self.on_submit_task_creator)
        btn_row.append(save_btn)

        box.append(btn_row)
        return box

    def show_task_creator(self, date_str: Optional[str] = None):
        if not date_str:
            date_str = datetime.date.today().strftime("%Y-%m-%d")
        self.creator_start_entry.set_text(date_str)
        self.creator_end_entry.set_text(date_str)
        self.creator_title_entry.set_text("")
        self.task_creator_box.set_visible(True)
        self.creator_title_entry.grab_focus()

    def on_submit_task_creator(self, *args):
        title = self.creator_title_entry.get_text().strip()
        if not title:
            return
        start_date = self.creator_start_entry.get_text().strip() or datetime.date.today().strftime("%Y-%m-%d")
        end_date = self.creator_end_entry.get_text().strip() or start_date
        category = self.creator_cat_entry.get_text().strip() or "general"

        prio_idx = self.creator_prio_dropdown.get_selected()
        prios = ["normal", "urgent", "high", "low"]
        priority = prios[prio_idx] if prio_idx < len(prios) else "normal"

        self.db.create_task(
            title=title,
            start_date=start_date,
            end_date=end_date,
            priority=priority,
            category=category
        )
        self.task_creator_box.set_visible(False)
        self.refresh_tasks()
        self.refresh_calendar_grid()
        if hasattr(self, "refresh_today"):
            self.refresh_today()

    def on_filter_clicked(self, btn, filter_key):
        for k, b in self.filter_buttons.items():
            b.remove_css_class("active")
        btn.add_css_class("active")
        self.current_filter = filter_key
        if self.current_view != "tasks":
            self.switch_view("tasks")
        self.refresh_tasks()

    def on_routine_filter_clicked(self, btn, filter_key):
        for k, b in self.routine_filter_buttons.items():
            b.remove_css_class("active")
        btn.add_css_class("active")
        self.current_routine_filter = filter_key
        if self.current_view != "routines":
            self.switch_view("routines")
        self.refresh_routines()

    def clear_calendar_selection(self, *args):
        self.selected_calendar_date = None
        self.refresh_calendar_grid()
        if self.current_view == "notes":
            self.refresh_notes()
        else:
            self.refresh_tasks()

    # --- TODAY FOCUS PAGE ---
    def build_today_page(self) -> Gtk.Box:
        self.today_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.today_page_box.add_css_class("routines-page-box")

        # 1. Header Card
        header_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        header_card.add_css_class("today-header-box")

        title_lbl = Gtk.Label(label="⭐ Today's Remaining Focus", xalign=0)
        title_lbl.add_css_class("calendar-title-ad")
        header_card.append(title_lbl)

        self.today_summary_lbl = Gtk.Label(label="0 routines left • 0 tasks remaining", xalign=0)
        self.today_summary_lbl.add_css_class("calendar-sub")
        header_card.append(self.today_summary_lbl)

        self.today_page_box.append(header_card)

        # 2. Scrollable Body
        self.today_scroll = Gtk.ScrolledWindow()
        self.today_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.today_scroll.set_vexpand(True)

        self.today_content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.today_scroll.set_child(self.today_content_box)
        self.today_page_box.append(self.today_scroll)

        return self.today_page_box

    def refresh_today(self):
        while child := self.today_content_box.get_first_child():
            self.today_content_box.remove(child)
        self.today_task_widgets.clear()
        self.today_routine_widgets.clear()

        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # 1. Routines Remaining for Today
        raw_routines = self.db.get_routines(today_str)
        enriched_routines = [calculate_routine_status(r, now) for r in raw_routines]
        remaining_routines = [r for r in enriched_routines if not r.get("is_completed_today")]

        # 2. Tasks Remaining for Today (Active today OR Rollover from yesterday/earlier)
        raw_tasks = self.db.get_tasks()
        enriched_tasks = [calculate_task_urgency(t, now) for t in raw_tasks]
        remaining_tasks = []
        for t in enriched_tasks:
            if t.get("is_completed"):
                continue
            ends = (t.get("end_date") or "")[:10]
            starts = (t.get("start_date") or "")[:10]
            is_past_due = (ends < today_str) or (t.get("seconds_remaining", 0) < 0)
            is_active_today = (starts <= today_str <= ends)
            if is_past_due or is_active_today:
                remaining_tasks.append(t)

        remaining_tasks.sort(key=lambda t: (0 if (t.get("end_date") or "")[:10] < today_str else 1, t.get("seconds_remaining", 0)))

        # Update summary & counters
        total_remaining = len(remaining_routines) + len(remaining_tasks)
        if hasattr(self, "today_summary_lbl"):
            self.today_summary_lbl.set_text(f"{len(remaining_routines)} routines left • {len(remaining_tasks)} tasks remaining")
        if hasattr(self, "btn_view_today"):
            self.btn_view_today.set_label(f"⭐ Today ({total_remaining})")

        # --- Section 1: Remaining Routines ---
        sec1_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sec1_lbl = Gtk.Label(label=f"⏰ REMAINING ROUTINES ({len(remaining_routines)})", xalign=0)
        sec1_lbl.add_css_class("calendar-sub")
        sec1_lbl.set_hexpand(True)
        sec1_header.append(sec1_lbl)

        btn_go_r = Gtk.Button(label="Manage ➔")
        btn_go_r.add_css_class("diary-nav-btn")
        btn_go_r.connect("clicked", lambda b: self.switch_view("routines"))
        sec1_header.append(btn_go_r)
        self.today_content_box.append(sec1_header)

        if not remaining_routines:
            clean_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            clean_box.add_css_class("today-clean-card")
            lbl = Gtk.Label(label="✓ All routines completed for today! Great job! 🎉" if raw_routines else "No routines scheduled today.")
            lbl.add_css_class("calendar-sub")
            clean_box.append(lbl)
            self.today_content_box.append(clean_box)
        else:
            for r in remaining_routines:
                card = self.create_today_routine_card(r)
                self.today_content_box.append(card)

        # --- Section 2: Remaining Tasks & Rollovers ---
        sec2_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sec2_header.set_margin_top(8)
        sec2_lbl = Gtk.Label(label=f"✓ REMAINING TASKS & ROLLOVERS ({len(remaining_tasks)})", xalign=0)
        sec2_lbl.add_css_class("calendar-sub")
        sec2_lbl.set_hexpand(True)
        sec2_header.append(sec2_lbl)

        btn_go_t = Gtk.Button(label="Manage ➔")
        btn_go_t.add_css_class("diary-nav-btn")
        btn_go_t.connect("clicked", lambda b: self.switch_view("tasks"))
        sec2_header.append(btn_go_t)
        self.today_content_box.append(sec2_header)

        if not remaining_tasks:
            clean_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            clean_box.add_css_class("today-clean-card")
            lbl = Gtk.Label(label="✓ All tasks completed for today! 🎉")
            lbl.add_css_class("calendar-sub")
            clean_box.append(lbl)
            self.today_content_box.append(clean_box)
        else:
            for t in remaining_tasks:
                card = self.create_today_task_card(t)
                self.today_content_box.append(card)

    def create_today_routine_card(self, r: Dict[str, Any]) -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        card.add_css_class("task-card")
        card.add_css_class("routine-card")
        if r.get("is_due_now"):
            card.add_css_class("urgency-critical")

        chk_btn = Gtk.Button(label="")
        chk_btn.add_css_class("check-btn")
        chk_btn.set_valign(Gtk.Align.CENTER)
        chk_btn.connect("clicked", lambda b, rid=r["id"]: self.on_toggle_routine_from_today(rid))
        card.append(chk_btn)

        detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        detail_box.set_hexpand(True)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        time_lbl = Gtk.Label(label=r.get("time_12h") or r.get("time_str"))
        time_lbl.add_css_class("range-pill")
        top_row.append(time_lbl)

        title_lbl = Gtk.Label(label=r["title"], xalign=0)
        title_lbl.add_css_class("task-title")
        top_row.append(title_lbl)
        detail_box.append(top_row)

        sub_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cat_lbl = Gtk.Label(label=f"@{r.get('category', 'routine')}", xalign=0)
        cat_lbl.add_css_class("task-category")
        sub_row.append(cat_lbl)

        countdown_lbl = Gtk.Label(label=r.get("countdown_text", ""), xalign=0)
        countdown_lbl.add_css_class("task-countdown")
        sub_row.append(countdown_lbl)
        detail_box.append(sub_row)
        card.append(detail_box)

        badge_lbl = Gtk.Label(label=r.get("badge_text", ""))
        badge_lbl.add_css_class("urgency-badge")
        for cls in r.get("badge_class", "badge-healthy").split():
            badge_lbl.add_css_class(cls)
        badge_lbl.set_valign(Gtk.Align.CENTER)
        card.append(badge_lbl)

        self.today_routine_widgets[r["id"]] = {
            "routine": r,
            "countdown_lbl": countdown_lbl,
            "badge_lbl": badge_lbl
        }

        return card

    def create_today_task_card(self, task: Dict[str, Any]) -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        card.add_css_class("task-card")
        if task.get("urgency_class"):
            card.add_css_class(task["urgency_class"])

        task_id = task["id"]
        chk_btn = Gtk.Button(label="")
        chk_btn.add_css_class("check-btn")
        chk_btn.set_valign(Gtk.Align.CENTER)
        chk_btn.connect("clicked", lambda b, tid=task_id: self.on_toggle_task_from_today(tid))
        card.append(chk_btn)

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)

        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_lbl = Gtk.Label(xalign=0)
        title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        title_lbl.set_hexpand(True)
        title_lbl.set_markup(f"<b>{GLib.markup_escape_text(task['title'])}</b>")
        title_lbl.add_css_class("task-title")
        title_row.append(title_lbl)

        today_str = datetime.date.today().strftime("%Y-%m-%d")
        ends_d = (task.get("end_date") or "")[:10]
        if ends_d < today_str or task.get("seconds_remaining", 0) < 0:
            is_yesterday = task.get("is_from_yesterday") or (task.get("overdue_days") == 1)
            txt = "[⚠️ From yesterday (-1d)]" if is_yesterday else f"[⚠️ Remaining -{task.get('overdue_days', 1)}d]"
            roll_lbl = Gtk.Label(label=txt)
            roll_lbl.add_css_class("rollover-pill")
            title_row.append(roll_lbl)

        if task.get("range_tag"):
            range_lbl = Gtk.Label(label=f"[{task['range_tag']}]")
            range_lbl.add_css_class("range-pill")
            title_row.append(range_lbl)

        info_box.append(title_row)

        sub_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cat_lbl = Gtk.Label(label=f"@{task.get('category', 'general')}", xalign=0)
        cat_lbl.add_css_class("calendar-sub")
        sub_row.append(cat_lbl)

        countdown_lbl = Gtk.Label(label=task.get("countdown_text", ""), xalign=0)
        countdown_lbl.add_css_class("calendar-sub")
        sub_row.append(countdown_lbl)

        info_box.append(sub_row)
        card.append(info_box)

        badge_lbl = Gtk.Label(label=task.get("badge_text", ""))
        badge_lbl.set_valign(Gtk.Align.CENTER)
        for cls in task.get("badge_class", "badge-healthy").split():
            badge_lbl.add_css_class(cls)
        card.append(badge_lbl)

        del_btn = Gtk.Button(label="✕")
        del_btn.add_css_class("delete-btn")
        del_btn.set_valign(Gtk.Align.CENTER)
        del_btn.connect("clicked", lambda b, tid=task_id: self.on_delete_task(tid))
        card.append(del_btn)

        self.today_task_widgets[task_id] = {
            "task": task,
            "countdown_lbl": countdown_lbl,
            "badge_lbl": badge_lbl
        }

        return card

    def on_toggle_routine_from_today(self, routine_id: int):
        self.db.toggle_routine_today(routine_id)
        self.refresh_today()
        self.refresh_routines()

    def on_toggle_task_from_today(self, task_id: int):
        self.db.toggle_task(task_id)
        self.refresh_today()
        self.refresh_tasks()
        self.refresh_calendar_grid()

    def on_delete_task(self, task_id: int):
        self.db.delete_task(task_id)
        if hasattr(self, "refresh_today"):
            self.refresh_today()
        self.refresh_tasks()
        self.refresh_calendar_grid()

    def switch_view(self, view_name: str):
        self.current_view = view_name
        self.content_stack.set_visible_child_name(view_name)

        if hasattr(self, "btn_view_today"):
            self.btn_view_today.remove_css_class("active")
        self.btn_view_tasks.remove_css_class("active")
        self.btn_view_routines.remove_css_class("active")
        self.btn_view_notes.remove_css_class("active")

        if view_name == "today":
            if hasattr(self, "btn_view_today"):
                self.btn_view_today.add_css_class("active")
            self.task_filter_bar.set_visible(False)
            self.routine_filter_box.set_visible(False)
            self.date_filter_banner.set_visible(False)
            self.refresh_today()
        elif view_name == "tasks":
            self.btn_view_tasks.add_css_class("active")
            self.task_filter_bar.set_visible(True)
            self.routine_filter_box.set_visible(False)
            self.date_filter_banner.set_visible(self.selected_calendar_date is not None)
            self.refresh_tasks()
        elif view_name == "routines":
            self.btn_view_routines.add_css_class("active")
            self.task_filter_bar.set_visible(False)
            self.routine_filter_box.set_visible(True)
            self.date_filter_banner.set_visible(False)
            self.refresh_routines()
        elif view_name == "notes":
            self.btn_view_notes.add_css_class("active")
            self.task_filter_bar.set_visible(False)
            self.routine_filter_box.set_visible(False)
            self.date_filter_banner.set_visible(False)
            self.refresh_notes()

    def refresh_tasks(self):
        while child := self.tasks_box.get_first_child():
            self.tasks_box.remove(child)
        self.task_card_widgets.clear()

        raw_tasks = self.db.get_tasks()
        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        all_enriched = [calculate_task_urgency(t, now) for t in raw_tasks]

        if self.selected_calendar_date:
            sel = self.selected_calendar_date
            if self.current_view == "tasks":
                self.date_filter_banner.set_visible(True)
                self.date_filter_lbl.set_label(f"📅 Filtered: {sel}")
            all_enriched = [
                t for t in all_enriched
                if ((t.get("start_date") or "")[:10] <= sel <= (t.get("end_date") or "9999-99-99")[:10])
                or ((t.get("completed_at") or "").startswith(sel))
                or ((t.get("end_date") or "")[:10] == sel)
            ]
        else:
            self.date_filter_banner.set_visible(False)

        # Update counter labels on filter buttons
        # Rule: In "All", uncompleted tasks + tasks completed TODAY.
        # Tasks completed yesterday or earlier are archived into Done / History.
        count_all = sum(1 for t in all_enriched if not t["is_completed"] or t.get("is_completed_today") or ((t.get("completed_at") or "").startswith(today_str)))
        count_active = sum(1 for t in all_enriched if not t["is_completed"] and not t.get("is_upcoming"))
        count_urgent = sum(1 for t in all_enriched if not t["is_completed"] and (t.get("is_urgent") or t.get("priority") in ("urgent", "high") or t.get("urgency") in ("critical", "warning", "overdue")))
        count_done = sum(1 for t in all_enriched if t["is_completed"])

        counts = {
            "all": count_all,
            "active": count_active,
            "urgent": count_urgent,
            "completed": count_done
        }
        labels = {
            "all": "All",
            "active": "Active",
            "urgent": "Urgent",
            "completed": "Done"
        }
        for f_key, btn in self.filter_buttons.items():
            btn.set_label(f"{labels.get(f_key, f_key)} ({counts.get(f_key, 0)})")

        if self.selected_calendar_date:
            if self.current_filter == "active":
                tasks = [t for t in all_enriched if not t["is_completed"]]
            elif self.current_filter == "urgent":
                tasks = [t for t in all_enriched if not t["is_completed"] and (t.get("is_urgent") or t.get("priority") in ("urgent", "high") or t.get("urgency") in ("critical", "warning", "overdue"))]
            elif self.current_filter == "completed":
                tasks = [t for t in all_enriched if t["is_completed"]]
            else:
                tasks = all_enriched
        else:
            if self.current_filter == "active":
                tasks = [t for t in all_enriched if not t["is_completed"] and not t.get("is_upcoming")]
            elif self.current_filter == "urgent":
                tasks = [t for t in all_enriched if not t["is_completed"] and (t.get("is_urgent") or t.get("priority") in ("urgent", "high") or t.get("urgency") in ("critical", "warning", "overdue"))]
            elif self.current_filter == "completed":
                tasks = [t for t in all_enriched if t["is_completed"]]
            else:
                # "all": uncompleted tasks (including overdue from yesterday/past) + tasks completed TODAY
                tasks = [t for t in all_enriched if not t["is_completed"] or t.get("is_completed_today") or ((t.get("completed_at") or "").startswith(today_str))]

        if not tasks:
            msg = f"No tasks recorded on {self.selected_calendar_date}.\nClick '+ Add Task' above to create one!" if self.selected_calendar_date else "No tasks in this view.\nType below to add one!"
            empty_lbl = Gtk.Label(label=msg)
            empty_lbl.set_margin_top(40)
            empty_lbl.add_css_class("calendar-sub")
            self.tasks_box.append(empty_lbl)
            return

        for t in tasks:
            card = self.create_task_card(t)
            self.tasks_box.append(card)

    def create_task_card(self, task: Dict[str, Any]) -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        card.add_css_class("task-card")

        task_id = task["id"]
        is_completed = bool(task.get("is_completed", 0))

        # Check button
        check_btn = Gtk.Button()
        check_btn.add_css_class("check-btn")
        check_btn.set_valign(Gtk.Align.CENTER)
        if is_completed:
            check_btn.set_label("✓")
            check_btn.add_css_class("checked")
        else:
            check_btn.set_label(" ")
        check_btn.connect("clicked", lambda b, tid=task_id: self.on_toggle_task(tid))
        card.append(check_btn)

        # Title + Range + Sub row
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_hexpand(True)

        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_lbl = Gtk.Label(xalign=0)
        title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        title_lbl.set_hexpand(True)

        if is_completed:
            title_lbl.set_markup(f"<span strikethrough='true' color='#64748b'>{GLib.markup_escape_text(task['title'])}</span>")
            title_lbl.add_css_class("task-title-completed")
        else:
            title_lbl.set_markup(f"<b>{GLib.markup_escape_text(task['title'])}</b>")
            title_lbl.add_css_class("task-title")
        title_row.append(title_lbl)

        today_str = datetime.date.today().strftime("%Y-%m-%d")
        if not is_completed:
            ends_d = (task.get("end_date") or "")[:10]
            if ends_d < today_str or task.get("seconds_remaining", 0) < 0:
                is_yesterday = task.get("is_from_yesterday") or (task.get("overdue_days") == 1)
                txt = "[⚠️ From yesterday (-1d)]" if is_yesterday else f"[⚠️ Remaining -{task.get('overdue_days', 1)}d]"
                roll_lbl = Gtk.Label(label=txt)
                roll_lbl.add_css_class("rollover-pill")
                title_row.append(roll_lbl)
        else:
            is_done_today = task.get("is_completed_today") or ((task.get("completed_at") or "").startswith(today_str))
            if is_done_today:
                done_lbl = Gtk.Label(label="[✓ Done today]")
                done_lbl.add_css_class("done-today-pill")
                title_row.append(done_lbl)
            else:
                done_lbl = Gtk.Label(label=f"[Done: {(task.get('completed_at') or '')[:10]}]")
                done_lbl.add_css_class("calendar-sub")
                title_row.append(done_lbl)

        if task.get("range_tag"):
            range_lbl = Gtk.Label(label=f"[{task['range_tag']}]")
            range_lbl.add_css_class("range-pill")
            range_lbl.set_tooltip_text(f"Origin (Start): {task.get('start_date')} | Deadline: {task.get('end_date')}")
            title_row.append(range_lbl)

        info_box.append(title_row)

        sub_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cat_lbl = Gtk.Label(label=f"@{task.get('category', 'general')}", xalign=0)
        cat_lbl.add_css_class("calendar-sub")
        sub_row.append(cat_lbl)

        countdown_lbl = Gtk.Label(label=task.get("countdown_text", ""), xalign=0)
        countdown_lbl.add_css_class("calendar-sub")
        sub_row.append(countdown_lbl)

        info_box.append(sub_row)
        card.append(info_box)

        # Urgency Badge
        badge_lbl = Gtk.Label(label=task.get("badge_text", ""))
        badge_lbl.set_valign(Gtk.Align.CENTER)
        for cls in task.get("badge_class", "badge-healthy").split():
            badge_lbl.add_css_class(cls)
        card.append(badge_lbl)

        # Delete Button
        del_btn = Gtk.Button(label="✕")
        del_btn.add_css_class("delete-btn")
        del_btn.set_valign(Gtk.Align.CENTER)
        del_btn.connect("clicked", lambda b, tid=task_id: self.on_delete_task(tid))
        card.append(del_btn)

        self.task_card_widgets[task_id] = {
            "task": task,
            "badge_lbl": badge_lbl,
            "countdown_lbl": countdown_lbl,
            "card": card
        }

        return card

    def on_toggle_task(self, task_id: int):
        self.db.toggle_task(task_id)
        if hasattr(self, "refresh_today"):
            self.refresh_today()
        self.refresh_tasks()
        self.refresh_calendar_grid()

    # Routines Page
    def build_routines_page(self):
        # 1. Header with title and summary
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_box.set_hexpand(True)

        lbl = Gtk.Label(label="⏰ Daily Routines & Habits", xalign=0)
        lbl.add_css_class("calendar-title-ad")
        title_box.append(lbl)

        self.routines_summary_label = Gtk.Label(label="Daily schedules • Automated alerts", xalign=0)
        self.routines_summary_label.add_css_class("calendar-sub")
        title_box.append(self.routines_summary_label)
        header_box.append(title_box)

        # Quick test alert button
        test_alert_btn = Gtk.Button(label="🔔 Test")
        test_alert_btn.add_css_class("screen-switch-btn")
        test_alert_btn.set_tooltip_text("Trigger a test desktop notification now")
        test_alert_btn.connect("clicked", lambda b: test_routine_notification("Daily Routine Test", "Now"))
        header_box.append(test_alert_btn)

        self.routines_page_box.append(header_box)

        # 2. Add Routine Form
        add_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        add_box.add_css_class("input-bar-container")

        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.routine_title_entry = Gtk.Entry()
        self.routine_title_entry.set_placeholder_text("Routine title (e.g. Morning stretch)...")
        self.routine_title_entry.set_hexpand(True)
        self.routine_title_entry.add_css_class("quick-entry")
        self.routine_title_entry.connect("activate", self.on_add_routine_clicked)
        row1.append(self.routine_title_entry)

        self.routine_time_entry = Gtk.Entry()
        self.routine_time_entry.set_placeholder_text("08:30")
        self.routine_time_entry.set_max_width_chars(6)
        self.routine_time_entry.add_css_class("quick-entry")
        self.routine_time_entry.connect("activate", self.on_add_routine_clicked)
        row1.append(self.routine_time_entry)

        add_box.append(row1)

        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.routine_cat_entry = Gtk.Entry()
        self.routine_cat_entry.set_placeholder_text("Category (e.g. health, work, routine)")
        self.routine_cat_entry.set_hexpand(True)
        self.routine_cat_entry.add_css_class("quick-entry")
        self.routine_cat_entry.connect("activate", self.on_add_routine_clicked)
        row2.append(self.routine_cat_entry)

        add_btn = Gtk.Button(label="+ Add")
        add_btn.add_css_class("quick-submit-btn")
        add_btn.connect("clicked", self.on_add_routine_clicked)
        row2.append(add_btn)

        add_box.append(row2)
        self.routines_page_box.append(add_box)

        # 3. Scrolled list of routine cards
        self.routines_scroll = Gtk.ScrolledWindow()
        self.routines_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.routines_scroll.set_vexpand(True)
        self.routines_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.routines_scroll.set_child(self.routines_box)
        self.routines_page_box.append(self.routines_scroll)

    def refresh_routines(self):
        while child := self.routines_box.get_first_child():
            self.routines_box.remove(child)
        self.routine_card_widgets.clear()

        now = datetime.datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        raw_routines = self.db.get_routines(today_str)
        enriched = [calculate_routine_status(r, now) for r in raw_routines]

        done_count = sum(1 for r in enriched if r.get("is_completed_today"))
        total_count = len(enriched)
        if hasattr(self, "btn_view_routines"):
            self.btn_view_routines.set_label(f"⏰ Routines ({done_count}/{total_count})")
        if hasattr(self, "routines_summary_label"):
            self.routines_summary_label.set_text(f"{done_count} of {total_count} completed today • Automated alerts active")

        # Counts calculation
        # Rule: completed routine tasks do NOT show in "All", only in "Done"
        count_all = sum(1 for r in enriched if not r.get("is_completed_today"))
        count_urgent = sum(1 for r in enriched if not r.get("is_completed_today") and (r.get("is_due_now") or r.get("is_urgent")))
        count_done = sum(1 for r in enriched if r.get("is_completed_today"))

        counts = {
            "all": count_all,
            "urgent": count_urgent,
            "completed": count_done
        }
        labels = {
            "all": "All",
            "urgent": "Urgent",
            "completed": "Done"
        }
        for f_key, btn in self.routine_filter_buttons.items():
            btn.set_label(f"{labels.get(f_key, f_key)} ({counts.get(f_key, 0)})")

        if self.current_routine_filter == "urgent":
            filtered_routines = [r for r in enriched if not r.get("is_completed_today") and (r.get("is_due_now") or r.get("is_urgent"))]
        elif self.current_routine_filter == "completed":
            filtered_routines = [r for r in enriched if r.get("is_completed_today")]
        else:
            # "all": ONLY uncompleted routines for today per user requirement
            filtered_routines = [r for r in enriched if not r.get("is_completed_today")]

        if not filtered_routines:
            if self.current_routine_filter == "completed":
                msg = "No completed routines yet today.\nCheck one off to see it here!"
            elif self.current_routine_filter == "urgent":
                msg = "No urgent routines right now.\nEverything on track!"
            else:
                msg = "All routines completed for today! 🎉\nCheck 'Done' tab to review." if count_done > 0 else "No daily routines configured.\nAdd one above to get automated reminders!"
            empty_lbl = Gtk.Label(label=msg)
            empty_lbl.set_margin_top(30)
            empty_lbl.add_css_class("calendar-sub")
            self.routines_box.append(empty_lbl)
            return

        for r in filtered_routines:
            card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            card.add_css_class("task-card")
            card.add_css_class("routine-card")
            if r.get("is_due_now"):
                card.add_css_class("urgency-critical")

            # Check button for today's completion
            is_done = bool(r.get("is_completed_today"))
            chk_btn = Gtk.Button(label="✓" if is_done else "")
            chk_btn.add_css_class("check-btn")
            if is_done:
                chk_btn.add_css_class("checked")
            chk_btn.set_valign(Gtk.Align.CENTER)
            chk_btn.connect("clicked", lambda b, rid=r["id"]: self.on_toggle_routine_today(rid))
            card.append(chk_btn)

            # Details
            detail_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            detail_box.set_hexpand(True)

            top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            time_lbl = Gtk.Label(label=r["time_12h"])
            time_lbl.add_css_class("range-pill")
            top_row.append(time_lbl)

            title_lbl = Gtk.Label(label=r["title"], xalign=0)
            title_lbl.add_css_class("task-title")
            if is_done:
                title_lbl.add_css_class("task-completed")
            top_row.append(title_lbl)
            detail_box.append(top_row)

            sub_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            cat_lbl = Gtk.Label(label=f"@{r.get('category', 'routine')}", xalign=0)
            cat_lbl.add_css_class("task-category")
            sub_row.append(cat_lbl)

            countdown_lbl = Gtk.Label(label=r["countdown_text"], xalign=0)
            countdown_lbl.add_css_class("task-countdown")
            sub_row.append(countdown_lbl)
            detail_box.append(sub_row)
            card.append(detail_box)

            # Urgency Badge
            badge_lbl = Gtk.Label(label=r["badge_text"])
            badge_lbl.add_css_class("urgency-badge")
            for cls in r["badge_class"].split():
                badge_lbl.add_css_class(cls)
            badge_lbl.set_valign(Gtk.Align.CENTER)
            card.append(badge_lbl)

            # Notification toggle button
            has_notify = bool(r.get("notify", 1))
            bell_btn = Gtk.Button(label="🔔" if has_notify else "🔕")
            bell_btn.add_css_class("delete-btn")
            bell_btn.set_tooltip_text("Toggle Notification (On/Off)")
            bell_btn.set_valign(Gtk.Align.CENTER)
            bell_btn.connect("clicked", lambda b, rid=r["id"]: self.on_toggle_routine_notify(rid))
            card.append(bell_btn)

            # Delete button
            del_btn = Gtk.Button(label="✕")
            del_btn.add_css_class("delete-btn")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.connect("clicked", lambda b, rid=r["id"]: self.on_delete_routine(rid))
            card.append(del_btn)

            self.routine_card_widgets[r["id"]] = {
                "routine": r,
                "badge_lbl": badge_lbl,
                "countdown_lbl": countdown_lbl,
                "card": card
            }
            self.routines_box.append(card)

    def on_add_routine_clicked(self, *args):
        title = self.routine_title_entry.get_text().strip()
        time_str = self.routine_time_entry.get_text().strip() or "09:00"
        category = self.routine_cat_entry.get_text().strip() or "routine"
        if title:
            self.db.create_routine(title=title, time_str=time_str, category=category, notify=1)
            self.routine_title_entry.set_text("")
            self.routine_time_entry.set_text("")
            self.routine_cat_entry.set_text("")
            self.refresh_routines()
            if hasattr(self, "refresh_today"):
                self.refresh_today()

    def on_toggle_routine_today(self, routine_id: int):
        self.db.toggle_routine_today(routine_id)
        self.refresh_routines()
        if hasattr(self, "refresh_today"):
            self.refresh_today()

    def on_toggle_routine_notify(self, routine_id: int):
        self.db.toggle_routine_notify(routine_id)
        self.refresh_routines()
        if hasattr(self, "refresh_today"):
            self.refresh_today()

    def on_delete_routine(self, routine_id: int):
        self.db.delete_routine(routine_id)
        self.refresh_routines()
        if hasattr(self, "refresh_today"):
            self.refresh_today()

    # Daily Diary (Notes Section)
    def build_notes_page(self):
        # 1. Header with Day Switcher + Diary Title
        diary_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        diary_header.add_css_class("diary-header-box")

        # Top nav row: Prev, Today, Next, History toggle
        nav_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        prev_btn = Gtk.Button(label="◀ Prev")
        prev_btn.add_css_class("diary-nav-btn")
        prev_btn.connect("clicked", self.on_diary_prev_day)
        nav_row.append(prev_btn)

        today_btn = Gtk.Button(label="Today")
        today_btn.add_css_class("diary-nav-btn")
        today_btn.connect("clicked", self.on_diary_today)
        nav_row.append(today_btn)

        next_btn = Gtk.Button(label="Next ▶")
        next_btn.add_css_class("diary-nav-btn")
        next_btn.connect("clicked", self.on_diary_next_day)
        nav_row.append(next_btn)

        history_btn = Gtk.Button(label="📚 History")
        history_btn.add_css_class("diary-nav-btn")
        history_btn.set_hexpand(True)
        history_btn.set_halign(Gtk.Align.END)
        history_btn.connect("clicked", self.on_toggle_diary_history)
        nav_row.append(history_btn)

        diary_header.append(nav_row)

        # Date titles
        self.diary_date_label = Gtk.Label(label="📔 Daily Reflections", xalign=0)
        self.diary_date_label.add_css_class("diary-date-title")
        diary_header.append(self.diary_date_label)

        self.diary_bs_label = Gtk.Label(label="", xalign=0)
        self.diary_bs_label.add_css_class("diary-date-sub")
        diary_header.append(self.diary_bs_label)

        self.notes_page_box.append(diary_header)

        # 2. History browser container (collapsible)
        self.diary_history_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.diary_history_box.set_visible(False)
        self.notes_page_box.append(self.diary_history_box)

        # 3. New Entry Input Box
        note_entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.note_entry = Gtk.Entry()
        self.note_entry.set_placeholder_text("Write reflection / thoughts for this day...")
        self.note_entry.set_hexpand(True)
        self.note_entry.add_css_class("quick-entry")
        self.note_entry.connect("activate", self.on_add_note)

        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("quick-submit-btn")
        save_btn.connect("clicked", self.on_add_note)

        note_entry_box.append(self.note_entry)
        note_entry_box.append(save_btn)
        self.notes_page_box.append(note_entry_box)

        # 4. Scrolled list of entries for this day
        self.notes_scroll = Gtk.ScrolledWindow()
        self.notes_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.notes_scroll.set_vexpand(True)
        self.notes_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.notes_scroll.set_child(self.notes_list_box)
        self.notes_page_box.append(self.notes_scroll)

    def refresh_notes(self):
        while child := self.notes_list_box.get_first_child():
            self.notes_list_box.remove(child)

        # Update header labels with selected diary date
        try:
            dt = datetime.date.fromisoformat(self.selected_diary_date)
            bs = ad_to_bs(dt)
            is_today = (self.selected_diary_date == datetime.date.today().strftime("%Y-%m-%d"))
            today_badge = " (Today)" if is_today else ""
            self.diary_date_label.set_text(f"📔 {dt.strftime('%A, %b %d, %Y')}{today_badge}")
            self.diary_bs_label.set_text(f"नेपाली: {bs['year_np']} {bs['month_name_np']} {bs['day_np']} • {bs['month_name_en']} {bs['day']}")
        except Exception:
            self.diary_date_label.set_text(f"📔 Date: {self.selected_diary_date}")

        # Update history box if open
        if self.showing_diary_history:
            self.refresh_diary_history()

        notes = self.db.get_notes(self.selected_diary_date)
        if not notes:
            empty_lbl = Gtk.Label(label=f"No diary entries recorded for {self.selected_diary_date}.\nWrite your thoughts above!")
            empty_lbl.set_margin_top(30)
            empty_lbl.add_css_class("calendar-sub")
            self.notes_list_box.append(empty_lbl)
            return

        for n in notes:
            card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            card.add_css_class("diary-card")

            txt_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            txt_box.set_hexpand(True)

            meta_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            time_part = n["created_at"].split()[-1][:5]
            time_badge = Gtk.Label(label=f"🕒 {time_part}")
            time_badge.add_css_class("diary-time-badge")
            meta_row.append(time_badge)
            txt_box.append(meta_row)

            content_lbl = Gtk.Label(label=n["content"], xalign=0)
            content_lbl.set_wrap(True)
            txt_box.append(content_lbl)

            card.append(txt_box)

            del_btn = Gtk.Button(label="✕")
            del_btn.add_css_class("delete-btn")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.connect("clicked", lambda b, nid=n["id"]: self.on_delete_note(nid))
            card.append(del_btn)

            self.notes_list_box.append(card)

    def on_toggle_diary_history(self, btn):
        self.showing_diary_history = not self.showing_diary_history
        self.diary_history_box.set_visible(self.showing_diary_history)
        if self.showing_diary_history:
            self.refresh_diary_history()

    def refresh_diary_history(self):
        while child := self.diary_history_box.get_first_child():
            self.diary_history_box.remove(child)

        dates = self.db.get_diary_dates()
        if not dates:
            lbl = Gtk.Label(label="No past diary entries yet.", xalign=0)
            lbl.add_css_class("calendar-sub")
            self.diary_history_box.append(lbl)
            return

        title = Gtk.Label(label="Past Journal Dates:", xalign=0)
        title.add_css_class("calendar-sub")
        self.diary_history_box.append(title)

        for d_info in dates[:12]:
            d_str = d_info["date"]
            count = d_info["count"]
            item_btn = Gtk.Button(label=f"📅 {d_str} ({count} {'entry' if count == 1 else 'entries'})")
            item_btn.add_css_class("diary-history-item")
            item_btn.connect("clicked", lambda b, d=d_str: self.select_diary_date(d))
            self.diary_history_box.append(item_btn)

    def select_diary_date(self, date_str: str):
        self.selected_diary_date = date_str
        self.showing_diary_history = False
        self.diary_history_box.set_visible(False)
        self.refresh_notes()

    def on_diary_prev_day(self, btn):
        try:
            d = datetime.date.fromisoformat(self.selected_diary_date) - datetime.timedelta(days=1)
            self.selected_diary_date = d.strftime("%Y-%m-%d")
        except Exception:
            self.selected_diary_date = datetime.date.today().strftime("%Y-%m-%d")
        self.refresh_notes()

    def on_diary_next_day(self, btn):
        try:
            d = datetime.date.fromisoformat(self.selected_diary_date) + datetime.timedelta(days=1)
            self.selected_diary_date = d.strftime("%Y-%m-%d")
        except Exception:
            self.selected_diary_date = datetime.date.today().strftime("%Y-%m-%d")
        self.refresh_notes()

    def on_diary_today(self, btn):
        self.selected_diary_date = datetime.date.today().strftime("%Y-%m-%d")
        self.refresh_notes()

    def on_add_note(self, *args):
        text = self.note_entry.get_text().strip()
        if text:
            self.db.create_note(content=text, date_str=self.selected_diary_date)
            self.note_entry.set_text("")
            self.refresh_notes()
            self.refresh_calendar_grid()

    def on_delete_note(self, note_id: int):
        self.db.delete_note(note_id)
        self.refresh_notes()
        self.refresh_calendar_grid()

    # Quick Add Command Bar
    def build_quick_input_bar(self):
        input_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        input_container.add_css_class("input-bar-container")

        # Autocomplete suggestions box floating above entry
        self.suggest_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.suggest_box.add_css_class("suggest-box")
        self.suggest_box.set_visible(False)
        input_container.append(self.suggest_box)

        entry_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        prefix_lbl = Gtk.Label(label="❯")
        prefix_lbl.add_css_class("calendar-title-ad")
        entry_row.append(prefix_lbl)

        self.cmd_entry = Gtk.Entry()
        self.cmd_entry.set_placeholder_text("Finish project from Sept 8 to Sept 20 #urgent")
        self.cmd_entry.set_hexpand(True)
        self.cmd_entry.add_css_class("quick-entry")
        self.cmd_entry.connect("activate", self.on_quick_submit)
        self.cmd_entry.connect("changed", self.on_cmd_changed)
        entry_row.append(self.cmd_entry)

        submit_btn = Gtk.Button(label="Add")
        submit_btn.add_css_class("quick-submit-btn")
        submit_btn.connect("clicked", self.on_quick_submit)
        entry_row.append(submit_btn)

        input_container.append(entry_row)

        hint_lbl = Gtk.Label(
            label="Commands: /routine 08:30 <title> • from <d1> to <d2> • by <d> • #urgent • /note • [/] Focus",
            xalign=0
        )
        hint_lbl.add_css_class("hint-label")
        input_container.append(hint_lbl)

        self.sidebar_pane.append(input_container)

    def on_cmd_changed(self, entry):
        text = entry.get_text()
        while child := self.suggest_box.get_first_child():
            self.suggest_box.remove(child)

        if not text.strip():
            self.suggest_box.set_visible(False)
            return

        suggestions = []
        lower = text.lower().strip()
        today_iso = datetime.date.today().strftime("%Y-%m-%d")

        if text.startswith("/"):
            if text == "/":
                suggestions = [
                    ("/routine 08:30 Morning routine #routine", "⏰ Routine"),
                    ("/note Today's reflection...", "📔 Diary note"),
                ]
            elif text.startswith("/r"):
                suggestions = [
                    ("/routine 08:30 " if text.strip() in ("/r", "/ro", "/rou", "/rout", "/routi", "/routin", "/routine") else text + " #routine", "⏰ Routine"),
                    ("/routine 18:00 Evening review #routine", "⏰ Evening"),
                ]
            elif text.startswith("/n"):
                suggestions = [
                    ("/note " if text.strip() in ("/n", "/no", "/not", "/note") else text, "📔 Diary note"),
                ]
        elif lower.startswith("rou") or lower.startswith("daily"):
            suggestions = [
                ("/routine 08:30 Morning routine #routine", "⏰ Add Routine"),
                ("/routine 18:00 Evening review #routine", "⏰ Add Routine"),
            ]
        elif lower.startswith("not") or lower.startswith("dia"):
            suggestions = [
                (f"/note {text}", "📔 Add to Diary"),
                ("/note Today's reflection...", "📔 Add to Diary"),
            ]
        elif lower.startswith("urg"):
            suggestions = [
                (f"{text} #urgent", "Priority #urgent"),
            ]
        elif "#" in text:
            last_word = text.split()[-1]
            if last_word.startswith("#"):
                base = text[:text.rfind("#")]
                tags = ["#urgent", "#high", "#normal", "#health", "#work", "#study"]
                suggestions = [(f"{base}{t}", f"Tag {t}") for t in tags if t.startswith(last_word)]
        elif "@" in text:
            last_word = text.split()[-1]
            if last_word.startswith("@"):
                base = text[:text.rfind("@")]
                cats = ["@work", "@personal", "@health", "@study", "@routine"]
                suggestions = [(f"{base}{c}", f"Category {c}") for c in cats if c.startswith(last_word)]
        elif "from " in lower and "to " not in lower:
            suggestions = [
                (f"{text} to {today_iso}", "Set end date"),
            ]
        elif "by " in lower:
            suggestions = [
                (f"{text} #urgent", "Priority #urgent"),
                (f"{text} @work", "Category @work"),
            ]
        else:
            suggestions = [
                (f"{text} #urgent", "Priority #urgent"),
                (f"{text} by {today_iso}", "Due today"),
                (f"{text} @work", "Category @work"),
            ]

        if suggestions:
            for val, hint in suggestions[:3]:
                btn = Gtk.Button()
                btn.add_css_class("suggest-btn")
                lbl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                tag_lbl = Gtk.Label(label=val[:26] + ("..." if len(val) > 26 else ""), xalign=0)
                tag_lbl.set_hexpand(True)
                tag_lbl.add_css_class("suggest-tag")
                lbl_box.append(tag_lbl)
                hint_lbl = Gtk.Label(label=hint, xalign=1)
                hint_lbl.add_css_class("suggest-hint")
                lbl_box.append(hint_lbl)
                btn.set_child(lbl_box)
                btn.connect("clicked", lambda b, v=val: self.apply_suggestion(v))
                self.suggest_box.append(btn)
            self.suggest_box.set_visible(True)
        else:
            self.suggest_box.set_visible(False)

    def apply_suggestion(self, text_val: str):
        self.cmd_entry.set_text(text_val)
        self.cmd_entry.set_position(-1)
        self.cmd_entry.grab_focus()
        self.suggest_box.set_visible(False)

    def on_quick_submit(self, *args):
        cmd = self.cmd_entry.get_text().strip()
        if not cmd:
            return

        parsed = parse_quick_command(cmd)
        if parsed["type"] == "note":
            self.db.create_note(content=parsed["content"], date_str=self.selected_diary_date)
            self.switch_view("notes")
        elif parsed["type"] == "routine":
            self.db.create_routine(
                title=parsed["title"],
                time_str=parsed["time_str"],
                category=parsed.get("category", "routine"),
                notify=parsed.get("notify", 1)
            )
            self.switch_view("routines")
        else:
            self.db.create_task(
                title=parsed["title"],
                start_date=parsed["start_date"],
                end_date=parsed["end_date"],
                priority=parsed["priority"],
                category=parsed["category"]
            )
            self.switch_view("tasks")

        self.cmd_entry.set_text("")
        self.suggest_box.set_visible(False)
        if hasattr(self, "refresh_today"):
            self.refresh_today()
        self.refresh_calendar_grid()

    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_slash:
            if not self.cmd_entry.has_focus() and not getattr(self, "note_entry", Gtk.Entry()).has_focus() and not getattr(self, "routine_title_entry", Gtk.Entry()).has_focus():
                self.cmd_entry.grab_focus()
                return True
        return False

    def on_second_tick(self) -> bool:
        self.update_calendar_header()
        now = datetime.datetime.now()

        # Check routines and trigger desktop notification + chime every 5 seconds
        if not hasattr(self, "_tick_count"):
            self._tick_count = 0
        self._tick_count += 1
        if self._tick_count % 5 == 0:
            try:
                notified = check_and_notify_routines(self.db, now)
                if notified:
                    self.refresh_routines()
                    if hasattr(self, "refresh_today"):
                        self.refresh_today()
            except Exception as e:
                print(f"[UI] Error checking routines: {e}")

        # Update task countdowns
        for task_id, widgets in list(self.task_card_widgets.items()):
            task = widgets["task"]
            if task.get("is_completed"):
                continue

            enriched = calculate_task_urgency(task, now)
            widgets["countdown_lbl"].set_text(enriched["countdown_text"])
            widgets["badge_lbl"].set_text(enriched["badge_text"])

            badge_lbl = widgets["badge_lbl"]
            for cls in ("badge-critical", "badge-warning", "badge-healthy", "badge-overdue", "badge-upcoming", "pulse-red"):
                badge_lbl.remove_css_class(cls)
            for cls in enriched["badge_class"].split():
                badge_lbl.add_css_class(cls)

        # Update routine countdowns when on routines view
        if self.current_view == "routines":
            for r_id, widgets in list(self.routine_card_widgets.items()):
                r = widgets["routine"]
                enriched = calculate_routine_status(r, now)
                widgets["countdown_lbl"].set_text(enriched["countdown_text"])
                widgets["badge_lbl"].set_text(enriched["badge_text"])
                badge_lbl = widgets["badge_lbl"]
                for cls in ("badge-critical", "badge-warning", "badge-healthy", "badge-completed", "badge-upcoming", "pulse-red"):
                    badge_lbl.remove_css_class(cls)
                for cls in enriched["badge_class"].split():
                    badge_lbl.add_css_class(cls)

        # Update Today view countdowns when on today view
        if self.current_view == "today":
            for task_id, widgets in list(self.today_task_widgets.items()):
                task = widgets["task"]
                enriched = calculate_task_urgency(task, now)
                widgets["countdown_lbl"].set_text(enriched["countdown_text"])
                widgets["badge_lbl"].set_text(enriched["badge_text"])
                badge_lbl = widgets["badge_lbl"]
                for cls in ("badge-critical", "badge-warning", "badge-healthy", "badge-overdue", "badge-upcoming", "pulse-red"):
                    badge_lbl.remove_css_class(cls)
                for cls in enriched["badge_class"].split():
                    badge_lbl.add_css_class(cls)

            for r_id, widgets in list(self.today_routine_widgets.items()):
                r = widgets["routine"]
                enriched = calculate_routine_status(r, now)
                widgets["countdown_lbl"].set_text(enriched["countdown_text"])
                widgets["badge_lbl"].set_text(enriched["badge_text"])
                badge_lbl = widgets["badge_lbl"]
                for cls in ("badge-critical", "badge-warning", "badge-healthy", "badge-completed", "badge-upcoming", "pulse-red"):
                    badge_lbl.remove_css_class(cls)
                for cls in enriched["badge_class"].split():
                    badge_lbl.add_css_class(cls)

        return True

def position_window_on_screen(window: Gtk.Window, config: AppConfig, target_screen: Optional[int] = None):
    """
    Position window strictly within safe on-screen bounds via Xlib ctypes,
    and applies EWMH atoms to hide window from taskbar and pager if configured.
    """
    geom = config.calculate_window_geometry(target_screen_idx=target_screen)
    target_x = geom["x"]
    target_y = geom["y"]
    target_w = geom["width"]
    target_h = geom["height"]

    print(f"[Placement] Positioned on Screen {geom.get('screen_index')}: {geom.get('screen_name')} -> ({target_x}, {target_y}, {target_w}x{target_h})")

    try:
        x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XDefaultRootWindow.restype = ctypes.c_ulong
        x11.XMoveResizeWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
        x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x11.XInternAtom.restype = ctypes.c_ulong
        x11.XChangeProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        x11.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]

        disp = x11.XOpenDisplay(None)
        if disp:
            surface = window.get_surface()
            if HAS_GDK_X11 and isinstance(surface, GdkX11.X11Surface):
                xid = surface.get_xid()
                root = x11.XDefaultRootWindow(disp)

                # Move and resize to target screen coordinates
                x11.XMoveResizeWindow(disp, xid, target_x, target_y, target_w, target_h)

                atom_state = x11.XInternAtom(disp, b"_NET_WM_STATE", 0)
                atom_sticky = x11.XInternAtom(disp, b"_NET_WM_STATE_STICKY", 0)
                atom_skip_taskbar = x11.XInternAtom(disp, b"_NET_WM_STATE_SKIP_TASKBAR", 0)
                atom_skip_pager = x11.XInternAtom(disp, b"_NET_WM_STATE_SKIP_PAGER", 0)
                atom_atom = x11.XInternAtom(disp, b"ATOM", 0)

                state_atoms = []
                if config.get("pinned", True):
                    state_atoms.append(atom_sticky)
                if config.get("skip_taskbar", True):
                    state_atoms.append(atom_skip_taskbar)
                if config.get("skip_pager", True):
                    state_atoms.append(atom_skip_pager)

                if state_atoms:
                    # 1. Update XChangeProperty
                    c_states = (ctypes.c_ulong * len(state_atoms))(*state_atoms)
                    x11.XChangeProperty(disp, xid, atom_state, atom_atom, 32, 2, ctypes.cast(c_states, ctypes.c_char_p), len(state_atoms))

                    # 2. Send EWMH ClientMessage event to root window so WM (xfwm4) updates immediately
                    mask = (1 << 20) | (1 << 19) # SubstructureRedirectMask | SubstructureNotifyMask
                    for a in state_atoms:
                        ev = XEvent()
                        ev.type = 33 # ClientMessage
                        ev.xclient.type = 33
                        ev.xclient.serial = 0
                        ev.xclient.send_event = 1
                        ev.xclient.display = disp
                        ev.xclient.window = xid
                        ev.xclient.message_type = atom_state
                        ev.xclient.format = 32
                        ev.xclient.data[0] = 1 # _NET_WM_STATE_ADD
                        ev.xclient.data[1] = a
                        ev.xclient.data[2] = 0
                        ev.xclient.data[3] = 1
                        ev.xclient.data[4] = 0
                        x11.XSendEvent(disp, root, 0, mask, ctypes.byref(ev))

                x11.XFlush(disp)
            x11.XCloseDisplay(disp)
    except Exception as e:
        print(f"[Placement] X11 placement note: {e}")

def run_gtk_app(config: Optional[AppConfig] = None):
    if config is None:
        config = AppConfig()

    app = Gtk.Application(application_id="org.antigravity.productivity.dashboard")

    def on_activate(app):
        windows = app.get_windows()
        if windows:
            windows[0].present()
            return

        if os.path.exists(STYLE_PATH):
            provider = Gtk.CssProvider()
            provider.load_from_path(STYLE_PATH)
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        geom = config.calculate_window_geometry()
        win = DashboardWindow(app, config)
        win.set_default_size(geom["width"], geom["height"])
        win.present()

        # Position once window is realized
        GLib.timeout_add(100, lambda: position_window_on_screen(win, config) or False)

    app.connect("activate", on_activate)
    return app.run([])

if __name__ == "__main__":
    cfg = AppConfig()
    run_gtk_app(cfg)
