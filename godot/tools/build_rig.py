"""Kahraman iskeleti kurucu.
Ayiklanmis parcalardan (tools/key_extract.py ciktisi) kanonik parcalar uretir:
 - uzuvlar dik dondurulur: eklem ustte ortada, alt eklem altta ortada
 - govdeden boyun / omuz / kalca noktalari olculur
Cikti: assets/rig/<ad>/*.png + rig.json
kullanim: build_rig.py <ad>   (HEROES tablosundan)"""
import json, math, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = "/tmp/ex"

# parca: (klasor, indeks) ; 'split': tam bacak/kol -> (ust, alt) dizden/dirsekten bolunur
HEROES = {
    "flame_knight": dict(src="parts_alev", head=0, torso=1, skirt=6, cape=2, back=3,
        ua=(4, 5), fa=(7, 8), thigh=(9, 10), shin=(11, 12), face="face_alev", thigh_w=1.45),
    "stone_guardian": dict(src="parts_kaya", head=0, torso=4, skirt=11, cape=10, back=12,
        ua=(1, 3), fa=(7, 8), thigh=(15, 15), shin=(14, 14), face="face_kaya", thigh_w=1.15, boot_w=1.15, back_rot=0.0, back_scale=0.8),
    "blade_master": dict(src="parts_kilic", head=0, torso=1, skirt=2, back=3,
        ua=(5, 6), fa=(7, 8), thigh=(9, 9), shin=(10, 10), face="face_kilic",
        extras=[("tail", 4, "head", (0.12, 0.42), 0.3, "back")]),
    "frost_knight": dict(src="parts_buz", head=0, torso=1, skirt=2, cape=7, back=3,
        ua=(4, 6), fa=(5, 8), thigh=(9, 11), shin=(10, 12), face="face_buz"),
    "storm_shaman": dict(src="parts_ejder", head=0, torso=1, skirt=9, cape=8, back=2,
        ua=(4, 4), fa=(7, 3), leg=(10, 11), face="face_ejder", neck=0.74,
        extras=[("pad", 6, "ua_f", (0.5, 0.15), 0.0, "front"), ("bolt", 5, "back", (0.5, 0.05), 0.0, "fx")]),
    "spirit_shaman": dict(src="parts_ruh", head=0, torso=4, skirt=9, back=2,
        arm=(6, 5), thigh=(10, 10), legsplit=(8, 11), face="face_ruh", thigh_w=1.15,
        extras=[("braid", 1, "head", (0.25, 0.55), 0.15, "back"), ("orb", 3, "fa_f", (0.5, 1.0), 0.0, "fx")]),
    "shadow_ninja": dict(src="parts_golge", head=0, torso=1, skirt=2, back=9,
        ua=("parts_golge_arms", 4, 6), fa=("parts_golge_arms", 5, 5), thigh=(13, 13), shin=(14, 14), face="face_golge", face_happy="face_golge_happy", arm_s=0.72,
        extras=[("scarf", 3, "torso", (0.6, 0.08), 0.2, "back"), ("dagger2", 10, "torso", (0.6, 0.45), -0.5, "back")]),
    "forest_archer": dict(src="parts_okcu", head=0, torso=2, skirt=5, cape=4, back=10,
        arm=(1, 3), leg=(7, 9), face="face_okcu",
        extras=[("quiver", 11, "torso", (0.65, 0.35), 0.35, "back")]),
}


def load(src, i):
    return Image.open(f"{EX}/{src}/{i:02d}.png").convert("RGBA")


def alpha_mask(im):
    return np.array(im)[..., 3] > 100


def orient(im, top_rule):
    """Uzvu dik dondur. top_rule: 'wide' (genis uc ustte) / 'narrow'"""
    m = alpha_mask(im)
    ys, xs = np.nonzero(m)
    c = np.cov(np.vstack([xs - xs.mean(), ys - ys.mean()]))
    w, v = np.linalg.eigh(c)
    ax = v[:, np.argmax(w)]
    ang = math.degrees(math.atan2(ax[1], ax[0]))   # eksenin x'e gore acisi
    im2 = im.rotate(ang - 90.0, resample=Image.BICUBIC, expand=True)
    im2 = im2.crop(im2.getbbox())
    m2 = alpha_mask(im2)
    h = m2.shape[0]
    q = max(1, h // 4)
    wt = m2[:q].sum()
    wb = m2[-q:].sum()
    want_wide_top = top_rule == "wide"
    if (wt < wb) == want_wide_top:
        im2 = im2.rotate(180, expand=True)
    return im2


def foot_right(im):
    """Alttaki ayak saga baksin (karakter saga bakiyor)."""
    m = alpha_mask(im)
    h, w = m.shape
    bot = m[int(h * 0.8):]
    ys, xs = np.nonzero(bot)
    if len(xs) and xs.mean() < w / 2:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    return im


def end_center(m, top=True, frac=0.06):
    h = m.shape[0]
    n = max(2, int(h * frac))
    rows = m[:n] if top else m[-n:]
    ys, xs = np.nonzero(rows)
    return float(xs.mean()) if len(xs) else m.shape[1] / 2


def limb(im, rule, foot=False):
    im = orient(im, rule)
    if foot:
        im = foot_right(im)
    m = alpha_mask(im)
    h = m.shape[0]
    # eklem: ust ucun biraz icinde (yuvarlak uc ust uste binsin)
    top = (end_center(m, True), h * 0.1)
    bot = (end_center(m, False, 0.25) if not foot else end_center(m[: int(h * 0.75)], False, 0.1), h * 0.9)
    return im, top, bot


def split(im, frac=0.5, over=0.08):
    """Dik duran tam uzvu ikiye bol (biraz ust uste binsin)."""
    w, h = im.size
    cut = int(h * frac)
    o = int(h * over)
    return im.crop((0, 0, w, min(h, cut + o))), im.crop((0, max(0, cut - o), w, h))


def main(name):
    cfg = HEROES[name]
    src = cfg["src"]
    out = f"{ROOT}/assets/rig/{name}"
    os.makedirs(out, exist_ok=True)
    rig = {"pivot": {}, "joint": {}, "extras": [], "size": {}}

    def save(part, im, pivot):
        im.save(f"{out}/{part}.png")
        rig["pivot"][part] = [round(pivot[0], 1), round(pivot[1], 1)]
        rig["size"][part] = list(im.size)

    def get(spec, i):
        if isinstance(spec[0], str):
            return load(spec[0], spec[1 + i])
        return load(src, spec[i])

    # govde
    torso = load(src, cfg["torso"])
    tm = alpha_mask(torso)
    th, tw = tm.shape
    neck_x = end_center(tm, True, 0.04)
    hip = (end_center(tm, False, 0.1), th * 0.95)
    save("torso", torso, hip)
    ox, oy = hip
    # yaka: ustteki dar boyun cikintisinin bittigi satir -> bas boynu buraya oturur (bosluk kalmaz)
    wid = tm.sum(1)
    collar = int(th * 0.06)
    for y in range(int(th * 0.4)):
        if wid[y] > wid.max() * 0.45:
            collar = y
            break
    rig["joint"]["head"] = [neck_x - ox, collar + cfg.get("collar_dy", 0.0) * th - oy]
    rows = np.nonzero(tm[int(th * 0.2)])[0]
    l, r = (rows.min(), rows.max()) if len(rows) else (0, tw)
    rig["joint"]["shoulder_f"] = [l + (r - l) * 0.2 - ox, th * 0.2 - oy]
    rig["joint"]["shoulder_b"] = [l + (r - l) * 0.78 - ox, th * 0.2 - oy]
    rig["joint"]["cape"] = [neck_x - ox + tw * 0.08, th * 0.1 - oy]
    rig["joint"]["back"] = [tw * 0.1, -th * 0.5]
    # bas
    head = load(src, cfg["head"])
    hm = alpha_mask(head)
    hh = hm.shape[0]
    nf = cfg.get("neck", 0.97)
    hp = (end_center(hm[: int(hh * nf)], False, 0.05), hh * nf)
    save("head", head, hp)
    # etek
    if "skirt" in cfg:
        sk = load(src, cfg["skirt"])
        sm = alpha_mask(sk)
        save("skirt", sk, (sm.shape[1] / 2, sm.shape[0] * 0.08))
        rig["joint"]["skirt"] = [0.0, -th * 0.04]
        sh = sm.shape[0]
    else:
        sh = th * 0.2
    rig["joint"]["hip_f"] = [tw * 0.13, sh * 0.25]   # on bacak one dogru kalcadan: X bacak olmaz
    rig["joint"]["hip_b"] = [-tw * 0.13, sh * 0.25]
    # kollar
    for k, side in ((0, "f"), (1, "b")):
        if "arm" in cfg:
            full = orient(load(src, cfg["arm"][k]), "wide")
            up, lo = split(full, 0.48)
            up_im, up_t, up_b = limb_from(up, "wide")
            lo_im, lo_t, lo_b = limb_from(lo, "narrow", already=True)
        else:
            up_im, up_t, up_b = limb(get(cfg["ua"], k), "wide")
            lo_im, lo_t, lo_b = limb(get(cfg["fa"], k), "narrow")
        a_s = cfg.get("arm_s", 1.0)
        if a_s != 1.0:
            rs = lambda im: im.resize((max(1, int(im.size[0] * a_s)), max(1, int(im.size[1] * a_s))), Image.LANCZOS)
            up_im, lo_im = rs(up_im), rs(lo_im)
            up_t, up_b, lo_t = [(v[0] * a_s, v[1] * a_s) for v in (up_t, up_b, lo_t)]
        save(f"arm_up_{side}", up_im, up_t)
        save(f"arm_lo_{side}", lo_im, lo_t)
        rig["joint"][f"elbow_{side}"] = [up_b[0] - up_t[0], up_b[1] - up_t[1]]
    # bacaklar
    for k, side in ((0, "f"), (1, "b")):
        if "leg" in cfg:
            full = foot_right(orient(load(src, cfg["leg"][k]), "wide"))
            th_im, sh_im = split(full, 0.45)
            t_im, t_t, t_b = limb_from(th_im, "wide", already=True)
            s_im, s_t, s_b = limb_from(sh_im, "narrow", already=True, foot=True)
        elif "legsplit" in cfg:
            t_im, t_t, t_b = limb(load(src, cfg["thigh"][k]), "wide")
            full = foot_right(orient(load(src, cfg["legsplit"][k]), "wide"))
            _, sh_im = split(full, 0.42)
            s_im, s_t, s_b = limb_from(sh_im, "narrow", already=True, foot=True)
        else:
            t_im, t_t, t_b = limb(load(src, cfg["thigh"][k]), "wide")
            s_im, s_t, s_b = limb(load(src, cfg["shin"][k]), "narrow", foot=True)
        save(f"thigh_{side}", t_im, t_t)
        save(f"boot_{side}", s_im, s_t)
        rig["joint"][f"knee_{side}"] = [t_b[0] - t_t[0], t_b[1] - t_t[1]]
        if side == "f":
            leg_len = (t_b[1] - t_t[1]) + (s_im.size[1] * 0.97 - s_t[1])
    rig["leg_len"] = round(float(leg_len + sh * 0.25 - th * 0.04 + th * 0.05), 1)
    # pelerin, sirt esyasi
    if "cape" in cfg:
        cp = load(src, cfg["cape"])
        cm = alpha_mask(cp)
        save("cape", cp, (end_center(cm, True, 0.05), cm.shape[0] * 0.04))
    if "back" in cfg:
        bk = load(src, cfg["back"])
        save("back", bk, (bk.size[0] / 2, bk.size[1] / 2))
        rig["back_rot"] = cfg.get("back_rot", -0.55)
        rig["back_scale"] = cfg.get("back_scale", 1.0)
    # ekler
    for (ename, idx, parent, at, rot, layer) in cfg.get("extras", []):
        ex = load(src, idx)
        save(ename, ex, (ex.size[0] * 0.5, ex.size[1] * (0.5 if layer == "fx" else 0.1)))
        rig["extras"].append({"part": ename, "parent": parent, "at": at, "rot": rot, "layer": layer})
    # yuz ifadeleri: ayni boya getir
    if cfg.get("face"):
        fdir = f"{EX}/{cfg['face']}"
        files = sorted(f for f in os.listdir(fdir) if f[0].isdigit())
        faces = [Image.open(f"{fdir}/{f}").convert("RGBA") for f in files]
        big = max(f.size[0] * f.size[1] for f in faces)
        faces = [f for f in faces if f.size[0] * f.size[1] > big * 0.45][:2]   # soldan saga: mutlu, aci
        if cfg.get("face_happy"):
            faces[0] = Image.open(f"{EX}/{cfg['face_happy']}/00.png").convert("RGBA")
        for nm, f in zip(("head_happy", "head_hurt"), faces):
            k = head.size[0] / f.size[0]
            f = f.resize((max(1, int(f.size[0] * k)), max(1, int(f.size[1] * k))), Image.LANCZOS)
            fm = alpha_mask(f)
            # ayni genislige olceklendi: pivotu normal basla ayni yere (alt hizali) koy -> yuz kaymaz
            save(nm, f, (hp[0], f.size[1] - (hh - hp[1]) * (0.5 if nf < 0.9 else 1.0)))
    rig["height"] = round(float(rig["leg_len"] - rig["joint"]["head"][1] + hh * nf), 1)
    rig["thigh_w"] = cfg.get("thigh_w", 1.0)
    rig["boot_w"] = cfg.get("boot_w", 1.0)
    json.dump(rig, open(f"{out}/rig.json", "w"), indent=1)
    print(name, "boy", rig["height"], "bacak", rig["leg_len"])


def limb_from(im, rule, already=False, foot=False):
    if not already:
        return limb(im, rule, foot)
    im = im.crop(im.getbbox())
    m = alpha_mask(im)
    h = m.shape[0]
    top = (end_center(m, True), h * 0.1)
    bot = (end_center(m, False, 0.25) if not foot else end_center(m[: int(h * 0.75)], False, 0.1), h * 0.9)
    return im, top, bot


if __name__ == "__main__":
    for n in (sys.argv[1:] or HEROES.keys()):
        main(n)
