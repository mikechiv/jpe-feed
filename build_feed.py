#!/usr/bin/env python3
"""
Build an RSS feed of Journal of Political Economy articles, combining:
  1. "Ahead of Print" articles (DOI registered, no volume/issue assigned)
  2. Articles in the latest published issue

Data source: CrossRef REST API. Stdlib only - no pip installs needed.
"""

import json
import time
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

ISSN = "1537-534X"  # JPE online ISSN
JOURNAL_NAME = "Journal of Political Economy"
FEED_TITLE = f"{JOURNAL_NAME}"
FEED_LINK = "https://www.journals.uchicago.edu/journal/jpe"
OUTPUT = "feed.xml"

BASE = f"https://api.crossref.org/journals/{ISSN}/works"
UA = {"User-Agent": "jpe-feed/2.0 (mailto:you@example.com)"}


def fetch(url, attempts=4):
    """Fetch with retries: CrossRef occasionally returns transient 5xx errors."""
    last_error = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)["message"]["items"]
        except Exception as e:
            last_error = e
            wait = 10 * (attempt + 1)  # 10s, 20s, 30s
            print(f"Fetch failed ({e}); retrying in {wait}s "
                  f"[{attempt + 1}/{attempts}]")
            if attempt < attempts - 1:
                time.sleep(wait)
    raise last_error


def is_article(item):
    if item.get("type") != "journal-article":
        return False
    title = (item.get("title") or [""])[0].lower()
    # Skip errata/corrections; delete these two lines to keep them.
    if title.startswith(("erratum", "correction", "corrigendum", "retraction")):
        return False
    return bool(item.get("title"))


def in_issue(item):
    return bool(item.get("volume")) or bool(item.get("issue"))


def created_dt(item):
    ts = item.get("created", {}).get("timestamp")
    if ts:
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    return datetime.now(timezone.utc)


def published_dt(item):
    for key in ("published", "published-online", "published-print"):
        parts = item.get(key, {}).get("date-parts", [[None]])[0]
        if parts and parts[0]:
            y = parts[0]
            m = parts[1] if len(parts) > 1 else 1
            d = parts[2] if len(parts) > 2 else 1
            return datetime(y, m, d, tzinfo=timezone.utc)
    return created_dt(item)


def get_ahead_of_print():
    items = fetch(f"{BASE}?sort=created&order=desc&rows=100")
    return [w for w in items if is_article(w) and not in_issue(w)]


def get_latest_issue():
    try:
        items = fetch(f"{BASE}?sort=published&order=desc&rows=100")
    except Exception as e:
        # If this query keeps failing, ship the feed with AOP items only
        # rather than failing the whole run; next scheduled run catches up.
        print(f"WARNING: latest-issue query failed after retries ({e}); "
              "building feed with ahead-of-print items only this run.")
        return [], None
    issue_items = [w for w in items if is_article(w) and in_issue(w)]
    if not issue_items:
        return [], None
    newest = max(issue_items, key=published_dt)
    vol, iss = newest.get("volume"), newest.get("issue")
    latest = [w for w in issue_items
              if w.get("volume") == vol and w.get("issue") == iss]
    label = f"Volume {vol}" + (f", Issue {iss}" if iss else "")
    return latest, label


def author_string(item):
    names = []
    for a in item.get("author", []):
        full = f"{a.get('given', '')} {a.get('family', '')}".strip()
        if full:
            names.append(full)
    return ", ".join(names)


def rss_item(item, section, date):
    title = escape(item["title"][0])
    doi = item["DOI"]
    desc_bits = [f"[{section}]"]
    authors = author_string(item)
    if authors:
        desc_bits.append(f"Authors: {authors}")
    if item.get("abstract"):
        desc_bits.append(escape(item["abstract"]))
    return "\n".join([
        "<item>",
        f"<title>{title}</title>",
        f"<link>https://doi.org/{escape(doi)}</link>",
        f"<guid isPermaLink=\"false\">{escape(doi)}</guid>",
        f"<category>{escape(section)}</category>",
        f"<pubDate>{format_datetime(date)}</pubDate>",
        f"<description>{escape('<br/><br/>'.join(desc_bits))}</description>",
        "</item>",
    ])


def main():
    aop = get_ahead_of_print()
    issue, issue_label = get_latest_issue()

    entries = []
    seen = set()
    for w in aop:
        if w["DOI"] not in seen:
            seen.add(w["DOI"])
            entries.append(rss_item(w, "Ahead of Print", created_dt(w)))
    for w in issue:
        if w["DOI"] not in seen:
            seen.add(w["DOI"])
            entries.append(rss_item(w, issue_label, published_dt(w)))

    now = format_datetime(datetime.now(timezone.utc))
    rss = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "<channel>",
        f"<title>{escape(FEED_TITLE)}</title>",
        f"<link>{escape(FEED_LINK)}</link>",
        "<description>JPE ahead-of-print articles and the latest "
        "published issue (via CrossRef)</description>",
        f"<lastBuildDate>{now}</lastBuildDate>",
        *entries,
        "</channel>",
        "</rss>",
    ])
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"Wrote {OUTPUT}: {len(aop)} ahead-of-print, "
          f"{len(entries) - len(aop)} from {issue_label}")


if __name__ == "__main__":
    main()
