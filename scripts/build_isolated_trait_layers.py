#!/usr/bin/env python3
"""Reconstruct individual V2 layers strictly from approved source pixels.

No trait contour is redrawn. Every visible pixel originates in the matching
approved 512px concept card, is isolated by an explicit category/trait mask,
then enlarged exactly 2x and placed on the locked 1028px canvas.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import cv2
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "review" / "trait-expansion-v2"
SOURCE = REVIEW / "cards-transparent"
OUTPUT = REVIEW / "isolated-layers"
COMPOSED = REVIEW / "composed-layers"
SOURCE_SIZE = 512
ARTBOARD = 1024
CANVAS = 1028
OFFSET = (2, 4)
INK = np.array((2, 1, 2), dtype=np.uint8)
YELLOW = np.array((253, 244, 35), dtype=np.uint8)
LIME = np.array((208, 247, 8), dtype=np.uint8)
GROUPS = (
    ("00-base", None, "Base"),
    ("01-hair-headwear", "hair-headwear", "Hair + Headwear"),
    ("02-eyes", "eyes", "Eyes"),
    ("03-eyewear", "eyewear", "Eyewear"),
    ("04-mouths", "mouths", "Mouths"),
    ("05-clothing", "outfits", "Clothing"),
    ("06-neck-accessories", "neck", "Neck Accessories"),
    ("07-face-details", "face-details", "Face Details"),
    ("08-rare-overrides", "rare", "Rare Overrides"),
)
NECK_BOXES = {
    "NE01": (255,390,360,505), "NE02": (225,390,400,500), "NE03": (215,400,420,490), "NE04": (215,395,420,490),
    "NE05": (205,380,430,512), "NE06": (255,390,385,512), "NE07": (225,400,420,480), "NE08": (260,395,400,505),
    "NE09": (220,405,410,485), "NE10": (255,405,385,512), "NE11": (250,405,395,512), "NE12": (200,390,440,490),
    "NE13": (220,405,420,485), "NE14": (255,410,400,485), "NE15": (255,395,390,512), "NE16": (235,385,415,512),
}
FACE_BOXES = {
    "FD01": (165,300,260,395), "FD02": (250,180,370,275), "FD03": (235,285,350,375), "FD04": (330,295,430,390),
    "FD05": (165,300,280,410), "FD06": (225,300,310,390), "FD07": (210,295,350,390), "FD08": (235,185,345,285),
    "FD09": (225,180,400,290), "FD10": (100,235,245,380), "FD11": (105,240,255,390), "FD12": (100,250,265,430),
    "FD13": (330,300,435,410), "FD14": (185,295,325,420), "FD15": (190,340,365,455), "FD16": (205,180,410,440),
}


def load(path: Path) -> np.ndarray:
    return np.array(Image.open(path).convert("RGBA"), dtype=np.uint8)


def visible(image: np.ndarray) -> np.ndarray:
    return image[:, :, 3] > 0


def rect(x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    mask = np.zeros((SOURCE_SIZE, SOURCE_SIZE), dtype=np.uint8); mask[y0:y1, x0:x1] = 255; return mask


def polygon(points) -> np.ndarray:
    mask = np.zeros((SOURCE_SIZE, SOURCE_SIZE), dtype=np.uint8); cv2.fillPoly(mask, [np.array(points, np.int32)], 255); return mask


def apply_mask(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    keep = visible(image) & (mask > 0); output = np.zeros_like(image); output[keep] = image[keep]; return output


def components(image: np.ndarray, minimum: int = 1) -> list[tuple[int, np.ndarray, np.ndarray]]:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(visible(image).astype(np.uint8), 8)
    return [(label, labels == label, stats[label]) for label in range(1, count) if stats[label, cv2.CC_STAT_AREA] >= minimum]


def keep_seeded(image: np.ndarray, region: np.ndarray, seed_y: int) -> np.ndarray:
    staged = apply_mask(image, region); keep = np.zeros((SOURCE_SIZE, SOURCE_SIZE), bool)
    for _, pixels, stats in components(staged, 18):
        if stats[cv2.CC_STAT_TOP] <= seed_y: keep |= pixels
    output = np.zeros_like(image); output[keep] = image[keep]; return output


def keep_largest(image: np.ndarray, region: np.ndarray, maximum: int, minimum: int = 8) -> np.ndarray:
    staged = apply_mask(image, region); ranked = sorted(components(staged, minimum), key=lambda item: int(item[2][cv2.CC_STAT_AREA]), reverse=True)
    keep = np.zeros((SOURCE_SIZE, SOURCE_SIZE), bool)
    for _, pixels, _ in ranked[:maximum]: keep |= pixels
    output = np.zeros_like(image); output[keep] = image[keep]; return output


def filter_components(image: np.ndarray, minimum: int) -> np.ndarray:
    keep = np.zeros((SOURCE_SIZE, SOURCE_SIZE), bool)
    for _, pixels, _ in components(image, minimum): keep |= pixels
    output = np.zeros_like(image); output[keep] = image[keep]; return output


def consensus(images: list[np.ndarray], threshold: float = .72) -> np.ndarray:
    return np.stack([visible(image) for image in images]).mean(axis=0) >= threshold


def exact_difference(image: np.ndarray, common: np.ndarray, region: np.ndarray, minimum: int = 2) -> np.ndarray:
    changed = np.logical_xor(visible(image), common) & (region > 0)
    output = np.zeros_like(image); output[changed, :3] = INK; output[changed, 3] = 255
    return filter_components(output, minimum)


def positive_difference(
    image: np.ndarray,
    common: np.ndarray,
    region: np.ndarray,
    minimum: int = 2,
    common_dilation: int = 0,
) -> np.ndarray:
    """Keep only source pixels added by this trait, never inverse/erase debris."""
    shared = common.astype(np.uint8)
    if common_dilation:
        shared = cv2.dilate(
            shared,
            np.ones((common_dilation, common_dilation), np.uint8),
            1,
        )
    keep = visible(image) & ~shared.astype(bool) & (region > 0)
    output = np.zeros_like(image)
    output[keep] = image[keep]
    return filter_components(output, minimum)


def positive_against_reference(
    image: np.ndarray,
    reference: np.ndarray,
    region: np.ndarray,
    minimum: int = 2,
) -> np.ndarray:
    """Keep only pixels absent from the separately rendered matched reference."""
    keep = visible(image) & ~visible(reference) & (region > 0)
    output = np.zeros_like(image)
    output[keep] = image[keep]
    return filter_components(output, minimum)


def extract_hair(image: np.ndarray, code: str) -> np.ndarray:
    region = polygon([(20,0),(500,0),(500,330),(440,365),(390,320),(250,300),(205,350),(75,355),(20,300)])
    if code in {"HH05","HH06","HH07","HH11","HH14"}: region = cv2.bitwise_or(region, rect(70,220,470,410))
    return keep_seeded(image, region, 245)


def extract_eyes(image: np.ndarray, code: str) -> np.ndarray:
    yellow = np.all(image[:, :, :3] == YELLOW, axis=2) & visible(image)
    ys, xs = np.where(yellow)
    if not len(xs): raise ValueError(f"{code}: approved yellow eye interior missing")
    midpoint = (int(xs.min()) + int(xs.max())) // 2
    mask = np.zeros((SOURCE_SIZE, SOURCE_SIZE), np.uint8)
    pad_x, pad_y = (20, 22) if code == "EY06" else (13, 17)
    if code in {"EY11","EY16"}: pad_y = 25
    for side in (xs <= midpoint, xs > midpoint):
        sx, sy = xs[side], ys[side]
        if not len(sx): continue
        x0=max(0,int(sx.min())-pad_x); x1=min(512,int(sx.max())+pad_x+1); y0=max(0,int(sy.min())-pad_y); y1=min(512,int(sy.max())+pad_y+1)
        mask[y0:y1,x0:x1]=255
    return filter_components(apply_mask(image, mask), 4)


def extract_eyewear(image: np.ndarray, reference: np.ndarray, code: str) -> np.ndarray:
    return positive_against_reference(image, reference, rect(195,210,465,385), 3)


def extract_mouth(image: np.ndarray, reference: np.ndarray, code: str) -> np.ndarray:
    region = rect(215,330,410,470) if code == "MO14" else rect(220,330,410,450)
    return positive_against_reference(image, reference, region, 2)


def extract_outfit(image: np.ndarray, reference: np.ndarray, code: str) -> np.ndarray:
    region = polygon([(30,340),(175,325),(245,385),(420,340),(500,375),(500,512),(30,512)])
    return positive_against_reference(image, reference, region, 4)


def extract_neck(image: np.ndarray, reference: np.ndarray, code: str) -> np.ndarray:
    x0,y0,x1,y1=NECK_BOXES[code]
    return positive_against_reference(image, reference, rect(x0,y0,x1,y1), 2)


def extract_face(image: np.ndarray, reference: np.ndarray, code: str) -> np.ndarray:
    x0,y0,x1,y1=FACE_BOXES[code]
    return positive_against_reference(image, reference, rect(x0,y0,x1,y1), 2)


def extract_base(common: np.ndarray) -> np.ndarray:
    source = load(SOURCE / "face-details" / "FD06.png")
    mask = np.zeros((512,512),np.uint8)
    # Exact ear, jaw/cheek outline, brows, nose and neck construction only.
    for region in (
        polygon([(90,235),(225,245),(245,385),(125,390)]),
        polygon([(185,230),(250,190),(450,205),(470,410),(405,455),(215,430),(170,340)]),
        rect(220,205,430,290), rect(330,285,445,390), rect(185,360,455,455),
    ): mask=cv2.bitwise_or(mask,region)
    # Remove feature interiors owned by separate layers and all hair/outfit fills.
    for region in (rect(225,255,430,365), rect(220,345,415,425), rect(0,0,512,210), rect(0,445,512,512)):
        mask[region>0]=0
    mask = cv2.bitwise_and(mask, common.astype(np.uint8) * 255)
    return filter_components(apply_mask(source,mask),3)


def to_canvas(image: np.ndarray) -> Image.Image:
    art=Image.fromarray(image).resize((ARTBOARD,ARTBOARD),Image.Resampling.NEAREST)
    canvas=Image.new("RGBA",(CANVAS,CANVAS),(0,0,0,0)); canvas.alpha_composite(art,OFFSET); return canvas


def remove_yellow(image: np.ndarray) -> np.ndarray:
    output=image.copy(); yellow=np.all(output[:,:,:3]==YELLOW,axis=2)&visible(output); output[yellow]=0; return output


def on_lime(layers: list[Image.Image]) -> Image.Image:
    canvas=Image.new("RGBA",(CANVAS,CANVAS),(*LIME.tolist(),255))
    for layer in layers: canvas.alpha_composite(layer)
    return canvas.convert("RGB")


def write_zip(path: Path, files: list[tuple[Path,str]]) -> None:
    with ZipFile(path,"w",ZIP_DEFLATED) as archive:
        for source,name in files:
            info=ZipInfo(name,date_time=(2026,1,1,0,0,0)); info.compress_type=ZIP_DEFLATED; info.external_attr=0o100644<<16
            archive.writestr(info,source.read_bytes())


def main() -> None:
    manifest=json.loads((REVIEW/"manifest.json").read_text()); by_source={source:[] for _,source,_ in GROUPS if source}
    for trait in manifest["traits"]: by_source[trait["category"]].append(trait)
    shutil.rmtree(OUTPUT,ignore_errors=True); OUTPUT.mkdir(); shutil.rmtree(COMPOSED,ignore_errors=True); COMPOSED.mkdir()
    source_images={category:[load(SOURCE/category/f"{trait['code']}.png") for trait in sorted(traits,key=lambda item:item["code"])] for category,traits in by_source.items()}
    common={category:consensus(images) for category,images in source_images.items()}
    records=[]; all_files=[]; base=to_canvas(extract_base(common["face-details"])); base_dir=OUTPUT/"00-base"; base_dir.mkdir(); base_path=base_dir/"BASE01.png"; base.save(base_path,optimize=True)
    records.append({"code":"BASE01","name":"Approved Locked Base","category":"00-base","categoryLabel":"Base","sourceCategory":None,"layer":"isolated-layers/00-base/BASE01.png","referenceCard":"composed-layers/00-base/BASE01.png","canvas":[CANVAS,CANVAS],"sourceCanvas":[512,512],"background":"transparent","bodyBaselineY":CANVAS,"resampling":"nearest","status":"approved-pixel-reconstruction"})
    all_files.append((base_path,"00-base/BASE01.png")); write_zip(OUTPUT/"neon-nocturne-00-base-layers.zip",[(base_path,"BASE01.png")])
    for folder,category,label in GROUPS[1:]:
        destination=OUTPUT/folder; destination.mkdir(); category_files=[]
        for trait_index, (trait,image) in enumerate(zip(sorted(by_source[category],key=lambda item:item["code"]),source_images[category])):
            code=trait["code"]
            neutral_reference=source_images["hair-headwear"][trait_index]
            outfit_reference=source_images["outfits"][trait_index]
            if category=="hair-headwear": layer=extract_hair(image,code)
            elif category=="eyes": layer=extract_eyes(image,code)
            elif category=="eyewear": layer=extract_eyewear(image,neutral_reference,code)
            elif category=="mouths": layer=extract_mouth(image,neutral_reference,code)
            elif category=="outfits": layer=extract_outfit(image,neutral_reference,code)
            elif category=="neck": layer=extract_neck(image,outfit_reference,code)
            elif category=="face-details": layer=extract_face(image,neutral_reference,code)
            else: layer=image
            if category not in {"eyes","rare"} and code != "HH05": layer=remove_yellow(layer)
            if not np.any(layer[:,:,3]): raise ValueError(f"{code}: empty reconstruction")
            output=destination/f"{code}.png"; to_canvas(layer).save(output,optimize=True); archive_name=f"{folder}/{code}.png"; category_files.append((output,f"{code}.png")); all_files.append((output,archive_name))
            records.append({"code":code,"name":trait["name"],"category":folder,"categoryLabel":label,"sourceCategory":category,"layer":f"isolated-layers/{archive_name}","referenceCard":f"composed-layers/{folder}/{code}.png","canvas":[CANVAS,CANVAS],"sourceCanvas":[512,512],"background":"transparent","bodyBaselineY":CANVAS,"resampling":"nearest","status":"approved-source-pixel-reconstruction" if category!="rare" else "approved-full-character-override"})
        write_zip(OUTPUT/f"neon-nocturne-{folder}-layers.zip",category_files)
    write_zip(OUTPUT/"neon-nocturne-all-129-generator-layers.zip",all_files)
    paths={record["code"]:OUTPUT/record["category"]/f"{record['code']}.png" for record in records}
    def layer(code): return Image.open(paths[code]).convert("RGBA")
    for record in records:
        folder=record["category"]; code=record["code"]; dest=COMPOSED/folder; dest.mkdir(exist_ok=True)
        if code=="BASE01": preview=on_lime([base])
        elif folder=="08-rare-overrides": preview=on_lime([layer(code)])
        else:
            chosen={"01-hair-headwear":"HH01","02-eyes":"EY01","03-eyewear":None,"04-mouths":"MO01","05-clothing":"OF05","06-neck-accessories":None,"07-face-details":None}; chosen[folder]=code
            stack=[layer("OF05"),base,layer(chosen["01-hair-headwear"]),layer(chosen["02-eyes"]),layer(chosen["04-mouths"])]
            for overlay in ("03-eyewear","06-neck-accessories","07-face-details"):
                if chosen[overlay]: stack.append(layer(chosen[overlay]))
            preview=on_lime(stack)
        preview.save(dest/f"{code}.png",optimize=True)
    output_manifest={"collection":"Neon Nocturne","count":len(records),"traitCount":128,"baseCount":1,"totalLayerFileCount":len(records),"format":"1028x1028 RGBA PNG","background":"transparent","sourceMethod":"exact-approved-pixel-reconstruction","registration":{"sourceCanvas":[512,512],"artboard":[ARTBOARD,ARTBOARD],"offset":list(OFFSET),"bodyBaselineY":CANVAS,"resampling":"nearest"},"categories":[folder for folder,_,_ in GROUPS],"layers":records}
    (OUTPUT/"manifest.json").write_text(json.dumps(output_manifest,indent=2)+"\n"); (OUTPUT/"manifest.js").write_text("window.ISOLATED_TRAIT_MANIFEST = "+json.dumps(output_manifest,indent=2)+";\n")
    print(f"Reconstructed {len(records)} individual layers exclusively from approved source pixels")


if __name__=="__main__": main()
