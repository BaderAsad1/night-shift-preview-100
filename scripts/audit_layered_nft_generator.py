#!/usr/bin/env python3
"""Audit the registered layer library and deterministic generator test output."""

from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "review" / "trait-expansion-v2" / "generator"
INK = (2, 1, 2)
LIME = (208, 247, 8)
YELLOW = (253, 244, 35)


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def components(alpha: Image.Image) -> list[list[tuple[int, int]]]:
    pixels = alpha.load()
    width, height = alpha.size
    seen: set[tuple[int, int]] = set()
    result: list[list[tuple[int, int]]] = []
    for y in range(height):
        for x in range(width):
            if not pixels[x, y] or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            group: list[tuple[int, int]] = []
            while queue:
                cx, cy = queue.popleft()
                group.append((cx, cy))
                for nx in range(cx - 1, cx + 2):
                    for ny in range(cy - 1, cy + 2):
                        if 0 <= nx < width and 0 <= ny < height and pixels[nx, ny] and (nx, ny) not in seen:
                            seen.add((nx, ny))
                            queue.append((nx, ny))
            result.append(group)
    return sorted(result, key=len, reverse=True)


def main() -> None:
    config = json.loads((GENERATOR / "config.json").read_text())
    size = tuple(config["canvas"])
    layer_files = sorted((GENERATOR / "layers").rglob("*.png"))
    if len(layer_files) != 128:
        fail(f"Expected 128 registered layer files, found {len(layer_files)}")
    for path in layer_files:
        image = Image.open(path).convert("RGBA")
        if image.size != size:
            fail(f"{path.name} has incorrect canvas size")
        if set(image.getchannel("A").getdata()) - {0, 255}:
            fail(f"{path.name} contains feathered alpha")
        visible = {pixel[:3] for pixel in image.getdata() if pixel[3]}
        if visible != {INK, YELLOW}:
            fail(f"{path.name} has an invalid visible palette")
        groups = components(image.getchannel("A"))
        if not groups or max(y for _, y in groups[0]) != size[1] - 1:
            fail(f"{path.name} main body does not sit on the bottom baseline")
        if any(x in (0, size[0] - 1) for x, _ in groups[0]):
            fail(f"{path.name} is clipped horizontally")

    manifest = json.loads((GENERATOR / "output" / "manifest.json").read_text())
    outputs = manifest["outputs"]
    if len(outputs) != manifest["count"] or len({item["dna"] for item in outputs}) != len(outputs):
        fail("Generator output DNA is missing or duplicated")
    for item in outputs:
        image = Image.open(GENERATOR / "output" / item["localImage"]).convert("RGB")
        if image.size != size or set(image.getdata()) != {INK, LIME, YELLOW}:
            fail(f"Generated edition {item['id']} has invalid dimensions or palette")
        metadata = json.loads((GENERATOR / "output" / item["metadataFile"]).read_text())
        if metadata["dna"] != item["dna"] or not metadata["attributes"]:
            fail(f"Generated edition {item['id']} metadata mismatch")
    print("status=pass")
    print(f"registeredLayers={len(layer_files)}")
    print(f"testEditions={len(outputs)}")
    print("baseline=512")
    print("alpha=binary")
    print("generation=deterministic-weighted-layer-composite")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        fail(str(exc))
