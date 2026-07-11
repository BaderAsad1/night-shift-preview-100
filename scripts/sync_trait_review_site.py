#!/usr/bin/env python3
"""Copy the validated V2 review surface into public assets for hosting."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "review" / "trait-expansion-v2"
DESTINATIONS = (
    ROOT / "public" / "review" / "trait-expansion-v2",
    ROOT / "docs" / "review" / "trait-expansion-v2",
)


def copy_item(relative: str, destination_root: Path) -> None:
    source = SOURCE / relative
    destination = destination_root / relative
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main() -> None:
    for destination in DESTINATIONS:
        shutil.rmtree(destination, ignore_errors=True)
        destination.mkdir(parents=True)
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
            copy_item(item, destination)
        print(f"Synced hosted review assets to {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
