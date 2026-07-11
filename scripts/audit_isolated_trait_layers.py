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
COMPOSED = ROOT / "review" / "trait-expansion-v2" / "composed-layers"
CATEGORIES = (
    "00-base", "01-hair-headwear", "02-eyes", "03-eyewear", "04-mouths",
    "05-clothing", "06-neck-accessories", "07-face-details", "08-rare-overrides",
)
INK = (2, 1, 2)
YELLOW = (253, 244, 35)
PREVIEW_BACKGROUND = (201, 255, 0)


def main() -> None:
    manifest = json.loads((LIBRARY / "manifest.json").read_text())
    assert manifest["count"] == 129
    assert manifest["traitCount"] == 128
    assert manifest["baseCount"] == 1
    assert tuple(manifest["categories"]) == CATEGORIES
    assert len(manifest["layers"]) == 129
    assert len({record["code"] for record in manifest["layers"]}) == 129

    failures: list[str] = []
    expected_all: set[str] = set()
    for category in CATEGORIES:
        files = sorted((LIBRARY / category).glob("*.png"))
        expected_count = 1 if category == "00-base" else 16
        if len(files) != expected_count:
            failures.append(f"{category}: expected {expected_count} PNGs, found {len(files)}")
        expected_category: set[str] = set()
        for path in files:
            image = np.array(Image.open(path).convert("RGBA"), dtype=np.uint8)
            alpha = image[:, :, 3]
            visible = alpha > 0
            colors = {tuple(color) for color in image[:, :, :3][visible]}
            if image.shape != (1028, 1028, 4): failures.append(f"{path.name}: not 1028x1028 RGBA")
            if not np.any(visible): failures.append(f"{path.name}: empty")
            if not set(np.unique(alpha)).issubset({0, 255}): failures.append(f"{path.name}: non-binary alpha")
            if not colors.issubset({INK, YELLOW}): failures.append(f"{path.name}: invalid visible colors {colors}")
            has_yellow = YELLOW in colors
            yellow_allowed = category in {"02-eyes", "08-rare-overrides"} or path.stem == "HH05"
            if has_yellow and not yellow_allowed: failures.append(f"{path.name}: yellow outside approved eye/flame categories")
            if category == "02-eyes" and not has_yellow: failures.append(f"{path.name}: missing approved yellow eye interior")
            if visible[0].any() or visible[:, 0].any() or visible[:, -1].any():
                failures.append(f"{path.name}: artwork touches top or side canvas edge")
            blocks = image.reshape(514, 2, 514, 2, 4).transpose(0, 2, 1, 3, 4)
            if np.any(blocks != blocks[:, :, :1, :1, :]):
                failures.append(f"{path.name}: contains pixels off the exact 2x logical grid")
            if category in {"00-base", "05-clothing", "08-rare-overrides"} and not visible[-1].any():
                failures.append(f"{path.name}: body-bearing layer does not terminate at row 1027")
            archive_name = f"{category}/{path.name}"
            expected_all.add(archive_name)
            expected_category.add(path.name)

        category_zip = LIBRARY / f"neon-nocturne-{category}-layers.zip"
        with ZipFile(category_zip) as archive:
            archived_category = {f"{category}/{name}" for name in expected_category}
            if set(archive.namelist()) != archived_category:
                failures.append(f"{category_zip.name}: contents do not match category PNGs")

    with ZipFile(LIBRARY / "neon-nocturne-all-129-generator-layers.zip") as archive:
        if set(archive.namelist()) != expected_all:
            failures.append("all-129 ZIP contents do not match categorized PNGs")

    composed_files = sorted(COMPOSED.glob("*/*.png"))
    if len(composed_files) != 129:
        failures.append(f"composed QA: expected 129 previews, found {len(composed_files)}")
    for path in composed_files:
        image = np.array(Image.open(path).convert("RGB"), dtype=np.uint8)
        colors = {tuple(color) for color in image.reshape(-1, 3)}
        if image.shape != (1028, 1028, 3): failures.append(f"{path.name} composed preview is not 1028x1028")
        if not colors.issubset({INK, YELLOW, PREVIEW_BACKGROUND}): failures.append(f"{path.name} composed preview has invalid colors")
        # Some outline garments leave lime gaps at the baseline; require at
        # least one ink pixel rather than a solid baseline.
        if not np.any(np.all(image[-1] == np.array(INK), axis=1)):
            failures.append(f"{path.name} composed character does not reach row 1027")

    if failures:
        raise SystemExit("Isolated layer audit failed:\n- " + "\n- ".join(failures))
    print("Generator layer audit passed: 129/129 PNGs (1 base + 128 traits), 9/9 categories, palette/alpha/ZIP checks clean")


if __name__ == "__main__":
    main()
