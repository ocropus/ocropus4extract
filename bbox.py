import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def draw_rectangle(top, left, bottom, right, color="red", width=1, ax=None):
  rect = Rectangle((left, top), width=right - left, height=bottom - top, color=color, linewidth=width, fill=False)
  ax = ax or plt.gca()
  ax.add_patch(rect)

class Bbox:
    def __init__(self, t=0, l=0, b=0, r=0, from_dict=None):
        if from_dict is not None:
            self.t = from_dict["t"]
            self.l = from_dict["l"]
            self.b = from_dict["b"]
            self.r = from_dict["r"]
        else:
            self.t = t
            self.l = l
            self.b = b
            self.r = r
    def draw_rect(self, color="red", width=1, ax=None):
        draw_rectangle(self.t, self.l, self.b, self.r, color=color, width=width, ax=ax)
    def height(self):
        return self.b - self.t
    def width(self):
        return self.r - self.l
    def scale_(self, scale):
        self.t = int(self.t * scale)
        self.l = int(self.l * scale)
        self.b = int(self.b * scale)
        self.r = int(self.r * scale)
    def __eq__(self, other):
        return self.t == other.t and self.l == other.l and self.b == other.b and self.r == other.r
    def __repr__(self):
        return "Bbox(%d, %d, %d, %d)" % (self.t, self.l, self.b, self.r)
    def __str__(self):
        return self.__repr__()
    def union(self, other):
        return Bbox(
            min(self.t, other.t),
            min(self.l, other.l),
            max(self.b, other.b),
            max(self.r, other.r),
        )
    def grow(self, margin, max_w=9999999, max_h=9999999):
        if not isinstance(margin, tuple):
            margin = (margin, margin, margin, margin)
        return Bbox(
            max(0, self.t - margin[0]),
            max(0, self.l - margin[1]),
            min(max_h, self.b + margin[2]),
            min(max_w, self.r + margin[3]),
        )

    def shrink(self, margin, min_w=1, min_h=1):
        if not isinstance(margin, tuple):
            margin = (margin, margin, margin, margin)
        t = self.t + margin[0]
        l = self.l + margin[1]
        b = self.b - margin[2]
        r = self.r - margin[3]

        if b - t < min_h:
            diff = min_h - (b - t)
            t -= diff // 2
            b += (diff + 1) // 2

        if r - l < min_w:
            diff = min_w - (r - l)
            l -= diff // 2
            r += (diff + 1) // 2

        return Bbox(t, l, b, r)
    
    def fill(self, nda, value):
        nda[self.t:self.b, self.l:self.r] = value

    def extract(self, arr):
        return arr[self.t:self.b, self.l:self.r, ...]
    
    def dict(self, **kw):
        return {
            "t": self.t,
            "l": self.l,
            "b": self.b,
            "r": self.r,
            **kw
        }

