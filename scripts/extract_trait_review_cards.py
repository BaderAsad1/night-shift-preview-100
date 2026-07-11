#!/usr/bin/env python3
"""Split the V2 concept sheets into registered numbered review cards.

The sheets contain complete character concepts, not isolated production layers.
Each card is extracted from the actual occupied row band, kept at one shared
source scale, and translated so the character body ends on the canvas baseline.
"""

from __future__ import annotations

import json
import re
import shutil
from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "trait-expansion-v2"
INK = (2, 1, 2)
LIME = (208, 247, 8)
YELLOW = (253, 244, 35)
PALETTE = (INK, LIME, YELLOW)
CANVAS = 512
SOURCE_CELL = 360
HEADER_BOTTOM = 65

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


def occupied_row_bands(image: Image.Image, column: int) -> list[tuple[int, int]]:
    """Return the four real artwork bands in one sheet column.

    The former equal-height split cut into the following row. Detecting the
    actual non-background runs makes the extraction independent of row spacing.
    """
    width, height = image.size
    x0 = round(column * width / 4)
    x1 = round((column + 1) * width / 4)
    pixels = image.load()
    occupied = [
        y
        for y in range(HEADER_BOTTOM, height)
        if any(pixels[x, y] != LIME for x in range(x0, x1))
    ]
    runs: list[tuple[int, int]] = []
    if occupied:
        start = previous = occupied[0]
        for y in occupied[1:]:
            if y != previous + 1:
                if previous - start >= 2:
                    runs.append((start, previous + 1))
                start = y
            previous = y
        if previous - start >= 2:
            runs.append((start, previous + 1))
    if len(runs) != 4:
        raise ValueError(f"Column {column + 1} has {len(runs)} artwork rows, expected 4: {runs}")
    return runs


def occupied_column_bands(image: Image.Image, row: int) -> list[tuple[int, int]]:
    """Return the four actual artwork bands across one sheet row."""
    row_runs = [occupied_row_bands(image, column)[row] for column in range(4)]
    y0 = min(run[0] for run in row_runs)
    y1 = max(run[1] for run in row_runs)
    pixels = image.load()
    occupied = [
        x
        for x in range(image.width)
        if any(pixels[x, y] != LIME for y in range(y0, y1))
    ]
    runs: list[tuple[int, int]] = []
    if occupied:
        start = previous = occupied[0]
        for x in occupied[1:]:
            if x != previous + 1:
                if previous - start >= 2:
                    runs.append((start, previous + 1))
                start = x
            previous = x
        if previous - start >= 2:
            runs.append((start, previous + 1))
    if len(runs) != 4:
        raise ValueError(f"Row {row + 1} has {len(runs)} artwork columns, expected 4: {runs}")
    return runs


def alpha_components(alpha: Image.Image) -> list[list[tuple[int, int]]]:
    pixels = alpha.load()
    width, height = alpha.size
    seen: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    for y in range(height):
        for x in range(width):
            if not pixels[x, y] or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            component: list[tuple[int, int]] = []
            while queue:
                cx, cy = queue.popleft()
                component.append((cx, cy))
                for nx in range(cx - 1, cx + 2):
                    for ny in range(cy - 1, cy + 2):
                        if (
                            0 <= nx < width
                            and 0 <= ny < height
                            and (nx, ny) not in seen
                            and pixels[nx, ny]
                        ):
                            seen.add((nx, ny))
                            queue.append((nx, ny))
            components.append(component)
    return sorted(components, key=len, reverse=True)


def remove_below_body_fragments(image: Image.Image) -> Image.Image:
    """Remove any disconnected artwork that sits below the main character body."""
    alpha = image.getchannel("A")
    components = alpha_components(alpha)
    if not components:
        raise ValueError("Extracted card contains no artwork")
    main_bottom = max(y for _, y in components[0])
    alpha_pixels = alpha.load()
    for component in components[1:]:
        if min(y for _, y in component) > main_bottom:
            for x, y in component:
                alpha_pixels[x, y] = 0
    cleaned = image.copy()
    cleaned.putalpha(alpha)
    return cleaned


def registered_cell(
    clean_sheet: Image.Image,
    source_sheet: Image.Image,
    row: int,
    column: int,
) -> tuple[Image.Image, Image.Image]:
    """Extract one concept at fixed scale and anchor its body to y=511."""
    width, _ = clean_sheet.size
    x0, x1 = occupied_column_bands(clean_sheet, row)[column]
    y0, y1 = occupied_row_bands(clean_sheet, column)[row]

    clean_crop = clean_sheet.crop((x0, y0, x1, y1)).convert("RGB")
    source_crop = quantize(source_sheet.crop((x0, y0, x1, y1)).convert("RGB"))
    nominal_center = (column + 0.5) * width / 4
    x_offset = round(SOURCE_CELL / 2 + x0 - nominal_center)

    clean_stage = Image.new("RGBA", (SOURCE_CELL, SOURCE_CELL), (*LIME, 0))
    source_stage = Image.new("RGBA", (SOURCE_CELL, SOURCE_CELL), (*LIME, 0))
    clean_pixels = clean_crop.load()
    source_pixels = source_crop.load()
    for y in range(clean_crop.height):
        for x in range(clean_crop.width):
            if clean_pixels[x, y] != LIME:
                clean_stage.putpixel((x + x_offset, y), (*clean_pixels[x, y], 255))
                source_stage.putpixel((x + x_offset, y), (*source_pixels[x, y], 255))

    clean_layer = clean_stage.resize((CANVAS, CANVAS), Image.Resampling.NEAREST)
    source_layer = source_stage.resize((CANVAS, CANVAS), Image.Resampling.NEAREST)
    clean_layer = remove_below_body_fragments(clean_layer)
    source_layer.putalpha(clean_layer.getchannel("A"))

    components = alpha_components(clean_layer.getchannel("A"))
    main_bottom = max(y for _, y in components[0]) + 1
    shift_y = CANVAS - main_bottom
    registered_clean = Image.new("RGBA", (CANVAS, CANVAS), (*LIME, 0))
    registered_source = Image.new("RGBA", (CANVAS, CANVAS), (*LIME, 0))
    registered_clean.alpha_composite(clean_layer, (0, shift_y))
    registered_source.alpha_composite(source_layer, (0, shift_y))
    return registered_clean, registered_source


def on_lime(layer: Image.Image) -> Image.Image:
    background = Image.new("RGBA", layer.size, (*LIME, 255))
    background.alpha_composite(layer)
    return background.convert("RGB")


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
            layer, source_layer = registered_cell(
                image,
                raw_image,
                index // 4,
                index % 4,
            )
            card = on_lime(layer)
            card_path = category_root / f"{code}.png"
            transparent_path = transparent_category_root / f"{code}.png"
            source_path = source_category_root / f"{code}.png"
            card.save(card_path, optimize=True)
            layer.save(transparent_path, optimize=True)
            source_card = on_lime(source_layer)
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
                "status": "registered-concept",
                "productionLayer": False,
                "registration": {
                    "canvas": [CANVAS, CANVAS],
                    "sourceCell": SOURCE_CELL,
                    "bodyBaselineY": CANVAS,
                    "resampling": "nearest",
                },
            })
            name_index += 1

    manifest = {
        "collection": "Neon Nocturne",
        "edition": "Trait Expansion V2 Review",
        "conceptCount": len(records),
        "productionLayerCount": 0,
        "warning": "Registered complete-character concepts. Not isolated mix-and-match production layers.",
        "palette": {"ink": "#020102", "presentationLime": "#d0f708", "traitYellow": "#fdf423"},
        "yellowPolicy": "explicit-mask-eyes-and-approved-flames-only",
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
