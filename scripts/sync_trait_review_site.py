#!/usr/bin/env python3
"""Copy the validated V2 review surface into public assets for hosting."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "review" / "trait-expansion-v2"
DESTINATION = ROOT / "public" / "review" / "trait-expansion-v2"


def copy_item(relative: str) -> None:
    source = SOURCE / relative
    destination = DESTINATION / relative
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main() -> None:
    shutil.rmtree(DESTINATION, ignore_errors=True)
    DESTINATION.mkdir(parents=True)
    for item in (
        "index.html",
        "review.css",
        "review.js",
        "manifest.js",
        "manifest.json",
        "cards",
        "cards-transparent",
        "isolated-layers",
        "generator/output",
        "generator/config.json",
        "generator/README.md",
        "generator/neon-nocturne-generator-layers.zip",
    ):
        copy_item(item)
    print(f"Synced hosted review assets to {DESTINATION.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
