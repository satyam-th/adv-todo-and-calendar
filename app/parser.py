"""
Natural Language & Command-Line Input Parser for Tasks and Notes.
Parses natural language date ranges, deadlines, priority tags, and commands.
"""

from __future__ import annotations
import re
import datetime
from typing import Dict, Any, Optional, Tuple

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12
}

WEEKDAYS_MAP = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6
}

def parse_time_str(time_str: str) -> Optional[Tuple[int, int]]:
    """Parse time string like '14:30', '3pm', '3:45pm', '11am'."""
    s = time_str.strip().lower()
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", s)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) else 0
    meridiem = m.group(3)

    if meridiem:
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
    elif hour > 23 or minute > 59:
        return None

    return hour, minute

def parse_single_date(date_str: str, now: Optional[datetime.datetime] = None) -> Optional[datetime.date]:
    """Parse date tokens like 'Sept 8', 'September 20th', '2026-09-08', 'today', 'tomorrow', 'Friday'."""
    if now is None:
        now = datetime.datetime.now()

    s = date_str.strip().lower()
    s = re.sub(r"^(?:on|by|due|before|at|from)\s+", "", s)

    if s == "today":
        return now.date()
    if s == "tomorrow":
        return (now + datetime.timedelta(days=1)).date()
    if s == "yesterday":
        return (now - datetime.timedelta(days=1)).date()

    # ISO format YYYY-MM-DD
    iso_match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if iso_match:
        try:
            return datetime.date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            pass

    # Weekday e.g. "friday", "next monday"
    clean_w = re.sub(r"^(?:next\s+|this\s+)", "", s)
    if clean_w in WEEKDAYS_MAP:
        target_w = WEEKDAYS_MAP[clean_w]
        cur_w = now.weekday()
        days_ahead = (target_w - cur_w) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (now + datetime.timedelta(days=days_ahead)).date()

    # Month Day e.g. "Sept 8", "September 20", "8 Sept", "Oct 15, 2026"
    m = re.match(r"^([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?$", s)
    if m:
        month_s, day_s, year_s = m.group(1), m.group(2), m.group(3)
        if month_s in MONTH_MAP:
            year = int(year_s) if year_s else now.year
            month = MONTH_MAP[month_s]
            day = int(day_s)
            try:
                dt = datetime.date(year, month, day)
                if not year_s and dt < (now.date() - datetime.timedelta(days=180)):
                    dt = datetime.date(year + 1, month, day)
                return dt
            except ValueError:
                pass

    # Day Month format e.g. "8 Sept"
    m_rev = re.match(r"^(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)(?:\s*,?\s*(\d{4}))?$", s)
    if m_rev:
        day_s, month_s, year_s = m_rev.group(1), m_rev.group(2), m_rev.group(3)
        if month_s in MONTH_MAP:
            year = int(year_s) if year_s else now.year
            month = MONTH_MAP[month_s]
            day = int(day_s)
            try:
                return datetime.date(year, month, day)
            except ValueError:
                pass

    return None

def parse_quick_command(raw_input: str, now: Optional[datetime.datetime] = None) -> Dict[str, Any]:
    """
    Main parser entry point.
    Takes user natural language input like:
      "Finish project from Sept 8 to Sept 20 #urgent @work"
      "Submit report by tomorrow 5pm #high"
      "/note Met with client regarding deployment timeline"
    Returns structured dictionary ready for database insertion.
    """
    if now is None:
        now = datetime.datetime.now()

    text = raw_input.strip()

    # 1. Check if note command
    if text.startswith(("/note", "note:", "#note")):
        note_content = re.sub(r"^(?:/note\s*|note:\s*|#note\s*)", "", text, flags=re.IGNORECASE).strip()
        return {
            "type": "note",
            "content": note_content,
            "date": now.strftime("%Y-%m-%d")
        }

    # 1b. Check if daily routine command
    if re.match(r"^(?:/routine|routine:|#routine|/habit|habit:|routine\b)", text, re.IGNORECASE):
        rem_text = re.sub(r"^(?:/routine\s*|routine:\s*|#routine\s*|/habit\s*|habit:\s*|routine\s+)", "", text, flags=re.IGNORECASE).strip()

        # Category tag (@health, #health, etc.)
        category = "routine"
        cat_match = re.search(r"[@#](\w+)\b", rem_text)
        if cat_match:
            category = cat_match.group(1).lower()
            rem_text = rem_text[:cat_match.start()] + rem_text[cat_match.end():]

        # Time extraction e.g. "08:30", "at 9am", "14:00", "7:30pm"
        time_str = "09:00"
        time_match = re.search(r"\b(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?|\d{1,2}:\d{2})\b", rem_text, re.IGNORECASE)
        if time_match:
            t_parsed = parse_time_str(time_match.group(1))
            if t_parsed:
                h, m = t_parsed
                time_str = f"{h:02d}:{m:02d}"
                rem_text = rem_text[:time_match.start()] + rem_text[time_match.end():]

        clean_title = re.sub(r"\s+", " ", rem_text).strip()
        if not clean_title:
            clean_title = "Daily Routine"

        return {
            "type": "routine",
            "title": clean_title,
            "time_str": time_str,
            "category": category,
            "notify": 1,
            "raw": raw_input
        }

    # 2. Extract priority tags (#urgent, #critical, #high, #normal, #low, #p1, #p2, etc.)
    priority = "normal"
    priority_patterns = [
        (r"#(urgent|critical|emergency)\b", "urgent"),
        (r"#(high|p1)\b", "high"),
        (r"#(normal|medium|med|p2)\b", "normal"),
        (r"#(low|p3)\b", "low")
    ]
    for pattern, prio_val in priority_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            priority = prio_val
            text = text[:match.start()] + text[match.end():]
            break

    # 3. Extract category tags (@work, @dev, @personal, etc.)
    category = "general"
    cat_match = re.search(r"@(\w+)\b", text)
    if cat_match:
        category = cat_match.group(1).lower()
        text = text[:cat_match.start()] + text[cat_match.end():]

    # 4. Check for explicit time e.g. "at 3pm", "at 16:30", "15:00"
    explicit_time = None
    time_match = re.search(r"\b(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)|\d{1,2}:\d{2})\b", text, re.IGNORECASE)
    if time_match:
        t_parsed = parse_time_str(time_match.group(1))
        if t_parsed:
            explicit_time = t_parsed
            text = text[:time_match.start()] + text[time_match.end():]

    # 5. Check for relative duration e.g. "in 3 days", "in 2 weeks", "in 5 hours"
    start_dt = now
    end_dt = None

    rel_match = re.search(r"\bin\s+(\d+)\s+(day|days|hour|hours|week|weeks)\b", text, re.IGNORECASE)
    if rel_match:
        val = int(rel_match.group(1))
        unit = rel_match.group(2).lower()
        if "hour" in unit:
            end_dt = now + datetime.timedelta(hours=val)
        elif "week" in unit:
            end_dt = (now + datetime.timedelta(weeks=val)).replace(hour=23, minute=59, second=59)
        else:
            end_dt = (now + datetime.timedelta(days=val)).replace(hour=23, minute=59, second=59)
        text = text[:rel_match.start()] + text[rel_match.end():]

    # 6. Check for Date Range:
    # Pattern A: Month Name ranges (e.g. from Sept 8 to Sept 20, Sept 8 - Sept 20)
    month_range_pattern = re.search(
        r"(?:from\s+)?(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|October|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?)\s+(?:to|until|-|–|through)\s+(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|October|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?)",
        text,
        re.IGNORECASE
    )
    # Pattern B: ISO ranges (e.g. 2026-10-01 to 2026-10-10)
    iso_range_pattern = re.search(
        r"(?:from\s+)?(\d{4}-\d{1,2}-\d{1,2})\s+(?:to|until|-|–|through)\s+(\d{4}-\d{1,2}-\d{1,2})",
        text,
        re.IGNORECASE
    )
    # Pattern C: Relative ranges (e.g. from today to Friday, today to tomorrow)
    rel_range_pattern = re.search(
        r"(?:from\s+)?(today|tomorrow)\s+(?:to|until|-|–|through)\s+([a-z0-9\s,]+)",
        text,
        re.IGNORECASE
    )

    if end_dt is None and month_range_pattern:
        d1 = parse_single_date(month_range_pattern.group(1), now)
        d2 = parse_single_date(month_range_pattern.group(2), now)
        if d1 and d2:
            start_dt = datetime.datetime(d1.year, d1.month, d1.day, 0, 0, 0)
            end_h, end_m = (explicit_time if explicit_time else (23, 59))
            end_dt = datetime.datetime(d2.year, d2.month, d2.day, end_h, end_m, 59)
            text = text[:month_range_pattern.start()] + text[month_range_pattern.end():]

    elif end_dt is None and iso_range_pattern:
        d1 = parse_single_date(iso_range_pattern.group(1), now)
        d2 = parse_single_date(iso_range_pattern.group(2), now)
        if d1 and d2:
            start_dt = datetime.datetime(d1.year, d1.month, d1.day, 0, 0, 0)
            end_h, end_m = (explicit_time if explicit_time else (23, 59))
            end_dt = datetime.datetime(d2.year, d2.month, d2.day, end_h, end_m, 59)
            text = text[:iso_range_pattern.start()] + text[iso_range_pattern.end():]

    elif end_dt is None and rel_range_pattern:
        d1 = parse_single_date(rel_range_pattern.group(1), now)
        d2 = parse_single_date(rel_range_pattern.group(2), now)
        if d1 and d2:
            start_dt = datetime.datetime(d1.year, d1.month, d1.day, 0, 0, 0)
            end_h, end_m = (explicit_time if explicit_time else (23, 59))
            end_dt = datetime.datetime(d2.year, d2.month, d2.day, end_h, end_m, 59)
            text = text[:rel_range_pattern.start()] + text[rel_range_pattern.end():]

    # 7. Check for Single Date deadline if no range matched:
    if end_dt is None:
        single_pattern = re.search(
            r"\b(?:by|due|on|before|until)?\s*([a-z]+\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?|\d{4}-\d{1,2}-\d{1,2}|today|tomorrow|yesterday|next\s+[a-z]+|[a-z]+day)\b",
            text,
            re.IGNORECASE
        )
        if single_pattern:
            tok = single_pattern.group(1).strip()
            d = parse_single_date(tok, now)
            if d:
                start_dt = now
                end_h, end_m = (explicit_time if explicit_time else (23, 59))
                end_dt = datetime.datetime(d.year, d.month, d.day, end_h, end_m, 59)
                text = text[:single_pattern.start()] + text[single_pattern.end():]

    # Default end date if still not specified
    if end_dt is None:
        end_h, end_m = (explicit_time if explicit_time else (23, 59))
        end_dt = datetime.datetime(now.year, now.month, now.day, end_h, end_m, 59)

    # 8. Clean up title
    clean_title = re.sub(r"\bfrom\b", "", text, flags=re.IGNORECASE)
    clean_title = re.sub(r"\s+", " ", clean_title).strip()
    clean_title = re.sub(r"^(?:task:|-|\*)\s*", "", clean_title)
    if not clean_title:
        clean_title = "Untitled Task"

    # Format ISO strings
    start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S") if (start_dt.hour != 0 or start_dt.minute != 0) else start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    return {
        "type": "task",
        "title": clean_title,
        "start_date": start_str,
        "end_date": end_str,
        "priority": priority,
        "category": category,
        "raw": raw_input
    }

if __name__ == "__main__":
    test_inputs = [
        "Finish project from Sept 8 to Sept 20 #urgent",
        "Submit quarterly tax report by Sept 10 #high",
        "Client presentation slides due Sept 8 18:00 #urgent",
        "Deploy v2 build in 3 days #high @dev",
        "Team sync tomorrow 3pm #normal @work",
        "Vacation 2026-10-01 to 2026-10-10 #low",
        "/note Remember to run migrations on secondary server"
    ]
    now = datetime.datetime(2026, 9, 8, 9, 0, 0)
    for inp in test_inputs:
        res = parse_quick_command(inp, now=now)
        print(f"INPUT : {inp}")
        print(f"TITLE : {res.get('title') or res.get('content')}")
        print(f"DATES : {res.get('start_date')} -> {res.get('end_date')}")
        print(f"META  : priority={res.get('priority')}, cat={res.get('category')}\n")
