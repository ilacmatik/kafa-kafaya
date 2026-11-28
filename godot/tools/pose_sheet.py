"""Gemini poz resminden (yesil zemin, yan yana pozlar) oyun animasyonu.
kullanim: pose_sheet.py resim.jpg kahraman hareket [satir_sayisi]
- pozlar soldan saga (cok satirliysa yukaridan asagi) siralanir
- olcek: yuz alani kahramanin idle videosundaki yuzle esitlenir (kafa boyu tutarli)
- her poz icin yuz merkezi (havadaki pozlar kafadan hizalanir) ve ayak tabani kaydedilir"""
import sys, os, json
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, os.path.dirname(__file__))
from face import face

src, rig, names = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
nrows = int(sys.argv[4]) if len(sys.argv) > 4 else 1
ymin = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0   # ustteki soluk "hayalet" satiri atmak icin

im = np.array(Image.open(src).convert("RGB")).astype(np.float32)
im = im[int(im.shape[0] * ymin):]
r, g, b = im[..., 0], im[..., 1], im[..., 2]
k = g - np.maximum(r, b)
a = np.clip(1 - (k - 30) / 60, 0, 1)
mx = np.maximum(r, b)
im[..., 1] = np.where(g > mx, mx + (g - mx) * 0.15, g)
# zemin cizgisi (koyu, ince, yatay) varsa sil: ayaklarla birlesip pozu bozmasin
dark = (im.sum(2) < 200) & (a > 0.5)
def longest_run(row):
    best = cur = 0
    for v in row:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best
cand = np.nonzero(dark.sum(1) > im.shape[1] * 0.3)[0]
for y in [y for y in cand if longest_run(dark[y]) > im.shape[1] * 0.3]:
    for yy in range(max(0, y - 3), min(im.shape[0], y + 4)):
        a[yy] = np.where(dark[yy] | (im[yy].sum(1) < 260), 0, a[yy])
rgba = np.dstack([im, a * 255]).clip(0, 255).astype(np.uint8)
m = a > 0.5
lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=10))
sizes = ndimage.sum(m, lab, range(1, n + 1))
big = [i + 1 for i in np.argsort(sizes)[::-1] if sizes[i] > sizes.max() * 0.25]
boxes = []
for L in big:
    ys, xs = np.nonzero(lab == L)
    boxes.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1, L))
# satir/sutun sirasi
H = im.shape[0]
boxes.sort(key=lambda bx: (int(((bx[1] + bx[3]) / 2) / (H / nrows)), bx[0]))
print("poz sayisi", len(boxes))

idle = json.load(open(f"assets/anim/{rig}/idle/anim.json"))
iat = np.array(Image.open(f"assets/anim/{rig}/idle/atlas.png"))
f0 = idle["frames"][0]
fi = face(iat[f0[1]:f0[1] + f0[3], f0[0]:f0[0] + f0[2]])
poses = []
for (x0, y0, x1, y1, L) in boxes:
    crop = rgba[y0:y1, x0:x1].copy()
    crop[..., 3] = np.where(lab[y0:y1, x0:x1] == L, crop[..., 3], 0)
    poses.append(crop)
fa = [face(p) for p in poses]
areas = sorted(f[2] for f in fa if f)
sc = float(np.sqrt(fi[2] / areas[len(areas) // 2]))   # ortanca yuz alani -> idle yuzu
print("idle yuz", fi, "olcek", round(sc, 3))
groups = [list(range(len(poses)))]
if len(names) > 1:
    per = len(poses) // len(names)
    groups = [list(range(i * per, (i + 1) * per)) for i in range(len(names))]
fa_all, poses_all = fa, poses
pad = 8
for name, grp in zip(names, groups):
  out = f"assets/anim/{rig}/{name}"
  os.makedirs(out, exist_ok=True)
  poses = [poses_all[i] for i in grp]
  fa = [fa_all[i] for i in grp]
  ws = [int(p.shape[1] * sc) + 2 * pad for p in poses]
  hs = [int(p.shape[0] * sc) + 2 * pad for p in poses]
  W, Hh = max(ws), max(hs)
  cols = max(1, 4096 // W)
  atlas = Image.new("RGBA", (cols * W, ((len(poses) + cols - 1) // cols) * Hh))
  frames, heads, feet = [], [], []
  for i, p in enumerate(poses):
      pi = Image.fromarray(p).resize((ws[i] - 2 * pad, hs[i] - 2 * pad), Image.LANCZOS)
      px, py = (i % cols) * W, (i // cols) * Hh
      ox, oy = (W - pi.width) // 2, Hh - pad - pi.height   # tabana oturt
      atlas.paste(pi, (px + ox, py + oy))
      f = fa[i]
      heads.append([round(ox + f[0] * sc, 1), round(oy + f[1] * sc, 1)])
      al = np.array(pi)[..., 3] > 128
      rows = np.nonzero(al.any(1))[0]
      bot = rows.max()
      xs = np.nonzero(al[max(0, bot - 6):bot + 1].any(0))[0]
      feet.append([round(ox + float(xs.mean()), 1), round(oy + float(bot), 1)])
      frames.append([px, py, W, Hh])
  atlas.save(f"{out}/atlas.png")
  json.dump({"fps": 12.0, "loop": False, "poses": True, "frames": frames, "heads": heads, "feet": feet,
             "foot": feet[0], "size": [W, Hh], "scale": idle["scale"], "top": 0.0}, open(f"{out}/anim.json", "w"))
  prev = Image.new("RGBA", atlas.size, (60, 120, 70, 255)); prev.alpha_composite(atlas); prev.save(f"{out}/_preview.png")
# idle'a da gercek yuz merkezini yaz (fizik kafasi hizasi)
idle["face"] = [round(fi[0], 1), round(fi[1], 1)]
json.dump(idle, open(f"assets/anim/{rig}/idle/anim.json", "w"))
print(out, "kare", len(frames), "atlas", atlas.size)
