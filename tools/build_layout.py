#!/usr/bin/env python3
"""
Generate data/layout.json - the poster hall floor plan used by map.html.

Measured off the venue drawing in map/Poster layout.pptx (Option 4, "Minimal
amount of walls"):

  * Its dimension annotation reads 13.5 m across and 6 m deep, and those rules
    are 323 px and 143 px long, which fixes the drawing at 23.9 px per metre.
  * The four wall marks on it are each 29.9 px - 1.25 m - so that is the width
    of one poster board.
  * Two of the marks lie flat against the south wall at 2.79 m and 5.14 m along
    the foyer. Those are boards 19 and 20, and they are confirmed correct.
  * The other two sit end to end in a line at 15.84 m, running from the south
    wall northwards to 4.03 m. That is the arrangement the whole hall uses: a
    RUN of 1.25 m walls in a line, standing out from the long wall, with a
    poster on each face. It is not a single stub per wall.
  * The drawing's own counts are:
        9 walls = 18 posters      6 walls =  6 posters
        3 walls =  6 posters      5 walls = 10 posters
        2 walls =  2 posters      -----------------------
                                  25 walls, 42 posters
    ...but the organiser has confirmed that the group numbered 31-36 here is
    three DOUBLE-sided walls giving six posters, not six single-sided ones.
    That is 42 posters either way, on 22 walls rather than 25.

The three extra posters the drawing mentions (Reception, the nestor survey and
"Trends in digital preservation") are not on the walls and are not on this map.

CONFIRMED by the organiser: boards 19 and 20 (flat, from the drawing), and that
boards 21-26, 31-36 and 37-42 are each three double-sided walls running south
to north.

STILL TO BE CONFIRMED: where each run sits along the foyer, and the depth of
the room. Every position in the RUNS table below is one number, so correcting
one is a one-line change followed by `python3 tools/build_layout.py --keep`.

Board 1 is the one nearest the stairs, where people come up, and the numbers
count away from there in the order of the RUNS table below - to renumber a
group, move its entry up or down that list. Board numbers are deliberately not tied to any
poster - every board is generated empty and filled in by hand in
data/layout.json. Groups are not named: numbers are all the map shows.

    python3 tools/build_layout.py            # regenerate the boards, empty
    python3 tools/build_layout.py --keep     # keep any boards already filled in
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTERS = os.path.join(ROOT, "data", "posters.json")
OUT = os.path.join(ROOT, "data", "layout.json")

ROOM_LENGTH = 34.5
ROOM_DEPTH = 9.0
BOARD = 1.25           # one board, from the marks on the drawing
GAP = 0.15             # between walls in a run, from the two marks at 15.84 m
WALL_THICKNESS = 0.1

#: Where a three-board run off the south wall reaches to. Shorter runs float so
#: that their north ends sit on this line too.
RUN_END = ROOM_DEPTH - (3 * BOARD + 2 * GAP)

# Deliberately NOT to scale. The real foyer is 34.5 m x 9 m, which drawn
# honestly is a 4:1 strip with boards too small to tap, so the short axis is
# stretched. It is still the longer way round - the map stays a wide rectangle,
# about 2.3:1 - and everything keeps its real order, spacing and side of the
# room, so the walk you do on the map is the walk you do in the foyer.
PX_PER_METRE_X = 64
PX_PER_METRE_Y = 90
FACE_OFFSET = 57        # px between the two faces of a wall, not metres
MARGIN = {"left": 0.7, "top": 0.9, "right": 0.7, "bottom": 1.0}

# Two shapes of wall, both built from the same 1.25 m board:
#   "run"   - boards end to end across the foyer at a fixed x, standing out
#             from `from` and heading `toward`; a poster on each face
#   "flat"  - single boards lying against a wall at each x in `at`
# `group` only ties an entry back to the drawing's counts; it is not shown.
RUNS = [
    # Numbering follows this list: board 1 is the first face of the first entry.
    # The list is in walking order from the stairs, so moving an entry up or
    # down renumbers that group and everything after it. Nothing else has to
    # change - board ids come from position, not from the number on them.

    # 5 walls = 10 posters, as a run of three and the run of two the drawing
    # marks at 15.84 m. The run of two does not touch the south wall: it floats,
    # with its north end level with every other run (RUN_END).
    # These four are 3.6 m apart rather than the drawing's 3 m, so no two number
    # buttons touch, and the group starts just past where the north side ends -
    # board 22 sits a little to the right of board 25, as it does in the foyer.
    {"group": 5, "kind": "run", "walls": 3, "x": 24.8, "from": ROOM_DEPTH, "toward": "north"},
    {"group": 4, "kind": "run", "walls": 3, "x": 21.2, "from": ROOM_DEPTH, "toward": "north"},
    {"group": 3, "kind": "run", "walls": 2, "x": 17.6, "from": RUN_END + 2 * BOARD + GAP,
     "toward": "north"},
    {"group": 3, "kind": "run", "walls": 3, "x": 14.0, "from": ROOM_DEPTH, "toward": "north"},

    # 9 walls = 18 posters, as three runs of three off the north wall.
    {"group": 1, "kind": "run", "walls": 3, "x": 11.0, "from": 0.0, "toward": "south"},

    # 2 walls = 2 posters. The drawing marks these at 2.79 m and 5.14 m; the
    # organiser has nudged them 2 m to the right, keeping the gap between them.
    # Listed nearest-the-stairs first, and standing just off the south wall.
    {"group": 2, "kind": "flat", "wall": "south", "at": [7.14, 4.79]},

    {"group": 1, "kind": "run", "walls": 3, "x": 7.0, "from": 0.0, "toward": "south"},
    {"group": 1, "kind": "run", "walls": 3, "x": 3.0, "from": 0.0, "toward": "south"},
]

# People arrive up the staircase, which runs right to left along the bottom of
# the foyer at its eastern end. There is no door at the far end. The area east
# of the last poster run, above the stairs, is the Community Survey.
FURNITURE = [
    {"kind": "stairs", "label": "Stairs up", "x": 27.3, "y": 7.1, "w": 7.0, "h": 1.9},
    # Just a table, not a zone. Its link lives in data/config.json.
    {"kind": "survey", "label": "Community Survey", "x": 29.6, "y": 5.4, "w": 1.8, "h": 0.8},
]

RUN_HINT = "Free-standing wall, one poster on each face."
FLAT_HINT = "Single-sided board, one poster facing into the room."


def m_to_px(x, y):
    """Metres from the north-west corner of the foyer -> SVG user units."""
    return (round((MARGIN["left"] + x) * PX_PER_METRE_X, 1),
            round((MARGIN["top"] + y) * PX_PER_METRE_Y, 1))


def build(previous):
    """Every wall, numbered from the stairs westwards - board 1 is nearest.

    Wall and board ids are derived from position, not from the numbering, so
    renumbering never silently moves a poster from one board to another.
    """
    entries = []

    for order, spec in enumerate(RUNS):
        if spec["kind"] == "flat":
            for index, along in enumerate(spec["at"]):
                on_north = spec["wall"] == "north"
                y = 0.0 if on_north else ROOM_DEPTH
                face = y + (0.42 if on_north else -0.42)
                entries.append({
                    "sort": (order, index),
                    "id": "F{:.0f}".format(along * 100),
                    "group": spec["group"], "kind": "flat", "hint": FLAT_HINT,
                    "a": (along - BOARD / 2, y), "b": (along + BOARD / 2, y),
                    "faces": [("south" if on_north else "north", 0)],
                    "mid": face, "x": along,
                })
            continue

        heading_north = spec["toward"] == "north"
        for index in range(spec["walls"]):
            offset = index * (BOARD + GAP)
            if heading_north:
                near, far = spec["from"] - offset, spec["from"] - offset - BOARD
            else:
                near, far = spec["from"] + offset, spec["from"] + offset + BOARD
            mid = (near + far) / 2
            wall_id = "X{:.0f}-{}".format(spec["x"] * 10, index + 1)
            entries.append({
                "sort": (order, index),
                "id": wall_id,
                "group": spec["group"], "kind": "run", "hint": RUN_HINT,
                "a": (spec["x"], near), "b": (spec["x"], far),
                "faces": [("east", FACE_OFFSET), ("west", -FACE_OFFSET)],
                "mid": mid, "x": spec["x"],
            })

    # Board 1 is the one closest to the stairs: the RUNS list is in that order,
    # and within a run the numbers run outwards from the wall it stands on.
    entries.sort(key=lambda e: e["sort"])

    walls = []
    for entry in entries:
        base_x, base_y = m_to_px(entry["x"], entry["mid"])
        entry["slots"] = [{
            "id": "{}{}".format(entry["id"], facing[0] if entry["kind"] == "run" else ""),
            "number": None, "x": round(base_x + dx, 1), "y": base_y, "facing": facing,
        } for facing, dx in entry["faces"]]

    # Numbering goes face by face, not wall by wall: walking up to a run of
    # three you see three boards, and those are 1, 2, 3. The three on the back
    # of the same walls are 4, 5, 6 - 4 is behind 1.
    number = 0
    for order in sorted({e["sort"][0] for e in entries}):
        run = [e for e in entries if e["sort"][0] == order]
        for side in range(max(len(e["slots"]) for e in run)):
            for entry in run:
                if side < len(entry["slots"]):
                    number += 1
                    entry["slots"][side]["number"] = number

    for entry in entries:
        for slot in entry["slots"]:
            slot["poster"] = previous.get(slot["id"])
        walls.append({
            "id": entry["id"], "group": entry["group"], "kind": entry["kind"],
            "hint": entry["hint"],
            "x1": m_to_px(*entry["a"])[0], "y1": m_to_px(*entry["a"])[1],
            "x2": m_to_px(*entry["b"])[0], "y2": m_to_px(*entry["b"])[1],
            "thickness": round(WALL_THICKNESS * PX_PER_METRE_Y, 1),
            "slots": entry["slots"],
        })
    return walls


def main():
    keep = "--keep" in sys.argv
    previous = {}
    if keep and os.path.exists(OUT):
        existing = json.load(open(OUT, encoding="utf-8"))
        for wall in existing.get("walls", []):
            for slot in wall.get("slots", []):
                if slot.get("poster"):
                    previous[slot["id"]] = slot["poster"]

    walls = build(previous)
    slots = [s for w in walls for s in w["slots"]]
    filled = sum(1 for s in slots if s["poster"])

    known = set()
    if os.path.exists(POSTERS):
        known = {p["id"] for p in json.load(open(POSTERS, encoding="utf-8"))["posters"]}
    unknown = [s["poster"] for s in slots if s["poster"] and s["poster"] not in known]

    origin_x, origin_y = m_to_px(0, 0)
    far_x, far_y = m_to_px(ROOM_LENGTH, ROOM_DEPTH)

    payload = {
        "provisional": True,
        "note": (
            "Board sizes, counts and the two boards on the south wall come "
            "straight off map/Poster layout.pptx. The map is deliberately NOT "
            "to scale - the short side of the foyer is stretched so the boards "
            "are big enough to tap - but every board keeps its real order and "
            "side of the room. Where each run of walls sits along the foyer is "
            "still being confirmed, and no poster has been put on a board yet."
        ),
        "source": "map/Poster layout.pptx",
        "viewBox": [
            0, 0,
            round((MARGIN["left"] + ROOM_LENGTH + MARGIN["right"]) * PX_PER_METRE_X),
            round((MARGIN["top"] + ROOM_DEPTH + MARGIN["bottom"]) * PX_PER_METRE_Y),
        ],
        "toScale": False,
        "scale": {"pxPerMetreX": PX_PER_METRE_X, "pxPerMetreY": PX_PER_METRE_Y,
                  "margin": MARGIN},
        "dimensions": {"lengthMetres": ROOM_LENGTH, "depthMetres": ROOM_DEPTH,
                       "boardWidthMetres": BOARD},
        "room": {"x": origin_x, "y": origin_y,
                 "w": round(far_x - origin_x), "h": round(far_y - origin_y)},
        "furniture": [
            dict(item,
                 x=m_to_px(item["x"], item["y"])[0], y=m_to_px(item["x"], item["y"])[1],
                 w=round(item["w"] * PX_PER_METRE_X), h=round(item["h"] * PX_PER_METRE_Y))
            for item in FURNITURE
        ],
        "counts": {"walls": len(walls), "slots": len(slots), "assigned": filled},
        "walls": walls,
    }

    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, ensure_ascii=False)
        handle.write("\n")

    print("Wrote {} - {} walls, {} boards, {} with a poster on them".format(
        os.path.relpath(OUT, ROOT), len(walls), len(slots), filled))
    for spec in RUNS:
        if spec["kind"] == "run":
            print("  run of {} across the foyer at {:>5.2f} m, heading {}".format(
                spec["walls"], spec["x"], spec["toward"]))
        else:
            print("  {} flat on the {} wall at {}".format(
                len(spec["at"]), spec["wall"], ", ".join("%.2f m" % a for a in spec["at"])))
    for pid in unknown:
        print("  ! board assigned to an unknown poster id: {}".format(pid))


if __name__ == "__main__":
    main()
