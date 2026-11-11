#!/usr/bin/env python3
"""Build year-independent school and sports ICS feeds from school-year source files."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "school-years"
OUTPUTS = {
    "school": ROOT / "combined" / "all-school-events.ics",
    "sports": ROOT / "combined" / "all-sports.ics",
}

def unfold(text):
    result = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.startswith((" ", "\t")) and result:
            result[-1] += line[1:]
        elif line:
            result.append(line)
    return result

def blocks(lines, name):
    result, current, depth = [], [], 0
    begin, end = f"BEGIN:{name}", f"END:{name}"
    for line in lines:
        if line == begin:
            current, depth = [line], 1
        elif current:
            current.append(line)
            if line == begin: depth += 1
            elif line == end:
                depth -= 1
                if depth == 0:
                    result.append(current)
                    current = []
    return result

def value(block, name):
    for line in block:
        if line.upper().startswith(name.upper() + ":") or line.upper().startswith(name.upper() + ";"):
            return line.split(":", 1)[1]
    return ""

def event_sort_key(event):
    return re.sub(r"[^0-9]", "", value(event, "DTSTART")) or "99999999999999"

def build(category, output):
    events, zones, seen = [], {}, set()
    sources = sorted(SOURCE_ROOT.glob(f"**/{category}/**/*.ics"))
    for source in sources:
        lines = unfold(source.read_text(encoding="utf-8-sig"))
        for zone in blocks(lines, "VTIMEZONE"):
            tzid = value(zone, "TZID")
            if tzid: zones.setdefault(tzid, zone)
        for event in blocks(lines, "VEVENT"):
            uid = value(event, "UID")
            key = uid or "\n".join(event)
            if key not in seen:
                seen.add(key)
                events.append(event)
    events.sort(key=event_sort_key)
    label = "Pauls Valley Public Schools — All School Events" if category == "school" else "Pauls Valley Schools — All Sports"
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//Personal Calendar Feeds//Pauls Valley Combined Calendars//EN",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{label}",
             "X-WR-TIMEZONE:America/Chicago"]
    for tzid in sorted(zones): lines.extend(zones[tzid])
    for event in events: lines.extend(event)
    lines.append("END:VCALENDAR")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    print(f"{category}: {len(events)} events from {len(sources)} source files")

if __name__ == "__main__":
    for category, output in OUTPUTS.items(): build(category, output)
