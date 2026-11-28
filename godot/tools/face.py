"""Yuz bulucu: ten rengi maskesinin en buyuk parcasi -> (merkez x, y, alan). Kare/poz hizalamada kullanilir."""
import numpy as np
from scipy import ndimage


def face(rgba):
    a = rgba
    r, g, b = [a[..., i].astype(int) for i in range(3)]
    s = (r > 170) & (g > 110) & (g < 220) & (b > 70) & (b < 190) & (r - g > 15) & (r - g < 80) & (g - b > 12) & (a[..., 3] > 200)
    s = ndimage.binary_opening(s, iterations=2)
    lab, n = ndimage.label(s)
    if n == 0:
        return None
    sizes = ndimage.sum(s, lab, range(1, n + 1))
    k = int(np.argmax(sizes)) + 1
    ys, xs = np.nonzero(lab == k)
    return float(xs.mean()), float(ys.mean()), float(sizes[k - 1])
