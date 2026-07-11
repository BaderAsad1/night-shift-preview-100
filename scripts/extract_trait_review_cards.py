#!/usr/bin/env python3
"""Split the V2 concept sheets into numbered review cards.

The exports are explicitly concept previews, not production source layers.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "trait-expansion-v2"
INK = (2, 1, 2)
LIME = (208, 247, 8)
YELLOW = (253, 244, 35)
PALETTE = (INK, LIME, YELLOW)

SHEETS = [
    ("hair-headwear", "HH", "01-hair-headwear.png"),
    ("eyes", "EY", "02-eyes.png"),
    ("eyewear", "EW", "03-eyewear.png"),
    ("mouths", "MO", "04-mouths.png"),
    ("outfits", "OF", "05-outfits.png"),
    ("neck", "NE", "06-neck.png"),
    ("rare", "RA", "07-rare.png"),
    ("face-details", "FD", "08-face-details.png"),
]


def names_from_readme() -> list[str]:
    text = (REVIEW / "README.md").read_text()
    entries = re.findall(r"\|\s*(\d{2})\s*\|\s*([^|\n]+)", text)
    if len(entries) != 128:
        raise ValueError(f"Expected 128 mapped names, found {len(entries)}")
    ordered: list[str] = []
    for start in range(0, len(entries), 16):
        group = sorted(entries[start : start + 16], key=lambda entry: int(entry[0]))
        ordered.extend(name.strip() for _, name in group)
    return ordered


def square_cell(image: Image.Image, row: int, column: int) -> Image.Image:
    width, height = image.size
    grid_top = round(height * 0.052)
    cell_width = width / 4
    cell_height = (height - grid_top) / 4
    x0 = round(column * cell_width)
    x1 = round((column + 1) * cell_width)
    y0 = round(grid_top + row * cell_height)
    y1 = round(grid_top + (row + 1) * cell_height)
    crop = image.crop((x0, y0, x1, y1))
    side = max(crop.size)
    square = Image.new("RGB", (side, side), LIME)
    square.paste(crop, ((side - crop.width) // 2, side - crop.height))
    return square.resize((512, 512), Image.Resampling.NEAREST)


def transparent(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    rgba.putdata([
        (red, green, blue, 0 if (red, green, blue) == LIME else 255)
        for red, green, blue, _ in rgba.getdata()
    ])
    return rgba


def quantize(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    output = Image.new("RGB", rgb.size)
    output.putdata([
        min(
            PALETTE,
            key=lambda color: sum((pixel[index] - color[index]) ** 2 for index in range(3)),
        )
        for pixel in rgb.getdata()
    ])
    return output


def main() -> None:
    names = names_from_readme()
    if len(names) != 128:
        raise ValueError(f"Expected 128 mapped names, found {len(names)}")

    cards_root = REVIEW / "cards"
    transparent_root = REVIEW / "cards-transparent"
    source_root = REVIEW / "cards-source"
    shutil.rmtree(cards_root, ignore_errors=True)
    shutil.rmtree(transparent_root, ignore_errors=True)
    shutil.rmtree(source_root, ignore_errors=True)
    records = []
    name_index = 0

    for category, prefix, sheet_name in SHEETS:
        image = Image.open(REVIEW / sheet_name).convert("RGB")
        raw_image = Image.open(REVIEW / "raw-sheets" / sheet_name).convert("RGB")
        category_root = cards_root / category
        transparent_category_root = transparent_root / category
        source_category_root = source_root / category
        category_root.mkdir(parents=True, exist_ok=True)
        transparent_category_root.mkdir(parents=True, exist_ok=True)
        source_category_root.mkdir(parents=True, exist_ok=True)
        for index in range(16):
            code = f"{prefix}{index + 1:02d}"
            card = square_cell(image, index // 4, index % 4)
            card_path = category_root / f"{code}.png"
            transparent_path = transparent_category_root / f"{code}.png"
            source_path = source_category_root / f"{code}.png"
            card.save(card_path, optimize=True)
            transparent(card).save(transparent_path, optimize=True)
            source_card = quantize(square_cell(raw_image, index // 4, index % 4))
            source_card.save(source_path, optimize=True)
            records.append({
                "code": code,
                "name": names[name_index],
                "category": category,
                "sheet": sheet_name,
                "cell": index + 1,
                "card": str(card_path.relative_to(REVIEW)),
                "transparentPreview": str(transparent_path.relative_to(REVIEW)),
                "sourceCard": str(source_path.relative_to(REVIEW)),
                "status": "working-set",
                "productionLayer": False,
            })
            name_index += 1

    manifest = {
        "collection": "Neon Nocturne",
        "edition": "Trait Expansion V2 Review",
        "conceptCount": len(records),
        "productionLayerCount": 0,
        "warning": "Concept previews only. Not aligned production source layers.",
        "palette": {"ink": "#020102", "presentationLime": "#d0f708", "traitYellow": "#fdf423"},
        "traits": records,
    }
    (REVIEW / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (REVIEW / "manifest.js").write_text(
        "window.TRAIT_REVIEW_MANIFEST = " + json.dumps(manifest, indent=2) + ";\n"
    )
    print(
        f"Exported {len(records)} review cards, {len(records)} transparent previews, "
        f"and {len(records)} clean source cards"
    )


if __name__ == "__main__":
    main()
