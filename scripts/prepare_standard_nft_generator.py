#!/usr/bin/env python3
"""Package the approved individual V2 layers in HashLips-style folders."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "trait-expansion-v2"
LIBRARY = REVIEW / "isolated-layers"
GENERATOR = REVIEW / "generator"
ORDER = (
    ("00-clothing", "05-clothing", False),
    ("01-base", "00-base", False),
    ("02-hair-headwear", "01-hair-headwear", False),
    ("03-eyes", "02-eyes", False),
    ("04-mouths", "04-mouths", False),
    ("05-eyewear", "03-eyewear", True),
    ("06-neck-accessories", "06-neck-accessories", True),
    ("07-face-details", "07-face-details", True),
)


def safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_") or "Layer"


def zip_files(path: Path, files: list[Path]) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for source in files:
            info = ZipInfo(str(source.relative_to(GENERATOR)), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED; info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
        for name in ("config.json", "README.md"):
            source = GENERATOR / name; info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)); info.compress_type = ZIP_DEFLATED; info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main() -> None:
    manifest = json.loads((LIBRARY / "manifest.json").read_text())
    records = {record["code"]: record for record in manifest["layers"]}
    layers_root = GENERATOR / "layers"; shutil.rmtree(layers_root, ignore_errors=True); layers_root.mkdir(parents=True)
    files = []
    for output_folder, source_folder, optional in ORDER:
        destination = layers_root / output_folder; destination.mkdir()
        for source in sorted((LIBRARY / source_folder).glob("*.png")):
            record = records[source.stem]
            target = destination / f"{record['code']}__{safe(record['name'])}#1.png"
            shutil.copy2(source, target); files.append(target)
        if optional:
            none = destination / "NONE__None#12.png"
            Image.new("RGBA", (1028, 1028), (0, 0, 0, 0)).save(none, optimize=True); files.append(none)
    zip_files(GENERATOR / "neon-nocturne-generator-layers.zip", files)
    print(f"Prepared {len(files)} individual generator inputs across {len(ORDER)} ordered folders")


if __name__ == "__main__": main()
