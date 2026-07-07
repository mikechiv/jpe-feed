#!/usr/bin/env python3
"""
Build an RSS feed of Journal of Political Economy "Ahead of Print" articles.

Data source: CrossRef REST API (no scraping, no bot detection issues).
JPE registers a DOI when an article is posted online ahead of print.
Ahead-of-print records have no volume/issue assigned yet, which is how
we separate them from articles already placed in an issue.

Stdlib only - no pip installs needed.
"""

import json
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

ISSN = "1537-534X"  # JPE online ISSN
JOURNAL_NAME = "Journal of Political Economy"
FEED_TITLE = f"{JOURNAL_NAME} - Ahead of Print"
FEED_LINK = "https://www.journals.uchicago.edu/toc/jpe/0/ja"
MAX_ITEMS = 40
OUTPUT = "feed.xml"

API_URL = (
    f"https://api.crossref.org/journals/{ISSN}/works"
    f"?sort=created&order=desc&rows=100"
    f"&select=DOI,title,author,created,volume,issue,abstract,URL,type"
)


def fetch_works():
    req = urllib.request.Request(
        API_URL,
        # CrossRef asks for a contact in the UA for their "polite pool"
        headers={"User-Agent": "jpe-aop-feed/1.0 (mailto:you@example.com)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return data["message"]["items"]


def is_ahead_of_print(item):
    if item.get("type") != "journal-article":
        return False
    # Articles assigned to an issue have volume/issue set; AOP ones don't.
    return not item.get("volume") and not item.get("issue")


def author_string(item):
    names = []
    for a in item.get("author", []):
        given, family = a.get("given", ""), a.get("family", "")
        full = f"{given} {family}".strip()
        if full:
            names.append(full)
    return ", ".join(names)


def created_datetime(item):
    ts = item.get("created", {}).get("timestamp")
    if ts:
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    return datetime.now(timezone.utc)


def build_rss(items):
    now = format_datetime(datetime.now(timezone.utc))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "<channel>",
        f"<title>{escape(FEED_TITLE)}</title>",
        f"<link>{escape(FEED_LINK)}</link>",
        "<description>New JPE articles posted online ahead of print "
        "(via CrossRef DOI registrations)</description>",
        f"<lastBuildDate>{now}</lastBuildDate>",
    ]
    for item in items:
        title = escape(item.get("title", ["Untitled"])[0])
        doi = item["DOI"]
        link = f"https://doi.org/{doi}"
        authors = escape(author_string(item))
        pub_date = format_datetime(created_datetime(item))
        desc_bits = []
        if authors:
            desc_bits.append(f"Authors: {authors}")
        if item.get("abstract"):
            desc_bits.append(escape(item["abstract"]))
        description = "<br/><br/>".join(desc_bits) or title
        parts += [
            "<item>",
            f"<title>{title}</title>",
            f"<link>{escape(link)}</link>",
            f"<guid isPermaLink=\"false\">{escape(doi)}</guid>",
            f"<pubDate>{pub_date}</pubDate>",
            f"<description>{escape(description)}</description>",
            "</item>",
        ]
    parts += ["</channel>", "</rss>"]
    return "\n".join(parts)


def main():
    works = fetch_works()
    aop = [w for w in works if is_ahead_of_print(w)]
    aop.sort(key=created_datetime, reverse=True)
    aop = aop[:MAX_ITEMS]
    rss = build_rss(aop)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"Wrote {OUTPUT} with {len(aop)} ahead-of-print articles")


if __name__ == "__main__":
    main()
