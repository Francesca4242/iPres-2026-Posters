# iPRES 2026 virtual poster hall

A website to display the iPRES 2026 posters: every abstract, every author, a
searchable index, a clickable map of the room, and themed trails through it.

**Adding the last four posters, changing the poll link, or setting the real
hall layout? See [ADDING-POSTERS.md](ADDING-POSTERS.md).**

## What's here

| Page | What it does |
| --- | --- |
| `index.html` | Landing page: counts, the eight themes, trail teasers, a shuffle button |
| `posters.html` | Every poster, searchable across titles, abstracts, authors, institutions and keywords; filter by theme; sort by walk order, title, author or theme |
| `poster.html?id=…` | One poster: the PDF readable in the page (paged, zoomable, downloadable), the full abstract, authors with their institutions, keywords, its board number, and the trails it is on |
| `map.html` | The poster hall as a bright, blocky, clickable board. Every board is colour-coded by theme; pick a trail and the route lights up; toggle the real venue floor plan underneath |
| `trails.html` | Twelve themed walks through the hall, plus a quiz that picks one for you |

Running through all of them: a **Vote** button wired to the best-poster poll, a
light/dark toggle, and a **poster passport** that remembers which posters you
have ticked off (in your browser only — nothing is sent anywhere).

## Running it

It is a plain static site: no build step, no framework, no npm. Any web server
will do.

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

For GitHub Pages: **Settings → Pages → Deploy from a branch**, pick the branch
and the `/ (root)` folder. The PDFs are served straight out of `posters/`.

Opening `index.html` as a `file://` URL will *not* work — browsers block the
`fetch()` calls that load the data. Use a server.

## How the data flows

```
poster_metadata.csv  ─┐
posters/*.pdf        ─┼─►  tools/build_data.py    ─►  data/posters.json
tools/poster_files.csv┘                                      │
                              tools/build_thumbs.py  ─►  assets/thumbs/*.webp
                                                             │
                          tools/build_layout.py   ─►  data/layout.json
```

* **`data/posters.json`** — one entry per poster: title, abstract, authors,
  institutions, keywords, topics, themes, orientation, whether it is presented
  online, and the path to its PDF (or `null` if it has not arrived). Regenerate
  with `python3 tools/build_data.py`.
* **`data/layout.json`** — the hall: 25 walls in five clusters, 42 boards, and
  which poster hangs on each. Currently **provisional**. Posters marked as
  presented online in the CSV get no board here, but stay everywhere else on
  the site.
* **`data/config.json`** — the poll URL and the conference details.
* **`assets/thumbs/*.webp`** — page 1 of each poster, ~50KB each, so the gallery
  does not have to download 55MB of PDFs to show its cards. Regenerate with
  `python3 tools/build_thumbs.py` (needs `pip install pypdfium2 Pillow`; without
  them the browser falls back to rendering previews itself).

A GitHub Action rebuilds `data/posters.json` and the thumbnails whenever a PDF
is added, so uploading a poster through the GitHub web interface is enough.

## The metadata is shown exactly as submitted

Titles, abstracts, author names, institutions and keywords are copied to the
page character for character. Nothing is re-spaced, re-punctuated, reordered or
corrected. `tools/check_verbatim.py` compares every field in
`data/posters.json` against the CSV and fails if anything has drifted; it runs
in CI on every push.

```bash
python3 tools/check_verbatim.py
```

## Themes

The eight themes are the iPRES topic groups the posters were submitted under.
They drive the colour coding everywhere — filters, cards, map boards, trails.

🗄️ Infrastructure & Storage · 🤝 Community & Collaboration ·
🧬 Formats & Integrity · 📊 Management & Costs · 🏷️ Metadata & Description ·
🔍 Access & Discovery · 📥 Appraisal & Ingest · ⚖️ Policy & Ethics

## Trails

Trails are declarative — a theme, a keyword or a phrase to match — and are
defined at the top of `assets/js/trails.js`. Their stops are ordered by board
number, so following one really is a walk round the room. Add, retune or delete
one by editing that table; nothing else needs to change.

## Layout of the repository

```
index.html posters.html poster.html map.html trails.html
assets/css/site.css          one stylesheet for every page
assets/js/site.js            shared: data loading, chrome, passport, PDF rendering
assets/thumbs/               pre-rendered gallery thumbnails, one per poster
assets/js/trails.js          the trail definitions and the quiz
assets/img/floorplan.png     the venue plan from map/Poster layout.pptx
data/                        posters.json, layout.json, config.json
posters/                     the poster PDFs
iPRES2026_Logos/             conference logos
tools/                       the four Python scripts, plus the filename overrides
poster_metadata.csv          the source of truth for all poster metadata; its
                             file_name column says which PDF belongs to which row
map/Poster layout.pptx       the venue's wall plan, where the map numbers come from
```

Posters remain the copyright of their authors.
