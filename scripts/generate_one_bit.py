#!/usr/bin/env python3
"""Create pure-black, transparent one-bit variants of the approved color renders."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


NATIVE = 128
SCALE = 8
BAYER_4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def is_edge(alpha, x: int, y: int) -> bool:
    width, height = alpha.size
    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        if nx < 0 or ny < 0 or nx >= width or ny >= height or alpha.getpixel((nx, ny)) < 72:
            return True
    return False


def convert(source: Image.Image) -> Image.Image:
    native = source.convert("RGBA").resize((NATIVE, NATIVE), Image.Resampling.NEAREST)
    alpha = native.getchannel("A")
    result = Image.new("RGBA", (NATIVE, NATIVE), (0, 0, 0, 0))
    src = native.load()
    out = result.load()

    for y in range(NATIVE):
        for x in range(NATIVE):
            r, g, b, a = src[x, y]
            if a < 72:
                continue
            luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
            darkness = (255 - luminance) / 255
            threshold = BAYER_4[y % 4][x % 4]
            black = is_edge(alpha, x, y) or darkness * 17.5 >= threshold
            if black:
                out[x, y] = (0, 0, 0, 255)

    return result.resize((NATIVE * SCALE, NATIVE * SCALE), Image.Resampling.NEAREST)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    files = sorted(args.input.glob("[0-9][0-9][0-9].png"))
    if len(files) != 100:
        raise SystemExit(f"Expected 100 source renders, found {len(files)}")

    coverage = []
    for path in files:
        image = convert(Image.open(path))
        image.save(args.output / path.name, optimize=True)
        black_pixels = sum(1 for a in image.getchannel("A").getdata() if a)
        coverage.append(black_pixels / (image.width * image.height))

    if min(coverage) < 0.025 or max(coverage) > 0.7:
        raise SystemExit(f"Unexpected black coverage range: {min(coverage):.3f}–{max(coverage):.3f}")
    print(f"Generated 100 one-bit black renders; coverage {min(coverage):.3f}–{max(coverage):.3f}")


if __name__ == "__main__":
    main()
