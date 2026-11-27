"""Gemini gorselinden zemin rengini (yesil ya da pembe-mor, otomatik) temizle, parcalari ayir.
kullanim: key_extract.py girdi.jpg cikis_klasoru [min_alan] [birlestirme_px]
Her parca NN.png olarak kaydedilir; _index.png onizleme."""
import sys, os
from PIL import Image, ImageDraw
import numpy as np
from scipy import ndimage
src, out = sys.argv[1], sys.argv[2]
min_area = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
merge = int(sys.argv[4]) if len(sys.argv) > 4 else 18
os.makedirs(out, exist_ok=True)
im = np.array(Image.open(src).convert('RGB')).astype(np.float32)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
corner = np.concatenate([im[:20, :20].reshape(-1, 3), im[-20:, -20:].reshape(-1, 3)]).mean(0)
magenta = corner[0] > 150 and corner[2] > 150 and corner[1] < 100
if magenta:
    key = np.minimum(r, b) - g          # pembe-mor baskinligi
    spill_fix = lambda c: c
else:
    key = g - np.maximum(r, b)
alpha = np.clip(1 - (key - 35) / 70, 0, 1)
rgb = im.copy()
if magenta:
    m = (r + b) / 2
    lim = g + (m - g) * 0.0
    hi = np.maximum(r, b) > g + 40
    rgb[..., 0] = np.where((alpha < 0.98) & hi, np.minimum(r, g + 40), r)
    rgb[..., 2] = np.where((alpha < 0.98) & hi, np.minimum(b, g + 40), b)
else:
    mx = np.maximum(r, b)
    rgb[..., 1] = np.where((g > mx) & (alpha < 0.98), mx + (g - mx) * 0.2, g)
mask = alpha > 0.5
grown = ndimage.binary_dilation(mask, iterations=merge)
lab, n = ndimage.label(grown)
parts = []
for i, sl in enumerate(ndimage.find_objects(lab)):
    comp = (lab[sl] == i + 1) & mask[sl]
    if comp.sum() < min_area:
        continue
    parts.append((sl, i + 1))
parts.sort(key=lambda p: (p[0][0].start // 150, p[0][1].start))
thumbs = []
for k, (sl, cid) in enumerate(parts):
    region = (lab[sl] == cid)
    a = np.where(region, alpha[sl], 0)
    rgba = np.dstack([rgb[sl], a * 255]).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(rgba, 'RGBA')
    bb = img.getbbox()
    img = img.crop(bb)
    img.save(f"{out}/{k:02d}.png")
    thumbs.append(img)
# onizleme
W = 220
sheet = Image.new('RGBA', (W * min(6, max(1, len(thumbs))), (W + 16) * ((len(thumbs) + 5) // 6)), (50, 50, 60, 255))
d = ImageDraw.Draw(sheet)
for k, t in enumerate(thumbs):
    tt = t.copy(); tt.thumbnail((W - 10, W - 10))
    x, y = (k % 6) * W, (k // 6) * (W + 16)
    sheet.alpha_composite(tt, (x + 5, y + 16)); d.text((x + 4, y + 2), f"{k:02d} {t.size}", fill='white')
sheet.save(f"{out}/_index.png")
print(src, 'magenta' if magenta else 'green', len(thumbs))
