#!/usr/bin/env python3
"""Create coarse, solid-black pixel portraits from the approved color renders.

The output deliberately uses a tiny 32x32 drawing grid. Unlike the existing
one-bit edition, it has no ordered dithering: only silhouette edges, dark forms,
and meaningful high-contrast interior edges survive.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


NATIVE = 32
SCALE = 32
ALPHA_THRESHOLD = 34
DARK_THRESHOLD = 112
EDGE_CONTRAST = 48


def luminance(pixel: tuple[int, int, int, int]) -> float:
    r, g, b, _ = pixel
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def neighbors(x: int, y: int):
    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        if 0 <= nx < NATIVE and 0 <= ny < NATIVE:
            yield nx, ny


def convert(source: Image.Image) -> Image.Image:
    native = source.convert("RGBA").resize((NATIVE, NATIVE), Image.Resampling.BOX)
    src = native.load()
    mask = [[False for _ in range(NATIVE)] for _ in range(NATIVE)]

    for y in range(NATIVE):
        for x in range(NATIVE):
            pixel = src[x, y]
            if pixel[3] < ALPHA_THRESHOLD:
                continue

            current_luma = luminance(pixel)
            adjacent = list(neighbors(x, y))
            silhouette_edge = any(src[nx, ny][3] < ALPHA_THRESHOLD for nx, ny in adjacent)
            darker_edge = any(
                src[nx, ny][3] >= ALPHA_THRESHOLD
                and luminance(src[nx, ny]) - current_luma >= EDGE_CONTRAST
                for nx, ny in adjacent
            )
            mask[y][x] = silhouette_edge or current_luma <= DARK_THRESHOLD or darker_edge

    # Drop lone specks introduced by downsampling unless they represent a very
    # dark source pixel. This keeps the chunky line work intentional.
    cleaned = [[False for _ in range(NATIVE)] for _ in range(NATIVE)]
    for y in range(NATIVE):
        for x in range(NATIVE):
            if not mask[y][x]:
                continue
            linked = sum(mask[ny][nx] for nx, ny in neighbors(x, y))
            cleaned[y][x] = linked > 0 or luminance(src[x, y]) < 42

    result = Image.new("RGBA", (NATIVE, NATIVE), (0, 0, 0, 0))
    out = result.load()
    for y in range(NATIVE):
        for x in range(NATIVE):
            if cleaned[y][x]:
                out[x, y] = (0, 0, 0, 255)

    return result.resize((NATIVE * SCALE, NATIVE * SCALE), Image.Resampling.NEAREST)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    files = sorted(args.input.glob("[0-9][0-9][0-9].png"))[: args.limit]
    if len(files) != args.limit:
        raise SystemExit(f"Expected {args.limit} source renders, found {len(files)}")

    coverage = []
    for path in files:
        image = convert(Image.open(path))
        image.save(args.output / path.name, optimize=True)
        black_pixels = sum(1 for alpha in image.getchannel("A").getdata() if alpha)
        coverage.append(black_pixels / (image.width * image.height))

    if min(coverage) < 0.012 or max(coverage) > 0.70:
        raise SystemExit(f"Unexpected black coverage range: {min(coverage):.3f}-{max(coverage):.3f}")
    print(
        f"Generated {len(files)} chunky one-bit renders on a {NATIVE}x{NATIVE} grid; "
        f"coverage {min(coverage):.3f}-{max(coverage):.3f}"
    )


if __name__ == "__main__":
    main()
