# Adding a poster (including the last four)

Four posters are still on their way. Each one already has its abstract, authors
and keywords on the site — only the PDF is missing, and its page says "PDF on
its way" until it turns up.

Still awaited:

| Poster | Authors |
| --- | --- |
| 50 Billion Objects of the Danish Web: Visualizing Two Decades of Netarkivet | Klindt Myrvoll, Anders |
| ARE WE ON THE RIGHT TRACK? | Stokes, Paul; Flores, Jacques |
| KEEPING OPEN BOOKS USABLE— CHALLENGES AND OPPORTUNITIES | Stokes, Paul; Cole, Gareth |
| Repository-Native Documentation for Research Data Preservation with Well-known URIs | Kameda, Akihiro; Kitaoka, Tamako; Goto, Makoto |

## The quick way (in the browser, no software)

1. Go to the `posters/` folder on GitHub and choose **Add file → Upload files**.
   Drop the PDF in and commit it.
2. Edit `poster_metadata.csv` and put the PDF's exact filename in that poster's
   **`file_name`** column, replacing the word `placeholder`.

A GitHub Action (`.github/workflows/build-data.yml`) rebuilds
`data/posters.json`, renders the poster's thumbnail, and commits both within a
minute or two. The poster then appears on the site — in the gallery, in the
search index, on its own page and on the map.



**If you only do step 1**, the build still tries to pair the PDF with its row
by looking for the author surname and words from the title in the filename, so
a file named like the existing ones will usually be picked up anyway. Anything
it cannot place is named in the Action's log and stays marked "PDF on its way".

**If a filename refuses to match** — an accented character can arrive mangled
when the CSV is exported — add one line to `tools/poster_files.csv`, which
overrides everything else:

```csv
50-billion-objects-of-the-danish-web-visualizing,Myrvoll_50-Billion-Objects.pdf
```

The left-hand column is the poster's id; `build_data.py` prints it in its log.

## The local way

```bash
cp ~/Downloads/the-new-poster.pdf posters/
# ...then put that filename in the row's file_name column
python3 tools/build_data.py        # rebuilds data/posters.json
python3 tools/build_thumbs.py      # renders its gallery thumbnail
python3 tools/check_verbatim.py    # confirms no metadata text was altered
git add posters data assets/thumbs && git commit -m "Add the Netarkivet poster" && git push
```

`build_data.py` needs nothing but a standard Python 3 — no pip, no node. It
prints what it matched, what it could not match, and what is still awaited.

`build_thumbs.py` needs two libraries (`pip install pypdfium2 Pillow`) and only
renders what is missing or out of date, so it takes a second. If they are not
installed it says so and does nothing, and the site still works — the browser
falls back to rendering previews itself, just more slowly.

## Adding a poster that is not in the CSV at all

Add a row to `poster_metadata.csv` with the same columns
(`title`, `abstract_plain`, `keywords`, `topics`, `authors`, `organisations`,
`poster_location`, `file_name`, `landscape/ portrait`, `online/ in-person`),
then run `python3 tools/build_data.py`. Keep the topics in the same
comma-and-newline shape as the existing rows — that is what drives the theme
colours, the filters and the trails.

If the hall has room for it, give it a board:

```bash
python3 tools/build_layout.py --keep   # keeps the boards already assigned
```

## Marking a poster as presented online

One column, `online/ in-person` in `poster_metadata.csv`. Put `online` in it
and, on the next rebuild, that poster:

* **comes off the map** — an online author is not in the room, so the board
  they had is freed and shown as an empty board, and the map page gains a note
  saying how many posters are online and linking to them;
* **stays everywhere else** — the gallery, the search index, the trails and its
  own page. Every poster is on this website whether or not it is in the hall;
* gets a 💻 **Online** chip on its card, a line on its page explaining there is
  no board for it, and a 💻 note against it in any trail it belongs to;
* becomes findable through a **💻 Presented online** filter on the All posters
  page. That filter stays hidden until at least one poster is marked online, so
  it appears by itself once you start filling the column in.

Anything that says online, virtual or remote counts as online; anything saying
in-person, in person or on-site counts as being in the room. Capitals and extra
spaces do not matter. A blank cell means "not decided yet" and shows nothing,
so you can fill the column in a few rows at a time without the site looking
half-finished.

Nothing else needs changing — no code, no layout file. Edit the column and the
rebuild Action does the rest, including taking the poster off the map. Change
your mind and clear the cell, and it gets a board again on the next rebuild.

## Why the thumbnails are committed

`assets/thumbs/` holds a ~50KB WebP of page 1 of each poster, rendered by
`tools/build_thumbs.py`. The gallery shows those instead of downloading the
PDFs: the page went from pulling 55MB and taking a few seconds to show anything,
to 2MB and showing everything at once. The PDFs are only fetched when somebody
opens a poster.

They are committed rather than generated on the fly because the site is plain
static files — there is no server to render them on demand.

## The metadata is never edited

Titles, abstracts, author names, institutions and keywords are copied to the
website character for character. Nothing is re-spaced, re-punctuated, reordered
or "tidied" — `tools/check_verbatim.py` fails the build if anything drifts, and
the same check runs in CI on every push. If a typo needs fixing, fix it in
`poster_metadata.csv` and the site follows.

## Setting the real hall layout

`data/layout.json` is currently a **provisional** arrangement: the right number
of walls in the right clusters (25 walls, 42 boards, from
`map/Poster layout.pptx`), but not the real positions, and the posters are assigned
to boards automatically so that each theme stays together.

When the hall is set up for real, edit `data/layout.json` directly. Every board
has plain numbers you can nudge:

```json
{ "id": "A1a", "number": 1, "x": 105, "y": 180, "facing": 270,
  "poster": "dignified-deletion-toward-a-philosophy-of-letting-go",
  "reservedFor": null }
```

* `x` / `y` — position on the map, in a 1000 × 700 grid where (0,0) is the
  top-left corner of the room.
* `poster` — the id of the poster on that board, or `null` for an empty one.
* `reservedFor` — text shown instead of a poster (three boards are held for
  Reception, the nestor survey and "Trends in digital preservation").

Then set `"provisional": false` at the top of the file and the orange "this
layout is provisional" banner disappears from the map page.

Do **not** re-run `tools/build_layout.py` after that — it regenerates the
positions from scratch. (`--keep` preserves the poster assignments but still
resets the coordinates.)

## Changing the poll link

`data/config.json`, one line:

```json
"url": "https://tally.so/r/Y5g4bz"
```

Every Vote button on every page reads that value. Blank it out and the buttons
say voting opens later instead of linking anywhere.
