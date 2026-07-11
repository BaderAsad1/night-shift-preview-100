#!/usr/bin/env python3
"""Build the canonical layered Night Shift one-bit production art system."""

from __future__ import annotations

import argparse
import json
from itertools import islice
from pathlib import Path
from random import Random
from hashlib import sha256
from shutil import copy2, copytree, rmtree
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageDraw


DESIGN_GRID = 128
LOW = 256
COORD_SCALE = LOW // DESIGN_GRID
SCALE = 4
SIZE = LOW * SCALE
INK = (2, 1, 2, 255)
YELLOW = (253, 244, 35, 255)
CLEAR = (0, 0, 0, 0)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


BASES = [
    "Classic Point", "Narrow Night", "Round Bite", "Wide Signal",
    "Tall Velvet", "Soft Jaw", "Sharp Chin", "Compact Fang",
]
HEADWEAR = [
    "Raven Wave", "Living Flame", "Pom Beanie", "Webbed Wave", "Flight Goggles",
    "Little Horns", "Mummy Wrap", "Coven Hat", "Spectral Wave", "Slick Curl",
    "Moon Beanie", "Spider Bob", "Aviator Crop", "Retro Visor", "Moth Antennae",
    "Wolf Ears", "Deep Rain Hood", "Sleek Bob", "Bat Courier Helmet", "High Pompadour",
    "Broadcast Headset", "Moonclip Bob", "Spiked Crest", "Roundglass Wave", "Broad Fedora",
    "Race Helmet", "Captain Cap", "Wild Side Hair", "Finger Wave", "Backward Cap",
]
EYES = [
    "Hollow Ovals", "Soft Glow", "Shadow Fade", "Long Lashes", "X Glow", "Angry Arches",
    "Mummy Glow", "Wide Awake", "Night Fade", "Hypno Spirals", "Sleepy Glow", "Web Liner",
    "Goggle Glow", "Visor Glow", "Moth Dark", "Wolf Slant", "Rain Focus", "Bob Lashes",
    "Courier Scan", "Rider Squint", "Broadcast Rings", "Moon Gaze", "Spike Stare", "Lens Glow",
]
MOUTHS = [
    "Twin Fangs", "Side Smirk", "Open Bite", "Quiet Fang", "Zigzag Bite", "Flat Mood",
    "Happy Fangs", "Single Fang", "Underbite", "Small O", "Crooked Grin", "Sharp Smile",
    "Night Pout", "Three Teeth", "Half Bite", "Pixel Laugh",
]
OUTFITS = [
    "Skull Tux", "High Collar", "Medallion Cape", "Striped Knit", "Undertaker Shirt",
    "Winged Cape", "Wrapped Tunic", "Coven Coat", "Chain Crewneck", "Velvet Jacket",
    "Skeleton Hoodie", "Webbed Court", "Fur Flight Jacket", "Utility Coat", "Moth Velvet",
    "Varsity Jacket", "Technical Shell", "Geometric Collar", "Messenger Rig", "Biker Jacket",
    "Broadcast Jacket", "Quilted Coat", "Armored Vest", "Knit Cardigan", "Trench Collar",
    "Racing Jacket", "Heavy Pea Coat", "Tool Apron", "Fur Collar", "Oversized Hoodie",
]
ACCESSORIES = [
    "Ear Cuff", "Brow Slit", "Cheek Scar", "Nose Ring", "Pixel Tear", "Face Bandage",
    "Jaw Bolts", "Temple Circuit", "Monocle", "Mini Shades", "Ear Tag", "Cheek Stripes",
    "Moon Clip", "Headset Mic", "Bridge Stud", "Double Earring", "Eye Spark", "Side Patch",
    "Brow Studs", "Fang Chain",
]
NAME_GROUPS = (BASES, HEADWEAR, EYES, MOUTHS, OUTFITS, ACCESSORIES)
CATEGORY_NAMES = {
    "Base": BASES, "Headwear": HEADWEAR, "Eyes": EYES,
    "Mouth": MOUTHS, "Outfit": OUTFITS, "Accessory": ACCESSORIES,
}


def rarity_tier(index: int, count: int) -> str:
    position = (index + 1) / count
    if position <= 0.55:
        return "Common"
    if position <= 0.78:
        return "Uncommon"
    if position <= 0.93:
        return "Rare"
    return "Legendary"


RARITY_WEIGHTS = {"Common": 8, "Uncommon": 4, "Rare": 2, "Legendary": 1}


def canvas() -> Image.Image:
    return Image.new("RGBA", (LOW, LOW), CLEAR)


def draw(image: Image.Image) -> ImageDraw.ImageDraw:
    return ImageDraw.Draw(image)


def line(d: ImageDraw.ImageDraw, points, fill=INK, width=2) -> None:
    scaled = [(x * COORD_SCALE, y * COORD_SCALE) for x, y in points]
    d.line(scaled, fill=fill, width=max(2, round(width * 1.5)), joint="curve")


def polygon(d: ImageDraw.ImageDraw, points, fill=INK) -> None:
    d.polygon([(x * COORD_SCALE, y * COORD_SCALE) for x, y in points], fill=fill)


def ellipse(d: ImageDraw.ImageDraw, box, fill=INK, outline=None, width=1) -> None:
    scaled = tuple(value * COORD_SCALE for value in box)
    d.ellipse(scaled, fill=fill, outline=outline, width=max(2, round(width * 1.5)))


def rect(d: ImageDraw.ImageDraw, box, fill=INK, outline=None, width=1) -> None:
    scaled = tuple(value * COORD_SCALE for value in box)
    d.rectangle(scaled, fill=fill, outline=outline, width=max(2, round(width * 1.5)))


def cut_line(d: ImageDraw.ImageDraw, points, width=1) -> None:
    line(d, points, CLEAR, width)


def cut_polygon(d: ImageDraw.ImageDraw, points) -> None:
    polygon(d, points, CLEAR)


def eye_pair(d: ImageDraw.ImageDraw, boxes, inner=YELLOW, outline=INK, inset=2) -> None:
    for box in boxes:
        ellipse(d, box, fill=outline)
        ellipse(d, (box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset), fill=inner)


def draw_base(index: int) -> Image.Image:
    im = canvas(); d = draw(im)
    variants = [
        (39, 91, 42, 88, 29, 99), (42, 88, 41, 88, 31, 97),
        (37, 93, 40, 89, 28, 100), (35, 95, 42, 87, 26, 102),
        (40, 90, 38, 90, 30, 98), (38, 92, 43, 87, 29, 99),
        (39, 91, 40, 92, 28, 100), (41, 89, 44, 86, 31, 97),
    ]
    left, right, temple_y, chin_y, ear_left, ear_right = variants[index]
    # Outfit sits behind this layer. The open forehead is closed by headwear.
    face = [(left, temple_y), (left - 2, 52), (left - 1, 68), (43, 79),
            (52, 86), (65, chin_y), (78, 86), (87, 79), (right + 1, 68),
            (right + 2, 52), (right, temple_y)]
    line(d, face, width=2)
    # Pointed ears and inner ear lines remain common anchors.
    line(d, [(left, 53), (ear_left, 48), (ear_left + 2, 63), (left + 2, 69)], width=2)
    line(d, [(ear_left + 3, 53), (left - 2, 59), (ear_left + 4, 58)], width=1)
    line(d, [(right, 53), (ear_right, 48), (ear_right - 2, 63), (right - 2, 69)], width=2)
    line(d, [(ear_right - 3, 53), (right + 2, 59), (ear_right - 4, 58)], width=1)
    # Nose and neck are fixed registration marks.
    line(d, [(63, 67), (65, 69), (69, 68)], width=2)
    line(d, [(53, 87), (52, 94)], width=2)
    line(d, [(77, 87), (78, 94)], width=2)
    if index in (1, 6):
        line(d, [(42, 74), (46, 78)], width=1)
    if index in (2, 5):
        line(d, [(85, 72), (82, 77)], width=1)
    return im


def hair_mass(d, points, cutouts=()) -> None:
    polygon(d, points, INK)
    for cut in cutouts:
        cut_polygon(d, cut)


def draw_headwear(index: int) -> Image.Image:
    im = canvas(); d = draw(im); i = index
    if i == 0:  # Raven wave
        hair_mass(d, [(37,53),(34,39),(43,31),(62,29),(78,32),(88,39),(91,49),(82,45),(76,39),(72,48),(64,39),(57,47),(49,39),(45,52)])
        polygon(d, [(78,32),(88,27),(91,30),(88,37)], INK)
    elif i == 1:  # Living flame
        flames=[[(37,54),(33,43),(38,32),(42,39),(45,22),(50,34),(57,15),(61,34),(68,21),(70,38),(79,17),(80,38),(88,30),(91,49),(84,53)]]
        for p in flames: polygon(d,p,YELLOW); line(d,p+[p[0]],INK,1)
        for p in ([(31,38),(33,30),(36,36)],[(92,29),(95,23),(96,34)],[(84,20),(86,13),(89,24)]):
            polygon(d,p,YELLOW); line(d,p+[p[0]],INK,1)
    elif i == 2:
        polygon(d, [(38,50),(38,34),(44,27),(80,27),(90,35),(90,50)], INK)
        cut_line(d, [(43,35),(85,35)],1); cut_line(d,[(47,29),(48,47)],1); cut_line(d,[(55,28),(56,47)],1); cut_line(d,[(66,28),(66,46)],1); cut_line(d,[(77,29),(76,47)],1)
        ellipse(d,(53,17,68,30),INK); ellipse(d,(57,20,64,26),CLEAR)
    elif i == 3:
        hair_mass(d,[(35,54),(35,38),(45,28),(65,25),(84,31),(92,43),(90,53),(80,47),(71,42),(63,49),(54,42),(46,51)])
        line(d,[(48,31),(69,44),(85,30)],CLEAR,1); line(d,[(55,28),(76,45)],CLEAR,1)
        line(d,[(68,27),(73,34),(80,27),(77,38),(88,40)],CLEAR,1)
    elif i == 4:
        hair_mass(d,[(36,54),(36,37),(48,29),(78,30),(90,40),(90,53),(79,45),(70,42),(62,49),(52,42),(44,52)])
        ellipse(d,(43,25,61,39),INK); ellipse(d,(66,25,84,39),INK); ellipse(d,(47,28,58,36),CLEAR); ellipse(d,(69,28,81,36),CLEAR); line(d,[(60,31),(67,31)],INK,2)
    elif i == 5:
        hair_mass(d,[(38,53),(38,38),(48,31),(79,32),(90,42),(89,53),(80,47),(70,42),(62,49),(52,42),(44,52)])
        polygon(d,[(46,34),(44,20),(53,34)],INK); polygon(d,[(76,34),(83,19),(85,40)],INK)
    elif i == 6:
        for y,x0,x1 in [(31,42,86),(37,37,90),(43,35,92),(49,35,92)]:
            polygon(d,[(x0,y),(x1,y-2),(x1+1,y+5),(x0+1,y+7)],INK); cut_line(d,[(x0+3,y+2),(x1-2,y+1)],1)
        line(d,[(39,29),(35,49)],INK,2); line(d,[(86,26),(92,51)],INK,2)
    elif i == 7:
        polygon(d,[(31,43),(39,34),(43,18),(75,18),(84,34),(98,41),(91,50),(80,46),(72,40),(61,48),(51,40),(43,51)],INK)
        cut_polygon(d,[(43,33),(77,33),(73,37),(45,37)]); rect(d,(56,13,76,18),INK); cut_line(d,[(60,16),(73,16)],1)
    elif i == 8:
        hair_mass(d,[(39,53),(35,38),(46,29),(78,30),(89,40),(91,53),(82,48),(74,41),(65,49),(56,41),(47,52)])
        for pts in ([(30,31),(26,25),(29,18),(32,24)],[(92,27),(96,20),(98,29)],[(35,18),(39,11),(41,21)]):
            line(d,pts,YELLOW,3); line(d,pts,INK,1)
    elif i == 9:
        hair_mass(d,[(38,53),(36,39),(46,31),(64,29),(81,33),(90,43),(89,53),(82,47),(72,40),(65,49),(57,41),(46,51)])
        polygon(d,[(70,31),(79,25),(88,27),(84,34)],INK)
    elif i == 10:
        polygon(d,[(37,50),(38,35),(48,28),(82,29),(90,38),(89,50)],INK); cut_line(d,[(44,36),(84,36)],1)
        ellipse(d,(50,19,62,30),INK); ellipse(d,(53,22,59,27),CLEAR)
    elif i == 11:
        hair_mass(d,[(34,55),(35,37),(48,27),(79,30),(91,42),(91,54),(80,45),(72,42),(65,49),(55,42),(44,52)])
        line(d,[(45,31),(55,40),(68,27),(80,41),(88,33)],CLEAR,1)
        rect(d,(75,25,79,29),CLEAR); line(d,[(73,24),(82,31)],CLEAR,1)
    elif i == 12:
        hair_mass(d,[(35,53),(36,36),(49,28),(80,31),(91,43),(90,54),(80,46),(72,41),(63,49),(53,41),(44,52)])
        rect(d,(39,26,86,34),INK); cut_line(d,[(42,30),(84,30)],1)
    elif i == 13:
        hair_mass(d,[(37,54),(37,37),(49,29),(79,30),(90,41),(90,53),(81,45),(71,41),(64,49),(54,41),(44,52)])
        polygon(d,[(39,43),(90,41),(88,50),(42,51)],INK); rect(d,(47,44,61,48),YELLOW); rect(d,(68,43,83,47),YELLOW)
    elif i == 14:
        hair_mass(d,[(39,53),(38,38),(49,31),(78,31),(89,42),(89,53),(81,46),(72,42),(64,49),(55,42),(46,52)])
        line(d,[(50,32),(45,17),(39,10)],INK,2); line(d,[(77,32),(82,17),(89,9)],INK,2); line(d,[(39,10),(35,13)],INK,2); line(d,[(89,9),(94,12)],INK,2)
    elif i == 15:
        hair_mass(d,[(38,54),(37,38),(48,29),(79,31),(90,42),(90,54),(81,46),(71,42),(64,49),(54,41),(45,52)])
        polygon(d,[(41,35),(36,15),(51,31)],INK); polygon(d,[(76,31),(92,15),(87,40)],INK); cut_line(d,[(40,23),(47,31)],1); cut_line(d,[(83,30),(89,22)],1)
    elif i == 16:
        polygon(d,[(31,52),(32,31),(43,17),(65,12),(86,19),(97,35),(96,60),(88,51),(87,37),(78,29),(67,26),(54,28),(44,36),(42,53)],INK)
        cut_line(d,[(38,34),(47,25),(65,20),(83,26),(91,37)],1)
    elif i == 17:
        polygon(d,[(32,56),(33,35),(48,25),(72,25),(91,37),(94,62),(87,68),(86,45),(79,38),(71,47),(63,39),(54,48),(45,40),(42,64)],INK)
        cut_line(d,[(36,39),(43,34)],1)
    elif i == 18:
        polygon(d,[(31,57),(31,31),(43,20),(82,20),(96,34),(96,58),(89,53),(88,37),(79,30),(48,29),(40,39),(40,55)],INK)
        cut_line(d,[(38,27),(89,27)],1); rect(d,(27,41,34,58),INK); rect(d,(94,41,101,58),INK)
    elif i == 19:
        hair_mass(d,[(36,55),(35,41),(42,31),(58,25),(78,27),(91,41),(90,53),(82,47),(74,41),(66,50),(58,41),(47,51)])
        polygon(d,[(41,33),(47,18),(57,29),(66,14),(72,29),(83,19),(82,35)],INK)
    elif i == 20:
        hair_mass(d,[(36,54),(35,39),(47,29),(78,30),(91,42),(90,54),(81,46),(72,42),(64,49),(54,42),(45,52)])
        rect(d,(27,35,39,59),INK); rect(d,(90,35,102,59),INK); ellipse(d,(29,39,36,55),CLEAR); ellipse(d,(93,39,99,55),CLEAR); line(d,[(99,54),(104,65),(98,69)],INK,2)
    elif i == 21:
        hair_mass(d,[(34,57),(35,37),(47,28),(79,30),(93,41),(94,62),(86,67),(86,45),(78,40),(69,48),(61,40),(52,48),(43,41),(42,64)])
        ellipse(d,(75,25,80,30),YELLOW)
    elif i == 22:
        hair_mass(d,[(37,55),(36,38),(48,29),(79,30),(91,42),(90,54),(81,46),(72,42),(64,49),(54,42),(45,52)])
        for x,y in [(43,30),(52,23),(62,26),(72,20),(81,28),(88,34)]:polygon(d,[(x-3,y+8),(x,y),(x+4,y+9)],INK)
    elif i == 23:
        hair_mass(d,[(37,54),(36,38),(47,29),(79,30),(91,42),(90,53),(81,46),(72,41),(64,49),(54,41),(45,52)])
        ellipse(d,(42,38,59,54),INK); ellipse(d,(69,38,86,54),INK); ellipse(d,(46,42,56,51),CLEAR); ellipse(d,(72,42,82,51),CLEAR); line(d,[(59,45),(69,45)],INK,2)
    elif i == 24:
        hair_mass(d,[(36,54),(36,39),(47,30),(78,31),(90,42),(89,53),(81,46),(72,42),(64,49),(55,42),(45,52)])
        polygon(d,[(24,31),(43,19),(87,20),(103,31),(90,37),(35,37)],INK); cut_line(d,[(35,30),(91,30)],1)
    elif i == 25:
        polygon(d,[(29,57),(29,29),(43,15),(84,15),(99,31),(99,58),(91,54),(90,37),(82,28),(45,28),(38,38),(38,55)],INK)
        cut_line(d,[(38,22),(89,22)],1); rect(d,(27,39,34,59),INK); rect(d,(95,39,102,59),INK)
    elif i == 26:
        hair_mass(d,[(37,53),(36,39),(47,31),(78,31),(89,42),(89,53),(80,46),(71,42),(63,49),(54,42),(45,52)])
        polygon(d,[(36,32),(43,20),(79,19),(91,30),(84,37),(42,36)],INK); cut_line(d,[(45,25),(80,24)],1)
    elif i == 27:
        hair_mass(d,[(34,55),(35,36),(45,29),(54,30),(58,20),(65,30),(75,22),(79,33),(90,39),(92,54),(81,46),(72,41),(64,49),(53,41),(44,52)])
        ellipse(d,(42,25,57,36),INK); ellipse(d,(68,24,84,35),INK); ellipse(d,(46,28,54,33),CLEAR); ellipse(d,(72,27,80,32),CLEAR)
    elif i == 28:
        hair_mass(d,[(35,55),(34,39),(45,30),(58,27),(77,31),(91,43),(91,55),(82,47),(73,41),(65,50),(56,42),(45,52)])
        line(d,[(42,33),(50,24),(60,31),(68,23),(78,34)],CLEAR,1)
    else:
        hair_mass(d,[(38,54),(37,39),(48,30),(78,31),(89,42),(89,53),(81,46),(72,41),(64,49),(55,42),(45,52)])
        polygon(d,[(42,24),(68,20),(87,25),(93,31),(83,34),(44,32)],INK); cut_line(d,[(49,27),(82,27)],1)
    return im


def draw_eyes(index: int) -> Image.Image:
    im = canvas(); d = draw(im); boxes=((47,51,59,68),(70,51,82,68)); i=index
    if i in (0,1,7,11,17,21):
        eye_pair(d, boxes, inset=2)
        if i==1:
            ellipse(d,(52,57,55,63),INK); ellipse(d,(75,57,78,63),INK)
        if i==11:
            line(d,[(46,50),(51,47),(58,49)],INK,1); line(d,[(70,49),(77,47),(83,50)],INK,1)
        if i==17:
            for x in (46,58,69,82):line(d,[(x,51),(x-2 if x<65 else x+2,48)],INK,1)
    elif i==2:
        for b in boxes:
            ellipse(d,b,INK); polygon(d,[(b[0]+2,b[1]+8),(b[2]-2,b[1]+8),(b[2]-3,b[3]-2),(b[0]+3,b[3]-2)],YELLOW)
    elif i==3:
        eye_pair(d,boxes,inset=2)
        for x in (47,51,55,70,74,78):line(d,[(x,51),(x-1,47)],INK,1)
    elif i==4:
        for b in boxes:
            rect(d,b,INK); rect(d,(b[0]+2,b[1]+2,b[2]-2,b[3]-2),YELLOW); line(d,[(b[0]+3,b[1]+3),(b[2]-3,b[3]-3)],INK,2); line(d,[(b[2]-3,b[1]+3),(b[0]+3,b[3]-3)],INK,2)
    elif i in (5,15,19,22):
        polygon(d,[(45,56),(52,49),(60,53),(58,68),(49,67)],INK); polygon(d,[(69,53),(77,49),(84,56),(81,67),(72,68)],INK)
        polygon(d,[(49,56),(53,53),(57,55),(56,64),(51,64)],YELLOW); polygon(d,[(72,55),(76,53),(81,56),(79,64),(74,64)],YELLOW)
    elif i==6:
        for b in boxes:
            rect(d,b,INK); ellipse(d,(b[0]+3,b[1]+3,b[2]-2,b[3]-2),YELLOW)
        line(d,[(44,50),(61,47)],INK,2); line(d,[(68,47),(85,50)],INK,2)
    elif i==8:
        for b in boxes:
            ellipse(d,b,INK); rect(d,(b[0]+2,b[1]+2,b[2]-2,b[1]+8),INK); ellipse(d,(b[0]+3,b[1]+7,b[2]-3,b[3]-2),YELLOW)
    elif i==9:
        eye_pair(d,boxes,inset=2)
        for cx in (53,76):
            line(d,[(cx,55),(cx+3,57),(cx+2,62),(cx-2,64),(cx-4,61),(cx-3,57),(cx,56)],INK,1)
    elif i==10:
        polygon(d,[(46,57),(52,52),(59,56),(58,63),(49,64)],INK); polygon(d,[(70,56),(77,52),(83,57),(80,64),(72,63)],INK)
        line(d,[(49,60),(57,59)],YELLOW,2); line(d,[(73,59),(81,60)],YELLOW,2)
    elif i in (12,20,23):
        for b in boxes:
            ellipse(d,(b[0]-2,b[1]-2,b[2]+2,b[3]+2),INK); ellipse(d,b,CLEAR); ellipse(d,(b[0]+2,b[1]+2,b[2]-2,b[3]-2),YELLOW)
        line(d,[(60,58),(69,58)],INK,2)
    elif i in (13,18):
        rect(d,(43,51,86,68),INK); rect(d,(47,55,61,64),YELLOW); rect(d,(68,55,82,64),YELLOW); line(d,[(63,54),(66,65)],CLEAR,1)
    elif i==14:
        for b in boxes:
            ellipse(d,b,INK); ellipse(d,(b[0]+3,b[1]+5,b[2]-3,b[3]-2),YELLOW); rect(d,(b[0]+2,b[1]+2,b[2]-2,b[1]+7),INK)
    elif i==16:
        eye_pair(d,boxes,inset=2); line(d,[(46,49),(59,47)],INK,2); line(d,[(70,47),(84,49)],INK,2)
    else:
        eye_pair(d,boxes,inset=2); ellipse(d,(51,55,56,64),INK); ellipse(d,(74,55,79,64),INK)
    # Distinguish related eye families with intentional expression details.
    if i == 7:
        ellipse(d,(51,55,55,64),INK); ellipse(d,(74,55,78,64),INK)
    elif i == 15:
        rect(d,(52,57,55,63),INK); rect(d,(75,57,78,63),INK)
    elif i == 18:
        cut_line(d,[(47,59),(82,59)],1); rect(d,(62,56,66,62),YELLOW)
    elif i == 19:
        line(d,[(49,59),(57,58)],INK,2); line(d,[(72,58),(81,59)],INK,2)
    elif i == 20:
        ellipse(d,(50,54,57,65),INK); ellipse(d,(73,54,80,65),INK); ellipse(d,(52,56,55,62),YELLOW); ellipse(d,(75,56,78,62),YELLOW)
    elif i == 21:
        ellipse(d,(51,54,56,65),INK); ellipse(d,(74,54,79,65),INK); line(d,[(54,55),(56,58)],YELLOW,1); line(d,[(77,55),(79,58)],YELLOW,1)
    elif i == 22:
        for x in (48,52,56,72,76,80): line(d,[(x,52),(x,48)],INK,1)
    elif i == 23:
        line(d,[(48,55),(55,62)],INK,1); line(d,[(71,55),(78,62)],INK,1)
    return im


def draw_mouth(index: int) -> Image.Image:
    im=canvas();d=draw(im);i=index
    if i==0: line(d,[(53,75),(58,79),(65,77),(72,79),(78,75)],INK,2); polygon(d,[(57,78),(60,78),(59,84)],INK); polygon(d,[(72,78),(75,78),(74,84)],INK)
    elif i==1: line(d,[(54,78),(62,81),(75,76)],INK,2); polygon(d,[(72,77),(75,76),(74,82)],INK)
    elif i==2: ellipse(d,(55,74,76,85),INK); ellipse(d,(58,77,73,82),CLEAR); polygon(d,[(59,77),(62,77),(61,82)],INK); polygon(d,[(69,77),(72,77),(71,82)],INK)
    elif i==3: line(d,[(58,78),(72,78)],INK,2); polygon(d,[(59,78),(62,78),(61,84)],INK)
    elif i==4: line(d,[(53,78),(57,74),(62,79),(67,74),(72,79),(77,75)],INK,2)
    elif i==5: line(d,[(56,79),(74,79)],INK,2)
    elif i==6: line(d,[(53,76),(59,82),(66,84),(73,81),(78,76)],INK,2); polygon(d,[(58,80),(61,81),(60,85)],INK); polygon(d,[(72,80),(75,79),(74,84)],INK)
    elif i==7: line(d,[(57,78),(73,78)],INK,2); polygon(d,[(70,78),(73,78),(72,84)],INK)
    elif i==8: line(d,[(55,77),(63,80),(75,77)],INK,2); polygon(d,[(61,80),(65,80),(63,85)],INK)
    elif i==9: ellipse(d,(61,76,69,84),INK); ellipse(d,(63,78,67,82),CLEAR)
    elif i==10: line(d,[(54,77),(61,80),(67,77),(75,81)],INK,2); polygon(d,[(58,79),(61,80),(60,84)],INK)
    elif i==11: line(d,[(54,80),(59,76),(65,79),(72,75),(78,79)],INK,2); polygon(d,[(57,78),(60,77),(59,83)],INK); polygon(d,[(72,76),(75,77),(73,82)],INK)
    elif i==12: line(d,[(58,80),(65,82),(72,80)],INK,2)
    elif i==13: line(d,[(54,77),(77,77)],INK,2); [polygon(d,[(x,77),(x+3,77),(x+1,82)],INK) for x in (56,64,72)]
    elif i==14: line(d,[(55,76),(64,80),(75,78)],INK,2); polygon(d,[(58,77),(61,78),(59,83)],INK); polygon(d,[(71,79),(74,78),(73,83)],INK)
    else: ellipse(d,(53,74,78,86),INK); ellipse(d,(57,78,74,83),CLEAR); [polygon(d,[(x,78),(x+3,78),(x+1,82)],INK) for x in (58,65,71)]
    return im


def garment(d, top=91, left=25, right=104, neck_left=54, neck_right=76) -> None:
    polygon(d,[(left,128),(left,107),(34,97),(50,91),(neck_left,91),(55,96),(75,96),(neck_right,91),(82,91),(97,98),(right,108),(right,128)],INK)


def draw_outfit(index: int) -> Image.Image:
    im=canvas();d=draw(im);i=index
    if i in {1,2,5,9,14,17,24,28}:
        garment(d, left=19, right=111)
    elif i in {10,16,21,29}:
        garment(d, left=22, right=108)
    elif i in {18,22,25,27}:
        garment(d, left=20, right=110)
    else:
        garment(d)
    if i==0:
        cut_polygon(d,[(50,91),(65,101),(80,91),(75,99),(55,99)]); ellipse(d,(59,100,71,112),CLEAR); rect(d,(63,104,67,109),INK); polygon(d,[(61,111),(65,108),(69,111)],CLEAR)
    elif i==1: cut_polygon(d,[(46,91),(55,103),(65,96),(75,103),(84,91),(78,111),(52,111)]); line(d,[(48,94),(65,111),(82,94)],CLEAR,2)
    elif i==2: cut_line(d,[(45,95),(65,111),(85,95)],2); ellipse(d,(61,103,69,111),YELLOW); ellipse(d,(63,105,67,109),INK)
    elif i==3:
        for y in (100,110,120):cut_line(d,[(29,y),(101,y)],2)
    elif i==4: cut_line(d,[(48,92),(52,128)],1); cut_line(d,[(81,92),(77,128)],1); rect(d,(61,101,68,108),CLEAR); ellipse(d,(63,103,66,106),INK)
    elif i==5: cut_polygon(d,[(44,92),(24,105),(36,111),(51,100)]); cut_polygon(d,[(84,92),(105,105),(93,111),(78,100)]); line(d,[(48,94),(65,111),(82,94)],CLEAR,2)
    elif i==6:
        for y in (96,104,112,120):cut_line(d,[(30,y),(99,y+3)],2)
        cut_line(d,[(45,93),(38,127)],1)
    elif i==7: cut_polygon(d,[(48,91),(58,103),(65,97),(72,103),(82,91),(77,111),(53,111)]); cut_line(d,[(43,100),(46,126)],1); cut_line(d,[(87,100),(84,126)],1)
    elif i==8: cut_line(d,[(48,94),(65,104),(82,94)],2); [ellipse(d,(x,101,x+5,106),CLEAR) for x in (51,58,65,72,79)]
    elif i==9: cut_polygon(d,[(45,92),(55,108),(65,99),(75,108),(85,92),(80,116),(50,116)]); cut_line(d,[(65,100),(65,128)],1)
    elif i==10: cut_polygon(d,[(44,92),(55,100),(75,100),(86,92),(82,109),(78,128),(52,128),(48,109)]); [cut_line(d,[(x,102),(x,122)],1) for x in (57,63,69,75)]
    elif i==11: cut_line(d,[(45,95),(65,112),(85,95)],2); cut_line(d,[(52,101),(78,101)],1); cut_line(d,[(58,106),(72,106)],1)
    elif i==12: cut_polygon(d,[(43,92),(51,103),(55,96),(62,103),(69,96),(76,103),(84,92),(80,111),(49,111)]); cut_line(d,[(43,112),(36,128)],2); cut_line(d,[(86,112),(94,128)],2)
    elif i==13: cut_polygon(d,[(48,92),(55,104),(65,98),(75,104),(82,92),(78,111),(52,111)]); rect(d,(33,104,43,111),CLEAR); rect(d,(87,104,97,111),CLEAR)
    elif i==14: cut_polygon(d,[(42,92),(51,104),(56,97),(62,104),(68,97),(75,104),(84,92),(81,113),(48,113)]); ellipse(d,(61,105,69,113),CLEAR)
    elif i==15: cut_polygon(d,[(49,91),(57,101),(65,97),(73,101),(81,91),(78,108),(52,108)]); cut_line(d,[(34,103),(47,103)],2); cut_line(d,[(83,103),(96,103)],2); rect(d,(58,113,72,121),CLEAR)
    elif i==16: cut_polygon(d,[(47,92),(56,104),(65,98),(74,104),(83,92),(80,113),(50,113)]); cut_line(d,[(40,100),(45,125)],1); cut_line(d,[(90,100),(85,125)],1)
    elif i==17: cut_polygon(d,[(43,92),(54,106),(65,98),(76,106),(87,92),(81,116),(49,116)]); line(d,[(52,94),(65,107),(78,94)],CLEAR,2)
    elif i==18: cut_line(d,[(47,93),(55,128)],2); cut_line(d,[(83,93),(75,128)],2); rect(d,(34,108,48,117),CLEAR); rect(d,(82,108,96,117),CLEAR)
    elif i==19: cut_polygon(d,[(47,92),(55,105),(65,98),(75,105),(83,92),(79,113),(51,113)]); cut_line(d,[(43,101),(51,128)],1); cut_line(d,[(87,101),(79,128)],1); ellipse(d,(61,114,69,122),CLEAR)
    elif i==20: cut_polygon(d,[(48,92),(56,104),(65,98),(74,104),(82,92),(78,111),(52,111)]); rect(d,(37,105,49,115),CLEAR); rect(d,(81,105,93,115),CLEAR); cut_line(d,[(65,99),(65,128)],1)
    elif i==21:
        for x in range(31,100,10):cut_line(d,[(x,99),(x+18,128)],1)
        for x in range(40,100,10):cut_line(d,[(x,99),(x-18,128)],1)
    elif i==22: cut_polygon(d,[(45,92),(53,103),(65,97),(77,103),(85,92),(81,112),(49,112)]); [polygon(d,[(x,99),(x+3,94),(x+6,99)],CLEAR) for x in (34,46,79,91)]; rect(d,(58,114,72,121),CLEAR)
    elif i==23: cut_polygon(d,[(49,92),(57,104),(65,98),(73,104),(81,92),(77,110),(53,110)]); cut_line(d,[(46,115),(84,115)],1); [ellipse(d,(x,119,x+3,122),CLEAR) for x in (51,59,67,75)]
    elif i==24: cut_polygon(d,[(44,91),(55,107),(65,98),(75,107),(86,91),(80,116),(50,116)]); cut_line(d,[(55,101),(45,128)],1); cut_line(d,[(75,101),(85,128)],1)
    elif i==25: cut_polygon(d,[(49,92),(57,103),(65,98),(73,103),(81,92),(78,109),(52,109)]); cut_line(d,[(36,104),(94,104)],2); rect(d,(57,113,73,122),CLEAR)
    elif i==26: cut_polygon(d,[(48,92),(57,103),(65,98),(73,103),(82,92),(79,112),(51,112)]); cut_line(d,[(65,100),(65,128)],1); [ellipse(d,(x,108,x+3,111),CLEAR) for x in (55,73)]
    elif i==27: cut_polygon(d,[(50,92),(57,101),(65,98),(73,101),(80,92),(77,107),(53,107)]); rect(d,(43,103,87,125),CLEAR); line(d,[(46,106),(52,126)],INK,2); line(d,[(84,106),(78,126)],INK,2); rect(d,(58,110,72,121),INK); cut_line(d,[(65,110),(65,121)],1)
    elif i==28: cut_polygon(d,[(40,92),(49,104),(55,97),(61,105),(67,97),(74,105),(81,97),(89,92),(85,115),(45,115)]); cut_line(d,[(38,116),(32,128)],2); cut_line(d,[(92,116),(98,128)],2)
    else: cut_polygon(d,[(45,92),(55,103),(65,98),(75,103),(85,92),(81,113),(49,113)]); cut_line(d,[(55,115),(55,128)],1); cut_line(d,[(75,115),(75,128)],1); rect(d,(61,106,69,113),CLEAR)
    return im


def draw_accessory(index: int) -> Image.Image:
    im=canvas();d=draw(im);i=index
    if i==0: ellipse(d,(28,57,34,64),INK); ellipse(d,(30,59,32,62),YELLOW)
    elif i==1: line(d,[(50,48),(53,49)],INK,2)
    elif i==2: line(d,[(82,70),(87,74)],INK,1); line(d,[(84,69),(88,72)],INK,1)
    elif i==3: ellipse(d,(64,67,70,72),INK); ellipse(d,(66,68,69,70),CLEAR)
    elif i==4: line(d,[(47,68),(45,74),(47,78)],YELLOW,2); line(d,[(47,68),(45,74),(47,78)],INK,1)
    elif i==5: rect(d,(82,66,89,72),INK); cut_line(d,[(83,71),(88,67)],1)
    elif i==6: rect(d,(38,77,43,82),INK); rect(d,(87,77,92,82),INK); cut_line(d,[(43,80),(48,82)],1); cut_line(d,[(82,82),(87,80)],1)
    elif i==7: line(d,[(86,47),(91,50),(88,53),(93,56)],INK,1); rect(d,(88,48,90,50),YELLOW)
    elif i==8: ellipse(d,(43,50,61,69),INK); ellipse(d,(46,53,58,66),CLEAR); line(d,[(61,58),(66,55)],INK,2)
    elif i==9: polygon(d,[(43,54),(61,53),(60,61),(45,61)],INK); polygon(d,[(68,53),(86,54),(84,61),(69,61)],INK); line(d,[(61,56),(68,56)],INK,2); line(d,[(47,56),(57,55)],YELLOW,1); line(d,[(72,55),(81,56)],YELLOW,1)
    elif i==10: rect(d,(29,55,35,65),INK); rect(d,(31,58,33,62),YELLOW)
    elif i==11: line(d,[(83,67),(88,68)],INK,2); line(d,[(82,71),(87,72)],INK,2)
    elif i==12: ellipse(d,(76,31,81,36),YELLOW); line(d,[(78,34),(82,38)],INK,1)
    elif i==13: line(d,[(95,57),(101,61),(99,68),(91,71)],INK,2); ellipse(d,(89,69,93,73),YELLOW)
    elif i==14: ellipse(d,(62,66,67,70),INK); ellipse(d,(64,67,66,69),YELLOW)
    elif i==15: ellipse(d,(27,53,33,60),INK); ellipse(d,(28,63,34,70),INK); ellipse(d,(29,55,31,58),YELLOW); ellipse(d,(30,65,32,68),YELLOW)
    elif i==16: polygon(d,[(81,51),(83,55),(87,55),(84,58),(85,62),(81,59),(78,61),(79,57),(76,54),(80,54)],YELLOW); line(d,[(81,51),(83,55),(87,55),(84,58),(85,62),(81,59),(78,61),(79,57),(76,54),(80,54),(81,51)],INK,1)
    elif i==17: rect(d,(44,55,60,67),INK); rect(d,(47,57,57,64),YELLOW); cut_line(d,[(48,63),(56,58)],1)
    elif i==18: [ellipse(d,(x,47,x+3,50),YELLOW) for x in (49,54,76,81)]; [ellipse(d,(x,47,x+3,50),INK,outline=YELLOW) for x in (49,54,76,81)]
    else: line(d,[(34,68),(39,73),(44,76)],INK,2); [ellipse(d,(x,70,x+3,73),YELLOW) for x in (36,40)]
    return im


def upscale(image: Image.Image) -> Image.Image:
    return image.resize((SIZE, SIZE), Image.Resampling.NEAREST)


def trait_specs():
    categories = [
        ("Base", "BA", BASES, draw_base),
        ("Headwear", "HW", HEADWEAR, draw_headwear),
        ("Eyes", "EY", EYES, draw_eyes),
        ("Mouth", "MO", MOUTHS, draw_mouth),
        ("Outfit", "OF", OUTFITS, draw_outfit),
        ("Accessory", "AC", ACCESSORIES, draw_accessory),
    ]
    for category, prefix, names, renderer in categories:
        for index, name in enumerate(names):
            yield category, f"{prefix}{index + 1:02d}", name, renderer(index)


def compatible(headwear: int, eyes: int, accessory: int) -> bool:
    helmet_headwear = {6, 13, 16, 18, 20, 25}
    integrated_eyewear = {4, 13, 18, 23, 25, 27}
    visor_eyes = {12, 13, 18, 20, 23}
    face_accessories = {8, 9, 17}
    if headwear in helmet_headwear and accessory in face_accessories:
        return False
    if headwear in integrated_eyewear and eyes in visor_eyes:
        return False
    if headwear in integrated_eyewear and accessory in face_accessories:
        return False
    if eyes in visor_eyes and accessory in face_accessories:
        return False
    return True


DNA_RADICES = (len(BASES), len(HEADWEAR), len(EYES), len(MOUTHS), len(OUTFITS), len(ACCESSORIES))
DNA_SPACE = len(BASES) * len(HEADWEAR) * len(EYES) * len(MOUTHS) * len(OUTFITS) * len(ACCESSORIES)


def decode_dna(value: int) -> tuple[int, int, int, int, int, int]:
    parts = []
    for radix in DNA_RADICES:
        parts.append(value % radix)
        value //= radix
    return tuple(parts)


def dna_stream():
    """Yield deterministic, well-distributed, non-repeating compatible DNA."""
    rng = Random(0xA11CE6666)
    seen = set()
    weights = [
        [RARITY_WEIGHTS[rarity_tier(index, len(names))] for index in range(len(names))]
        for names in NAME_GROUPS
    ]
    while len(seen) < DNA_SPACE:
        dna = tuple(
            rng.choices(range(radix), weights=category_weights, k=1)[0]
            for radix, category_weights in zip(DNA_RADICES, weights)
        )
        if dna in seen or not compatible(dna[1], dna[2], dna[5]):
            continue
        seen.add(dna)
        yield dna


def composite(dna: tuple[int, int, int, int, int, int]) -> Image.Image:
    base, headwear, eyes, mouth, outfit, accessory = dna
    result = canvas()
    for layer in (
        draw_outfit(outfit), draw_base(base), draw_headwear(headwear),
        draw_eyes(eyes), draw_mouth(mouth), draw_accessory(accessory),
    ):
        result.alpha_composite(layer)
    return upscale(result)


def verify_render_hash_capacity(count: int) -> int:
    """Prove compatible DNA remains pixel-unique after real layer compositing."""
    layers = [
        [draw_base(index) for index in range(len(BASES))],
        [draw_headwear(index) for index in range(len(HEADWEAR))],
        [draw_eyes(index) for index in range(len(EYES))],
        [draw_mouth(index) for index in range(len(MOUTHS))],
        [draw_outfit(index) for index in range(len(OUTFITS))],
        [draw_accessory(index) for index in range(len(ACCESSORIES))],
    ]
    hashes = set()
    for dna in islice(dna_stream(), count):
        image = canvas()
        for category, trait in (
            (4, dna[4]), (0, dna[0]), (1, dna[1]),
            (2, dna[2]), (3, dna[3]), (5, dna[5]),
        ):
            image.alpha_composite(layers[category][trait])
        digest = sha256(image.tobytes()).digest()
        if digest in hashes:
            raise ValueError(f"Rendered pixel collision within first {count} compatible DNA records")
        hashes.add(digest)
    if len(hashes) != count:
        raise ValueError(f"Expected {count} unique render hashes, found {len(hashes)}")
    return len(hashes)


def validate(image: Image.Image, label: str, bottom_required: bool = False) -> None:
    if image.size != (SIZE, SIZE):
        raise ValueError(f"{label}: invalid size {image.size}")
    alpha = image.getchannel("A")
    if set(alpha.getdata()) - {0, 255}:
        raise ValueError(f"{label}: feathered alpha")
    colors = {pixel[:3] for pixel in image.getdata() if pixel[3]}
    if colors - {INK[:3], YELLOW[:3]}:
        raise ValueError(f"{label}: off-palette pixels {colors}")
    bbox = alpha.getbbox()
    if not bbox:
        raise ValueError(f"{label}: empty")
    if bottom_required and bbox[3] != SIZE:
        raise ValueError(f"{label}: body does not meet canvas bottom {bbox}")


def write_zip(path: Path, files: list[Path], root: Path) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, file.relative_to(root))


def build(output: Path, render_count: int = 100) -> None:
    traits_dir = output / "traits"
    renders_dir = output / "renders"
    traits_dir.mkdir(parents=True, exist_ok=True)
    renders_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir = output / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    trait_records = []
    category_files: dict[str, list[Path]] = {}
    category_hashes: dict[str, set[str]] = {}
    for category, code, name, low_image in trait_specs():
        folder = category.lower()
        path = traits_dir / folder / f"{code}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        image = upscale(low_image)
        validate(image, code, bottom_required=category == "Outfit")
        digest = sha256(image.tobytes()).hexdigest()
        if digest in category_hashes.setdefault(category, set()):
            raise ValueError(f"{code}: duplicate pixels within {category}")
        category_hashes[category].add(digest)
        yellow_pixels = sum(pixel == YELLOW for pixel in image.getdata())
        if category == "Eyes" and yellow_pixels < 1_000:
            raise ValueError(f"{code}: eye interior is not fully yellow")
        if code == "HW02" and yellow_pixels < 50_000:
            raise ValueError("HW02: Living Flame is not fully yellow")
        image.save(path, optimize=True)
        category_files.setdefault(folder, []).append(path)
        trait_records.append({
            "category": category,
            "code": code,
            "name": name,
            "rarity": rarity_tier(int(code[2:]) - 1, len(CATEGORY_NAMES[category])),
            "file": f"traits/{folder}/{code}.png",
        })

    characters = []
    hashes = set()
    dnas = set()
    preview_dnas = list(islice(dna_stream(), render_count))
    capacity_probe = list(islice(dna_stream(), 6_666))
    if len(set(capacity_probe)) != 6_666:
        raise ValueError("DNA generator cannot provide 6,666 unique compatible combinations")
    verified_render_capacity = verify_render_hash_capacity(6_666)
    for identifier, dna in enumerate(preview_dnas, 1):
        if dna in dnas:
            raise ValueError(f"Duplicate DNA at {identifier}: {dna}")
        dnas.add(dna)
        image = composite(dna)
        validate(image, f"#{identifier:03d}", bottom_required=True)
        digest = image.tobytes()
        if digest in hashes:
            raise ValueError(f"Duplicate rendered pixels at {identifier}")
        hashes.add(digest)
        image.save(renders_dir / f"{identifier:03d}.png", optimize=True)
        indices = dict(zip(("Base", "Headwear", "Eyes", "Mouth", "Outfit", "Accessory"), dna))
        names = {"Base": BASES, "Headwear": HEADWEAR, "Eyes": EYES, "Mouth": MOUTHS, "Outfit": OUTFITS, "Accessory": ACCESSORIES}
        prefixes = {"Base": "BA", "Headwear": "HW", "Eyes": "EY", "Mouth": "MO", "Outfit": "OF", "Accessory": "AC"}
        characters.append({
            "id": identifier,
            "image": f"renders/{identifier:03d}.png",
            "dna": [
                {"category": category, "code": f"{prefixes[category]}{value + 1:02d}", "name": names[category][value]}
                for category, value in indices.items()
            ],
        })
        metadata = {
            "name": f"Night Shift #{identifier:04d}",
            "description": "Canonical layered one-bit Night Shift production test.",
            "image": f"../renders/{identifier:03d}.png",
            "attributes": [
                {"trait_type": category, "value": names[category][value]}
                for category, value in indices.items()
            ],
        }
        (metadata_dir / f"{identifier:03d}.json").write_text(
            json.dumps(metadata, indent=2) + "\n",
            encoding="utf-8",
        )

    manifest = {
        "collection": "Night Shift Society",
        "edition": "Canonical Layered One-Bit",
        "canvas": "1024x1024 RGBA",
        "workingGrid": "256x256 rasterized from a canonical 128-unit design grid, scaled 4x nearest-neighbor",
        "palette": {"ink": "#020102", "traitYellow": "#fdf423"},
        "traitCount": len(trait_records),
        "categoryCounts": {folder.title(): len(files) for folder, files in category_files.items()},
        "renderCount": len(characters),
        "uniqueDnaCount": len(dnas),
        "uniqueRenderCount": len(hashes),
        "verifiedUniqueDnaCapacity": 6_666,
        "verifiedUniqueRenderCapacity": verified_render_capacity,
        "totalRawDnaSpace": DNA_SPACE,
        "rarityPolicy": {
            "tiers": RARITY_WEIGHTS,
            "method": "Deterministic weighted draw without duplicate DNA",
        },
        "compatibilityRules": [
            "Integrated helmet and visor headwear cannot combine with visor-class eyes",
            "Integrated eyewear cannot combine with face-covering eyewear accessories",
            "Helmet headwear cannot combine with face-covering eyewear accessories",
            "No background-object category exists",
        ],
        "traits": trait_records,
        "characters": characters,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    all_files = [path for files in category_files.values() for path in files]
    write_zip(output / "night-shift-128-production-traits.zip", all_files, traits_dir)
    for folder, files in category_files.items():
        write_zip(output / f"night-shift-{folder}-traits.zip", files, traits_dir)
    write_zip(output / f"night-shift-{render_count}-test-renders.zip", sorted(renders_dir.glob("*.png")), renders_dir)
    write_zip(output / f"night-shift-{render_count}-test-metadata.zip", sorted(metadata_dir.glob("*.json")), metadata_dir)


def publish_to_site(output: Path) -> None:
    public_traits = PROJECT_ROOT / "public" / "traits"
    public_studio = PROJECT_ROOT / "public" / "characters-one-bit-studio"
    for target in (public_traits, public_studio):
        if target.exists():
            rmtree(target)

    copytree(output / "traits", public_traits)
    copy2(output / "manifest.json", public_traits / "manifest.json")
    for archive in output.glob("night-shift-*-traits.zip"):
        copy2(archive, public_traits / archive.name)

    public_studio.mkdir(parents=True)
    for render in sorted((output / "renders").glob("*.png")):
        copy2(render, public_studio / render.name)
    copytree(output / "metadata", public_studio / "metadata")
    copy2(output / "manifest.json", public_studio / "manifest.json")
    for archive in output.glob("night-shift-*-test-*.zip"):
        copy2(archive, public_studio / archive.name)

    docs_traits = PROJECT_ROOT / "docs" / "traits"
    docs_studio = PROJECT_ROOT / "docs" / "studio"
    for source, target in ((public_traits, docs_traits), (public_studio, docs_studio)):
        if target.exists():
            rmtree(target)
        copytree(source, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("tmp/production-layered"))
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--publish-site", action="store_true")
    args = parser.parse_args()
    build(args.output, args.count)
    if args.publish_site:
        publish_to_site(args.output)
    print(f"Built 128 genuine layers and {args.count} unique outputs in {args.output}")


if __name__ == "__main__":
    main()
