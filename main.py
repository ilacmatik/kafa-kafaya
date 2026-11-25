"""KAFA KAFAYA - iki kisilik yerel ag kafa topu oyunu.

Calistirma:  python main.py
Exe:         build.bat (PyInstaller ile tek dosya)
"""
import math
import os
import random
import socket
import sys
import time

# Windows ekran olcegi (%125/%150) yuzunden goruntu bulaniklasmasin
if sys.platform == "win32":
    os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
# tam ekranda buyutme yumusak (pikselli degil) olsun
os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "1")
os.environ.setdefault("SDL_HINT_RENDER_SCALE_QUALITY", "1")

import pygame  # noqa: E402

import fx  # noqa: E402
import gfx  # noqa: E402
from gfx import draw as gd, transform as tf  # noqa: E402
import net  # noqa: E402
import sim  # noqa: E402

W, H = sim.W, sim.H
FPS = 60
STEP = 1.0 / 60
VERSION = 1
DURATIONS = [60, 90, 120, 180]
LEVELS = ["KOLAY", "NORMAL", "ZOR"]
STADIUMS = [
    {"name": "GECE ARENASI", "bg": "stadium_night_clean.jpg", "crowd": "crowd_night.json",
     "mask": "crowd_mask_night.png", "light": 0.82,
     "lamps": ((90, 80), (435, 194), (851, 194), (1180, 80)), "boards": None},
    {"name": "TİMSAH ARENA", "bg": "stadium_timsah_clean.jpg",
     "wx": {"rain": "stadium_timsah_rain_clean.jpg", "snow": "stadium_timsah_snow_clean.jpg"}, "crowd": "crowd_timsah.json",
     "mask": "crowd_mask_timsah.png", "light": 0.95, "lamps": (), "boards": (527, 24)},
]
ADS = [("ULUDAĞ GAZOZ", (255, 214, 60)), ("MATLI", (255, 120, 90)), ("TURKCELL", (255, 205, 40)),
       ("ÖZDİLEK", (255, 255, 255)), ("KÖFTECİ YUSUF", (255, 90, 80))]
PODIUMS = [158, 352, 545, 735, 927, 1122]   # karakter secim podyumlari (x)

GOLD = (255, 205, 60)
WHITE = (255, 255, 255)
DARK = (18, 22, 38)
P_COLORS = [(70, 160, 255), (255, 85, 85)]
FIRE_C = (255, 140, 40)
ICE_C = (110, 220, 255)

KEYS_SOLO = {
    "l": (pygame.K_a, pygame.K_LEFT), "r": (pygame.K_d, pygame.K_RIGHT),
    "j": (pygame.K_w, pygame.K_UP), "k": (pygame.K_SPACE, pygame.K_k),
    "s": (pygame.K_s, pygame.K_DOWN), "o": (pygame.K_e, pygame.K_RCTRL),
}
KEYS_P1 = {
    "l": (pygame.K_a,), "r": (pygame.K_d,), "j": (pygame.K_w,),
    "k": (pygame.K_SPACE,), "s": (pygame.K_s,), "o": (pygame.K_e,),
}
KEYS_P2 = {
    "l": (pygame.K_LEFT,), "r": (pygame.K_RIGHT,), "j": (pygame.K_UP,),
    "k": (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_KP0), "s": (pygame.K_DOWN, pygame.K_KP1),
    "o": (pygame.K_RCTRL, pygame.K_KP2),
}
WEATHERS = [("clear", "AÇIK HAVA"), ("rain", "YAĞMUR"), ("snow", "KAR"), ("wind", "RÜZGAR"), ("random", "RASTGELE")]


def pick_weather(i):
    w = WEATHERS[i % len(WEATHERS)][0]
    return random.choice(["clear", "rain", "snow", "wind"]) if w == "random" else w


def _sw(v):
    return [v[1], v[0]] if isinstance(v, list) and len(v) == 2 else v


def mirror_snap(m):
    """Istemci icin goruntuyu aynala: kendi oyuncun solda, rakip sagda."""
    m = dict(m)
    b = list(m["b"])
    b[0] = W - b[0]
    b[2] = -b[2]
    b[4] = -b[4]
    m["b"] = b
    ps = []
    for p in m["p"][::-1]:
        q = list(p)
        q[0] = W - q[0]
        q[2] = -q[2]
        q[3] = -q[3]
        ps.append(q)
    m["p"] = ps
    for k in ("sc", "sh", "gl", "mg"):
        if k in m:
            m[k] = _sw(m[k])
    if m.get("pu"):
        pu = list(m["pu"])
        pu[1] = W - pu[1]
        m["pu"] = pu
    if m.get("scr", -1) in (0, 1):
        m["scr"] = 1 - m["scr"]
    if m.get("win", -1) in (0, 1):
        m["win"] = 1 - m["win"]
    if "wd" in m:
        m["wd"] = -m["wd"]
    if m.get("pen"):
        m["pen"] = [1 - m["pen"][0], m["pen"][1][::-1]]
    if m.get("st"):
        m["st"] = {k: _sw(v) for k, v in m["st"].items()}
    if "ag" in m and m["ag"]:
        m["ag"] = _sw(m["ag"])
    evs = []
    for ev in m.get("ev", []):
        parts = ev.split(":")
        n = parts[0]
        if n in ("goal", "jump2", "shoulder", "bump", "bicycle", "pen_goal", "pen_miss", "magnet", "glove",
                 "quake", "bolt") and len(parts) > 1:
            parts[1] = str(1 - int(parts[1]))
            if n == "bolt" and len(parts) > 2:
                parts[2] = str(int(W - int(parts[2])))
        elif n == "pu" and len(parts) > 2:
            parts[2] = str(1 - int(parts[2]))
        evs.append(":".join(parts))
    m["ev"] = evs
    return m


def record_path():
    return os.path.join(os.path.expanduser("~"), "kafakafaya_kayit.json")


def load_record():
    import json
    try:
        with open(record_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_record(rec):
    import json
    try:
        with open(record_path(), "w", encoding="utf-8") as fh:
            json.dump(rec, fh)
    except OSError:
        pass

POWERS = {   # isim, renk, super bar rengi
    "fire": ("ATEŞ ŞUTU", (255, 140, 40), "fire"),
    "ice": ("BUZ ŞUTU", (110, 220, 255), "ice"),
    "magnet": ("MIKNATIS", (200, 130, 255), "fire"),
    "glove": ("DEV ELDİVEN", (255, 214, 60), "fire"),
    "bolt": ("YILDIRIM", (255, 235, 90), "ice"),
    "quake": ("DEPREM", (230, 150, 90), "fire"),
}

GOAL_LINES = {
    "super": ["SÜPER GÜÇ! DURDURULAMAZ!", "BU ŞUT DEĞİL, FÜZE!", "KALECİ ERİDİ GİTTİ!", "GÜÇ SENDE, GOL BİZDE!"],
    "head": ["KAFAYLA ÇAKTI!", "KAFA ÇALIŞIYOR MAŞALLAH!", "KAFA GOLÜ! NE YÜKSELDİ AMA!", "KAFANI KULLAN DEMİŞTİM!"],
    "lob": ["AŞIRTMA! BAKAKALDI!", "GÖKYÜZÜNDEN DÜŞTÜ!", "TOP KAFANIN ÜSTÜNDEN UÇTU!", "YAĞMUR GİBİ İNDİ!"],
    "flick": ["TOPUKLA! ŞOV YAPIYOR!", "TOPUK GOLÜ! AYIP OLDU!", "BAKMADAN ATTI!"],
    "own": ["KENDİ KALESİNE! TEŞEKKÜRLER!", "ÇOK AYIP, KENDİ KALENE!", "HEDİYE GOL! SAĞ OL!", "YANLIŞ KALE KARDEŞİM!"],
    "hard": ["ÇOK SERT! TUTABİLİRSEN TUT!", "FÜZE GİBİ GİRDİ!", "FİLEYİ YIRTTI!", "BU NE VURUŞ BE!", "ELİNİ YAKARDI!"],
    "volley": ["VOLE! HAVADA YAKALADI!", "NE VOLE AMA!", "DÜŞMEDEN VURDU!"],
    "bicycle": ["RÖVAŞATA! İNANILMAZ!", "TERS MAKAS! FİLELER!", "BU GOL YILIN GOLÜ!", "HAVADA TAKLA ATTI!"],
    "smash": ["SMAÇ KAFA! YERE GÖMDÜ!", "YUKARIDAN ÇAKTI!", "KAFAYI GÖMDÜ GİTTİ!", "VOLEYBOL MU OYNUYORUZ?"],
    "power": ["ŞARJLI FÜZE!", "BEKLEDİ, BEKLEDİ... BAM!", "TAM GÜÇ! FİLE DAYANMADI!", "BU ŞUTA KALE DAYANMAZ!"],
    "any": ["NASIL ATTIM AMA!", "KALECİ NEREDEYDİ?", "UYUMA, MAÇ VAR!", "TAM DOKSANA!", "BİR DAHA DENE!",
            "ÇOK KOLAY OLDU!", "BU DA MI GOL?", "DERS GİBİ GOL!"],
}

PU_TEXT = {"speed": "HIZ!", "jump": "SÜPER ZIPLAMA!", "shield": "BUZ KALKAN!",
           "freeze": "DONDURMA!", "gold": "SÜPER DOLDU!"}


def res(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


try:
    with open(res("assets", "version.txt"), encoding="utf-8") as _vf:
        VERSION_TEXT = _vf.read().strip().replace("surum-", "Sürüm ")
except OSError:
    VERSION_TEXT = "Sürüm geliştirme"


# ====================================================================== yazi
_fonts = {}
_tcache = {}


FONT_FILES = {True: "FiraSans-BlackItalic.ttf", False: "FiraSans-Black.ttf"}
GRADS = {
    (255, 205, 60): ((255, 242, 160), (255, 168, 24)),     # altin
    (255, 255, 255): ((255, 255, 255), (198, 214, 245)),   # beyaz
    (255, 140, 40): ((255, 226, 120), (255, 96, 20)),      # ates
    (110, 220, 255): ((225, 250, 255), (70, 180, 255)),    # buz
}


def get_font(size, title=False):
    key = (size, title)
    f = _fonts.get(key)
    if f is None:
        try:
            f = pygame.font.Font(res("assets", "fonts", FONT_FILES[title]), size)
        except Exception:
            names = "arialblack,segoeuiblack,impact,arial" if title else "segoeuisemibold,segoeui,arial,tahoma"
            try:
                f = pygame.font.SysFont(names, size, bold=not title)
            except Exception:
                f = pygame.font.Font(None, size)
        _fonts[key] = f
    return f


_OUT_DIRS = [(math.cos(a * math.pi / 8), math.sin(a * math.pi / 8)) for a in range(16)]


def text_surf(txt, size, color=WHITE, outline=3, ocolor=(12, 14, 34), title=True, shadow=None):
    """Oyun yazisi: (istege bagli) gradyan dolgu, kalin yuvarlak kontur ve alt golge. gfx.Img dondurur."""
    key = (txt, size, color, outline, ocolor, title, shadow)
    s = _tcache.get(key)
    if s is not None:
        return s
    k = gfx.K
    f = get_font(max(6, int(round(size * k))), title)
    mask = f.render(txt, True, (255, 255, 255))
    w, h = mask.get_size()
    o = int(round(outline * k))
    if shadow is None:
        shadow = outline > 0
    sh = int(round(max(2, outline * 0.9) * k)) if shadow else 0
    surf = pygame.Surface((w + 2 * o + 2, h + 2 * o + sh + 2), pygame.SRCALPHA)
    if o:
        om = f.render(txt, True, ocolor)
        rings = [(dx * o, dy * o) for dx, dy in _OUT_DIRS] + [(dx * o * 0.5, dy * o * 0.5) for dx, dy in _OUT_DIRS[::2]]
        if sh:
            shm = om.copy()
            shm.set_alpha(150)
            for dx, dy in rings:
                surf.blit(shm, (o + 1 + dx, o + 1 + dy + sh))
        for dx, dy in rings:
            surf.blit(om, (o + 1 + dx, o + 1 + dy))
    grad = GRADS.get(tuple(color)) if title or size >= 26 else None
    if grad:
        g = pygame.Surface((w, h), pygame.SRCALPHA)
        top, bot = grad
        for y in range(h):
            t = y / max(1, h - 1)
            g.fill(tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,), (0, y, w, 1))
        g.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(g, (o + 1, o + 1))
    else:
        surf.blit(f.render(txt, True, color), (o + 1, o + 1))
    s = gfx.Img(surf)
    if len(_tcache) > 600:
        _tcache.clear()
    _tcache[key] = s
    return s


def draw_text(surf, txt, size, pos, color=WHITE, anchor="center", outline=3, title=True, alpha=255):
    s = text_surf(txt, size, color, outline, title=title)
    if alpha < 255:
        s = s.copy()
        s.set_alpha(alpha)
    r = s.get_rect()
    setattr(r, anchor, (int(pos[0]), int(pos[1])))
    surf.blit(s, r)
    return r


_pills = {}


def _shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3])


def pill(surf, rect, color, border=(12, 14, 34), radius=None, gloss=True):
    """Parlak, gradyanli, koyu kenarli yuvarlak etiket."""
    r = pygame.Rect(rect)
    key = (r.w, r.h, tuple(color), border, radius, gloss)
    img = _pills.get(key)
    if img is None:
        k = gfx.K
        PW, PH = max(4, int(r.w * k)), max(4, int(r.h * k))
        rad = int((radius if radius is not None else r.h / 2) * k)
        bw = max(2, int(3 * k))
        out = pygame.Surface((PW, PH), pygame.SRCALPHA)
        pygame.draw.rect(out, border, out.get_rect(), 0, border_radius=rad)
        inner = pygame.Rect(bw, bw, PW - 2 * bw, PH - 2 * bw)
        g = pygame.Surface(inner.size, pygame.SRCALPHA)
        top, bot = _shade(color, 1.28), _shade(color, 0.78)
        for y in range(inner.h):
            t = y / max(1, inner.h - 1)
            g.fill(tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,), (0, y, inner.w, 1))
        m_ = pygame.Surface(inner.size, pygame.SRCALPHA)
        pygame.draw.rect(m_, (255, 255, 255, 255), m_.get_rect(), 0, border_radius=max(0, rad - bw))
        g.blit(m_, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        out.blit(g, inner.topleft)
        if gloss and inner.h > 8:
            hl = pygame.Surface((inner.w - 2 * bw, max(2, inner.h // 2 - bw)), pygame.SRCALPHA)
            pygame.draw.rect(hl, (255, 255, 255, 70), hl.get_rect(), 0, border_radius=max(0, rad - 2 * bw))
            out.blit(hl, (inner.x + bw, inner.y + max(1, bw // 2)))
        img = gfx.Img(out)
        if len(_pills) > 300:
            _pills.clear()
        _pills[key] = img
    surf.blit(img, r.topleft)


def draw_meter(surf, rect, frac, color, right=False, glow=False):
    """Yuvarlak dolum cubugu."""
    r = pygame.Rect(rect)
    pill(surf, r, (22, 28, 52), gloss=False)
    fw = int((r.w - 6) * max(0.0, min(1.0, frac)))
    if fw >= r.h - 6:
        fr = pygame.Rect(0, 0, fw, r.h - 6)
        fr.centery = r.centery
        if right:
            fr.right = r.right - 3
        else:
            fr.left = r.left + 3
        pill(surf, fr, color, border=_shade(color, 0.45))
    if glow:
        fx.blit_glow(surf, r.centerx, r.centery, r.w * 0.55, _shade(color, 0.35))


_segs = {}


def seg_img(name, h):
    """Gemini segment gorseli, h mantiksal yukseklikte."""
    key = (name, h)
    img = _segs.get(key)
    if img is None:
        raw = ASSETS.seg_raw[name]
        base_h = 322
        f = h / base_h
        img = gfx.from_surface(raw, (raw.get_width() * f, raw.get_height() * f))
        _segs[key] = img
    return img


def stat_seg(surf, x, y, on, maxed, t):
    """Ozellik segmenti: dolu (altin), 5/5 (yesil parlak), bos (lacivert yuva)."""
    if on and maxed:
        fx.blit_glow(surf, x, y, 16 + 3 * math.sin(t * 6), (20, 60, 25))
        img = seg_img("seg_green_glow", 21)
    elif on:
        img = seg_img("seg_gold", 21)
    else:
        img = seg_img("seg_empty", 21)
    surf.blit(img, img.get_rect(center=(x, y)))


def seg_meter(surf, rect, frac, kind, right=False, flash=False):
    """Maç ici super bari: 8 parlak segment."""
    r = pygame.Rect(rect)
    pill(surf, r.inflate(10, 8), (16, 22, 46), gloss=False)
    n = 8
    h = r.h
    step = r.w / n
    filled = frac * n
    name = "seg_orange" if kind == "fire" else "seg_blue"
    for i in range(n):
        idx = (n - 1 - i) if right else i
        cx = r.x + step * (idx + 0.5)
        part = max(0.0, min(1.0, filled - i))
        empty = seg_img("seg_empty", h)
        surf.blit(empty, empty.get_rect(center=(cx, r.centery)))
        if part > 0:
            img = seg_img(name, h)
            if part < 1:
                img.set_alpha(int(80 + 140 * part))
            surf.blit(img, img.get_rect(center=(cx, r.centery)))
            img.set_alpha(255)
    if flash:
        fx.blit_glow(surf, r.centerx, r.centery, r.w * 0.55, (70, 40, 10) if kind == "fire" else (20, 50, 80))


def panel(surf, rect, color=(15, 20, 40, 200), radius=16, border=None, bw=3):
    r = pygame.Rect(rect)
    k = gfx.K
    s = pygame.Surface((max(1, int(r.w * k)), max(1, int(r.h * k))), pygame.SRCALPHA)
    pygame.draw.rect(s, color, s.get_rect(), 0, border_radius=int(radius * k))
    if border:
        pygame.draw.rect(s, border, s.get_rect(), max(1, int(bw * k)), border_radius=int(radius * k))
    surf.blit(gfx.Img(s), r.topleft)


# ====================================================================== ses
class Sound:
    def __init__(self):
        self.ok = False
        self.muted = False
        self.hidden = False
        self.snd = {}
        self.last = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 2, 512)
            freq, size, ch = pygame.mixer.get_init()
            self.freq, self.ch = freq, ch
            if abs(size) != 16:
                return
            pygame.mixer.set_num_channels(24)
            self._build()
            self.ok = True
        except Exception:
            self.ok = False

    def _mk(self, samples, vol=0.6):
        import array
        peak = max(1e-6, max(abs(v) for v in samples))
        g = vol / peak
        a = array.array("h")
        ch = self.ch
        for v in samples:
            v = int(max(-1.0, min(1.0, v * g)) * 32000)
            a.append(v)
            if ch == 2:
                a.append(v)
        return pygame.mixer.Sound(buffer=a.tobytes())

    def _build(self):
        sr = self.freq
        rnd = random.Random(7)
        sin = math.sin
        tau = math.tau

        def n(sec):
            return int(sr * sec)

        def env_ad(N, att, dec_pow=2.0):
            a = max(1, int(N * att))
            return [(i / a) if i < a else (1 - (i - a) / max(1, N - a)) ** dec_pow for i in range(N)]

        def noise(dur, lp=0.2, hp=0.0):
            out, y, z = [], 0.0, 0.0
            for _ in range(n(dur)):
                x = rnd.random() * 2 - 1
                y += lp * (x - y)
                if hp:
                    z += hp * (y - z)
                    out.append(y - z)
                else:
                    out.append(y)
            return out

        def mul(a, b):
            return [x * y for x, y in zip(a, b)]

        def mix(*parts):
            L = max(len(p) for p, _ in parts)
            out = [0.0] * L
            for p, g in parts:
                for i, v in enumerate(p):
                    out[i] += v * g
            return out

        def pad(sig, before):
            return [0.0] * n(before) + sig

        def thump(f0, f1, dur, click=0.4, slap=0.0):
            N = n(dur)
            out, ph = [], 0.0
            for i in range(N):
                t = i / N
                f = f1 + (f0 - f1) * (1 - t) ** 3
                ph += tau * f / sr
                e = (1 - t) ** 2.5
                v = sin(ph) * e
                if i < n(0.012):
                    v += click * (rnd.random() * 2 - 1) * (1 - i / n(0.012))
                out.append(v)
            if slap:
                sl = noise(0.04, 0.9, 0.5)
                sl = mul(sl, [(1 - i / len(sl)) ** 3 for i in range(len(sl))])
                out = mix((out, 1), (sl, slap))
            return out

        def bell(freqs, dur, decay):
            N = n(dur)
            return [sum(sin(tau * f * i / sr) * math.exp(-decay * k * i / sr) for k, f in enumerate(freqs, 1))
                    for i in range(N)]

        def whistle(dur):
            out, ph = [], 0.0
            N = n(dur)
            for i in range(N):
                t = i / sr
                f = 2700 + 160 * sin(tau * 28 * t)
                ph += tau * f / sr
                e = min(1, t * 60) * min(1, (dur - t) * 25)
                out.append((sin(ph) + 0.25 * sin(2 * ph)) * e + (rnd.random() - 0.5) * 0.2 * e)
            return out

        def voices(dur, count, f_lo, f_hi, glide, harm, att=0.15, rel=0.5, vib=5.0):
            N = n(dur)
            out = [0.0] * N
            for _ in range(count):
                f0 = rnd.uniform(f_lo, f_hi)
                ph = rnd.uniform(0, tau)
                vr = rnd.uniform(4, 7)
                st = rnd.uniform(0, 0.12)
                for i in range(N):
                    t = i / sr
                    if t < st:
                        continue
                    u = i / N
                    f = f0 * (1 + glide * u) * (1 + 0.012 * sin(tau * vr * t))
                    ph += tau * f / sr
                    v = sin(ph) + harm[0] * sin(2 * ph) + harm[1] * sin(3 * ph) + harm[2] * sin(4 * ph)
                    e = min(1, (t - st) / att) * min(1, (dur - t) / rel)
                    out[i] += v * e
            return out

        def claps(dur, times):
            N = n(dur)
            out = [0.0] * N
            for t0 in times:
                for _ in range(6):
                    s0 = int((t0 + rnd.uniform(-0.025, 0.025)) * sr)
                    L = n(0.03)
                    for k in range(L):
                        if 0 <= s0 + k < N:
                            out[s0 + k] += (rnd.random() * 2 - 1) * (1 - k / L) ** 4
            return out

        s = self.snd
        # top sesleri
        s["kick"] = self._mk(thump(190, 52, 0.22, 0.7, 0.6), 0.95)
        s["head"] = self._mk(thump(320, 140, 0.13, 0.3, 0.35), 0.75)
        s["bounce"] = self._mk(thump(140, 70, 0.11, 0.2, 0.15), 0.45)
        s["land"] = self._mk(thump(90, 50, 0.08, 0.3), 0.25)
        s["post"] = self._mk(mix((bell([523, 1415, 2560, 3810], 0.9, 3.2), 1), (thump(240, 120, 0.1, 0.8), 0.6)), 0.6)
        s["swing"] = self._mk(mul(noise(0.16, 0.35, 0.1), [sin(math.pi * i / n(0.16)) for i in range(n(0.16))]), 0.22)
        s["jump"] = self._mk(mul(noise(0.12, 0.25, 0.05), env_ad(n(0.12), 0.3)), 0.18)
        # hakem
        s["whistle"] = self._mk(whistle(0.5), 0.45)
        s["end"] = self._mk(whistle(0.28) + [0] * n(0.1) + whistle(0.28) + [0] * n(0.1) + whistle(0.9), 0.45)
        s["beep"] = self._mk(mul(bell([880], 0.18, 6), env_ad(n(0.18), 0.02)), 0.35)
        s["tick"] = self._mk(thump(1800, 1500, 0.04, 0.2), 0.25)
        # tribun
        roar_d = 3.6
        roar = mix((noise(roar_d, 0.12, 0.004), 1.0), (voices(roar_d, 14, 260, 520, 0.08, (0.45, 0.3, 0.15)), 0.12),
                   (claps(roar_d, [0.6 + k * 0.14 for k in range(18)]), 0.35))
        Nr = len(roar)
        roar = mul(roar, [min(1, i / n(0.35)) * (1 - i / Nr) ** 0.9 for i in range(Nr)])
        horn = mul(bell([233, 294, 349, 466], 1.3, 0.6), env_ad(n(1.3), 0.05, 1.2))
        s["goal"] = self._mk(mix((roar, 1), (pad(horn, 0.15), 0.35)), 0.9)
        ooh = mix((voices(1.4, 12, 150, 260, -0.22, (0.25, 0.05, 0.0), 0.12, 0.6), 1),
                  (noise(1.4, 0.06), 0.4))
        s["ooh"] = self._mk(mul(ooh, env_ad(len(ooh), 0.1, 1.3)), 0.55)
        cheer = mix((voices(1.5, 12, 300, 560, 0.18, (0.5, 0.35, 0.2), 0.08, 0.7), 1), (noise(1.5, 0.15), 0.7))
        s["cheer"] = self._mk(mul(cheer, env_ad(len(cheer), 0.06, 1.5)), 0.5)
        amb_d = 6.0
        amb = mix((noise(amb_d, 0.05, 0.002), 1.0), (noise(amb_d, 0.3, 0.2), 0.25),
                  (claps(amb_d, [1.0, 1.25, 1.5, 1.62, 1.75, 4.0, 4.25, 4.5, 4.62, 4.75]), 0.18))
        Na = len(amb)
        lfo = [0.8 + 0.2 * sin(tau * i / Na * 3) for i in range(Na)]
        fade = n(0.25)
        amb = [v * lfo[i] * min(1, i / fade, (Na - i) / fade) for i, v in enumerate(amb)]
        s["crowd"] = self._mk(amb, 0.16)
        # gucler
        whoosh = mul(noise(0.7, 0.45, 0.05), env_ad(n(0.7), 0.15, 1.5))
        crackle = [((rnd.random() * 2 - 1) if rnd.random() < 0.02 else 0) for _ in range(n(0.7))]
        s["super_fire"] = self._mk(mix((whoosh, 1), (thump(120, 40, 0.5, 0.9), 0.8), (crackle, 0.8)), 0.75)
        s["super_ice"] = self._mk(mix((bell([1568, 2093, 2637, 3136], 0.8, 2.5), 0.5),
                                      (mul(noise(0.6, 0.6, 0.4), env_ad(n(0.6), 0.05, 2)), 0.6)), 0.6)
        s["freeze"] = self._mk(mix((mul(noise(0.5, 0.9, 0.6), env_ad(n(0.5), 0.01, 3)), 1),
                                   (bell([2400, 3300], 0.5, 6), 0.4)), 0.5)
        s["shatter"] = self._mk(mix((mul(noise(0.45, 0.95, 0.7), env_ad(n(0.45), 0.005, 4)), 1),
                                    (bell([2900, 3700, 4600, 5300], 0.45, 7), 0.5)), 0.55)
        s["fire_hit"] = self._mk(mix((thump(110, 38, 0.45, 1.0, 0.8), 1), (whoosh, 0.6), (crackle, 0.7)), 0.9)
        s["pu"] = self._mk(sum([mul(bell([f], 0.12, 8), [1] * n(0.12)) for f in (660, 880, 1100, 1320)], []), 0.45)
        s["pu_spawn"] = self._mk(mul(bell([1318, 1760, 2637], 0.5, 5), env_ad(n(0.5), 0.02)), 0.3)
        s["shield"] = self._mk(mix((bell([660, 990, 1320], 0.45, 6), 1), (thump(200, 100, 0.1, 0.5), 0.6)), 0.5)
        s["block"] = self._mk(thump(230, 70, 0.28, 1.0, 0.8), 0.9)
        rise = []
        ph = 0.0
        for i in range(n(0.4)):
            u = i / n(0.4)
            ph += tau * (300 + 900 * u * u) / sr
            rise.append((sin(ph) + 0.4 * sin(2 * ph)) * min(1, u * 8) * (1 - u) ** 0.5)
        s["armed"] = self._mk(rise, 0.35)
        s["click"] = self._mk(thump(1200, 900, 0.035, 0.1), 0.3)
        fan = []
        for k, f in enumerate((523, 659, 784, 1046)):
            fan += mul(bell([f, f * 2], 0.16 if k < 3 else 0.6, 3), [1] * n(0.16 if k < 3 else 0.6))
        s["golden"] = self._mk(fan, 0.5)
        crack = [((rnd.random() * 2 - 1) * (1 - i / n(0.5)) ** 2 if rnd.random() < 0.08 else 0.0) for i in range(n(0.5))]
        s["pop"] = self._mk(mix((thump(420, 90, 0.18, 0.9), 1), (crack, 0.9)), 0.5)

    def play(self, name, gap=0.05, vol=1.0):
        if not self.ok or self.muted or self.hidden or name not in self.snd:
            return
        now = time.time()
        if now - self.last.get(name, 0) < gap:
            return
        self.last[name] = now
        ch = self.snd[name].play()
        if ch is not None and vol != 1.0:
            ch.set_volume(vol)

    def ambience(self, on):
        if not self.ok:
            return
        self.snd["crowd"].stop()
        if on and not self.muted:
            self.snd["crowd"].play(loops=-1)

    def toggle(self):
        self.muted = not self.muted
        if self.ok and self.muted:
            pygame.mixer.stop()


# ====================================================================== gorseller
class Assets:
    """Tum gorseller gfx.Img olarak (ekran cozunurlugunde keskin)."""

    def __init__(self):
        def L(f):
            return pygame.image.load(res("assets", f)).convert_alpha()

        def S(raw, w, h):
            return gfx.from_surface(raw, (w, h))

        def scaled(raw, f):
            return S(raw, raw.get_width() * f, raw.get_height() * f)

        self.stadiums = []
        vig = fx.make_vignette(int(W * gfx.K), int(H * gfx.K), 80)
        for sd in STADIUMS:
            st = pygame.transform.smoothscale(pygame.image.load(res("assets", sd["bg"])).convert(),
                                              (int(W * gfx.K), int(H * gfx.K)))
            st.blit(vig, (0, 0))  # vinyet arka plana gomulu
            self.stadiums.append(gfx.Img(st))
        self.stadium_wx = {}
        for si, sd in enumerate(STADIUMS):
            for wname, fn in sd.get("wx", {}).items():
                if os.path.exists(res("assets", fn)):
                    st = pygame.transform.smoothscale(pygame.image.load(res("assets", fn)).convert(),
                                                      (int(W * gfx.K), int(H * gfx.K)))
                    st.blit(vig, (0, 0))
                    self.stadium_wx[(si, wname)] = gfx.Img(st)
        self.banner_raw = {}
        for n in ("bn_hold", "bn_flag", "bn_pennant", "bn_sign"):
            if os.path.exists(res("assets", n + "0.png")):
                self.banner_raw[n] = [pygame.image.load(res("assets", "%s%d.png" % (n, k))).convert_alpha()
                                      for k in (0, 1)]
        self.board_strip = None
        self._shadow = {}
        GD, GH = sim.GOAL_D, sim.GROUND - sim.GOAL_TOP
        k = gfx.K
        sh = pygame.Surface((int(GD * k), int(GH * k)), pygame.SRCALPHA)
        for x in range(sh.get_width()):
            pygame.draw.line(sh, (20, 30, 40, 60 + int(50 * abs(x - sh.get_width() / 2) / sh.get_width())),
                             (x, 0), (x, sh.get_height()))
        self.net_shade = gfx.Img(sh)
        nl = pygame.Surface((int(GD * k), int(GH * k)), pygame.SRCALPHA)
        lw = max(1, int(2 * k))
        for x in range(0, GD + 1, 14):
            pygame.draw.line(nl, (240, 240, 245, 170), (x * k, 0), (x * k, GH * k), lw)
        for y in range(0, GH, 14):
            pygame.draw.line(nl, (240, 240, 245, 170), (0, y * k), (GD * k, y * k), lw)
        self.net_lines = gfx.Img(nl)
        # Gemini kale cizimi: on direk ic yuzu x=660, ust direk alti y=104, zemin y=598 (kaynak piksel)
        ga = pygame.image.load(res("assets", "goal_art.png")).convert_alpha()
        gp = pygame.image.load(res("assets", "goal_post.png")).convert_alpha()
        sy = (sim.GROUND - sim.GOAL_TOP) / (598 - 104)
        sx = 0.24
        self.goal_sx, self.goal_sy = sx, sy
        self.goal_back = gfx.from_surface(ga, (ga.get_width() * sx, ga.get_height() * sy))
        self.goal_front = gfx.from_surface(gp, (gp.get_width() * sx, gp.get_height() * sy))
        self.goal_back_r = tf.flip(self.goal_back, True, False)
        self.goal_front_r = tf.flip(self.goal_front, True, False)
        self.goal_pos = (sim.GOAL_D - 660 * sx, sim.GOAL_TOP - 104 * sy)          # sol kale sol-ust
        self.goal_post_x = sim.GOAL_D + (648 - 660) * sx
        mb = pygame.transform.smoothscale(pygame.image.load(res("assets", "menu_bg.jpg")).convert(),
                                          (int(W * k), int(H * k)))
        self.menu_bg = gfx.Img(mb)
        mbd = mb.copy()
        dark = pygame.Surface(mb.get_size(), pygame.SRCALPHA)
        dark.fill((4, 8, 24, 120))
        mbd.blit(dark, (0, 0))
        self.menu_bg_dark = gfx.Img(mbd)
        self.select_bg = gfx.Img(pygame.transform.smoothscale(
            pygame.image.load(res("assets", "select_bg.jpg")).convert(), (int(W * k), int(H * k))))
        self.idle, self.kick, self.idle_ice, self.kick_ice = [], [], [], []
        self.big, self.portrait = [], []
        self.big_celeb = []
        self.portrait_big = []
        self.kick_anchor = []
        self.poses = []
        import json
        try:
            with open(res("assets", "anchors.json"), encoding="utf-8") as fh:
                self.anchors = json.load(fh)
        except (OSError, ValueError):
            self.anchors = {}
        for i in range(6):
            idle = L("p%d_idle.png" % i)
            kick = L("p%d_kick.png" % i)
            sc = sim.CHARACTERS[i]["scale"]
            f = sim.BASE_H * sc / idle.get_height()
            iw = scaled(idle, f)
            kw = scaled(kick, f)
            self.idle.append(iw)
            self.kick.append(kw)
            self.idle_ice.append(self._ice(iw))
            self.kick_ice.append(self._ice(kw))
            self.kick_anchor.append(0.40)
            poses = {}
            if os.path.exists(res("assets", "p%d_run1.png" % i)):
                for name in ("run1", "run2", "jump", "celeb"):
                    poses[name] = scaled(L("p%d_%s.png" % (i, name)), f)
                poses["jump_ice"] = self._ice(poses["jump"])
            for name in ("bike", "shoulder"):
                if os.path.exists(res("assets", "p%d_%s.png" % (i, name))):
                    poses[name] = scaled(L("p%d_%s.png" % (i, name)), f)
            self.poses.append(poses)
            bh = 215
            fb = bh / idle.get_height()
            self.big.append(scaled(idle, fb))
            cp = res("assets", "p%d_celeb.png" % i)
            cimg = L("p%d_celeb.png" % i) if os.path.exists(cp) else idle
            self.big_celeb.append(scaled(cimg, fb))
            self.portrait.append(self._round_portrait(idle, 66))
            self.portrait_big.append(self._round_portrait(idle, 100))
        d = sim.BALL_R * 2 + 2
        self.ball = S(L("ball.png"), d, d)
        self.ball_fire = self._fit(L("ball_fire.png"), int(d * 1.45))
        self.ball_ice = self._fit(L("ball_ice.png"), int(d * 1.45))
        self.fx_fire = self._fit(L("fx_fire.png"), 150)
        self.fx_ice = self._fit(L("fx_ice.png"), 140)
        self.ice_block = self._fit(L("fx_ice.png"), 120)
        self.pu = {key: self._fit(L(f), 66) for key, f in
                   (("speed", "pu_speed.png"), ("jump", "pu_jump.png"), ("shield", "pu_shield.png"),
                    ("freeze", "pu_freeze.png"), ("gold", "orb_gold.png"))}
        self.pu_small = {key: tf.smoothscale(v, (30, 30)) for key, v in self.pu.items()}
        self.icon_fire = self._fit(L("ball_fire.png"), 30)
        self.seg_raw = {n: L(n + ".png") for n in ("seg_gold", "seg_orange", "seg_green", "seg_blue", "seg_empty",
                                                   "seg_gold_glow", "seg_green_glow")}
        def picon(name, fallback, size):
            if os.path.exists(res("assets", name)):
                return self._fit(L(name), size)
            return self._fit(L(fallback), size)
        pmap = {"fire": ("ball_fire.png", "ball_fire.png"), "ice": ("ball_ice.png", "ball_ice.png"),
                "magnet": ("pw_magnet.png", "orb_gold.png"), "glove": ("pw_glove.png", "pu_shield.png"),
                "bolt": ("pw_bolt.png", "pu_speed.png"), "quake": ("pw_quake.png", "pu_jump.png")}
        self.power_icon = {k: picon(a, b, 32) for k, (a, b) in pmap.items()}
        self.power_icon_small = {k: picon(a, b, 28) for k, (a, b) in pmap.items()}
        self.fx_art = {}
        for n in ("fx_glove", "fx_bolt", "fx_quake", "fx_magnet", "fx_flash", "fx_dust", "fx_spark", "fx_stars",
                  "fx_confetti", "fx_fw_gold", "fx_fw_red", "fx_fw_blue", "fx_str_red", "fx_str_gold",
                  "fx_str_blue", "fx_str_white", "fx_starburst", "fx_star", "fx_ring",
                  "wx_drop", "wx_flake", "wx_gust", "wx_leaf", "wx_splash", "wx_snowpile", "wx_puddle"):
            if os.path.exists(res("assets", n + ".png")):
                self.fx_art[n] = L(n + ".png")
        self.stat_badges = []
        if os.path.exists(res("assets", "sb_0.png")):
            self.stat_badges = [self._fit(L("sb_%d.png" % k), 28) for k in range(8)]
        self.stat_icons = [self._fit(L(n), 30) for n in ("st_speed.png", "st_jump.png", "st_shot.png")]
        # arayuz parcalari
        self.ui_raw = {n: L(n + ".png") for n in ("ui_btn", "ui_btn_hot", "ui_btn_blue", "ui_panel")}
        self.icons = {n: self._fit(L("ic_%s.png" % n), 46) for n in ("host", "join", "bot", "2p", "keys", "exit")}
        self.icons["cup"] = self.icons["bot"]
        self.ref = {}
        for n in ("idle", "whistle", "point", "card"):
            if os.path.exists(res("assets", "ref_%s.png" % n)):
                raw = L("ref_%s.png" % n)
                self.ref[n] = scaled(raw, 132 / raw.get_height())
        self.cup_art = {}
        for n, sz in (("cup_gold", 120), ("cup_silver", 90), ("cup_bronze", 90), ("medal", 80), ("podium", 260),
                      ("laurel", 120), ("ribbon", 200), ("crown", 80), ("st_lock", 30), ("st_check", 30),
                      ("st_swords", 30), ("st_skull", 30), ("st_star", 30)):
            if os.path.exists(res("assets", n + ".png")):
                self.cup_art[n] = self._fit(L(n + ".png"), sz)
        if os.path.exists(res("assets", "cup_gold.png")):
            self.cup_art["cup_gold_big"] = self._fit(L("cup_gold.png"), 200)
        if os.path.exists(res("assets", "podium.png")):
            self.cup_art["podium_big"] = self._fit(L("podium.png"), 470)
            self.icons["cup"] = self._fit(L("cup_gold.png"), 44)
        logo = L("logo.png")
        self.logo = self._fit(logo, 540)
        self.logo_small = self._fit(logo, 300)
        self.hero = []
        for i in range(6):
            src = L("p%d_celeb.png" % i) if os.path.exists(res("assets", "p%d_celeb.png" % i)) else L("p%d_idle.png" % i)
            idl = L("p%d_idle.png" % i)
            f = 300 / idl.get_height()
            self.hero.append((scaled(idl, f), scaled(src, f)))
        self._slices = {}
        self.icon_ice = self._fit(L("ball_ice.png"), 30)
        self._flip_cache = {}

    @staticmethod
    def _round_portrait(idle, d):
        """Kafayi tamamen gosteren yuvarlak portre (cap = d mantiksal piksel)."""
        w, h = idle.get_size()
        a = pygame.mask.from_surface(idle, 60)
        # kafanin alt siniri: ust %45'teki en dar satir (boyun)
        neck, best = int(h * 0.38), w
        for y in range(int(h * 0.28), int(h * 0.46)):
            cnt = sum(1 for x in range(0, w, 2) if a.get_at((x, y)))
            if cnt < best:
                best, neck = cnt, y
        side = int(max(w, neck) * 1.08)
        sq = pygame.Surface((side, side), pygame.SRCALPHA)
        sq.blit(idle, ((side - w) // 2, int(side * 0.06)), pygame.Rect(0, 0, w, min(h, side)))
        D = max(4, int(d * gfx.K))
        sq = pygame.transform.smoothscale(sq, (D, D))
        circ = pygame.Surface((D, D), pygame.SRCALPHA)
        pygame.draw.circle(circ, (255, 255, 255, 255), (D // 2, D // 2), D // 2)
        sq.blit(circ, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        return gfx.Img(sq)

    @staticmethod
    def _fit(raw, size):
        w, h = raw.get_size()
        f = size / max(w, h)
        return gfx.from_surface(raw, (w * f, h * f))

    @staticmethod
    def _ice(img):
        s = img.hi.copy()
        s.fill((150, 200, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
        s.fill((40, 70, 110, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return gfx.Img(s)

    def slice3(self, name, w, h):
        """Hap seklindeki butonu kenarlari bozulmadan genislet."""
        key = (name, int(w), int(h))
        img = self._slices.get(key)
        if img is None:
            raw = self.ui_raw[name]
            k = gfx.K
            PW, PH = max(4, int(w * k)), max(4, int(h * k))
            f = PH / raw.get_height()
            src = pygame.transform.smoothscale(raw, (max(4, int(raw.get_width() * f)), PH))
            cap = min(int(PH * 0.6), src.get_width() // 2 - 1, PW // 2)
            out = pygame.Surface((PW, PH), pygame.SRCALPHA)
            out.blit(src, (0, 0), pygame.Rect(0, 0, cap, PH))
            out.blit(src, (PW - cap, 0), pygame.Rect(src.get_width() - cap, 0, cap, PH))
            mid = src.subsurface(pygame.Rect(cap, 0, src.get_width() - 2 * cap, PH))
            out.blit(pygame.transform.smoothscale(mid, (max(1, PW - 2 * cap), PH)), (cap, 0))
            img = gfx.Img(out)
            self._slices[key] = img
        return img

    def slice9(self, name, w, h, corner=40, out_corner=30):
        """Cerceveli paneli koseleri bozulmadan istenen boyuta getir."""
        key = (name, int(w), int(h), 9)
        img = self._slices.get(key)
        if img is None:
            raw = self.ui_raw[name]
            k = gfx.K
            PW, PH = max(8, int(w * k)), max(8, int(h * k))
            c = corner
            oc = min(int(out_corner * k), PW // 2, PH // 2)
            rw, rh = raw.get_size()
            out = pygame.Surface((PW, PH), pygame.SRCALPHA)

            def part(sx, sy, sw, sh, dx, dy, dw, dh):
                if sw <= 0 or sh <= 0 or dw <= 0 or dh <= 0:
                    return
                piece = raw.subsurface(pygame.Rect(sx, sy, sw, sh))
                out.blit(pygame.transform.smoothscale(piece, (dw, dh)), (dx, dy))
            part(0, 0, c, c, 0, 0, oc, oc)
            part(rw - c, 0, c, c, PW - oc, 0, oc, oc)
            part(0, rh - c, c, c, 0, PH - oc, oc, oc)
            part(rw - c, rh - c, c, c, PW - oc, PH - oc, oc, oc)
            part(c, 0, rw - 2 * c, c, oc, 0, PW - 2 * oc, oc)
            part(c, rh - c, rw - 2 * c, c, oc, PH - oc, PW - 2 * oc, oc)
            part(0, c, c, rh - 2 * c, 0, oc, oc, PH - 2 * oc)
            part(rw - c, c, c, rh - 2 * c, PW - oc, oc, oc, PH - 2 * oc)
            part(c, c, rw - 2 * c, rh - 2 * c, oc, oc, PW - 2 * oc, PH - 2 * oc)
            img = gfx.Img(out)
            self._slices[key] = img
        return img

    def fx(self, name, h):
        """Gemini efekt gorseli (yoksa None), h mantiksal yukseklik."""
        raw = self.fx_art.get(name)
        if raw is None:
            return None
        key = ("fx", name, int(h))
        img = self._slices.get(key)
        if img is None:
            f = h / raw.get_height()
            img = gfx.from_surface(raw, (raw.get_width() * f, h))
            self._slices[key] = img
        return img

    def shadow(self, r):
        r = max(2, int(r) // 2 * 2)
        s = self._shadow.get(r)
        if s is None:
            d = fx.soft_dot(r, (0, 0, 0))
            s = tf.smoothscale(d, (d.get_width(), max(4, int(d.get_height() * 0.28))))
            self._shadow[r] = s
        return s

    def flipped(self, img):
        key = id(img)
        f = self._flip_cache.get(key)
        if f is None or f[0] is not img:
            f = (img, tf.flip(img, True, False))
            self._flip_cache[key] = f
        return f[1]


# ====================================================================== sahneler
class Scene:
    def __init__(self, app):
        self.app = app

    def handle(self, e):
        pass

    def update(self, dt):
        pass

    def draw(self, s):
        pass

    def leave(self):
        pass


ASSETS = None   # App tarafindan doldurulur


def frame(s, rect, alpha=240):
    """Altin cerceveli lacivert panel (Gemini arayuz parcasi)."""
    r = pygame.Rect(rect)
    img = ASSETS.slice9("ui_panel", r.w, r.h)
    if alpha < 255:
        img.set_alpha(alpha)
    s.blit(img, r.topleft)
    if alpha < 255:
        img.set_alpha(255)


class Sparkles:
    """Menulerde suzulen isiltilar ve konfeti."""

    def __init__(self, n=40):
        self.p = [self._new(True) for _ in range(n)]

    @staticmethod
    def _new(anywhere=False):
        return [random.uniform(0, W), random.uniform(0, H) if anywhere else -10, random.uniform(-15, 15),
                random.uniform(18, 50), random.uniform(0, 6.28), random.choice((0, 0, 1)),
                random.choice([GOLD, (255, 255, 255), (120, 200, 255), (255, 120, 160)])]

    def update(self, dt):
        for q in self.p:
            q[0] += q[2] * dt + math.sin(q[4]) * 10 * dt
            q[1] += q[3] * dt
            q[4] += dt * 2
            if q[1] > H + 10:
                q[:] = self._new()

    def draw(self, s, t):
        for x, y, _, _, ph, kind, col in self.p:
            if kind == 0:
                r = 2 + 1.5 * abs(math.sin(ph * 2))
                MatchScene._star(s, x, y, r * 1.6, col)
            else:
                w = 4
                hgt = 1 + 6 * abs(math.cos(ph))
                gd.rect(s, col, (x, y, w, hgt))


class Button:
    def __init__(self, rect, text, cb, icon=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.cb = cb
        self.icon = icon

    def draw(self, s, hot, t):
        A = ASSETS
        r = self.rect.copy()
        if hot:
            r.inflate_ip(16 + 4 * math.sin(t * 6), 8)
            fx.blit_glow(s, r.centerx, r.centery, r.w * 0.45, (60, 40, 10))
        img = A.slice3("ui_btn_hot" if hot else "ui_btn_blue", r.w, r.h)
        s.blit(img, r.topleft)
        if self.icon:
            ic = A.icons[self.icon]
            s.blit(ic, ic.get_rect(center=(r.x + r.h * 0.62, r.centery - 1)))
        draw_text(s, self.text, 28 if hot else 26, (r.centerx + (14 if self.icon else 0), r.centery - 2),
                  WHITE, outline=3)


class ButtonList:
    def __init__(self, buttons):
        self.buttons = buttons
        self.sel = 0
        self.t = 0

    def handle(self, e, app):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_DOWN, pygame.K_s, pygame.K_TAB):
                self.sel = (self.sel + 1) % len(self.buttons)
                app.sound.play("click")
            elif e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.buttons)
                app.sound.play("click")
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                app.sound.play("kick")
                self.buttons[self.sel].cb()
                return True
        elif e.type == pygame.MOUSEMOTION:
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(e.pos):
                    if self.sel != i:
                        app.sound.play("click")
                    self.sel = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(e.pos):
                    self.sel = i
                    app.sound.play("kick")
                    b.cb()
                    return True
        return False

    def draw(self, s, dt):
        self.t += dt
        for i, b in enumerate(self.buttons):
            b.draw(s, i == self.sel, self.t)


def draw_title(s, y, t, small=False):
    img = ASSETS.logo_small if small else ASSETS.logo
    bob = math.sin(t * 2.2) * (3 if small else 5)
    fx.blit_glow(s, W // 2, y + bob, img.get_width() * 0.42, (40, 30, 10))
    s.blit(img, img.get_rect(center=(W // 2, y + bob)))


def menu_backdrop(s, t, dark=True, sparkles=None):
    A = ASSETS
    s.blit(A.menu_bg_dark if dark else A.menu_bg, (0, 0))
    fx.blit_glow(s, 637, 262, 120 + 12 * math.sin(t * 2), (40, 50, 80))
    if sparkles:
        sparkles.draw(s, t)


class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        a = app
        x, bw, bh = W // 2 - 210, 420, 60
        mk = lambda i, txt, cb, ic: Button((x, 238 + i * 63, bw, 54), txt, cb, ic)
        self.list = ButtonList([
            mk(0, "MAÇ KUR", lambda: a.go(HostWaitScene(a)), "host"),
            mk(1, "MAÇA KATIL", lambda: a.go(JoinScene(a)), "join"),
            mk(2, "BİLGİSAYARA KARŞI", lambda: a.go(SelectScene(a, "bot")), "bot"),
            mk(3, "TURNUVA", lambda: a.go(SelectScene(a, "cup")), "cup"),
            mk(4, "TEK PC 2 KİŞİ", lambda: a.go(SelectScene(a, "local2")), "2p"),
            mk(5, "KONTROLLER", lambda: a.go(HelpScene(a)), "keys"),
            mk(6, "ÇIKIŞ", a.quit, "exit"),
        ])
        self.t = 0
        self.spark = Sparkles(50)
        self.heroes = random.sample(range(6), 2)
        self.cheer = [0.0, 0.0]

    def handle(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.quit()
            return
        self.list.handle(e, self.app)

    def update(self, dt):
        self.t += dt
        self.spark.update(dt)
        for i in range(2):
            self.cheer[i] -= dt
            if self.cheer[i] < -random.uniform(3, 6):
                self.cheer[i] = 1.2

    def draw(self, s):
        A = self.app.assets
        menu_backdrop(s, self.t, dark=False, sparkles=self.spark)
        for side, ci in enumerate(self.heroes):
            idle, celeb = A.hero[ci]
            img = celeb if self.cheer[side] > 0 else idle
            hop = abs(math.sin(self.t * 9)) * 14 if self.cheer[side] > 0 else math.sin(self.t * 2.5 + side) * 3
            if side == 1:
                img = A.flipped(img)
            cx = 205 if side == 0 else W - 205
            fx.blit_glow(s, cx, 650, 150, (30, 45, 80))
            sh = A.shadow(70)
            s.blit(sh, sh.get_rect(center=(cx, 668)))
            s.blit(img, img.get_rect(midbottom=(cx, 672 - hop)))
        draw_title(s, 128, self.t)
        self.list.draw(s, 1 / FPS)
        draw_text(s, "F11: tam ekran   ·   M: ses   ·   P: gizle", 17, (W // 2, H - 16), (200, 210, 230),
                  outline=2, title=False)
        draw_text(s, VERSION_TEXT, 15, (W - 12, H - 14), (170, 185, 215), anchor="midright", outline=2,
                  title=False)


class HelpScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.t = 0
        self.spark = Sparkles(25)

    def update(self, dt):
        self.t += dt
        self.spark.update(dt)

    def handle(self, e):
        if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.app.go(MenuScene(self.app))

    def draw(self, s):
        menu_backdrop(s, self.t, sparkles=self.spark)
        draw_title(s, 62, self.t, small=True)
        frame(s, (150, 125, W - 300, H - 150))
        rows = [
            ("İKİ PC / BİLGİSAYARA KARŞI", None),
            ("Hareket", "A / D  veya  ← / →"),
            ("Zıpla", "W  veya  ↑"),
            ("Şut", "BOŞLUK  (basılı tut = şarjlı şut)"),
            ("Aşırtma", "Top ayağa değerken W / ↑ basılı olsun"),
            ("Çift zıplama", "havadayken tekrar W / ↑"),
            ("Süper güç", "S  veya  ↓  (bar dolunca)"),
            ("Omuz at", "E  veya  Sağ CTRL"),
            ("Gizle", "P  (küçült + sesi kapat)"),
            ("TEK PC 2 KİŞİ", None),
            ("1. Oyuncu", "A/D, W zıpla, BOŞLUK şut, S süper, E omuz"),
            ("2. Oyuncu", "←/→, ↑ zıpla, ENTER şut, ↓ süper, Sağ CTRL omuz"),
        ]
        y = 168
        for a, b in rows:
            if b is None:
                draw_text(s, a, 24, (W // 2, y), (255, 170, 60), outline=3)
                y += 38
            else:
                draw_text(s, a, 22, (W // 2 - 170, y), WHITE, anchor="midright", outline=2, title=False)
                draw_text(s, b, 22, (W // 2 - 140, y), (180, 230, 255), anchor="midleft", outline=2, title=False)
                y += 33
        tips = ["Havada top kafanın üstündeyken ŞUT: RÖVAŞATA  ·  önündeyken: SMAÇ KAFA",
                "Top arkanda kaldıysa ŞUT: topukla kafanın üstünden öne aşırtırsın",
                "Topu güç simgelerine çarptır: HIZ, ZIPLAMA, BUZ KALKAN, DONDURMA, SÜPER",
                "Süper şut gelirken tam zamanında ŞUT tuşuna basarsan kurtarırsın!"]
        for k, tip in enumerate(tips):
            draw_text(s, tip, 18, (W // 2, y + 8 + k * 25), (255, 230, 150), outline=2, title=False)
        draw_text(s, "Geri dönmek için bir tuşa bas", 18, (W // 2, H - 66), (200, 210, 230), outline=2, title=False)


class MessageScene(Scene):
    def __init__(self, app, title, msg):
        super().__init__(app)
        self.title, self.msg = title, msg
        self.t = 0

    def update(self, dt):
        self.t += dt

    def handle(self, e):
        if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.app.go(MenuScene(self.app))

    def draw(self, s):
        menu_backdrop(s, self.t)
        draw_title(s, 110, self.t, small=True)
        frame(s, (250, 220, W - 500, 270))
        draw_text(s, self.title, 42, (W // 2, 285), (255, 120, 110), outline=4)
        y = 345
        for line in self.msg.split("\n"):
            draw_text(s, line, 22, (W // 2, y), WHITE, outline=2, title=False)
            y += 32
        draw_text(s, "Devam etmek için bir tuşa bas", 19, (W // 2, 450), (190, 200, 220), outline=2, title=False)


class OnlineMixin:
    """Baglanti kopmasini algilar, ping gonderir."""

    def online_tick(self, dt):
        self._ping = getattr(self, "_ping", 0) - dt
        if self._ping <= 0:
            self._ping = 1.0
            self.conn.send({"t": "ping"})
        if not self.conn.alive or time.time() - self.conn.last_recv > 6:
            left = any(m.get("t") == "bye" for m in self.conn.poll())
            self.conn.close()
            if left:
                self.app.go(MessageScene(self.app, "RAKİP ÇIKTI", "Diğer oyuncu oyundan ayrıldı."))
            else:
                self.app.go(MessageScene(self.app, "BAĞLANTI KOPTU",
                                         "Rakip oyundan çıktı veya ağ bağlantısı kesildi."))
            return False
        return True


class HostWaitScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.host = net.Host(socket.gethostname()[:20])
        self.ips = net.local_ips()
        self.dur_i = 1
        self.t = 0

    def leave(self):
        if self.host.conn is None:
            self.host.stop()

    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.host.stop()
                self.app.go(MenuScene(self.app))
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                self.dur_i = (self.dur_i - 1) % len(DURATIONS)
                self.app.sound.play("click")
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self.dur_i = (self.dur_i + 1) % len(DURATIONS)
                self.app.sound.play("click")

    def update(self, dt):
        self.t += dt
        if self.host.conn is not None:
            conn = self.host.conn
            conn.send({"t": "welcome", "v": VERSION, "dur": DURATIONS[self.dur_i]})
            self.app.sound.play("whistle")
            self.app.go(SelectScene(self.app, "host", conn=conn, dur=DURATIONS[self.dur_i]))

    def draw(self, s):
        menu_backdrop(s, self.t)
        draw_title(s, 92, self.t, small=True)
        frame(s, (190, 180, W - 380, 430))
        ic = self.app.assets.icons["host"]
        s.blit(ic, ic.get_rect(center=(250, 235)))
        if self.host.error:
            draw_text(s, "MAÇ KURULAMADI", 40, (W // 2, 240), (255, 110, 100), outline=4)
            draw_text(s, self.host.error, 20, (W // 2, 300), WHITE, outline=2, title=False)
            draw_text(s, "Oyun zaten açık olabilir. ESC ile geri dön.", 22, (W // 2, 350), WHITE, outline=2,
                      title=False)
            return
        dots = "." * (int(self.t * 2) % 4)
        draw_text(s, "RAKİP BEKLENİYOR" + dots, 40, (W // 2 - 0, 235), WHITE, outline=4)
        # donen top
        img = tf.rotate(self.app.assets.ball, -self.t * 300)
        s.blit(img, img.get_rect(center=(W // 2, 300)))
        draw_text(s, "Bu bilgisayarın IP adresi:", 24, (W // 2, 355), (190, 210, 235), outline=2, title=False)
        ip_txt = "   /   ".join(self.ips[:3]) if self.ips else "Ağ bağlantısı bulunamadı!"
        draw_text(s, ip_txt, 44, (W // 2, 400), GOLD, outline=4)
        draw_text(s, "Diğer PC'de  MAÇA KATIL  seçin. Maç listede otomatik görünür,", 20, (W // 2, 455),
                  WHITE, outline=2, title=False)
        draw_text(s, "görünmezse yukarıdaki IP adresini yazarak bağlanın.", 20, (W // 2, 482), WHITE, outline=2,
                  title=False)
        dur = pygame.Rect(0, 0, 380, 58)
        dur.center = (W // 2, 552)
        s.blit(self.app.assets.slice3("ui_btn", dur.w, dur.h), dur.topleft)
        draw_text(s, "MAÇ SÜRESİ:  <  %d sn  >" % DURATIONS[self.dur_i], 26, (dur.centerx, dur.centery - 2), WHITE,
                  outline=3)
        draw_text(s, "ESC: geri", 18, (W // 2, H - 30), (190, 200, 220), outline=2, title=False)


class JoinScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.finder = net.Finder()
        self.ip = ""
        self.sel = 0
        self.connector = None
        self.target = None
        self.error = ""
        self.t = 0
        self.wait_welcome = None
        self.rows = []

    def leave(self):
        self.finder.stop()

    def _connect(self, ip):
        ip = ip.strip()
        if not ip:
            return
        self.error = ""
        self.target = ip
        self.connector = net.Connector(ip)

    def handle(self, e):
        if self.connector or self.wait_welcome:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                if self.wait_welcome:
                    self.wait_welcome.close()
                self.connector = None
                self.wait_welcome = None
            return
        hosts = self.finder.hosts()
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.app.go(MenuScene(self.app))
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.ip:
                    self._connect(self.ip)
                elif hosts:
                    self._connect(hosts[min(self.sel, len(hosts) - 1)][0])
            elif e.key == pygame.K_BACKSPACE:
                self.ip = self.ip[:-1]
            elif e.key == pygame.K_DOWN:
                self.sel = min(self.sel + 1, max(0, len(hosts) - 1))
            elif e.key == pygame.K_UP:
                self.sel = max(0, self.sel - 1)
            elif e.unicode and e.unicode in "0123456789." and len(self.ip) < 15:
                self.ip += e.unicode
            elif e.unicode == "," and len(self.ip) < 15:
                self.ip += "."
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, ip in self.rows:
                if r.collidepoint(e.pos):
                    self._connect(ip)

    def update(self, dt):
        self.t += dt
        if self.connector and self.connector.done:
            c = self.connector
            self.connector = None
            if c.conn:
                c.conn.send({"t": "hello", "v": VERSION, "name": socket.gethostname()[:20]})
                self.wait_welcome = c.conn
                self.wait_t = 5.0
            else:
                self.error = "Bağlanamadı: %s" % self.target
        if self.wait_welcome:
            self.wait_t -= dt
            msgs = self.wait_welcome.poll()
            for i, m in enumerate(msgs):
                if m.get("t") == "welcome":
                    conn = self.wait_welcome
                    self.wait_welcome = None
                    self.app.sound.play("whistle")
                    self.app.go(SelectScene(self.app, "client", conn=conn, dur=m.get("dur", 90),
                                            pending=msgs[i + 1:]))
                    return
            if self.wait_t <= 0 or not self.wait_welcome.alive:
                self.wait_welcome.close()
                self.wait_welcome = None
                self.error = "Karşı taraf cevap vermedi."

    def draw(self, s):
        A = self.app.assets
        menu_backdrop(s, self.t)
        draw_title(s, 80, self.t, small=True)
        frame(s, (190, 150, W - 380, 520))
        ic = A.icons["join"]
        s.blit(ic, ic.get_rect(center=(250, 200)))
        draw_text(s, "AĞDAKİ MAÇLAR", 32, (W // 2, 198), GOLD, outline=3)
        hosts = self.finder.hosts()
        self.rows = []
        if not hosts:
            dots = "." * (int(self.t * 2) % 4)
            draw_text(s, "Aranıyor" + dots, 24, (W // 2, 250), (180, 190, 210), outline=2, title=False)
        for i, (ip, name, port) in enumerate(hosts[:4]):
            r = pygame.Rect(W // 2 - 300, 232 + i * 58, 600, 52)
            hot = i == self.sel and not self.ip
            s.blit(A.slice3("ui_btn_hot" if hot else "ui_btn_blue", r.w, r.h), r.topleft)
            draw_text(s, "%s   (%s)" % (name, ip), 24, (r.centerx, r.centery - 2), WHITE, outline=3)
            self.rows.append((r, ip))
        y = 470
        draw_text(s, "veya IP adresini yaz:", 22, (W // 2, y), (190, 210, 235), outline=2, title=False)
        box = pygame.Rect(W // 2 - 210, y + 22, 420, 58)
        gd.rect(s, (10, 14, 30), box.inflate(10, 10), 0, border_radius=16)
        gd.rect(s, (245, 245, 250), box, 0, border_radius=14)
        gd.rect(s, GOLD, box, 4, border_radius=14)
        cur = "|" if int(self.t * 2) % 2 == 0 else " "
        draw_text(s, self.ip + cur, 32, box.center, DARK, outline=0, title=False)
        if self.connector:
            draw_text(s, "Bağlanıyor: %s ..." % self.target, 24, (W // 2, 600), GOLD, outline=3)
        elif self.wait_welcome:
            draw_text(s, "Bağlandı, maç bilgisi bekleniyor...", 24, (W // 2, 600), GOLD, outline=3)
        elif self.error:
            draw_text(s, self.error, 22, (W // 2, 595), (255, 120, 110), outline=2)
            draw_text(s, "IP'yi, kabloyu ve güvenlik duvarını kontrol et.", 18, (W // 2, 622), WHITE,
                      outline=2, title=False)
        else:
            draw_text(s, "ENTER: bağlan   ↑↓: seç   ESC: geri", 20, (W // 2, 605), (190, 200, 220), outline=2,
                      title=False)


class SelectScene(Scene, OnlineMixin):
    """mode: bot | local2 | host | client"""

    def __init__(self, app, mode, conn=None, dur=90, pending=None, picks=None):
        super().__init__(app)
        self.mode = mode
        self.conn = conn
        self.dur = dur
        self.level = app.bot_level
        self.pick = list(picks) if picks else [0, 1]
        self.ready = [False, False]
        self.t = 0
        self.pending = pending or []
        self.me = 1 if mode == "client" else 0
        if mode in ("bot", "cup"):
            self.pick[1] = random.randrange(6)
        if self.conn:
            self._send_pick()
            if mode == "host":
                self.conn.send({"t": "stad", "s": app.stadium})
                self.conn.send({"t": "wx", "w": app.weather})
        self.cards = [pygame.Rect(cx - 85, 300, 170, 270) for cx in PODIUMS]
        self.anim = [[-1, 0.0], [-1, 0.0]]
        self.stad_rect = pygame.Rect(0, 0, 250, 28)
        self.stad_rect.center = (W // 2, 247)
        self.wx_rect = pygame.Rect(0, 0, 210, 26)
        self.wx_rect.center = (W // 2, 278)

    def _send_pick(self):
        if self.conn:
            self.conn.send({"t": "pick", "c": self.pick[self.me], "r": self.ready[self.me]})

    def leave(self):
        pass

    def _back(self):
        if self.conn:
            self.conn.send({"t": "bye"})
            self.conn.close()
        self.app.go(MenuScene(self.app))

    def _move(self, who, d):
        if self.ready[who]:
            return
        self.pick[who] = (self.pick[who] + d) % 6
        self.app.sound.play("click")
        if who == self.me:
            self._send_pick()

    def _toggle_ready(self, who):
        self.ready[who] = not self.ready[who]
        self.app.sound.play("kick" if self.ready[who] else "click")
        if who == self.me:
            self._send_pick()

    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            k = e.key
            if k == pygame.K_ESCAPE:
                self._back()
                return
            if self.mode == "local2":
                if k == pygame.K_a:
                    self._move(0, -1)
                elif k == pygame.K_d:
                    self._move(0, 1)
                elif k in (pygame.K_SPACE, pygame.K_w):
                    self._toggle_ready(0)
                elif k == pygame.K_LEFT:
                    self._move(1, -1)
                elif k == pygame.K_RIGHT:
                    self._move(1, 1)
                elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_UP):
                    self._toggle_ready(1)
            else:
                me = self.me
                if k in (pygame.K_a, pygame.K_LEFT):
                    self._move(me, -1)
                elif k in (pygame.K_d, pygame.K_RIGHT):
                    self._move(me, 1)
                elif k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    self._toggle_ready(me)
                elif self.mode == "bot" and k in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
                    self.pick[1] = (self.pick[1] + (1 if k in (pygame.K_DOWN, pygame.K_s) else -1)) % 6
                    self.app.sound.play("click")
            if k == pygame.K_t and self.mode != "client":
                i = (DURATIONS.index(self.dur) + 1) % len(DURATIONS) if self.dur in DURATIONS else 1
                self.dur = DURATIONS[i]
                self.app.sound.play("click")
                if self.conn:
                    self.conn.send({"t": "dur", "d": self.dur})
            if k == pygame.K_v and self.mode == "client":
                self.app.mirror = not self.app.mirror
                rec = load_record()
                rec["mirror"] = self.app.mirror
                save_record(rec)
                self.app.sound.play("click")
            if k == pygame.K_h and self.mode != "client":
                self.app.weather = (self.app.weather + 1) % len(WEATHERS)
                self.app.sound.play("click")
                if self.conn:
                    self.conn.send({"t": "wx", "w": self.app.weather})
            if k == pygame.K_y and self.mode != "client":
                self.app.stadium = (self.app.stadium + 1) % len(STADIUMS)
                self.app.sound.play("click")
                if self.conn:
                    self.conn.send({"t": "stad", "s": self.app.stadium})
            if k == pygame.K_z and self.mode == "bot":
                self.level = (self.level + 1) % 3
                self.app.bot_level = self.level
                self.app.sound.play("click")
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.wx_rect.collidepoint(e.pos):
            if self.mode != "client":
                self.app.weather = (self.app.weather + 1) % len(WEATHERS)
                self.app.sound.play("click")
                if self.conn:
                    self.conn.send({"t": "wx", "w": self.app.weather})
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.stad_rect.collidepoint(e.pos):
            if self.mode != "client":
                self.app.stadium = (self.app.stadium + 1) % len(STADIUMS)
                self.app.sound.play("click")
                if self.conn:
                    self.conn.send({"t": "stad", "s": self.app.stadium})
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self.cards):
                if r.collidepoint(e.pos):
                    who = self.me
                    if self.ready[who]:
                        return
                    if self.pick[who] == i:
                        self._toggle_ready(who)
                    else:
                        self.pick[who] = i
                        self.app.sound.play("click")
                        self._send_pick()

    def update(self, dt):
        self.t += dt
        for a in self.anim:
            a[1] = min(1.5, a[1] + dt * 1.6)
        if self.conn:
            if not self.online_tick(dt):
                return
            msgs = self.pending + self.conn.poll()
            self.pending = []
            other = 1 - self.me
            for i, m in enumerate(msgs):
                t = m.get("t")
                if t == "pick":
                    self.pick[other] = m.get("c", 0) % 6
                    self.ready[other] = bool(m.get("r"))
                elif t == "dur":
                    self.dur = m.get("d", 90)
                elif t == "bye":
                    self.conn.close()
                    self.app.go(MessageScene(self.app, "RAKİP ÇIKTI", "Diğer oyuncu oyundan ayrıldı."))
                    return
                elif t == "stad":
                    self.app.stadium = m.get("s", 0) % len(STADIUMS)
                elif t == "wx":
                    self.app.weather = m.get("w", 0) % len(WEATHERS)
                elif t == "start" and self.mode == "client":
                    self.app.stadium = m.get("st", 0) % len(STADIUMS)
                    self.app.go(MatchScene(self.app, "client", m["c"], m["dur"], conn=self.conn,
                                           pending=msgs[i + 1:]))
                    return
        if self.mode == "cup" and self.ready[0]:
            self.app.go(CupScene(self.app, new_cup(self.pick[0])))
        elif self.mode == "bot" and self.ready[0]:
            self.app.go(MatchScene(self.app, "bot", self.pick, self.dur, level=self.level))
        elif self.mode in ("local2",) and all(self.ready):
            self.app.go(MatchScene(self.app, "local2", self.pick, self.dur))
        elif self.mode == "host" and all(self.ready):
            self.conn.send({"t": "start", "c": self.pick, "dur": self.dur, "st": self.app.stadium})
            self.app.go(MatchScene(self.app, "host", self.pick, self.dur, conn=self.conn))

    def draw(self, s):
        A = self.app.assets
        s.blit(A.select_bg, (0, 0))
        labels = {"bot": ("SEN", "BİLGİSAYAR"), "local2": ("1. OYUNCU", "2. OYUNCU"),
                  "host": ("SEN", "RAKİP"), "client": ("RAKİP", "SEN"), "cup": ("SEN", "RAKİPLER")}[self.mode]
        draw_text(s, "KARAKTERİNİ SEÇ", 44, (W // 2, 42), GOLD, outline=5)
        # oyuncu bilgi panelleri
        for who in (0, 1):
            c = self.pick[who]
            px = 28 if who == 0 else W - 28 - 430
            r = pygame.Rect(px, 82, 430, 190)
            frame(s, r)
            por = A.portrait_big[c]
            if who == 1:
                por = A.flipped(por)
            pc = (r.x + 78, r.y + 98) if who == 0 else (r.right - 78, r.y + 98)
            fx.blit_glow(s, pc[0], pc[1], 70, tuple(v // 4 for v in P_COLORS[who]))
            gd.circle(s, P_COLORS[who], pc, 58)
            gd.circle(s, (12, 18, 40), pc, 52)
            s.blit(por, por.get_rect(center=(pc[0], pc[1] + 4)))
            gd.circle(s, GOLD, pc, 58, 3)
            tx = r.x + 150 if who == 0 else r.x + 26
            draw_text(s, sim.DISPLAY_NAMES[c], 34, (tx - 2, r.y + 44), WHITE, anchor="midleft", outline=4)
            if self.anim[who][0] != c:
                self.anim[who] = [c, 0.0]
            prog = self.anim[who][1]
            for j, (lab, val) in enumerate(zip(("HIZ", "ZIPLAMA", "ŞUT"), sim.STAT_BARS[c])):
                y = r.y + 84 + j * 25
                ic = A.stat_icons[j]
                s.blit(ic, ic.get_rect(center=(tx + 12, y)))
                draw_text(s, lab, 14, (tx + 30, y), (205, 218, 245), anchor="midleft", outline=2)
                for k in range(5):
                    on = k < val and prog * 10 > j * 2 + k
                    stat_seg(s, tx + 114 + k * 27, y, on, val >= 5, self.t + k * 0.15)
            pw = sim.CHARACTERS[c]["power"]
            ic = A.power_icon[pw]
            s.blit(ic, ic.get_rect(center=(tx + 12, r.y + 162)))
            draw_text(s, POWERS[pw][0], 19, (tx + 30, r.y + 161), POWERS[pw][1], anchor="midleft", outline=3)
            # durum etiketi
            if self.mode == "cup" and who == 1:
                st, tcol = "5 MAÇLIK KUPA YOLU", (150, 110, 20)
            elif self.mode == "bot" and who == 1:
                st, tcol = "ZORLUK: %s  (Z)" % LEVELS[self.level], (120, 70, 200)
            elif self.ready[who]:
                st, tcol = "HAZIR", (40, 170, 70)
            else:
                dots = "." * (int(self.t * 2) % 4)
                st, tcol = "SEÇİYOR" + dots, _shade(P_COLORS[who], 0.85)
            tag = pygame.Rect(0, 0, 270, 38)
            tag.center = (r.centerx, r.bottom + 2)
            pill(s, tag, tcol)
            lab = labels[who]
            draw_text(s, "%s  ·  %s" % (lab, st), 17, (tag.centerx, tag.centery - 1), WHITE, outline=2)
        # VS ve ayarlar
        vs_bob = math.sin(self.t * 3) * 4
        fx.blit_glow(s, W // 2, 160, 90, (70, 50, 10))
        draw_text(s, "VS", 78, (W // 2, 160 + vs_bob), GOLD, outline=6)
        draw_text(s, "Süre: %d sn%s" % (self.dur, "  (T)" if self.mode != "client" else ""), 17,
                  (W // 2, 220), (215, 225, 245), outline=2, title=False)
        stp = self.stad_rect
        pill(s, stp, (30, 120, 60) if self.app.stadium == 1 else (40, 60, 130), radius=12)
        draw_text(s, STADIUMS[self.app.stadium]["name"] + ("  (Y)" if self.mode != "client" else ""), 15,
                  (stp.centerx, stp.centery - 1), WHITE, outline=2)
        wxr = self.wx_rect
        wcol = {"clear": (200, 140, 30), "rain": (50, 90, 160), "snow": (120, 150, 190), "wind": (60, 140, 150),
                "random": (110, 70, 160)}[WEATHERS[self.app.weather][0]]
        pill(s, wxr, wcol, radius=11)
        draw_text(s, WEATHERS[self.app.weather][1] + ("  (H)" if self.mode != "client" else ""), 14,
                  (wxr.centerx, wxr.centery - 1), WHITE, outline=2)
        # podyumlar ve karakterler
        for i, cx in enumerate(PODIUMS):
            sel0, sel1 = self.pick[0] == i, self.pick[1] == i
            ready = (sel0 and self.ready[0]) or (sel1 and self.ready[1])
            if sel0 or sel1:
                col = P_COLORS[0] if sel0 else P_COLORS[1]
                fx.blit_glow(s, cx, 545, 105 + 6 * math.sin(self.t * 5), tuple(v // 3 for v in col))
                gd.ellipse(s, col, (cx - 74, 532, 148, 26), 4)
                if sel0 and sel1:
                    gd.ellipse(s, P_COLORS[1], (cx - 64, 535, 128, 20), 3)
            img = A.big_celeb[i] if ready else A.big[i]
            bob = abs(math.sin(self.t * 8 + i)) * 10 if ready else (math.sin(self.t * 3 + i) * 2 if (sel0 or sel1) else 0)
            if not (sel0 or sel1):
                img.set_alpha(185)
            s.blit(img, img.get_rect(midbottom=(cx, 548 - bob)))
            img.set_alpha(255)
            draw_text(s, sim.DISPLAY_NAMES[i], 21, (cx, 590), GOLD if (sel0 or sel1) else WHITE, outline=3)
            # secim oklari
            tags = [(0, labels[0])] if sel0 else []
            if sel1:
                tags.append((1, labels[1]))
            for n, (who, lab) in enumerate(tags):
                ty = 314 - n * 34 + math.sin(self.t * 5) * 3
                tag = pygame.Rect(0, 0, 124, 28)
                tag.center = (cx, ty)
                gd.polygon(s, (12, 14, 34), [(cx - 10, tag.bottom - 2), (cx + 10, tag.bottom - 2), (cx, tag.bottom + 11)])
                gd.polygon(s, P_COLORS[who], [(cx - 7, tag.bottom - 2), (cx + 7, tag.bottom - 2), (cx, tag.bottom + 7)])
                pill(s, tag, P_COLORS[who], radius=11)
                draw_text(s, lab, 15, (tag.centerx, tag.centery - 1), WHITE, outline=2)
        if self.mode == "local2":
            hint = "1. oyuncu: A/D seç, BOŞLUK hazır  ·  2. oyuncu: ←/→ seç, ENTER hazır  ·  Y stadyum  ·  H hava"
        elif self.mode == "bot":
            hint = "←/→ seç · ENTER hazır · ↑/↓ rakip · Z zorluk · T süre · Y stadyum · H hava"
        else:
            hint = "←/→ seç · ENTER hazır" + (" · T süre · Y stadyum · H hava" if self.mode == "host" else
                                             " · V görünüm: " + ("SEN SOLDA" if self.app.mirror else "SEN SAĞDA"))
        panel(s, (W // 2 - 420, 640, 840, 64), (8, 12, 28, 190), 18)
        draw_text(s, hint, 19, (W // 2, 660), (225, 232, 250), outline=2, title=False)
        draw_text(s, "Fare ile karaktere tıklayarak da seçebilirsin   ·   ESC: geri", 15, (W // 2, 688),
                  (170, 185, 215), outline=2, title=False)


# ====================================================================== mac
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "color", "size", "g", "kind", "rot", "vr")

    def __init__(self, x, y, vx, vy, life, color, size, g=600, kind="dot"):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.color, self.size, self.g, self.kind = color, size, g, kind
        self.rot = random.uniform(0, 360)
        self.vr = random.uniform(-400, 400)


def lerp(a, b, t):
    return a + (b - a) * t


class MatchScene(Scene, OnlineMixin):
    """mode: bot | local2 | host | client"""

    def __init__(self, app, mode, chars, dur, conn=None, level=1, pending=None, weather=None, cup=None):
        super().__init__(app)
        self.mode = mode
        self.cup = cup
        self.weather = weather or pick_weather(app.weather)
        self.recorded = False
        self.record_line = ""
        self.last_stats = None
        self.rain = [[random.uniform(0, W), random.uniform(0, H), random.uniform(0.8, 1.2)] for _ in range(160)]
        self.chars = list(chars)
        self.dur = dur
        self.conn = conn
        self.level = level
        self.world = None
        if mode != "client":
            self.world = sim.World(chars[0], chars[1], dur, weather=self.weather)
        self.bot = sim.Bot(1, level) if mode == "bot" else None
        self.acc = 0.0
        self.counts = [[0, 0, 0], [0, 0, 0]]    # [sut, super, omuz] yerel basis sayaclari
        self.used = [[0, 0, 0], [0, 0, 0]]
        self.remote = {"l": 0, "r": 0, "j": 0, "k": 0, "s": 0}
        self.snaps = []
        self.snap = None
        self.pending = pending or []
        self.parts = []
        self.banner = None      # (metin, renk, sure, maks)
        self.floaters = []
        self.shake = 0.0
        self.t = 0.0
        self.prev_phase = None
        self.paused = False
        self.quit_ask = False
        self.again = [False, False]
        self.over_t = 0.0
        self.me = 1 if mode == "client" else 0
        self.mirror = mode == "client" and app.mirror
        if self.mirror:
            self.me = 0
            self.chars = self.chars[::-1]
        self.frame = gfx.Canvas(pygame.Surface((int(W * gfx.K), int(H * gfx.K))))
        self.rings = []
        self.flashes = []
        self.ripple = None
        self.goal_flash = 0.0
        self.goal_line = None
        self.bolts = []
        self.quakes = []
        self.ref_card = 0.0
        self.ref_x = W / 2 + 60
        self.ref_pose = ["whistle", 1.2]
        self.ref_on = 1.0          # 1: sahada, 0: kenarda (reklam panolarinin onunde, kucuk)
        self.ref_target = W / 2 + 60
        self.pops = []   # [gorsel, x, y, boy, omur(, maks)]
        self.fw_queue = []
        self.last_count = None
        self.pstate = [{"og": None, "sq": 0.0, "st": 0.0, "fz": 0.0} for _ in range(2)]
        self.stad = app.stadium if 0 <= app.stadium < len(STADIUMS) else 0
        self.crowd = app.crowds[self.stad]
        self.crowd.excite = self.crowd.target = 0.15
        self.crowd.set_teams(self.chars[0], self.chars[1])
        self.crowd.fill = 0.0
        self.banners = self._make_banners()
        app.sound.ambience(True)
        if self.world:
            self.snap = self.world.snapshot()
            self._process(self.snap)

    def leave(self):
        self.app.sound.ambience(False)

    # -------------------------------------------------- girdi
    def _held(self, keymap):
        k = pygame.key.get_pressed()
        return {a: any(k[c] for c in keys) for a, keys in keymap.items()}

    def _maps(self):
        if self.mode == "local2":
            return [KEYS_P1, KEYS_P2]
        return [KEYS_SOLO, None]

    def handle(self, e):
        if e.type != pygame.KEYDOWN:
            return
        k = e.key
        over = self.snap and self.snap["ph"] == "over"
        if over:
            if self.over_t < 1.2:
                return
            if self.cup is not None:
                if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    self.app.go(CupScene(self.app, self.cup, result=self.snap["win"] == 0))
                return
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._rematch()
            elif k == pygame.K_ESCAPE:
                self._to_select()
            return
        if k == pygame.K_ESCAPE:
            if self.mode in ("bot", "local2"):
                self.paused = not self.paused
            else:
                self.quit_ask = not self.quit_ask
            return
        if (self.paused or self.quit_ask) and k == pygame.K_q:
            if self.conn:
                self.conn.send({"t": "bye"})
                self.conn.close()
            self.app.go(MenuScene(self.app))
            return
        maps = self._maps()
        if self.mode == "client":
            maps = [None, KEYS_SOLO]
        for i, m in enumerate(maps):
            if m is None:
                continue
            if k in m["k"]:
                self.counts[i][0] += 1
            if k in m["s"]:
                self.counts[i][1] += 1
            if k in m["o"]:
                self.counts[i][2] += 1

    def _rematch(self):
        if self.mode in ("bot", "local2"):
            self.app.go(MatchScene(self.app, self.mode, self.chars, self.dur, level=self.level,
                                   weather=pick_weather(self.app.weather)))
            return
        if self.again[self.me]:
            return
        self.again[self.me] = True
        self.conn.send({"t": "again"})
        self.app.sound.play("click")

    def _to_select(self):
        if self.mode in ("bot", "local2"):
            self.app.go(SelectScene(self.app, self.mode, dur=self.dur, picks=self.chars))
            return
        if self.mode == "host":
            self.conn.send({"t": "select"})
            self.app.go(SelectScene(self.app, "host", conn=self.conn, dur=self.dur, picks=self.chars))
        else:
            self.conn.send({"t": "toselect"})

    def _local_input(self, i, keymap, first):
        h = self._held(keymap)
        kp = sp = op = False
        if first:
            kp = self.counts[i][0] > self.used[i][0]
            sp = self.counts[i][1] > self.used[i][1]
            op = self.counts[i][2] > self.used[i][2]
            self.used[i] = list(self.counts[i])
        return h["l"], h["r"], h["j"], kp, sp, h["k"], op

    # -------------------------------------------------- guncelleme
    def update(self, dt):
        self.t += dt
        if self.snap and self.snap["ph"] == "over":
            self.over_t += dt
        if self.conn and not self.online_tick(dt):
            return
        if self.mode == "client":
            self._update_client(dt)
        else:
            self._update_server(dt)
        self._update_fx(dt)

    def _update_server(self, dt):
        w = self.world
        if self.conn:
            for m in self.pending + self.conn.poll():
                t = m.get("t")
                if t == "in":
                    self.remote = m
                elif t == "again":
                    self.again[1] = True
                elif t == "toselect":
                    self._to_select()
                    return
                elif t == "bye":
                    self.conn.close()
                    self.app.go(MessageScene(self.app, "RAKİP ÇIKTI", "Diğer oyuncu oyundan ayrıldı."))
                    return
            self.pending = []
            if w.phase == "over" and all(self.again):
                self.conn.send({"t": "start", "c": self.chars, "dur": self.dur, "st": self.app.stadium})
                self.app.go(MatchScene(self.app, "host", self.chars, self.dur, conn=self.conn))
                return
        if self.paused:
            return
        self.acc += min(dt, 0.1)
        first = True
        while self.acc >= STEP:
            self.acc -= STEP
            maps = self._maps()
            w.apply_input(0, *self._local_input(0, maps[0], first))
            if self.mode == "local2":
                w.apply_input(1, *self._local_input(1, maps[1], first))
            elif self.mode == "bot":
                w.apply_input(1, *self.bot.think(w, STEP), None, getattr(self.bot, "shoulder", False))
            else:
                r = self.remote
                kp = sp = op = False
                if first:
                    kp = r.get("k", 0) > self.used[1][0]
                    sp = r.get("s", 0) > self.used[1][1]
                    op = r.get("o", 0) > self.used[1][2]
                    self.used[1] = [r.get("k", 0), r.get("s", 0), r.get("o", 0)]
                w.apply_input(1, bool(r.get("l")), bool(r.get("r")), bool(r.get("j")), kp, sp,
                              bool(r.get("kh", 0)) if "kh" in r else None, op)
            w.step(STEP)
            first = False
        snap = w.snapshot()
        if self.conn:
            msg = dict(snap)
            msg["t"] = "st"
            msg["ag"] = [1 if a else 0 for a in self.again]
            self.conn.send(msg)
        self.snap = snap
        self._process(snap)

    def _update_client(self, dt):
        h = self._held(KEYS_SOLO)
        if self.mirror:
            h["l"], h["r"] = h["r"], h["l"]
        self.conn.send({"t": "in", "l": int(h["l"]), "r": int(h["r"]), "j": int(h["j"]),
                        "k": self.counts[1][0], "s": self.counts[1][1], "kh": int(h["k"]),
                        "o": self.counts[1][2]})
        now = time.time()
        msgs = self.pending + self.conn.poll()
        self.pending = []
        for i, m in enumerate(msgs):
            t = m.get("t")
            if t == "st":
                if self.mirror:
                    m = mirror_snap(m)
                self.snaps.append((now, m))
                self._process(m)
                ag = m.get("ag")
                if ag:
                    self.again = [bool(ag[0]), bool(ag[1])]
            elif t == "start":
                self.app.stadium = m.get("st", 0) % len(STADIUMS)
                self.app.go(MatchScene(self.app, "client", m["c"], m["dur"], conn=self.conn, pending=msgs[i + 1:]))
                return
            elif t == "select":
                self.app.go(SelectScene(self.app, "client", conn=self.conn, dur=self.dur, picks=self.chars,
                                        pending=msgs[i + 1:]))
                return
            elif t == "bye":
                self.conn.close()
                self.app.go(MessageScene(self.app, "RAKİP ÇIKTI", "Diğer oyuncu oyundan ayrıldı."))
                return
        # yumusak goruntu: ~2 kare geriden ara degerleme
        self.snaps = self.snaps[-12:]
        if not self.snaps:
            return
        rt = now - 0.035
        s0 = s1 = None
        for k in range(len(self.snaps) - 1, -1, -1):
            if self.snaps[k][0] <= rt:
                s0 = self.snaps[k]
                s1 = self.snaps[k + 1] if k + 1 < len(self.snaps) else None
                break
        if s0 is None:
            self.snap = self.snaps[0][1]
        elif s1 is None or s1[0] - s0[0] <= 1e-4:
            self.snap = s0[1]
        else:
            f = (rt - s0[0]) / (s1[0] - s0[0])
            a, b = s0[1], s1[1]
            snap = dict(b)
            ba, bb = a["b"], b["b"]
            if abs(ba[0] - bb[0]) < 200 and abs(ba[1] - bb[1]) < 200:
                snap["b"] = [lerp(ba[0], bb[0], f), lerp(ba[1], bb[1], f)] + bb[2:]
            ps = []
            for pa, pb in zip(a["p"], b["p"]):
                if abs(pa[0] - pb[0]) < 150:
                    ps.append([lerp(pa[0], pb[0], f), lerp(pa[1], pb[1], f)] + pb[2:])
                else:
                    ps.append(pb)
            snap["p"] = ps
            self.snap = snap

    # -------------------------------------------------- efektler
    def _say(self, txt, color, dur=1.6):
        self.banner = [txt, color, dur, dur]

    def _burst(self, x, y, n, colors, speed=300, life=0.6, size=5, g=600, kind="dot", up=0.3):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(0.3, 1) * speed
            self.parts.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v - speed * up,
                                       random.uniform(0.5, 1) * life, random.choice(colors), size, g, kind))

    def _ring(self, x, y, r, color, life=0.3):
        self.rings.append([x, y, r, color, life, life])

    def _dust(self, x, y, n=8, spread=60):
        for _ in range(n):
            self.parts.append(Particle(x + random.uniform(-spread / 3, spread / 3), y - 4,
                                       random.uniform(-spread, spread) * 1.5, random.uniform(-60, -10),
                                       random.uniform(0.35, 0.6), (205, 190, 160), random.uniform(5, 9), -20,
                                       "smoke"))

    def _process(self, snap):
        snd = self.app.sound
        crowd = self.crowd
        bx, by = snap["b"][0], snap["b"][1]
        ph = snap["ph"]
        if ph != self.prev_phase:
            if ph == "ready":
                self._say("HAZIR", WHITE, 1.0)
            elif ph == "play" and self.prev_phase == "ready":
                self._say("BAŞLA!", GOLD, 0.8)
            elif ph == "over":
                crowd.kick(1.0, snap["win"])
                self._record(snap)
            self.prev_phase = ph
        # geri sayim / son saniyeler
        if ph == "ready":
            c = int(math.ceil(snap["pt"]))
            if c != self.last_count and c <= 3:
                snd.play("beep", 0)
            self.last_count = c
        elif ph == "play" and not snap["gg"]:
            c = int(math.ceil(snap["tm"]))
            if c != self.last_count and c <= 10:
                snd.play("tick", 0)
            self.last_count = c
        for ev in snap.get("ev", []):
            name = ev.split(":")[0]
            if name in ("whistle", "end", "pens"):
                self.ref_pose = ["whistle", 1.0]
                self.ref_target = W / 2 + 60
            elif name in ("goal", "pen_goal"):
                self.ref_pose = ["point", 2.2]
                self.ref_target = W / 2 + 60
            if name in ("kick", "head", "bounce", "post", "whistle", "super_fire", "super_ice", "freeze",
                        "fire_hit", "jump", "swing", "shield", "block", "armed", "end", "golden", "pu_spawn",
                        "land"):
                snd.play(name, 0.08 if name in ("head", "bounce", "land") else 0.04)
            if name == "kick":
                self._burst(bx, by, 10, [(255, 255, 255), (255, 245, 200)], 260, 0.35, 3, 300, "spark", 0)
                self._ring(bx, by, 46, (255, 255, 255))
                self.flashes.append([bx, by, 0.12])
                if bx < 330 or bx > W - 330:
                    crowd.kick(0.45)
            elif name in ("magnet", "glove", "bolt", "quake"):
                parts_ = ev.split(":")
                who = int(parts_[1])
                pp = snap["p"][who]
                pcol = POWERS[name][1]
                self.floaters.append([POWERS[name][0] + "!", pp[0], pp[1] - 210, 1.4, pcol])
                self.crowd.kick(0.6)
                if name == "magnet":
                    snd.play("armed", 0)
                    self._ring(bx, by, 90, pcol, 0.4)
                    self._burst(bx, by, 20, [pcol, WHITE], 260, 0.5, 4, 0, "snow", 0)
                elif name == "glove":
                    snd.play("shield", 0)
                    gx = sim.GOAL_D + 20 if who == 0 else W - sim.GOAL_D - 20
                    self._burst(gx, sim.GROUND - 100, 30, [GOLD, WHITE], 320, 0.6, 5, 200, "spark", 0)
                elif name == "bolt":
                    snd.play("super_ice", 0)
                    fx_from = int(parts_[2]) if len(parts_) > 2 else pp[0]
                    self.bolts.append([fx_from, 0.35])
                    self.bolts.append([pp[0], 0.45])
                    self.pops.append(["fx_flash", pp[0], pp[1] - 70, 150, 0.35])
                    self.pops.append(["fx_flash", fx_from, sim.GROUND - 70, 110, 0.3])
                    self.flashes.append([pp[0], pp[1] - 80, 0.2])
                    self._burst(pp[0], pp[1] - 70, 26, [(255, 240, 120), WHITE, (120, 200, 255)], 420, 0.4, 3, 0,
                                "spark", 0)
                    self.shake = max(self.shake, 0.2)
                elif name == "quake":
                    snd.play("fire_hit", 0)
                    snd.play("land", 0)
                    self.quakes.append([pp[0], 0.9])
                    op = snap["p"][1 - who]
                    self.pops.append(["fx_dust", pp[0] - 90, sim.GROUND - 40, 90, 0.7])
                    self.pops.append(["fx_dust", pp[0] + 90, sim.GROUND - 40, 90, 0.7])
                    self.pops.append(["fx_spark", op[0], op[1] - 60, 80, 0.4])
                    self._ring(pp[0], sim.GROUND, 160, (230, 170, 110), 0.5)
                    for k in range(-5, 6):
                        self._dust(pp[0] + k * 45, sim.GROUND, 3, 40)
                    self._burst(pp[0], sim.GROUND - 5, 24, [(150, 110, 70), (110, 80, 50)], 380, 0.8, 6, 900,
                                "shard", 0.6)
            elif name == "bicycle":
                who = int(ev.split(":")[1])
                pp = snap["p"][who]
                snd.play("block", 0.05)
                snd.play("cheer", 0.3, 0.8)
                self.floaters.append(["RÖVAŞATA!", pp[0], pp[1] - 220, 1.5, GOLD])
                self._burst(bx, by, 24, [WHITE, GOLD, (255, 220, 140)], 420, 0.45, 3, 300, "spark", 0)
                self._ring(bx, by, 90, GOLD, 0.35)
                self.pops.append(["fx_starburst", bx, by, 120, 0.35])
                self.crowd.kick(0.8)
                self.shake = max(self.shake, 0.25)
            elif name == "shoulder":
                snd.play("swing", 0.05, 1.0)
            elif name == "bump":
                who = int(ev.split(":")[1])
                pp = snap["p"][who]
                snd.play("fire_hit", 0.1, 0.5)
                snd.play("ooh", 0.5, 0.6)
                self.pops.append(["fx_spark", pp[0], pp[1] - 90, 70, 0.3])
                self._burst(pp[0], pp[1] - 90, 12, [WHITE, GOLD], 260, 0.35, 3, 300, "spark", 0)
                self.shake = max(self.shake, 0.15)
                if random.random() < 0.35:
                    self.ref_pose = ["card", 1.8]
                    self.ref_target = max(160, min(W - 160, pp[0] + (90 if pp[0] < W / 2 else -90)))
            elif name == "pens":
                self._say("PENALTILAR!", GOLD, 2.0)
                snd.play("golden", 0)
                self.crowd.kick(0.8)
            elif name in ("pen_goal", "pen_miss"):
                who = int(ev.split(":")[1])
                if name == "pen_goal":
                    snd.play("goal", 0)
                    self._say("GOL!", GOLD, 1.4)
                    self.crowd.kick(1.0, who)
                    gx = W - 60 if who == 0 else 60
                    self.pops.append(["fx_confetti", gx, sim.GOAL_TOP + 40, 200, 1.0, 1.0])
                else:
                    snd.play("ooh", 0)
                    self._say("KAÇTI!", (255, 120, 110), 1.4)
                    self.crowd.kick(1.0, 1 - who)
            elif name == "wind":
                self.floaters.append(["RÜZGAR DÖNDÜ!", W // 2, 150, 1.5, (190, 230, 255)])
            elif name == "jump2":
                who = int(ev.split(":")[1]) if ":" in ev else 0
                pp = snap["p"][who]
                snd.play("jump", 0.02)
                self._ring(pp[0], pp[1] - 4, 40, (200, 235, 255), 0.25)
                self._burst(pp[0], pp[1], 10, [(220, 240, 255), WHITE], 160, 0.35, 3, 200, "snow", 0)
            elif name == "smash":
                snd.play("block", 0.05)
                self._burst(bx, by, 18, [WHITE, GOLD, (255, 200, 120)], 380, 0.4, 3, 300, "spark", 0)
                self._ring(bx, by, 70, GOLD, 0.3)
                self.flashes.append([bx, by, 0.15])
                self.shake = max(self.shake, 0.2)
                self.crowd.kick(0.5)
            elif name == "kick_hard":
                snd.play("fire_hit", 0.1, 0.6)
                self._ring(bx, by, 90, (255, 230, 150), 0.3)
                self._burst(bx, by, 16, [(255, 240, 180), GOLD], 420, 0.35, 3, 200, "spark", 0)
                self.shake = max(self.shake, 0.15)
            elif name == "pop":
                snd.play("head", 0.1)
                self._burst(bx, by, 10, [(255, 255, 255), (255, 240, 180)], 260, 0.35, 3, 300, "spark", 0)
                self._ring(bx, by, 50, (255, 255, 255), 0.25)
            elif name == "head":
                self._burst(bx, by, 6, [(255, 255, 255)], 180, 0.25, 3, 300, "spark", 0)
                self._ring(bx, by, 34, (255, 255, 230), 0.22)
            elif name == "bounce" and by > sim.GROUND - 40:
                self._dust(bx, sim.GROUND, 6, 40)
            elif name == "post":
                self._burst(bx, by, 14, [(255, 255, 200), GOLD], 320, 0.4, 3, 400, "spark", 0)
                self._ring(bx, by, 60, GOLD, 0.35)
                snd.play("ooh", 0.5)
                crowd.kick(0.7)
            elif name == "goal":
                snd.play("goal", 0)
                who = snap.get("scr", 0)
                parts = ev.split(":")
                kind, speed, own = "shot", 0, 0
                if len(parts) >= 5:
                    kind, speed, own = parts[2], int(parts[3]), int(parts[4])
                if own:
                    cat = "own"
                elif kind in ("super", "head", "lob", "flick", "volley", "smash", "power", "bicycle"):
                    cat = kind
                elif speed > 760:
                    cat = "hard"
                else:
                    cat = "any"
                lines = GOAL_LINES[cat]
                # iki bilgisayarda ayni yazi cikmasi icin skordan secilir
                pick = lines[(sum(snap["sc"]) * 7 + speed) % len(lines)]
                self.goal_line = [pick, 2.6, P_COLORS[who]]
                gx = W - 40 if who == 0 else 40
                for _ in range(3):
                    self._burst(gx, sim.GOAL_TOP + 40, 40,
                                [(255, 80, 80), (80, 160, 255), GOLD, (120, 255, 120), WHITE], 650, 1.8, 7, 500,
                                "confetti")
                # tribunden kagit yagmuru
                for _ in range(70):
                    self.parts.append(Particle(random.uniform(0, W), random.uniform(90, 250),
                                               random.uniform(-80, 80), random.uniform(-200, 0),
                                               random.uniform(1.8, 3.0),
                                               random.choice([(255, 80, 80), (80, 160, 255), GOLD, WHITE]),
                                               5, 260, "confetti"))
                if self.mode == "local2":
                    msg = "%d. OYUNCU" % (who + 1)
                elif who == self.me:
                    msg = "SEN ATTIN!"
                else:
                    msg = "RAKİP ATTI"
                self._say("GOOOL!", GOLD, 2.4)
                # Gemini kutlama efektleri
                gx2 = W - 70 if who == 0 else 70
                self.pops.append(["fx_confetti", gx2, sim.GOAL_TOP + 40, 230, 1.1, 1.1])
                self.pops.append(["fx_starburst", gx2, sim.GOAL_TOP + 80, 200, 0.5, 0.5])
                self.pops.append(["fx_ring", gx2, sim.GOAL_TOP + 80, 160, 0.6, 0.6])
                for k in range(7):
                    self.fw_queue.append([0.15 + k * 0.28, random.uniform(160, W - 160), random.uniform(90, 250),
                                          random.choice(["fx_fw_gold", "fx_fw_red", "fx_fw_blue"])])
                for _ in range(26):
                    self.parts.append(Particle(random.uniform(0, W), random.uniform(-80, 40), random.uniform(-40, 40),
                                               random.uniform(40, 120), random.uniform(2.2, 3.2),
                                               random.choice(["fx_str_red", "fx_str_gold", "fx_str_blue",
                                                              "fx_str_white", "fx_star"]),
                                               random.uniform(22, 34), 40, "img"))
                self.floaters.append([msg, W // 2, 292, 2.2, P_COLORS[who]])
                self.shake = 0.5
                self.ripple = [1 if who == 0 else 0, by, 0.0]
                self.goal_flash = 0.35
                crowd.kick(1.0, who)
            elif name in ("super_fire", "super_ice"):
                fire = name == "super_fire"
                c = [FIRE_C, (255, 220, 80), (255, 90, 30)] if fire else [ICE_C, WHITE, (170, 230, 255)]
                self._burst(bx, by, 30, c, 480, 0.6, 6, 200, "flame" if fire else "snow", 0)
                self._ring(bx, by, 110, FIRE_C if fire else ICE_C, 0.4)
                self.flashes.append([bx, by, 0.25])
                self.shake = max(self.shake, 0.3)
                snd.play("cheer", 0.6, 0.7)
                crowd.kick(0.65)
            elif name == "fire_hit":
                self._burst(bx, by, 40, [FIRE_C, (255, 60, 30), (255, 230, 90)], 520, 0.7, 7, 100, "flame", 0)
                self._burst(bx, by, 14, [(90, 80, 80)], 120, 1.0, 10, -60, "smoke", 0)
                self._ring(bx, by, 120, FIRE_C, 0.4)
                self.shake = 0.4
                crowd.kick(0.7)
            elif name == "freeze":
                self._burst(bx, by, 26, [ICE_C, WHITE], 380, 0.7, 5, 300, "shard")
                self._burst(bx, by, 16, [WHITE], 200, 0.8, 4, 0, "snow")
                self._ring(bx, by, 90, ICE_C, 0.35)
                crowd.kick(0.6)
            elif name == "block":
                self._burst(bx, by, 22, [WHITE, GOLD], 400, 0.5, 4, 300, "spark", 0)
                self._ring(bx, by, 80, WHITE, 0.3)
                self.floaters.append(["KURTARIŞ!", bx, by - 40, 1.2, WHITE])
                snd.play("ooh", 0.5)
                crowd.kick(0.75)
            elif name == "shield":
                self._burst(bx, by, 16, [ICE_C, WHITE], 260, 0.5, 4, 200, "shard")
                self._ring(bx, by, 60, ICE_C, 0.3)
            elif name == "golden":
                self._say("ALTIN GOL!", GOLD, 2.2)
                crowd.kick(0.8)
            elif name == "pu":
                _, kind, who = ev.split(":")
                snd.play("pu", 0)
                who = int(who)
                p = snap["p"][who]
                self.floaters.append([PU_TEXT.get(kind, kind), p[0], p[1] - 200, 1.6, P_COLORS[who]])
                self._burst(bx, by, 24, [GOLD, WHITE, (120, 255, 200)], 320, 0.6, 4, 100, "snow", 0)
                self._ring(bx, by, 70, GOLD, 0.35)
        # oyuncu durum gecisleri: inis/ziplama/buz cozulmesi
        for i, p in enumerate(snap["p"]):
            st = self.pstate[i]
            x, y, on_ground, frozen = p[0], p[1], p[8], p[5]
            if st["og"] is not None:
                if on_ground and not st["og"]:
                    st["sq"] = 0.16
                    st["st"] = 0
                    self._dust(x, y, 6, 45)
                elif not on_ground and st["og"] and y < sim.GROUND - 2:
                    st["st"] = 0.16
                    self._dust(x, sim.GROUND, 4, 30)
            if st["fz"] > 0.05 and frozen <= 0:
                h = sim.BASE_H * sim.CHARACTERS[p[9]]["scale"]
                self._burst(x, y - h / 2, 34, [ICE_C, WHITE, (180, 235, 255)], 420, 0.8, 7, 700, "shard")
                snd.play("shatter", 0.1)
            st["og"] = on_ground
            st["fz"] = frozen
        # top kaleye yakin ve hizli: tribun heyecanlanir
        b = snap["b"]
        if (b[0] < 300 and b[4] < -300) or (b[0] > W - 300 and b[4] > 300):
            crowd.target = max(crowd.target, 0.4)
        self.shake = max(self.shake, snap.get("shk", 0) or 0)

    def weather_now(self):
        return (self.snap or {}).get("wx", "clear")

    def _record(self, snap):
        if self.recorded:
            return
        self.recorded = True
        rec = load_record()
        win = snap["win"]
        if self.mode == "local2":
            r = rec.get("p1p2", [0, 0, 0])
            r[2 if win == 2 else win] += 1
            rec["p1p2"] = r
            self.record_line = "Toplam:  1. Oyuncu %d  ·  2. Oyuncu %d  ·  Berabere %d" % tuple(r)
        else:
            key = "lan" if self.mode in ("host", "client") else "bot"
            r = rec.get(key, [0, 0, 0])
            r[1 if win == 2 else (0 if win == self.me else 2)] += 1
            rec[key] = r
            self.record_line = ("Rakibe karşı toplam:  " if key == "lan" else "Bilgisayara karşı toplam:  ") + \
                "%d Galibiyet · %d Beraberlik · %d Mağlubiyet" % tuple(r)
        save_record(rec)

    def _update_fx(self, dt):
        self.crowd.update(dt)
        if self.crowd.fill < 1.0:
            self.crowd.fill = min(1.0, self.crowd.fill + dt / 2.3)
        for p in self.parts:
            p.vy += p.g * dt
            if p.kind == "confetti":
                p.vx *= (1 - 2.0 * dt)
                p.vy = min(p.vy, 140)
                p.vx += math.sin(p.rot * 0.05) * 30 * dt
            elif p.kind == "img":
                p.vx += math.sin(p.life * 3 + p.rot * 0.01) * 40 * dt
                p.rot -= p.vr * dt * 0.75
            elif p.kind in ("smoke", "snow"):
                p.vx *= (1 - 2.5 * dt)
                p.vy *= (1 - 2.5 * dt) if p.kind == "snow" else 1
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.rot += p.vr * dt
            p.life -= dt
        self.parts = [p for p in self.parts if p.life > 0 and p.y < H + 20]
        if len(self.parts) > 700:
            self.parts = self.parts[-700:]
        for r in self.rings:
            r[4] -= dt
        self.rings = [r for r in self.rings if r[4] > 0]
        for f in self.flashes:
            f[2] -= dt
        self.flashes = [f for f in self.flashes if f[2] > 0]
        if self.ripple:
            self.ripple[2] += dt
            if self.ripple[2] > 1.4:
                self.ripple = None
        self.goal_flash = max(0.0, self.goal_flash - dt)
        self.ref_card = max(0.0, self.ref_card - dt)
        if self.snap:
            ph_ = self.snap["ph"]
            active = self.ref_pose[1] > 0 or ph_ in ("ready", "pen_ready", "over")
            goal_ = 1.0 if active else 0.0
            self.ref_on += (goal_ - self.ref_on) * min(1.0, dt * 3.5)
            if ph_ in ("ready", "pen_ready"):
                tx = W / 2 + 60
            elif active:
                tx = self.ref_target
            else:
                bxr = self.snap["b"][0]
                tx = max(160, min(W - 160, bxr))
            self.ref_x += (tx - self.ref_x) * min(1.0, dt * (3.0 if active else 1.0))
        self.ref_pose[1] -= dt
        for r_ in self.rain:
            r_[1] += 900 * r_[2] * dt if self.weather_now() == "rain" else 70 * r_[2] * dt
            r_[0] += (self.snap or {}).get("wd", 0) * dt * (0.6 if self.weather_now() != "rain" else 0.3)
            if self.weather_now() == "snow":
                r_[0] += math.sin(self.t * 1.5 + r_[2] * 9) * 20 * dt
            if r_[1] > H:
                r_[1] -= H + 20
                r_[0] = random.uniform(-40, W + 40)
            r_[0] %= W + 80
        for q in self.bolts + self.quakes:
            q[1] -= dt
        self.bolts = [q for q in self.bolts if q[1] > 0]
        for q in self.fw_queue:
            q[0] -= dt
            if q[0] <= 0:
                self.pops.append([q[3], q[1], q[2], random.uniform(150, 220), 0.9, 0.9])
                self.app.sound.play("pop" if "pop" in self.app.sound.snd else "kick", 0.05, 0.5)
        self.fw_queue = [q for q in self.fw_queue if q[0] > 0]
        for q in self.pops:
            q[4] -= dt
        self.pops = [q for q in self.pops if q[4] > 0]
        self.quakes = [q for q in self.quakes if q[1] > 0]
        if self.goal_line:
            self.goal_line[1] -= dt
            if self.goal_line[1] <= 0:
                self.goal_line = None
        for st in self.pstate:
            st["sq"] = max(0.0, st["sq"] - dt)
            st["st"] = max(0.0, st["st"] - dt)
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None
        for f in self.floaters:
            f[2] -= 40 * dt
            f[3] -= dt
        self.floaters = [f for f in self.floaters if f[3] > 0]
        self.shake = max(0.0, self.shake - dt)
        if not self.snap:
            return
        b = self.snap["b"]
        rr = random.uniform
        if b[3] == 1:
            for _ in range(4):
                self.parts.append(Particle(b[0] + rr(-12, 12), b[1] + rr(-12, 12), rr(-50, 50) - b[4] * 0.08,
                                           rr(-120, -20) - b[5] * 0.08, rr(0.25, 0.45),
                                           random.choice([FIRE_C, (255, 220, 80), (255, 90, 30)]),
                                           rr(7, 12), -200, "flame"))
            if random.random() < 0.5:
                self.parts.append(Particle(b[0], b[1], rr(-30, 30), rr(-60, -20), rr(0.5, 0.8),
                                           (80, 70, 70), rr(6, 10), -40, "smoke"))
        elif b[3] == 2:
            for _ in range(3):
                self.parts.append(Particle(b[0] + rr(-14, 14), b[1] + rr(-14, 14), rr(-40, 40), rr(-40, 40),
                                           rr(0.35, 0.6), random.choice([ICE_C, WHITE, (170, 230, 255)]),
                                           rr(3, 5), 60, random.choice(("shard", "snow"))))
        elif math.hypot(b[4], b[5]) > 1000 and random.random() < 0.5:
            self.parts.append(Particle(b[0], b[1], 0, 0, 0.18, (255, 255, 255), 6, 0, "smoke"))
        for i, p in enumerate(self.snap["p"]):
            x, y, vx = p[0], p[1], p[2]
            h = sim.BASE_H * sim.CHARACTERS[p[9]]["scale"]
            if p[10] > 0 and abs(vx) > 100 and p[8]:
                self.parts.append(Particle(x - (14 if vx > 0 else -14), y - rr(10, h * 0.8), -vx * 0.25, 0, 0.22,
                                           (255, 230, 120), 3, 0, "spark"))
            elif abs(vx) > 250 and p[8] and random.random() < 0.12:
                self._dust(x - (10 if vx > 0 else -10), y, 1, 25)
            if p[7] > 0:
                if sim.CHARACTERS[p[9]]["power"] == "fire":
                    for _ in range(2):
                        self.parts.append(Particle(x + rr(-34, 34), y - rr(0, h * 0.9), rr(-15, 15), rr(-90, -40),
                                                   rr(0.3, 0.55), random.choice([FIRE_C, (255, 200, 70)]),
                                                   rr(6, 10), -120, "flame"))
                else:
                    a = self.t * 5 + rr(0, 6.28)
                    self.parts.append(Particle(x + math.cos(a) * 42, y - h * 0.5 + math.sin(a) * 60,
                                               rr(-20, 20), rr(-30, 10), rr(0.4, 0.7),
                                               random.choice([ICE_C, WHITE]), rr(3, 5), 0, "snow"))
            if p[5] > 0 and random.random() < 0.15:
                self.parts.append(Particle(x + rr(-35, 35), y - rr(10, h), 0, rr(-15, 15), 0.6, WHITE, 3, 0,
                                           "snow"))

    # -------------------------------------------------- cizim
    def draw(self, screen):
        A = self.app.assets
        s = self.frame
        wxn = self.weather_now()
        bgk = (self.stad, wxn)
        s.blit(A.stadium_wx.get(bgk, A.stadiums[self.stad]), (0, 0))
        self.crowd.draw(s)
        self._draw_banners(s)
        sd = STADIUMS[self.stad]
        if sd["boards"]:
            self._draw_boards(s, sd["boards"], self.snap)
        for i, (lx, ly) in enumerate(sd["lamps"]):
            fx.blit_glow(s, lx, ly, 95 + 8 * math.sin(self.t * 2 + i), (110, 110, 120))
        snap = self.snap
        if snap is None:
            screen.blit(s, (0, 0))
            draw_text(screen, "Bağlanıyor...", 40, (W // 2, H // 2), WHITE)
            return
        self._draw_goal_back(s, snap)
        b = snap["b"]
        for x, y, wdt in [(p[0], p[1], 70) for p in snap["p"]] + [(b[0], b[1], 44)]:
            hgt = max(0.0, sim.GROUND - y)
            k = max(0.25, 1 - hgt / 420)
            sh = A.shadow(int(wdt * k / 2) + 2)
            sh.set_alpha(int(150 * k))
            s.blit(sh, sh.get_rect(center=(x, sim.GROUND + 3)))
            sh.set_alpha(255)
        if snap.get("pu"):
            kind, px, py, life = snap["pu"]
            img = A.pu.get(kind)
            if img and (life > 2 or int(self.t * 8) % 2 == 0):
                bob = math.sin(self.t * 3) * 8
                fx.blit_glow(s, px, py + bob, 62 + 6 * math.sin(self.t * 6), (110, 100, 50))
                sp = tf.rotozoom(img, math.sin(self.t * 2.5) * 10, 1 + 0.05 * math.sin(self.t * 6))
                s.blit(sp, sp.get_rect(center=(px, py + bob)))
                for k in range(3):
                    a = self.t * 2 + k * 2.09
                    sx, sy = px + math.cos(a) * 44, py + bob + math.sin(a) * 44
                    self._star(s, sx, sy, 4 + 2 * math.sin(self.t * 8 + k), (255, 250, 210))
        for qx, life in self.quakes:
            img = A.fx("fx_quake", 90)
            if img is not None:
                img.set_alpha(int(255 * min(1, life * 2.5)))
                s.blit(img, img.get_rect(midbottom=(qx, sim.GROUND + 30)))
                img.set_alpha(255)
            else:
                for k in range(-3, 4):
                    gd.line(s, (60, 40, 25), (qx + k * 30, sim.GROUND), (qx + k * 38, sim.GROUND - 20 * life), 4)
        # arkadaki parcaciklar (duman)
        for p in self.parts:
            if p.kind == "smoke":
                self._draw_particle(s, p)
        self._draw_ref(s, snap)
        for i, p in enumerate(snap["p"]):
            self._draw_player(s, i, p, snap)
        mg = snap.get("mg", [0, 0])
        if max(mg) > 0:
            fx.blit_glow(s, b[0], b[1], 60 + 6 * math.sin(self.t * 14), (70, 30, 110))
            img = A.fx("fx_magnet", 92)
            if img is not None:
                rimg = tf.rotate(img, (self.t * 240) % 360)
                s.blit(rimg, rimg.get_rect(center=(b[0], b[1])))
            else:
                gd.circle(s, (200, 130, 255), (b[0], b[1]), 36 + 4 * math.sin(self.t * 12), 3)
        self._draw_ball(s, b)
        self._draw_goal_front(s, snap)
        for q in self.pops:
            name_, px_, py_, sz, life = q[:5]
            img = A.fx(name_, sz)
            if img is not None:
                if len(q) > 5:
                    k_ = 0.35 + 0.85 * min(1.0, (1 - life / q[5]) * 2.2)
                else:
                    k_ = 1 + (0.6 - min(0.6, life)) * 0.8
                im2 = tf.rotozoom(img, 0, k_) if name_ != "fx_dust" else img
                im2.set_alpha(int(255 * min(1, life * 3)))
                s.blit(im2, im2.get_rect(center=(px_, py_)))
                im2.set_alpha(255)
        for bx_, life in self.bolts:
            img = A.fx("fx_bolt", 300)
            if img is not None:
                img.set_alpha(int(255 * min(1, life * 4)))
                s.blit(img, img.get_rect(midbottom=(bx_, sim.GROUND)))
                img.set_alpha(255)
            else:
                pts = [(bx_ + (14 if k % 2 else -14), 40 + k * (sim.GROUND - 40) / 8) for k in range(9)]
                gd.lines(s, (255, 250, 200), False, pts, 6)
            fx.blit_glow(s, bx_, sim.GROUND - 120, 110 * life + 40, (90, 90, 40))
        for p in self.parts:
            if p.kind != "smoke":
                self._draw_particle(s, p)
        for x, y, r, col, life, mx in self.rings:
            k = 1 - life / mx
            rad = int(10 + r * k)
            gd.circle(s, col, (int(x), int(y)), rad, max(1, int(5 * (1 - k))))
        for x, y, life in self.flashes:
            fx.blit_glow(s, x, y, 40 + life * 200, (255, 245, 220))
        if self.goal_flash > 0:
            v = int(110 * self.goal_flash / 0.35)
            s.add_full((v, v, int(v * 0.8)))
        self._draw_weather(s, snap)
        self._draw_hud(s, snap)
        ox = oy = 0
        if self.shake > 0:
            m = 10 * min(1, self.shake * 2.5)
            ox, oy = random.uniform(-m, m), random.uniform(-m, m)
        screen.fill((0, 0, 0))
        screen.blit(s, (ox, oy))
        self._draw_overlays(screen, snap)

    def _make_banners(self):
        """Gemini beyaz pankart/bayraklari forma rengine boyar, kafa + isim basar."""
        A = self.app.assets
        out = []
        spots = self.crowd.banner_spots
        if not A.banner_raw:
            return out
        for side in (0, 1):
            c = self.chars[side]
            col = fx.TEAM["k%d" % c][0]
            my = [sp for sp in spots if (sp[0] < W / 2) == (side == 0)]
            for n, (x, y) in enumerate(my):
                kind = "bn_hold" if n % 2 == 0 else "bn_flag"
                frames = [self._paint_banner(raw, col, c, kind) for raw in A.banner_raw[kind]]
                out.append([frames, x, y, random.uniform(0, 6.28), side, kind])
        return out

    def _paint_banner(self, raw, col, char, kind):
        A = self.app.assets
        k = gfx.K
        lh = 44 if kind == "bn_hold" else 52     # mantiksal yukseklik (taraftar boyuna uygun)
        f = lh * k / raw.get_height()
        img = pygame.transform.smoothscale(raw, (max(1, int(raw.get_width() * f)), max(1, int(lh * k))))
        w, h = img.get_size()
        # beyaz bezi forma rengine boya (golgeler korunur)
        px = pygame.PixelArray(img)
        cloth = []
        for xx in range(w):
            for yy in range(h):
                r, g, b, a = img.unmap_rgb(px[xx, yy])
                if a > 80 and min(r, g, b) > 150 and max(r, g, b) - min(r, g, b) < 40:
                    lum = (r + g + b) / 765.0
                    px[xx, yy] = (int(col[0] * lum), int(col[1] * lum), int(col[2] * lum), a)
                    cloth.append((xx, yy))
        del px
        if cloth:
            xs = [p[0] for p in cloth]
            ys = [p[1] for p in cloth]
            x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
            ch = y1 - y0
            por = A.portrait[char].hi
            d = max(4, int(ch * 0.62))
            pp = pygame.transform.smoothscale(por, (d, d))
            light = sum(col) > 560
            if kind == "bn_hold":
                cx = x0 + int((x1 - x0) * 0.24)
                img.blit(pp, (cx - d // 2, y0 + (ch - d) // 2))
                f_ = get_font(max(6, int(ch * 0.30)), True)
                t = f_.render(sim.DISPLAY_NAMES[char], True, (25, 30, 50) if light else (255, 255, 255))
                if t.get_width() > (x1 - x0) * 0.52:
                    t = pygame.transform.smoothscale(t, (int((x1 - x0) * 0.52),
                                                         int(t.get_height() * (x1 - x0) * 0.52 / t.get_width())))
                img.blit(t, (x0 + int((x1 - x0) * 0.68) - t.get_width() // 2, y0 + (ch - t.get_height()) // 2))
            else:
                img.blit(pp, (x0 + (x1 - x0) // 2 - d // 2, y0 + (ch - d) // 2))
        return gfx.Img(img)

    def _draw_ref(self, s, snap):
        """Hakem: olay aninda sahaya gelir, diger zamanlarda kenarda (panolarin onunde) kucuk durur."""
        A = self.app.assets
        if not A.ref:
            return
        f = max(0.0, min(1.0, self.ref_on))
        pose = self.ref_pose[0] if self.ref_pose[1] > 0 else "idle"
        img = A.ref.get(pose, A.ref.get("idle"))
        bxr = snap["b"][0]
        if bxr < self.ref_x:
            img = A.flipped(img)
        sc = 0.5 + 0.5 * f
        y = 568 + (sim.GROUND - 568) * f
        if sc < 0.99:
            img = tf.rotozoom(img, 0, sc)
        sh = A.shadow(int(30 * sc))
        s.blit(sh, sh.get_rect(center=(self.ref_x, y + 2)))
        s.blit(img, img.get_rect(midbottom=(self.ref_x, y)))

    def _draw_weather(self, s, snap):
        wx = snap.get("wx", "clear")
        if wx == "clear":
            return
        A = self.app.assets
        themed = (self.stad, wx) in A.stadium_wx
        if wx == "rain":
            if not themed:
                s.overlay((10, 20, 40, 70))
            wd = snap.get("wd", 0) * 0.02
            for x, y, k in self.rain[:55]:
                gd.line(s, (150, 175, 210), (x, y - 10 * k), (x - 2 - wd, y), 1)
                if y > sim.GROUND - 16 and int(x * 7) % 4 == 0:
                    sp = A.fx("wx_splash", 9)
                    if sp is not None:
                        s.blit(sp, sp.get_rect(midbottom=(x, sim.GROUND + 3)))
        elif wx == "snow":
            if not themed:
                s.overlay((200, 215, 240, 26))
            flake = A.fx("wx_flake", 7)
            for n, (x, y, k) in enumerate(self.rain[:60]):
                if flake is not None and n % 4 == 0:
                    s.blit(flake, (x, y))
                else:
                    gd.circle(s, (235, 240, 250), (x, y), 1 + 0.6 * k)
            gd.rect(s, (235, 242, 252), (0, sim.GROUND + 2, W, 6))
            pile = A.fx("wx_snowpile", 26)
            if pile is not None:
                for px_ in (150, 420, 860, 1130):
                    s.blit(pile, pile.get_rect(midbottom=(px_, sim.GROUND + 8)))
        elif wx == "wind":
            wd = snap.get("wd", 0)
            d = 1 if wd >= 0 else -1
            gust = A.fx("wx_gust", 40)
            leaf = A.fx("wx_leaf", 18)
            for n, (x, y, k) in enumerate(self.rain[:28]):
                yy = 140 + (y % 420)
                xx = (x + self.t * abs(wd) * 1.6 * k) % (W + 80) - 40
                if d < 0:
                    xx = W - xx
                if n % 4 == 0 and gust is not None:
                    g_ = A.flipped(gust) if d < 0 else gust
                    g_.set_alpha(110)
                    s.blit(g_, (xx, yy))
                    g_.set_alpha(255)
                elif n % 4 == 1 and leaf is not None:
                    r_ = tf.rotate(leaf, (self.t * 200 * k) % 360)
                    s.blit(r_, (xx, yy + math.sin(self.t * 3 + k * 5) * 18))
                elif n % 4 >= 2:
                    gd.line(s, (230, 240, 255), (xx, yy), (xx + d * 50 * k, yy), 2)
            pnl = pygame.Rect(0, 0, 150, 30)
            pnl.midtop = (W // 2, 98)
            pill(s, pnl, (40, 70, 120), radius=12)
            draw_text(s, ("RÜZGAR →" if d > 0 else "← RÜZGAR"), 15, (pnl.centerx, pnl.centery - 1), WHITE, outline=2)

    def _draw_banners(self, s):
        ex = self.crowd.excite
        sad = self.crowd.boost_side if self.crowd.boost_t > 0 else -1
        if self.crowd.fill < 1.0:
            return
        for frames, x, y, ph, side, kind in self.banners:
            happy = sad < 0 or sad == side
            rate = (2.5 + ex * 6) if happy else 1.2
            img = frames[int(self.t * rate + ph) % 2]
            lift = (ex * 10 * abs(math.sin(self.t * 7 + ph))) if happy else 0
            s.blit(img, img.get_rect(midbottom=(x, y + 20 - lift)))

    def _draw_boards(self, s, spec, snap):
        """Saha kenarindaki LED reklam panolari: kayan yazilar, golde GOOOL."""
        y, h = spec
        k = gfx.K
        A = self.app.assets
        goal = snap is not None and snap.get("ph") == "goal"
        key = ("goal" if goal else "ads", h)
        if getattr(A, "_board_key", None) != key:
            parts = ([("GOOOL!", GOLD)] * 6) if goal else ADS
            imgs = [text_surf(t, int(h * 0.62), c, 0, title=True) for t, c in parts]
            gap = int(70 * k)
            tw = sum(i.hi.get_width() for i in imgs) + gap * len(imgs)
            strip = pygame.Surface((tw, int(h * k)), pygame.SRCALPHA)
            x = 0
            for im in imgs:
                strip.blit(im.hi, (x, (strip.get_height() - im.hi.get_height()) // 2))
                x += im.hi.get_width()
                pygame.draw.circle(strip, (90, 200, 255), (x + gap // 2, strip.get_height() // 2), max(2, int(3 * k)))
                x += gap
            A._board_strip = strip
            A._board_key = key
            led = pygame.Surface((int(W * k), int(h * k)), pygame.SRCALPHA)
            for yy in range(0, led.get_height(), max(2, int(3 * k))):
                pygame.draw.line(led, (0, 0, 0, 70), (0, yy), (led.get_width(), yy))
            A._board_led = led
        surf = s.surf
        top = int(y * k)
        pygame.draw.rect(surf, (10, 12, 22), (0, top - int(2 * k), int(W * k), int((h + 4) * k)))
        pygame.draw.rect(surf, (22, 26, 44), (0, top, int(W * k), int(h * k)))
        strip = A._board_strip
        sw = strip.get_width()
        speed = 260 if goal else 70
        off = int((self.t * speed * k) % sw)
        x = -off
        flash = goal and int(self.t * 6) % 2 == 0
        while x < W * k:
            surf.blit(strip, (x, top))
            x += sw
        if flash:
            surf.fill((40, 32, 0), (0, top, int(W * k), int(h * k)), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(A._board_led, (0, top))
        pygame.draw.line(surf, (120, 200, 255), (0, top), (int(W * k), top), max(1, int(k)))

    @staticmethod
    def _star(s, x, y, r, col):
        pts = []
        for k in range(8):
            rad = r if k % 2 == 0 else r * 0.35
            a = k * math.pi / 4
            pts.append((x + math.cos(a) * rad, y + math.sin(a) * rad))
        gd.polygon(s, col, pts)

    def _draw_particle(self, s, p):
        a = max(0.0, min(1.0, p.life / p.max))
        k = p.kind
        if k == "img":
            img = self.app.assets.fx(p.color, p.size)
            if img is not None:
                r_ = tf.rotate(img, p.rot % 360)
                if a < 0.3:
                    r_.set_alpha(int(255 * a / 0.3))
                s.blit(r_, r_.get_rect(center=(p.x, p.y)))
            return
        if k == "confetti":
            r = pygame.Rect(0, 0, p.size, int(p.size * 1.6 * abs(math.cos(math.radians(p.rot)))) + 1)
            r.center = (p.x, p.y)
            gd.rect(s, p.color, r)
        elif k == "shard":
            sz = p.size * (0.5 + 0.5 * a)
            pts = [(p.x + math.cos(math.radians(p.rot + j * 120)) * sz * (1.7 if j == 0 else 0.7),
                    p.y + math.sin(math.radians(p.rot + j * 120)) * sz * (1.7 if j == 0 else 0.7)) for j in range(3)]
            gd.polygon(s, p.color, pts)
            gd.polygon(s, (255, 255, 255), pts, 1)
        elif k == "flame":
            t = 1 - a
            if t < 0.3:
                col = (255, 230, 140)
            elif t < 0.6:
                col = (255, 150, 40)
            else:
                col = (210, 60, 20)
            fx.blit_glow(s, p.x, p.y, p.size * (1.6 - t * 0.9), col)
        elif k == "smoke":
            img = fx.soft_dot(int(p.size * (1 + (1 - a) * 1.5)), p.color)
            img.set_alpha(int(140 * a))
            s.blit(img, img.get_rect(center=(p.x, p.y)))
            img.set_alpha(255)
        elif k == "spark":
            ex, ey = p.x - p.vx * 0.035, p.y - p.vy * 0.035
            gd.line(s, p.color, (p.x, p.y), (ex, ey), 2)
        elif k == "snow":
            self._star(s, p.x, p.y, p.size * (0.4 + 0.6 * a) * (1 + 0.3 * math.sin(p.rot * 0.1)), p.color)
        else:
            rad = max(1, int(p.size * (0.4 + 0.6 * a)))
            gd.circle(s, p.color, (int(p.x), int(p.y)), rad)

    def _draw_goal_back(self, s, snap):
        GT, GR = sim.GOAL_TOP, sim.GROUND
        A = self.app.assets
        rp = self.ripple
        gx, gy = A.goal_pos
        for side in (0, 1):
            off = 0.0
            if rp and rp[0] == side:
                off = 5 * math.exp(-rp[2] * 4) * math.sin(rp[2] * 40) * (-1 if side == 0 else 1)
            if side == 0:
                img = A.goal_back
                x = gx + off
            else:
                img = A.goal_back_r
                x = W - gx - img.get_width() + off
            s.blit(img, (x, gy))
        gl = snap.get("gl", [0, 0])
        for i in range(2):
            if gl[i] > 0:
                continue
            if snap["sh"][i] > 0:
                x = sim.GOAL_D + 2 if i == 0 else W - sim.GOAL_D - 2
                wall = pygame.Surface((26, GR - GT), pygame.SRCALPHA)
                al = 140 if snap["sh"][i] > 1.5 or int(self.t * 10) % 2 else 60
                wall.fill((140, 220, 255, al))
                gd.line(wall, (255, 255, 255, 200), (6, 10), (6, GR - GT - 10), 2)
                s.blit(wall, wall.get_rect(midtop=(x, GT)))
                fx.blit_glow(s, x, GT + (GR - GT) / 2, 90, (30, 70, 100))
                ice = self.app.assets.ice_block
                for yy in range(GT + 30, GR, 70):
                    s.blit(ice, ice.get_rect(center=(x, yy)))

    def _draw_goal_front(self, s, snap):
        A = self.app.assets
        GT, GR = sim.GOAL_TOP, sim.GROUND
        gl = snap.get("gl", [0, 0])
        for i in range(2):
            if gl[i] <= 0 or not (gl[i] > 1.2 or int(self.t * 10) % 2):
                continue
            x = sim.GOAL_D + 26 if i == 0 else W - sim.GOAL_D - 26
            img = A.fx("fx_glove", (GR - GT) * 0.92)
            bob = math.sin(self.t * 4) * 4
            fx.blit_glow(s, x, GT + (GR - GT) * 0.5, 120, (60, 50, 10))
            if img is not None:
                if i == 1:
                    img = A.flipped(img)
                s.blit(img, img.get_rect(midbottom=(x, GR + 4 + bob)))
            else:
                gd.ellipse(s, (255, 214, 60), (x - 30, GT + 10, 60, GR - GT - 10))
        gy = A.goal_pos[1]
        s.blit(A.goal_front, (A.goal_post_x, gy))
        s.blit(A.goal_front_r, (W - A.goal_post_x - A.goal_front_r.get_width(), gy))

    def _player_img(self, char, p, snap, i):
        """Duruma gore uygun pozu sec."""
        A = self.app.assets
        x, y, vx, face, kick_t, frozen, meter, armed, on_ground, _, speed_t, jump_t, stun, run_t = p[:14]
        poses = A.poses[char]
        ice = frozen > 0
        celebrate = (snap["ph"] == "goal" and snap.get("scr") == i) or (snap["ph"] == "over" and snap["win"] == i)
        bike = p[16] if len(p) > 16 else 0
        shoulder = p[17] if len(p) > 17 else 0
        if bike > 0:
            if "bike" in poses:
                return poses["bike"], "bike", "bike"
            return tf.rotate(A.kick[char], 150), "bike", "kick"
        if shoulder > 0:
            if "shoulder" in poses:
                return poses["shoulder"], "shoulder", "shoulder"
            return tf.rotate(poses.get("run1", A.idle[char]), -16), "shoulder", "run1"
        if kick_t > 0.04:
            return (A.kick_ice if ice else A.kick)[char], "kick", "kick"
        if celebrate and "celeb" in poses:
            return poses["celeb"], "celeb", "celeb"
        if not on_ground and "jump" in poses:
            return (poses["jump_ice"] if ice else poses["jump"]), "jump", "jump"
        if on_ground and abs(vx) > 40 and not ice and "run1" in poses:
            fr = "run1" if int(run_t * 9) % 2 == 0 else "run2"
            return poses[fr], "run", fr
        return (A.idle_ice if ice else A.idle)[char], "idle", "idle"

    def _draw_player(self, s, i, p, snap):
        A = self.app.assets
        x, y, vx, face, kick_t, frozen, meter, armed, on_ground, char, speed_t, jump_t, stun, run_t = p[:14]
        img, pose, akey = self._player_img(char, p, snap, i)
        flip = face < 0
        if flip:
            img = A.flipped(img)
        h = sim.BASE_H * sim.CHARACTERS[char]["scale"]
        tilt = 0
        bob = 0
        if pose in ("idle", "run") and on_ground and abs(vx) > 40 and frozen <= 0:
            bob = abs(math.sin(run_t * 14)) * (5 if pose == "idle" else 3)
            tilt = math.sin(run_t * 14) * (4 if pose == "idle" else 2) + (3 if pose == "run" else 0) * (1 if vx > 0 else -1)
        if pose == "idle" and frozen <= 0 and on_ground and abs(vx) <= 40:
            # nefes alma
            bob = math.sin(self.t * 3 + i) * 1.2
        if pose == "celeb" or (snap["ph"] == "goal" and snap.get("scr") == i and on_ground):
            bob = abs(math.sin(self.t * 9)) * 16
        if stun > 0:
            tilt = math.sin(self.t * 30) * 12
        if not on_ground and pose != "kick":
            tilt = -6 * face if vx * face > 0 else 0
        st = self.pstate[i]
        sx = sy = 1.0
        if len(p) > 18 and p[18] and pose == "idle":
            sy, sx = 0.74, 1.12   # penaltida comelen kaleci
        if st["sq"] > 0:
            k = st["sq"] / 0.16
            sx, sy = 1 + 0.16 * k, 1 - 0.14 * k
        elif st["st"] > 0:
            k = st["st"] / 0.16
            sx, sy = 1 - 0.08 * k, 1 + 0.1 * k
        if armed > 0:
            pw = sim.CHARACTERS[char]["power"]
            c = _shade(POWERS[pw][1], 0.45)
            fx.blit_glow(s, x, y - h * 0.5, 95 + 8 * math.sin(self.t * 12), c)
        if sx != 1.0 or sy != 1.0:
            img = tf.smoothscale(img, (max(1, int(img.get_width() * sx)),
                                                     max(1, int(img.get_height() * sy))))
        if tilt:
            img = tf.rotate(img, -tilt * (1 if not flip else -1))
        rect = img.get_rect()
        # kafa hizasi: her pozda kafa oyuncunun x konumunda dursun
        ax = A.anchors.get("p%d_%s" % (char, akey), 0.40 if pose == "kick" else 0.5)
        rect.bottom = int(y - bob)
        if flip:
            rect.left = int(x - rect.w * (1 - ax))
        else:
            rect.left = int(x - rect.w * ax)
        if frozen > 0:
            # buz kalibi
            blk = pygame.Rect(0, 0, 96, int(h + 26))
            blk.midbottom = (int(x), int(y + 4))
            ice = pygame.Surface(blk.size, pygame.SRCALPHA)
            gd.rect(ice, (150, 220, 255, 70), ice.get_rect(), 0, border_radius=14)
            s.blit(img, rect)
            s.blit(ice, blk)
            gd.rect(s, (220, 245, 255), blk, 3, border_radius=14)
            gd.line(s, (255, 255, 255), (blk.x + 14, blk.y + 18), (blk.x + 30, blk.y + 60), 3)
            gd.line(s, (255, 255, 255), (blk.x + 22, blk.y + 14), (blk.x + 34, blk.y + 38), 2)
            gd.line(s, (200, 240, 255), (blk.right - 20, blk.bottom - 50), (blk.right - 10, blk.bottom - 20), 2)
            ice2 = A.fx_ice
            s.blit(ice2, ice2.get_rect(center=(x, y - 20)))
            draw_text(s, "%.1f" % frozen, 20, (x, blk.y - 14), ICE_C, outline=3)
        else:
            s.blit(img, rect)
        if stun > 0:
            st_img = A.fx("fx_stars", 46)
            if st_img is not None:
                sq = tf.smoothscale(st_img, (st_img.get_width(), max(4, st_img.get_height() * 0.45)))
                s.blit(sq, sq.get_rect(center=(x + math.sin(self.t * 6) * 4, y - h - 6)))
            else:
                for k in range(3):
                    a = self.t * 8 + k * 2.1
                    self._star(s, x + math.cos(a) * 28, y - h - 8 + math.sin(a) * 8, 7, GOLD)
        if jump_t > 0:
            gd.ellipse(s, (120, 255, 160), (x - 32, y - 7, 64, 14), 3)
        label = None
        if self.mode == "local2":
            label = "P%d" % (i + 1)
        elif i == self.me:
            label = "SEN"
        charge = p[14] if len(p) > 14 else -1
        if charge >= 0:
            cb = pygame.Rect(0, 0, 70, 12)
            cb.center = (x, y - h - 58 - bob)
            col = (120, 230, 120) if charge < 0.5 else ((255, 200, 60) if charge < 0.95 else (255, 90, 50))
            draw_meter(s, cb, charge, col, glow=charge >= 0.95)
            if len(p) > 15 and p[15] and p[8]:
                ax_, ay_ = cb.right + 14, cb.centery
                gd.polygon(s, (12, 14, 34), [(ax_ - 10, ay_ + 4), (ax_ + 10, ay_ + 4), (ax_, ay_ - 12)])
                gd.polygon(s, (120, 230, 255), [(ax_ - 7, ay_ + 2), (ax_ + 7, ay_ + 2), (ax_, ay_ - 8)])
                draw_text(s, "AŞIRTMA", 12, (cb.centerx, cb.y - 10), (150, 235, 255), outline=2)
        if label:
            ty = y - h - 30 + math.sin(self.t * 5) * 3 - bob
            tg = pygame.Rect(0, 0, 52 if len(label) <= 3 else 64, 22)
            tg.center = (x, ty)
            gd.polygon(s, (12, 14, 34), [(x - 9, tg.bottom - 2), (x + 9, tg.bottom - 2), (x, tg.bottom + 9)])
            gd.polygon(s, P_COLORS[i], [(x - 6, tg.bottom - 2), (x + 6, tg.bottom - 2), (x, tg.bottom + 6)])
            pill(s, tg, P_COLORS[i], radius=9)
            draw_text(s, label, 13, (x, ty - 1), WHITE, outline=2, title=False)

    def _draw_ball(self, s, b):
        A = self.app.assets
        x, y, ang, mode, vx, vy = b
        sp = math.hypot(vx, vy) or 1
        if mode in (1, 2):
            dx, dy = -vx / sp, -vy / sp
            fx.blit_glow(s, x, y, 80, (150, 70, 10) if mode == 1 else (40, 110, 160))
            trail = A.fx_fire if mode == 1 else A.fx_ice
            a = math.degrees(math.atan2(-dy, dx))
            tr = tf.rotate(trail, a)
            L = trail.get_width() * 0.38
            s.blit(tr, tr.get_rect(center=(x + dx * L, y + dy * L)))
            img = A.ball_fire if mode == 1 else A.ball_ice
        else:
            img = A.ball
        img = tf.rotate(img, -math.degrees(ang) % 360)
        if mode == 0 and sp > 750:
            k = min(1.0, (sp - 750) / 700)
            for j, al in ((3, 50), (2, 80), (1, 120)):
                img.set_alpha(int(al * k))
                s.blit(img, img.get_rect(center=(int(x - vx * 0.011 * j), int(y - vy * 0.011 * j))))
            img.set_alpha(255)
        s.blit(img, img.get_rect(center=(int(x), int(y))))

    def _draw_hud(self, s, snap):
        A = self.app.assets
        sc = snap["sc"]
        # skor tablosu
        cx = W // 2
        board = pygame.Rect(cx - 230, 10, 460, 78)
        frame(s, board)
        tm = snap["tm"]
        if snap.get("pen"):
            tt, tc = "PEN", GOLD
        elif snap["gg"]:
            tt, tc = "ALTIN GOL", GOLD
        else:
            sec = max(0, int(math.ceil(tm)))
            tt, tc = "%d:%02d" % (sec // 60, sec % 60), (255, 90, 80) if sec <= 10 else WHITE
        timer = pygame.Rect(0, 0, 124 if not snap["gg"] else 160, 46)
        timer.center = (cx, board.centery)
        pill(s, timer, (36, 52, 110), radius=14)
        draw_text(s, tt, 28 if not snap["gg"] else 22, (timer.centerx, timer.centery - 1), tc, outline=2)
        draw_text(s, str(sc[0]), 54, (cx - 118, board.centery - 2), WHITE, outline=4)
        draw_text(s, str(sc[1]), 54, (cx + 118, board.centery - 2), WHITE, outline=4)
        for i in (0, 1):
            p = snap["p"][i]
            char = p[9]
            por = A.portrait[char]
            if i == 1:
                por = A.flipped(por)
            px = board.left - 50 if i == 0 else board.right + 50
            cy = board.centery
            fx.blit_glow(s, px, cy, 52, _shade(P_COLORS[i], 0.3))
            gd.circle(s, (12, 14, 34), (px, cy), 42)
            gd.circle(s, P_COLORS[i], (px, cy), 39)
            gd.circle(s, (16, 24, 52), (px, cy), 34)
            s.blit(por, por.get_rect(center=(px, cy + 2)))
            gd.circle(s, GOLD, (px, cy), 39, 3)
            name = sim.DISPLAY_NAMES[char]
            if self.mode == "local2":
                tag = "P%d" % (i + 1)
            elif self.mode == "bot":
                tag = "SEN" if i == 0 else "CPU"
            else:
                tag = "SEN" if i == self.me else "RAKİP"
            # isim plakasi
            plate = pygame.Rect(0, 0, 214, 32)
            if i == 0:
                plate.topright = (px - 48, 12)
            else:
                plate.topleft = (px + 48, 12)
            pill(s, plate, (20, 28, 60), radius=12)
            chip = pygame.Rect(0, 0, 62 if len(tag) > 3 else 50, 24)
            chip.centery = plate.centery
            if i == 0:
                chip.left = plate.left + 5
                draw_text(s, name, 19, (chip.right + 10, plate.centery - 1), WHITE, anchor="midleft", outline=2)
            else:
                chip.right = plate.right - 5
                draw_text(s, name, 19, (chip.left - 10, plate.centery - 1), WHITE, anchor="midright", outline=2)
            pill(s, chip, P_COLORS[i], radius=9)
            draw_text(s, tag, 13, (chip.centerx, chip.centery - 1), WHITE, outline=2, title=False)
            # super bar
            meter_v, armed = p[6], p[7]
            pw = sim.CHARACTERS[char]["power"]
            col = POWERS[pw][1]
            bar = pygame.Rect(0, 0, 176, 20)
            if i == 0:
                bar.topright = (px - 52, 50)
            else:
                bar.topleft = (px + 52, 50)
            full = meter_v >= 100 or armed > 0
            seg_meter(s, bar, meter_v / 100, POWERS[pw][2], right=(i == 1), flash=full and int(self.t * 6) % 2 == 0)
            ic = A.power_icon_small[pw]
            s.blit(ic, ic.get_rect(center=(bar.left - 18 if i == 0 else bar.right + 18, bar.centery)))
            local = self.mode == "local2" or i == self.me
            if full and local:
                if armed > 0 or snap.get("mg", [0, 0])[i] > 0:
                    t = "SÜPER AKTİF!"
                else:
                    t = POWERS[pw][0] + " HAZIR · %s" % ("S / ↓" if self.mode != "local2" else ("S" if i == 0 else "↓"))
                draw_text(s, t, 16, (bar.centerx, bar.bottom + 14), col, outline=3)
            # aktif guc ikonlari
            icons = []
            if p[10] > 0:
                icons.append("speed")
            if p[11] > 0:
                icons.append("jump")
            if snap["sh"][i] > 0:
                icons.append("shield")
            for k, name in enumerate(icons):
                img = A.pu_small[name]
                ix = (bar.left + 16 + k * 34) if i == 0 else (bar.right - 16 - k * 34)
                s.blit(img, img.get_rect(center=(ix, bar.bottom + 46)))

    def _draw_pens(self, s, snap):
        pen = snap.get("pen")
        if not pen:
            return
        turn, res_ = pen
        box = pygame.Rect(0, 0, 360, 74)
        box.midtop = (W // 2, 96)
        frame(s, box)
        draw_text(s, "PENALTILAR", 16, (box.centerx, box.y + 16), GOLD, outline=2)
        for i in (0, 1):
            r = res_[i]
            n = max(5, len(r))
            for k in range(min(n, 8)):
                cx = box.centerx + (-1 if i == 0 else 1) * (30 + k * 20) if False else \
                    (box.x + 30 + k * 20 if i == 0 else box.right - 30 - k * 20)
                cy = box.y + 46
                if k < len(r):
                    col = (60, 210, 90) if r[k] else (230, 70, 60)
                    gd.circle(s, (12, 14, 34), (cx, cy), 9)
                    gd.circle(s, col, (cx, cy), 7)
                else:
                    gd.circle(s, (12, 14, 34), (cx, cy), 9)
                    gd.circle(s, (50, 60, 95), (cx, cy), 7)
            draw_text(s, str(sum(r)), 26, (box.centerx + (-24 if i == 0 else 24), box.y + 46), WHITE, outline=3)
        if snap["ph"] == "pen_ready":
            shooter = snap["p"][turn][9]
            if self.mode == "local2":
                who = "%d. OYUNCU" % (turn + 1)
            else:
                who = "SEN" if turn == self.me else "RAKİP"
            draw_text(s, "%s ATIYOR · %s" % (who, sim.DISPLAY_NAMES[shooter]), 26, (W // 2, 290), WHITE, outline=4)
            tip = "Şut: yerden  ·  Şut + YUKARI: üst köşe" if (self.mode == "local2" or turn == self.me) \
                else "Kaleci: ZIPLA (üst köşe) ya da BEKLE (yerden)"
            draw_text(s, tip, 18, (W // 2, 324), (200, 225, 255), outline=2, title=False)

    def _draw_overlays(self, s, snap):
        self._draw_pens(s, snap)
        for txt, x, y, life, col in self.floaters:
            draw_text(s, txt, 30, (x, y), col, outline=4, alpha=int(255 * min(1, life * 2)))
        if self.banner:
            txt, col, t, mx = self.banner
            k = 1 - t / mx
            scale = 1 + 0.35 * max(0, 1 - k * 6)
            size = int(96 * scale) if txt == "GOOOL!" else int(72 * scale)
            draw_text(s, txt, size, (W // 2, 200), col, outline=7, alpha=int(255 * min(1, t * 3)))
        if self.goal_line:
            txt, life, col = self.goal_line
            k = min(1.0, (2.6 - life) * 4)
            wob = math.sin(self.t * 10) * 2 if life > 0.5 else 0
            panel(s, (W // 2 - 360, 330 + wob, 720, 62), (10, 12, 28, int(200 * min(1, life * 2))), 20, col, 4)
            draw_text(s, txt, int(30 + 6 * (1 - k)), (W // 2, 361 + wob), WHITE, outline=4,
                      alpha=int(255 * min(1, life * 2)))
        if snap["ph"] == "ready" and snap["pt"] > 0 and self.banner is None:
            draw_text(s, str(int(math.ceil(snap["pt"]))), 80, (W // 2, 180), WHITE, outline=6)
        if snap["ph"] == "over":
            s.overlay((5, 8, 20, 150))
            win = snap["win"]
            if win == 2:
                t, c = "BERABERE", WHITE
            elif self.mode == "local2":
                t, c = "%d. OYUNCU KAZANDI!" % (win + 1), P_COLORS[win]
            elif win == self.me:
                t, c = "KAZANDIN!", GOLD
            else:
                t, c = "KAYBETTİN", (255, 110, 100)
            frame(s, (W // 2 - 390, 70, 780, 590))
            draw_text(s, t, 64, (W // 2, 128), c, outline=6)
            sc = snap["sc"]
            A = self.app.assets
            for i in (0, 1):
                img = (A.big_celeb if win in (i,) else A.big)[snap["p"][i][9]]
                if i == 1:
                    img = A.flipped(img)
                img = tf.smoothscale(img, (int(img.get_width() * 0.55), int(img.get_height() * 0.55)))
                s.blit(img, img.get_rect(midbottom=(W // 2 + (-270 if i == 0 else 270), 300)))
            draw_text(s, "%d  -  %d" % (sc[0], sc[1]), 76, (W // 2, 230), WHITE, outline=6)
            if snap.get("pen"):
                r_ = snap["pen"][1]
                draw_text(s, "Penaltılar: %d - %d" % (sum(r_[0]), sum(r_[1])), 22, (W // 2, 282), GOLD, outline=3)
            st = snap.get("st") or self.last_stats
            if st:
                self.last_stats = st
                poss = st["poss"]
                tot = max(0.01, poss[0] + poss[1])
                rows = [("ŞUT", st["shots"][0], st["shots"][1], 0),
                        ("KAFA", st["heads"][0], st["heads"][1], 1),
                        ("KURTARIŞ", st["saves"][0], st["saves"][1], 5),
                        ("TOPA SAHİP OLMA", "%%%d" % round(100 * poss[0] / tot), "%%%d" % round(100 * poss[1] / tot), 2),
                        ("EN SERT ŞUT", "%d km/s" % (st["fast"][0] // 8), "%d km/s" % (st["fast"][1] // 8), 3)]
                y = 336
                for lab, v0, v1, ic in rows:
                    rr = pygame.Rect(W // 2 - 330, y - 17, 660, 34)
                    pill(s, rr, (24, 34, 70), radius=12, gloss=False)
                    icon = A.stat_badges[ic] if A.stat_badges else None
                    if icon is not None:
                        s.blit(icon, icon.get_rect(center=(W // 2 - 104, y)))
                    draw_text(s, lab, 17, (W // 2 + 10, y - 1), (205, 218, 245), outline=2)
                    draw_text(s, str(v0), 22, (W // 2 - 300, y - 1), P_COLORS[0], anchor="midleft", outline=3)
                    draw_text(s, str(v1), 22, (W // 2 + 300, y - 1), P_COLORS[1], anchor="midright", outline=3)
                    y += 42
            if self.record_line:
                draw_text(s, self.record_line, 17, (W // 2, 560), (255, 225, 140), outline=2, title=False)
            if self.cup is not None:
                hint = "ENTER: devam"
            elif self.mode in ("bot", "local2"):
                hint = "ENTER: rövanş     ESC: karakter seçimi"
            else:
                me_ok = self.again[self.me]
                other_ok = self.again[1 - self.me]
                hint = "ENTER: rövanş     ESC: karakter seçimi"
                if me_ok:
                    hint = "Rakibin rövanş onayı bekleniyor..."
                elif other_ok:
                    hint = "Rakip rövanş istiyor!  ENTER: kabul"
            draw_text(s, hint, 22, (W // 2, 610), (220, 230, 250), outline=3, title=False)
        if self.paused:
            s.overlay((5, 8, 20, 170))
            draw_text(s, "DURAKLATILDI", 70, (W // 2, 280), GOLD, outline=6)
            draw_text(s, "ESC: devam     Q: ana menü", 28, (W // 2, 370), WHITE, outline=3, title=False)
        if self.quit_ask:
            frame(s, (W // 2 - 290, 290, 580, 140))
            draw_text(s, "Maçtan çıkılsın mı?", 34, (W // 2, 335), WHITE, outline=3)
            draw_text(s, "Q: çık     ESC: oyuna dön", 24, (W // 2, 385), (220, 230, 250), outline=2, title=False)


# ====================================================================== turnuva
CUP_STAGES = [   # (ad, bot seviyesi, hava, stadyum)
    ("ÇEYREK FİNAL 1", 0, "clear", 1),
    ("ÇEYREK FİNAL 2", 1, "rain", 0),
    ("YARI FİNAL", 1, "wind", 1),
    ("FİNAL ÖNCESİ", 2, "snow", 0),
    ("BÜYÜK FİNAL", 2, "clear", 1),
]


def new_cup(char):
    opps = [c for c in range(6) if c != char]
    random.shuffle(opps)
    return {"char": char, "stage": 0, "opps": opps[:5], "lost": False}


class CupScene(Scene):
    def __init__(self, app, cup, result=None):
        super().__init__(app)
        self.cup = cup
        self.t = 0
        self.spark = Sparkles(30)
        self.msg = None
        self.champion = False
        if result is True:
            cup["stage"] += 1
            cup["lost"] = False
            self.msg = ("KAZANDIN! SIRADAKİ TURA GEÇTİN", (120, 255, 140))
            app.sound.play("cheer", 0)
            if cup["stage"] >= len(CUP_STAGES):
                rec = load_record()
                rec["cups"] = rec.get("cups", 0) + 1
                save_record(rec)
                self.champion = True
        elif result is False:
            cup["lost"] = True
            self.msg = ("ELENDİN! ENTER İLE TEKRAR DENE", (255, 120, 110))
            app.sound.play("ooh", 0)

    def update(self, dt):
        self.t += dt
        self.spark.update(dt)
        if self.champion:
            self.app.go(TrophyScene(self.app, self.cup))

    def _play(self):
        if self.champion:
            return
        c = self.cup
        name, lvl, wx, stad = CUP_STAGES[c["stage"]]
        self.app.stadium = stad
        opp = c["opps"][c["stage"]]
        self.app.go(MatchScene(self.app, "bot", [c["char"], opp], 90, level=lvl, weather=wx, cup=c))

    def handle(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                self.app.sound.play("kick")
                self._play()
            elif e.key == pygame.K_ESCAPE:
                self.app.go(MenuScene(self.app))
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self._play()

    def draw(self, s):
        A = self.app.assets
        menu_backdrop(s, self.t, sparkles=self.spark)
        if self.champion or self.cup["stage"] >= len(CUP_STAGES):
            return
        draw_title(s, 62, self.t, small=True)
        frame(s, (90, 120, W - 180, 520))
        draw_text(s, "KUPA YOLU", 40, (W // 2, 160), GOLD, outline=5)
        trophy = A.cup_art.get("cup_gold")
        if trophy is not None:
            s.blit(trophy, trophy.get_rect(center=(W - 190, 190 + math.sin(self.t * 2) * 4)))
        c = self.cup
        me = A.portrait_big[c["char"]]
        s.blit(me, me.get_rect(center=(190, 195)))
        draw_text(s, sim.DISPLAY_NAMES[c["char"]], 20, (190, 258), WHITE, outline=3)
        n = len(CUP_STAGES)
        x0, x1, y = 190, W - 190, 400
        gd.line(s, (12, 14, 34), (x0, y), (x1, y), 12)
        gd.line(s, (80, 90, 130), (x0, y), (x1, y), 6)
        done_x = x0 + (x1 - x0) * min(c["stage"], n - 1) / (n - 1)
        if c["stage"] > 0:
            gd.line(s, GOLD, (x0, y), (done_x, y), 6)
        for k, (name, lvl, wx, stad) in enumerate(CUP_STAGES):
            x = x0 + (x1 - x0) * k / (n - 1)
            cur = k == c["stage"]
            won = k < c["stage"]
            badge = A.cup_art.get("st_check" if won else ("st_skull" if k == n - 1 else
                                                          ("st_swords" if cur else "st_lock")))
            r = 46 if cur else 38
            if cur:
                fx.blit_glow(s, x, y, 80 + 8 * math.sin(self.t * 4), (70, 55, 10))
            opp = c["opps"][k]
            por = A.portrait_big[opp] if (won or cur) else None
            gd.circle(s, (12, 14, 34), (x, y), r + 4)
            gd.circle(s, GOLD if cur else ((60, 200, 90) if won else (70, 80, 120)), (x, y), r + 1)
            gd.circle(s, (18, 26, 56), (x, y), r - 3)
            if por is not None:
                p2 = tf.smoothscale(por, (r * 2 - 8, r * 2 - 8))
                s.blit(p2, p2.get_rect(center=(x, y)))
            if badge is not None:
                s.blit(badge, badge.get_rect(center=(x + r * 0.7, y - r * 0.7)))
            draw_text(s, name, 15 if not cur else 17, (x, y + r + 22), GOLD if cur else WHITE, outline=2)
            sub = "%s · %s" % (dict(WEATHERS)[wx], STADIUMS[stad]["name"])
            draw_text(s, sub, 12, (x, y + r + 44), (190, 205, 235), outline=2, title=False)
            draw_text(s, LEVELS[lvl], 12, (x, y - r - 16), (255, 200, 120), outline=2, title=False)
        if self.msg:
            draw_text(s, self.msg[0], 26, (W // 2, 540), self.msg[1], outline=3)
        name = CUP_STAGES[c["stage"]][0]
        opp = c["opps"][c["stage"]]
        draw_text(s, "%s: %s  vs  %s" % (name, sim.DISPLAY_NAMES[c["char"]], sim.DISPLAY_NAMES[opp]), 22,
                  (W // 2, 584), WHITE, outline=3)
        draw_text(s, "ENTER: maça başla   ·   ESC: ana menü", 17, (W // 2, 620), (200, 210, 230), outline=2,
                  title=False)


class TrophyScene(Scene):
    def __init__(self, app, cup):
        super().__init__(app)
        self.cup = cup
        self.t = 0
        self.spark = Sparkles(80)
        self.fw = []
        app.sound.play("golden", 0)
        app.sound.play("goal", 0)

    def update(self, dt):
        self.t += dt
        self.spark.update(dt)
        if random.random() < dt * 3:
            self.fw.append([random.uniform(150, W - 150), random.uniform(80, 300),
                            random.choice(["fx_fw_gold", "fx_fw_red", "fx_fw_blue"]), 1.0])
            self.app.sound.play("pop", 0.05, 0.5)
        for f in self.fw:
            f[3] -= dt
        self.fw = [f for f in self.fw if f[3] > 0]

    def handle(self, e):
        if self.t > 1.5 and e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.app.go(MenuScene(self.app))

    def draw(self, s):
        A = self.app.assets
        menu_backdrop(s, self.t, dark=False, sparkles=self.spark)
        for x, y, name, life in self.fw:
            img = A.fx(name, 200)
            if img is not None:
                k = 0.4 + 0.8 * min(1, (1 - life) * 2.5)
                im = tf.rotozoom(img, 0, k)
                im.set_alpha(int(255 * min(1, life * 2)))
                s.blit(im, im.get_rect(center=(x, y)))
        pod = A.cup_art.get("podium_big")
        base_y = 560
        if pod is not None:
            pr = pod.get_rect(midbottom=(W // 2, 712))
            s.blit(pod, pr)
            base_y = pr.top + 10
        hero = A.hero[self.cup["char"]][1]
        hop = abs(math.sin(self.t * 6)) * 14
        s.blit(hero, hero.get_rect(midbottom=(W // 2, base_y - hop)))
        trophy = A.cup_art.get("cup_gold_big")
        if trophy is not None:
            fx.blit_glow(s, W // 2 + 120, 360, 140, (80, 60, 10))
            s.blit(trophy, trophy.get_rect(center=(W // 2 + 130, 380 - hop * 0.5)))
        draw_text(s, "ŞAMPİYON!", 92, (W // 2, 120), GOLD, outline=7)
        draw_text(s, sim.DISPLAY_NAMES[self.cup["char"]], 40, (W // 2, 205), WHITE, outline=5)
        cups = load_record().get("cups", 0)
        draw_text(s, "Toplam kupa: %d" % cups, 22, (W // 2, 248), (255, 225, 140), outline=3, title=False)
        if self.t > 1.5:
            draw_text(s, "Devam etmek için bir tuşa bas", 18, (W // 2, H - 20), WHITE, outline=2, title=False)


# ====================================================================== uygulama
class App:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        gfx.set_scale(self._pick_scale())
        PW, PH = int(W * gfx.K), int(H * gfx.K)
        flags = pygame.SCALED | pygame.RESIZABLE
        try:
            # varsayilan: tam ekran (F11 ile pencereye gecilir)
            surf = pygame.display.set_mode((PW, PH), flags | pygame.FULLSCREEN)
        except pygame.error:
            try:
                surf = pygame.display.set_mode((PW, PH), flags)
            except pygame.error:
                surf = pygame.display.set_mode((PW, PH))
        self.screen = gfx.Canvas(surf)
        pygame.display.set_caption("Kafa Kafaya Futbol")
        try:
            pygame.display.set_icon(pygame.image.load(res("assets", "ball.png")))
        except Exception:
            pass
        self.screen.fill(DARK)
        draw_text(self.screen, "Yükleniyor...", 40, (W // 2, H // 2))
        pygame.display.flip()
        self.assets = Assets()
        global ASSETS
        ASSETS = self.assets
        self.crowds = [fx.Crowd(res, W, sd["crowd"], sd["mask"], sd["light"]) for sd in STADIUMS]
        self.stadium = 1   # varsayilan: Timsah Arena
        self.mirror = load_record().get("mirror", True)
        self.weather = 0
        self.sound = Sound()
        self.clock = pygame.time.Clock()
        self.running = True
        self.bot_level = 1
        self.hidden = False
        self._restore_events = tuple(getattr(pygame, n) for n in ("WINDOWRESTORED", "WINDOWFOCUSGAINED")
                                     if hasattr(pygame, n))
        self.scene = MenuScene(self)

    @staticmethod
    def _pick_scale():
        """Ekran cozunurlugune gore cizim olcegi: 1280x720 -> 1.0, 1920x1080 -> 1.5."""
        env = os.environ.get("KAFA_OLCEK")
        if env:
            try:
                return max(0.5, min(2.0, float(env)))
            except ValueError:
                pass
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except Exception:
            return 1.0
        r = min(dw / W, dh / H)
        return max(1.0, min(1.5, math.floor(r * 4) / 4))

    def go(self, scene):
        old = self.scene
        self.scene = scene
        if old is not None and old is not scene:
            old.leave()

    def quit(self):
        self.running = False

    def hide(self):
        """P: oyunu simge durumuna kucult ve sesi kapat."""
        self.hidden = True
        self.sound.hidden = True
        try:
            pygame.mixer.pause()
        except pygame.error:
            pass
        if isinstance(self.scene, MatchScene) and self.scene.mode in ("bot", "local2"):
            self.scene.paused = True
        try:
            pygame.display.iconify()
        except pygame.error:
            pass

    def unhide(self):
        self.hidden = False
        self.sound.hidden = False
        try:
            pygame.mixer.unpause()
        except pygame.error:
            pass

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for e in pygame.event.get():
                if e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN) and gfx.K != 1.0:
                    d = dict(e.dict)
                    d["pos"] = (int(e.pos[0] / gfx.K), int(e.pos[1] / gfx.K))
                    e = pygame.event.Event(e.type, d)
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                    try:
                        pygame.display.toggle_fullscreen()
                    except pygame.error:
                        pass
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_p and not isinstance(self.scene, JoinScene):
                    self.hide()
                elif self.hidden and e.type in self._restore_events:
                    self.unhide()
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_m and not isinstance(self.scene, JoinScene):
                    self.sound.toggle()
                    if not self.sound.muted and isinstance(self.scene, MatchScene):
                        self.sound.ambience(True)
                else:
                    self.scene.handle(e)
            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()
        sc = self.scene
        try:
            if getattr(sc, "conn", None):
                sc.conn.send({"t": "bye"})
                sc.conn.close()
            sc.leave()
        except Exception:
            pass
        pygame.quit()


def main():
    try:
        App().run()
    except Exception:
        import traceback
        path = os.path.join(os.path.expanduser("~"), "kafakafaya_hata.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except OSError:
            pass
        raise


if __name__ == "__main__":
    main()
