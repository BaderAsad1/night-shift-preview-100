#!/usr/bin/env python3
"""Normalize concept sheets to the locked Neon Nocturne review palette.

Base artwork is strictly ink or presentation lime. Yellow is introduced only
by the explicit eye-interior and approved flame-interior passes below.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


INK = (2, 1, 2)
LIME = (208, 247, 8)
YELLOW = (253, 244, 35)
BASE_PALETTE = (INK, LIME)
HEADER_BOTTOM = 65
MASK_ROOT = Path(__file__).resolve().parents[1] / "review" / "trait-expansion-v2" / "yellow-masks"


def nearest_palette(pixel: tuple[int, int, int]) -> tuple[int, int, int]:
    return min(
        BASE_PALETTE,
        key=lambda color: sum((pixel[index] - color[index]) ** 2 for index in range(3)),
    )


def occupied_row_bands(image: Image.Image, column: int) -> list[tuple[int, int]]:
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
        raise ValueError(f"Column {column + 1} has invalid artwork rows: {runs}")
    return runs


def cell_bounds(image: Image.Image, row: int, column: int) -> tuple[int, int, int, int]:
    width, _ = image.size
    x0 = round(column * width / 4)
    x1 = round((column + 1) * width / 4)
    y0, y1 = occupied_row_bands(image, column)[row]
    return x0, y0, x1, y1


def normalize(source: Path, destination: Path | None = None) -> list[int]:
    image = Image.open(source).convert("RGB")
    quantized = Image.new("RGB", image.size)
    quantized.putdata([nearest_palette(pixel) for pixel in image.getdata()])
    mask_path = MASK_ROOT / source.name
    if not mask_path.exists():
        raise ValueError(f"Missing approved eye/flame mask: {mask_path}")
    mask = Image.open(mask_path).convert("1")
    if mask.size != image.size:
        raise ValueError(f"Yellow mask size mismatch for {source.name}")
    prepared = quantized.copy()
    pixels = prepared.load()
    mask_pixels = mask.load()
    for y in range(image.height):
        for x in range(image.width):
            if mask_pixels[x, y] and pixels[x, y] == LIME:
                pixels[x, y] = YELLOW
    counts = []
    for row in range(4):
        for column in range(4):
            x0, y0, x1, y1 = cell_bounds(prepared, row, column)
            counts.append(sum(mask_pixels[x, y] != 0 for y in range(y0, y1) for x in range(x0, x1)))
    prepared.save(destination or source, optimize=True)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    for path in args.paths:
        destination = args.output_dir / path.name if args.output_dir else path
        if args.output_dir:
            args.output_dir.mkdir(parents=True, exist_ok=True)
        counts = normalize(path, destination)
        print(f"{path.name}: eye-components={','.join(map(str, counts))}")


if __name__ == "__main__":
    main()
