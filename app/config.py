"""
Configuration and Multi-Monitor Geometry Management.
Detects Linux X11/Wayland screens and calculates accurate on-screen coordinates.
"""

from __future__ import annotations
import os
import json
import subprocess
import re
from typing import List, Dict, Any, Optional

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

DEFAULT_CONFIG = {
    "target_screen": 2,          # 1: Primary (HDMI-1), 2: Secondary (eDP-1)
    "dock_mode": "split",        # "split" (Calendar + Sidebar), "right", "left", "fill", "float"
    "sidebar_width": 390,        # Width of task sidebar in split mode
    "calendar_mode": "bs",       # "bs" (Bikram Sambat default) or "ad" (Gregorian)
    "borderless": False,         # False = safe standard titlebar so window can be dragged/moved freely
    "pinned": True,              # True: sticky across all virtual desktops
    "skip_taskbar": True,        # True: completely hides window name and icon from taskbar / panel
    "skip_pager": True,          # True: hides window from alt-tab and workspace pagers
    "web_server_port": 8765,     # Web dashboard REST port
    "auto_refresh_sec": 1        # Real-time countdown refresh interval
}

def detect_monitors() -> List[Dict[str, Any]]:
    """Detect all attached monitors via xrandr or fallback."""
    screens = []
    try:
        out = subprocess.check_output(["xrandr", "--listmonitors"], text=True)
        for line in out.strip().split("\n")[1:]:
            parts = line.strip().split()
            if len(parts) >= 4:
                idx = int(parts[0].replace(":", ""))
                name = parts[-1]
                geom_part = parts[2]
                is_primary = ("*" in parts[1]) or (idx == 0)

                m = re.search(r"(\d+)(?:/\d+)?x(\d+)(?:/\d+)?\+(\d+)\+(\d+)", geom_part)
                if m:
                    w, h, x, y = map(int, m.groups())
                    screens.append({
                        "index": idx + 1,  # 1-based index
                        "name": name,
                        "width": w,
                        "height": h,
                        "x": x,
                        "y": y,
                        "primary": is_primary
                    })
    except Exception:
        screens = [{
            "index": 1,
            "name": "Default",
            "width": 1920,
            "height": 1080,
            "x": 0,
            "y": 0,
            "primary": True
        }]
    return screens

class AppConfig:
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
            except Exception as e:
                print(f"[Config] Error loading config file: {e}")

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[Config] Error saving config file: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        self.data[key] = value
        self.save()

    def calculate_window_geometry(self, target_screen_idx: Optional[int] = None,
                                  dock_mode: Optional[str] = None,
                                  width: Optional[int] = None) -> Dict[str, Any]:
        monitors = detect_monitors()
        screen_idx = target_screen_idx or self.data.get("target_screen", 2)
        mode = dock_mode or self.data.get("dock_mode", "split")
        side_w = width or self.data.get("sidebar_width", 390)

        chosen = None
        for m in monitors:
            if m["index"] == screen_idx:
                chosen = m
                break
        if chosen is None:
            chosen = monitors[-1] if len(monitors) > 1 else monitors[0]

        mx, my = chosen["x"], chosen["y"]
        mw, mh = chosen["width"], chosen["height"]

        pad_top = 28
        pad_bottom = 12
        pad_x = 8
        usable_h = max(600, mh - pad_top - pad_bottom)

        if mode in ("split", "fill"):
            w = mw - (pad_x * 2)
            h = usable_h
            x = mx + pad_x
            y = my + pad_top
            return {"x": x, "y": y, "width": w, "height": h, "screen_name": chosen["name"], "screen_index": chosen["index"]}

        elif mode == "right":
            w = min(side_w, mw - 40)
            h = usable_h
            x = mx + (mw - w - pad_x)
            y = my + pad_top
            return {"x": x, "y": y, "width": w, "height": h, "screen_name": chosen["name"], "screen_index": chosen["index"]}

        elif mode == "left":
            w = min(side_w, mw - 40)
            h = usable_h
            x = mx + pad_x
            y = my + pad_top
            return {"x": x, "y": y, "width": w, "height": h, "screen_name": chosen["name"], "screen_index": chosen["index"]}

        else:
            w = min(1200, mw - 40)
            h = min(720, usable_h)
            x = mx + (mw - w) // 2
            y = my + pad_top + (usable_h - h) // 2
            return {"x": x, "y": y, "width": w, "height": h, "screen_name": chosen["name"], "screen_index": chosen["index"]}

if __name__ == "__main__":
    cfg = AppConfig()
    print("Default config skip_taskbar:", cfg.get("skip_taskbar"))
