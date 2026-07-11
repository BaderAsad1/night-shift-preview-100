#!/usr/bin/env python3
"""Build registered transparent review layers from the V2 concept cards.

Every source portrait is normalized to the same eye anchor and body baseline
before a category-specific mask isolates the trait. Optional overlay categories
use a modal common-base subtraction so inherited face/cape linework is removed.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import cv2
import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "trait-expansion-v2"
SOURCE = REVIEW / "cards-transparent"
OUTPUT = REVIEW / "isolated-layers"
INK = np.array((2, 1, 2), dtype=np.uint8)
YELLOW = np.array((253, 244, 35), dtype=np.uint8)
CANVAS = 512
TARGET_EYE = (335.0, 305.0)

CATEGORY_ORDER = (
    "hair-headwear",
    "eyes",
    "eyewear",
    "mouths",
    "outfits",
    "neck",
    "face-details",
    "rare",
)
FACE_DETAIL_BOXES = {
    "FD01": (220, 320, 285, 385), "FD02": (250, 205, 355, 280),
    "FD03": (245, 300, 335, 365), "FD04": (345, 315, 425, 385),
    "FD05": (200, 315, 290, 395), "FD06": (240, 320, 300, 390),
    "FD07": (235, 315, 345, 390), "FD08": (250, 225, 330, 290),
    "FD09": (245, 220, 390, 295), "FD10": (145, 260, 250, 365),
    "FD11": (155, 275, 255, 380), "FD12": (150, 285, 260, 415),
    "FD13": (345, 315, 425, 400), "FD14": (210, 315, 310, 410),
    "FD15": (220, 350, 345, 440), "FD16": (225, 205, 380, 425),
}
NECK_BOXES = {
    "NE01": (275, 415, 360, 512), "NE02": (260, 405, 395, 500),
    "NE03": (245, 410, 410, 490), "NE04": (245, 405, 420, 490),
    "NE05": (235, 400, 420, 512), "NE06": (275, 405, 375, 512),
    "NE07": (245, 410, 415, 490), "NE08": (285, 405, 395, 512),
    "NE09": (245, 420, 410, 490), "NE10": (290, 415, 370, 512),
    "NE11": (280, 415, 385, 512), "NE12": (220, 400, 435, 490),
    "NE13": (240, 415, 410, 490), "NE14": (275, 420, 390, 490),
    "NE15": (285, 410, 370, 512), "NE16": (260, 400, 400, 512),
}


def load_rgba(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGBA"), dtype=np.uint8)


def alpha_bbox(image: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(image[:, :, 3] > 0)
    if not len(xs):
        raise ValueError("Layer contains no artwork")
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def eye_anchor(image: np.ndarray) -> tuple[float, float]:
    x0, y0, x1, y1 = alpha_bbox(image)
    width, height = x1 - x0, y1 - y0
    region = np.zeros((CANVAS, CANVAS), dtype=bool)
    region[
        round(y0 + height * 0.20) : round(y0 + height * 0.62),
        round(x0 + width * 0.24) : round(x0 + width * 0.96),
    ] = True
    yellow = np.all(image[:, :, :3] == YELLOW, axis=2) & (image[:, :, 3] > 0) & region
    ys, xs = np.where(yellow)
    if len(xs) >= 40 and int(xs.max()) - int(xs.min()) >= 34:
        return (float(xs.min() + xs.max()) / 2, float(ys.min() + ys.max()) / 2)
    return (x0 + width * 0.66, y0 + height * 0.45)


def register(image: np.ndarray) -> np.ndarray:
    source_x, source_y = eye_anchor(image)
    scale = (CANVAS - TARGET_EYE[1]) / max(1.0, CANVAS - source_y)
    scale = min(1.14, max(0.88, scale))
    matrix = np.array(
        [
            [scale, 0.0, TARGET_EYE[0] - scale * source_x],
            [0.0, scale, CANVAS - scale * CANVAS],
        ],
        dtype=np.float32,
    )
    registered = cv2.warpAffine(
        image,
        matrix,
        (CANVAS, CANVAS),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    registered[:, :, 3] = np.where(registered[:, :, 3] >= 128, 255, 0).astype(np.uint8)
    return registered


def rectangle_mask(x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    mask = np.zeros((CANVAS, CANVAS), dtype=np.uint8)
    mask[y0:y1, x0:x1] = 255
    return mask


def polygon_mask(points: list[tuple[int, int]]) -> np.ndarray:
    mask = np.zeros((CANVAS, CANVAS), dtype=np.uint8)
    cv2.fillPoly(mask, [np.array(points, dtype=np.int32)], 255)
    return mask


def semantic_mask(category: str, code: str) -> np.ndarray:
    if category == "eyes":
        return rectangle_mask(245, 235, 425, 365)
    if category == "eyewear":
        return rectangle_mask(220, 220, 450, 370)
    if category == "mouths":
        return rectangle_mask(245, 335, 435, 460) if code == "MO14" else rectangle_mask(265, 345, 425, 415)
    if category == "outfits":
        return polygon_mask([(70, 390), (180, 365), (250, 390), (420, 375), (485, 410), (485, 512), (70, 512)])
    if category == "neck":
        return rectangle_mask(180, 345, 445, 505)
    if category == "face-details":
        return rectangle_mask(195, 175, 455, 420)
    if category == "rare":
        return np.full((CANVAS, CANVAS), 255, dtype=np.uint8)

    # Hair/headwear: retain the crown and exterior silhouette while removing
    # the central face. Specific covering traits extend through the eye area.
    mask = polygon_mask([(35, 0), (500, 0), (500, 330), (440, 380), (390, 330), (260, 295), (205, 350), (90, 360), (35, 300)])
    if code in {"HH05", "HH06", "HH11"}:
        mask = cv2.bitwise_or(mask, rectangle_mask(80, 250, 470, 410))
    if code == "HH07":
        mask = cv2.bitwise_or(mask, rectangle_mask(160, 225, 455, 405))
    if code == "HH14":
        mask = cv2.bitwise_or(mask, rectangle_mask(190, 210, 450, 390))
    return mask


def subtract_mask(image: np.ndarray, remove: np.ndarray, region: np.ndarray, dilation: int = 1) -> np.ndarray:
    visible = image[:, :, 3] > 0
    remove_near = cv2.dilate(remove.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=dilation) > 0
    keep = visible & (region > 0) & ~remove_near
    output = np.zeros_like(image)
    output[keep] = image[keep]
    return output


def isolated_box(image: np.ndarray, box: tuple[int, int, int, int], minimum: int = 3) -> np.ndarray:
    x0, y0, x1, y1 = box
    source = ((image[:, :, 3] > 0) & (rectangle_mask(x0, y0, x1, y1) > 0)).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(source, connectivity=8)
    keep = np.zeros_like(source, dtype=bool)
    for label in range(1, count):
        x, y, width, height, pixels = stats[label]
        touches = x <= x0 or y <= y0 or x + width >= x1 or (y + height >= y1 and y1 < CANVAS)
        if pixels >= minimum and not touches:
            keep |= labels == label
    if not np.any(keep):
        keep = source > 0
    output = np.zeros_like(image)
    output[keep] = image[keep]
    return output


def filter_components(image: np.ndarray, minimum: int) -> np.ndarray:
    source = (image[:, :, 3] > 0).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(source, connectivity=8)
    keep = np.zeros_like(source, dtype=bool)
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] >= minimum:
            keep |= labels == label
    output = np.zeros_like(image)
    output[keep] = image[keep]
    return output


def seeded_components(image: np.ndarray, region: np.ndarray, seed_y: int, minimum: int = 8) -> np.ndarray:
    """Keep components that originate in the crown/headwear zone."""
    source = ((image[:, :, 3] > 0) & (region > 0)).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(source, connectivity=8)
    keep = np.zeros_like(source, dtype=bool)
    for label in range(1, count):
        _x, y, _width, _height, pixels = stats[label]
        if pixels >= minimum and y <= seed_y:
            keep |= labels == label
    output = np.zeros_like(image)
    output[keep] = image[keep]
    return output


def largest_components(
    image: np.ndarray,
    region: np.ndarray,
    maximum: int = 3,
    minimum: int = 8,
) -> np.ndarray:
    source = ((image[:, :, 3] > 0) & (region > 0)).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(source, connectivity=8)
    ranked = sorted(
        range(1, count),
        key=lambda label: int(stats[label, cv2.CC_STAT_AREA]),
        reverse=True,
    )
    keep = np.zeros_like(source, dtype=bool)
    for label in ranked[:maximum]:
        if stats[label, cv2.CC_STAT_AREA] >= minimum:
            keep |= labels == label
    output = np.zeros_like(image)
    output[keep] = image[keep]
    return output


def consensus_visible(images: list[np.ndarray], threshold: float = 0.55) -> np.ndarray:
    """Return pixels occupied by the shared category character construction."""
    samples = np.stack([image[:, :, 3] > 0 for image in images], axis=0)
    return samples.mean(axis=0) >= threshold


def difference_layer(
    image: np.ndarray,
    consensus: np.ndarray,
    region: np.ndarray,
    minimum: int = 3,
) -> np.ndarray:
    """Extract positive and carved-out trait marks against a shared base.

    A carved lime line inside a black garment is represented as ink in the
    standalone review layer, so it remains legible on a transparent canvas.
    """
    visible = image[:, :, 3] > 0
    changed = np.logical_xor(visible, consensus) & (region > 0)
    output = np.zeros_like(image)
    output[changed, :3] = INK
    output[changed, 3] = 255
    return filter_components(output, minimum)


def blank_layer() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    return image, ImageDraw.Draw(image)


def procedural_neck(code: str) -> np.ndarray:
    """Clean one-bit neck assets redrawn from the approved concept silhouettes."""
    image, draw = blank_layer()
    c = tuple(INK.tolist() + [255])
    if code == "NE01":
        draw.ellipse((287, 425, 327, 465), fill=c); draw.ellipse((296, 437, 306, 447), fill=(0, 0, 0, 0)); draw.ellipse((310, 437, 320, 447), fill=(0, 0, 0, 0)); draw.polygon([(301, 458), (307, 448), (313, 458)], fill=(0, 0, 0, 0))
    elif code == "NE02":
        draw.polygon([(300, 433), (260, 416), (260, 462), (300, 449)], fill=c); draw.polygon([(314, 433), (354, 416), (354, 462), (314, 449)], fill=c); draw.rectangle((299, 428, 315, 453), fill=c)
    elif code == "NE03":
        for i in range(7): draw.ellipse((252 + i * 17, 424 + abs(3 - i) * 5, 274 + i * 17, 441 + abs(3 - i) * 5), outline=c, width=6)
    elif code == "NE04":
        for i in range(8): draw.ellipse((255 + i * 16, 427 + abs(3.5 - i) * 6, 268 + i * 16, 440 + abs(3.5 - i) * 6), fill=c)
    elif code == "NE05":
        draw.arc((248, 410, 365, 465), 8, 172, fill=c, width=8); draw.arc((255, 421, 358, 475), 8, 172, fill=c, width=8); draw.polygon([(270, 451), (288, 451), (280, 505), (258, 485)], fill=c); draw.polygon([(326, 451), (344, 451), (357, 486), (334, 505)], fill=c)
    elif code == "NE06":
        draw.line((307, 420, 307, 485), fill=c, width=7); draw.arc((272, 415, 307, 450), 205, 65, fill=c, width=7); draw.arc((307, 415, 342, 450), 115, 335, fill=c, width=7)
    elif code == "NE07":
        draw.rounded_rectangle((260, 425, 355, 454), radius=8, outline=c, width=7)
        for x in range(278, 345, 22): draw.ellipse((x, 435, x + 8, 443), fill=c)
    elif code == "NE08":
        draw.line((270, 414, 298, 439), fill=c, width=5); draw.line((344, 414, 316, 439), fill=c, width=5); draw.ellipse((292, 431, 322, 461), outline=c, width=7)
    elif code == "NE09":
        draw.polygon([(307, 437), (287, 422), (267, 434), (278, 452), (296, 449), (307, 463), (318, 449), (336, 452), (347, 434), (327, 422)], fill=c)
    elif code == "NE10":
        draw.line((273, 414, 307, 438), fill=c, width=5); draw.line((341, 414, 307, 438), fill=c, width=5); draw.polygon([(296, 435), (318, 435), (312, 472), (305, 486), (301, 467)], fill=c)
    elif code == "NE11":
        draw.line((270, 414, 307, 440), fill=c, width=5); draw.line((344, 414, 307, 440), fill=c, width=5); draw.ellipse((291, 432, 324, 468), fill=c); draw.ellipse((302, 429, 328, 458), fill=(0, 0, 0, 0))
    elif code == "NE12":
        for i in range(5): draw.ellipse((250 + i * 18, 423 + i * 5, 273 + i * 18, 440 + i * 5), outline=c, width=5)
        draw.arc((334, 433, 378, 474), 65, 300, fill=c, width=6); draw.line((365, 439, 349, 466), fill=c, width=5)
    elif code == "NE13":
        draw.line((260, 430, 355, 430), fill=c, width=8)
        for x in range(268, 350, 20): draw.polygon([(x, 434), (x + 14, 434), (x + 7, 456)], fill=c)
    elif code == "NE14":
        draw.ellipse((278, 429, 296, 447), fill=c); draw.ellipse((322, 429, 340, 447), fill=c)
    elif code == "NE15":
        draw.line((270, 414, 307, 450), fill=c, width=5); draw.line((344, 414, 307, 450), fill=c, width=5); draw.ellipse((296, 439, 318, 462), fill=c); draw.line((307, 460, 307, 506), fill=c, width=7)
    else:
        draw.polygon([(270, 414), (307, 441), (344, 414), (333, 456), (307, 478), (281, 456)], outline=c, width=7); draw.polygon([(289, 459), (307, 479), (325, 459), (320, 499), (294, 499)], fill=c)
    return np.array(image, dtype=np.uint8)


def procedural_face_detail(code: str) -> np.ndarray:
    """Clean black-only facial marks on the locked 512px registration."""
    image, draw = blank_layer()
    c = tuple(INK.tolist() + [255])
    if code in {"FD01", "FD02", "FD03", "FD15"}:
        anchors = {"FD01": (205, 342, 244, 372), "FD02": (282, 220, 338, 205), "FD03": (268, 342, 318, 350), "FD15": (245, 392, 322, 414)}
        x0, y0, x1, y1 = anchors[code]; draw.line((x0, y0, x1, y1), fill=c, width=5)
        for t in range(1, 5):
            x = round(x0 + (x1 - x0) * t / 5); y = round(y0 + (y1 - y0) * t / 5); draw.line((x - 5, y - 6, x + 5, y + 6), fill=c, width=4)
    elif code in {"FD04", "FD05"}:
        box = (342, 334, 384, 354) if code == "FD04" else (202, 334, 244, 360); draw.rounded_rectangle(box, radius=4, outline=c, width=5); draw.line((box[0] + 8, box[1] + 2, box[2] - 8, box[3] - 2), fill=c, width=3)
    elif code == "FD06": draw.ellipse((255, 346, 263, 354), fill=c)
    elif code == "FD07":
        for x, y in [(239, 337), (252, 344), (266, 338), (278, 348), (291, 341)]: draw.ellipse((x, y, x + 5, y + 5), fill=c)
    elif code in {"FD08", "FD09"}:
        draw.line((274, 252, 283, 239), fill=c, width=5)
        if code == "FD09": draw.line((288, 250, 297, 237), fill=c, width=5)
    elif code == "FD10": draw.line((160, 305, 177, 321, 163, 335), fill=c, width=6)
    elif code == "FD11": draw.arc((159, 308, 188, 346), 80, 285, fill=c, width=6)
    elif code == "FD12": draw.ellipse((166, 332, 178, 344), outline=c, width=4); draw.ellipse((181, 343, 193, 355), outline=c, width=4)
    elif code == "FD13": draw.arc((350, 343, 376, 371), 330, 210, fill=c, width=6)
    elif code == "FD14": draw.ellipse((221, 339, 245, 363), outline=c, width=5); draw.line((233, 335, 233, 367), fill=c, width=3); draw.line((217, 351, 249, 351), fill=c, width=3)
    else:
        draw.line((272, 239, 286, 263, 276, 282, 298, 301), fill=c, width=5); draw.line((286, 263, 306, 251), fill=c, width=4); draw.line((276, 282, 257, 292), fill=c, width=4)
    return np.array(image, dtype=np.uint8)


def mask_layer(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    output = image.copy()
    output[:, :, 3] = np.where((image[:, :, 3] > 0) & (mask > 0), 255, 0).astype(np.uint8)
    output[output[:, :, 3] == 0, :3] = 0
    return output


def remove_unapproved_yellow(layer: np.ndarray, category: str, code: str) -> np.ndarray:
    allow = category in {"eyes", "rare"} or code == "HH05"
    if allow:
        return layer
    yellow = np.all(layer[:, :, :3] == YELLOW, axis=2) & (layer[:, :, 3] > 0)
    layer[yellow, 3] = 0
    layer[yellow, :3] = 0
    return layer


def write_zip(path: Path, files: list[tuple[Path, str]]) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for source, name in files:
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main() -> None:
    manifest = json.loads((REVIEW / "manifest.json").read_text())
    traits_by_code = {trait["code"]: trait for trait in manifest["traits"]}
    shutil.rmtree(OUTPUT, ignore_errors=True)
    OUTPUT.mkdir(parents=True)
    records = []
    all_files: list[tuple[Path, str]] = []
    for category in CATEGORY_ORDER:
        source_paths = sorted((SOURCE / category).glob("*.png"))
        codes = [path.stem for path in source_paths]
        # The review cards already share the locked 360→512 nearest-neighbour
        # scale and y=512 body baseline. Re-registering from trait-dependent
        # bounds would move hats, eyewear, and mouths independently and break
        # layer compatibility.
        registered = [load_rgba(path) for path in source_paths]
        consensus = consensus_visible(registered)
        destination = OUTPUT / category
        destination.mkdir(parents=True)
        category_files: list[tuple[Path, str]] = []
        for code, image in zip(codes, registered):
            region = semantic_mask(category, code)
            if category == "hair-headwear":
                layer = seeded_components(image, region, seed_y=245, minimum=18)
            elif category == "eyes":
                layer = mask_layer(image, region)
                layer = filter_components(layer, 18)
            elif category == "eyewear":
                layer = largest_components(image, rectangle_mask(220, 245, 440, 360), maximum=3, minimum=8)
            elif category == "mouths":
                box = (245, 330, 435, 465) if code == "MO14" else (270, 345, 405, 415)
                layer = isolated_box(image, box, minimum=3)
            elif category == "outfits":
                layer = mask_layer(image, region)
                layer = filter_components(layer, 24)
            elif category == "neck":
                layer = procedural_neck(code)
            elif category == "face-details":
                layer = procedural_face_detail(code)
            else:
                layer = mask_layer(image, region)
            layer = remove_unapproved_yellow(layer, category, code)
            if not np.any(layer[:, :, 3]):
                raise ValueError(f"{code} isolated to an empty layer")
            output_path = destination / f"{code}.png"
            Image.fromarray(layer).save(output_path, optimize=True)
            archive_name = f"{category}/{code}.png"
            category_files.append((output_path, f"{code}.png"))
            all_files.append((output_path, archive_name))
            trait = traits_by_code[code]
            records.append({
                "code": code,
                "name": trait["name"],
                "category": category,
                "layer": f"isolated-layers/{archive_name}",
                "referenceCard": trait["card"],
                "canvas": [CANVAS, CANVAS],
                "background": "transparent",
                "bodyBaselineY": CANVAS,
                "sourceScale": "360-to-512-nearest",
                "status": "isolated-review-layer",
            })
        write_zip(OUTPUT / f"neon-nocturne-{category}-layers.zip", category_files)

    write_zip(OUTPUT / "neon-nocturne-all-128-isolated-layers.zip", all_files)
    output_manifest = {
        "collection": "Neon Nocturne",
        "count": len(records),
        "format": "512x512 RGBA PNG",
        "background": "transparent",
        "registration": {"sourceScale": "360-to-512-nearest", "bodyBaselineY": CANVAS, "resampling": "nearest"},
        "categories": list(CATEGORY_ORDER),
        "layers": records,
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(output_manifest, indent=2) + "\n")
    (OUTPUT / "manifest.js").write_text("window.ISOLATED_TRAIT_MANIFEST = " + json.dumps(output_manifest, indent=2) + ";\n")
    print(f"Built {len(records)} categorized isolated review layers")


if __name__ == "__main__":
    main()
