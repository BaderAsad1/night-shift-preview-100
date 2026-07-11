#!/usr/bin/env python3
"""Build normalized Neon Nocturne masters and transparent component downloads."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from shutil import copytree, rmtree
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageChops, ImageDraw

from build_neon_nocturne import (
    ARCHETYPES,
    TRAIT_SOURCE_DIR,
    build_portrait_trait_sources,
)


ROOT = Path(__file__).resolve().parents[1]
CATEGORY_DIRS = {
    "Silhouette / Headwear": "headwear",
    "Eyes": "eyes",
    "Outfit": "outfits",
    "Master Archetype": "masters",
}


def isolated(image: Image.Image, mask: Image.Image) -> Image.Image:
    result = image.copy()
    result.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
    return result


def remove_unrelated_fragments(image: Image.Image, minimum_pixels: int = 220) -> Image.Image:
    """Remove tiny black crop remnants while preserving yellow flame sparks."""
    alpha = image.getchannel("A")
    pixels = alpha.load()
    source = image.load()
    seen = set()
    keep = Image.new("L", image.size, 0)
    keep_pixels = keep.load()
    for y in range(image.height):
        for x in range(image.width):
            if not pixels[x, y] or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            component = []
            contains_yellow = False
            while queue:
                cx, cy = queue.popleft()
                component.append((cx, cy))
                contains_yellow |= source[cx, cy][:3] == (253, 244, 35)
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if (0 <= nx < image.width and 0 <= ny < image.height
                            and pixels[nx, ny] and (nx, ny) not in seen):
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            xs = [point[0] for point in component]
            ys = [point[1] for point in component]
            is_far_outfit_remnant = min(xs) > 800 and min(ys) > 600 and not contains_yellow
            if not is_far_outfit_remnant and (len(component) >= minimum_pixels or contains_yellow):
                for px, py in component:
                    keep_pixels[px, py] = 255
    return isolated(image, keep)


def remove_yellow_components(image: Image.Image) -> Image.Image:
    """Drop flame/eye components from outfit-only exports."""
    alpha = image.getchannel("A")
    pixels = alpha.load()
    source = image.load()
    seen = set()
    keep = Image.new("L", image.size, 0)
    keep_pixels = keep.load()
    for y in range(image.height):
        for x in range(image.width):
            if not pixels[x, y] or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            component = []
            contains_yellow = False
            while queue:
                cx, cy = queue.popleft()
                component.append((cx, cy))
                contains_yellow |= source[cx, cy][:3] == (253, 244, 35)
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if (0 <= nx < image.width and 0 <= ny < image.height
                            and pixels[nx, ny] and (nx, ny) not in seen):
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            if not contains_yellow:
                for px, py in component:
                    keep_pixels[px, py] = 255
    return isolated(image, keep)


def component_images(
    master: Image.Image,
    eye_boxes: tuple[tuple[int, int, int, int], tuple[int, int, int, int]],
) -> dict[str, Image.Image]:
    """Extract full-canvas component references without scaling or feathering."""
    width, height = master.size
    eye_top = min(box[1] for box in eye_boxes)
    eye_bottom = max(box[3] for box in eye_boxes)
    eye_left = min(box[0] for box in eye_boxes)
    eye_right = max(box[2] for box in eye_boxes)
    face_center = (eye_left + eye_right) // 2

    eyes_mask = Image.new("L", master.size, 0)
    eyes_core = Image.new("L", master.size, 0)
    eye_draw = ImageDraw.Draw(eyes_mask)
    eye_core_draw = ImageDraw.Draw(eyes_core)
    for x0, y0, x1, y1 in eye_boxes:
        eye_draw.rectangle((x0 - 22, y0 - 28, x1 + 22, y1 + 28), fill=255)
        eye_core_draw.rectangle((x0, y0, x1, y1), fill=255)

    # Headwear keeps everything above the brow line plus side silhouette work.
    # A face-shaped cutout removes eyes, nose, and mouth without a horizontal
    # crop through side hair, ears, hats, flames, horns, or helmets.
    headwear_mask = Image.new("L", master.size, 0)
    headwear_draw = ImageDraw.Draw(headwear_mask)
    headwear_draw.rectangle((0, 0, width, eye_top + 18), fill=255)
    headwear_draw.rectangle((0, eye_top + 18, width, eye_bottom + 100), fill=255)
    headwear_draw.ellipse(
        (eye_left - 78, eye_top - 10, eye_right + 78, eye_bottom + 205),
        fill=0,
    )

    # The outfit begins below the face on one clean source-aligned row. This
    # intentionally excludes hair, aura, eyes, and facial ink from the file.
    outfit_mask = Image.new("L", master.size, 0)
    outfit_draw = ImageDraw.Draw(outfit_mask)
    shoulder_y = min(height, eye_bottom + 118)
    outfit_draw.rectangle((0, shoulder_y, width, height), fill=255)

    eyes_image = isolated(master, eyes_mask)
    yellow_pixels = Image.new("L", master.size, 0)
    yellow_data = yellow_pixels.load()
    source_data = master.load()
    for y in range(height):
        for x in range(width):
            if source_data[x, y][:3] == (253, 244, 35) and source_data[x, y][3] == 255:
                yellow_data[x, y] = 255
    yellow_outside_core = ImageChops.subtract(yellow_pixels, eyes_core)
    eyes_image.putalpha(ImageChops.subtract(eyes_image.getchannel("A"), yellow_outside_core))

    return {
        "Silhouette / Headwear": remove_unrelated_fragments(isolated(master, headwear_mask), 500),
        "Eyes": eyes_image,
        "Outfit": remove_yellow_components(isolated(master, outfit_mask)),
        "Master Archetype": master.copy(),
    }


def validate_component(image: Image.Image, code: str) -> None:
    alpha = image.getchannel("A")
    if image.size != (1024, 1024) or not alpha.getbbox():
        raise ValueError(f"{code} is empty or incorrectly sized")
    if set(alpha.getdata()) - {0, 255}:
        raise ValueError(f"{code} contains feathered alpha")
    opaque = sum(value == 255 for value in alpha.getdata())
    if opaque < 500:
        raise ValueError(f"{code} contains too little trait artwork: {opaque} pixels")


def write_zip(path: Path, files: list[tuple[Path, str]]) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for source, archive_name in files:
            archive.write(source, archive_name)


def build_download_library(
    normalized_eye_boxes: list[tuple[tuple[int, int, int, int], tuple[int, int, int, int]]],
) -> None:
    records = []
    destination = ROOT / "public" / "traits"
    if destination.exists():
        rmtree(destination)
    destination.mkdir(parents=True)
    output_files: list[tuple[Path, str]] = []
    category_files: dict[str, list[tuple[Path, str]]] = {
        folder: [] for folder in CATEGORY_DIRS.values()
    }

    for index, (archetype, silhouette, eyes, outfit) in enumerate(ARCHETYPES):
        number = index + 1
        master = Image.open(TRAIT_SOURCE_DIR / f"AR{number:02d}.png").convert("RGBA")
        images = component_images(master, normalized_eye_boxes[index])
        definitions = (
            ("Silhouette / Headwear", f"SH{number:02d}", silhouette),
            ("Eyes", f"EY{number:02d}", eyes),
            ("Outfit", f"OF{number:02d}", outfit),
            ("Master Archetype", f"AR{number:02d}", archetype),
        )
        for category, code, name in definitions:
            folder = CATEGORY_DIRS[category]
            folder_path = destination / folder
            folder_path.mkdir(exist_ok=True)
            output = folder_path / f"{code}.png"
            image = images[category]
            validate_component(image, code)
            image.save(output, optimize=True)
            archive_name = f"{folder}/{code}.png"
            output_files.append((output, archive_name))
            category_files[folder].append((output, f"{code}.png"))
            records.append({
                "category": category,
                "folder": folder,
                "code": code,
                "name": name,
                "file": f"traits/{archive_name}",
            })

    component_files = [item for item in output_files if not item[1].startswith("masters/")]
    write_zip(destination / "night-shift-108-component-traits-transparent.zip", component_files)
    write_zip(destination / "night-shift-144-trait-library-transparent.zip", output_files)
    for folder, files in category_files.items():
        write_zip(destination / f"night-shift-{folder}-36-transparent.zip", files)

    manifest = {
        "componentTraitCount": 108,
        "masterCount": 36,
        "totalFileCount": 144,
        "format": "1024x1024 RGBA PNG",
        "background": "transparent",
        "traits": records,
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    docs_destination = ROOT / "docs" / "traits"
    if docs_destination.exists():
        rmtree(docs_destination)
    copytree(destination, docs_destination)


if __name__ == "__main__":
    boxes = build_portrait_trait_sources(TRAIT_SOURCE_DIR)
    build_download_library(boxes)
    print("Built 108 transparent component traits plus 36 normalized masters")
