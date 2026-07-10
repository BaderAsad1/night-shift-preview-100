#!/usr/bin/env python3
"""Build Neon Nocturne from complete portraits and illustrated motifs.

No head/torso splicing and no procedural grids, bars, charts, or scan lines.
Every portrait is complete. A curated pixel-art motif is placed only around the
portrait and erased behind a solid silhouette-protection matte.
"""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
import itertools
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PORTRAIT_SOURCES = [
    ROOT / "reference" / "neon-nocturne-calibration.png",
    ROOT / "reference" / "neon-nocturne-expansion-a.png",
    ROOT / "reference" / "neon-nocturne-expansion-b.png",
]
MOTIF_SOURCE = ROOT / "reference" / "neon-nocturne-motifs.png"
TRAIT_SOURCE_DIR = ROOT / "reference" / "neon-nocturne-traits"
INK = (2, 1, 2)
LIME = "#d0f708"
TRAIT_YELLOW = (253, 244, 35)

HOUSES = [
    {"name": "Velvet Court", "accent": "#ff405b", "motto": "Old blood, new rules."},
    {"name": "Neon Vein", "accent": "#35e7ff", "motto": "Stay bright after dark."},
    {"name": "Cold Blood", "accent": "#9bdcff", "motto": "Calm is a superpower."},
    {"name": "Asphalt Fangs", "accent": "#ff7a32", "motto": "The city is ours at night."},
    {"name": "Black Signal", "accent": "#a576ff", "motto": "Broadcast from the void."},
    {"name": "Wild Bite", "accent": "#d8ff4f", "motto": "Instinct over etiquette."},
]

# name, silhouette/headwear, eyes, outfit
ARCHETYPES = [
    ("Raven Tux", "Raven Wave", "Hollow Ovals", "Skull Tux"),
    ("Pumpkin Regent", "Pumpkin Crown", "Soft Glow", "High Collar"),
    ("Midnight Medallion", "Midnight Slick", "Shadow Fade", "Medallion Cape"),
    ("Flame Knit", "Living Flame", "Long Lashes", "Striped Knit"),
    ("Stitched Undertaker", "Stitched Crop", "X Glow", "Undertaker Shirt"),
    ("Horned Wing", "Little Horns", "Angry Arches", "Winged Cape"),
    ("Mummy Wrap", "Mummy Wraps", "Soft Glow", "Wrapped Tunic"),
    ("Coven Courier", "Coven Hat", "Hollow Ovals", "Coven Coat + Lantern"),
    ("Spectral Chain", "Spectral Wave", "Hollow Ovals", "Chain Crewneck"),
    ("Hypno Velvet", "Raven Wave", "Hypno Spirals", "Velvet Jacket"),
    ("Beanie Bones", "Pom Beanie", "Hollow Ovals", "Skeleton Hoodie"),
    ("Webbed Court", "Webbed Wave", "Hollow Ovals", "High Collar"),
    ("Goggle Aviator", "Flight Goggles", "Hollow Ovals", "Fur Flight Jacket"),
    ("Neon Visor", "Retro Visor", "Visor Glow", "Utility Coat"),
    ("Moth Velvet", "Moth Antennae", "Dark Glow", "Velvet Cape"),
    ("Wolf Varsity", "Wolf Ears", "Hollow Ovals", "Varsity Jacket"),
    ("Rain Runner", "Deep Rain Hood", "Hollow Ovals", "Technical Shell"),
    ("Geometric Bob", "Sleek Bob", "Hollow Ovals", "Geometric Collar"),
    ("Bat Courier", "Bat Courier Helmet", "Hollow Ovals", "Messenger Rig"),
    ("Night Rider", "High Pompadour", "Hollow Ovals", "Biker Jacket"),
    ("Broadcast Headset", "Oversized Headphones", "Hollow Ovals", "Broadcast Jacket"),
    ("Quilted Moonclip", "Moonclip Bob", "Hollow Ovals", "Quilted Coat"),
    ("Spike Armor", "Spiked Crest", "Hollow Ovals", "Armored Vest"),
    ("Roundglass Cardigan", "Round Glasses", "Lens Glow", "Knit Cardigan"),
    ("Noir Detective", "Broad Fedora", "Hollow Ovals", "Trench Collar"),
    ("Arcade Racer", "Compact Race Helmet", "Full Visor Glow", "Racing Jacket"),
    ("Deep-Sea Captain", "Captain Cap", "Hollow Ovals", "Heavy Pea Coat"),
    ("Wild Inventor", "Wild Side Hair + Goggles", "Hollow Ovals", "Tool Apron"),
    ("Silent Film Star", "Finger-Wave Hair", "Long Lashes", "Fur Collar"),
    ("Desert Nomad", "Wrapped Goggles", "Goggle Glow", "Desert Scarf"),
    ("Botanical Keeper", "Leaf Crown", "Hollow Ovals", "Work Overalls"),
    ("Synth Shade", "Angular Shades", "Shade Reflection", "Stage Coat"),
    ("Ice Climber", "Fur Climber Cap", "Hollow Ovals", "Padded Parka"),
    ("Street Magician", "Tall Top Hat", "Hollow Ovals", "Patterned Vest"),
    ("Graffiti Courier", "Backward Cap", "Hollow Ovals", "Oversized Hoodie"),
    ("Chess Strategist", "Center-Part Hair + Glasses", "Lens Glow", "Sharp Blazer"),
]

# Two tight eye-interior regions for each complete portrait, in final 1024px
# coordinates. The fill routine only colors enclosed negative space inside these
# regions, preserving every black outline, lash, spiral, pupil, and reflection.
EYE_BOXES = [
    ((470, 420, 610, 615), (650, 420, 790, 615)),
    ((420, 430, 605, 610), (620, 430, 790, 610)),
    ((460, 510, 625, 640), (655, 510, 805, 640)),
    ((455, 500, 610, 700), (620, 500, 750, 700)),
    ((485, 420, 635, 585), (690, 420, 810, 585)),
    ((450, 530, 620, 700), (630, 530, 770, 700)),
    ((475, 420, 635, 620), (660, 420, 820, 620)),
    ((490, 480, 650, 680), (670, 480, 810, 680)),
    ((480, 430, 630, 640), (640, 430, 770, 640)),
    ((420, 370, 600, 590), (620, 370, 750, 590)),
    ((480, 430, 650, 640), (660, 430, 800, 640)),
    ((485, 410, 650, 620), (675, 410, 815, 620)),
    ((470, 420, 620, 620), (635, 420, 765, 620)),
    ((450, 440, 630, 550), (640, 440, 790, 550)),
    ((450, 420, 595, 600), (610, 420, 735, 600)),
    ((490, 460, 635, 660), (640, 460, 765, 660)),
    ((460, 360, 625, 560), (620, 360, 760, 560)),
    ((470, 410, 620, 590), (645, 410, 760, 590)),
    ((480, 405, 620, 580), (635, 410, 750, 580)),
    ((470, 430, 610, 620), (630, 430, 750, 620)),
    ((485, 390, 630, 570), (650, 395, 775, 570)),
    ((490, 410, 630, 590), (650, 410, 760, 590)),
    ((485, 430, 615, 610), (640, 430, 750, 610)),
    ((470, 400, 625, 575), (645, 400, 785, 575)),
    ((430, 450, 565, 630), (585, 450, 710, 630)),
    ((520, 410, 680, 625), (690, 410, 825, 625)),
    ((450, 440, 595, 630), (615, 440, 735, 630)),
    ((460, 420, 610, 610), (630, 420, 750, 610)),
    ((460, 450, 625, 620), (650, 450, 780, 620)),
    ((450, 390, 610, 570), (620, 390, 750, 570)),
    ((460, 440, 610, 630), (630, 440, 750, 630)),
    ((430, 450, 625, 625), (635, 450, 800, 625)),
    ((460, 400, 620, 590), (630, 400, 750, 590)),
    ((405, 450, 550, 630), (560, 450, 680, 630)),
    ((450, 380, 610, 570), (625, 380, 755, 570)),
    ((450, 390, 600, 560), (625, 390, 745, 560)),
]

MOTIFS = [
    ("MO01", "Crescent Moon"), ("MO02", "Crater Moon"),
    ("MO03", "Bat Trio"), ("MO04", "Hanging Spider"),
    ("MO05", "Luna Moths"), ("MO06", "Curling Fog"),
    ("MO07", "Black Cat"), ("MO08", "Perched Crow"),
    ("MO09", "Mushroom Cluster"), ("MO10", "Thorn Leaves"),
    ("MO11", "Floating Eyes"), ("MO12", "Pumpkin Lantern"),
    ("MO13", "Night Comet"), ("MO14", "Storm Cloud"),
    ("MO15", "Wolf Paw"), ("MO16", "Old Cassette"),
    ("MO17", "Pocket Radio"), ("MO18", "Potion Bottle"),
    ("MO19", "Coiled Snake"), ("MO20", "Night Beetle"),
    ("MO21", "Ornate Key"), ("MO22", "Tiny Ghost"),
]
# The generated 6x4 sheet also contains a window and candle. They are omitted
# so nothing in the collection can be mistaken for religious imagery.
MOTIF_SOURCE_INDICES = list(range(20)) + [22, 23]

LAYOUTS = [
    ("LY01", "Upper Left", [(8, 8, False)]),
    ("LY02", "Upper Right", [(904, 8, False)]),
    ("LY03", "Middle Left", [(8, 336, False)]),
    ("LY04", "Middle Right", [(904, 336, False)]),
    ("LY05", "Lower Left", [(8, 896, False)]),
    ("LY06", "Lower Right", [(904, 896, False)]),
    ("LY07", "Twin Upper", [(8, 8, False), (904, 8, True)]),
    ("LY08", "Twin Sides", [(8, 408, False), (904, 408, True)]),
    ("LY09", "Diagonal Pair", [(8, 8, False), (904, 896, True)]),
]


def portrait_cells(sheet: Image.Image) -> list[Image.Image]:
    xs = [0, 356, 716, 1013, sheet.width]
    ys = [0, 399, 750, sheet.height]
    return [sheet.crop((xs[c], ys[r], xs[c + 1], ys[r + 1])).convert("RGB") for r in range(3) for c in range(4)]


def motif_cells(sheet: Image.Image) -> list[Image.Image]:
    xs = [round(i * sheet.width / 6) for i in range(7)]
    ys = [round(i * sheet.height / 4) for i in range(5)]
    return [sheet.crop((xs[c], ys[r], xs[c + 1], ys[r + 1])).convert("RGB") for r in range(4) for c in range(6)]


def lime_to_alpha(cell: Image.Image) -> Image.Image:
    alpha = Image.new("L", cell.size, 0)
    src = cell.load()
    dst = alpha.load()
    for y in range(cell.height):
        for x in range(cell.width):
            r, g, b = src[x, y]
            luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if luminance <= 30:
                value = 255
            elif luminance >= 188:
                value = 0
            else:
                value = round((188 - luminance) / 158 * 255)
            if g > 170 and r > 120 and b < 130:
                value = min(value, 20)
            dst[x, y] = value
    return alpha


def alpha_art(alpha: Image.Image, max_width: int, max_height: int, canvas_size: tuple[int, int], anchor_bottom: int) -> Image.Image:
    solid = alpha.point(lambda value: 255 if value > 28 else 0)
    bbox = solid.getbbox()
    if not bbox:
        raise ValueError("Art cell contains no ink")
    alpha = alpha.crop((max(0, bbox[0] - 3), max(0, bbox[1] - 3), min(alpha.width, bbox[2] + 3), min(alpha.height, bbox[3] + 3)))
    ratio = min(max_width / alpha.width, max_height / alpha.height)
    size = (round(alpha.width * ratio), round(alpha.height * ratio))
    alpha = alpha.resize(size, Image.Resampling.LANCZOS)
    canvas_alpha = Image.new("L", canvas_size, 0)
    canvas_alpha.paste(alpha, ((canvas_size[0] - size[0]) // 2, anchor_bottom - size[1]))
    image = Image.new("RGBA", canvas_size, (*INK, 0))
    image.putalpha(canvas_alpha)
    return image


def remove_tiny_fragments(image: Image.Image, maximum_pixels: int = 180) -> Image.Image:
    """Remove isolated extraction specks without touching real illustrated traits."""
    alpha = image.getchannel("A")
    solid = alpha.point(lambda value: 255 if value > 24 else 0)
    px = solid.load()
    seen = set()
    components = []
    for y in range(solid.height):
        for x in range(solid.width):
            if not px[x, y] or (x, y) in seen:
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            component = []
            while queue:
                cx, cy = queue.popleft()
                component.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < solid.width and 0 <= ny < solid.height and px[nx, ny] and (nx, ny) not in seen:
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            components.append(component)
    if not components:
        return image
    main = max(components, key=len)
    main_bottom = max(y for _, y in main)
    remove = []
    for component in components:
        component_top = min(y for _, y in component)
        if (len(component) <= maximum_pixels or component_top > main_bottom + 4
                or (component_top > 780 and len(component) < 2500)):
            remove.extend(component)
    if remove:
        mutable = alpha.load()
        for x, y in remove:
            mutable[x, y] = 0
    image.putalpha(alpha)
    return image


def extract_portrait(cell: Image.Image) -> Image.Image:
    return alpha_art(lime_to_alpha(cell), 760, 820, (1024, 1024), 960)


def clean_portrait_footer(image: Image.Image, archetype_index: int) -> Image.Image:
    """Remove two known source-sheet footer marks without touching character detail."""
    alpha = image.getchannel("A")
    if archetype_index == 4:  # Stitched Undertaker source squiggle
        for y in range(920, 1024):
            for x in range(480, 560):
                alpha.putpixel((x, y), 0)
    elif archetype_index == 16:  # Rain Runner source footer fragments
        for y in range(920, 1024):
            for x in range(420, 720):
                alpha.putpixel((x, y), 0)
    image.putalpha(alpha)
    return image


def eye_interior_mask(portrait: Image.Image, archetype_index: int) -> Image.Image:
    """Find only the enclosed negative space within each portrait's two eyes."""
    closed_ink = portrait.getchannel("A").point(
        lambda value: 255 if value > 24 else 0
    ).filter(ImageFilter.MaxFilter(17))
    source = closed_ink.load()
    mask = Image.new("L", portrait.size, 0)
    target = mask.load()

    for x0, y0, x1, y1 in EYE_BOXES[archetype_index]:
        seen = set()
        for y in range(y0, y1):
            for x in range(x0, x1):
                if source[x, y] or (x, y) in seen:
                    continue
                queue = deque([(x, y)])
                seen.add((x, y))
                component = []
                touches_edge = False
                while queue:
                    cx, cy = queue.popleft()
                    component.append((cx, cy))
                    touches_edge |= cx in (x0, x1 - 1) or cy in (y0, y1 - 1)
                    for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                        if (x0 <= nx < x1 and y0 <= ny < y1 and not source[nx, ny]
                                and (nx, ny) not in seen):
                            seen.add((nx, ny))
                            queue.append((nx, ny))
                if not touches_edge and len(component) >= 300:
                    for px, py in component:
                        target[px, py] = 255

    # The Hypno Spiral linework is intentionally open. Solid yellow discs sit
    # behind the black spirals so every gap inside the two eyes gets the same fill.
    if archetype_index == 9:
        draw = ImageDraw.Draw(mask)
        draw.ellipse((442, 390, 578, 568), fill=255)
        draw.ellipse((638, 400, 728, 570), fill=255)
    elif archetype_index == 31:
        # The two angular shade reflections are open to the lens edge. These
        # lens-shaped underlays color both reflections while the opaque black
        # glasses continue to mask everything else.
        draw = ImageDraw.Draw(mask)
        draw.polygon(((430, 450), (625, 450), (602, 610), (458, 610)), fill=255)
        draw.polygon(((635, 450), (800, 450), (776, 600), (654, 600)), fill=255)
    return mask


def flame_interior_mask(portrait: Image.Image, archetype_index: int) -> Image.Image:
    """Return the inset body of the Living Flame silhouette, keeping a black rim."""
    mask = Image.new("L", portrait.size, 0)
    if archetype_index != 3:
        return mask
    solid_ink = portrait.getchannel("A").point(lambda value: 255 if value > 90 else 0)
    inset = solid_ink.filter(ImageFilter.MinFilter(9))
    flame_region = Image.new("L", portrait.size, 0)
    ImageDraw.Draw(flame_region).rectangle((300, 70, 850, 500), fill=255)
    return ImageChops.multiply(inset, flame_region)


def apply_trait_color(portrait: Image.Image, archetype_index: int) -> Image.Image:
    """Build source-level eye and flame color without altering black ink."""
    yellow = Image.new("RGBA", portrait.size, (*TRAIT_YELLOW, 0))
    yellow.putalpha(eye_interior_mask(portrait, archetype_index))
    colored = yellow
    colored.alpha_composite(portrait)

    flame = Image.new("RGBA", portrait.size, (*TRAIT_YELLOW, 0))
    flame.putalpha(flame_interior_mask(portrait, archetype_index))
    colored.alpha_composite(flame)
    return colored


def normalize_portrait_trait(portrait: Image.Image, archetype_index: int) -> Image.Image:
    """Normalize a source portrait around a shared 160px eye span and eye-line."""
    boxes = EYE_BOXES[archetype_index]
    centers = [((x0 + x1) / 2, (y0 + y1) / 2) for x0, y0, x1, y1 in boxes]
    eye_midpoint = (
        (centers[0][0] + centers[1][0]) / 2,
        (centers[0][1] + centers[1][1]) / 2,
    )
    eye_span = centers[1][0] - centers[0][0]
    bbox = portrait.getchannel("A").getbbox()
    if not bbox or eye_span <= 0:
        raise ValueError(f"Cannot normalize archetype {archetype_index + 1}")

    scale = min(
        160 / eye_span,
        920 / (bbox[2] - bbox[0]),
        920 / (bbox[3] - bbox[1]),
    )
    target_eye = (620, 520)
    transformed = [
        (bbox[0] - eye_midpoint[0]) * scale + target_eye[0],
        (bbox[1] - eye_midpoint[1]) * scale + target_eye[1],
        (bbox[2] - eye_midpoint[0]) * scale + target_eye[0],
        (bbox[3] - eye_midpoint[1]) * scale + target_eye[1],
    ]
    # Calibrate to an inset 52..972 frame so Lanczos edge pixels still remain
    # inside the public 48..976 safety boundary after resampling.
    shift_x = max(52 - transformed[0], 0) + min(972 - transformed[2], 0)
    shift_y = max(52 - transformed[1], 0) + min(972 - transformed[3], 0)

    resized = portrait.resize(
        (round(portrait.width * scale), round(portrait.height * scale)),
        Image.Resampling.LANCZOS,
    )
    normalized = Image.new("RGBA", portrait.size, (0, 0, 0, 0))
    normalized.alpha_composite(resized, (
        round(target_eye[0] + shift_x - eye_midpoint[0] * scale),
        round(target_eye[1] + shift_y - eye_midpoint[1] * scale),
    ))
    return normalized


def build_portrait_trait_sources(output_dir: Path = TRAIT_SOURCE_DIR) -> None:
    """Create the reusable, colored, normalized archetype source assets."""
    portraits = []
    for source in PORTRAIT_SOURCES:
        portraits.extend(extract_portrait(cell) for cell in portrait_cells(Image.open(source)))
    if len(portraits) != len(ARCHETYPES):
        raise ValueError(f"Expected {len(ARCHETYPES)} portraits, found {len(portraits)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("AR*.png"):
        old.unlink()
    for index, portrait in enumerate(portraits):
        cleaned = clean_portrait_footer(portrait, index)
        colored = apply_trait_color(cleaned, index)
        normalized = normalize_portrait_trait(colored, index)
        normalized.save(output_dir / f"AR{index + 1:02d}.png", optimize=True)


def load_portrait_trait_sources() -> list[Image.Image]:
    paths = [TRAIT_SOURCE_DIR / f"AR{index + 1:02d}.png" for index in range(len(ARCHETYPES))]
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing portrait trait sources: {', '.join(missing)}. "
            "Run scripts/build_neon_nocturne_traits.py first."
        )
    return [Image.open(path).convert("RGBA") for path in paths]


def extract_motif(cell: Image.Image) -> Image.Image:
    return remove_tiny_fragments(alpha_art(lime_to_alpha(cell), 104, 104, (112, 112), 108), maximum_pixels=50)


def protection_matte(base: Image.Image) -> Image.Image:
    """Protect lime interior spaces as well as black portrait pixels."""
    alpha = base.getchannel("A").point(lambda value: 255 if value > 24 else 0)
    src = alpha.load()
    matte = Image.new("L", alpha.size, 0)
    dst = matte.load()
    for y in range(alpha.height):
        occupied = [x for x in range(alpha.width) if src[x, y]]
        if occupied:
            for x in range(max(0, occupied[0] - 8), min(alpha.width, occupied[-1] + 9)):
                dst[x, y] = 255
    return matte.filter(ImageFilter.MaxFilter(17))


def motif_layer(motif: Image.Image, layout_index: int) -> Image.Image:
    layer = Image.new("RGBA", (1024, 1024), (*INK, 0))
    for x, y, mirrored in LAYOUTS[layout_index][2]:
        art = ImageOps.mirror(motif) if mirrored else motif
        layer.alpha_composite(art, (x, y))
    return layer


def all_combinations() -> list[tuple[int, int, int]]:
    overlays = list(itertools.product(range(len(MOTIFS)), range(len(LAYOUTS))))
    result = []
    for round_index in range(len(overlays)):
        for archetype_index in range(len(ARCHETYPES)):
            overlay_index = (round_index * 37 + archetype_index * 17) % len(overlays)
            motif_index, layout_index = overlays[overlay_index]
            result.append((archetype_index, motif_index, layout_index))
    if len(result) != 7128 or len(set(result)) != 7128:
        raise ValueError("Expected exactly 7,128 unique combinations")
    return result


def trait_records(archetype_index: int, motif_index: int, layout_index: int):
    archetype = ARCHETYPES[archetype_index]
    return [
        {"category": "Archetype", "code": f"AR{archetype_index + 1:02d}", "name": archetype[0]},
        {"category": "Silhouette / Headwear", "code": f"SH{archetype_index + 1:02d}", "name": archetype[1]},
        {"category": "Eyes", "code": f"EY{archetype_index + 1:02d}", "name": archetype[2]},
        {"category": "Outfit", "code": f"OF{archetype_index + 1:02d}", "name": archetype[3]},
        {"category": "Night Motif", "code": MOTIFS[motif_index][0], "name": MOTIFS[motif_index][1]},
        {"category": "Motif Layout", "code": LAYOUTS[layout_index][0], "name": LAYOUTS[layout_index][1]},
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    combinations = all_combinations()
    if not 1 <= args.limit <= len(combinations):
        raise ValueError(f"Limit must be between 1 and {len(combinations)}")

    portraits = load_portrait_trait_sources()
    mattes = [protection_matte(portrait) for portrait in portraits]

    source_cells = motif_cells(Image.open(MOTIF_SOURCE))
    motifs = [extract_motif(source_cells[index]) for index in MOTIF_SOURCE_INDICES]
    if len(motifs) != len(MOTIFS):
        raise ValueError(f"Expected {len(MOTIFS)} motifs, found {len(motifs)}")

    args.output.mkdir(parents=True, exist_ok=True)
    for old in args.output.glob("*.png"):
        old.unlink()
    hashes = set()
    records = []
    for number, (archetype_index, motif_index, layout_index) in enumerate(combinations[:args.limit], 1):
        decoration = motif_layer(motifs[motif_index], layout_index)
        decoration.putalpha(ImageChops.subtract(decoration.getchannel("A"), mattes[archetype_index]))
        image = decoration
        image.alpha_composite(portraits[archetype_index])
        digest = hashlib.sha256(image.tobytes()).hexdigest()
        if digest in hashes:
            raise SystemExit(f"Duplicate rendered art at #{number:03d}")
        hashes.add(digest)
        filename = f"{number:03d}.png"
        image.save(args.output / filename, optimize=True)
        house = HOUSES[(number - 1) % len(HOUSES)]
        records.append({
            "id": number,
            "name": f"Night Shift #{number:03d}",
            "house": house["name"],
            "accent": house["accent"],
            "motto": house["motto"],
            "image": f"studio/{filename}",
            "modules": {"archetype": archetype_index + 1, "motif": motif_index + 1, "layout": layout_index + 1},
            "traits": trait_records(archetype_index, motif_index, layout_index),
        })

    possible = len(combinations)
    categories = {
        "Archetype": [
            {"code": f"AR{i + 1:02d}", "name": values[0],
             "components": {"silhouette": values[1], "eyes": values[2], "outfit": values[3]}}
            for i, values in enumerate(ARCHETYPES)
        ],
        "Night Motif": [{"code": code, "name": name} for code, name in MOTIFS],
        "Motif Layout": [{"code": code, "name": name} for code, name, _ in LAYOUTS],
    }
    library = {
        "name": "Neon Nocturne — Complete Archetype System",
        "sources": ["neon-nocturne-traits/AR01.png–AR36.png", MOTIF_SOURCE.name],
        "palette": {"ink": "#020102", "traitYellow": "#fdf423", "presentationLime": LIME},
        "rendering": {
            "output": "1024x1024 RGBA PNG",
            "architecture": "Normalized source portrait trait plus curated illustrated motif",
            "compositing": "Motif is erased inside a solid silhouette-protection matte",
            "normalization": {"eyeSpan": 160, "eyeLineY": 520, "safeFrame": [48, 48, 976, 976]},
        },
        "rules": [
            "Complete portraits are never split into head or torso layers",
            "Portrait size is normalized at the source-trait stage before collection assembly",
            "Only curated hand-drawn night motifs are used",
            "Motifs cannot erase, mask, or overpaint portrait pixels",
            "Every eye interior and Living Flame interior is embedded in its source trait as #fdf423",
            "Motif library is limited to nature, nocturnal objects, and creatures",
            "No text, logo, signature, or watermark",
        ],
        "moduleCount": sum(len(values) for values in categories.values()),
        "collectionTarget": 6666,
        "possibleCombinations": possible,
        "reserveCombinations": possible - 6666,
        "categories": categories,
    }
    manifest = {"collection": "Night Shift Society", "edition": "Neon Nocturne", "count": len(records),
                "traitLibrary": library, "characters": records}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Built {len(records)} previews from 36 complete portraits, 22 motifs, and 9 layouts "
          f"({possible} valid combinations; target 6666)")


if __name__ == "__main__":
    main()
