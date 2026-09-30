"""
Bikram Sambat (BS) / Nepali Patro Conversion Engine & Full Monthly Calendar Generator.
Supports years 1975 BS to 2100 BS (1918 AD to 2043 AD).
Accurate astronomical lunar-solar mapping according to official calendar data.
"""

from __future__ import annotations
import datetime
import calendar
from typing import Any, Dict, List, Optional

try:
    from app.bs_data import BS_MONTH_DAYS
except ImportError:
    from bs_data import BS_MONTH_DAYS

# Reference anchor: 1975-01-01 BS = 1918-04-13 AD
REFERENCE_DATE_AD = datetime.date(1918, 4, 13)
REFERENCE_YEAR_BS = 1975

MONTH_NAMES_EN = [
    "Baishakh", "Jestha", "Ashadh", "Shrawan", "Bhadra", "Ashwin",
    "Kartik", "Mangsir", "Poush", "Magh", "Falgun", "Chaitra"
]

MONTH_NAMES_NP = [
    "बैशाख", "जेठ", "असार", "साउन", "भदौ", "असोज",
    "कार्तिक", "मंसिर", "पुस", "माघ", "फागुन", "चैत"
]

WEEKDAY_NAMES_EN = [
    "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
]

WEEKDAY_NAMES_NP = [
    "आइतबार", "सोमबार", "मङ्गलबार", "बुधबार", "बिहिबार", "शुक्रबार", "शनिबार"
]

WEEKDAY_SHORT_EN = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
WEEKDAY_SHORT_NP = ["आइत", "सोम", "मङ्गल", "बुध", "बिहि", "शुक्र", "शनि"]

DEVANAGARI_DIGITS = {
    "0": "०", "1": "१", "2": "२", "3": "३", "4": "४",
    "5": "५", "6": "६", "7": "७", "8": "८", "9": "९"
}

RITU_NAMES = [
    ("Basanta", "वसन्त"),   # Chaitra - Baishakh
    ("Grishma", "ग्रीष्म"),   # Jestha - Ashadh
    ("Barsha", "वर्षा"),     # Shrawan - Bhadra
    ("Sharad", "शरद"),      # Ashwin - Kartik
    ("Hemanta", "हेमन्त"),   # Mangsir - Poush
    ("Shishir", "शिशिर")    # Magh - Falgun
]

def to_devanagari_num(num: Any) -> str:
    """Convert integer or number string to Devanagari numerals."""
    return "".join(DEVANAGARI_DIGITS.get(ch, ch) for ch in str(num))

def get_ritu(month_bs: int) -> tuple[str, str]:
    """Return English and Nepali names for current Ritu (season)."""
    mapping = {
        12: 0, 1: 0,
        2: 1, 3: 1,
        4: 2, 5: 2,
        6: 3, 7: 3,
        8: 4, 9: 4,
        10: 5, 11: 5
    }
    idx = mapping.get(month_bs, 0)
    return RITU_NAMES[idx]

def ad_to_bs(ad_date: datetime.date | datetime.datetime) -> Dict[str, Any]:
    """
    Convert Gregorian (AD) date to Bikram Sambat (BS) date dictionary.
    Returns structured data with both English and Devanagari representations.
    """
    if isinstance(ad_date, datetime.datetime):
        ad_date = ad_date.date()

    days_delta = (ad_date - REFERENCE_DATE_AD).days
    if days_delta < 0:
        raise ValueError("Date is before supported BS range (1975 BS / 1918 AD)")

    cur_year = REFERENCE_YEAR_BS
    cur_month = 1
    cur_day = 1

    while days_delta > 0:
        if cur_year not in BS_MONTH_DAYS:
            raise ValueError(f"Year {cur_year} exceeds supported BS calendar range")
        days_in_cur_month = BS_MONTH_DAYS[cur_year][cur_month - 1]
        if days_delta >= days_in_cur_month:
            days_delta -= days_in_cur_month
            cur_month += 1
            if cur_month > 12:
                cur_month = 1
                cur_year += 1
        else:
            cur_day += days_delta
            days_delta = 0

    days_in_month = BS_MONTH_DAYS[cur_year][cur_month - 1]
    # 0 = Sunday in our week system
    wday_idx = (ad_date.weekday() + 1) % 7

    m_en = MONTH_NAMES_EN[cur_month - 1]
    m_np = MONTH_NAMES_NP[cur_month - 1]
    w_en = WEEKDAY_NAMES_EN[wday_idx]
    w_np = WEEKDAY_NAMES_NP[wday_idx]
    ritu_en, ritu_np = get_ritu(cur_month)

    y_np = to_devanagari_num(cur_year)
    d_np = to_devanagari_num(cur_day)

    formatted_en = f"{cur_day} {m_en} {cur_year}"
    formatted_np = f"{d_np} {m_np} {y_np}"
    header_title = f"{m_en} {cur_day}, {cur_year} BS ({m_np} {d_np})"

    return {
        "year": cur_year,
        "month": cur_month,
        "day": cur_day,
        "month_name_en": m_en,
        "month_name_np": m_np,
        "weekday_name_en": w_en,
        "weekday_name_np": w_np,
        "year_np": y_np,
        "day_np": d_np,
        "formatted_en": formatted_en,
        "formatted_np": formatted_np,
        "header_title": header_title,
        "days_in_month": days_in_month,
        "ritu_en": ritu_en,
        "ritu_np": ritu_np
    }

def bs_to_ad(year_bs: int, month_bs: int, day_bs: int) -> datetime.date:
    """Convert Bikram Sambat (BS) date to Gregorian (AD) date."""
    if year_bs < REFERENCE_YEAR_BS or year_bs > 2100:
        raise ValueError("Year outside supported BS range (1975-2100)")
    if month_bs < 1 or month_bs > 12:
        raise ValueError("Month must be between 1 and 12")
    max_days = BS_MONTH_DAYS[year_bs][month_bs - 1]
    if day_bs < 1 or day_bs > max_days:
        raise ValueError(f"Day {day_bs} invalid for month {month_bs} of year {year_bs} (max {max_days})")

    total_days = 0
    for y in range(REFERENCE_YEAR_BS, year_bs):
        total_days += sum(BS_MONTH_DAYS[y])
    for m in range(1, month_bs):
        total_days += BS_MONTH_DAYS[year_bs][m - 1]
    total_days += (day_bs - 1)

    return REFERENCE_DATE_AD + datetime.timedelta(days=total_days)

def get_dual_calendar(ref_datetime: Optional[datetime.datetime] = None) -> Dict[str, Any]:
    """
    Get synchronized dual calendar information for Gregorian (AD) and Bikram Sambat (BS).
    Returns rich metadata for UI widgets.
    """
    if ref_datetime is None:
        ref_datetime = datetime.datetime.now()

    ad_date = ref_datetime.date()
    bs_info = ad_to_bs(ad_date)

    return {
        "ad": {
            "year": ad_date.year,
            "month": ad_date.month,
            "day": ad_date.day,
            "month_name": ad_date.strftime("%B"),
            "month_short": ad_date.strftime("%b"),
            "weekday": ad_date.strftime("%A"),
            "weekday_short": ad_date.strftime("%a"),
            "formatted": ad_date.strftime("%a, %b %d, %Y"),
            "formatted_short": ad_date.strftime("%b %d, %Y"),
            "iso": ad_date.isoformat(),
            "time_12h": ref_datetime.strftime("%I:%M:%S %p"),
            "time_hm": ref_datetime.strftime("%I:%M %p"),
            "time_24h": ref_datetime.strftime("%H:%M:%S")
        },
        "bs": bs_info,
        "combined_header": f"{ad_date.strftime('%b %d, %Y')} AD  •  {bs_info['formatted_en']} BS"
    }

def get_bs_month_calendar(year_bs: int, month_bs: int, today: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    Generate full monthly calendar grid for Bikram Sambat (BS).
    Includes dual Gregorian AD dates for every single day cell.
    """
    if year_bs not in BS_MONTH_DAYS:
        raise ValueError(f"Year {year_bs} not in calendar dataset")
    total_days = BS_MONTH_DAYS[year_bs][month_bs - 1]
    first_ad = bs_to_ad(year_bs, month_bs, 1)
    start_col = (first_ad.weekday() + 1) % 7  # 0 = Sun, 6 = Sat
    if today is None:
        today = datetime.date.today()

    cells = []
    # Leading empty cells
    for _ in range(start_col):
        cells.append(None)

    for d in range(1, total_days + 1):
        ad_dt = bs_to_ad(year_bs, month_bs, d)
        wday_idx = (ad_dt.weekday() + 1) % 7
        cells.append({
            "bs_day": d,
            "bs_day_np": to_devanagari_num(d),
            "bs_month": month_bs,
            "bs_year": year_bs,
            "ad_day": ad_dt.day,
            "ad_month": ad_dt.strftime("%b"),
            "ad_year": ad_dt.year,
            "ad_date_iso": ad_dt.isoformat(),
            "is_today": (ad_dt == today),
            "weekday": wday_idx,
            "is_saturday": (wday_idx == 6)
        })

    m_en = MONTH_NAMES_EN[month_bs - 1]
    m_np = MONTH_NAMES_NP[month_bs - 1]
    last_ad = bs_to_ad(year_bs, month_bs, total_days)

    ad_span = f"{first_ad.strftime('%b %Y')} - {last_ad.strftime('%b %Y')}" if first_ad.month != last_ad.month else first_ad.strftime('%B %Y')

    # Prev/Next calculations
    prev_m = 12 if month_bs == 1 else month_bs - 1
    prev_y = year_bs - 1 if month_bs == 1 else year_bs
    next_m = 1 if month_bs == 12 else month_bs + 1
    next_y = year_bs + 1 if month_bs == 12 else year_bs

    return {
        "year_bs": year_bs,
        "month_bs": month_bs,
        "month_name_en": m_en,
        "month_name_np": m_np,
        "year_np": to_devanagari_num(year_bs),
        "total_days": total_days,
        "ad_span": ad_span,
        "prev_year": prev_y,
        "prev_month": prev_m,
        "next_year": next_y,
        "next_month": next_m,
        "weekdays_en": WEEKDAY_SHORT_EN,
        "weekdays_np": WEEKDAY_SHORT_NP,
        "cells": cells
    }

def get_ad_month_calendar(year_ad: int, month_ad: int, today: Optional[datetime.date] = None) -> Dict[str, Any]:
    """
    Generate full monthly calendar grid for Gregorian (AD).
    Includes dual Bikram Sambat BS dates for every single day cell.
    """
    total_days = calendar.monthrange(year_ad, month_ad)[1]
    first_dt = datetime.date(year_ad, month_ad, 1)
    start_col = (first_dt.weekday() + 1) % 7  # 0 = Sun
    if today is None:
        today = datetime.date.today()

    cells = []
    for _ in range(start_col):
        cells.append(None)

    for d in range(1, total_days + 1):
        ad_dt = datetime.date(year_ad, month_ad, d)
        bs_info = ad_to_bs(ad_dt)
        wday_idx = (ad_dt.weekday() + 1) % 7
        cells.append({
            "ad_day": d,
            "ad_month": month_ad,
            "ad_year": year_ad,
            "ad_date_iso": ad_dt.isoformat(),
            "bs_day": bs_info["day"],
            "bs_day_np": bs_info["day_np"],
            "bs_month": bs_info["month"],
            "bs_month_name": bs_info["month_name_en"],
            "bs_month_name_np": bs_info["month_name_np"],
            "bs_year": bs_info["year"],
            "is_today": (ad_dt == today),
            "weekday": wday_idx,
            "is_saturday": (wday_idx == 6)
        })

    first_bs = ad_to_bs(first_dt)
    last_bs = ad_to_bs(datetime.date(year_ad, month_ad, total_days))
    bs_span = f"{first_bs['month_name_en']} - {last_bs['month_name_en']} {last_bs['year']} BS"

    prev_m = 12 if month_ad == 1 else month_ad - 1
    prev_y = year_ad - 1 if month_ad == 1 else year_ad
    next_m = 1 if month_ad == 12 else month_ad + 1
    next_y = year_ad + 1 if month_ad == 12 else year_ad

    return {
        "year_ad": year_ad,
        "month_ad": month_ad,
        "month_name": first_dt.strftime("%B"),
        "total_days": total_days,
        "bs_span": bs_span,
        "prev_year": prev_y,
        "prev_month": prev_m,
        "next_year": next_y,
        "next_month": next_m,
        "weekdays_en": WEEKDAY_SHORT_EN,
        "weekdays_np": WEEKDAY_SHORT_NP,
        "cells": cells
    }

if __name__ == "__main__":
    now = datetime.datetime.now()
    dual = get_dual_calendar(now)
    print("Dual Calendar Report:")
    print("  AD Date :", dual["ad"]["formatted"], "| Time:", dual["ad"]["time_12h"])
    print("  BS Date :", dual["bs"]["formatted_en"], "| Devanagari:", dual["bs"]["formatted_np"])
