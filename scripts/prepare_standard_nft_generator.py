#!/usr/bin/env python3
"""Package the registered V2 concepts as a HashLips-style starter layer set."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "trait-expansion-v2"
GENERATOR = REVIEW / "generator"
LAYER_ROOT = GENERATOR / "layers" / "01-complete-character"


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return value or "Trait"


def main() -> None:
    manifest = json.loads((REVIEW / "manifest.json").read_text())
    shutil.rmtree(GENERATOR / "layers", ignore_errors=True)
    LAYER_ROOT.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    for trait in manifest["traits"]:
        source = REVIEW / trait["transparentPreview"]
        filename = f"{trait['code']}__{safe_name(trait['name'])}#1.png"
        destination = LAYER_ROOT / filename
        shutil.copy2(source, destination)
        files.append(destination)

    zip_path = GENERATOR / "neon-nocturne-generator-layers.zip"
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(GENERATOR))
        archive.write(GENERATOR / "config.json", "config.json")
        archive.write(GENERATOR / "README.md", "README.md")

    print(f"Prepared {len(files)} registered generator assets and {zip_path.name}")


if __name__ == "__main__":
    main()
