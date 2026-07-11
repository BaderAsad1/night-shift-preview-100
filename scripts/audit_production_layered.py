#!/usr/bin/env python3
"""Strict pixel, metadata, uniqueness, and mint-capacity audit."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from hashlib import sha256
from pathlib import Path

from PIL import Image


INK = (2, 1, 2, 255)
YELLOW = (253, 244, 35, 255)
EXPECTED_COUNTS = {
    "base": 8,
    "headwear": 30,
    "eyes": 24,
    "mouth": 16,
    "outfit": 30,
    "accessory": 20,
}
PROHIBITED = re.compile(r"cross|crucifix|religious|pentagram|rosary|halo", re.I)


def pixel_hash(image: Image.Image) -> str:
    return sha256(image.convert("RGBA").tobytes()).hexdigest()


def audit(root: Path) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    errors = []
    category_results = {}

    for category, expected in EXPECTED_COUNTS.items():
        files = sorted((root / "traits" / category).glob("*.png"))
        hashes = set()
        for path in files:
            image = Image.open(path).convert("RGBA")
            alpha = image.getchannel("A")
            bbox = alpha.getbbox()
            colors = {pixel for pixel in image.getdata() if pixel[3]}
            if image.size != (1024, 1024):
                errors.append(f"{path.name}: invalid canvas {image.size}")
            if set(alpha.getdata()) - {0, 255}:
                errors.append(f"{path.name}: feathered alpha")
            if colors - {INK, YELLOW}:
                errors.append(f"{path.name}: off-palette pixels")
            if not bbox:
                errors.append(f"{path.name}: empty")
                continue
            if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == 1024:
                errors.append(f"{path.name}: trait clips a top or side canvas edge {bbox}")
            if category == "outfit" and bbox[3] != 1024:
                errors.append(f"{path.name}: outfit misses body baseline {bbox}")
            if category != "outfit" and bbox[3] == 1024:
                errors.append(f"{path.name}: non-outfit clips bottom canvas edge {bbox}")
            digest = pixel_hash(image)
            if digest in hashes:
                errors.append(f"{path.name}: duplicate pixels within {category}")
            hashes.add(digest)
            yellow_count = sum(pixel == YELLOW for pixel in image.getdata())
            if category == "eyes" and yellow_count < 1_000:
                errors.append(f"{path.name}: incomplete #fdf423 eye interior")
            if path.name == "HW02.png" and yellow_count < 50_000:
                errors.append("HW02.png: incomplete #fdf423 Living Flame fill")
        if len(files) != expected:
            errors.append(f"{category}: expected {expected} files, found {len(files)}")
        category_results[category] = {"files": len(files), "uniquePixelHashes": len(hashes)}

    render_files = sorted((root / "renders").glob("*.png"))
    render_hashes = set()
    for path in render_files:
        image = Image.open(path).convert("RGBA")
        alpha = image.getchannel("A")
        bbox = alpha.getbbox()
        if image.size != (1024, 1024):
            errors.append(f"{path.name}: invalid render canvas")
        if set(alpha.getdata()) - {0, 255}:
            errors.append(f"{path.name}: feathered render alpha")
        if {pixel for pixel in image.getdata() if pixel[3]} - {INK, YELLOW}:
            errors.append(f"{path.name}: off-palette render pixels")
        if not bbox or bbox[3] != 1024:
            errors.append(f"{path.name}: render misses body baseline {bbox}")
        if bbox and (bbox[0] < 80 or bbox[2] > 944):
            errors.append(f"{path.name}: render violates horizontal safe area {bbox}")
        digest = pixel_hash(image)
        if digest in render_hashes:
            errors.append(f"{path.name}: duplicate rendered pixels")
        render_hashes.add(digest)

    metadata_files = sorted((root / "metadata").glob("*.json"))
    dna = [tuple(attribute["code"] for attribute in character["dna"]) for character in manifest["characters"]]
    names = [trait["name"] for trait in manifest["traits"]]
    if any(PROHIBITED.search(name) for name in names):
        errors.append("Prohibited religious reference exists in trait names")
    if any(trait["category"].lower() == "background" for trait in manifest["traits"]):
        errors.append("Background trait category exists")
    if len(set(dna)) != len(dna):
        errors.append("Duplicate DNA in preview manifest")
    if len(render_files) != manifest["renderCount"]:
        errors.append("Render count does not match manifest")
    if len(metadata_files) != manifest["renderCount"]:
        errors.append("Metadata count does not match manifest")
    if manifest.get("verifiedUniqueDnaCapacity") != 6_666:
        errors.append("6,666 DNA capacity is not verified")
    if manifest.get("verifiedUniqueRenderCapacity") != 6_666:
        errors.append("6,666 rendered-pixel capacity is not verified")

    report = {
        "status": "pass" if not errors else "fail",
        "traitCount": sum(result["files"] for result in category_results.values()),
        "categories": category_results,
        "renderCount": len(render_files),
        "uniqueRenderHashes": len(render_hashes),
        "metadataCount": len(metadata_files),
        "verifiedUniqueDnaCapacity": manifest.get("verifiedUniqueDnaCapacity"),
        "verifiedUniqueRenderCapacity": manifest.get("verifiedUniqueRenderCapacity"),
        "errors": errors,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("tmp/production-layered"))
    args = parser.parse_args()
    report = audit(args.root)
    print(json.dumps(report, indent=2))
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
