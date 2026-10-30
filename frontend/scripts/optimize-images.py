#!/usr/bin/env python3
"""Convert the necklace product PNGs to WebP and recompress large JPEGs.

Why: the 17 product PNGs were 1122x1402 and ~1.4-1.9 MB each (~28 MB total),
which made the home page download tens of MB before this optimization. WebP at
quality 82 keeps the jewelry renders visually identical for web display while
fitting the <=300 KB per-image budget.

Usage (repo frontend/ directory, needs Pillow):
    python3 scripts/optimize-images.py          # write optimized files
    python3 scripts/optimize-images.py --check  # only report sizes
"""
import glob
import os
import sys

from PIL import Image

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "public", "images")
WEBP_QUALITY = 82
JPEG_QUALITY = 85
BUDGET_KB = 300


def convert_necklace_pngs(check: bool) -> None:
    for src in sorted(glob.glob(os.path.join(IMAGES_DIR, "*-necklace.png"))):
        dst = src[:-4] + ".webp"
        if not check:
            with Image.open(src) as im:
                im.save(dst, "WEBP", quality=WEBP_QUALITY, method=6)
        before = os.path.getsize(src) / 1024
        after = os.path.getsize(dst) / 1024 if os.path.exists(dst) else 0
        flag = "OK " if after <= BUDGET_KB else "OVER"
        print(f"{flag} {os.path.basename(dst):32s} {before:7.0f} KB -> {after:6.0f} KB")


def recompress_jpeg(name: str, check: bool) -> None:
    path = os.path.join(IMAGES_DIR, name)
    before = os.path.getsize(path) / 1024
    if not check:
        with Image.open(path) as im:
            im.convert("RGB").save(path, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    after = os.path.getsize(path) / 1024
    print(f"    {name:32s} {before:7.0f} KB -> {after:6.0f} KB")


def main() -> None:
    check = "--check" in sys.argv
    convert_necklace_pngs(check)
    # product.jpg is the database-referenced fallback image; keep the path,
    # only slim the file. The small hero/story JPEGs stay untouched.
    recompress_jpeg("product.jpg", check)


if __name__ == "__main__":
    main()
