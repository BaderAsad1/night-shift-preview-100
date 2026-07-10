#!/usr/bin/env python3
"""Generate registered, compatibility-checked Night Shift preview composites."""

from __future__ import annotations

import argparse
import json
import random
from collections import deque
from pathlib import Path

from PIL import Image, ImageEnhance


ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT.parent / "v2_8bit"
DEFAULT_OUT = ROOT / "public" / "characters"
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
    "B": "Origin", "O": "Outfit", "H": "Hair / Headwear", "F_eye": "Eyes",
    "F_gear": "Eyewear", "F_mouth": "Mouth", "C_neck": "Neck",
    "C_ear": "Earring", "P": "Side Prop", "K": "Companion", "E": "Effect",
    "X": "Face Detail",
}

# All coordinates are registered against the same 128x128 base.
HAIR_BOXES = {
    1: (27, 2, 101, 53), 2: (28, 2, 100, 54), 3: (27, 0, 101, 56),
    4: (25, 1, 103, 78), 5: (25, 2, 103, 67), 6: (24, 0, 104, 60),
    7: (29, 0, 99, 58), 8: (24, 1, 104, 77), 12: (31, 0, 97, 32),
}
BACK_HEAD_BOXES = {14: (27, 5, 101, 58), 16: (18, 0, 110, 92)}
EYE_BOX = (39, 42, 89, 56)
EYEWEAR_BOXES = {
    5: (36, 41, 92, 57), 6: (39, 40, 89, 58),
    7: (61, 38, 84, 63), 8: (35, 42, 93, 55),
}
MOUTH_BOXES = {
    9: (49, 64, 79, 74), 10: (50, 62, 78, 75), 11: (57, 63, 71, 74),
    12: (49, 63, 79, 76), 13: (48, 66, 80, 73), 15: (49, 60, 79, 70),
    16: (38, 56, 90, 83),
}
FACE_BOXES = {
    1: (42, 55, 57, 68), 2: (43, 37, 85, 48), 3: (36, 39, 92, 74),
    4: (72, 52, 89, 69), 5: (45, 48, 56, 70), 6: (45, 48, 56, 70),
    7: (43, 53, 85, 64), 8: (70, 54, 89, 68), 9: (59, 55, 69, 65),
    10: (27, 49, 101, 63), 11: (42, 55, 56, 67), 12: (70, 49, 90, 70),
}
NECK_BOXES = {
    7: (46, 80, 82, 94), 8: (51, 77, 77, 99), 9: (47, 79, 81, 91),
    10: (50, 79, 78, 98), 11: (45, 80, 83, 92), 12: (46, 78, 82, 99),
}
EARRING_BOXES = {13: (90, 49, 103, 68), 14: (92, 51, 103, 70)}

PROP_BOXES_LEFT = {
    1: (0, 45, 27, 124), 2: (1, 49, 27, 124), 3: (2, 84, 28, 108),
    4: (2, 82, 28, 109), 5: (2, 81, 29, 111), 6: (0, 86, 34, 111),
    7: (1, 84, 31, 113), 8: (3, 80, 28, 105), 9: (4, 66, 25, 113),
    10: (3, 83, 28, 111), 11: (5, 77, 25, 114), 12: (2, 63, 29, 115),
    13: (4, 72, 28, 113), 14: (3, 80, 29, 106), 15: (4, 78, 25, 115),
    16: (2, 78, 29, 111),
}
COMPANION_BOXES_LEFT = {
    1: (0, 59, 30, 84), 2: (0, 60, 30, 85), 3: (1, 82, 29, 115),
    4: (1, 70, 28, 111), 5: (1, 64, 27, 91), 6: (2, 83, 27, 112),
    7: (2, 80, 28, 111), 8: (2, 84, 28, 113), 9: (1, 82, 29, 114),
    10: (1, 69, 29, 93), 11: (2, 88, 29, 114), 12: (0, 87, 31, 114),
    13: (0, 80, 30, 112), 14: (0, 80, 30, 113), 15: (2, 78, 28, 110),
    16: (0, 79, 30, 115),
}

SAFE_HAIR = [1, 2, 3, 4, 5, 6, 7, 8, 12, 14, 16]
SAFE_MOUTHS = [9, 11, 12, 13, 15, 16]
SAFE_FACE = [1, 3, 4, 5, 6, 7, 8, 9, 12]
SAFE_EFFECTS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16]
HIGH_COLLAR_OUTFITS = {3, 4, 6, 8, 10, 12, 13, 16}
EAR_HIDING_HAIR = {4, 5, 8, 12, 14, 16}


def crop_cell(board: Image.Image, index: int) -> Image.Image:
    col, row = index % 4, index // 4
    x0, x1 = round(col * board.width / 4), round((col + 1) * board.width / 4)
    y0, y1 = round(row * board.height / 4), round((row + 1) * board.height / 4)
    cell = board.crop((x0, y0, x1, y1)).convert("RGBA")
    alpha = cell.getchannel("A").point(lambda a: 255 if a >= 72 else 0)
    cell.putalpha(alpha)
    cell = remove_small_components(cell)
    bbox = cell.getchannel("A").getbbox()
    return cell.crop(bbox) if bbox else cell


def remove_small_components(image: Image.Image) -> Image.Image:
    """Drop extraction specks while preserving paired parts such as horns and earrings."""
    alpha = image.getchannel("A")
    px = alpha.load()
    width, height = image.size
    seen: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    for y in range(height):
        for x in range(width):
            if px[x, y] == 0 or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            component = []
            while queue:
                cx, cy = queue.popleft()
                component.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < width and 0 <= ny < height and px[nx, ny] and (nx, ny) not in seen:
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            components.append(component)
    if not components:
        return image
    largest = max(len(component) for component in components)
    keep = {point for component in components if len(component) >= max(6, largest * 0.045) for point in component}
    cleaned = image.copy()
    clean_alpha = Image.new("L", image.size, 0)
    clean_px = clean_alpha.load()
    for x, y in keep:
        clean_px[x, y] = 255
    cleaned.putalpha(clean_alpha)
    return cleaned


def fit(layer: Image.Image, box: tuple[int, int, int, int], exact: bool = False) -> tuple[Image.Image, tuple[int, int]]:
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    if exact:
        size = (bw, bh)
    else:
        ratio = min(bw / layer.width, bh / layer.height)
        size = (max(1, round(layer.width * ratio)), max(1, round(layer.height * ratio)))
    resized = layer.resize(size, Image.Resampling.NEAREST)
    return resized, (x0 + (bw - size[0]) // 2, y0 + (bh - size[1]) // 2)


def paste(canvas: Image.Image, layer: Image.Image, box: tuple[int, int, int, int], exact: bool = False) -> None:
    layer, pos = fit(layer, box, exact)
    canvas.alpha_composite(layer, dest=pos)


def mirror_box(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    return (NATIVE - x1, y0, NATIVE - x0, y1)


def tighten_palette(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB").quantize(colors=40, method=Image.Quantize.MEDIANCUT).convert("RGBA")
    rgb.putalpha(img.getchannel("A"))
    return ImageEnhance.Contrast(rgb).enhance(1.1)


CALIBRATION = [
    dict(origin="B1", outfit="O9", hair="H1", eye="F1", mouth="F9"),
    dict(origin="B2", outfit="O3", hair="H2", eye="F2", mouth="F13", face="X1"),
    dict(origin="B3", outfit="O13", hair="H3", eye="F3", mouth="F11", eyewear="F5"),
    dict(origin="B6", outfit="O15", hair="H4", eye="F4", mouth="F12", earring="C13"),
    dict(origin="B10", outfit="O12", hair="H5", eye="F1", mouth="F15"),
    dict(origin="B11", outfit="O11", hair="H6", eye="F2", mouth="F16"),
    dict(origin="B13", outfit="O16", hair="H7", eye="F3", mouth="F9", face="X9"),
    dict(origin="B14", outfit="O6", hair="H8", eye="F4", mouth="F13", eyewear="F6"),
    dict(origin="B15", outfit="O2", hair="H12", eye="F1", mouth="F12", prop="P5"),
    dict(origin="B16", outfit="O7", hair="H14", eye="F2", mouth="F11", companion="K3"),
    dict(origin="B9", outfit="O14", hair="H16", eye="F3", mouth="F9", effect="E4"),
    dict(origin="B8", outfit="O1", hair="H3", eye="F4", mouth="F13", prop="P12"),
    dict(origin="B4", outfit="O5", hair="H2", eye="F1", mouth="F15", eyewear="F7"),
    dict(origin="B7", outfit="O8", hair="H1", eye="F2", mouth="F12", eyewear="F8"),
    dict(origin="B1", outfit="O15", hair="H6", eye="F3", mouth="F13", neck="C11"),
    dict(origin="B3", outfit="O9", hair="H7", eye="F4", mouth="F11", earring="C14", companion="K1"),
]


def make_random_character(rng: random.Random) -> dict[str, str | None]:
    origin = f"B{rng.randint(1, 16)}"
    outfit_num = rng.randint(1, 16)
    hair_num = rng.choice(SAFE_HAIR)
    mouth_num = rng.choice(SAFE_MOUTHS)
    data: dict[str, str | None] = {
        "origin": origin, "outfit": f"O{outfit_num}", "hair": f"H{hair_num}",
        "eye": f"F{rng.randint(1, 4)}", "mouth": f"F{mouth_num}",
        "eyewear": None, "face": None, "neck": None, "earring": None,
        "prop": None, "companion": None, "effect": None,
    }

    # One face-level accent maximum. Masks remain completely clean.
    if mouth_num != 16:
        face_roll = rng.random()
        if face_roll < 0.25:
            data["eyewear"] = f"F{rng.choice([5, 6, 7, 8])}"
        elif face_roll < 0.43:
            data["face"] = f"X{rng.choice(SAFE_FACE)}"

    # One neck/ear accent maximum, and only where it remains visible.
    if rng.random() < 0.2:
        if outfit_num not in HIGH_COLLAR_OUTFITS and rng.random() < 0.65:
            data["neck"] = f"C{rng.randint(7, 12)}"
        elif hair_num not in EAR_HIDING_HAIR:
            data["earring"] = f"C{rng.choice([13, 14])}"

    # One composition accent maximum: prop, companion, or atmosphere.
    extras = int(bool(data["eyewear"] or data["face"])) + int(bool(data["neck"] or data["earring"]))
    if extras < 2:
        accent_roll = rng.random()
        if accent_roll < 0.22:
            data["prop"] = f"P{rng.randint(1, 16)}"
        elif accent_roll < 0.38:
            data["companion"] = f"K{rng.randint(1, 16)}"
        elif accent_roll < 0.48:
            data["effect"] = f"E{rng.choice(SAFE_EFFECTS)}"
    return data


def render_character(data: dict[str, str | None], cell, number: int) -> Image.Image:
    canvas = Image.new("RGBA", (NATIVE, NATIVE), (0, 0, 0, 0))
    effect = data.get("effect")
    hair = data["hair"]
    hair_num = int(hair[1:])

    if effect:
        paste(canvas, cell(effect), (3, 5, 125, 125))
    if hair_num in BACK_HEAD_BOXES:
        paste(canvas, cell(hair), BACK_HEAD_BOXES[hair_num])

    paste(canvas, cell(data["origin"]), (27, 5, 101, 103), exact=True)
    paste(canvas, cell(data["outfit"]), (7, 75, 121, 128), exact=True)

    # Tall held objects sit behind the face and torso.
    prop = data.get("prop")
    side_left = number % 2 == 0
    if prop and int(prop[1:]) in {1, 2, 9, 12}:
        box = PROP_BOXES_LEFT[int(prop[1:])]
        paste(canvas, cell(prop), box if side_left else mirror_box(box))

    paste(canvas, cell(data["eye"]), EYE_BOX)
    face = data.get("face")
    if face:
        paste(canvas, cell(face), FACE_BOXES[int(face[1:])])
    paste(canvas, cell(data["mouth"]), MOUTH_BOXES[int(data["mouth"][1:])])

    if hair_num in HAIR_BOXES:
        paste(canvas, cell(hair), HAIR_BOXES[hair_num])
    eyewear = data.get("eyewear")
    if eyewear:
        paste(canvas, cell(eyewear), EYEWEAR_BOXES[int(eyewear[1:])])

    neck = data.get("neck")
    if neck:
        paste(canvas, cell(neck), NECK_BOXES[int(neck[1:])])
    earring = data.get("earring")
    if earring:
        paste(canvas, cell(earring), EARRING_BOXES[int(earring[1:])])

    if prop and int(prop[1:]) not in {1, 2, 9, 12}:
        box = PROP_BOXES_LEFT[int(prop[1:])]
        paste(canvas, cell(prop), box if side_left else mirror_box(box))
    companion = data.get("companion")
    if companion:
        box = COMPANION_BOXES_LEFT[int(companion[1:])]
        paste(canvas, cell(companion), box if side_left else mirror_box(box))
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    rng = random.Random(8888)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()

    catalog = json.loads(CATALOG_PATH.read_text())
    categories = catalog["categories"]
    names = {trait["code"]: trait["name"] for category in categories.values() for trait in category["traits"]}
    names["H12"] = "Bat beanie"
    boards = {code: Image.open(V2 / category["source"]).convert("RGBA") for code, category in categories.items()}
    cells = {code: [tighten_palette(crop_cell(boards[code], i)) for i in range(16)] for code in categories}

    def cell(code: str) -> Image.Image:
        return cells[code[0]][int(code[1:]) - 1]

    source = CALIBRATION if args.calibration else []
    signatures: set[tuple[str, ...]] = set()
    if not args.calibration:
        while len(source) < 100:
            candidate = make_random_character(rng)
            signature = tuple(value or "-" for value in candidate.values())
            if signature not in signatures:
                signatures.add(signature)
                source.append(candidate)

    characters = []
    for number, raw in enumerate(source, 1):
        data = {key: raw.get(key) for key in [
            "origin", "outfit", "hair", "eye", "mouth", "eyewear", "face",
            "neck", "earring", "prop", "companion", "effect",
        ]}
        canvas = render_character(data, cell, number)
        image = canvas.resize((NATIVE * SCALE, NATIVE * SCALE), Image.Resampling.NEAREST)
        filename = f"{number:03d}.png"
        image.save(out / filename, optimize=True)

        house = HOUSES[(number - 1) % len(HOUSES)]
        ordered = [
            ("B", data["origin"]), ("O", data["outfit"]), ("H", data["hair"]),
            ("F_eye", data["eye"]), ("F_mouth", data["mouth"]),
            ("F_gear", data["eyewear"]), ("X", data["face"]),
            ("C_neck", data["neck"]), ("C_ear", data["earring"]),
            ("P", data["prop"]), ("K", data["companion"]), ("E", data["effect"]),
        ]
        traits = [
            {"category": CATEGORY_LABELS[key], "code": code, "name": names[code]}
            for key, code in ordered if code
        ]
        characters.append({
            "id": number, "name": f"Night Shift #{number:03d}", "house": house["name"],
            "accent": house["accent"], "motto": house["motto"],
            "image": f"/characters/{filename}", "traits": traits,
        })

    manifest = {
        "collection": "Night Shift Society", "status": "Registered assembly preview",
        "count": len(characters), "traitConcepts": catalog["concept_count"],
        "houses": HOUSES, "characters": characters,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Generated {len(characters)} registered preview characters in {out}")


if __name__ == "__main__":
    main()
