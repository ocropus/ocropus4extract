#!/usr/bin/env python
# coding: utf-8

# %%

import numpy as np
import scipy.ndimage as ndi
import tempfile
from itertools import islice
import xml.etree.ElementTree as ET
from lxml import etree
import io
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import imageio.v2 as imageio
import subprocess
import os
import webdataset as wds
import gzip
import zipfile
from bbox import Bbox


def splitat(lst, predicate):
    sublists = []
    start = 0
    for i, x in enumerate(lst):
        if predicate(x):
            sublists.append(lst[start:i])
            start = i
    sublists.append(lst[start:])
    return sublists


def gettext(l):
    return "".join(x.text for x in l)

def getbbox(elts):
    l = min(int(x.get("l")) for x in elts)
    t = min(int(x.get("t")) for x in elts)
    b = max(int(x.get("b")) for x in elts)
    r = max(int(x.get("r")) for x in elts)
    return dict(l=l, t=t, b=b, r=r)

def removespace(chars):
    return [c for c in chars if c.text != " "]

def parse_abbyy(file_path, max_pages=9999999):
    parser = etree.XMLParser(recover=True) # Recover from bad characters.
    tree = ET.parse(file_path, parser=parser)
    root = tree.getroot()
    
    if root is None:
        return None

    namespace = root.tag.split('}')[0].strip('{')
    namespace
    prefix = f"{{{namespace}}}"

    result = []
    for page in islice(root.findall(prefix+"page"), 0, 9999):
        if len(result) >= max_pages:
            break
        pw, ph = int(page.get("width")), int(page.get("height"))
        rpage = dict(
            size=dict(w=pw, h=ph),
            lines=[],
            words=[],
        )
        for line in page.findall(".//"+prefix+"line"):
            chars = [cp for cp in line.findall(".//"+prefix+"charParams")]
            if len(chars) == 0:
                continue
            rline = getbbox(chars)
            rline["text"] = gettext(chars)
            rpage["lines"].append(rline)
            words = splitat(chars, lambda x: x.get("wordStart")=="true")
            words = map(removespace, words)
            words = [w for w in words if len(w) > 0]
            rwords = [dict(getbbox(w), text=gettext(w)) for w in words]
            rpage["words"] += rwords
        chars = [dict(t=int(x.get("t")), b=int(x.get("b")), l=int(x.get("l")), r=int(x.get("r")), text=x.text) for x in page.findall(".//"+prefix+"charParams")]
        rpage["chars"] = chars
        result.append(rpage)
    return result

def make_page_mask(page, elts, grow=10, shrink=2, shrink2=(200, 5, 200, 5), grow3=3):
    mask = np.zeros((page["size"]["h"], page["size"]["w"]), dtype=np.uint8)
    for elt in elts:
        bbox = Bbox(from_dict=elt)
        bbox.grow(grow).fill(mask, 1)
        bbox.shrink(shrink).fill(mask, 2)
        bbox.shrink(shrink2).grow(grow3).fill(mask, 3)
    return mask

def djvu_npages(djvu_file):
    output =os.popen(f"djvused -e n '{djvu_file}'").read().strip()
    print(output)
    return int(output)

def djvu_page(djvu_file, pageno, size):
    os.system(f"ddjvu -size={size[0]}x{size[1]} -page={pageno+1} {djvu_file} /tmp/page.pgm")
    image = imageio.imread("/tmp/page.pgm")
    return image

# %%


class Jp2Zip:
    def __init__(self, fname):
        # fname = f"iadownloads/{base}.zip"
        self.zf = zipfile.ZipFile(fname)
        self.jp2s = sorted([x for x in self.zf.namelist() if x.endswith('.jp2')])
        self.pages = {int(x[-8:-4]): x for x in self.jp2s}
    def __len__(self):
        return len(self.pages.keys())
    # implement in operator
    def __contains__(self, i):
        return i in self.pages
    def raw(self, i):
        fname = self.pages[i]
        with self.zf.open(fname) as f:
            return f.read()
    def decode(self, i):
        fname = self.pages[i]
        with self.zf.open(fname) as f:
            image = imageio.imread(f)
        return image
    


def make_page_mask(page, elts, max_height=150, min_width=10):
    mask = np.zeros((page["size"]["h"], page["size"]["w"]), dtype=np.uint8)
    # sort the elts by height reverse
    # this takes care of overlapping boxes in a simple (if imperfect) way
    boxes = [Bbox(from_dict=x) for x in elts]
    boxes = sorted(boxes, key=lambda x: -x.height())
    boxes = [x for x in boxes if x.height() < max_height and x.width() > min_width]
    for bbox in boxes:
        bbox.grow(max(5, int(bbox.height()*0.1))).fill(mask, 1)
    for bbox in boxes:
        bbox.shrink(max(3, int(bbox.height()*0.05))).fill(mask, 2)
    for bbox in boxes:
        height = bbox.height()
        cheight = max(3, int(height*0.2))
        hmargin = max(10, int(height*0.5))
        bbox.shrink((height, hmargin, height, hmargin)).grow(cheight).fill(mask, 3)
    return mask
