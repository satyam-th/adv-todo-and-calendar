#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
AUTOSTART_DIR="${HOME}/.config/autostart"
DESKTOP_FILE="${AUTOSTART_DIR}/dualscreen-dashboard.desktop"
AUTOSTART_SH="${APP_DIR}/scripts/autostart.sh"

echo "=========================================================="
echo " Apex Dashboard: Linux & Ubuntu Power-On Autostart Setup"
echo "=========================================================="
echo "[*] App Directory       : ${APP_DIR}"
echo "[*] Autostart Script    : ${AUTOSTART_SH}"
echo "[*] Target Desktop File : ${DESKTOP_FILE}"

mkdir -p "${AUTOSTART_DIR}"
chmod +x "${AUTOSTART_SH}"

cat << DESKTOP_EOF > "${DESKTOP_FILE}"
[Desktop Entry]
Type=Application
Version=1.0
Name=Apex Dual-Screen Productivity Dashboard
Comment=Interactive desktop widget with full monthly calendar, tasks, and hidden from taskbar
Exec=${AUTOSTART_SH}
Path=${APP_DIR}
Terminal=false
Categories=Utility;Office;Productivity;
StartupNotify=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=3
DESKTOP_EOF

chmod +x "${DESKTOP_FILE}"

echo "[✓] Autostart successfully configured for system power-on / boot!"
echo "[✓] The dashboard will automatically launch docked to Screen 2,"
echo "    with full monthly calendar on the left, tasks on the right,"
echo "    and completely hidden from the Linux taskbar/panel."
echo "=========================================================="
