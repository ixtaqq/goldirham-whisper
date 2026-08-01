#!/usr/bin/env python3
"""
Goldirham Whisper Aggregator
Pulls exchange infrastructure dates + obscure economic releases
and writes a unified events.json for a static Hugo site.

Inputs : scripts/config.yaml + optional data/manual_events.json (curated) +
         optional published Google Sheet CSV (community submissions)
Output : data/events.json
"""

import csv
import io
import json
import logging
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

import feedparser
import icalendar
import requests
import yaml
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

CONFIG_PATH = Path(__file__).parent / "config.yaml"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "events.json"
MANUAL_PATH = Path(__file__).parent.parent / "data" / "manual_events.json"
SPA_DATA_DIR = Path(__file__).parent.parent / "static" / "data"
USER_AGENT = "GoldirhamWhisper/1.0 (calendar@example.com)"  # Be polite
LOOKBACK_DAYS = 30
LOOKAHEAD_DAYS = 365

# Source-name substring patterns -> flag emoji (must mirror layouts/partials/store.html GW_FLAGS).
GW_FLAGS = [
    ["nasdaq nordic", "\U0001F1F8\U0001F1EA"], ["omx", "\U0001F1F8\U0001F1EA"],
    ["new york stock exchange", "\U0001F1FA\U0001F1F8"], ["nyse", "\U0001F1FA\U0001F1F8"], ["nasdaq", "\U0001F1FA\U0001F1F8"],
    ["cme", "\U0001F1FA\U0001F1F8"], ["cboe", "\U0001F1FA\U0001F1F8"], ["dtcc", "\U0001F1FA\U0001F1F8"], ["msci", "\U0001F1FA\U0001F1F8"],
    ["ice futures", "\U0001F1FA\U0001F1F8"], ["chicago board", "\U0001F1FA\U0001F1F8"],
    ["london stock exchange", "\U0001F1EC\U0001F1E7"], ["lse", "\U0001F1EC\U0001F1E7"],
    ["euronext", "\U0001F1EA\U0001F1FA"],
    ["deutsche börse", "\U0001F1E9\U0001F1EA"], ["deutsche borse", "\U0001F1E9\U0001F1EA"], ["eurex", "\U0001F1E9\U0001F1EA"],
    ["tokyo stock exchange", "\U0001F1EF\U0001F1F5"], ["jpx", "\U0001F1EF\U0001F1F5"], ["ose", "\U0001F1EF\U0001F1F5"],
    ["singapore exchange", "\U0001F1F8\U0001F1EC"], ["sgx", "\U0001F1F8\U0001F1EC"],
    ["asx", "\U0001F1E6\U0001F1FA"],
    ["hkex", "\U0001F1ED\U0001F1F0"], ["hong kong", "\U0001F1ED\U0001F1F0"],
    ["shanghai", "\U0001F1E8\U0001F1F3"], ["shenzhen", "\U0001F1E8\U0001F1F3"], ["general administration", "\U0001F1E8\U0001F1F3"], ["nbs", "\U0001F1E8\U0001F1F3"], ["pboc", "\U0001F1E8\U0001F1F3"],
    ["korea exchange", "\U0001F1F0\U0001F1F7"], ["krx", "\U0001F1F0\U0001F1F7"],
    ["tsx", "\U0001F1E8\U0001F1E6"], ["tmx", "\U0001F1E8\U0001F1E6"],
    ["six", "\U0001F1E8\U0001F1ED"],
    ["borsa italiana", "\U0001F1EE\U0001F1F9"],
    ["iberclear", "\U0001F1EA\U0001F1F8"], ["bme", "\U0001F1EA\U0001F1F8"],
    ["tadawul", "\U0001F1F8\U0001F1E6"], ["saudi", "\U0001F1F8\U0001F1E6"],
    ["bovespa", "\U0001F1E7\U0001F1F7"], ["b3", "\U0001F1E7\U0001F1F7"], ["ibge", "\U0001F1E7\U0001F1F7"],
    ["bmv", "\U0001F1F2\U0001F1FD"], ["inegi", "\U0001F1F2\U0001F1FD"],
    ["jse", "\U0001F1FF\U0001F1E6"], ["idx", "\U0001F1EE\U0001F1E9"], ["indonesia", "\U0001F1EE\U0001F1E9"], ["twse", "\U0001F1F9\U0001F1FC"], ["taiwan", "\U0001F1F9\U0001F1FC"],
    ["mospi", "\U0001F1EE\U0001F1F3"], ["nse", "\U0001F1EE\U0001F1F3"], ["bse india", "\U0001F1EE\U0001F1F3"],
    ["bls", "\U0001F1FA\U0001F1F8"], ["bureau of labor", "\U0001F1FA\U0001F1F8"], ["federal reserve", "\U0001F1FA\U0001F1F8"], ["fed", "\U0001F1FA\U0001F1F8"],
    ["bea", "\U0001F1FA\U0001F1F8"], ["treasury", "\U0001F1FA\U0001F1F8"], ["ism", "\U0001F1FA\U0001F1F8"], ["s&p", "\U0001F1FA\U0001F1F8"], ["sp global", "\U0001F1FA\U0001F1F8"],
    ["ecb", "\U0001F1EA\U0001F1FA"], ["eurostat", "\U0001F1EA\U0001F1FA"],
    ["bank of japan", "\U0001F1EF\U0001F1F5"], ["boj", "\U0001F1EF\U0001F1F5"], ["statistics bureau of japan", "\U0001F1EF\U0001F1F5"], ["ministry of finance japan", "\U0001F1EF\U0001F1F5"],
    ["destatis", "\U0001F1E9\U0001F1EA"], ["ifo", "\U0001F1E9\U0001F1EA"],
    ["bank of england", "\U0001F1EC\U0001F1E7"], ["mni", "\U0001F1EC\U0001F1E7"],
    ["rba", "\U0001F1E6\U0001F1FA"], ["reserve bank of australia", "\U0001F1E6\U0001F1FA"],
]
GW_FLAG_DEFAULT = "\U0001F310"  # 🌐


def flag_for(source):
    """First matching substring pattern wins; falls back to the globe."""
    s = str(source or "").lower()
    for key, flag in GW_FLAGS:
        if key in s:
            return flag
    return GW_FLAG_DEFAULT


def make_slug(title):
    """URL-safe slug, mirroring the frontend gwSlug() / Hugo urlize()."""
    s = unicodedata.normalize("NFKD", str(title or "")).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch_content(url):
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logging.error("Failed to fetch %s: %s", url, e)
        return None


def looks_like(content, kind):
    """Cheap sniff — many 'iCal/RSS' endpoints now return HTML SPA wrappers."""
    if not content:
        return False
    head = content[:4000].decode("utf-8", "ignore").lstrip().lower()
    if kind == "ical":
        return "begin:vcalendar" in head
    if kind == "rss":
        return head.startswith(("<?xml", "<rss", "<feed", "<rdf")) or "<rss" in head or "<feed" in head
    return True  # html fallback always allowed


def in_window(event_date):
    return (
        date.today() - timedelta(days=LOOKBACK_DAYS)
        <= event_date
        <= date.today() + timedelta(days=LOOKAHEAD_DAYS)
    )


def parse_ical(content, source_name, source_type="exchange"):
    """Extract events from iCal data."""
    events = []
    try:
        cal = icalendar.Calendar.from_ical(content)
        for component in cal.walk():
            if component.name != "VEVENT":
                continue
            summary = str(component.get("summary") or "").strip()
            if not summary:
                continue  # empty titles pollute the calendar; skip
            dtstart = component.get("dtstart")
            if not dtstart:
                continue
            dtstart = dtstart.dt
            if isinstance(dtstart, datetime):
                event_date = dtstart.date()
            else:
                event_date = dtstart
            if not in_window(event_date):
                continue
            dtend = component.get("dtend")
            events.append(
                {
                    "date": event_date.isoformat(),
                    "title": summary or f"{source_name} event",
                    "source": source_name,
                    "type": source_type,
                    "description": str(component.get("description") or "").strip(),
                    "url": str(component.get("url") or "") if component.get("url") else "",
                    "tags": [source_name.lower(), source_type],
                }
            )
    except Exception as e:
        logging.error("Error parsing iCal from %s: %s", source_name, e)
    return events


def parse_rss(content, source_name, source_type="economics", keywords=None):
    """Extract items from RSS/Atom feed.

    Many free central-bank/regulator feeds mix real statistical releases with
    HR announcements and PR fluff ("names new COO", "hosts virtual roundtable").
    If `keywords` is given, only entries whose title or summary contain at
    least one keyword are kept — a relevance filter, not a topic restriction.
    """
    events = []
    try:
        feed = feedparser.parse(content)
        for entry in feed.entries:
            date_str = None
            if getattr(entry, "published_parsed", None):
                p = entry.published_parsed
                date_str = f"{p[0]:04d}-{p[1]:02d}-{p[2]:02d}"
            elif getattr(entry, "updated_parsed", None):
                p = entry.updated_parsed
                date_str = f"{p[0]:04d}-{p[1]:02d}-{p[2]:02d}"
            if not date_str:
                continue
            try:
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if not in_window(event_date):
                continue
            title = (entry.get("title") or f"{source_name} release").strip()
            summary = entry.get("summary") or ""
            if keywords:
                haystack = (title + " " + summary).lower()
                if not any(k in haystack for k in keywords):
                    continue
            events.append(
                {
                    "date": event_date.isoformat(),
                    "title": title,
                    "source": source_name,
                    "type": source_type,
                    "description": summary[:500],
                    "url": entry.get("link", ""),
                    "tags": [source_name.lower(), source_type, "economics"],
                }
            )
    except Exception as e:
        logging.error("Error parsing RSS from %s: %s", source_name, e)
    return events


def parse_html_calendar(content, source_name, source_type="exchange"):
    """Fallback parser for HTML-based calendar pages (extend per venue)."""
    events = []
    try:
        soup = BeautifulSoup(content, "lxml")
        # Highly venue-specific; place a real selector per exchange here.
        # Example heuristic: <td class="date">2026-08-15</td> rows.
        for row in soup.select("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            text = " ".join(c.get_text(" ", strip=True) for c in cells)
            m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
            if not m:
                continue
            try:
                event_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            except ValueError:
                continue
            if not in_window(event_date):
                continue
            events.append(
                {
                    "date": event_date.isoformat(),
                    "title": text[:120],
                    "source": source_name,
                    "type": source_type,
                    "description": text,
                    "url": "",
                    "tags": [source_name.lower(), source_type],
                }
            )
    except Exception as e:
        logging.error("Error parsing HTML from %s: %s", source_name, e)
    return events


MONTH_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def parse_jpx_holidays(content, source_name, source_type="exchange"):
    """JPX's market-holiday page (jpx.co.jp/.../calendar/) is one of the few
    exchange calendars still served as plain server-rendered HTML. Each year
    is an <h2 class="heading-title"><span>YYYY</span></h2> followed by a
    <table class="overtable"> of rows like ["Jan. 1 (Thu.)", "New Year's Day"].
    Generic tr/td scraping (parse_html_calendar) finds no ISO dates here, so
    this walks the DOM tracking the current year heading per table."""
    events = []
    try:
        soup = BeautifulSoup(content, "lxml")
        current_year = None
        for el in soup.find_all(["h2", "table"]):
            if el.name == "h2" and "heading-title" in (el.get("class") or []):
                text = el.get_text(strip=True)
                m = re.match(r"(\d{4})", text)
                if m:
                    current_year = int(m.group(1))
                continue
            if el.name == "table" and current_year:
                for row in el.select("tr"):
                    cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
                    if len(cells) < 2:
                        continue
                    dm = re.match(r"^([A-Za-z]{3})\.?\s*(\d{1,2})", cells[0])
                    if not dm:
                        continue
                    month = MONTH_NUM.get(dm.group(1).lower())
                    if not month:
                        continue
                    try:
                        event_date = date(current_year, month, int(dm.group(2)))
                    except ValueError:
                        continue
                    if not in_window(event_date):
                        continue
                    title = re.sub(r"\s*\d+$", "", cells[1]).strip()  # strip footnote markers
                    events.append(
                        {
                            "date": event_date.isoformat(),
                            "title": f"Market holiday — {title}",
                            "source": source_name,
                            "type": source_type,
                            "description": f"{source_name} closed for {title}. Settlement and expiry cycles roll to the next session.",
                            "url": "https://www.jpx.co.jp/english/corporate/about-jpx/calendar/",
                            "tags": [source_name.lower(), source_type, "holiday"],
                        }
                    )
    except Exception as e:
        logging.error("Error parsing JPX calendar from %s: %s", source_name, e)
    return events


def process_source(source, source_type):
    logging.info("Processing %s (%s)", source["name"], source["type"])
    content = fetch_content(source["url"])
    if not content:
        return []
    parser = {
        "ical": parse_ical,
        "rss": parse_rss,
        "jpx_holidays": parse_jpx_holidays,
    }.get(source["type"], parse_html_calendar)
    if source["type"] in ("ical", "rss") and not looks_like(content, source["type"]):
        logging.warning(
            "%s returned non-%s payload (SPA/HTML wrapper?) — skipped",
            source["name"], source["type"].upper(),
        )
        return []
    kwargs = {"source_type": source_type}
    if source["type"] == "rss" and source.get("keywords"):
        kwargs["keywords"] = [k.strip().lower() for k in source["keywords"] if k.strip()]
    return parser(content, source["name"], **kwargs)


def load_manual_events():
    """Raw entries from data/manual_events.json (curated picks)."""
    if not MANUAL_PATH.exists():
        return []
    try:
        manual = json.loads(MANUAL_PATH.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        logging.warning("Skipping manual_events.json: %s", e)
        return []
    return manual if isinstance(manual, list) else []


def normalize_manual(events):
    """Validate + normalise hand-maintained entries (accepts both .json and sheet rows).
    Status: missing/unknown -> "approved"; "pending"/"rejected" are staged OUT (never published)."""
    out = []
    for e in events:
        if not isinstance(e, dict):
            continue
        date_str = str(e.get("date") or "").strip()
        title = str(e.get("title") or "").strip()
        if not date_str or not title:
            continue
        status = str(e.get("status") or "approved").strip().lower() or "approved"
        if status in ("pending", "rejected"):
            logging.info("Staging out %s event: %s", status, title)
            continue
        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logging.warning("Skipping manual event: unparseable date %r", date_str)
            continue
        if not in_window(event_date):
            continue
        tags_raw = e.get("tags") or []
        if isinstance(tags_raw, str):
            tags = [t.strip().lower() for t in tags_raw.split(",") if t.strip()]
        elif isinstance(tags_raw, (list, tuple)):
            tags = [t.strip().lower() for t in tags_raw if str(t).strip()]
        else:
            tags = []
        out.append(
            {
                "date": event_date.isoformat(),
                "title": title,
                "source": str(e.get("source") or "Community").strip() or "Community",
                "type": str(e.get("type") or "economics").strip().lower(),
                "description": str(e.get("description") or "").strip(),
                "url": str(e.get("url") or "").strip(),
                "tags": tags or ["community"],
                "status": "approved",
            }
        )
    return out


def fetch_google_sheet(csv_url):
    """Community submissions from a published Google Sheet CSV export."""
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(csv_url, headers=headers, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        logging.error("Failed to fetch Google Sheet %s: %s", csv_url, e)
        return []
    try:
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
    except Exception as e:
        logging.error("Bad Google Sheet CSV: %s", e)
        return []
    logging.info("Google Sheet: %d CSV rows", len(rows))

    events = []
    for raw in rows:
        row = {((k or "").strip().lower()): (v or "").strip() for k, v in raw.items()}

        def pick(*names):
            for n in names:
                if n in row and row[n]:
                    return row[n]
            return ""

        date_str = pick("event date", "date", "eventdate", "when")
        title = pick("title", "headline", "event")
        if not date_str or not title:
            continue
        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logging.warning("Skipping sheet row: unparseable date %r", date_str)
            continue
        if not in_window(event_date):
            continue
        tags = [t.strip().lower() for t in pick("tags", "tag").split(",") if t.strip()]
        status = pick("status") or "approved"  # "Status" column: Approved / Pending
        events.append(
            {
                "date": event_date.isoformat(),
                "title": title,
                "source": pick("source", "issuer") or "Community",
                "type": (pick("type", "category") or "economics").lower(),
                "description": pick("description", "details"),
                "url": pick("url", "source url", "link"),
                "tags": tags or ["community"],
                "status": status,
            }
        )
    logging.info("Google Sheet: %d valid in-window events", len(events))
    return events


def merge_sources(auto_events, config):
    """Auto feeds first; manual/community entries override on (date, title, source)."""
    merged = {}
    for ev in auto_events:
        key = (ev.get("date"), (ev.get("title") or "")[:100], ev.get("source"))
        if all(key):
            merged[key] = ev

    sheet_url = (config.get("community") or {}).get("sheet_csv_url") or config.get("sheet_csv_url")
    manual = []
    if sheet_url:
        manual += fetch_google_sheet(sheet_url)
    else:
        logging.info("No sheet_csv_url configured — skipping Google Sheet merge")
    local = load_manual_events()
    if local:
        logging.info("Loading %d local manual_events.json entries", len(local))
    manual += local

    manual = normalize_manual(manual)
    added = 0
    for ev in manual:
        key = (ev.get("date"), (ev.get("title") or "")[:100], ev.get("source"))
        if not all(key):
            continue
        if key not in merged:
            added += 1
        merged[key] = ev  # manual wins over auto
    if manual:
        logging.info("Merged %d manual/community events (%d new)", len(manual), added)
    return sorted(merged.values(), key=lambda x: x["date"])


def export_spa_data(events):
    """Write the JS modules the frontend SPA imports from static/data/."""
    SPA_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with_slug = [{**ev, "slug": make_slug(ev.get("title"))} for ev in events]

    js_events = "// Generated by aggregator.py \u2014 do not edit.\n"
    js_events += "export const events = " + json.dumps(with_slug, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (SPA_DATA_DIR / "events-data.js").write_text(js_events, encoding="utf-8")

    flag_map = {name: flag_for(name) for name in sorted({e.get("source") or "" for e in events}) if name}
    js_flags = "// Generated by aggregator.py \u2014 do not edit.\n"
    js_flags += "export const flagMap = " + json.dumps(flag_map, ensure_ascii=False, indent=2) + ";\n"
    js_flags += 'export function flagFor(source) { return flagMap[source] || "\U0001F310"; }\n'
    (SPA_DATA_DIR / "flags-data.js").write_text(js_flags, encoding="utf-8")
    logging.info("Exported SPA data: %d events, %d flags", len(with_slug), len(flag_map))


def main():
    config = load_config()
    all_events = []
    for ex in config.get("exchanges", []):
        all_events += process_source(ex, "exchange")
    for eco in config.get("economics", []):
        all_events += process_source(eco, "economics")

    events = merge_sources(all_events, config)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    logging.info("Written %d events to %s", len(events), OUTPUT_PATH)

    export_spa_data(events)


if __name__ == "__main__":
    if "--export-only" in __import__("sys").argv:
        try:
            events = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except (ValueError, OSError) as e:
            logging.error("export-only failed to load %s: %s", OUTPUT_PATH, e)
            raise SystemExit(1)
        export_spa_data(events)
    else:
        main()