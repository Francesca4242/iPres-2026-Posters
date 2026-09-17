#!/usr/bin/env python3
"""
Prove that the website shows the submitted metadata unchanged.

Every title, abstract, author name, keyword and institution in data/posters.json
is compared character for character against poster_metadata.csv. Nothing may be
re-spaced, re-punctuated, reordered or "tidied" on its way to the page.

    python3 tools/check_verbatim.py

Exits non-zero (and says what differs) if anything has drifted.
"""

import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "poster_metadata.csv")
JSON_PATH = os.path.join(ROOT, "data", "posters.json")


def read_metadata():
    raw = open(CSV_PATH, "rb").read()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return list(csv.DictReader(raw.decode(encoding).splitlines()))
        except UnicodeDecodeError:
            continue
    sys.exit("Could not decode poster_metadata.csv")


def newline_only(text):
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def main():
    rows = read_metadata()
    posters = json.load(open(JSON_PATH, encoding="utf-8"))["posters"]
    by_title = {p["title"]: p for p in posters}
    problems = []

    for row in rows:
        title = newline_only(row["title"])
        poster = by_title.get(title)
        if poster is None:
            problems.append("title not found verbatim in posters.json: {!r}".format(title))
            continue
        if poster["abstract"] != newline_only(row["abstract_plain"]):
            problems.append("abstract differs for {!r}".format(title[:60]))
        for author in poster["authors"]:
            if author["raw"] not in row["authors"]:
                problems.append("author {!r} is not verbatim in {!r}".format(author["raw"], title[:40]))
            if author["name"] not in author["raw"]:
                problems.append("author display name {!r} was rewritten".format(author["name"]))
        for keyword in poster["keywords"]:
            if keyword not in row["keywords"]:
                problems.append("keyword {!r} is not verbatim in {!r}".format(keyword, title[:40]))
        for org in poster["organisations"]:
            if org not in row["organisations"]:
                problems.append("institution {!r} is not verbatim in {!r}".format(org, title[:40]))
        for topic in poster["topics"]:
            if topic not in row["topics"]:
                problems.append("topic {!r} is not verbatim in {!r}".format(topic, title[:40]))
        for field, column in (("orientation", "landscape/ portrait"), ("attendance", "online/ in-person")):
            value = poster.get(field)
            if value and value.lower() not in (row.get(column) or "").lower():
                problems.append("{} {!r} is not verbatim in {!r}".format(field, value, title[:40]))
        # Columns copied straight through, when the CSV has them at all.
        for field, column in (("presenting", "presenting"), ("locationHint", "poster_location")):
            if poster.get(field) and poster[field] != newline_only(row.get(column)):
                problems.append("{} {!r} was rewritten in {!r}".format(
                    field, poster[field], title[:40]))

    if problems:
        print("Metadata has been altered:")
        for problem in problems:
            print("  -", problem)
        sys.exit(1)

    print("All {} posters: titles, abstracts, authors, keywords, institutions, "
          "topics, orientation and presenting times are character-for-character "
          "identical to the "
          "CSV.".format(len(rows)))


if __name__ == "__main__":
    main()
