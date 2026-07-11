#!/usr/bin/env python3
"""Audit the real individual-layer 1028px NFT generator test."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "review" / "trait-expansion-v2" / "generator"
INK = (2, 1, 2); LIME = (208, 247, 8); YELLOW = (253, 244, 35)
EXPECTED = [16, 1, 16, 16, 16, 17, 17, 17]


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    config = json.loads((GENERATOR / "config.json").read_text())
    size = tuple(config["canvas"])
    if size != (1028, 1028): fail(f"canvas is {size}, expected 1028x1028")
    folders = [GENERATOR / "layers" / name for name in config["layerConfigurations"][0]["layersOrder"]]
    counts = [len(list(folder.glob("*.png"))) for folder in folders]
    if counts != EXPECTED: fail(f"generator folder counts are {counts}, expected {EXPECTED}")
    for folder in folders:
        for path in folder.glob("*.png"):
            image = np.array(Image.open(path).convert("RGBA"), dtype=np.uint8)
            if image.shape != (1028, 1028, 4): fail(f"{path.name} has incorrect dimensions")
            if not set(np.unique(image[:, :, 3])).issubset({0, 255}): fail(f"{path.name} has feathered alpha")
            visible = image[:, :, 3] > 0
            colors = {tuple(color) for color in np.unique(image[:, :, :3][visible], axis=0)} if np.any(visible) else set()
            if not colors.issubset({INK, YELLOW}): fail(f"{path.name} has invalid visible colors")
            yellow_allowed = folder.name == "03-eyes" or path.name.startswith("HH05__")
            if YELLOW in colors and not yellow_allowed: fail(f"{path.name} has yellow outside eyes/flames")

    manifest = json.loads((GENERATOR / "output" / "manifest.json").read_text())
    if manifest["layerCount"] != 8: fail("generator did not use eight ordered layer folders")
    if [layer["elementCount"] for layer in manifest["layers"]] != EXPECTED: fail("output manifest folder counts mismatch")
    outputs = manifest["outputs"]
    if len(outputs) != 24 or len({item["dna"] for item in outputs}) != 24: fail("output DNA is missing or duplicated")
    for item in outputs:
        image = np.array(Image.open(GENERATOR / "output" / item["localImage"]).convert("RGB"), dtype=np.uint8)
        colors = {tuple(color) for color in np.unique(image.reshape(-1, 3), axis=0)}
        if image.shape != (1028, 1028, 3) or not colors.issubset({INK, LIME, YELLOW}): fail(f"edition {item['id']} dimensions/palette failed")
        if not np.any(np.all(image[-1] == np.array(INK), axis=1)): fail(f"edition {item['id']} does not reach row 1027")
        metadata = json.loads((GENERATOR / "output" / item["metadataFile"]).read_text())
        if metadata["dna"] != item["dna"] or len(metadata["attributes"]) != 8: fail(f"edition {item['id']} metadata failed")
    print("Generator audit passed: 116 inputs / 8 folders / 24 unique 1028px composites")


if __name__ == "__main__": main()
