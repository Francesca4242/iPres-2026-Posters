#!/usr/bin/env python3
"""
Build data/posters.json for the iPRES 2026 virtual poster hall.

Reads:
  poster_metadata.csv      - one row per accepted poster (exported from the CMS)
  posters/*.pdf            - the poster files themselves
  tools/poster_files.csv   - optional id -> filename overrides

Writes:
  data/posters.json        - everything the website needs

Run it after adding a new poster PDF or editing the metadata:

    python3 tools/build_data.py

It needs nothing but a standard Python 3 install - no pip, no node.
"""

import csv
import difflib
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "poster_metadata.csv")
PDF_DIR = os.path.join(ROOT, "posters")
OVERRIDES = os.path.join(ROOT, "tools", "poster_files.csv")
OUT = os.path.join(ROOT, "data", "posters.json")

# The iPRES topic taxonomy arrives as one line per topic group. Each group
# becomes a colour-coded theme used by the gallery filters, the map and the
# trails.
THEMES = [
    {
        "id": "infrastructure",
        "name": "Infrastructure & Storage",
        "short": "Infrastructure",
        "emoji": "\U0001F5C4️",
        "color": "#0b82c6",
        "blurb": "Bits, boxes, tape and the machinery that keeps them alive.",
        "topics": ["Technical Infrastructure", "Tools", "Storage", "Bit Preservation"],
    },
    {
        "id": "community",
        "name": "Community & Collaboration",
        "short": "Community",
        "emoji": "\U0001F91D",
        "color": "#ef4444",
        "blurb": "Nobody preserves anything alone: networks, partnerships and shared effort.",
        "topics": ["Community", "Collaborations"],
    },
    {
        "id": "formats",
        "name": "Formats & Integrity",
        "short": "Formats",
        "emoji": "\U0001F9EC",
        "color": "#8b5cf6",
        "blurb": "File formats, fixity, migration and keeping content genuinely usable.",
        "topics": ["File Formats", "Content Integrity", "Migrations", "Content Preservation"],
    },
    {
        "id": "management",
        "name": "Management & Costs",
        "short": "Management",
        "emoji": "\U0001F4CA",
        "color": "#f97316",
        "blurb": "People, money, maturity models and proving that any of it works.",
        "topics": ["Management", "Organizations", "Staffing", "Repository Assessments", "Costs"],
    },
    {
        "id": "metadata",
        "name": "Metadata & Description",
        "short": "Metadata",
        "emoji": "\U0001F3F7️",
        "color": "#10b981",
        "blurb": "The data about the data: schemas, description and provenance.",
        "topics": ["Metadata", "Description"],
    },
    {
        "id": "access",
        "name": "Access & Discovery",
        "short": "Access",
        "emoji": "\U0001F50D",
        "color": "#06b6d4",
        "blurb": "Getting preserved things back out again, and making them findable.",
        "topics": ["Discovery", "Access", "Delivery", "Emulation"],
    },
    {
        "id": "ingest",
        "name": "Appraisal & Ingest",
        "short": "Appraisal",
        "emoji": "\U0001F4E5",
        "color": "#eab308",
        "blurb": "Choosing what comes in, and getting it through the front door.",
        "topics": ["Appraisal / Selection", "Acquisition", "Ingest"],
    },
    {
        "id": "policy",
        "name": "Policy & Ethics",
        "short": "Policy",
        "emoji": "⚖️",
        "color": "#d946ef",
        "blurb": "Law, ethics, sustainability and the strategies that hold it together.",
        "topics": ["Legal / Ethical / Environmental Considerations", "Policy", "Strategy"],
    },
]

TOPIC_TO_THEME = {}
for _theme in THEMES:
    for _topic in _theme["topics"]:
        TOPIC_TO_THEME[_topic.lower()] = _theme["id"]


def clean(text):
    """Return the field EXACTLY as the export has it.

    Titles, abstracts, author names, institutions and keywords are never
    rewritten, re-spaced, re-punctuated or "corrected": whatever the presenters
    submitted is what the website shows. The only thing normalised here is the
    line ending, which is a file-format artefact rather than part of the text.
    Character encoding is handled once, in read_metadata.
    """
    if not text:
        return ""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def slugify(text):
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    words = [w for w in text.split("-") if w]
    return "-".join(words[:8]) or "poster"


def squash(text):
    """Aggressively normalise for filename matching."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", text.lower())


def split_people(raw):
    """Split the semicolon-separated author field into one entry per person.

    Names are NOT reordered, reformatted or otherwise touched - "Schmid, Irina"
    stays "Schmid, Irina". The only thing lifted out of the name is the trailing
    "(1)" footnote marker, which is a pointer into the institution list rather
    than part of anybody's name; it is kept in `affiliations` and used to show
    the right institution beside them. `raw` is the untouched original and
    `last` exists only so the site can sort and match on a surname.
    """
    people = []
    for chunk in re.split(r";|\n", clean(raw)):
        if not chunk.strip():
            continue
        original = chunk.strip()
        affil = re.findall(r"\(([\d,\s]+)\)\s*$", original)
        name = re.sub(r"\s*\(([\d,\s]+)\)\s*$", "", original)
        last = name.split(",")[0].strip() if "," in name else (name.split() or [name])[-1]
        people.append({
            "name": name,
            "raw": original,
            "last": last,
            "affiliations": [a.strip() for a in affil[0].split(",")] if affil else [],
        })
    return people


def split_orgs(raw):
    """Split the institution field into one entry per institution.

    The leading "1:" / "2:" on each line is the numbering that ties an
    institution to an author's footnote marker, not part of the institution's
    name, so it is dropped from the display name and kept implicitly as the
    list position. Every institution name itself is left exactly as submitted.
    """
    orgs = []
    for chunk in re.split(r";\n|;(?=\s*\d+:)|\n", clean(raw)):
        chunk = re.sub(r"^\d+\s*:\s*", "", chunk.strip())
        if chunk and chunk not in orgs:
            orgs.append(chunk)
    return orgs


def split_list(raw):
    out = []
    for chunk in re.split(r"[,\n]", clean(raw)):
        chunk = chunk.strip()
        if chunk and chunk not in out:
            out.append(chunk)
    return out


def load_overrides():
    mapping = {}
    if not os.path.exists(OVERRIDES):
        return mapping
    with open(OVERRIDES, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            pid = (row.get("id") or "").strip()
            fname = (row.get("filename") or "").strip()
            if pid and fname:
                mapping[pid] = fname
    return mapping


#: file_name values that mean "this poster has not been sent yet".
PLACEHOLDERS = {"", "placeholder", "tbc", "tba", "n/a", "na", "none", "-"}


def resolve_name(name, by_nfc):
    """Turn a file_name from the CSV into a real filename in posters/.

    The export is cp1252, so a filename with a character that encoding cannot
    represent arrives mangled - "1093_Tome?_Adapting-to-Context.pdf" is really
    "1093_Tomé_...". Where a name does not match a file on disk, any "?" is
    treated as a single-character wildcard before giving up. The wildcard is
    tried against both the composed and decomposed spelling of each filename,
    because "?" may have replaced a whole accented letter or just the accent.
    """
    if not name:
        return None
    exact = by_nfc.get(unicodedata.normalize("NFC", name))
    if exact:
        return exact
    if "?" in name:
        pattern = re.compile("^" + ".".join(re.escape(part) for part in name.split("?")) + "$")
        hits = {
            real for real in by_nfc.values()
            for form in ("NFC", "NFD")
            if pattern.match(unicodedata.normalize(form, real))
        }
        if len(hits) == 1:
            return hits.pop()
    return None


def guess_file(record, available):
    """Best-effort match of a metadata row to a PDF that nobody has mapped yet.

    Scores the longest shared run of characters between the squashed filename
    and the squashed title, with a healthy bonus for each author surname that
    turns up in the filename. A poster named like the existing ones is matched
    automatically; anything doubtful is reported and left unmatched.
    """
    title = squash(record["title"])
    surnames = [squash(p["last"]) for p in record["authors"] if len(p["last"]) > 3]
    best, best_score = None, 0
    for fname in available:
        squashed = squash(fname)
        run = difflib.SequenceMatcher(None, squashed, title).find_longest_match(
            0, len(squashed), 0, len(title)
        ).size
        score = run + 8 * sum(1 for surname in surnames if surname and surname in squashed)
        if score > best_score:
            best, best_score = fname, score
    return (best, best_score) if best_score >= 14 else (None, best_score)


def read_metadata():
    raw = open(CSV_PATH, "rb").read()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return list(csv.DictReader(raw.decode(encoding).splitlines()))
        except UnicodeDecodeError:
            continue
    sys.exit("Could not decode poster_metadata.csv")


def main():
    if not os.path.exists(CSV_PATH):
        sys.exit("Cannot find {}".format(CSV_PATH))

    rows = read_metadata()
    pdfs = sorted(f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf"))
    # Accented filenames can be stored decomposed on disk but composed in the
    # CSV (or the other way round), so match on a normalised form.
    by_nfc = {unicodedata.normalize("NFC", f): f for f in pdfs}
    overrides = load_overrides()
    theme_order = {theme["id"]: i for i, theme in enumerate(THEMES)}

    records, seen_ids = [], {}
    for row in rows:
        title = clean(row.get("title"))
        if not title:
            continue
        pid = slugify(title)
        seen_ids[pid] = seen_ids.get(pid, 0) + 1
        if seen_ids[pid] > 1:
            pid = "{}-{}".format(pid, seen_ids[pid])
        topics = split_list(row.get("topics"))
        theme_ids = []
        for topic in topics:
            tid = TOPIC_TO_THEME.get(topic.lower())
            if tid and tid not in theme_ids:
                theme_ids.append(tid)
        theme_ids.sort(key=lambda t: theme_order[t])
        records.append({
            "id": pid,
            "title": title,
            "abstract": clean(row.get("abstract_plain")),
            "keywords": split_list(row.get("keywords")),
            "topics": topics,
            "themes": theme_ids,
            "authors": split_people(row.get("authors")),
            "organisations": split_orgs(row.get("organisations")),
            "locationHint": clean(row.get("poster_location")),
            "orientation": clean(row.get("landscape/ portrait")).strip().lower() or None,
            "attendance": clean(row.get("online/ in-person")).strip() or None,
            "csvFileName": clean(row.get("file_name")).strip(),
        })

    # Three ways to pair a metadata row with its PDF, in order of authority:
    #   1. tools/poster_files.csv, for anything that needs a manual decision
    #   2. the file_name column of poster_metadata.csv - the normal route
    #   3. a fuzzy match on the title and author surnames, as a last resort
    claimed, guessed, missing = set(), [], []
    for record in records:
        override = overrides.get(record["id"], "")
        fname = resolve_name(override, by_nfc)
        if fname:
            record["file"] = fname
            claimed.add(fname)
            continue
        if override:
            print("  ! override for '{}' points at a missing file: {}".format(record["id"], override))

        stated = record["csvFileName"]
        if stated.lower() in PLACEHOLDERS:
            continue
        fname = resolve_name(stated, by_nfc)
        if fname:
            record["file"] = fname
            claimed.add(fname)
        else:
            missing.append((record["id"], stated))

    for record in records:
        if record.get("file") or record["csvFileName"].lower() in PLACEHOLDERS:
            continue
        fname, _score = guess_file(record, [f for f in pdfs if f not in claimed])
        if fname:
            record["file"] = fname
            claimed.add(fname)
            guessed.append((record["id"], fname))

    for record in records:
        fname = record.get("file")
        if fname:
            record["file"] = "posters/" + fname
            record["fileSize"] = os.path.getsize(os.path.join(PDF_DIR, fname))
            record["status"] = "available"
            number = re.match(r"^(\d{2,4})[_\-]", fname)
            record["number"] = number.group(1) if number else None
        else:
            record["file"] = None
            record["fileSize"] = 0
            record["status"] = "awaited"
            record["number"] = None
        record.pop("csvFileName", None)
        # "online/ in-person" is still being collected, so read it generously:
        # anything that says online / virtual / remote counts as online, and
        # anything mentioning a person counts as in the room. The raw cell is
        # kept as `attendance`; `presentedOnline` is what the website reads.
        said = (record["attendance"] or "").lower()
        if any(word in said for word in ("online", "virtual", "remote")):
            record["presentedOnline"] = True
        elif "person" in said or "onsite" in said or "on-site" in said:
            record["presentedOnline"] = False
        else:
            record["presentedOnline"] = None
        # Landscape is the exception worth flagging; portrait is the norm and
        # saying so just adds noise, so only landscape is surfaced.
        record["landscape"] = record["orientation"] == "landscape"
        record["authorLine"] = "; ".join(p["name"] for p in record["authors"])
        record["searchText"] = " ".join([
            record["title"], record["abstract"], record["authorLine"],
            " ".join(record["keywords"]), " ".join(record["topics"]),
            " ".join(record["organisations"]),
        ]).lower()

    records.sort(key=lambda r: r["title"].lower())

    # Deliberately no build timestamp: it would differ on every run and make
    # the rebuild Action commit a new posters.json even when nothing changed.
    # Git history already records when the data last moved.
    payload = {
        "themes": THEMES,
        "counts": {
            "total": len(records),
            "available": sum(1 for r in records if r["status"] == "available"),
            "awaited": sum(1 for r in records if r["status"] == "awaited"),
        },
        "posters": records,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, ensure_ascii=False)
        handle.write("\n")

    print("Wrote {} - {} posters, {} with a PDF, {} still awaited".format(
        os.path.relpath(OUT, ROOT), len(records),
        payload["counts"]["available"], payload["counts"]["awaited"]))
    if missing:
        print("file_name in the CSV does not match anything in posters/:")
        for pid, stated in missing:
            print("   {:<44} wants {}".format(pid, stated))
    if guessed:
        print("Matched on the title instead of file_name "
              "(fill in file_name, or add a line to tools/poster_files.csv):")
        for pid, fname in guessed:
            print("   {:<44} -> {}".format(pid, fname))
    unused = [f for f in pdfs if f not in claimed]
    if unused:
        print("PDFs with no metadata row - check the filename, or add a CSV row:")
        for fname in unused:
            print("   {}".format(fname))
    for record in records:
        if record["status"] == "awaited":
            print("Still awaiting a PDF: {}".format(record["title"][:70]))


if __name__ == "__main__":
    main()
