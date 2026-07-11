#!/usr/bin/env python3
"""Package the reviewed 129-file trait library for review and generation."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "trait-expansion-v2"
SOURCE = ROOT / "review" / "trait-layers-final"
DESTINATION = REVIEW / "isolated-layers"
COMPOSED = REVIEW / "composed-layers"
CONCEPT_MANIFEST = REVIEW / "manifest.json"
CANVAS = (1028, 1028)
BACKGROUND = (201, 255, 0, 255)

CATEGORIES = (
    ("00-base", "Base"),
    ("01-hair-headwear", "Hair + Headwear"),
    ("02-eyes", "Eyes"),
    ("03-eyewear", "Eyewear"),
    ("04-mouths", "Mouths"),
    ("05-clothing", "Clothing"),
    ("06-neck-accessories", "Neck Accessories"),
    ("07-face-details", "Face Details"),
    ("08-rare-overrides", "Rare Overrides"),
)


def deterministic_zip(path: Path, members: list[Path]) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for source in sorted(members):
            relative = source.relative_to(DESTINATION)
            info = ZipInfo(str(relative), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def composite(paths: list[Path], destination: Path) -> None:
    canvas = Image.new("RGBA", CANVAS, BACKGROUND)
    for path in paths:
        with Image.open(path) as layer:
            canvas.alpha_composite(layer.convert("RGBA"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, optimize=True)


def default_layers() -> dict[str, Path]:
    return {
        "base": SOURCE / "00-base" / "BA01.png",
        "hair": SOURCE / "01-hair-headwear" / "HH01.png",
        "eyes": SOURCE / "02-eyes" / "EY01.png",
        "mouth": SOURCE / "04-mouths" / "MO01.png",
        "clothing": SOURCE / "05-clothing" / "OF01.png",
    }


def preview_stack(category: str, layer: Path) -> list[Path]:
    d = default_layers()
    if category == "00-base":
        return [layer, d["clothing"], d["hair"], d["eyes"], d["mouth"]]
    if category == "01-hair-headwear":
        return [d["base"], d["clothing"], layer, d["eyes"], d["mouth"]]
    if category == "02-eyes":
        return [d["base"], d["clothing"], d["hair"], layer, d["mouth"]]
    if category == "03-eyewear":
        return [d["base"], d["clothing"], d["hair"], d["eyes"], d["mouth"], layer]
    if category == "04-mouths":
        return [d["base"], d["clothing"], d["hair"], d["eyes"], layer]
    if category == "05-clothing":
        return [d["base"], layer, d["hair"], d["eyes"], d["mouth"]]
    if category == "06-neck-accessories":
        return [d["base"], d["hair"], d["eyes"], d["mouth"], layer]
    if category == "07-face-details":
        return [d["base"], d["hair"], d["eyes"], d["mouth"], layer]
    if category == "08-rare-overrides":
        return [layer]
    raise ValueError(category)


def main() -> None:
    concept = json.loads(CONCEPT_MANIFEST.read_text())
    names = {item["code"]: item["name"] for item in concept["traits"]}
    names["BA01"] = "Locked Vampire Base"

    shutil.rmtree(DESTINATION, ignore_errors=True)
    shutil.rmtree(COMPOSED, ignore_errors=True)
    DESTINATION.mkdir(parents=True)
    COMPOSED.mkdir(parents=True)

    records: list[dict] = []
    category_files: dict[str, list[Path]] = {}
    for category, category_label in CATEGORIES:
        sources = sorted((SOURCE / category).glob("*.png"))
        if not sources:
            raise SystemExit(f"No final layers found in {category}")
        output_folder = DESTINATION / category
        reference_folder = COMPOSED / category
        output_folder.mkdir()
        reference_folder.mkdir()
        category_files[category] = []
        for source in sources:
            destination = output_folder / source.name
            shutil.copy2(source, destination)
            reference = reference_folder / source.name
            composite(preview_stack(category, source), reference)
            category_files[category].append(destination)
            records.append({
                "code": source.stem,
                "name": names.get(source.stem, source.stem),
                "category": category,
                "categoryLabel": category_label,
                "layer": f"isolated-layers/{category}/{source.name}",
                "referenceCard": f"composed-layers/{category}/{source.name}",
                "canvas": list(CANVAS),
                "background": "transparent",
                "bodyBaselineY": 1028 if category in {"00-base", "05-clothing", "08-rare-overrides"} else None,
                "resampling": "nearest",
                "status": "reviewed-final",
            })

    all_files = [path for paths in category_files.values() for path in paths]
    deterministic_zip(DESTINATION / "neon-nocturne-all-129-generator-layers.zip", all_files)
    for category, _ in CATEGORIES:
        deterministic_zip(DESTINATION / f"neon-nocturne-{category}-layers.zip", category_files[category])

    manifest = {
        "collection": "Neon Nocturne",
        "format": "registered-transparent-png-layers",
        "canvas": list(CANVAS),
        "count": len(records),
        "baseCount": 1,
        "traitCount": len(records) - 1,
        "categories": [category for category, _ in CATEGORIES],
        "registration": "shared 1028x1028 canvas; no runtime movement or scaling",
        "sourceMethod": "individually authored and normalized final layers",
        "layers": records,
    }
    (DESTINATION / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (DESTINATION / "manifest.js").write_text(
        "window.ISOLATED_TRAIT_MANIFEST = " + json.dumps(manifest, indent=2) + ";\n"
    )
    print(f"Packaged {len(records)} reviewed layers, references, and 10 deterministic ZIP archives")


if __name__ == "__main__":
    main()
