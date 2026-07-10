#!/usr/bin/env python3
"""Build the Neon Nocturne edition from the approved calibration sheet.

The twelve approved founder portraits remain pixel-for-pixel intact. Collection
variation is added only in registered negative-space-safe zones around them, so
the core anatomy, expression, clothing and line quality cannot drift.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "reference" / "neon-nocturne-calibration.png"
INK = (2, 1, 2)
LIME = "#d0f708"
NATIVE = 128
SCALE = 8

HOUSES = [
    {"name": "Velvet Court", "accent": "#ff405b", "motto": "Old blood, new rules."},
    {"name": "Neon Vein", "accent": "#35e7ff", "motto": "Stay bright after dark."},
    {"name": "Cold Blood", "accent": "#9bdcff", "motto": "Calm is a superpower."},
    {"name": "Asphalt Fangs", "accent": "#ff7a32", "motto": "The city is ours at night."},
    {"name": "Black Signal", "accent": "#a576ff", "motto": "Broadcast from the void."},
    {"name": "Wild Bite", "accent": "#d8ff4f", "motto": "Instinct over etiquette."},
]

FOUNDER_TRAITS = [
    ("Raven Wave", "Hollow Ovals", "Twin Fangs", "Skull Tux", "Skull Bow", "Clean Frame"),
    ("Pumpkin Crown", "Soft Glow", "Jagged Grin", "High Collar", "Soft Bow", "Clean Frame"),
    ("Midnight Slick", "Shadow Fade", "Twin Fangs", "High Collar", "Round Medallion", "Clean Frame"),
    ("Living Flame", "Long Lashes", "Crooked Fangs", "Striped Knit", "Black Choker", "Clean Frame"),
    ("Stitched Crop", "X Glow", "Twin Fangs", "Undertaker Shirt", "Double Buttons", "Brow Stitches"),
    ("Little Horns", "Angry Arches", "Crooked Fangs", "Winged Cape", "Round Medallion", "Bat Wings"),
    ("Mummy Wraps", "Soft Glow", "Tiny Fangs", "Wrapped Tunic", "No Neckpiece", "Clean Frame"),
    ("Coven Hat", "Hollow Ovals", "Twin Fangs", "Coven Coat", "Slim Scarf", "Pumpkin Lantern"),
    ("Spectral Wave", "Hollow Ovals", "Tiny Fangs", "Chain Crewneck", "Loose Chain", "Smoke Halo"),
    ("Raven Wave", "Hypno Spirals", "Twin Fangs", "Velvet Jacket", "Soft Bow", "Clean Frame"),
    ("Pom Beanie", "Hollow Ovals", "Twin Fangs", "Skeleton Hoodie", "No Neckpiece", "Clean Frame"),
    ("Webbed Wave", "Hollow Ovals", "Crooked Fangs", "High Collar", "Round Medallion", "Hanging Spider"),
]

MODIFIERS = [
    ("MD01", "Founder Clean"),
    ("MD02", "Left Bat Signal"),
    ("MD03", "Right Bat Signal"),
    ("MD04", "Static Shards"),
    ("MD05", "Night Wisps"),
    ("MD06", "Spider Drop"),
    ("MD07", "Comet Sparks"),
    ("MD08", "Orbit Dots"),
    ("MD09", "Falling Pixels"),
    ("MD10", "Twin Moths"),
]

CATEGORY_CODES = {
    "Head": "HD", "Eyes": "EY", "Mouth": "MT", "Outfit": "OF",
    "Neck": "NK", "Extra": "EX",
}


def split_cells(sheet: Image.Image) -> list[Image.Image]:
    # The approved sheet uses optical spacing rather than mathematically equal
    # cells. These separators sit in the measured blank gutters.
    xs = [0, 356, 716, 1013, sheet.width]
    ys = [0, 399, 750, sheet.height]
    cells = []
    for row in range(3):
        for col in range(4):
            cells.append(sheet.crop((xs[col], ys[row], xs[col + 1], ys[row + 1])).convert("RGB"))
    return cells


def extract_ink(cell: Image.Image) -> Image.Image:
    """Turn the lime field into alpha while retaining black and soft glow."""
    alpha = Image.new("L", cell.size, 0)
    src = cell.load()
    out = alpha.load()
    for y in range(cell.height):
        for x in range(cell.width):
            r, g, b = src[x, y]
            luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if luminance <= 30:
                value = 255
            elif luminance >= 188:
                value = 0
            else:
                value = round((188 - luminance) / 158 * 255)
            # Lime and yellow-green are presentation color, never ink.
            if g > 170 and r > 120 and b < 130:
                value = min(value, 20)
            out[x, y] = value

    solid = alpha.point(lambda value: 255 if value > 28 else 0)
    bbox = solid.getbbox()
    if not bbox:
        raise ValueError("Founder cell contains no ink")
    alpha = alpha.crop((max(0, bbox[0] - 3), max(0, bbox[1] - 3), min(cell.width, bbox[2] + 3), min(cell.height, bbox[3] + 3)))
    ratio = min(900 / alpha.width, 940 / alpha.height)
    width = round(alpha.width * ratio)
    height = round(alpha.height * ratio)
    alpha = alpha.resize((width, height), Image.Resampling.LANCZOS)
    canvas_alpha = Image.new("L", (1024, 1024), 0)
    canvas_alpha.paste(alpha, ((1024 - width) // 2, 990 - height))
    image = Image.new("RGBA", (1024, 1024), (*INK, 0))
    image.putalpha(canvas_alpha)
    return image


def draw_modifier(code: str, variant: int) -> Image.Image:
    mask = Image.new("L", (NATIVE, NATIVE), 0)
    d = ImageDraw.Draw(mask)

    def bat(cx, cy, size=5):
        d.polygon([
            (cx, cy + 1), (cx - size, cy - 2), (cx - size + 1, cy + 3),
            (cx - 2, cy + 4), (cx, cy + 2), (cx + 2, cy + 4),
            (cx + size - 1, cy + 3), (cx + size, cy - 2), (cx, cy + 1),
        ], fill=255)

    def sparkle(cx, cy, size=3):
        d.polygon([(cx, cy - size), (cx + 1, cy - 1), (cx + size, cy),
                   (cx + 1, cy + 1), (cx, cy + size), (cx - 1, cy + 1),
                   (cx - size, cy), (cx - 1, cy - 1)], fill=255)

    if code == "MD02":
        for x, y, s in ((9, 24 + variant, 5), (18, 15, 4), (7, 41, 3)):
            bat(x, y, s)
    elif code == "MD03":
        for x, y, s in ((118, 22 + variant, 5), (108, 14, 4), (120, 41, 3)):
            bat(x, y, s)
    elif code == "MD04":
        for x, y, w, h in ((7, 35, 4, 2), (14, 27, 2, 5), (114, 32, 5, 2), (108, 43, 2, 4)):
            d.rectangle((x, y + variant % 3, x + w, y + h + variant % 3), fill=255)
    elif code == "MD05":
        d.line([(10, 105), (5, 98), (9, 90), (5, 82), (10, 74)], fill=255, width=2)
        d.line([(117, 107), (122, 99), (118, 91), (123, 82), (118, 74)], fill=255, width=2)
        d.arc((2, 62, 16, 80), 90, 260, fill=255, width=1)
        d.arc((112, 62, 126, 80), 270, 450, fill=255, width=1)
    elif code == "MD06":
        x = 10 if variant % 2 == 0 else 118
        d.line((x, 5, x, 47), fill=255, width=1)
        d.ellipse((x - 4, 46, x + 4, 53), fill=255)
        d.ellipse((x - 2, 43, x + 2, 48), fill=255)
        for y in (46, 49, 52):
            direction = 1 if x < 64 else -1
            d.line((x - 2 * direction, y, x - 7 * direction, y - 3), fill=255, width=1)
            d.line((x + 2 * direction, y, x + 7 * direction, y - 3), fill=255, width=1)
    elif code == "MD07":
        side = 1 if variant % 2 else -1
        base = 111 if side == 1 else 17
        for dx, dy, size in ((0, 0, 4), (side * 6, -10, 3), (-side * 3, -18, 2)):
            sparkle(base + dx, 48 + dy, size)
        d.line((base - side * 12, 59, base - side * 3, 52), fill=255, width=1)
    elif code == "MD08":
        for x, y, r in ((8, 72, 2), (15, 62, 1), (119, 68, 2), (112, 57, 1)):
            d.ellipse((x - r, y - r, x + r, y + r), fill=255)
    elif code == "MD09":
        offset = variant % 4
        for x, y, size in ((7, 30, 2), (15, 40, 1), (120, 27, 2), (112, 38, 1), (118, 51, 1)):
            d.rectangle((x, y + offset, x + size, y + offset + size), fill=255)
    elif code == "MD10":
        for cx, cy, flip in ((12, 56, -1), (116, 50, 1)):
            d.ellipse((cx - 1, cy - 3, cx + 1, cy + 4), fill=255)
            d.polygon([(cx, cy), (cx + 6 * flip, cy - 5), (cx + 5 * flip, cy + 2)], fill=255)
            d.polygon([(cx, cy + 1), (cx + 5 * flip, cy + 7), (cx + 4 * flip, cy + 1)], fill=255)

    alpha = mask.resize((1024, 1024), Image.Resampling.NEAREST)
    image = Image.new("RGBA", (1024, 1024), (*INK, 0))
    image.putalpha(alpha)
    return image


def trait_records(founder_index: int, modifier_code: str, modifier_name: str):
    values = FOUNDER_TRAITS[founder_index]
    records = []
    for index, (category, prefix) in enumerate(CATEGORY_CODES.items()):
        records.append({
            "category": category,
            "code": f"{prefix}{founder_index + 1:02d}",
            "name": values[index],
        })
    records.append({"category": "Signal", "code": modifier_code, "name": modifier_name})
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for old in args.output.glob("*.png"):
        old.unlink()

    sheet = Image.open(args.source)
    founders = [extract_ink(cell) for cell in split_cells(sheet)]
    combinations = [(founder, 0) for founder in range(12)]
    for modifier in range(1, len(MODIFIERS)):
        for founder in range(12):
            modifier_code = MODIFIERS[modifier][0]
            # Do not double the founder's defining atmosphere/companion.
            if founder == 11 and modifier_code == "MD06":
                continue
            if founder == 8 and modifier_code == "MD05":
                continue
            combinations.append((founder, modifier))
    combinations = combinations[:args.limit]

    hashes = set()
    records = []
    for number, (founder_index, modifier_index) in enumerate(combinations, 1):
        image = founders[founder_index].copy()
        modifier_code, modifier_name = MODIFIERS[modifier_index]
        image.alpha_composite(draw_modifier(modifier_code, founder_index + modifier_index))
        digest = hashlib.sha256(image.tobytes()).hexdigest()
        if digest in hashes:
            raise SystemExit(f"Duplicate art at #{number:03d}")
        hashes.add(digest)
        filename = f"{number:03d}.png"
        image.save(args.output / filename, optimize=True)
        house = HOUSES[(number - 1) % len(HOUSES)]
        records.append({
            "id": number,
            "name": f"Night Shift #{number:03d}",
            "house": house["name"],
            "accent": house["accent"],
            "motto": house["motto"],
            "image": f"studio/{filename}",
            "founder": founder_index + 1,
            "traits": trait_records(founder_index, modifier_code, modifier_name),
        })

    categories = {}
    for category, prefix in CATEGORY_CODES.items():
        seen = {}
        index = list(CATEGORY_CODES).index(category)
        for founder, values in enumerate(FOUNDER_TRAITS, 1):
            seen[f"{prefix}{founder:02d}"] = values[index]
        categories[category] = [{"code": code, "name": name} for code, name in seen.items()]
    categories["Signal"] = [{"code": code, "name": name} for code, name in MODIFIERS]
    library = {
        "name": "Neon Nocturne",
        "source": "Approved 12-founder calibration",
        "palette": {"ink": "#020102", "presentationLime": LIME},
        "rendering": {
            "output": "1024x1024 RGBA PNG",
            "lineLanguage": "Fine hand-authored pixel steps with solid ink masses",
            "anatomy": "Fixed three-quarter vampire bust, oversized near ear and oval eyes",
            "glow": "Restricted to founder supernatural eye and pumpkin cutouts",
        },
        "rules": [
            "Founder core pixels are immutable",
            "Signals occupy registered negative-space-safe zones",
            "No cross, crucifix, pentagram, or religious reference",
            "No text, logo, signature, or watermark",
        ],
        "traitCount": sum(len(values) for values in categories.values()),
        "categories": categories,
    }
    manifest = {
        "collection": "Night Shift Society",
        "edition": "Neon Nocturne",
        "count": len(records),
        "traitLibrary": library,
        "characters": records,
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Built {len(records)} portraits from 12 approved founders and {len(MODIFIERS)} registered signals")


if __name__ == "__main__":
    main()
