from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
from typing import Dict, List
import re

import pandas as pd
import requests
from utils.streamlit_compat import st
from bs4 import BeautifulSoup

from config.settings import EVENT_CACHE_TTL_SECONDS, LIVE_FETCH_ENABLED


_HISTORICAL_PLAYBOOK_EVENTS: List[Dict[str, str]] = [
    {"date": "2018-06-15", "family": "trade_war", "label": "Tariff escalation phase"},
    {"date": "2022-03-08", "family": "war_oil_stagflation", "label": "Commodity shock spike"},
    {"date": "2025-04-09", "family": "tariff_bond_rout", "label": "Tariff shock and bond selloff"},
    {"date": "2026-03-31", "family": "war_oil_stagflation", "label": "War-driven oil and inflation shock"},
]

_KEY_EVENT_RULES: List[tuple[str, int, str, str]] = [
    (r"employment situation|nonfarm payroll|payroll", 100, "labor", "high"),
    (r"consumer price index|\bcpi\b", 98, "inflation", "high"),
    (r"personal income and outlays|\bpce\b", 96, "inflation", "high"),
    (r"gdp", 95, "growth", "high"),
    (r"fomc|federal open market committee|fed meeting", 94, "policy", "high"),
    (r"producer price index|\bppi\b", 88, "inflation_pipeline", "medium"),
    (r"job openings and labor turnover survey|\bjolts\b", 84, "labor", "medium"),
    (r"employment cost index|\beci\b", 82, "labor_cost", "medium"),
    (r"retail sales", 80, "consumer", "medium"),
    (r"ism|manufacturing|services pmi", 78, "activity", "medium"),
    (r"import and export price|import price|export price", 70, "inflation_pipeline", "watch"),
]


def load_event_library() -> List[Dict[str, str]]:
    return list(_HISTORICAL_PLAYBOOK_EVENTS)


@st.cache_data(ttl=EVENT_CACHE_TTL_SECONDS, show_spinner=False)
def load_macro_calendar(*, force_refresh: bool = False) -> Dict[str, object]:
    now = datetime.now(timezone.utc)
    if not LIVE_FETCH_ENABLED or not force_refresh:
        return {"generated_at": now.isoformat(), "events": [], "all_events": [], "next_event": None}
    collected: List[Dict[str, object]] = []
    for loader in (_load_bls_calendar, _load_bea_calendar, _load_fomc_calendar):
        try:
            collected.extend(loader(now))
        except Exception:
            continue

    deduped = _dedupe_and_sort(collected)
    upcoming = [x for x in deduped if _parse_iso_dt(x.get("event_dt")) and _parse_iso_dt(x.get("event_dt")) >= now]
    return {
        "generated_at": now.isoformat(),
        "events": upcoming[:14],
        "all_events": deduped[:32],
        "next_event": upcoming[0] if upcoming else None,
    }


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


def _fetch_html(url: str) -> str:
    return _session().get(url, timeout=6).text


def _parse_iso_dt(value: object) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _event_meta(title: str) -> tuple[int, str, str]:
    lower = str(title).strip().lower()
    for pattern, priority, family, impact in _KEY_EVENT_RULES:
        if re.search(pattern, lower):
            return priority, family, impact
    return 0, "other", "watch"


def _clean_title(title: object) -> str:
    txt = re.sub(r"\s+", " ", str(title or "")).strip()
    return txt.replace("N ews", "News").replace("D ata", "Data").replace("  ", " ")


def _extract_time(text: str) -> str:
    m = re.search(r"(\d{1,2}:\d{2})\s*([AP]M)", text, flags=re.I)
    if not m:
        return ""
    return f"{m.group(1)} {m.group(2).upper()}"


def _parse_date_time(date_text: object, time_text: object | None = None, year_hint: int | None = None) -> datetime | None:
    date_s = _clean_title(date_text)
    time_s = _clean_title(time_text)
    if not date_s:
        return None
    date_s = re.sub(r"\s+", " ", date_s)
    if year_hint and not re.search(r"\b\d{4}\b", date_s):
        date_s = f"{date_s} {year_hint}"
    raw = f"{date_s} {time_s}".strip()
    for fmt in (
        "%A, %B %d, %Y %I:%M %p",
        "%A, %b %d, %Y %I:%M %p",
        "%B %d %Y %I:%M %p",
        "%B %d, %Y %I:%M %p",
        "%b %d %Y %I:%M %p",
        "%b %d, %Y %I:%M %p",
        "%A, %B %d, %Y",
        "%A, %b %d, %Y",
        "%B %d %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%b %d, %Y",
    ):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    try:
        dt = pd.to_datetime(raw, utc=True, errors="coerce")
        if pd.notna(dt):
            return dt.to_pydatetime()
    except Exception:
        pass
    return None


def _build_event(source: str, title: str, when: datetime | None, source_url: str) -> Dict[str, object] | None:
    title = _clean_title(title)
    priority, family, impact = _event_meta(title)
    if priority <= 0 or not when:
        return None
    return {
        "type": "MACRO",
        "source": source,
        "source_url": source_url,
        "family": family,
        "impact": impact,
        "priority": priority,
        "title": title,
        "label": f"{title} · {when.strftime('%b %d %H:%M UTC')}",
        "date": when.strftime("%Y-%m-%d"),
        "time": when.strftime("%H:%M UTC"),
        "event_dt": when.isoformat(),
    }


def _load_bls_calendar(now: datetime) -> List[Dict[str, object]]:
    url = "https://www.bls.gov/schedule/news_release/current_year.asp"
    html = _fetch_html(url)
    out: List[Dict[str, object]] = []

    try:
        tables = pd.read_html(StringIO(html))
    except Exception:
        tables = []

    for table in tables:
        cols = [re.sub(r"\s+", " ", str(c)).strip().lower() for c in table.columns]
        if not ("date" in cols and "release" in cols):
            continue
        date_col = table.columns[cols.index("date")]
        release_col = table.columns[cols.index("release")]
        time_col = table.columns[cols.index("time")] if "time" in cols else None
        for _, row in table.iterrows():
            title = _clean_title(row.get(release_col))
            date_val = _clean_title(row.get(date_col))
            time_val = _clean_title(row.get(time_col)) if time_col is not None else "08:30 AM"
            when = _parse_date_time(date_val, time_val, year_hint=now.year)
            event = _build_event("BLS", title, when, url)
            if event:
                out.append(event)

    if out:
        return out

    soup = BeautifulSoup(html, "lxml")
    current_month = ""
    for row in soup.select("table tr, tr"):
        cells = [_clean_title(x.get_text(" ", strip=True)) for x in row.find_all(["th", "td"])]
        if len(cells) == 1 and re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)", cells[0], re.I):
            current_month = cells[0]
            continue
        if len(cells) < 3:
            continue
        date_cell, time_cell, title = cells[0], cells[1], cells[2]
        if current_month and re.match(r"^[A-Za-z]+day,", date_cell):
            date_cell = date_cell
        when = _parse_date_time(date_cell, time_cell, year_hint=now.year)
        event = _build_event("BLS", title, when, url)
        if event:
            out.append(event)
    return out


def _load_bea_calendar(now: datetime) -> List[Dict[str, object]]:
    url = "https://www.bea.gov/news/schedule"
    html = _fetch_html(url)
    out: List[Dict[str, object]] = []
    text = re.sub(r"\s+", " ", BeautifulSoup(html, "lxml").get_text(" ", strip=True))

    # Regex fallback works well on the public page snippet ordering: Month Day, time, News, title
    pattern = re.compile(
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2})\s+(\d{1,2}:\d{2}\s*[AP]M)\s+N\s*ews\s+(.+?)(?=(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\s+\d{1,2}:\d{2}\s*[AP]M\s+N\s*ews|$)",
        flags=re.I,
    )
    for date_s, time_s, title in pattern.findall(text):
        when = _parse_date_time(f"{date_s}, {now.year}", time_s, year_hint=now.year)
        event = _build_event("BEA", title, when, url)
        if event:
            out.append(event)

    if out:
        return out

    try:
        tables = pd.read_html(StringIO(html))
    except Exception:
        tables = []
    for table in tables:
        if table.empty or table.shape[1] < 3:
            continue
        for _, row in table.iterrows():
            cells = [_clean_title(x) for x in row.tolist() if _clean_title(x) and _clean_title(x).lower() != "nan"]
            if len(cells) < 3:
                continue
            title = cells[-1]
            date_cell = next((x for x in cells if re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)", x, flags=re.I)), "")
            time_cell = next((x for x in cells if re.search(r"\d{1,2}:\d{2}\s*[AP]M", x, flags=re.I)), "8:30 AM")
            when = _parse_date_time(f"{date_cell}, {now.year}", time_cell, year_hint=now.year)
            event = _build_event("BEA", title, when, url)
            if event:
                out.append(event)
    return out


def _load_fomc_calendar(now: datetime) -> List[Dict[str, object]]:
    url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    text = _fetch_html(url)
    year = now.year
    out: List[Dict[str, object]] = []
    cleaned = re.sub(r"<[^>]+>", " ", text)
    year_match = re.search(rf"{year}\s*FOMC Meetings(.*?)(?:{year - 1}\s*FOMC Meetings|$)", cleaned, flags=re.I | re.S)
    section = year_match.group(1) if year_match else cleaned
    month_pattern = r"(January|February|March|April|May|June|July|August|September|October|November|December|Apr/May|Jan/Feb)"
    for month, dates in re.findall(rf"{month_pattern}\s+(\d{{1,2}}(?:-\d{{1,2}})?\*?)", section, flags=re.I):
        date_part = dates.replace("*", "")
        last_day = date_part.split("-")[-1]
        month_norm = month.replace("Apr/May", "April").replace("Jan/Feb", "January")
        when = _parse_date_time(f"{month_norm} {last_day}, {year}", "19:00", year_hint=year)
        if when is None:
            try:
                when = datetime.strptime(f"{month_norm} {last_day} {year}", "%B %d %Y").replace(tzinfo=timezone.utc)
            except Exception:
                when = None
        event = _build_event("FED", f"FOMC Meeting / Statement ({month_norm})", when, url)
        if event:
            out.append(event)
    return out


def _dedupe_and_sort(events: List[Dict[str, object]]) -> List[Dict[str, object]]:
    seen = set()
    deduped: List[Dict[str, object]] = []
    for item in sorted(events, key=lambda x: (-int(x.get("priority", 0)), str(x.get("event_dt", "")), str(x.get("title", "")))):
        key = (str(item.get("title", "")).lower(), str(item.get("event_dt", "")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return sorted(deduped, key=lambda x: (_parse_iso_dt(x.get("event_dt")) or datetime.max.replace(tzinfo=timezone.utc), -int(x.get("priority", 0))))
