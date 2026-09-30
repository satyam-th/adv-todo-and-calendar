#!/usr/bin/env bash
# Robust power-on autostart launcher for Apex Productivity Dashboard

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${APP_DIR}"

LOG_FILE="${APP_DIR}/autostart.log"
# Rotate log if larger than 1MB
if [ -f "${LOG_FILE}" ] && [ $(stat -c%s "${LOG_FILE}" 2>/dev/null || echo 0) -gt 1048576 ]; then
    tail -n 500 "${LOG_FILE}" > "${LOG_FILE}.tmp" 2>/dev/null && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
fi

exec >> "${LOG_FILE}" 2>&1
echo "=================================================="
echo "Apex Dashboard Autostart: $(date)"
echo "Working directory: ${APP_DIR}"

# 1. Ensure DISPLAY environment is available
if [ -z "${DISPLAY}" ]; then
    export DISPLAY=":0.0"
fi
echo "DISPLAY=${DISPLAY}"

# Ensure XAUTHORITY is available
if [ -z "${XAUTHORITY}" ] && [ -f "${HOME}/.Xauthority" ]; then
    export XAUTHORITY="${HOME}/.Xauthority"
fi

# Ensure DBUS session bus is available if in user space
if [ -z "${DBUS_SESSION_BUS_ADDRESS}" ] && [ -e "/run/user/$(id -u)/bus" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
fi

export GTK_THEME="Adwaita:dark"

# 2. Wait up to 15 seconds for X11 & xrandr to respond after boot
for i in {1..15}; do
    if xrandr --listmonitors >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# If an external monitor (like HDMI-1) is attached, wait up to 5 seconds for it to register
for i in {1..5}; do
    MON_COUNT=$(xrandr --listmonitors 2>/dev/null | awk '/Monitors:/ {print $2}')
    if [ "${MON_COUNT:-0}" -ge 2 ]; then
        echo "Detected dual monitors after ${i}s check."
        break
    fi
    sleep 1
done

echo "Current monitor configuration:"
xrandr --listmonitors 2>&1 || true

# Small buffer for desktop panel (xfce4-panel) and window manager (xfwm4) to fully initialize
sleep 2

# 3. Launch dashboard on Screen 2 with full calendar and hidden from taskbar
echo "Launching Apex Dashboard..."
exec /usr/bin/python3 "${APP_DIR}/main.py" --screen 2 --dock split --skip-taskbar
