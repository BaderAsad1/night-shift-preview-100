#!/usr/bin/env python3
"""Deterministic weighted layered NFT generator.

The folder order, full-canvas transparent PNGs, filename rarity weights,
uniqueness DNA, and metadata output follow the conventional HashLips model.
No layer is scaled or moved during generation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "review" / "trait-expansion-v2" / "generator"


@dataclass(frozen=True)
class Element:
    path: Path
    code: str
    value: str
    weight: float


def parse_element(path: Path, delimiter: str) -> Element:
    stem = path.stem
    label, raw_weight = stem.rsplit(delimiter, 1) if delimiter in stem else (stem, "1")
    try:
        weight = float(raw_weight)
    except ValueError as exc:
        raise ValueError(f"Invalid rarity weight in {path.name}") from exc
    if weight <= 0:
        raise ValueError(f"Rarity weight must be positive in {path.name}")
    code, value = label.split("__", 1) if "__" in label else (label, label)
    return Element(path, code, value.replace("_", " "), weight)


def weighted_choice(rng: random.Random, elements: list[Element]) -> Element:
    return rng.choices(elements, weights=[element.weight for element in elements], k=1)[0]


def clean_layer_name(folder: str) -> str:
    name = folder.split("-", 1)[1] if "-" in folder and folder.split("-", 1)[0].isdigit() else folder
    return name.replace("-", " ").title()


def code_matches(code: str, allowed: list[str]) -> bool:
    return ("*" in allowed and code != "NONE") or code in allowed


def selection_is_compatible(selection: list[tuple[str, Element]], rules: list[dict]) -> bool:
    chosen = {name: element.code for name, element in selection}
    for rule in rules:
        if (
            code_matches(chosen.get(rule["ifLayer"], "NONE"), rule["ifCodes"])
            and code_matches(chosen.get(rule["withLayer"], "NONE"), rule["withCodes"])
        ):
            return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--count", type=int)
    args = parser.parse_args()

    generator_root = args.root.resolve()
    config = json.loads((generator_root / "config.json").read_text())
    width, height = config["canvas"]
    configuration = config["layerConfigurations"][0]
    count = args.count or configuration.get("growEditionSizeTo", config["editionSize"])
    delimiter = config.get("rarityDelimiter", "#")
    rng = random.Random(config["seed"])

    layer_folders = [generator_root / "layers" / name for name in configuration["layersOrder"]]
    if not layer_folders:
        raise ValueError("No layer folders found")
    if any(not path.is_dir() for path in layer_folders):
        missing = [path.name for path in layer_folders if not path.is_dir()]
        raise ValueError(f"Configured layer folders are missing: {missing}")
    layers = [
        (clean_layer_name(folder.name), [parse_element(path, delimiter) for path in sorted(folder.glob("*.png"))])
        for folder in layer_folders
    ]
    if any(not elements for _, elements in layers):
        raise ValueError("Every layer folder must contain at least one PNG")

    max_combinations = 1
    for _, elements in layers:
        max_combinations *= len(elements)
    if count > max_combinations:
        raise ValueError(f"Requested {count} unique outputs but only {max_combinations} combinations exist")

    output = generator_root / "output"
    images_root = output / "images"
    metadata_root = output / "json"
    shutil.rmtree(output, ignore_errors=True)
    images_root.mkdir(parents=True)
    metadata_root.mkdir(parents=True)

    used: set[str] = set()
    records = []
    attempts = 0
    while len(records) < count:
        attempts += 1
        if attempts > count * 1000:
            raise RuntimeError("Could not find enough unique DNA combinations")
        selection = [(name, weighted_choice(rng, elements)) for name, elements in layers]
        if not selection_is_compatible(selection, config.get("incompatibilities", [])):
            continue
        signature = "|".join(f"{name}:{element.path.name}" for name, element in selection)
        dna = hashlib.sha256(signature.encode()).hexdigest()
        if dna in used:
            continue
        used.add(dna)

        canvas = Image.new("RGBA", (width, height), (*ImageColor(config["background"]), 255))
        for _, element in selection:
            layer = Image.open(element.path).convert("RGBA")
            if layer.size != (width, height):
                raise ValueError(f"{element.path.name} is {layer.size}; expected {(width, height)}")
            canvas.alpha_composite(layer)

        edition = len(records) + 1
        image_name = f"{edition:04d}.png"
        canvas.convert("RGB").save(images_root / image_name, optimize=True)
        attributes = [
            {"trait_type": name, "value": element.value, "code": element.code}
            for name, element in selection
        ]
        metadata = {
            "name": f"{config['namePrefix']} #{edition}",
            "description": config["description"],
            "image": f"{config['baseUri'].rstrip('/')}/{image_name}",
            "dna": dna,
            "edition": edition,
            "attributes": attributes,
            "compiler": "Night Shift Layer Generator 1.0",
        }
        (metadata_root / f"{edition:04d}.json").write_text(json.dumps(metadata, indent=2) + "\n")
        records.append({
            "id": edition,
            "localImage": f"images/{image_name}",
            "metadataFile": f"json/{edition:04d}.json",
            **metadata,
        })

    (output / "_metadata.json").write_text(json.dumps(records, indent=2) + "\n")
    manifest = {
        "generator": "standard-layered",
        "hashLipsCompatibleStructure": True,
        "seed": config["seed"],
        "count": count,
        "maximumUniqueCombinations": max_combinations,
        "layerCount": len(layers),
        "layers": [{"name": name, "elementCount": len(elements)} for name, elements in layers],
        "outputs": records,
        "readiness": "individual-layer-test",
        "limitation": "Rare full-character overrides are reviewed separately and are excluded from normal mixed combinations.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "manifest.js").write_text("window.NFT_GENERATOR_TEST = " + json.dumps(manifest, indent=2) + ";\n")
    print(f"Generated {count} deterministic unique test editions from {len(layers)} ordered layer folders")


def ImageColor(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Invalid background color: {value}")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


if __name__ == "__main__":
    main()
