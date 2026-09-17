#!/usr/bin/env python3
"""
Generate data/layout.json - the poster hall floor plan used by map.html.

Everything here is measured off the venue drawing in map/Poster layout.pptx
(Option 4, "Minimal amount of walls") rather than invented:

  * The dimension annotation on the drawing reads 13.5 m across and 6 m deep,
    and those rules are 323 px and 143 px long, which puts the plan at a
    consistent 23.9 px per metre.
  * The four wall marks drawn on it are each 29.9 px long - 1.25 m - which is
    the width of one poster board.
  * Two of those marks stand at right angles to the long wall (a fin, with a
    poster on each face) and two lie flat against it (one poster).
  * The wall counts and the split into five groups are the drawing's own:
        9 walls = 18 posters      6 walls =  6 posters
        3 walls =  6 posters      5 walls = 10 posters
        2 walls =  2 posters      -----------------------
                                  25 walls, 42 posters
  * The five red labels sit at 1.0 m, 1.6 m, 12.0 m, 18.0 m and 22.8 m along
    the foyer, which is what positions each group below.

The three extra posters the drawing mentions (Reception, the nestor survey and
"Trends in digital preservation") are not on the walls and are deliberately not
on this map.

WHAT IS STILL NOT DECIDED is the exact spacing within each group, and which
poster hangs on which board - so every board is generated empty, ready to be
filled in by hand.

    python3 tools/build_layout.py            # regenerate the boards, empty
    python3 tools/build_layout.py --keep     # keep any boards already filled in

Assign posters by editing data/layout.json: set a board's "poster" to a poster
id from data/posters.json. See ADDING-POSTERS.md.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTERS = os.path.join(ROOT, "data", "posters.json")
OUT = os.path.join(ROOT, "data", "layout.json")

# --- the room, in metres, measured off the drawing -------------------------
#
#     0                                                                 26.5
#   0 +--------------------------------------------------------------------+
#     |  A: 9 fins off the top wall          B: 6 boards flat on the top    |
#     |                                                                     |
#     |  [-- the 13.5 x 6 m open area --]                                   |
# 6.5 |  E: 2 flat      D: 5 fins off the bottom      C: 3 fins             |
#     +--------------------------------------------------------------------+

ROOM_LENGTH = 26.5
ROOM_DEPTH = 6.5
WALL = 1.25            # one board, from the marks on the drawing
WALL_THICKNESS = 0.1
MEASURED_AREA = {"x": 0.0, "y": 0.38, "w": 13.5, "h": 6.0}  # the annotated box

PX_PER_METRE = 60
# Room to breathe outside the foyer itself, in metres: the entrance sits to the
# left of it, the cafe above it, and the group captions and scale bar below.
MARGIN = {"left": 1.7, "top": 2.9, "right": 0.7, "bottom": 3.2}

# Where the scanned plan sits, so the "real floor plan" overlay lines up with
# the boards: its dimension rule is 323 px for 13.5 m, and the corner of the
# foyer (metre 0, 0) is at (50, 175) in that image.
PLAN_IMAGE = "assets/img/floorplan.png"
PLAN_SIZE = (898, 364)
PLAN_PX_PER_METRE = 323 / 13.5
PLAN_ORIGIN = (50, 175)

# kind:    "fin"  - stands out from the wall, a poster on each face
#          "flat" - lies against the wall, one poster
# anchor:  which wall it is attached to
# at:      the centre of each wall, in metres along the foyer
CLUSTERS = [
    {
        "id": "A",
        "name": "Havnegade Block",
        "hint": "Nine double-sided walls along the top of the open area.",
        "kind": "fin",
        "anchor": "top",
        "at": [1.0, 2.5, 4.0, 5.5, 7.0, 8.5, 10.0, 11.5, 13.0],
    },
    {
        "id": "E",
        "name": "Kaffe Korner",
        "hint": "Two boards flat against the bottom wall, by the coffee.",
        "kind": "flat",
        "anchor": "bottom",
        "at": [2.8, 5.15],
    },
    {
        "id": "D",
        "name": "Str\u00f8get",
        "hint": "Five double-sided walls forming the main thoroughfare.",
        "kind": "fin",
        "anchor": "bottom",
        "at": [11.5, 13.0, 14.5, 16.0, 17.5],
    },
    {
        "id": "B",
        "name": "Nyhavn Row",
        "hint": "Six boards flat against the top wall.",
        "kind": "flat",
        "anchor": "top",
        "at": [17.1, 18.6, 20.1, 21.6, 23.1, 24.6],
    },
    {
        "id": "C",
        "name": "Kastellet Corner",
        "hint": "Three double-sided walls in the far corner.",
        "kind": "fin",
        "anchor": "bottom",
        "at": [20.6, 22.1, 23.6],
    },
]

# Where the group's caption sits, in metres.
LABELS = {"A": (7.0, -1.15), "E": (4.0, 7.5), "D": (14.5, 7.5),
          "B": (20.85, -1.15), "C": (22.1, 7.5)}

# Fixed features, in metres, taken from the drawing.
# Positions read off the plan: the entrance at the left end, "Kaffe" in the bay
# above the foyer about 15 m along, and the staircase at the far right.
FURNITURE = [
    {"kind": "entrance", "label": "Entrance", "x": -1.25, "y": 2.0, "w": 0.85, "h": 2.5},
    {"kind": "coffee", "label": "Coffee", "x": 14.8, "y": -2.3, "w": 2.7, "h": 1.7},
    {"kind": "stairs", "label": "Stairs", "x": 24.9, "y": 4.4, "w": 1.6, "h": 2.1},
]


def m_to_px(x, y):
    """Metres from the top-left corner of the foyer -> SVG user units."""
    return (round((MARGIN["left"] + x) * PX_PER_METRE, 1),
            round((MARGIN["top"] + y) * PX_PER_METRE, 1))


def build(previous_assignments):
    """One entry per wall, with a board on one or both faces."""
    clusters, number = [], 0
    for spec in CLUSTERS:
        double = spec["kind"] == "fin"
        walls = []
        for index, along in enumerate(spec["at"], start=1):
            wall_id = "{}{}".format(spec["id"], index)

            if double:
                # A fin: runs into the room from the wall it is attached to.
                if spec["anchor"] == "top":
                    x0, y0, x1, y1 = along, 0.0, along, WALL
                else:
                    x0, y0, x1, y1 = along, ROOM_DEPTH, along, ROOM_DEPTH - WALL
                faces = [("west", -1, 0), ("east", 1, 0)]
            else:
                # Flat against the wall, facing into the room.
                if spec["anchor"] == "top":
                    x0, y0, x1, y1 = along - WALL / 2, 0.0, along + WALL / 2, 0.0
                    faces = [("south", 0, 1)]
                else:
                    x0, y0, x1, y1 = along - WALL / 2, ROOM_DEPTH, along + WALL / 2, ROOM_DEPTH
                    faces = [("north", 0, -1)]

            mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
            slots = []
            for face_index, (facing, dx, dy) in enumerate(faces):
                number += 1
                slot_id = wall_id + ("ab"[face_index] if double else "")
                px, py = m_to_px(mid_x + dx * 0.32, mid_y + dy * 0.42)
                slots.append({
                    "id": slot_id,
                    "number": number,
                    "x": px,
                    "y": py,
                    "facing": facing,
                    "poster": previous_assignments.get(slot_id),
                })

            ax, ay = m_to_px(x0, y0)
            bx, by = m_to_px(x1, y1)
            walls.append({
                "id": wall_id,
                "x1": ax, "y1": ay, "x2": bx, "y2": by,
                "thickness": round(WALL_THICKNESS * PX_PER_METRE, 1),
                "kind": spec["kind"],
                "slots": slots,
            })

        label_x, label_y = m_to_px(*LABELS[spec["id"]])
        clusters.append({
            "id": spec["id"],
            "name": spec["name"],
            "hint": spec["hint"],
            "labelX": label_x,
            "labelY": label_y,
            "walls": walls,
        })
    return clusters


def main():
    keep = "--keep" in sys.argv
    previous = {}
    if keep and os.path.exists(OUT):
        existing = json.load(open(OUT, encoding="utf-8"))
        for cluster in existing.get("clusters", []):
            for wall in cluster.get("walls", []):
                for slot in wall.get("slots", []):
                    if slot.get("poster"):
                        previous[slot["id"]] = slot["poster"]

    clusters = build(previous)
    slot_count = sum(len(w["slots"]) for c in clusters for w in c["walls"])
    wall_count = sum(len(c["walls"]) for c in clusters)
    filled = sum(1 for c in clusters for w in c["walls"] for s in w["slots"] if s["poster"])

    known_ids = set()
    if os.path.exists(POSTERS):
        known_ids = {p["id"] for p in json.load(open(POSTERS, encoding="utf-8"))["posters"]}
    unknown = [
        s["poster"] for c in clusters for w in c["walls"] for s in w["slots"]
        if s["poster"] and s["poster"] not in known_ids
    ]

    origin_x, origin_y = m_to_px(0, 0)
    far_x, far_y = m_to_px(ROOM_LENGTH, ROOM_DEPTH)
    area_x, area_y = m_to_px(MEASURED_AREA["x"], MEASURED_AREA["y"])
    view_w = round((MARGIN["left"] + ROOM_LENGTH + MARGIN["right"]) * PX_PER_METRE)
    view_h = round((MARGIN["top"] + ROOM_DEPTH + MARGIN["bottom"]) * PX_PER_METRE)

    # Place the scanned plan so its metre grid matches ours.
    plan_scale = PX_PER_METRE / PLAN_PX_PER_METRE
    plan_x, plan_y = m_to_px(-PLAN_ORIGIN[0] / PLAN_PX_PER_METRE,
                             -PLAN_ORIGIN[1] / PLAN_PX_PER_METRE)

    payload = {
        "provisional": True,
        "note": (
            "Wall counts, sizes and groups come from map/Poster layout.pptx and "
            "the plan is drawn to its scale, but the spacing within each group "
            "is an even guess and no poster has been put on a board yet. Set a "
            "board's \"poster\" here to fill it in."
        ),
        "source": "map/Poster layout.pptx",
        "viewBox": [0, 0, view_w, view_h],
        "scale": {"pxPerMetre": PX_PER_METRE, "margin": MARGIN},
        "dimensions": {"lengthMetres": ROOM_LENGTH, "depthMetres": ROOM_DEPTH,
                       "boardWidthMetres": WALL},
        "room": {"x": origin_x, "y": origin_y,
                 "w": round(far_x - origin_x), "h": round(far_y - origin_y)},
        "scaleBarY": m_to_px(0, ROOM_DEPTH + 2.2)[1],
        "measuredArea": {
            "x": area_x, "y": area_y,
            "w": round(MEASURED_AREA["w"] * PX_PER_METRE),
            "h": round(MEASURED_AREA["h"] * PX_PER_METRE),
            "label": "13.5 m × 6 m",
        },
        "furniture": [
            dict(item,
                 x=m_to_px(item["x"], item["y"])[0],
                 y=m_to_px(item["x"], item["y"])[1],
                 w=round(item["w"] * PX_PER_METRE),
                 h=round(item["h"] * PX_PER_METRE))
            for item in FURNITURE
        ],
        "floorPlan": {
            "image": PLAN_IMAGE,
            "x": round(plan_x, 1), "y": round(plan_y, 1),
            "w": round(PLAN_SIZE[0] * plan_scale, 1),
            "h": round(PLAN_SIZE[1] * plan_scale, 1),
        },
        "counts": {"walls": wall_count, "slots": slot_count, "assigned": filled},
        "clusters": clusters,
    }

    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, ensure_ascii=False)
        handle.write("\n")

    print("Wrote {} - {} walls, {} boards, {} with a poster on them".format(
        os.path.relpath(OUT, ROOT), wall_count, slot_count, filled))
    print("  {:.1f} m x {:.1f} m foyer, {:.2f} m boards, drawn at {} px/m".format(
        ROOM_LENGTH, ROOM_DEPTH, WALL, PX_PER_METRE))
    for pid in unknown:
        print("  ! board assigned to an unknown poster id: {}".format(pid))
    if not filled:
        print("  Boards are numbered 1-{} and empty. Assign posters by editing {}.".format(
            slot_count, os.path.relpath(OUT, ROOT)))


if __name__ == "__main__":
    main()
