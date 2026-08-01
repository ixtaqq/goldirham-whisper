#!/usr/bin/env python3
"""
Shadow Trader Weekly Digest
Picks the 3 most obscure upcoming events and writes an RSS item that a free
Mailchimp RSS-to-email campaign turns into a Sunday email.

Reads : data/events.json        (aggregator output)
Writes: static/digest.xml       (served at /digest.xml by Hugo)
"""

import json
import logging
import os
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Paths — note: the aggregator writes data/events.json (NOT static/data/events.json)
EVENTS_PATH = Path(__file__).parent.parent / "data" / "events.json"
RSS_PATH = Path(__file__).parent.parent / "static" / "digest.xml"

# Set this env var (or edit below) to your real domain. The <link> is only used
# by feed readers; Mailchimp delivers via the item description.
SITE_URL = os.environ.get("DIGEST_SITE_URL", "https://goldirhamwhisper.example.com/")

# Mainstream sources that won't be considered "obscure".
# Substring-matched against our actual source names (e.g. "New York Stock Exchange").
MAINSTREAM_SOURCES = [
    "federal reserve", "european central bank", "bank of england", "bank of canada",
    "bank of japan", "nyse", "nasdaq", "london stock exchange", "tokyo stock exchange",
    "pboc", "people's bank", "imf", "world bank", "cme group", "cboe",
    "eurostat", "bureau of labor", "us treasury",
]

# Substring flag matcher — mirrors layouts/partials/store.html (GW_FLAGS) so the
# digest email shows the same flags as the site. Specific patterns first.
FLAG_PAIRS = [
    ("nasdaq nordic", "\U0001F1F8\U0001F1EA"), ("omx", "\U0001F1F8\U0001F1EA"),
    ("new york stock exchange", "\U0001F1FA\U0001F1F8"), ("nyse", "\U0001F1FA\U0001F1F8"),
    ("nasdaq", "\U0001F1FA\U0001F1F8"), ("cme", "\U0001F1FA\U0001F1F8"),
    ("cboe", "\U0001F1FA\U0001F1F8"), ("dtcc", "\U0001F1FA\U0001F1F8"),
    ("msci", "\U0001F1FA\U0001F1F8"), ("ice futures", "\U0001F1FA\U0001F1F8"),
    ("chicago board", "\U0001F1FA\U0001F1F8"), ("london stock exchange", "\U0001F1EC\U0001F1E7"),
    ("lse", "\U0001F1EC\U0001F1E7"), ("euronext", "\U0001F1EA\U0001F1FA"),
    ("deutsche börse", "\U0001F1E9\U0001F1EA"), ("deutsche borse", "\U0001F1E9\U0001F1EA"),
    ("eurex", "\U0001F1E9\U0001F1EA"), ("tokyo stock exchange", "\U0001F1EF\U0001F1F5"),
    ("jpx", "\U0001F1EF\U0001F1F5"), ("ose", "\U0001F1EF\U0001F1F5"),
    ("singapore exchange", "\U0001F1F8\U0001F1EC"), ("sgx", "\U0001F1F8\U0001F1EC"),
    ("asx", "\U0001F1E6\U0001F1FA"), ("hkex", "\U0001F1ED\U0001F1F0"),
    ("hong kong", "\U0001F1ED\U0001F1F0"), ("shanghai", "\U0001F1E8\U0001F1F3"),
    ("shenzhen", "\U0001F1E8\U0001F1F3"), ("nbs", "\U0001F1E8\U0001F1F3"),
    ("pboc", "\U0001F1E8\U0001F1F3"), ("korea exchange", "\U0001F1F0\U0001F1F7"),
    ("krx", "\U0001F1F0\U0001F1F7"), ("tsx", "\U0001F1E8\U0001F1E6"),
    ("tmx", "\U0001F1E8\U0001F1E6"), ("six", "\U0001F1E8\U0001F1ED"),
    ("borsa italiana", "\U0001F1EE\U0001F1F9"), ("iberclear", "\U0001F1EA\U0001F1F8"),
    ("bme", "\U0001F1EA\U0001F1F8"), ("tadawul", "\U0001F1F8\U0001F1E6"),
    ("saudi", "\U0001F1F8\U0001F1E6"), ("bovespa", "\U0001F1E7\U0001F1F7"),
    ("b3", "\U0001F1E7\U0001F1F7"), ("ibge", "\U0001F1E7\U0001F1F7"),
    ("bmv", "\U0001F1F2\U0001F1FD"), ("inegi", "\U0001F1F2\U0001F1FD"),
    ("jse", "\U0001F1FF\U0001F1E6"), ("idx", "\U0001F1EE\U0001F1E9"),
    ("indonesia", "\U0001F1EE\U0001F1E9"), ("twse", "\U0001F1F9\U0001F1FC"),
    ("taiwan", "\U0001F1F9\U0001F1FC"), ("mospi", "\U0001F1EE\U0001F1F3"),
    ("nse", "\U0001F1EE\U0001F1F3"), ("bse india", "\U0001F1EE\U0001F1F3"),
    # economics issuers
    ("bls", "\U0001F1FA\U0001F1F8"), ("bureau of labor", "\U0001F1FA\U0001F1F8"),
    ("federal reserve", "\U0001F1FA\U0001F1F8"), ("bea", "\U0001F1FA\U0001F1F8"),
    ("treasury", "\U0001F1FA\U0001F1F8"), ("ism", "\U0001F1FA\U0001F1F8"),
    ("sp global", "\U0001F1FA\U0001F1F8"), ("ecb", "\U0001F1EA\U0001F1FA"),
    ("eurostat", "\U0001F1EA\U0001F1FA"), ("bank of japan", "\U0001F1EF\U0001F1F5"),
    ("boj", "\U0001F1EF\U0001F1F5"), ("destatis", "\U0001F1E9\U0001F1EA"),
    ("ifo", "\U0001F1E9\U0001F1EA"), ("bank of england", "\U0001F1EC\U0001F1E7"),
    ("mni", "\U0001F1EC\U0001F1E7"), ("rba", "\U0001F1E6\U0001F1FA"),
]
FLAG_DEFAULT = "\U0001F310"


def get_flag(source_name):
    if not source_name:
        return FLAG_DEFAULT
    s = str(source_name).lower()
    for key, flag in FLAG_PAIRS:
        if key in s:
            return flag
    return FLAG_DEFAULT


def load_events():
    if not EVENTS_PATH.exists():
        logging.warning("No events file at %s", EVENTS_PATH)
        return []
    with open(EVENTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def score_obscurity(event):
    """Score 0-10+ — how under-the-radar is this event?"""
    score = 0
    # 1. Source obscurity (up to +4)
    source_lower = str(event.get("source", "")).lower()
    if not any(ms in source_lower for ms in MAINSTREAM_SOURCES):
        score += 4
    # 2. Description length: longer = more niche detail (up to +3)
    desc_len = len(event.get("description") or "")
    if desc_len > 200:
        score += 3
    elif desc_len > 100:
        score += 2
    elif desc_len > 30:
        score += 1
    # 3. Tag bonus for genuinely obscure keywords
    tags = [str(t).lower() for t in event.get("tags", [])]
    obscure_keywords = {
        "maintenance", "settlement", "ccass", "warrant", "reconstitution", "baltic",
        "tic", "tankan", "drill", "failover", "opex", "roll", "migration", "expiry",
        "saron", "luld", "itch", "chess", "iso20022",
    }
    score += sum(2 for t in tags if t in obscure_keywords)
    return score


def is_community_event(event):
    """True if the event came from a community submission."""
    if str(event.get("source", "")).strip().lower() == "community":
        return True
    tags = [str(t).lower() for t in event.get("tags", [])]
    return "community" in tags


def select_events(events, top_n=3):
    """Filter the next 7 days (starting tomorrow), keep the weirdest top_n,
    and pick the best community submission not already in the top.
    Returns (top_events, community_pick) — community_pick may be None."""
    today = date.today()
    start = today + timedelta(days=1)
    end = start + timedelta(days=7)
    upcoming = []
    for ev in events:
        if str(ev.get("status") or "approved").strip().lower() == "pending":
            continue  # belt-and-braces: aggregator already staged these out
        try:
            ev_date = datetime.strptime(str(ev.get("date")), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if start <= ev_date <= end:
            upcoming.append(ev)
    if not upcoming:
        return [], None

    upcoming.sort(key=score_obscurity, reverse=True)
    top = upcoming[:top_n]

    community_events = [e for e in upcoming if is_community_event(e) and e not in top]
    community_pick = max(community_events, key=score_obscurity) if community_events else None
    return top, community_pick


def build_html(top_events, community_pick):
    today_str = date.today().strftime("%d %B %Y")
    parts = [f"<h2>\U0001F575\uFE0F Shadow Trader Digest \u2013 {today_str}</h2>",
             "<p>Three under-the-radar events that might quietly move markets this week:</p>",
             "<ol>"]
    for ev in top_events:
        ev_date = datetime.strptime(str(ev["date"]), "%Y-%m-%d").strftime("%A, %d %B")
        flag = get_flag(ev.get("source", ""))
        parts.append(
            f"<li><strong>{flag} {ev['title']}</strong><br/>"
            f"<em>{ev_date} \u00b7 {ev.get('source', '')}</em><br/>"
            f"{str(ev.get('description', ''))[:250]}<br/>"
            f"<a href=\"{ev.get('url') or SITE_URL}\">Source \u2192</a></li>"
        )
    parts.append("</ol>")

    if community_pick:
        ev_date = datetime.strptime(str(community_pick["date"]), "%Y-%m-%d").strftime("%A, %d %B")
        flag = get_flag(community_pick.get("source", ""))
        parts.append(
            f"<hr/><h3>\U0001FAF5 Community Pick of the Week</h3>"
            f"<p><strong>{flag} {community_pick['title']}</strong><br/>"
            f"<em>{ev_date} \u00b7 {community_pick['source']}</em><br/>"
            f"{str(community_pick.get('description', ''))[:250]}<br/>"
            f"<a href=\"{community_pick.get('url') or SITE_URL}\">Source \u2192</a></p>"
            f"<p><em>Submitted by a Goldirham Whisper reader. Want to contribute? "
            f"<a href=\"{SITE_URL}about/\">Submit your own event</a>.</em></p>"
        )

    parts.append("<p>Stay hidden. Stay ahead.<br/>\u2014 Goldirham Whisper</p>")
    return "<br/>".join(parts)


def write_rss(html_content, link=SITE_URL, title="Shadow Trader Weekly Digest"):
    now = datetime.now(timezone.utc)
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "link").text = link
    ET.SubElement(channel, "description").text = "Weekly hand-picked obscure financial events"
    ET.SubElement(channel, "lastBuildDate").text = now.strftime("%a, %d %b %Y %H:%M:%S +0000")

    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = f"Shadow Trader Digest \u2013 {date.today().strftime('%d %B %Y')}"
    ET.SubElement(item, "link").text = link
    # Mailchimp RSS campaigns sort/dedupe on pubDate + guid — both are required.
    ET.SubElement(item, "pubDate").text = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
    ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = f"digest-{date.today().isoformat()}"
    ET.SubElement(item, "description").text = html_content

    tree = ET.ElementTree(rss)
    RSS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tree.write(RSS_PATH, encoding="utf-8", xml_declaration=True)
    logging.info("RSS digest written to %s", RSS_PATH)


def main():
    events = load_events()
    if not events:
        write_rss("<p>No events on file. Check back next Sunday.</p>")
        return
    top, community = select_events(events)
    if not top and not community:
        html = "<p>No obscure events found in the next 7 days. The markets are quiet \u2013 for now.</p>"
    else:
        html = build_html(top, community)
    write_rss(html)


if __name__ == "__main__":
    main()