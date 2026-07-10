#!/usr/bin/env python3
"""Build Neon Nocturne from complete, source-normalized portraits.

No head/torso splicing, background objects, procedural grids, bars, charts, or
scan lines. Every output is assembled from one complete portrait source trait.
"""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
PORTRAIT_SOURCES = [
    ROOT / "reference" / "neon-nocturne-calibration.png",
    ROOT / "reference" / "neon-nocturne-expansion-a.png",
    ROOT / "reference" / "neon-nocturne-expansion-b.png",
]
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

def portrait_cells(sheet: Image.Image) -> list[Image.Image]:
    xs = [0, 356, 716, 1013, sheet.width]
    ys = [0, 399, 750, sheet.height]
    return [sheet.crop((xs[c], ys[r], xs[c + 1], ys[r + 1])).convert("RGB") for r in range(3) for c in range(4)]


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
    # One-pixel inset: keep the crisp black outline while coloring narrow flame
    # tongues that the old four-pixel inset incorrectly left black.
    inset = solid_ink.filter(ImageFilter.MinFilter(3))
    flame_region = Image.new("L", portrait.size, 0)
    flame_draw = ImageDraw.Draw(flame_region)
    flame_draw.rectangle((300, 70, 850, 500), fill=255)
    # The left temple flame drops below the main crown. It is part of the same
    # hair trait, not a separate black hair block.
    flame_draw.rectangle((280, 440, 455, 690), fill=255)
    return ImageChops.multiply(inset, flame_region)


def sharpen_portrait_ink(portrait: Image.Image) -> Image.Image:
    """Snap generated line art to opaque black pixels with no glow feather."""
    alpha = portrait.getchannel("A").point(lambda value: 255 if value >= 96 else 0)
    sharp = Image.new("RGBA", portrait.size, (*INK, 0))
    sharp.putalpha(alpha)
    return sharp


def apply_spectral_flame_color(portrait: Image.Image, archetype_index: int) -> Image.Image:
    """Color AR09's disconnected spectral-flame stroke at the source level."""
    if archetype_index != 8:
        return portrait

    pixels = portrait.load()
    ink_pixels = {
        (x, y)
        for y in range(portrait.height)
        for x in range(portrait.width)
        if pixels[x, y][3] == 255 and pixels[x, y][:3] == INK
    }
    components: list[list[tuple[int, int]]] = []
    while ink_pixels:
        start = ink_pixels.pop()
        queue = deque([start])
        component = [start]
        while queue:
            x, y = queue.popleft()
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in ink_pixels:
                    ink_pixels.remove(neighbor)
                    queue.append(neighbor)
                    component.append(neighbor)
        components.append(component)

    largest = max(components, key=len)
    flame_mask = Image.new("L", portrait.size, 0)
    flame_pixels = flame_mask.load()
    for component in components:
        if component is largest or len(component) < 12:
            continue
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        bbox = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
        if bbox[0] < 230 or bbox[2] > 800 or bbox[1] < 280:
            for x, y in component:
                flame_pixels[x, y] = 255

    # Widen the disconnected flame contour into a clearly yellow pixel stroke,
    # then remove the full character silhouette so it can never spill into face
    # or outfit negative space.
    character_matte = Image.new("L", portrait.size, 0)
    character_pixels = character_matte.load()
    character_rows: dict[int, list[int]] = {}
    for x, y in largest:
        character_rows.setdefault(y, []).append(x)
    for y, xs in character_rows.items():
        for x in range(min(xs), max(xs) + 1):
            character_pixels[x, y] = 255
    character_matte = character_matte.filter(ImageFilter.MaxFilter(7))

    colored_flame = flame_mask.filter(ImageFilter.MaxFilter(11))
    colored_flame = ImageChops.subtract(colored_flame, character_matte)
    outline = colored_flame.filter(ImageFilter.MaxFilter(5))
    outlined = Image.new("RGBA", portrait.size, (*INK, 0))
    outlined.putalpha(outline)
    outlined.alpha_composite(portrait)
    yellow = Image.new("RGBA", portrait.size, (*TRAIT_YELLOW, 0))
    yellow.putalpha(colored_flame)
    outlined.alpha_composite(yellow)
    return outlined


def apply_trait_color(
    portrait: Image.Image,
    archetype_index: int,
    mask_source: Image.Image | None = None,
) -> Image.Image:
    """Build source-level eye and flame color without altering black ink."""
    mask_source = mask_source or portrait
    yellow = Image.new("RGBA", portrait.size, (*TRAIT_YELLOW, 0))
    yellow.putalpha(eye_interior_mask(mask_source, archetype_index))
    colored = yellow
    colored.alpha_composite(portrait)

    flame = Image.new("RGBA", portrait.size, (*TRAIT_YELLOW, 0))
    flame.putalpha(flame_interior_mask(mask_source, archetype_index))
    colored.alpha_composite(flame)
    return colored


def validate_portrait_trait(portrait: Image.Image, archetype_index: int) -> None:
    """Reject soft, floating, off-palette, or incompletely colored sources."""
    alpha = portrait.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox or bbox[3] != 1024:
        raise ValueError(f"AR{archetype_index + 1:02d} is not bottom-aligned: {bbox}")
    if set(alpha.getdata()) - {0, 255}:
        raise ValueError(f"AR{archetype_index + 1:02d} contains feathered alpha")
    colors = {pixel[:3] for pixel in portrait.getdata() if pixel[3]}
    if colors - {INK, TRAIT_YELLOW}:
        raise ValueError(f"AR{archetype_index + 1:02d} contains off-palette pixels: {colors}")
    yellow_count = sum(
        pixel[:3] == TRAIT_YELLOW and pixel[3] == 255
        for pixel in portrait.getdata()
    )
    minimum = 100_000 if archetype_index == 3 else 60_000 if archetype_index == 8 else 500
    if yellow_count < minimum:
        raise ValueError(
            f"AR{archetype_index + 1:02d} has incomplete eye/flame color: {yellow_count} yellow pixels"
        )


def normalize_portrait_trait(portrait: Image.Image, archetype_index: int) -> Image.Image:
    """Use one face scale and anchor every portrait to the canvas bottom."""
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

    scale = 160 / eye_span
    target_eye_x = 620
    target_left = (bbox[0] - eye_midpoint[0]) * scale + target_eye_x
    target_right = (bbox[2] - eye_midpoint[0]) * scale + target_eye_x
    shift_x = max(-target_left, 0) + min(1024 - target_right, 0)

    resized = portrait.resize(
        (round(portrait.width * scale), round(portrait.height * scale)),
        Image.Resampling.NEAREST,
    )
    resized_bbox = resized.getchannel("A").getbbox()
    if not resized_bbox:
        raise ValueError(f"Empty normalized archetype {archetype_index + 1}")
    normalized = Image.new("RGBA", portrait.size, (0, 0, 0, 0))
    normalized.alpha_composite(resized, (
        round(target_eye_x + shift_x - eye_midpoint[0] * scale),
        1024 - resized_bbox[3],
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
        colored = apply_trait_color(sharpen_portrait_ink(cleaned), index, cleaned)
        normalized = normalize_portrait_trait(colored, index)
        normalized = apply_spectral_flame_color(normalized, index)
        validate_portrait_trait(normalized, index)
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


def trait_records(archetype_index: int):
    archetype = ARCHETYPES[archetype_index]
    return [
        {"category": "Archetype", "code": f"AR{archetype_index + 1:02d}", "name": archetype[0]},
        {"category": "Silhouette / Headwear", "code": f"SH{archetype_index + 1:02d}", "name": archetype[1]},
        {"category": "Eyes", "code": f"EY{archetype_index + 1:02d}", "name": archetype[2]},
        {"category": "Outfit", "code": f"OF{archetype_index + 1:02d}", "name": archetype[3]},
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        raise ValueError("Limit must be between 1 and 100")

    portraits = load_portrait_trait_sources()

    args.output.mkdir(parents=True, exist_ok=True)
    for old in args.output.glob("*.png"):
        old.unlink()
    records = []
    for number in range(1, args.limit + 1):
        archetype_index = (number - 1) % len(ARCHETYPES)
        image = portraits[archetype_index].copy()
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
            "modules": {"archetype": archetype_index + 1},
            "traits": trait_records(archetype_index),
        })

    categories = {
        "Archetype": [
            {"code": f"AR{i + 1:02d}", "name": values[0],
             "components": {"silhouette": values[1], "eyes": values[2], "outfit": values[3]}}
            for i, values in enumerate(ARCHETYPES)
        ],
    }
    library = {
        "name": "Neon Nocturne — Complete Archetype System",
        "sources": ["neon-nocturne-traits/AR01.png–AR36.png"],
        "palette": {"ink": "#020102", "traitYellow": "#fdf423", "presentationLime": LIME},
        "rendering": {
            "output": "1024x1024 RGBA PNG",
            "architecture": "One complete, normalized source portrait trait; no background objects",
            "normalization": {"eyeSpan": 160, "bodyBaselineY": 1024, "resampling": "nearest"},
        },
        "rules": [
            "Complete portraits are never split into head or torso layers",
            "Portrait scale and body baseline are normalized at the source-trait stage",
            "No decorative characters, icons, animals, objects, or motifs are placed in the background",
            "Every eye interior, Living Flame interior, and Spectral Flame stroke is embedded in its source trait as #fdf423",
            "No text, logo, signature, or watermark",
        ],
        "moduleCount": sum(len(values) for values in categories.values()),
        "collectionTarget": 6666,
        "sourceArchetypeCount": len(ARCHETYPES),
        "categories": categories,
    }
    manifest = {"collection": "Night Shift Society", "edition": "Neon Nocturne", "count": len(records),
                "traitLibrary": library, "characters": records}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Built {len(records)} clean previews from 36 complete source portraits; no background motifs")


if __name__ == "__main__":
    main()
