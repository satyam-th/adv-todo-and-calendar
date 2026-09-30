"""
Countdown & Urgency Engine for Tasks.
Calculates real-time deadlines, remaining buffers, active ranges, and visual badges.
"""

from __future__ import annotations
import datetime
from typing import Dict, Any, Optional

def parse_iso_datetime(dt_str: str) -> datetime.datetime:
    """Parse ISO or standard YYYY-MM-DD [HH:MM[:SS]] string into datetime."""
    dt_str = dt_str.strip()
    # Try with time
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    # Default fallback
    return datetime.datetime.now()

def format_short_month_day(dt: datetime.datetime) -> str:
    """Format datetime as e.g. 'Sept 08'."""
    month_name = dt.strftime("%b")
    return f"{month_name} {dt.day:02d}"

def calculate_task_urgency(task: Dict[str, Any], now: Optional[datetime.datetime] = None) -> Dict[str, Any]:
    """
    Enrich task dictionary with real-time countdown, urgency classification, and badge metadata.
    """
    if now is None:
        now = datetime.datetime.now()

    is_completed = bool(task.get("is_completed", 0))
    start_dt = parse_iso_datetime(task.get("start_date", now.strftime("%Y-%m-%d")))
    end_dt = parse_iso_datetime(task.get("end_date", now.strftime("%Y-%m-%d 23:59:59")))

    # Range calculation
    is_multi_day = (end_dt.date() - start_dt.date()).days > 0
    range_tag = f"{format_short_month_day(start_dt)} → {format_short_month_day(end_dt)}" if is_multi_day else format_short_month_day(end_dt)
    is_active_range = (start_dt <= now <= end_dt)
    is_upcoming = (now < start_dt)
    is_active = (not is_completed) and (not is_upcoming)
    priority = str(task.get("priority", "normal")).lower()

    if is_completed:
        completed_at = task.get("completed_at") or ""
        is_completed_today = bool(completed_at[:10] == now.strftime("%Y-%m-%d"))
        return {
            **task,
            "status": "completed",
            "urgency": "completed",
            "urgency_class": "urgency-completed",
            "badge_class": "badge-completed",
            "badge_text": "Completed",
            "countdown_text": "Completed",
            "seconds_remaining": 0,
            "range_tag": range_tag,
            "is_multi_day": is_multi_day,
            "is_active_range": False,
            "is_upcoming": False,
            "is_active": False,
            "is_urgent": False,
            "is_completed_today": is_completed_today,
            "is_overdue": False,
            "overdue_days": 0,
            "is_from_yesterday": False,
            "overdue_label": ""
        }

    delta = end_dt - now
    total_sec = delta.total_seconds()

    if total_sec < 0:
        # Overdue
        abs_sec = abs(total_sec)
        days = int(abs_sec // 86400)
        hours = int((abs_sec % 86400) // 3600)
        mins = int((abs_sec % 3600) // 60)
        
        cal_days = (now.date() - end_dt.date()).days
        overdue_days = max(days, cal_days if cal_days > 0 else 0)
        is_from_yesterday = (overdue_days == 1) or (end_dt.date() == (now.date() - datetime.timedelta(days=1)))
        if is_from_yesterday:
            overdue_label = "Remaining from yesterday (-1d)"
            badge_text = "-1d overdue"
            countdown_text = f"Overdue from yesterday ({hours}h)" if hours > 0 else "Overdue by 1d"
        elif overdue_days > 0:
            overdue_label = f"Remaining from -{overdue_days}d"
            badge_text = f"-{overdue_days}d overdue"
            countdown_text = f"Overdue by {overdue_days}d {hours}h"
        elif hours > 0:
            overdue_label = f"Overdue by {hours}h"
            countdown_text = f"Overdue by {hours}h {mins}m"
            badge_text = f"-{hours}h overdue"
        else:
            overdue_label = f"Overdue by {mins}m"
            countdown_text = f"Overdue by {mins}m"
            badge_text = "Overdue!"

        return {
            **task,
            "status": "overdue",
            "urgency": "overdue",
            "urgency_class": "urgency-overdue",
            "badge_class": "badge-overdue pulse-red",
            "badge_text": badge_text,
            "countdown_text": countdown_text,
            "seconds_remaining": int(total_sec),
            "range_tag": range_tag,
            "is_multi_day": is_multi_day,
            "is_active_range": False,
            "is_upcoming": False,
            "is_active": True,
            "is_urgent": True,
            "is_overdue": True,
            "overdue_days": overdue_days,
            "is_from_yesterday": is_from_yesterday,
            "overdue_label": overdue_label,
            "is_completed_today": False
        }

    # Upcoming task: starts in the future, not yet active in the present
    if is_upcoming:
        start_delta = start_dt - now
        start_sec = start_delta.total_seconds()
        start_days = int(start_sec // 86400)
        start_hours = int((start_sec % 86400) // 3600)

        if start_days > 1:
            countdown_text = f"Starts in {start_days} days"
            badge_text = f"In {start_days} days"
        elif start_days == 1:
            countdown_text = f"Starts tomorrow ({start_hours}h)"
            badge_text = "Starts tomorrow"
        elif start_hours > 0:
            countdown_text = f"Starts in {start_hours}h"
            badge_text = f"In {start_hours}h"
        else:
            countdown_text = "Starts soon"
            badge_text = "Starting soon"

        if priority == "urgent":
            urgency = "critical"
            urgency_class = "urgency-critical"
            badge_class = "badge-critical pulse-red"
            badge_text = f"Urgent • In {start_days}d" if start_days > 0 else "Urgent • Soon"
            is_urgent = True
        elif priority == "high":
            urgency = "warning"
            urgency_class = "urgency-warning"
            badge_class = "badge-warning"
            badge_text = f"High • In {start_days}d" if start_days > 0 else "High • Soon"
            is_urgent = True
        else:
            urgency = "upcoming"
            urgency_class = "urgency-upcoming"
            badge_class = "badge-upcoming"
            is_urgent = False

        return {
            **task,
            "status": "upcoming",
            "urgency": urgency,
            "urgency_class": urgency_class,
            "badge_class": badge_class,
            "badge_text": badge_text,
            "countdown_text": countdown_text,
            "seconds_remaining": int(total_sec),
            "range_tag": range_tag,
            "is_multi_day": is_multi_day,
            "is_active_range": False,
            "is_upcoming": True,
            "is_active": False,
            "is_urgent": is_urgent,
            "is_completed_today": False,
            "is_overdue": False,
            "overdue_days": 0,
            "is_from_yesterday": False,
            "overdue_label": ""
        }

    # Active in the present:
    # 1. Critical urgency (< 24 hours remaining or urgent priority)
    if total_sec < 86400:
        hours = int(total_sec // 3600)
        mins = int((total_sec % 3600) // 60)
        secs = int(total_sec % 60)

        if hours > 0:
            countdown_text = f"{hours}h {mins:02d}m left"
            badge_text = f"{hours}h left!"
        else:
            countdown_text = f"{mins:02d}m {secs:02d}s remaining!"
            badge_text = f"{mins}m left!"

        urgency_class = "urgency-critical"
        badge_class = "badge-critical pulse-red"
        urgency = "critical"
        status = "urgent"
        is_urgent = True

    elif priority == "urgent":
        days = int(total_sec // 86400)
        hours = int((total_sec % 86400) // 3600)
        countdown_text = f"{days} days remaining" if days > 1 else f"1 day, {hours}h remaining"
        badge_text = f"Urgent • {days}d left" if days > 1 else "Urgent • 1d left"
        urgency_class = "urgency-critical"
        badge_class = "badge-critical pulse-red"
        urgency = "critical"
        status = "urgent"
        is_urgent = True

    # 2. Approaching deadline (1 to 3 days remaining, or high priority)
    elif total_sec <= 3 * 86400:
        days = int(total_sec // 86400)
        hours = int((total_sec % 86400) // 3600)
        
        if days > 1:
            countdown_text = f"{days} days, {hours}h remaining"
            badge_text = f"{days} days left"
        else:
            countdown_text = f"1 day, {hours}h remaining"
            badge_text = f"1d {hours}h left"

        urgency_class = "urgency-warning"
        badge_class = "badge-warning"
        urgency = "warning"
        status = "approaching"
        is_urgent = True

    elif priority == "high":
        days = int(total_sec // 86400)
        hours = int((total_sec % 86400) // 3600)
        countdown_text = f"{days} days remaining" if days > 1 else f"1 day, {hours}h remaining"
        badge_text = f"High • {days}d left" if days > 1 else "High • 1d left"
        urgency_class = "urgency-warning"
        badge_class = "badge-warning"
        urgency = "warning"
        status = "high"
        is_urgent = True

    # 3. Healthy buffer (> 3 days remaining and normal/low priority)
    else:
        days = int(total_sec // 86400)
        countdown_text = f"{days} days remaining"
        badge_text = f"{days} days left"
        urgency_class = "urgency-healthy"
        badge_class = "badge-healthy"
        urgency = "healthy"
        status = "healthy"
        is_urgent = False

    return {
        **task,
        "status": status,
        "urgency": urgency,
        "urgency_class": urgency_class,
        "badge_class": badge_class,
        "badge_text": badge_text,
        "countdown_text": countdown_text,
        "seconds_remaining": int(total_sec),
        "range_tag": range_tag,
        "is_multi_day": is_multi_day,
        "is_active_range": is_active_range,
        "is_upcoming": False,
        "is_active": True,
        "is_urgent": is_urgent,
        "is_completed_today": False,
        "is_overdue": False,
        "overdue_days": 0,
        "is_from_yesterday": False,
        "overdue_label": ""
    }

if __name__ == "__main__":
    from app.database import Database
    db = Database()
    tasks = db.get_tasks()
    now = datetime.datetime.now()
    print(f"=== Countdown Urgency Report at {now.strftime('%Y-%m-%d %H:%M:%S')} ===")
    for t in tasks:
        enriched = calculate_task_urgency(t, now)
        print(f"Task: {enriched['title']:<32} | {enriched['badge_text']:<16} | Urgency: {enriched['urgency'].upper():<10} | Tag: [{enriched['range_tag']}]")
