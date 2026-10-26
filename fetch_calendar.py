#!/usr/bin/env python3
"""
Pull the next N days of events from a public Google Calendar and write
them to a standalone ICS file.

Configuration (environment variables):
  CALENDAR_ID   Required. Either the calendar ID (e.g. abc123@group.calendar.google.com)
                or the full "Public address in iCal format" URL.
  DAYS_AHEAD    Optional. How many days ahead to include. Default: 14.
  OUTPUT_FILE   Optional. Where to write the ICS. Default: public/calendar.ics
  SOURCE_FILE   Optional. Read a local .ics instead of fetching (for testing).
"""

import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import icalendar
import recurring_ical_events


def feed_url(calendar_id: str) -> str:
    """Accept either a bare calendar ID or a full iCal URL."""
    if calendar_id.startswith(("http://", "https://")):
        return calendar_id
    return (
        "https://calendar.google.com/calendar/ical/"
        f"{quote(calendar_id, safe='')}/public/basic.ics"
    )


def load_source() -> bytes:
    source_file = os.environ.get("SOURCE_FILE")
    if source_file:
        with open(source_file, "rb") as fh:
            return fh.read()

    calendar_id = os.environ.get("CALENDAR_ID", "").strip()
    if not calendar_id:
        sys.exit("CALENDAR_ID is not set.")

    req = Request(feed_url(calendar_id), headers={"User-Agent": "calendar-feed/1.0"})
    try:
        with urlopen(req, timeout=60) as resp:
            data = resp.read()
    except HTTPError as err:
        if err.code in (403, 404):
            sys.exit(
                f"Google returned {err.code} for the calendar feed. The calendar is probably "
                "not public – tick 'Make available to public' in its settings, or set "
                "CALENDAR_ID to the calendar's 'Secret address in iCal format'."
            )
        raise
    if b"BEGIN:VCALENDAR" not in data[:500]:
        sys.exit("The calendar URL did not return an iCal feed – is the calendar public?")
    return data


def sort_key(event) -> datetime:
    """Normalise all-day dates and naive/aware datetimes so they sort together."""
    start = event.get("DTSTART").dt
    if isinstance(start, datetime):
        return start if start.tzinfo else start.replace(tzinfo=timezone.utc)
    return datetime(start.year, start.month, start.day, tzinfo=timezone.utc)


def build_calendar(raw: bytes, days_ahead: int) -> tuple[icalendar.Calendar, int]:
    source = icalendar.Calendar.from_ical(raw)

    window_start = datetime.now(timezone.utc)
    window_end = window_start + timedelta(days=days_ahead)
    events = recurring_ical_events.of(source).between(window_start, window_end)

    out = icalendar.Calendar()
    out.add("PRODID", "-//Calendar feed//Next two weeks//EN")
    out.add("VERSION", "2.0")
    out.add("CALSCALE", "GREGORIAN")
    out.add("METHOD", "PUBLISH")

    name = source.get("X-WR-CALNAME")
    out.add("X-WR-CALNAME", f"{name} (next {days_ahead} days)" if name else f"Next {days_ahead} days")
    if source.get("X-WR-TIMEZONE"):
        out.add("X-WR-TIMEZONE", source.get("X-WR-TIMEZONE"))
    out.add(
        "X-WR-CALDESC",
        f"Snapshot generated {window_start:%Y-%m-%d %H:%M} UTC covering {days_ahead} days.",
    )

    # Keep the source time-zone definitions so local times stay correct.
    for tz in source.walk("VTIMEZONE"):
        out.add_component(tz)

    for event in sorted(events, key=sort_key):
        # Each occurrence becomes a standalone event: drop recurrence rules and
        # give it a unique UID so calendar apps don't merge occurrences together.
        for prop in ("RRULE", "RDATE", "EXDATE", "RECURRENCE-ID"):
            if prop in event:
                del event[prop]
        start = event.get("DTSTART").dt
        stamp = start.strftime("%Y%m%dT%H%M%S") if isinstance(start, datetime) else start.strftime("%Y%m%d")
        uid = str(event.get("UID", "event"))
        event["UID"] = f"{uid}-{stamp}"
        out.add_component(event)

    return out, len(events)


def write_atomically(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)


def main() -> None:
    days_ahead = int(os.environ.get("DAYS_AHEAD", "14"))
    output_file = os.environ.get("OUTPUT_FILE", "public/calendar.ics")

    raw = load_source()
    calendar, count = build_calendar(raw, days_ahead)
    write_atomically(output_file, calendar.to_ical())
    print(f"Wrote {count} event(s) for the next {days_ahead} days to {output_file}")


if __name__ == "__main__":
    main()
