# ⚡ Apex Dual-Screen Productivity Dashboard (Linux / Ubuntu)

A modern, ultra-lightweight desktop productivity dashboard and live widget tailored specifically for dual-screen Linux setups (X11 & Wayland).

The application functions like an interactive desktop widget that docks seamlessly to your secondary monitor (e.g. `eDP-1` or `HDMI-1`), automatically launches on system power-on, stays pinned across virtual workspaces, and **stays completely hidden from your taskbar / panel** so your panel remains clean!

---

## 🌟 Key Features

### 1. Dual-Layout: Full Monthly Calendar (Left) + Task Sidebar (Right)
- **Full Monthly Calendar Grid**:
  - Displays full month view with 6x7 day cells (e.g. **Bhadra 2083 BS / September 2026 AD**).
  - Every day cell displays both the primary month date and corresponding dual date.
  - Highlights **Today** with glowing accent styling.
  - Highlights **Saturday (शनि)** with weekend red accent styling.
  - Interactive month navigation controls (`◀ Prev Month`, `Today`, `Next Month ▶`).
  - View Toggle: Switch between **Nepali (BS)** view and **English (AD)** view with one click.
  - Task Indicators: Days with active deadlines display colored event pills (e.g., `🔴 Submit client report`).
  - Clicking any date pre-fills the quick-add bar for that day.
- **Dynamic Task & Deadline Sidebar**:
  - Urgency Engine with real-time 1-second countdowns.
  - **Green / Blue**: Healthy buffer (> 3 days).
  - **Yellow / Orange**: Approaching deadline (1 to 3 days).
  - **Pulsing Red / Emergency Badge**: Critical urgency (< 24 hours).
  - Multi-day intervals: `[Sep 08 → Sep 20]`.
  - Day-specific scratchpad notes.

### 2. ⏰ Daily Routine & Automated Notification System
- **Daily Recurring Routines & Habits**:
  - Set scheduled daily habits with specific target times (e.g. `08:30 AM`, `01:00 PM`, `04:30 PM`).
  - Dedicated **⏰ Routines** tab in both native GTK4 widget and Web dashboard.
  - Track completions per day (check off routines for today without affecting future days).
  - Live countdown and dynamic status badges (`Due Now!`, `In 45m`, `Passed`, `Done today`).
- **Automated Desktop Notifications & Audio Chimes**:
  - Dispatches native Linux desktop notifications via `notify-send` at routine scheduled times.
  - Plays audio notification chimes (`paplay` / system alert sounds).
  - Intelligent duplicate suppression (ensures only one alert per routine per day).
  - Immediate **🔔 Test Alert** button to preview notification audio and banners.
  - Full support in both GTK4 desktop widget and browser web dashboard (via HTML5 Web Notifications API & Web Audio API).

### 3. Hidden From Taskbar & Pager (Clean Desktop Integration)
- Automatically sets X11 EWMH hints:
  - `_NET_WM_STATE_SKIP_TASKBAR`: Hides the window name and icon completely from your Linux taskbar, window buttons panel, and dock.
  - `_NET_WM_STATE_SKIP_PAGER`: Excludes the window from workspace pagers and alt-tab lists.
  - `_NET_WM_STATE_STICKY`: Keeps the widget pinned across all virtual workspaces.

### 4. Automatic Launch on Power-On / Boot
- Installs to `~/.config/autostart/dualscreen-dashboard.desktop`.
- Includes a startup delay and multi-monitor detection loop in `scripts/autostart.sh` so Screen 2 is guaranteed to be detected after boot before the window positions itself.

### 5. Natural Language Quick-Add Input Bar
- Quick command entry at the bottom of the sidebar:
  - `"/routine 08:30 Morning workout #health"`
  - `"/routine at 3pm Afternoon Coffee Break @work"`
  - `"Finish project from Sept 8 to Sept 20 #urgent"`
  - `"Submit quarterly tax report by Sept 10 #high"`
  - `"Sync with design team tomorrow 3pm #normal @work"`
  - `"/note Deploy database migration before EOD"`
- Press <kbd>/</kbd> anywhere to immediately focus the input bar.

### 6. Instant Screen Switcher
- Click the `🖥 Move to Screen 1` / `🖥 Move to Screen 2` button in the top header to instantly teleport the dashboard between monitors without restarting.

---

## 🚀 Step-by-Step Instructions

### 1. Launch Manually (Docked to Screen 2 with Full Calendar & Hidden Taskbar)
```bash
cd /home/v14/Documents/wallpaper
./scripts/run.sh
```

### 2. Enable Autostart on System Power-On
To ensure the dashboard automatically starts on boot docked on Screen 2:
```bash
cd /home/v14/Documents/wallpaper
./scripts/install_autostart.sh
```

To disable autostart in the future:
```bash
rm -f ~/.config/autostart/dualscreen-dashboard.desktop
```

### 3. Custom Commands & Flags
```bash
# Launch on Screen 1 instead:
./scripts/run.sh --screen 1

# If you ever want the window to appear on the taskbar:
./scripts/run.sh --show-taskbar

# Launch web dashboard in browser:
python3 main.py --web --port 8765
```

---

## 🧪 Unit Tests
```bash
PYTHONPATH=. python3 tests/test_app.py
```
*(Runs 15 automated tests verifying BS/AD conversions, month grid generation, and urgency calculations.)*
