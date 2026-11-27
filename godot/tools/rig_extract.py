"""Gemini parca sayfasindan (yesil zemin) parcalari ayikla: anahtar renk temizleme + bilesen ayirma."""
import sys, json
from PIL import Image
import numpy as np
from scipy import ndimage
src, out_dir, names_json = sys.argv[1], sys.argv[2], sys.argv[3]
names = json.loads(names_json)          # [[ad, x, y], ...] parcanin icinden bir nokta
im = np.array(Image.open(src).convert('RGB')).astype(np.float32)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
key = g - np.maximum(r, b)
alpha = np.clip(1 - (key - 30) / 70, 0, 1)
mask = alpha > 0.5
lab, n = ndimage.label(mask)
sizes = ndimage.sum(mask, lab, range(1, n + 1))
# yesil tasmasini temizle
rgb = im.copy()
mx = np.maximum(r, b)
rgb[..., 1] = np.where(g > mx, mx + (g - mx) * 0.15 * (alpha > 0.95), g)
info = {}
for name, px, py in names:
    cid = lab[py, px]
    if cid == 0:
        print("BOS NOKTA", name); continue
    comp = lab == cid
    # kucuk komsu parcalari (alev kivilcimlari) ekle
    grown = ndimage.binary_dilation(comp, iterations=25)
    for j in range(1, n + 1):
        if sizes[j - 1] < 800 and (grown & (lab == j)).any():
            comp |= lab == j
    soft = ndimage.binary_dilation(comp, iterations=3)
    a = np.where(soft, alpha, 0)
    ys, xs = np.where(a > 0.02)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    pad = 4
    y0, x0 = max(0, y0 - pad), max(0, x0 - pad)
    y1, x1 = min(im.shape[0], y1 + pad), min(im.shape[1], x1 + pad)
    rgba = np.dstack([rgb[y0:y1, x0:x1], a[y0:y1, x0:x1] * 255]).clip(0, 255).astype(np.uint8)
    Image.fromarray(rgba, 'RGBA').save(f"{out_dir}/{name}.png")
    info[name] = [int(x0), int(y0), int(x1 - x0), int(y1 - y0)]
json.dump(info, open(f"{out_dir}/_sheet.json", "w"), indent=1)
print(info)
