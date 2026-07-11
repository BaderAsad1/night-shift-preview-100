#!/usr/bin/env python3
"""Normalize an individually generated trait to the locked 512→1028 pixel grid."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


INK = (2, 1, 2, 255)
YELLOW = (253, 244, 35, 255)
CLEAR = (0, 0, 0, 0)
LOGICAL_SIZE = 514
FINAL_SIZE = 1028


def keep_largest_component(image: Image.Image) -> Image.Image:
    """Remove detached generation debris while preserving the main trait silhouette."""
    pixels = image.load()
    width, height = image.size
    visited: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y][3] == 0 or (x, y) in visited:
                continue
            stack = [(x, y)]
            visited.add((x, y))
            component: list[tuple[int, int]] = []
            while stack:
                current_x, current_y = stack.pop()
                component.append((current_x, current_y))
                for neighbor_x, neighbor_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if not (0 <= neighbor_x < width and 0 <= neighbor_y < height):
                        continue
                    if (neighbor_x, neighbor_y) in visited:
                        continue
                    if pixels[neighbor_x, neighbor_y][3] == 0:
                        continue
                    visited.add((neighbor_x, neighbor_y))
                    stack.append((neighbor_x, neighbor_y))
            components.append(component)
    if not components:
        return image
    largest = set(max(components, key=len))
    cleaned = Image.new("RGBA", image.size, CLEAR)
    cleaned_pixels = cleaned.load()
    for x, y in largest:
        cleaned_pixels[x, y] = pixels[x, y]
    return cleaned


def normalize(
    source: Path,
    destination: Path,
    allow_yellow: bool,
    largest_component_only: bool,
    target_bbox: tuple[int, int, int, int] | None,
    stretch_bottom_from: int | None,
    clear_boxes: list[tuple[int, int, int, int]],
) -> None:
    source_image = Image.open(source).convert("RGB")
    logical = source_image.resize((LOGICAL_SIZE, LOGICAL_SIZE), Image.Resampling.NEAREST)
    output = Image.new("RGBA", logical.size, CLEAR)
    source_pixels = logical.load()
    output_pixels = output.load()
    for y in range(LOGICAL_SIZE):
        for x in range(LOGICAL_SIZE):
            red, green, blue = source_pixels[x, y]
            if allow_yellow and red > 145 and green > 135 and blue < 125:
                output_pixels[x, y] = YELLOW
            elif max(red, green, blue) < 115:
                output_pixels[x, y] = INK
    if largest_component_only:
        output = keep_largest_component(output)
    if target_bbox:
        if any(value % 2 for value in target_bbox):
            raise ValueError("target bbox coordinates must be even to preserve the 2x grid")
        source_bbox = output.getchannel("A").getbbox()
        if not source_bbox:
            raise ValueError("cannot place an empty trait")
        left, top, right, bottom = (value // 2 for value in target_bbox)
        if right <= left or bottom <= top:
            raise ValueError("target bbox must have positive width and height")
        crop = output.crop(source_bbox).resize(
            (right - left, bottom - top),
            Image.Resampling.NEAREST,
        )
        placed = Image.new("RGBA", output.size, CLEAR)
        placed.alpha_composite(crop, (left, top))
        output = placed
    if stretch_bottom_from is not None:
        if stretch_bottom_from % 2:
            raise ValueError("stretch start must be even to preserve the 2x grid")
        logical_start = stretch_bottom_from // 2
        source_bottom = output.getchannel("A").getbbox()
        if not source_bottom or source_bottom[3] <= logical_start:
            raise ValueError("no artwork exists below the requested stretch start")
        lower = output.crop((0, logical_start, LOGICAL_SIZE, source_bottom[3])).resize(
            (LOGICAL_SIZE, LOGICAL_SIZE - logical_start),
            Image.Resampling.NEAREST,
        )
        stretched = output.copy()
        stretched.paste(CLEAR, (0, logical_start, LOGICAL_SIZE, LOGICAL_SIZE))
        stretched.alpha_composite(lower, (0, logical_start))
        output = stretched
    output = output.resize((FINAL_SIZE, FINAL_SIZE), Image.Resampling.NEAREST)
    output_pixels = output.load()
    for left, top, right, bottom in clear_boxes:
        for y in range(max(0, top), min(FINAL_SIZE, bottom)):
            for x in range(max(0, left), min(FINAL_SIZE, right)):
                output_pixels[x, y] = CLEAR
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.save(destination, optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--yellow", action="store_true")
    parser.add_argument("--largest-component", action="store_true")
    parser.add_argument(
        "--target-bbox",
        metavar="LEFT,TOP,RIGHT,BOTTOM",
        help="Scale and register the reviewed artwork into this final-canvas bbox.",
    )
    parser.add_argument(
        "--stretch-bottom-from",
        type=int,
        help="Vertically stretch artwork below this final-canvas y coordinate to y=1028.",
    )
    parser.add_argument(
        "--clear-box",
        action="append",
        default=[],
        metavar="LEFT,TOP,RIGHT,BOTTOM",
        help="Clear a reviewed final-canvas rectangle; may be supplied repeatedly.",
    )
    arguments = parser.parse_args()
    target_bbox = (
        tuple(int(value) for value in arguments.target_bbox.split(","))
        if arguments.target_bbox
        else None
    )
    if target_bbox and len(target_bbox) != 4:
        parser.error("--target-bbox requires four comma-separated integers")
    clear_boxes = [
        tuple(int(value) for value in box.split(","))
        for box in arguments.clear_box
    ]
    if any(len(box) != 4 for box in clear_boxes):
        parser.error("--clear-box requires four comma-separated integers")
    normalize(
        arguments.source,
        arguments.destination,
        arguments.yellow,
        arguments.largest_component,
        target_bbox,
        arguments.stretch_bottom_from,
        clear_boxes,
    )
