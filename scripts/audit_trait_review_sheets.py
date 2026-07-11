#!/usr/bin/env python3
"""Strict mechanical audit for the Neon Nocturne V2 concept sheets."""

from __future__ import annotations

import re
import json
import sys
from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "trait-expansion-v2"
EXPECTED = [
    "01-hair-headwear.png",
    "02-eyes.png",
    "03-eyewear.png",
    "04-mouths.png",
    "05-outfits.png",
    "06-neck.png",
    "07-rare.png",
    "08-face-details.png",
]
PALETTE = {(2, 1, 2), (208, 247, 8), (253, 244, 35)}
INK = (2, 1, 2)
YELLOW = (253, 244, 35)
CANVAS = 512


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def audit_sheet(path: Path) -> tuple[int, int]:
    image = Image.open(path).convert("RGB")
    if image.size != (1254, 1254):
        fail(f"{path.name} has size {image.size}, expected 1254x1254")
    colors = set(image.getdata())
    if colors != PALETTE:
        fail(f"{path.name} palette mismatch: {sorted(colors)}")
    mask_path = REVIEW / "yellow-masks" / path.name
    if not mask_path.exists():
        fail(f"{path.name} is missing its approved eye/flame yellow mask")
    approved_yellow = Image.open(mask_path).convert("1")
    if approved_yellow.size != image.size:
        fail(f"{path.name} yellow mask size mismatch")
    approved_pixels = approved_yellow.load()
    image_pixels = image.load()
    unauthorized_yellow = sum(
        image_pixels[x, y] == YELLOW and not approved_pixels[x, y]
        for y in range(image.height)
        for x in range(image.width)
    )
    if unauthorized_yellow:
        fail(f"{path.name} has {unauthorized_yellow} yellow pixels outside approved eyes/flames")

    width, height = image.size
    pixels = image.load()
    grid_top = round(height * 0.052)
    cell_width = width / 4
    cell_height = (height - grid_top) / 4
    minimum_ink = 10**9
    minimum_yellow = 10**9
    for row in range(4):
        for column in range(4):
            x0 = round(column * cell_width)
            x1 = round((column + 1) * cell_width)
            y0 = round(grid_top + row * cell_height)
            y1 = round(grid_top + (row + 1) * cell_height)
            ink = 0
            yellow = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    if pixels[x, y] == INK:
                        ink += 1
                    elif pixels[x, y] == YELLOW:
                        yellow += 1
            minimum_ink = min(minimum_ink, ink)
            minimum_yellow = min(minimum_yellow, yellow)
            if ink < 1800:
                fail(f"{path.name} cell {row * 4 + column + 1:02d} is empty or incomplete ({ink} ink pixels)")
            if yellow < 24:
                fail(f"{path.name} cell {row * 4 + column + 1:02d} lacks approved yellow ({yellow} pixels)")
    return minimum_ink, minimum_yellow


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


def main() -> None:
    files = sorted(path.name for path in REVIEW.glob("*.png"))
    if files != EXPECTED:
        fail(f"sheet set mismatch: {files}")
    readme = (REVIEW / "README.md").read_text()
    entries = re.findall(r"\|\s*(\d{2})\s*\|\s*([^|\n]+)", readme)
    if len(entries) != 128:
        fail(f"README maps {len(entries)} traits, expected 128")
    names = [name.strip().lower() for _, name in entries]
    prohibited = re.compile(r"cross|crucifix|religious|pentagram|grid|graph|scan line")
    offenders = [name for name in names if prohibited.search(name)]
    if offenders:
        fail(f"prohibited trait names: {offenders}")

    print("status=pass")
    print("traitConcepts=128")
    for filename in EXPECTED:
        minimum_ink, minimum_yellow = audit_sheet(REVIEW / filename)
        print(f"{filename}: cells=16 palette=3 minInk={minimum_ink} minYellow={minimum_yellow}")

    manifest = json.loads((REVIEW / "manifest.json").read_text())
    if manifest.get("conceptCount") != 128 or manifest.get("productionLayerCount") != 0:
        fail("manifest must describe 128 concepts and zero production layers")
    traits = manifest.get("traits", [])
    if len(traits) != 128 or len({trait["code"] for trait in traits}) != 128:
        fail("manifest trait records are missing or duplicated")
    for trait in traits:
        for key in ("card", "transparentPreview", "sourceCard"):
            path = REVIEW / trait[key]
            if not path.exists():
                fail(f"missing {key} for {trait['code']}: {path}")
        card = Image.open(REVIEW / trait["card"]).convert("RGB")
        source = Image.open(REVIEW / trait["sourceCard"]).convert("RGB")
        if card.size != (512, 512) or source.size != (512, 512):
            fail(f"{trait['code']} review/source card is not 512x512")
        if set(card.getdata()) != PALETTE or set(source.getdata()) != PALETTE:
            fail(f"{trait['code']} card palette mismatch")
        transparent = Image.open(REVIEW / trait["transparentPreview"]).convert("RGBA")
        if transparent.size != (512, 512):
            fail(f"{trait['code']} transparent preview is not 512x512")
        alpha_values = {pixel[3] for pixel in transparent.getdata()}
        visible_colors = {pixel[:3] for pixel in transparent.getdata() if pixel[3]}
        if alpha_values != {0, 255} or visible_colors != {INK, YELLOW}:
            fail(f"{trait['code']} transparent preview alpha/palette mismatch")
        components = alpha_components(transparent.getchannel("A"))
        if not components:
            fail(f"{trait['code']} has no visible character")
        main_bottom = max(y for _, y in components[0])
        if main_bottom != CANVAS - 1:
            fail(f"{trait['code']} body baseline is y={main_bottom}, expected {CANVAS - 1}")
        detached_below = [
            component
            for component in components[1:]
            if min(y for _, y in component) > main_bottom
        ]
        if detached_below:
            fail(f"{trait['code']} has detached artwork below the character")
        edge_pixels = [
            (x, y)
            for x, y in components[0]
            if x in (0, CANVAS - 1)
        ]
        if edge_pixels:
            fail(f"{trait['code']} main character is clipped at a horizontal edge")
        registration = trait.get("registration", {})
        if registration.get("bodyBaselineY") != CANVAS:
            fail(f"{trait['code']} is missing baseline registration metadata")
    print("reviewCards=128")
    print("sourceCards=128")
    print("transparentPreviews=128")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
