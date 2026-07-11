#!/usr/bin/env python3
"""Build reusable, normalized Neon Nocturne portrait trait assets."""

from pathlib import Path
from shutil import copy2
from zipfile import ZIP_DEFLATED, ZipFile

from build_neon_nocturne import TRAIT_SOURCE_DIR, build_portrait_trait_sources


ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_NAME = "night-shift-neon-nocturne-traits-transparent.zip"


def build_download_libraries() -> None:
    """Publish transparent source traits individually and as one batch archive."""
    source_files = sorted(TRAIT_SOURCE_DIR.glob("AR*.png"))
    if len(source_files) != 36:
        raise ValueError(f"Expected 36 trait sources, found {len(source_files)}")
    for destination in (ROOT / "public" / "traits", ROOT / "docs" / "traits"):
        destination.mkdir(parents=True, exist_ok=True)
        for stale in destination.glob("AR*.png"):
            stale.unlink()
        for source in source_files:
            copy2(source, destination / source.name)
        with ZipFile(destination / DOWNLOAD_NAME, "w", ZIP_DEFLATED) as archive:
            for source in source_files:
                archive.write(source, source.name)


if __name__ == "__main__":
    build_portrait_trait_sources(TRAIT_SOURCE_DIR)
    build_download_libraries()
    print(f"Built 36 normalized portrait traits and transparent downloads in {TRAIT_SOURCE_DIR}")
