#!/usr/bin/env python3
"""Mechanical QA for the categorized transparent V2 trait-layer library."""

from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "review" / "trait-expansion-v2" / "isolated-layers"
CATEGORIES = (
    "hair-headwear", "eyes", "eyewear", "mouths",
    "outfits", "neck", "face-details", "rare",
)
INK = (2, 1, 2)
YELLOW = (253, 244, 35)


def main() -> None:
    manifest = json.loads((LIBRARY / "manifest.json").read_text())
    assert manifest["count"] == 128
    assert tuple(manifest["categories"]) == CATEGORIES
    assert len(manifest["layers"]) == 128
    assert len({record["code"] for record in manifest["layers"]}) == 128

    failures: list[str] = []
    expected_all: set[str] = set()
    for category in CATEGORIES:
        files = sorted((LIBRARY / category).glob("*.png"))
        if len(files) != 16:
            failures.append(f"{category}: expected 16 PNGs, found {len(files)}")
        expected_category: set[str] = set()
        for path in files:
            image = np.array(Image.open(path).convert("RGBA"), dtype=np.uint8)
            alpha = image[:, :, 3]
            visible = alpha > 0
            colors = {tuple(color) for color in image[:, :, :3][visible]}
            if image.shape != (512, 512, 4): failures.append(f"{path.name}: not 512x512 RGBA")
            if not np.any(visible): failures.append(f"{path.name}: empty")
            if not set(np.unique(alpha)).issubset({0, 255}): failures.append(f"{path.name}: non-binary alpha")
            if not colors.issubset({INK, YELLOW}): failures.append(f"{path.name}: invalid visible colors {colors}")
            has_yellow = YELLOW in colors
            yellow_allowed = category in {"eyes", "rare"} or path.stem == "HH05"
            if has_yellow and not yellow_allowed: failures.append(f"{path.name}: yellow outside approved eye/flame categories")
            if category == "eyes" and not has_yellow: failures.append(f"{path.name}: missing approved yellow eye interior")
            if category not in {"outfits", "rare"}:
                edge = visible[0].any() or visible[-1].any() or visible[:, 0].any() or visible[:, -1].any()
                if edge: failures.append(f"{path.name}: artwork touches canvas edge")
            archive_name = f"{category}/{path.name}"
            expected_all.add(archive_name)
            expected_category.add(path.name)

        category_zip = LIBRARY / f"neon-nocturne-{category}-layers.zip"
        with ZipFile(category_zip) as archive:
            if set(archive.namelist()) != expected_category:
                failures.append(f"{category_zip.name}: contents do not match category PNGs")

    with ZipFile(LIBRARY / "neon-nocturne-all-128-isolated-layers.zip") as archive:
        if set(archive.namelist()) != expected_all:
            failures.append("all-128 ZIP contents do not match categorized PNGs")

    if failures:
        raise SystemExit("Isolated layer audit failed:\n- " + "\n- ".join(failures))
    print("Isolated layer audit passed: 128/128 PNGs, 8/8 categories, palette/alpha/ZIP checks clean")


if __name__ == "__main__":
    main()
