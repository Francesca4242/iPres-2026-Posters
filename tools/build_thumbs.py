#!/usr/bin/env python3
"""
Pre-render a thumbnail of page 1 of every poster PDF.

The gallery used to build its previews in the browser, which meant downloading
all ~56MB of PDFs to show one page of cards. These thumbnails are a few tens of
kilobytes each, so the gallery loads immediately and the PDFs are only fetched
when somebody actually opens a poster.

    pip install pypdfium2 Pillow
    python3 tools/build_thumbs.py            # only renders what is missing or stale
    python3 tools/build_thumbs.py --force    # re-renders everything

Writes assets/thumbs/<poster-id>.webp and records it in data/posters.json. Run
tools/build_data.py first: this reads the poster list from it, and writes the
thumbnail paths back into it. WebP only - every browser has supported it since
2020, and a JPEG fallback would double the size of the repository for nobody.

If the libraries are not installed the script says so and exits 0 without
touching anything, so a build without them still produces a working site - the
browser just falls back to rendering previews itself.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTERS = os.path.join(ROOT, "data", "posters.json")
OUT_DIR = os.path.join(ROOT, "assets", "thumbs")

#: Wide enough for a 2x retina poster card, small enough to stay tens of KB.
WIDTH = 520
WEBP_QUALITY = 80


def load_libraries():
    try:
        import pypdfium2
        from PIL import Image
        return pypdfium2, Image
    except ImportError as err:
        print("Thumbnails skipped: {}.".format(err))
        print("  Install them with:  pip install pypdfium2 Pillow")
        print("  The site still works - the browser renders previews itself.")
        return None, None


def is_stale(pdf_path, thumb_path):
    """Re-render when the thumbnail is missing or older than its PDF."""
    if not os.path.exists(thumb_path):
        return True
    return os.path.getmtime(pdf_path) > os.path.getmtime(thumb_path)


def render(pdfium, Image, pdf_path, width):
    pdf = pdfium.PdfDocument(pdf_path)
    try:
        page = pdf[0]
        page_width = page.get_size()[0] or width
        image = page.render(scale=width / page_width).to_pil()
        # Posters are occasionally saved with a transparent background, which
        # turns into black when flattened into a JPEG. Put them on white.
        if image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGBA")
            backdrop = Image.new("RGB", image.size, "white")
            backdrop.paste(image, mask=image.split()[-1])
            image = backdrop
        return image.convert("RGB")
    finally:
        pdf.close()


def main():
    force = "--force" in sys.argv
    pdfium, Image = load_libraries()
    if pdfium is None:
        return

    data = json.load(open(POSTERS, encoding="utf-8"))
    os.makedirs(OUT_DIR, exist_ok=True)

    built, skipped, failed, total_bytes = 0, 0, 0, 0
    wanted = set()

    for poster in data["posters"]:
        if not poster.get("file"):
            poster["thumb"] = None
            poster["thumbWidth"] = None
            poster["thumbHeight"] = None
            continue

        pdf_path = os.path.join(ROOT, poster["file"])
        webp_name = "{}.webp".format(poster["id"])
        webp_path = os.path.join(OUT_DIR, webp_name)
        wanted.add(webp_name)

        if force or is_stale(pdf_path, webp_path):
            try:
                image = render(pdfium, Image, pdf_path, WIDTH)
            except Exception as err:  # a damaged or encrypted PDF
                print("  ! could not render {}: {}".format(poster["file"], err))
                poster["thumb"] = None
                poster["thumbWidth"] = None
                poster["thumbHeight"] = None
                failed += 1
                continue
            image.save(webp_path, "WEBP", quality=WEBP_QUALITY, method=6)
            built += 1
        else:
            image = Image.open(webp_path)
            skipped += 1

        poster["thumb"] = "assets/thumbs/" + webp_name
        poster["thumbWidth"], poster["thumbHeight"] = image.size
        total_bytes += os.path.getsize(webp_path)

    # A poster that was renamed or removed leaves its thumbnail behind.
    for name in sorted(os.listdir(OUT_DIR)):
        if name.endswith(".webp") and name not in wanted:
            os.remove(os.path.join(OUT_DIR, name))
            print("  removed stale thumbnail {}".format(name))

    with open(POSTERS, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=1, ensure_ascii=False)
        handle.write("\n")

    print("Thumbnails: {} rendered, {} already up to date, {} failed - {} KB of WebP".format(
        built, skipped, failed, total_bytes // 1024))


if __name__ == "__main__":
    main()
