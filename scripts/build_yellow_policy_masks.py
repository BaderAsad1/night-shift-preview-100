#!/usr/bin/env python3
"""Build explicit sheet-level masks for approved eye and flame yellow pixels.

This is a one-time source-preparation utility. The committed masks, not color
quantization, are the authority for where #fdf423 may appear.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image

from prepare_trait_review_sheets import INK, LIME, YELLOW, cell_bounds, nearest_palette


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "trait-expansion-v2"
FLAME_CELLS = {"01-hair-headwear.png": {5}, "07-rare.png": {4}}


def groups_in_region(
    image: Image.Image,
    color: tuple[int, int, int],
    bounds: tuple[int, int, int, int],
) -> list[list[tuple[int, int]]]:
    x0, y0, x1, y1 = bounds
    pixels = image.load()
    seen: set[tuple[int, int]] = set()
    groups: list[list[tuple[int, int]]] = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if pixels[x, y] != color or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            group: list[tuple[int, int]] = []
            while queue:
                cx, cy = queue.popleft()
                group.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if x0 <= nx < x1 and y0 <= ny < y1 and (nx, ny) not in seen and pixels[nx, ny] == color:
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            groups.append(group)
    return sorted(groups, key=len, reverse=True)


def add_eye_mask(mask: Image.Image, base: Image.Image, reference: Image.Image, cell: int) -> int:
    row, column = divmod(cell - 1, 4)
    cell_x0, cell_y0, cell_x1, cell_y1 = cell_bounds(base, row, column)
    base_pixels = base.load()
    ink = [
        (x, y)
        for y in range(cell_y0, cell_y1)
        for x in range(cell_x0, cell_x1)
        if base_pixels[x, y] == INK
    ]
    xs = [x for x, _ in ink]
    ys = [y for _, y in ink]
    art_x0, art_x1 = min(xs), max(xs) + 1
    art_y0, art_y1 = min(ys), max(ys) + 1
    art_width = art_x1 - art_x0
    art_height = art_y1 - art_y0
    eye_bounds = (
        round(art_x0 + art_width * 0.27),
        round(art_y0 + art_height * 0.17),
        round(art_x0 + art_width * 0.94),
        round(art_y0 + art_height * 0.58),
    )
    selected = []
    for group in groups_in_region(reference, YELLOW, eye_bounds):
        group_xs = [x for x, _ in group]
        group_ys = [y for _, y in group]
        width = max(group_xs) - min(group_xs) + 1
        height = max(group_ys) - min(group_ys) + 1
        center_y = sum(group_ys) / len(group)
        if not 20 <= len(group) <= 3000:
            continue
        if width > art_width * 0.36 or height > art_height * 0.36:
            continue
        if not art_y0 + art_height * 0.24 <= center_y <= art_y0 + art_height * 0.61:
            continue
        selected.extend(group)
    target = mask.load()
    for x, y in selected:
        target[x, y] = 255
    return len(selected)


def add_flame_mask(mask: Image.Image, base: Image.Image, raw: Image.Image, cell: int) -> int:
    row, column = divmod(cell - 1, 4)
    bounds = cell_bounds(base, row, column)
    lime_groups = groups_in_region(base, LIME, bounds)
    background_and_flame = max(lime_groups, key=len)
    raw_pixels = raw.load()
    target = mask.load()
    count = 0
    for x, y in background_and_flame:
        red, green, blue = raw_pixels[x, y]
        if red >= 235 and green >= 220 and blue <= 110:
            target[x, y] = 255
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-root", type=Path, required=True)
    args = parser.parse_args()
    destination = REVIEW / "yellow-masks"
    destination.mkdir(exist_ok=True)
    for raw_path in sorted((REVIEW / "raw-sheets").glob("0*.png")):
        raw = Image.open(raw_path).convert("RGB")
        base = Image.new("RGB", raw.size)
        base.putdata([nearest_palette(pixel) for pixel in raw.getdata()])
        reference = Image.open(args.reference_root / raw_path.name).convert("RGB")
        mask = Image.new("L", raw.size, 0)
        counts = [add_eye_mask(mask, base, reference, cell) for cell in range(1, 17)]
        for cell in FLAME_CELLS.get(raw_path.name, set()):
            counts[cell - 1] += add_flame_mask(mask, base, raw, cell)
        if any(count == 0 for count in counts):
            missing = [index + 1 for index, count in enumerate(counts) if count == 0]
            raise ValueError(f"{raw_path.name} has empty approved-yellow masks in cells {missing}")
        mask.save(destination / raw_path.name, optimize=True)
        print(f"{raw_path.name}: minYellowMask={min(counts)} maxYellowMask={max(counts)}")


if __name__ == "__main__":
    main()
