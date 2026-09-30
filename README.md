# ⚡ Apex Dual-Screen Productivity Dashboard (Linux / Ubuntu)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GTK4](https://img.shields.io/badge/GUI-GTK4%20%2F%20PyGObject-green.svg)](https://www.gtk.org/)
[![Platform Linux](https://img.shields.io/badge/platform-Linux%20%2F%20Ubuntu-orange.svg)](https://ubuntu.com/)
[![SQLite3](https://img.shields.io/badge/database-SQLite3%20WAL-lightgrey.svg)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/tests-29%20passing-brightgreen.svg)](tests/test_app.py)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

An ultra-lightweight, high-performance desktop productivity dashboard and live widget tailored specifically for dual-screen Linux setups (X11 & Wayland).

The application functions like an interactive, always-accessible desktop companion docked seamlessly to your secondary monitor (e.g. `eDP-1` or `HDMI-1`), launches automatically on system power-on, stays pinned across virtual workspaces, and **stays completely hidden from your Linux taskbar and window panel** so your workspace remains distraction-free.

---

## 🌟 What This App Does

Apex Productivity Dashboard bridges calendar systems, urgency-driven task tracking, recurring daily routines, and date-bound personal journaling into a unified split-screen desktop hub:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  GREGORIAN (AD)                  LIVE CLOCK                 BIKRAM SAMBAT (BS)         │
│  Sep 30, 2026 • Wednesday       [ 01:15:30 PM ]        14 Ashwin 2083 BS • शरद् ऋतु    │
├──────────────────────────────────────────────────────────┬─────────────────────────────┤
│  FULL MONTHLY DUAL-CALENDAR GRID (LEFT)                  │ SIDEBAR COCKPIT (RIGHT)     │
│  ◀ Prev  Today  Next ▶   [Ashwin 2083 BS / Sep-Oct 2026] │ [⭐ Today] [✓ Tasks]        │
│  ─────────────────────────────────────────────────────── │ [⏰ Routines] [📔 Diary]    │
│  Sun   Mon   Tue   Wed   Thu   Fri   Sat(शनि)            │ ─────────────────────────── │
│   -     -     -     -     -     1      2 [🔴]            │ • Overdue (-1d from y'day)  │
│   3     4     5     6     7     8      9                 │ • Active Today tasks        │
│  10    11    12    13   [14]   15     16                 │ • Routines due / upcoming   │
│  17    18    19    20    21    22     23                 │ • Real-time 1s countdowns   │
│  24    25    26    27    28    29     30                 │ • One-click complete        │
├──────────────────────────────────────────────────────────┴─────────────────────────────┤
│  [Quick Add Bar] Press '/' anywhere: "Finish project from Sep 8 to Sep 20 #urgent" ↵   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features

### 1. ⭐ Consolidated "Today" Focus Hub
- **Unified Daily View**: Combines everything demanding your attention today in a single glance.
- **Incomplete Yesterday Rollover**: Automatically identifies tasks that weren't finished yesterday and rolls them over prominently with badges like `Remaining from yesterday (-1d)`.
- **Today's Active Tasks**: Displays tasks scheduled for today with live countdowns.
- **Today's Routines**: Shows habits and routines scheduled for today; checking them off instantly updates your progress without cluttering future days.

---

### 2. 📅 Full Monthly Dual-Calendar Grid (Bikram Sambat BS + Gregorian AD)
- **Synchronized Dual-Calendar Engine**:
  - Accurate astronomical lunar-solar mapping covering years **1975 BS to 2100 BS** (**1918 AD to 2043 AD**).
  - Displays dual dates inside every single cell (e.g. Nepali date prominently with corresponding Gregorian date).
- **One-Click View Mode Toggle**: Switch between **Nepali (BS)** primary view and **English (AD)** primary view on the fly.
- **Cultural & Visual Accents**:
  - Highlights **Saturday (शनिबार)** with red weekend styling (official Nepal weekend).
  - Highlights **Today** with a glowing accent border.
  - Displays current season (**Ritu / ऋतु**: वसन्त, ग्रीष्म, वर्षा, शरद, हेमन्त, शिशिर) and Devanagari numerals (`०-९`).
- **Interactive Day Cells**:
  - Days with active tasks display colored event pills indicating deadlines.
  - Days with diary notes display journal badge icons.
  - Clicking any date filters the sidebar to display tasks and notes for that specific day and pre-fills the quick task creator.

---

### 3. ⏳ Task Management & Urgency Countdown Engine
- **Live 1-Second Urgency Engine**: Continuously updates countdown timers down to the second.
- **Multi-Day Interval Spans**: Supports project timelines spanning multiple days (e.g. `[Sep 08 → Sep 20]`).
- **Dynamic Visual Urgency Tiers**:
  - **Critical Urgency** (`< 24 hours` remaining or `#urgent`): Pulsing red badge (`5h left!`).
  - **Approaching Deadline** (`1 to 3 days` remaining or `#high`): Warning orange/yellow badge (`2 days left`).
  - **Healthy Buffer** (`> 3 days` remaining or `#normal`): Clean blue/green badge (`10 days left`).
  - **Overdue Rollover**: Clear overdue tracking (`-1d overdue`, `-3d overdue`).
- **Intelligent View Filtering**:
  - **All**: Displays active uncompleted tasks + tasks completed today (yesterday's completed tasks are automatically archived).
  - **Active**: Shows only currently active tasks within their date window.
  - **Urgent**: Filters to tasks due within 3 days or tagged `#urgent` / `#high`.
  - **Done**: Full archive of all completed tasks.

---

### 4. ⏰ Daily Recurring Routines & Automated Alert Engine
- **Daily Habit Tracking**: Configure recurring daily routines with scheduled target times (e.g. `08:30 AM Standup`, `01:00 PM Lunch`, `04:30 PM Code Review`).
- **Automated Desktop Notifications & Audio Chimes**:
  - Dispatches native Linux desktop notifications via `notify-send` when routine time arrives.
  - Plays alert chimes (`paplay` / `aplay`) using system sound themes.
  - **Duplicate Prevention**: Built-in notification logger ensures exactly one alert per routine per day.
  - **Instant Preview**: Includes a **🔔 Test Alert** button to preview notification banners and audio.
- **Dynamic Routine Badges**:
  - `Due Now!` (flashing red badge within grace period)
  - `In 45m` / `In 2h 15m` (upcoming countdown)
  - `Passed` (scheduled time passed without completion)
  - `Done today` (completed for today)
- **Sub-Filter Navigation**: Easily toggle between **All** (uncompleted routines), **Urgent**, and **Done**.

---

### 5. 📔 Date-Bound Personal Diary & Scratchpad Notes
- **Daily Journaling**: Write and save notes tied directly to specific dates.
- **Calendar Integration**: Click any past or future day on the monthly calendar grid to view or add diary entries for that date.
- **Pinned Notes**: Pin critical reference notes to the top of your diary.
- **Diary History Drawer**: View list of all dates with diary entries and entry counts.

---

### 6. 💬 Natural Language & Command-Line Quick-Add Bar
Press <kbd>/</kbd> anywhere to immediately focus the quick-add input bar:

| Command / Natural Language Pattern | What It Creates |
| :--- | :--- |
| `"Finish project from Sept 8 to Sept 20 #urgent @work"` | Multi-day project task starting Sep 8, ending Sep 20, critical urgency |
| `"Submit quarterly tax report by Sept 10 #high"` | Single deadline task due Sep 10 with high priority |
| `"Deploy v2 release in 3 days #urgent @dev"` | Relative deadline calculation from current timestamp |
| `"Client sync tomorrow 3pm #normal @work"` | Tomorrow deadline with explicit time tag |
| `"/routine 08:30 Morning workout #health"` | Recurring daily routine scheduled daily at 8:30 AM |
| `"routine: at 3pm Afternoon Coffee Break @break"` | Recurring routine scheduled daily at 3:00 PM |
| `"/note Standup sync: Database migration completed"` | Diary note recorded for today |

---

### 7. 🖥 Multi-Monitor & Linux Desktop Integration
- **Targeted Secondary Display**: Automatically detects connected monitors via `xrandr` and docks to Screen 2 (`eDP-1` / `HDMI-1`) by default.
- **Instant Screen Teleportation**: Click `🖥 Move to Screen 1` or `🖥 Move to Screen 2` in the top header to teleport the window between monitors instantly without restarting.
- **Completely Hidden From Taskbar & Pager**:
  - Uses X11 EWMH properties: `_NET_WM_STATE_SKIP_TASKBAR` and `_NET_WM_STATE_SKIP_PAGER`.
  - Window never appears in your panel, dock, or Alt-Tab switcher.
- **Sticky / Pinned Across Desktops**: Window remains visible across all virtual workspaces (`_NET_WM_STATE_STICKY`).
- **Robust Autostart on Boot**:
  - Startup script (`scripts/autostart.sh`) waits for display server and multi-monitor detection before positioning the widget.

---

### 8. 🌐 Dual Interface Architecture: Native GTK4 + Web Dashboard
- **Native GTK4 Application**: Modern GTK4 desktop widget with dark CSS styling, zero lag, and minimal RAM footprint.
- **Zero-Dependency Web Dashboard**: Embedded standard library HTTP server (`main.py --web`) providing a browser-accessible version with glassmorphic UI, Web Audio API chimes, and HTML5 Web Notifications.
- **Hybrid Mode**: Run the GTK4 widget on Screen 2 while exposing the REST API on `localhost:8765` (`main.py --hybrid`).

---

## 📂 Project Architecture

```
adv-todo-and-calendar/
├── app/
│   ├── bs_data.py            # Bikram Sambat astronomical calendar dataset (1975-2100 BS)
│   ├── config.py             # Config manager & multi-monitor geometry detection
│   ├── countdown.py          # Real-time urgency calculation & rollover logic
│   ├── database.py           # SQLite database engine (WAL mode) for tasks, routines, notes
│   ├── nepali_calendar.py    # BS <-> AD conversion & 6x7 monthly grid generator
│   ├── notifier.py           # Linux desktop notifications & sound alert engine
│   ├── parser.py             # Natural language command and date-range parser
│   ├── server.py             # Embedded REST API & HTTP dashboard server
│   ├── ui_gtk.py             # Native GTK4 desktop widget implementation
│   └── styles/
│       └── style.css         # Modern dark theme stylesheet for GTK4
├── autostart/
│   └── dualscreen-dashboard.desktop  # Linux autostart desktop entry
├── scripts/
│   ├── autostart.sh          # Boot script with monitor detection delay
│   ├── install_autostart.sh  # Autostart installer script
│   └── run.sh                # Main executable launcher
├── tests/
│   └── test_app.py           # 29 automated unit tests
├── web/
│   ├── index.html            # Web dashboard markup
│   ├── app.js                # Web dashboard client controller
│   └── style.css             # Glassmorphism dark web theme
├── config.json               # Persistent user settings
├── main.py                   # Application entry point & CLI flags
└── tasks.db                  # Local SQLite database
```

---

## ⚡ Getting Started

### Prerequisites (Ubuntu / Debian / Linux Mint)
```bash
sudo apt update
sudo apt install -y python3 python3-gi gir1.2-gtk-4.0 libnotify-bin pulseaudio-utils x11-utils
```

### 1. Launch the Native GTK4 Desktop Widget
```bash
# Clone the repository
git clone https://github.com/satyam-th/wallpaper.git adv-todo-and-calendar
cd adv-todo-and-calendar

# Run on Screen 2 (default)
./scripts/run.sh
```

### 2. Command-Line Options
```bash
# Launch on Primary Monitor (Screen 1):
python3 main.py --screen 1

# Launch as a Web Dashboard in your default browser:
python3 main.py --web --port 8765

# Launch both GTK4 desktop widget AND background web REST server:
python3 main.py --hybrid --port 8765

# Display connected monitors and calculated geometries:
python3 main.py --list-monitors

# Run with standard window borders:
python3 main.py --show-taskbar
```

---

## 🔄 Automatic Launch on System Boot

To automatically start the dashboard docked to your secondary monitor on system power-on:

```bash
cd adv-todo-and-calendar
./scripts/install_autostart.sh
```

To remove or disable autostart:
```bash
rm -f ~/.config/autostart/dualscreen-dashboard.desktop
```

---

## 🔌 REST API Reference

When running the web server (`--web` or `--hybrid`), the embedded REST API is available on `http://127.0.0.1:8765`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/calendar/dual` | Returns synchronized Gregorian (AD) and Bikram Sambat (BS) date info |
| `GET` | `/api/calendar/month/bs?year=&month=` | Generates BS monthly calendar grid with dual AD dates |
| `GET` | `/api/calendar/month/ad?year=&month=` | Generates AD monthly calendar grid with dual BS dates |
| `GET` | `/api/tasks` | Returns all tasks with real-time urgency and countdowns |
| `POST` | `/api/tasks` | Creates a new task (`title`, `start_date`, `end_date`, `priority`, etc.) |
| `PUT` | `/api/tasks/{id}/toggle` | Toggles task completion state |
| `DELETE`| `/api/tasks/{id}` | Deletes a task |
| `GET` | `/api/routines` | Returns daily routines with live status badges |
| `POST` | `/api/routines` | Creates a daily routine (`title`, `time_str`, `category`, `notify`) |
| `PUT` | `/api/routines/{id}/toggle` | Toggles routine completion for today |
| `PUT` | `/api/routines/{id}/notify` | Toggles notifications for routine |
| `POST` | `/api/routines/{id}/test` | Triggers a test desktop notification for routine |
| `DELETE`| `/api/routines/{id}` | Deletes a routine |
| `GET` | `/api/notes?date=YYYY-MM-DD` | Returns diary notes for specific date |
| `POST` | `/api/notes` | Creates a diary note (`content`, `date`, `is_pinned`) |
| `DELETE`| `/api/notes/{id}` | Deletes a diary note |
| `GET` | `/api/diary/dates` | Returns list of dates containing diary entries with entry counts |
| `POST` | `/api/add` | Unified natural language quick command processor |
| `GET` | `/api/monitors` | Detects and returns connected monitor geometries |
| `GET` | `/api/health` | Health check endpoint |

---

## 🧪 Automated Unit Tests

The test suite thoroughly verifies date conversions, SQLite CRUD operations, natural language parsing, urgency calculations, routine notifications, and rollover behavior:

```bash
PYTHONPATH=. python3 tests/test_app.py
```

```text
Ran 29 tests in 1.109s

OK
```

---

## 📄 License

This project is licensed under the MIT License - feel free to customize and adapt it for your productivity workflows.
