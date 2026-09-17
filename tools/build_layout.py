#!/usr/bin/env python3
"""
Generate data/layout.json - the poster hall floor plan used by map.html.

The shape comes from "map/Poster layout.pptx" (Option 4, "Minimal amount of
walls"), which specifies:

    9 walls = 18 posters      6 walls =  6 posters
    3 walls =  6 posters      5 walls = 10 posters
    2 walls =  2 posters      ------------------------
                              25 walls, 42 posters

plus three reserved spots for Reception, the nestor survey and "Trends in
digital preservation / future".

WHERE THE WALLS ACTUALLY GO IS NOT DECIDED YET, so the coordinates below are a
tidy, schematic arrangement with the right number of walls and posters in
roughly the right part of the room. The website flags the map as provisional.

    python3 tools/build_layout.py            # regenerate from scratch
    python3 tools/build_layout.py --keep     # keep existing poster assignments

Once the real positions are known, edit data/layout.json directly (each slot
has plain x / y / angle numbers) and stop running this script - or edit the
CLUSTERS table below and re-run it. See ADDING-POSTERS.md.
"""

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTERS = os.path.join(ROOT, "data", "posters.json")
OUT = os.path.join(ROOT, "data", "layout.json")

VIEW_W, VIEW_H = 1000, 700

# One entry per cluster of walls: how many walls, how many posters hang on each
# of them, which way the wall runs, how long it is, the centre point of every
# wall, and where to park the cluster's label so it collides with nothing.
CLUSTERS = [
    {
        "id": "A",
        "name": "Havnegade Block",
        "hint": "Nine double-sided walls - the busiest corner of the hall.",
        "perWall": 2,
        "angle": 90,
        "length": 104,
        "centres": [(x, y) for y in (180, 320, 460) for x in (120, 240, 360)],
        "label": (240, 105),
    },
    {
        "id": "B",
        "name": "Nyhavn Row",
        "hint": "Six single-sided walls along the side of the room.",
        "perWall": 1,
        "angle": 0,
        "length": 96,
        "centres": [(x, y) for y in (210, 330) for x in (700, 820, 940)],
        "label": (820, 150),
    },
    {
        "id": "C",
        "name": "Kastellet Corner",
        "hint": "Three double-sided walls tucked into the far corner.",
        "perWall": 2,
        "angle": 90,
        "length": 96,
        "centres": [(770, 580), (850, 580), (930, 580)],
        "label": (835, 496),
    },
    {
        "id": "D",
        "name": "Strøget",
        "hint": "Five double-sided walls forming the main thoroughfare.",
        "perWall": 2,
        "angle": 90,
        "length": 96,
        "centres": [(430, 580), (488, 580), (546, 580), (604, 580), (662, 580)],
        "label": (546, 496),
    },
    {
        "id": "E",
        "name": "Kaffe Korner",
        "hint": "Two walls by the coffee - linger here.",
        "perWall": 1,
        "angle": 0,
        "length": 96,
        "centres": [(120, 640), (250, 640)],
        "label": (185, 595),
    },
]

# Which slots are held back for the three extra posters named in the pptx.
RESERVED = {
    "B4": "Reception",
    "B5": "nestor survey",
    "B6": "Trends in digital preservation: the future",
}

# Decorative furniture so the map reads as a room rather than a scatter plot.
FURNITURE = [
    {"kind": "entrance", "label": "Entrance", "x": 24, "y": 300, "w": 28, "h": 120},
    {"kind": "coffee", "label": "Coffee", "x": 45, "y": 520, "w": 112, "h": 50},
    {"kind": "reception", "label": "Reception", "x": 700, "y": 34, "w": 260, "h": 52},
    {"kind": "seating", "label": "Seating", "x": 455, "y": 190, "w": 180, "h": 120},
]


def slot_points(centre, angle, length, per_wall):
    """Where the poster(s) hang on a wall, and which way they face.

    A single-sided wall has its poster on the front face. A double-sided wall
    is numbered back face first, so that board numbers read left to right (or
    top to bottom) across a row of walls on the map instead of zig-zagging.
    """
    cx, cy = centre
    radians = math.radians(angle)
    # Unit vector perpendicular to the wall - posters hang off the faces.
    nx, ny = math.sin(radians), -math.cos(radians)
    offset = 15
    front = (round(cx + nx * offset, 1), round(cy + ny * offset, 1), angle)
    back = (round(cx - nx * offset, 1), round(cy - ny * offset, 1), (angle + 180) % 360)
    return [front] if per_wall == 1 else [back, front]


def build(previous_assignments):
    clusters, number = [], 0
    for spec in CLUSTERS:
        walls = []
        for index, centre in enumerate(spec["centres"], start=1):
            wall_id = "{}{}".format(spec["id"], index)
            slots = []
            for face, (x, y, angle) in enumerate(
                slot_points(centre, spec["angle"], spec["length"], spec["perWall"])
            ):
                number += 1
                slot_id = wall_id + ("ab"[face] if spec["perWall"] > 1 else "")
                slots.append({
                    "id": slot_id,
                    "number": number,
                    "x": x,
                    "y": y,
                    "facing": angle,
                    "poster": previous_assignments.get(slot_id),
                    "reservedFor": RESERVED.get(wall_id) if spec["perWall"] == 1 else None,
                })
            walls.append({
                "id": wall_id,
                "x": centre[0],
                "y": centre[1],
                "angle": spec["angle"],
                "length": spec["length"],
                "slots": slots,
            })
        clusters.append({
            "id": spec["id"],
            "name": spec["name"],
            "hint": spec["hint"],
            "labelX": spec["label"][0],
            "labelY": spec["label"][1],
            "walls": walls,
        })
    return clusters


def assign(clusters, posters):
    """Fill empty slots, keeping each theme together so the trails walk well."""
    open_slots = [
        slot
        for cluster in clusters
        for wall in cluster["walls"]
        for slot in wall["slots"]
        if not slot["reservedFor"] and not slot["poster"]
    ]
    taken = {
        slot["poster"]
        for cluster in clusters
        for wall in cluster["walls"]
        for slot in wall["slots"]
        if slot["poster"]
    }
    queue = [p for p in posters if p["id"] not in taken]
    queue.sort(key=lambda p: ((p["themes"] or ["zzz"])[0], p["title"].lower()))
    for slot, poster in zip(open_slots, queue):
        slot["poster"] = poster["id"]
    return len(queue) - len(open_slots)


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

    posters = json.load(open(POSTERS, encoding="utf-8"))["posters"]
    clusters = build(previous)
    unplaced = assign(clusters, posters)

    slot_count = sum(len(w["slots"]) for c in clusters for w in c["walls"])
    wall_count = sum(len(c["walls"]) for c in clusters)

    payload = {
        "provisional": True,
        "note": (
            "Wall counts come from map/Poster layout.pptx (Option 4). The exact "
            "positions and which poster goes where are NOT confirmed yet - "
            "edit data/layout.json to set the real ones."
        ),
        "source": "map/Poster layout.pptx",
        "viewBox": [0, 0, VIEW_W, VIEW_H],
        "dimensions": {"widthMetres": 13.5, "depthMetres": 6},
        "floorPlanImage": "assets/img/floorplan.png",
        "counts": {"walls": wall_count, "slots": slot_count, "reserved": len(RESERVED)},
        "furniture": FURNITURE,
        "clusters": clusters,
    }

    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, ensure_ascii=False)
        handle.write("\n")

    print("Wrote {} - {} walls, {} slots, {} reserved".format(
        os.path.relpath(OUT, ROOT), wall_count, slot_count, len(RESERVED)))
    if unplaced > 0:
        print("  ! {} poster(s) could not be placed - not enough slots".format(unplaced))
    elif unplaced < 0:
        print("  {} slot(s) left empty".format(-unplaced))


if __name__ == "__main__":
    main()
