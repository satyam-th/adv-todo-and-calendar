"""
Notification and Alert Engine for Daily Routines and Deadlines.
Provides desktop notifications via freedesktop notify-send, sound chimes,
and real-time routine schedule status calculations.
"""

from __future__ import annotations
import os
import shutil
import subprocess
import threading
import datetime
from typing import Dict, Any, Optional, List

SOUND_FILES = [
    "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga",
    "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga",
    "/usr/share/sounds/freedesktop/stereo/message.oga",
    "/usr/share/sounds/freedesktop/stereo/complete.oga"
]

def find_available_sound() -> Optional[str]:
    """Return path to first available system sound file."""
    for s in SOUND_FILES:
        if os.path.exists(s):
            return s
    return None

def play_chime(sound_file: Optional[str] = None):
    """Play notification sound asynchronously without blocking."""
    sound = sound_file or find_available_sound()
    if not sound:
        return

    def _play():
        try:
            if shutil.which("paplay"):
                subprocess.run(["paplay", sound], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            elif shutil.which("aplay"):
                subprocess.run(["aplay", "-q", sound], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except Exception as e:
            print(f"[Notifier] Sound playback error: {e}")

    threading.Thread(target=_play, daemon=True).start()

def send_desktop_notification(
    title: str,
    message: str,
    sound: bool = True,
    urgency: str = "normal",
    icon: str = "appointment-soon"
) -> bool:
    """
    Send freedesktop desktop notification using notify-send.
    Safely falls back if notify-send is unavailable.
    """
    if sound:
        play_chime()

    if shutil.which("notify-send"):
        try:
            subprocess.run(
                [
                    "notify-send",
                    "-a", "Apex Dashboard",
                    "-u", urgency,
                    "-i", icon,
                    title,
                    message
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            return True
        except Exception as e:
            print(f"[Notifier] Failed to invoke notify-send: {e}")
            return False
    else:
        print(f"[Notifier] [DESKTOP ALERT] {title} - {message}")
        return False

def format_time_12h(time_str: str) -> str:
    """Convert '09:00' to '9:00 AM' and '16:30' to '4:30 PM'."""
    try:
        parts = time_str.split(":")
        h, m = int(parts[0]), int(parts[1])
        dt = datetime.time(h, m)
        formatted = dt.strftime("%I:%M %p").lstrip("0")
        return formatted
    except Exception:
        return time_str

def calculate_routine_status(routine: Dict[str, Any], now: Optional[datetime.datetime] = None) -> Dict[str, Any]:
    """
    Enrich a routine with live countdown, urgency badge, and status classification.
    """
    if now is None:
        now = datetime.datetime.now()

    time_str = routine.get("time_str", "09:00")
    try:
        parts = time_str.split(":")
        r_hour, r_min = int(parts[0]), int(parts[1])
    except Exception:
        r_hour, r_min = 9, 0

    sched_today = now.replace(hour=r_hour, minute=r_min, second=0, microsecond=0)
    is_completed = bool(routine.get("is_completed_today", 0))
    time_12h = format_time_12h(time_str)

    if is_completed:
        return {
            **routine,
            "status": "completed",
            "time_12h": time_12h,
            "badge_class": "badge-completed",
            "badge_text": "Done today",
            "countdown_text": "Completed for today",
            "is_due_now": False
        }

    diff_sec = (sched_today - now).total_seconds()

    # If within 5 minutes past or 1 minute before -> Due Now
    if -300 <= diff_sec <= 60:
        return {
            **routine,
            "status": "due_now",
            "time_12h": time_12h,
            "badge_class": "badge-critical pulse-red",
            "badge_text": "Due Now!",
            "countdown_text": "Scheduled for now!",
            "is_due_now": True
        }
    elif diff_sec > 60:
        # Upcoming today
        mins = int(diff_sec // 60)
        hours = int(mins // 60)
        rem_mins = mins % 60
        if hours > 0:
            cd_text = f"In {hours}h {rem_mins}m"
        else:
            cd_text = f"In {rem_mins}m"

        badge_class = "badge-warning" if mins <= 60 else "badge-upcoming"
        return {
            **routine,
            "status": "upcoming",
            "time_12h": time_12h,
            "badge_class": badge_class,
            "badge_text": cd_text,
            "countdown_text": f"Scheduled at {time_12h}",
            "is_due_now": False
        }
    else:
        # Past today
        abs_sec = abs(diff_sec)
        hours = int(abs_sec // 3600)
        mins = int((abs_sec % 3600) // 60)
        passed_text = f"{hours}h ago" if hours > 0 else f"{mins}m ago"
        return {
            **routine,
            "status": "past",
            "time_12h": time_12h,
            "badge_class": "badge-healthy",
            "badge_text": f"Passed ({time_12h})",
            "countdown_text": f"Passed {passed_text} • Not marked done",
            "is_due_now": False
        }

def check_and_notify_routines(db: Any, now: Optional[datetime.datetime] = None) -> List[Dict[str, Any]]:
    """
    Check all active routines for current time.
    Sends desktop notification for routines that reached their scheduled time today
    and haven't yet been notified.
    Returns list of newly notified routine dicts.
    """
    if now is None:
        now = datetime.datetime.now()

    today_str = now.strftime("%Y-%m-%d")
    weekday_str = str(now.weekday())  # 0=Mon, 6=Sun

    notified_routines = []
    routines = db.get_routines(today_str)

    for r in routines:
        if not r.get("is_active", 1) or not r.get("notify", 1):
            continue

        # Check weekday filter
        allowed_days = [d.strip() for d in r.get("days_of_week", "0,1,2,3,4,5,6").split(",") if d.strip()]
        if weekday_str not in allowed_days and "all" not in allowed_days:
            continue

        # Check if already completed today (don't alert if user already checked it off)
        if r.get("is_completed_today"):
            continue

        # Check if already notified today
        if r.get("has_notified_today") or db.has_routine_been_notified(r["id"], today_str):
            continue

        # Parse routine time
        time_str = r.get("time_str", "09:00")
        try:
            parts = time_str.split(":")
            r_hour, r_min = int(parts[0]), int(parts[1])
        except Exception:
            continue

        scheduled_dt = now.replace(hour=r_hour, minute=r_min, second=0, microsecond=0)
        offset_mins = r.get("notify_offset_minutes", 0)
        target_dt = scheduled_dt - datetime.timedelta(minutes=offset_mins)

        # Trigger condition:
        # Current time has reached or passed target time, within 15 minutes grace period
        diff_sec = (now - target_dt).total_seconds()
        if 0 <= diff_sec <= 900:
            time_12h = format_time_12h(time_str)
            title = f"⏰ Routine Reminder: {r['title']}"
            category = r.get("category", "routine")
            body = f"Scheduled for {time_12h} (@{category}). Time to get started!"

            success = send_desktop_notification(
                title=title,
                message=body,
                sound=True,
                urgency="normal",
                icon="appointment-soon"
            )
            db.record_routine_notification(r["id"], today_str)
            notified_routines.append({
                **r,
                "notification_title": title,
                "notification_body": body,
                "time_12h": time_12h
            })

    return notified_routines

def test_routine_notification(title: str, time_str: str) -> bool:
    """Trigger a test notification for a routine."""
    time_12h = format_time_12h(time_str)
    return send_desktop_notification(
        title=f"⏰ [Test] Routine: {title}",
        message=f"Test notification successful! Scheduled daily for {time_12h}.",
        sound=True,
        urgency="normal",
        icon="appointment-soon"
    )
