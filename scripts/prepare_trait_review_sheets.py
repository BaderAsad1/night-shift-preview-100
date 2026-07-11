#!/usr/bin/env python3
"""Normalize concept sheets to the locked Neon Nocturne review palette.

These sheets are approval artifacts, not production layers. The script removes
generated antialiasing/gradients and recolors enclosed eye interiors to the
approved warm yellow so reviewers see the intended final color behavior.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter


INK = (2, 1, 2)
LIME = (208, 247, 8)
YELLOW = (253, 244, 35)
PALETTE = (INK, LIME, YELLOW)


def nearest_palette(pixel: tuple[int, int, int]) -> tuple[int, int, int]:
    return min(
        PALETTE,
        key=lambda color: sum((pixel[index] - color[index]) ** 2 for index in range(3)),
    )


def components(
    pixels: list[list[tuple[int, int, int]]],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
) -> list[list[tuple[int, int]]]:
    seen: set[tuple[int, int]] = set()
    groups: list[list[tuple[int, int]]] = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if (x, y) in seen or pixels[y][x] != LIME:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            group: list[tuple[int, int]] = []
            while queue:
                current_x, current_y = queue.popleft()
                group.append((current_x, current_y))
                for next_x, next_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if not (x0 <= next_x < x1 and y0 <= next_y < y1):
                        continue
                    if (next_x, next_y) in seen or pixels[next_y][next_x] != LIME:
                        continue
                    seen.add((next_x, next_y))
                    queue.append((next_x, next_y))
            groups.append(group)
    return groups


def open_components(
    blocked: list[list[bool]],
    x0: int,
    y0: int,
    x1: int,
    y1: int,
) -> list[list[tuple[int, int]]]:
    seen: set[tuple[int, int]] = set()
    groups: list[list[tuple[int, int]]] = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            if (x, y) in seen or blocked[y][x]:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            group: list[tuple[int, int]] = []
            while queue:
                current_x, current_y = queue.popleft()
                group.append((current_x, current_y))
                for next_x, next_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if not (x0 <= next_x < x1 and y0 <= next_y < y1):
                        continue
                    if (next_x, next_y) in seen or blocked[next_y][next_x]:
                        continue
                    seen.add((next_x, next_y))
                    queue.append((next_x, next_y))
            groups.append(group)
    return groups


def recolor_eye_interiors(image: Image.Image) -> tuple[Image.Image, list[int]]:
    width, height = image.size
    data = list(image.getdata())
    rows = [data[y * width : (y + 1) * width] for y in range(height)]
    ink_mask = Image.new("L", image.size, 0)
    ink_mask.putdata([255 if pixel == INK else 0 for pixel in data])
    closed_ink = ink_mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    closed_data = list(closed_ink.getdata())
    blocked = [
        [closed_data[y * width + x] > 0 for x in range(width)]
        for y in range(height)
    ]
    grid_top = round(height * 0.052)
    cell_width = width / 4
    cell_height = (height - grid_top) / 4
    candidate_counts: list[int] = []

    for row in range(4):
        for column in range(4):
            cell_x0 = round(column * cell_width)
            cell_x1 = round((column + 1) * cell_width)
            cell_y0 = round(grid_top + row * cell_height)
            cell_y1 = round(grid_top + (row + 1) * cell_height)
            ink_points = [
                (x, y)
                for y in range(cell_y0, cell_y1)
                for x in range(cell_x0, cell_x1)
                if rows[y][x] == INK
            ]
            if not ink_points:
                candidate_counts.append(0)
                continue
            xs = [point[0] for point in ink_points]
            ys = [point[1] for point in ink_points]
            art_x0, art_x1 = min(xs), max(xs) + 1
            art_y0, art_y1 = min(ys), max(ys) + 1
            art_width = art_x1 - art_x0
            art_height = art_y1 - art_y0
            eye_x0 = round(art_x0 + art_width * 0.27)
            eye_x1 = round(art_x0 + art_width * 0.94)
            eye_y0 = round(art_y0 + art_height * 0.17)
            eye_y1 = round(art_y0 + art_height * 0.58)

            candidates: list[list[tuple[int, int]]] = []
            for group in open_components(blocked, eye_x0, eye_y0, eye_x1, eye_y1):
                if not 24 <= len(group) <= 4800:
                    continue
                group_xs = [point[0] for point in group]
                group_ys = [point[1] for point in group]
                group_width = max(group_xs) - min(group_xs) + 1
                group_height = max(group_ys) - min(group_ys) + 1
                if group_width > art_width * 0.43 or group_height > art_height * 0.39:
                    continue
                if (
                    min(group_xs) == eye_x0
                    or max(group_xs) == eye_x1 - 1
                    or min(group_ys) == eye_y0
                    or max(group_ys) == eye_y1 - 1
                ):
                    continue
                candidates.append(group)

            candidate_counts.append(len(candidates))
            for group in candidates:
                for x, y in group:
                    if rows[y][x] == LIME:
                        rows[y][x] = YELLOW

    flattened = [pixel for row in rows for pixel in row]
    output = Image.new("RGB", image.size)
    output.putdata(flattened)
    return output, candidate_counts


def normalize(source: Path) -> list[int]:
    image = Image.open(source).convert("RGB")
    quantized = Image.new("RGB", image.size)
    quantized.putdata([nearest_palette(pixel) for pixel in image.getdata()])
    prepared, counts = recolor_eye_interiors(quantized)
    prepared.save(source, optimize=True)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.paths:
        counts = normalize(path)
        print(f"{path.name}: eye-components={','.join(map(str, counts))}")


if __name__ == "__main__":
    main()
