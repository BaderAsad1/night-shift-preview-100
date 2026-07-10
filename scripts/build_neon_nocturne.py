#!/usr/bin/env python3
"""Build the expanded Neon Nocturne edition from approved pixel modules.

The calibration sheet supplies twelve head/face modules and twelve torso/neck
modules. They are registered independently and recombined with atmosphere
traits, producing real core variation while preserving the approved pixels.
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

HEAD_MODULE_NAMES = [
    "Raven Hollow", "Pumpkin Glow", "Midnight Fade", "Flame Lashes",
    "Stitched X", "Horned Anger", "Mummy Glow", "Coven Hollow",
    "Spectral Hollow", "Raven Hypno", "Beanie Hollow", "Webbed Hollow",
]

TORSO_MODULE_NAMES = [
    "Skull Tux + Skull Bow", "High Collar + Soft Bow",
    "High Collar + Medallion", "Striped Knit + Choker",
    "Undertaker Shirt + Buttons", "Winged Cape + Medallion",
    "Wrapped Tunic", "Coven Coat + Slim Scarf",
    "Chain Crewneck + Loose Chain", "Velvet Jacket + Soft Bow",
    "Skeleton Hoodie", "High Collar + Medallion",
]

# Each head ends at a slightly different vertical landmark. These registered
# cuts preserve faces, fangs, hats and head-specific effects without carrying
# the original lower outfit into the recombined portrait.
HEAD_BOTTOMS = [735, 805, 745, 710, 720, 760, 790, 735, 740, 735, 735, 740]
TORSO_START = 675


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


def keep_alpha(image: Image.Image, predicate) -> Image.Image:
    result = image.copy()
    source = image.getchannel("A")
    target = Image.new("L", image.size, 0)
    src = source.load()
    dst = target.load()
    for y in range(image.height):
        for x in range(image.width):
            if predicate(x, y):
                dst[x, y] = src[x, y]
    result.putalpha(target)
    return result


def make_head_module(founder: Image.Image, index: int) -> Image.Image:
    bottom = HEAD_BOTTOMS[index]

    def keep(x: int, y: int) -> bool:
        if y <= bottom:
            return True
        # Preserve head-owned effects that extend below the normal neck cut.
        if index == 5 and y <= 825 and (x < 270 or x > 750):
            return True
        if index == 8 and (x < 245 or x > 785):
            return True
        if index == 11 and x < 285:
            return True
        return False

    return keep_alpha(founder, keep)


def make_torso_module(founder: Image.Image, index: int) -> Image.Image:
    def keep(x: int, y: int) -> bool:
        if y >= TORSO_START:
            return True
        # The lantern belongs to the Coven torso module and begins above the
        # shared shoulder landmark.
        return index == 7 and x < 330 and y >= 515

    return keep_alpha(founder, keep)


def assemble(head: Image.Image, torso: Image.Image, head_index: int, atmosphere_index: int) -> Image.Image:
    image = torso.copy()
    alpha = image.getchannel("A")
    # Knock out donor head pixels from the torso layer. This lets the selected
    # head's lime negative space remain clean rather than revealing a second
    # face underneath it.
    clear = ImageDraw.Draw(alpha)
    clear.rectangle((150, 0, 875, HEAD_BOTTOMS[head_index]), fill=0)
    image.putalpha(alpha)
    image.alpha_composite(head)
    modifier_code, _ = MODIFIERS[atmosphere_index]
    image.alpha_composite(draw_modifier(modifier_code, head_index + atmosphere_index))
    return image


def trait_records(head_index: int, torso_index: int, atmosphere_index: int):
    head_values = FOUNDER_TRAITS[head_index]
    torso_values = FOUNDER_TRAITS[torso_index]
    modifier_code, modifier_name = MODIFIERS[atmosphere_index]
    records = [
        {"category": "Head / Face", "code": f"HF{head_index + 1:02d}", "name": HEAD_MODULE_NAMES[head_index]},
        {"category": "Hair / Headwear", "code": f"HD{head_index + 1:02d}", "name": head_values[0]},
        {"category": "Eyes", "code": f"EY{head_index + 1:02d}", "name": head_values[1]},
        {"category": "Mouth", "code": f"MT{head_index + 1:02d}", "name": head_values[2]},
        {"category": "Outfit / Neck", "code": f"OT{torso_index + 1:02d}", "name": TORSO_MODULE_NAMES[torso_index]},
        {"category": "Outfit", "code": f"OF{torso_index + 1:02d}", "name": torso_values[3]},
        {"category": "Neck", "code": f"NK{torso_index + 1:02d}", "name": torso_values[4]},
        {"category": "Atmosphere", "code": modifier_code.replace("MD", "AT"), "name": modifier_name.replace("Founder Clean", "Clean Air")},
    ]
    head_extra = head_values[5]
    if head_extra in {"Brow Stitches", "Bat Wings", "Smoke Halo", "Hanging Spider"}:
        records.insert(4, {"category": "Head Extra", "code": f"HX{head_index + 1:02d}", "name": head_extra})
    if torso_index == 7:
        records.append({"category": "Companion", "code": "CP08", "name": "Pumpkin Lantern"})
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
    heads = [make_head_module(founder, index) for index, founder in enumerate(founders)]
    torsos = [make_torso_module(founder, index) for index, founder in enumerate(founders)]

    # Latin-square offsets balance every head and torso across the collection.
    # The first twelve recreate the approved founders; every later character
    # changes its core head/torso pairing before atmosphere is considered.
    offsets = [0, 5, 10, 3, 8, 1, 6, 11, 4, 9, 2, 7]
    combinations = []
    for block, offset in enumerate(offsets):
        for head_index in range(12):
            torso_index = (head_index + offset) % 12
            atmosphere_index = len(combinations) % len(MODIFIERS)
            if head_index == 8 and MODIFIERS[atmosphere_index][0] == "MD05":
                atmosphere_index = (atmosphere_index + 1) % len(MODIFIERS)
            if head_index == 11 and MODIFIERS[atmosphere_index][0] == "MD06":
                atmosphere_index = (atmosphere_index + 1) % len(MODIFIERS)
            combinations.append((head_index, torso_index, atmosphere_index))
    combinations = combinations[:args.limit]

    hashes = set()
    records = []
    for number, (head_index, torso_index, atmosphere_index) in enumerate(combinations, 1):
        image = assemble(heads[head_index], torsos[torso_index], head_index, atmosphere_index)
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
            "modules": {"head": head_index + 1, "torso": torso_index + 1, "atmosphere": atmosphere_index + 1},
            "traits": trait_records(head_index, torso_index, atmosphere_index),
        })

    categories = {
        "Head / Face": [
            {
                "code": f"HF{index + 1:02d}", "name": HEAD_MODULE_NAMES[index],
                "components": {"hair": values[0], "eyes": values[1], "mouth": values[2]},
            }
            for index, values in enumerate(FOUNDER_TRAITS)
        ],
        "Outfit / Neck": [
            {
                "code": f"OT{index + 1:02d}", "name": TORSO_MODULE_NAMES[index],
                "components": {"outfit": values[3], "neck": values[4]},
            }
            for index, values in enumerate(FOUNDER_TRAITS)
        ],
        "Atmosphere": [
            {"code": code.replace("MD", "AT"), "name": name.replace("Founder Clean", "Clean Air")}
            for code, name in MODIFIERS
        ],
    }
    library = {
        "name": "Neon Nocturne",
        "source": "Approved modular calibration",
        "palette": {"ink": "#020102", "presentationLime": LIME},
        "rendering": {
            "output": "1024x1024 RGBA PNG",
            "lineLanguage": "Fine hand-authored pixel steps with solid ink masses",
            "anatomy": "Fixed three-quarter vampire bust, oversized near ear and oval eyes",
            "glow": "Restricted to founder supernatural eye and pumpkin cutouts",
        },
        "rules": [
            "Head/face and outfit/neck modules are independently registered",
            "Every published pairing is unique before atmosphere is applied",
            "Atmosphere occupies registered negative-space-safe zones",
            "No cross, crucifix, pentagram, or religious reference",
            "No text, logo, signature, or watermark",
        ],
        "moduleCount": sum(len(values) for values in categories.values()),
        "possibleCorePairings": len(heads) * len(torsos),
        "possibleCombinations": len(heads) * len(torsos) * len(MODIFIERS),
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
    print(
        f"Built {len(records)} portraits from {len(heads)} head modules, {len(torsos)} torso modules "
        f"and {len(MODIFIERS)} atmospheres ({library['possibleCombinations']} possible combinations)"
    )


if __name__ == "__main__":
    main()
