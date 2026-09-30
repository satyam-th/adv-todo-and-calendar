#!/usr/bin/env python3
"""
Apex Productivity Dashboard • Dual-Screen Linux Live Widget
Split Dashboard: Full Monthly Dual Calendar (Left) + Task & Deadline Sidebar (Right).
Hides from Linux taskbar and pager for seamless desktop widget integration.
"""

from __future__ import annotations
import os
import sys
import argparse
import webbrowser
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import AppConfig, detect_monitors
from app.database import Database
from app.server import start_server
from app.ui_gtk import run_gtk_app

def print_banner():
    banner = r"""
    ╔══════════════════════════════════════════════════════════════╗
    ║       APEX PRODUCTIVITY DASHBOARD • DUAL-SCREEN HUB          ║
    ║   Full Monthly Calendar (BS+AD) • Urgency Engine • Tasks     ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    parser = argparse.ArgumentParser(
        description="Lightweight desktop productivity dashboard tailored for Linux dual-screen setups."
    )
    parser.add_argument(
        "--screen", type=int, default=None,
        help="Target monitor number (1: Primary, 2: Secondary). Default: Screen 2"
    )
    parser.add_argument(
        "--dock", choices=["split", "right", "left", "fill", "float"], default=None,
        help="Display layout mode (default: split - Full Calendar on Left + Sidebar on Right)"
    )
    parser.add_argument(
        "--width", type=int, default=None,
        help="Sidebar width in pixels (default: 390)"
    )
    parser.add_argument(
        "--borderless", action="store_true",
        help="Run without window titlebars / borders"
    )
    parser.add_argument(
        "--show-taskbar", action="store_true",
        help="Show window name and icon in the Linux panel/taskbar (default is hidden)"
    )
    parser.add_argument(
        "--skip-taskbar", action="store_true", default=True,
        help="Hide window name and icon from the Linux panel/taskbar (default: True)"
    )
    parser.add_argument(
        "--unpinned", action="store_true",
        help="Do not pin to all workspaces (by default widget stays visible on all virtual desktops)"
    )
    parser.add_argument(
        "--web", action="store_true",
        help="Launch as a web dashboard in your default browser"
    )
    parser.add_argument(
        "--hybrid", action="store_true",
        help="Launch both GTK4 desktop widget on Screen 2 AND background web server"
    )
    parser.add_argument(
        "--port", type=int, default=8765,
        help="Port for the embedded web server (default: 8765)"
    )
    parser.add_argument(
        "--list-monitors", action="store_true",
        help="Display connected monitors and calculated geometries, then exit"
    )

    args = parser.parse_args()

    if args.list_monitors:
        print_banner()
        monitors = detect_monitors()
        print(f"Detected {len(monitors)} connected monitor(s):")
        for m in monitors:
            p_tag = " (PRIMARY)" if m.get("primary") else ""
            print(f"  • Screen {m['index']}: {m['name']} -> {m['width']}x{m['height']} at +{m['x']}+{m['y']}{p_tag}")
        return

    config = AppConfig()

    if args.screen is not None:
        config.set("target_screen", args.screen)
    if args.dock is not None:
        config.set("dock_mode", args.dock)
    if args.width is not None:
        config.set("sidebar_width", args.width)
    if args.borderless:
        config.set("borderless", True)
    if args.show_taskbar:
        config.set("skip_taskbar", False)
        config.set("skip_pager", False)
    else:
        config.set("skip_taskbar", True)
        config.set("skip_pager", True)

    if args.unpinned:
        config.set("pinned", False)

    print_banner()
    monitors = detect_monitors()
    target_scr = config.get("target_screen", 2)
    if not any(m["index"] == target_scr for m in monitors):
        target_scr = len(monitors)

    geom = config.calculate_window_geometry(target_screen_idx=target_scr)
    print(f"[*] Target Monitor : Screen {target_scr} ({geom.get('screen_name', 'Default')})")
    print(f"[*] On-Screen Rect : {geom['width']}x{geom['height']} at +{geom['x']}+{geom['y']}")
    print(f"[*] Layout Mode    : {config.get('dock_mode', 'split').upper()} (Full Calendar Left + Sidebar Right)")
    print(f"[*] Taskbar State  : {'HIDDEN from taskbar & pager' if config.get('skip_taskbar') else 'Visible in taskbar'}")
    print(f"[*] Pinned Desktop : {config.get('pinned', True)}")

    if args.web:
        port = args.port
        url = f"http://127.0.0.1:{port}"
        print(f"[*] Starting Web Dashboard on {url} ...")
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        start_server(port=port, background=False)
        return

    if args.hybrid:
        port = args.port
        print(f"[*] Starting background REST & Web server on http://127.0.0.1:{port} ...")
        start_server(port=port, background=True)

    print(f"[*] Launching native GTK4 widget on Screen {target_scr}...")
    run_gtk_app(config)

if __name__ == "__main__":
    main()
