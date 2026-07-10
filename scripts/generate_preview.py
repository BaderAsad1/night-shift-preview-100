#!/usr/bin/env python3
"""Build 100 deterministic 8-bit concept composites from the approved trait boards."""

from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageEnhance


ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT.parent / "v2_8bit"
OUT = ROOT / "public" / "characters"
CATALOG_PATH = V2 / "concept_catalog.json"
NATIVE = 128
SCALE = 8

HOUSES = [
    {"name": "Velvet Court", "accent": "#ff405b", "motto": "Old blood, new rules."},
    {"name": "Neon Vein", "accent": "#35e7ff", "motto": "Stay bright after dark."},
    {"name": "Cold Blood", "accent": "#9bdcff", "motto": "Calm is a superpower."},
    {"name": "Asphalt Fangs", "accent": "#ff7a32", "motto": "The city is ours at night."},
    {"name": "Black Signal", "accent": "#a576ff", "motto": "Broadcast from the void."},
    {"name": "Wild Bite", "accent": "#d8ff4f", "motto": "Instinct over etiquette."},
]

CATEGORY_LABELS = {
    "B": "Origin",
    "O": "Outfit",
    "H": "Hair / Headwear",
    "F_eye": "Eyes",
    "F_gear": "Eyewear",
    "F_mouth": "Mouth",
    "C_neck": "Neck",
    "C_ear": "Earring",
    "P": "Side Prop",
    "K": "Companion",
    "E": "Effect",
    "X": "Face Detail",
}


def crop_cell(board: Image.Image, index: int) -> Image.Image:
    col, row = index % 4, index // 4
    x0 = round(col * board.width / 4)
    x1 = round((col + 1) * board.width / 4)
    y0 = round(row * board.height / 4)
    y1 = round((row + 1) * board.height / 4)
    cell = board.crop((x0, y0, x1, y1)).convert("RGBA")
    alpha = cell.getchannel("A")
    alpha = alpha.point(lambda a: 255 if a >= 72 else 0)
    cell.putalpha(alpha)
    bbox = alpha.getbbox()
    return cell.crop(bbox) if bbox else cell


def fit(layer: Image.Image, box: tuple[int, int, int, int], exact: bool = False) -> tuple[Image.Image, tuple[int, int]]:
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    if exact:
        size = (bw, bh)
    else:
        ratio = min(bw / layer.width, bh / layer.height)
        size = (max(1, round(layer.width * ratio)), max(1, round(layer.height * ratio)))
    resized = layer.resize(size, Image.Resampling.NEAREST)
    x = x0 + (bw - size[0]) // 2
    y = y0 + (bh - size[1]) // 2
    return resized, (x, y)


def paste(canvas: Image.Image, layer: Image.Image, box: tuple[int, int, int, int], exact: bool = False) -> None:
    layer, pos = fit(layer, box, exact)
    canvas.alpha_composite(layer, dest=pos)


def soften_gradients(img: Image.Image) -> Image.Image:
    """Reduce source-board gradients into a tighter arcade palette without blurring."""
    rgb = img.convert("RGB").quantize(colors=48, method=Image.Quantize.MEDIANCUT).convert("RGBA")
    rgb.putalpha(img.getchannel("A"))
    return ImageEnhance.Contrast(rgb).enhance(1.08)


def main() -> None:
    random.seed(8888)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()

    catalog = json.loads(CATALOG_PATH.read_text())
    categories = catalog["categories"]
    names = {
        trait["code"]: trait["name"]
        for category in categories.values()
        for trait in category["traits"]
    }
    names["H12"] = "Bat beanie"
    boards = {
        code: Image.open(V2 / category["source"]).convert("RGBA")
        for code, category in categories.items()
    }
    cells = {
        code: [soften_gradients(crop_cell(boards[code], i)) for i in range(16)]
        for code in categories
    }

    def choose(prefix: str, values: list[int]) -> str:
        return f"{prefix}{random.choice(values)}"

    def cell(code: str) -> Image.Image:
        return cells[code[0]][int(code[1:]) - 1]

    characters = []
    signatures: set[tuple[str, ...]] = set()

    for number in range(1, 101):
        house = HOUSES[(number - 1) % len(HOUSES)]
        while True:
            origin = choose("B", list(range(1, 17)))
            outfit = choose("O", list(range(1, 17)))
            # Crowns are held out because their tiny negative-space marks can read as crosses.
            # The witch hat is also held out to keep this review batch fully secular.
            hair = choose("H", [1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 14, 15, 16])
            eye = choose("F", [1, 2, 3, 4])
            mouth = choose("F", list(range(9, 17)))
            eyewear = choose("F", [5, 6, 7, 8]) if random.random() < 0.38 else None
            neck = choose("C", list(range(7, 13))) if random.random() < 0.38 else None
            earring = choose("C", [13, 14]) if random.random() < 0.24 else None
            face = choose("X", list(range(1, 17))) if random.random() < 0.48 else None
            prop = choose("P", list(range(1, 17))) if random.random() < 0.46 else None
            companion = choose("K", list(range(1, 17))) if random.random() < 0.34 else None
            effect = choose("E", list(range(1, 17))) if random.random() < 0.28 else None
            signature = tuple(x or "-" for x in [origin, outfit, hair, eye, mouth, eyewear, neck, earring, face, prop, companion, effect])
            if signature not in signatures:
                signatures.add(signature)
                break

        canvas = Image.new("RGBA", (NATIVE, NATIVE), (0, 0, 0, 0))
        if effect:
            paste(canvas, cell(effect), (2, 4, 126, 126))
        paste(canvas, cell(origin), (27, 5, 101, 103), exact=True)
        paste(canvas, cell(outfit), (7, 75, 121, 128), exact=True)

        # Face features are registered to the canonical head from the body board.
        paste(canvas, cell(eye), (38, 42, 90, 57))
        if face:
            face_boxes = {
                1: (40, 55, 58, 70), 2: (42, 36, 86, 49), 3: (35, 38, 93, 75),
                4: (70, 51, 91, 72), 5: (44, 48, 58, 73), 6: (44, 48, 58, 73),
                7: (41, 52, 87, 66), 8: (69, 53, 91, 69), 9: (55, 56, 73, 70),
                10: (26, 48, 102, 65), 11: (40, 54, 58, 69), 12: (68, 48, 91, 72),
                13: (48, 65, 80, 76), 14: (50, 65, 78, 76), 15: (48, 63, 81, 82),
                16: (69, 61, 93, 87),
            }
            paste(canvas, cell(face), face_boxes[int(face[1:])])
        paste(canvas, cell(mouth), (46, 64, 82, 82))
        if eyewear:
            paste(canvas, cell(eyewear), (33, 39, 95, 62))

        if hair:
            hnum = int(hair[1:])
            box = (24, 1, 104, 61) if hnum <= 8 else (27, 0, 101, 45)
            paste(canvas, cell(hair), box)
        if neck:
            paste(canvas, cell(neck), (38, 78, 90, 103))
        if earring:
            paste(canvas, cell(earring), (91, 48, 108, 73))
        if prop:
            box = (93, 69, 127, 121) if number % 2 else (1, 69, 35, 121)
            paste(canvas, cell(prop), box)
        if companion:
            box = (1, 75, 39, 122) if number % 2 else (89, 75, 127, 122)
            paste(canvas, cell(companion), box)

        image = canvas.resize((NATIVE * SCALE, NATIVE * SCALE), Image.Resampling.NEAREST)
        filename = f"{number:03d}.png"
        image.save(OUT / filename, optimize=True)

        ordered = [
            ("B", origin), ("O", outfit), ("H", hair), ("F_eye", eye),
            ("F_mouth", mouth), ("F_gear", eyewear), ("X", face),
            ("C_neck", neck), ("C_ear", earring), ("P", prop),
            ("K", companion), ("E", effect),
        ]
        traits = [
            {"category": CATEGORY_LABELS[key], "code": code, "name": names[code]}
            for key, code in ordered if code
        ]
        characters.append({
            "id": number,
            "name": f"Night Shift #{number:03d}",
            "house": house["name"],
            "accent": house["accent"],
            "motto": house["motto"],
            "image": f"/characters/{filename}",
            "traits": traits,
        })

    manifest = {
        "collection": "Night Shift Society",
        "status": "Concept preview — not final mint art",
        "count": len(characters),
        "traitConcepts": catalog["concept_count"],
        "houses": HOUSES,
        "characters": characters,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Generated {len(characters)} preview characters in {OUT}")


if __name__ == "__main__":
    main()
