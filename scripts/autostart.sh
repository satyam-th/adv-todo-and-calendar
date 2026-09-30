#!/usr/bin/env bash
# Robust power-on autostart launcher for Apex Productivity Dashboard

# 1. Ensure DISPLAY environment is available
if [ -z "${DISPLAY}" ]; then
    export DISPLAY=":0.0"
fi

export GTK_THEME="Adwaita:dark"

# 2. Wait up to 15 seconds for X11 & multi-monitor setup to settle after boot
for i in {1..15}; do
    if xrandr --listmonitors >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Small buffer for desktop panel (xfce4-panel) to load
sleep 2

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${APP_DIR}"

# 3. Launch dashboard on Screen 2 with full calendar and hidden from taskbar
exec /usr/bin/python3 "${APP_DIR}/main.py" --screen 2 --dock split --skip-taskbar
