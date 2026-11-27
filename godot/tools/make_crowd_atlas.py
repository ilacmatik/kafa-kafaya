"""Taraftar sprite atlasi (Godot icin). Iki atlas: renkli taban (forma/takim bolgeleri beyaz)
ve boya maskesi (R=forma, G=takim rengi). Shader takima gore boyar."""
import json, sys
from PIL import Image, ImageDraw
OUT = (30, 24, 30, 255)
SKINS = [(255, 216, 172), (236, 186, 142), (198, 142, 100), (142, 96, 64)]
HAIRS = [(60, 40, 25), (25, 22, 25), (235, 200, 90), (150, 70, 30)]
W, H = 22, 34
Q = 4        # atlastaki olcek (22x34 -> 88x136)
SS = 4       # yumusak kenar icin fazladan buyutme
PAD = 4
COLS = 12

def sprite(stripe, skin, hair, pose):
    Z = Q * SS
    base = Image.new("RGBA", (W * Z, H * Z), (0, 0, 0, 0))
    msk = Image.new("RGBA", (W * Z, H * Z), (0, 0, 0, 0))
    db, dm = ImageDraw.Draw(base), ImageDraw.Draw(msk)
    WHITE = (255, 255, 255, 255)
    SH = (255, 0, 0, 255)     # forma
    TM = (0, 255, 0, 255)     # takim
    NO = (0, 0, 0, 255)
    sk = SKINS[skin] + (255,)
    cx = 11
    def P(x, y): return (x * Z, y * Z)
    def line(cb, cm, a, b, w):
        for d, c in ((db, cb), (dm, cm)):
            d.line([P(*a), P(*b)], fill=c, width=int(w * Z))
            for p in (a, b):   # pygame kalin cizgi uclari ~ yuvarlak
                r = w * Z / 2
                d.ellipse([P(*p)[0] - r, P(*p)[1] - r, P(*p)[0] + r, P(*p)[1] + r], fill=c)
    def circ(cb, cm, p, r):
        for d, c in ((db, cb), (dm, cm)):
            d.ellipse([(p[0] - r) * Z, (p[1] - r) * Z, (p[0] + r) * Z, (p[1] + r) * Z], fill=c)
    def rect(cb, cm, r, rad=0):
        for d, c in ((db, cb), (dm, cm)):
            box = [r[0] * Z, r[1] * Z, (r[0] + r[2]) * Z - 1, (r[1] + r[3]) * Z - 1]
            if rad: d.rounded_rectangle(box, radius=rad * Z, fill=c)
            else: d.rectangle(box, fill=c)
    if pose in (1, 2):
        for side in (-1, 1):
            sx, sy = cx + side * 5, 20
            ex, ey = cx + side * 9, (7 if pose == 1 else 6)
            line(OUT, NO, (sx, sy), (ex, ey), 5)
            line(WHITE, SH, (sx, sy), (ex, ey), 3)
            circ(OUT, NO, (ex, ey), 3)
            circ(sk, NO, (ex, ey), 2)
    rect(OUT, NO, (cx - 7, 18, 14, 16), 5)
    rect(WHITE, SH, (cx - 6, 19, 12, 15), 4)
    if stripe:
        line(WHITE, TM, (cx - 6, 24), (cx + 5, 24), 3)
    circ(OUT, NO, (cx, 13), 7)
    if hair < 4: circ(HAIRS[hair] + (255,), NO, (cx, 12), 6)
    else: circ(WHITE, TM, (cx, 12), 6)
    circ(sk, NO, (cx, 14), 5)
    circ(OUT, NO, (cx + 2, 14), 1)
    if hair == 4:
        rect(WHITE, TM, (cx - 6, 7, 12, 4), 2)
    if pose == 2:
        rect(OUT, NO, (0, 2, 22, 7), 2)
        rect(WHITE, TM, (1, 3, 20, 5))
        for xx in range(3, 20, 6):
            rect(WHITE, NO, (xx, 3, 2, 5))
    sz = (W * Q, H * Q)
    b = base.convert("RGBa").resize(sz, Image.LANCZOS).convert("RGBA")
    m = msk.convert("RGBa").resize(sz, Image.LANCZOS).convert("RGBA")
    m.putalpha(255)
    return b, m

def main(out_dir):
    cells = []
    for stripe in (0, 1):
        for skin in range(4):
            for hair in range(5):
                for pose in range(3):
                    cells.append(sprite(stripe, skin, hair, pose))
    pw, ph = W * Q + PAD * 2, H * Q + PAD * 2
    rows = (len(cells) + COLS - 1) // COLS
    A = Image.new("RGBA", (COLS * pw, rows * ph), (0, 0, 0, 0))
    M = Image.new("RGBA", A.size, (0, 0, 0, 255))
    for i, (b, m) in enumerate(cells):
        x, y = (i % COLS) * pw + PAD, (i // COLS) * ph + PAD
        A.paste(b, (x, y)); M.paste(m, (x, y))
    A.save(f"{out_dir}/crowd_atlas.png", optimize=True)
    M.convert("RGB").save(f"{out_dir}/crowd_tint.png", optimize=True)
    print(A.size, len(cells))

main(sys.argv[1])
