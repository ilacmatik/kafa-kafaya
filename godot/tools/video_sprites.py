"""Yesil zeminli animasyon videosundan oyun karelerine.
kullanim: video_sprites.py video.mp4 cikis_klasoru [loop|once] [bas_sn] [bit_sn]
- yesil anahtarlama + yesil tasma temizligi, govdeye bagli olmayan lekeler (nefes buhari vb.) atilir
- kamera sabit kabul edilir: kareler TEK ortak kutuyla kesilir (titreme olmaz), ayak tabani hizasi korunur
- loop: en benzer iki kare arasi secilir (dikissiz dongu)
cikis: atlas.png (yatay seritler) + anim.json {fps, frames:[[x,y,w,h]], foot:[x,y] (kare icinde), size:[w,h]}"""
import sys, os, json, subprocess, tempfile, glob
import numpy as np
from PIL import Image
from scipy import ndimage

src, out = sys.argv[1], sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "loop"
t0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
t1 = float(sys.argv[5]) if len(sys.argv) > 5 else 1e9
os.makedirs(out, exist_ok=True)

# 1) ham kareler (videonun kendi hizi, genelde 24)
fps = 24.0
tmp = tempfile.mkdtemp()
subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-vsync", "0", f"{tmp}/%04d.png"], check=True)
files = sorted(glob.glob(f"{tmp}/*.png"))
files = [f for k, f in enumerate(files) if t0 <= k / fps < t1]
# 2) AI videolari genelde "ikiserli": her poz 2 kare tekrar eder (gercekte 12 kare/sn) -> tekrarlari at
raw = [np.array(Image.open(f).convert("RGB"))[::4, ::4].astype(np.int16) for f in files]
keep = [0]
for k in range(1, len(files)):
    if np.abs(raw[k] - raw[keep[-1]]).mean() > 1.2:
        keep.append(k)
ratio = len(keep) / len(files)
print("tekrarsiz kare: %d / %d" % (len(keep), len(files)))
if ratio < 0.8:
    files = [files[k] for k in keep]
    fps = float(round(fps * ratio))
# 3) ara kare: hareket telafili, hedef INTERP_FPS (hizli hareketlerde dusuk tutulur: bulasma olmasin)
tgt = float(os.environ.get("INTERP_FPS", "24"))
if tgt > fps:
    d2 = tempfile.mkdtemp()
    for n, f in enumerate(files):
        os.symlink(f, f"{d2}/{n:04d}.png")
    d3 = tempfile.mkdtemp()
    vf = f"minterpolate=fps={tgt:g}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-framerate", f"{fps:g}", "-i", f"{d2}/%04d.png", "-vf", vf, f"{d3}/%04d.png"], check=True)
    files = sorted(glob.glob(f"{d3}/*.png"))
    fps = tgt
print("kare hizi", fps)


def key(path):
    im = np.array(Image.open(path).convert("RGB")).astype(np.float32)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    k = g - np.maximum(r, b)
    a = np.clip(1 - (k - 28) / 60, 0, 1)
    # yesil tasma: yari saydam kenar ve yesile kacan pikseller
    mx = np.maximum(r, b)
    im[..., 1] = np.where(g > mx, mx + (g - mx) * 0.15, g)
    m = a > 0.5
    lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=6))
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        main = np.argmax(sizes) + 1
        a = np.where(lab == main, a, 0)
    a = ndimage.grey_erosion((a * 255).astype(np.uint8), size=(2, 2)).astype(np.float32) / 255 * 0.35 + a * 0.65
    return np.dstack([im, a * 255]).clip(0, 255).astype(np.uint8)


frames = [key(f) for f in files]

alphas = [f[..., 3] > 128 for f in frames]

# dongu secimi
sel = list(range(len(frames)))
if mode == "loop" and len(frames) > 30:
    sm = [np.array(Image.fromarray(f).resize((f.shape[1] // 8, f.shape[0] // 8))).astype(np.float32) for f in frames]
    best = (1e18, 0, len(frames))
    minlen = int(fps * float(os.environ.get("MINLEN", "1.2")))
    maxlen = int(fps * float(os.environ.get("MAXLEN", "3.0")))   # atlas 4096'yi asmasin
    for i in range(len(frames)):
        for j in range(i + minlen, min(len(frames), i + maxlen + 1)):
            d = np.abs(sm[i] - sm[j]).mean()
            if d < best[0]:
                best = (d, i, j)
    print("dongu: kare %d -> %d (%.2f sn) fark %.2f" % (best[1], best[2], (best[2] - best[1]) / fps, best[0]))
    sel = list(range(best[1], best[2]))

union = np.zeros_like(alphas[0])
for k in sel:
    union |= alphas[k]
ys, xs = np.nonzero(union)
pad = 6
x0, x1 = int(max(0, xs.min() - pad)), int(min(union.shape[1], xs.max() + pad))
y0, y1 = int(max(0, ys.min() - pad)), int(min(union.shape[0], ys.max() + pad))
w, h = x1 - x0, y1 - y0
# ayak: ilk karede tabanin ortasi (en alttaki %4 satir)
a0 = alphas[sel[0]][y0:y1, x0:x1]
rows = np.nonzero(a0.any(1))[0]
bot = rows.max()
fx = np.nonzero(a0[max(0, bot - int(h * 0.04)):bot + 1].any(0))[0].mean()
# boy: karakter ~CHAR_H piksel olsun (1080p'de oyunda ~230 px gorunur; 4K icin pay)
CHAR_H = 360.0
rowsu = np.nonzero(union.any(1))[0]
sc = min(1.0, CHAR_H / float(rowsu.max() - rowsu.min()))
W0, H0 = w, h
w, h = max(1, int(round(w * sc))), max(1, int(round(h * sc)))
fx, bot = fx * sc, bot * sc
cols = max(1, int(4096 // w))
rows_n = (len(sel) + cols - 1) // cols
atlas = Image.new("RGBA", (cols * w, rows_n * h))
rects = []
for n, k in enumerate(sel):
    im = Image.fromarray(frames[k][y0:y1, x0:x1]).resize((w, h), Image.LANCZOS)
    px, py = (n % cols) * w, (n // cols) * h
    atlas.paste(im, (px, py))
    rects.append([px, py, w, h])
atlas.save(f"{out}/atlas.png")
json.dump({"fps": fps, "loop": mode == "loop", "frames": rects, "foot": [round(float(fx), 1), round(float(bot), 1)], "size": [w, h],
           "top": round(float((rowsu.min() - y0) * sc), 1), "scale": round(sc, 4)},
          open(f"{out}/anim.json", "w"))
# onizleme seridi
prev = Image.new("RGBA", (w * min(8, len(sel)), h), (60, 120, 70, 255))
for n, k in enumerate(sel[:: max(1, len(sel) // 8)][:8]):
    prev.alpha_composite(Image.fromarray(frames[k][y0:y1, x0:x1]).resize((w, h), Image.LANCZOS), (n * w, 0))
prev.save(f"{out}/_preview.png")
print(out, "kare", len(sel), "boyut", w, h, "atlas", atlas.size)
