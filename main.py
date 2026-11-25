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
    "s": (pygame.K_s, pygame.K_DOWN),
}
KEYS_P1 = {
    "l": (pygame.K_a,), "r": (pygame.K_d,), "j": (pygame.K_w,),
    "k": (pygame.K_SPACE,), "s": (pygame.K_s,),
}
KEYS_P2 = {
    "l": (pygame.K_LEFT,), "r": (pygame.K_RIGHT,), "j": (pygame.K_UP,),
    "k": (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_KP0), "s": (pygame.K_DOWN, pygame.K_KP1),
}

GOAL_LINES = {
    "super": ["SÜPER GÜÇ! DURDURULAMAZ!", "BU ŞUT DEĞİL, FÜZE!", "KALECİ ERİDİ GİTTİ!", "GÜÇ SENDE, GOL BİZDE!"],
    "head": ["KAFAYLA ÇAKTI!", "KAFA ÇALIŞIYOR MAŞALLAH!", "KAFA GOLÜ! NE YÜKSELDİ AMA!", "KAFANI KULLAN DEMİŞTİM!"],
    "lob": ["AŞIRTMA! BAKAKALDI!", "GÖKYÜZÜNDEN DÜŞTÜ!", "TOP KAFANIN ÜSTÜNDEN UÇTU!", "YAĞMUR GİBİ İNDİ!"],
    "flick": ["TOPUKLA! ŞOV YAPIYOR!", "TOPUK GOLÜ! AYIP OLDU!", "BAKMADAN ATTI!"],
    "own": ["KENDİ KALESİNE! TEŞEKKÜRLER!", "ÇOK AYIP, KENDİ KALENE!", "HEDİYE GOL! SAĞ OL!", "YANLIŞ KALE KARDEŞİM!"],
    "hard": ["ÇOK SERT! TUTABİLİRSEN TUT!", "FÜZE GİBİ GİRDİ!", "FİLEYİ YIRTTI!", "BU NE VURUŞ BE!", "ELİNİ YAKARDI!"],
    "volley": ["VOLE! HAVADA YAKALADI!", "NE VOLE AMA!", "DÜŞMEDEN VURDU!"],
    "any": ["NASIL ATTIM AMA!", "KALECİ NEREDEYDİ?", "UYUMA, MAÇ VAR!", "TAM DOKSANA!", "BİR DAHA DENE!",
            "ÇOK KOLAY OLDU!", "BU DA MI GOL?", "DERS GİBİ GOL!"],
}

PU_TEXT = {"speed": "HIZ!", "jump": "SÜPER ZIPLAMA!", "shield": "BUZ KALKAN!",
           "freeze": "DONDURMA!", "gold": "SÜPER DOLDU!"}


def res(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


# ====================================================================== yazi
_fonts = {}
_tcache = {}


def get_font(size, title=False):
    key = (size, title)
    f = _fonts.get(key)
    if f is None:
        names = "arialblack,segoeuiblack,impact,arial" if title else "segoeuisemibold,segoeui,arial,tahoma"
        try:
            f = pygame.font.SysFont(names, size, bold=not title)
        except Exception:
            f = pygame.font.Font(None, size)
        _fonts[key] = f
    return f


def text_surf(txt, size, color=WHITE, outline=3, ocolor=(15, 18, 30), title=True):
    """Yaziyi ekran cozunurlugunde (K kat) cizer, gfx.Img dondurur."""
    key = (txt, size, color, outline, ocolor, title)
    s = _tcache.get(key)
    if s is not None:
        return s
    k = gfx.K
    f = get_font(max(6, int(round(size * k))), title)
    base = f.render(txt, True, color)
    o_px = int(round(outline * k))
    if outline:
        o = f.render(txt, True, ocolor)
        surf = pygame.Surface((base.get_width() + o_px * 2, base.get_height() + o_px * 2), pygame.SRCALPHA)
        steps = max(1, o_px)
        dirs = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
        for dx, dy in dirs:
            surf.blit(o, (o_px + dx * steps, o_px + dy * steps))
        if o_px >= 3:
            for dx, dy in dirs:
                surf.blit(o, (o_px + dx * steps // 2, o_px + dy * steps // 2))
        surf.blit(base, (o_px, o_px))
    else:
        surf = base
    s = gfx.Img(surf)
    if len(_tcache) > 500:
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

        st = pygame.transform.smoothscale(pygame.image.load(res("assets", "stadium_night_clean.jpg")).convert(),
                                          (int(W * gfx.K), int(H * gfx.K)))
        st.blit(fx.make_vignette(st.get_width(), st.get_height(), 80), (0, 0))  # vinyet arka plana gomulu
        self.stadium = gfx.Img(st)
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
            self.poses.append(poses)
            bh = 215
            fb = bh / idle.get_height()
            self.big.append(scaled(idle, fb))
            cp = res("assets", "p%d_celeb.png" % i)
            cimg = L("p%d_celeb.png" % i) if os.path.exists(cp) else idle
            self.big_celeb.append(scaled(cimg, fb))
            head = idle.subsurface(pygame.Rect(0, 0, idle.get_width(), int(idle.get_height() * 0.40))).copy()
            ph = 58
            self.portrait.append(scaled(head, ph / head.get_height()))
            self.portrait_big.append(scaled(head, 104 / head.get_height()))
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
        # arayuz parcalari
        self.ui_raw = {n: L(n + ".png") for n in ("ui_btn", "ui_btn_hot", "ui_btn_blue", "ui_panel")}
        self.icons = {n: self._fit(L("ic_%s.png" % n), 46) for n in ("host", "join", "bot", "2p", "keys", "exit")}
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
        mk = lambda i, txt, cb, ic: Button((x, 262 + i * 70, bw, bh), txt, cb, ic)
        self.list = ButtonList([
            mk(0, "MAÇ KUR", lambda: a.go(HostWaitScene(a)), "host"),
            mk(1, "MAÇA KATIL", lambda: a.go(JoinScene(a)), "join"),
            mk(2, "BİLGİSAYARA KARŞI", lambda: a.go(SelectScene(a, "bot")), "bot"),
            mk(3, "TEK PC 2 KİŞİ", lambda: a.go(SelectScene(a, "local2")), "2p"),
            mk(4, "KONTROLLER", lambda: a.go(HelpScene(a)), "keys"),
            mk(5, "ÇIKIŞ", a.quit, "exit"),
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
            ("Şut", "BOŞLUK"),
            ("Süper güç", "S  veya  ↓  (bar dolunca)"),
            ("Gizle", "P  (küçült + sesi kapat)"),
            ("TEK PC 2 KİŞİ", None),
            ("1. Oyuncu", "A/D hareket, W zıpla, BOŞLUK şut, S süper"),
            ("2. Oyuncu", "←/→ hareket, ↑ zıpla, ENTER şut, ↓ süper"),
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
        tips = ["Şut topu yukarı kaldırır  ·  Geri giderken şut: yüksek aşırtma",
                "Top arkanda kaldıysa ŞUT: topukla kafanın üstünden öne aşırtırsın",
                "Topu güç simgelerine çarptır: HIZ, ZIPLAMA, BUZ KALKAN, DONDURMA, SÜPER",
                "Süper şut gelirken tam zamanında ŞUT tuşuna basarsan kurtarırsın!"]
        for k, tip in enumerate(tips):
            draw_text(s, tip, 18, (W // 2, y + 8 + k * 25), (255, 230, 150), outline=2, title=False)
        draw_text(s, "Geri dönmek için bir tuşa bas", 18, (W // 2, H - 44), (200, 210, 230), outline=2, title=False)


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
        if mode == "bot":
            self.pick[1] = random.randrange(6)
        if self.conn:
            self._send_pick()
        self.cards = [pygame.Rect(cx - 85, 300, 170, 270) for cx in PODIUMS]

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
            if k == pygame.K_z and self.mode == "bot":
                self.level = (self.level + 1) % 3
                self.app.bot_level = self.level
                self.app.sound.play("click")
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
                elif t == "start" and self.mode == "client":
                    self.app.go(MatchScene(self.app, "client", m["c"], m["dur"], conn=self.conn,
                                           pending=msgs[i + 1:]))
                    return
        if self.mode == "bot" and self.ready[0]:
            self.app.go(MatchScene(self.app, "bot", self.pick, self.dur, level=self.level))
        elif self.mode in ("local2",) and all(self.ready):
            self.app.go(MatchScene(self.app, "local2", self.pick, self.dur))
        elif self.mode == "host" and all(self.ready):
            self.conn.send({"t": "start", "c": self.pick, "dur": self.dur})
            self.app.go(MatchScene(self.app, "host", self.pick, self.dur, conn=self.conn))

    def draw(self, s):
        A = self.app.assets
        s.blit(A.select_bg, (0, 0))
        labels = {"bot": ("SEN", "BİLGİSAYAR"), "local2": ("1. OYUNCU", "2. OYUNCU"),
                  "host": ("SEN", "RAKİP"), "client": ("RAKİP", "SEN")}[self.mode]
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
            draw_text(s, sim.DISPLAY_NAMES[c], 32, (tx, r.y + 42), WHITE, anchor="midleft", outline=3)
            for j, (lab, val) in enumerate(zip(("HIZ", "ZIPLAMA", "ŞUT"), sim.STAT_BARS[c])):
                y = r.y + 82 + j * 24
                draw_text(s, lab, 15, (tx, y), (200, 215, 240), anchor="midleft", outline=2, title=False)
                for k in range(5):
                    col = GOLD if k < val else (45, 55, 90)
                    gd.rect(s, col, (tx + 92 + k * 28, y - 7, 24, 14), 0, border_radius=4)
            pw = sim.CHARACTERS[c]["power"]
            ic = A.icon_fire if pw == "fire" else A.icon_ice
            s.blit(ic, ic.get_rect(center=(tx + 12, r.y + 160)))
            draw_text(s, "ATEŞ ŞUTU" if pw == "fire" else "BUZ ŞUTU", 18, (tx + 32, r.y + 160),
                      FIRE_C if pw == "fire" else ICE_C, anchor="midleft", outline=2)
            # durum etiketi
            if self.mode == "bot" and who == 1:
                st, sc = "ZORLUK: %s (Z)" % LEVELS[self.level], (255, 200, 120)
            elif self.ready[who]:
                st, sc = "HAZIR!", (120, 255, 140)
            else:
                st, sc = "seçiyor...", (220, 225, 240)
            tag = pygame.Rect(0, 0, 250, 36)
            tag.center = (r.centerx, r.bottom)
            gd.rect(s, (10, 14, 30), tag.inflate(6, 6), 0, border_radius=12)
            gd.rect(s, P_COLORS[who], tag, 0, border_radius=10)
            draw_text(s, "%s · %s" % (labels[who], st), 17, tag.center, sc if st == "HAZIR!" else WHITE, outline=2)
        # VS ve ayarlar
        vs_bob = math.sin(self.t * 3) * 4
        fx.blit_glow(s, W // 2, 160, 90, (70, 50, 10))
        draw_text(s, "VS", 78, (W // 2, 160 + vs_bob), GOLD, outline=6)
        draw_text(s, "Süre: %d sn%s" % (self.dur, "  (T)" if self.mode != "client" else ""), 18,
                  (W // 2, 232), (215, 225, 245), outline=2, title=False)
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
            draw_text(s, sim.DISPLAY_NAMES[i], 19, (cx, 588), GOLD if (sel0 or sel1) else (210, 215, 230), outline=3)
            # secim oklari
            tags = [(0, labels[0])] if sel0 else []
            if sel1:
                tags.append((1, labels[1]))
            for n, (who, lab) in enumerate(tags):
                ty = 312 - n * 34 + math.sin(self.t * 5) * 3
                tag = pygame.Rect(0, 0, 118, 28)
                tag.center = (cx, ty)
                gd.rect(s, P_COLORS[who], tag, 0, border_radius=10)
                gd.polygon(s, P_COLORS[who], [(cx - 8, tag.bottom), (cx + 8, tag.bottom), (cx, tag.bottom + 9)])
                draw_text(s, lab, 15, tag.center, outline=2)
        if self.mode == "local2":
            hint = "1. oyuncu: A/D seç, BOŞLUK hazır    ·    2. oyuncu: ←/→ seç, ENTER hazır"
        elif self.mode == "bot":
            hint = "←/→ seç · ENTER hazır · ↑/↓ rakip karakteri · Z zorluk · T süre"
        else:
            hint = "←/→ seç · ENTER hazır" + (" · T süre" if self.mode == "host" else "")
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

    def __init__(self, app, mode, chars, dur, conn=None, level=1, pending=None):
        super().__init__(app)
        self.mode = mode
        self.chars = list(chars)
        self.dur = dur
        self.conn = conn
        self.level = level
        self.world = None
        if mode != "client":
            self.world = sim.World(chars[0], chars[1], dur)
        self.bot = sim.Bot(1, level) if mode == "bot" else None
        self.acc = 0.0
        self.counts = [[0, 0], [0, 0]]          # [kick, super] yerel basis sayaclari
        self.used = [[0, 0], [0, 0]]
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
        self.frame = gfx.Canvas(pygame.Surface((int(W * gfx.K), int(H * gfx.K))))
        self.rings = []
        self.flashes = []
        self.ripple = None
        self.goal_flash = 0.0
        self.goal_line = None
        self.last_count = None
        self.pstate = [{"og": None, "sq": 0.0, "st": 0.0, "fz": 0.0} for _ in range(2)]
        app.crowd.excite = app.crowd.target = 0.15
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

    def _rematch(self):
        if self.mode in ("bot", "local2"):
            self.app.go(MatchScene(self.app, self.mode, self.chars, self.dur, level=self.level))
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
        kp = sp = False
        if first:
            kp = self.counts[i][0] > self.used[i][0]
            sp = self.counts[i][1] > self.used[i][1]
            self.used[i] = list(self.counts[i])
        return h["l"], h["r"], h["j"], kp, sp

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
                self.conn.send({"t": "start", "c": self.chars, "dur": self.dur})
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
                w.apply_input(1, *self.bot.think(w, STEP))
            else:
                r = self.remote
                kp = sp = False
                if first:
                    kp = r.get("k", 0) > self.used[1][0]
                    sp = r.get("s", 0) > self.used[1][1]
                    self.used[1] = [r.get("k", 0), r.get("s", 0)]
                w.apply_input(1, bool(r.get("l")), bool(r.get("r")), bool(r.get("j")), kp, sp)
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
        self.conn.send({"t": "in", "l": int(h["l"]), "r": int(h["r"]), "j": int(h["j"]),
                        "k": self.counts[1][0], "s": self.counts[1][1]})
        now = time.time()
        msgs = self.pending + self.conn.poll()
        self.pending = []
        for i, m in enumerate(msgs):
            t = m.get("t")
            if t == "st":
                self.snaps.append((now, m))
                self._process(m)
                ag = m.get("ag")
                if ag:
                    self.again = [bool(ag[0]), bool(ag[1])]
            elif t == "start":
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
        crowd = self.app.crowd
        bx, by = snap["b"][0], snap["b"][1]
        ph = snap["ph"]
        if ph != self.prev_phase:
            if ph == "ready":
                self._say("HAZIR", WHITE, 1.0)
            elif ph == "play" and self.prev_phase == "ready":
                self._say("BAŞLA!", GOLD, 0.8)
            elif ph == "over":
                crowd.kick(1.0, snap["win"])
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
                elif kind in ("super", "head", "lob", "flick", "volley"):
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

    def _update_fx(self, dt):
        self.app.crowd.update(dt)
        for p in self.parts:
            p.vy += p.g * dt
            if p.kind == "confetti":
                p.vx *= (1 - 2.0 * dt)
                p.vy = min(p.vy, 140)
                p.vx += math.sin(p.rot * 0.05) * 30 * dt
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
        s.blit(A.stadium, (0, 0))
        self.app.crowd.draw(s)
        for i, (lx, ly) in enumerate(((90, 80), (435, 194), (851, 194), (1180, 80))):
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
        # arkadaki parcaciklar (duman)
        for p in self.parts:
            if p.kind == "smoke":
                self._draw_particle(s, p)
        for i, p in enumerate(snap["p"]):
            self._draw_player(s, i, p, snap)
        self._draw_ball(s, b)
        self._draw_goal_front(s, snap)
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
        self._draw_hud(s, snap)
        ox = oy = 0
        if self.shake > 0:
            m = 10 * min(1, self.shake * 2.5)
            ox, oy = random.uniform(-m, m), random.uniform(-m, m)
        screen.fill((0, 0, 0))
        screen.blit(s, (ox, oy))
        self._draw_overlays(screen, snap)

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
        GD, GT, GR = sim.GOAL_D, sim.GOAL_TOP, sim.GROUND
        A = self.app.assets
        rp = self.ripple
        for side in (0, 1):
            x0 = 0 if side == 0 else W - GD
            s.blit(A.net_shade, (x0, GT))
            if rp and rp[0] == side:
                t = rp[2]
                amp = 16 * math.exp(-t * 3.2)
                d = -1 if side == 0 else 1
                for gx in range(0, GD + 1, 14):
                    u = gx / GD if side == 1 else 1 - gx / GD
                    pts = []
                    for gy in range(0, GR - GT + 1, 10):
                        dist = (GT + gy - rp[1]) / 70.0
                        off = amp * math.exp(-dist * dist) * math.cos(t * 18 - abs(dist) * 2) * (0.3 + u)
                        pts.append((x0 + gx + d * off, GT + gy))
                    gd.lines(s, (240, 240, 245), False, pts, 2)
                for gy in range(0, GR - GT, 14):
                    dist = (GT + gy - rp[1]) / 70.0
                    off = amp * math.exp(-dist * dist) * math.cos(t * 18 - abs(dist) * 2)
                    gd.line(s, (240, 240, 245), (x0, GT + gy), (x0 + GD + d * off * 0.3, GT + gy), 2)
            else:
                s.blit(A.net_lines, (x0, GT))
        for x in (6, W - 6):
            gd.line(s, (200, 200, 210), (x, GT), (x, GR), 6)
        for i in range(2):
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
        GD, GT, GR, RT = sim.GOAL_D, sim.GOAL_TOP, sim.GROUND, sim.ROOF_T
        for side in (0, 1):
            if side == 0:
                roof = pygame.Rect(0, GT - RT, GD + 6, RT)
                postx = GD
            else:
                roof = pygame.Rect(W - GD - 6, GT - RT, GD + 6, RT)
                postx = W - GD
            gd.rect(s, (30, 30, 40), roof.inflate(4, 4), 0, border_radius=6)
            gd.rect(s, (245, 245, 250), roof, 0, border_radius=6)
            gd.line(s, (255, 255, 255), (roof.x + 4, roof.y + 3), (roof.right - 4, roof.y + 3), 2)
            gd.line(s, (30, 30, 40), (postx, GT - 2), (postx, GR), 12)
            gd.line(s, (245, 245, 250), (postx, GT - 2), (postx, GR), 8)
            gd.line(s, (255, 255, 255), (postx - 2, GT), (postx - 2, GR), 2)
            for yy in (GT + 20, GT + 70, GT + 120, GT + 170):
                gd.line(s, (230, 70, 70), (postx, yy), (postx, yy + 20), 8)

    def _player_img(self, char, p, snap, i):
        """Duruma gore uygun pozu sec."""
        A = self.app.assets
        x, y, vx, face, kick_t, frozen, meter, armed, on_ground, _, speed_t, jump_t, stun, run_t = p
        poses = A.poses[char]
        ice = frozen > 0
        celebrate = (snap["ph"] == "goal" and snap.get("scr") == i) or (snap["ph"] == "over" and snap["win"] == i)
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
        x, y, vx, face, kick_t, frozen, meter, armed, on_ground, char, speed_t, jump_t, stun, run_t = p
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
        if st["sq"] > 0:
            k = st["sq"] / 0.16
            sx, sy = 1 + 0.16 * k, 1 - 0.14 * k
        elif st["st"] > 0:
            k = st["st"] / 0.16
            sx, sy = 1 - 0.08 * k, 1 + 0.1 * k
        if armed > 0:
            pw = sim.CHARACTERS[char]["power"]
            c = (130, 60, 10) if pw == "fire" else (30, 90, 130)
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
        if label:
            ty = y - h - 30 + math.sin(self.t * 5) * 3 - bob
            gd.polygon(s, P_COLORS[i], [(x - 9, ty + 10), (x + 9, ty + 10), (x, ty + 20)])
            draw_text(s, label, 18, (x, ty), P_COLORS[i], outline=3)

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
        if snap["gg"]:
            tt, tc = "ALTIN GOL", GOLD
        else:
            sec = max(0, int(math.ceil(tm)))
            tt, tc = "%d:%02d" % (sec // 60, sec % 60), (255, 90, 80) if sec <= 10 else WHITE
        timer = pygame.Rect(0, 0, 120 if not snap["gg"] else 150, 44)
        timer.center = (cx, board.centery)
        gd.rect(s, (40, 46, 70), timer, 0, border_radius=12)
        gd.rect(s, (90, 100, 140), timer, 2, border_radius=12)
        draw_text(s, tt, 28 if not snap["gg"] else 22, timer.center, tc, outline=2)
        draw_text(s, str(sc[0]), 50, (cx - 112, board.centery), WHITE, outline=4)
        draw_text(s, str(sc[1]), 50, (cx + 112, board.centery), WHITE, outline=4)
        for i in (0, 1):
            p = snap["p"][i]
            char = p[9]
            por = A.portrait[char]
            if i == 1:
                por = A.flipped(por)
            px = board.left - 50 if i == 0 else board.right + 50
            circ = pygame.Rect(0, 0, 76, 76)
            circ.center = (px, board.centery)
            gd.circle(s, P_COLORS[i], circ.center, 40)
            gd.circle(s, (12, 16, 34), circ.center, 35)
            s.blit(por, por.get_rect(center=(px, board.centery + 2)))
            gd.circle(s, GOLD, circ.center, 40, 3)
            name = sim.DISPLAY_NAMES[char]
            if self.mode == "local2":
                tag = "P%d" % (i + 1)
            elif self.mode == "bot":
                tag = "SEN" if i == 0 else "CPU"
            else:
                tag = "SEN" if i == self.me else "RAKİP"
            nx = px - 50 if i == 0 else px + 50
            draw_text(s, "%s · %s" % (tag, name), 20, (nx, 30), P_COLORS[i],
                      anchor="midright" if i == 0 else "midleft", outline=3)
            # super bar
            meter, armed = p[6], p[7]
            pw = sim.CHARACTERS[char]["power"]
            col = FIRE_C if pw == "fire" else ICE_C
            bw = 170
            bar = pygame.Rect(0, 0, bw, 16)
            if i == 0:
                bar.midright = (px - 50, 62)
            else:
                bar.midleft = (px + 50, 62)
            gd.rect(s, (12, 16, 34), bar.inflate(6, 6), 0, border_radius=8)
            fill = bar.copy()
            fill.w = int(bw * meter / 100)
            if i == 1:
                fill.right = bar.right
            full = meter >= 100 or armed > 0
            fc = col if not full else tuple(min(255, int(c * (1 + 0.3 * math.sin(self.t * 10)))) for c in col)
            if fill.w > 0:
                gd.rect(s, fc, fill, 0, border_radius=6)
            gd.rect(s, (230, 230, 240), bar.inflate(6, 6), 2, border_radius=8)
            ic = A.icon_fire if pw == "fire" else A.icon_ice
            s.blit(ic, ic.get_rect(center=(bar.left - 20 if i == 0 else bar.right + 20, bar.centery)))
            local = self.mode == "local2" or i == self.me
            if full and local:
                if armed > 0:
                    t = "SÜPER AKTİF!"
                else:
                    t = "SÜPER HAZIR! [%s]" % ("S / ↓" if self.mode != "local2" else ("S" if i == 0 else "↓"))
                draw_text(s, t, 16, (bar.centerx, bar.bottom + 14), col, outline=2)
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

    def _draw_overlays(self, s, snap):
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
            frame(s, (W // 2 - 340, 170, 680, 380))
            draw_text(s, t, 72, (W // 2, 250), c, outline=6)
            sc = snap["sc"]
            A = self.app.assets
            for i in (0, 1):
                img = (A.big_celeb if win in (i,) else A.big)[snap["p"][i][9]]
                if i == 1:
                    img = A.flipped(img)
                img = tf.smoothscale(img, (int(img.get_width() * 0.62), int(img.get_height() * 0.62)))
                s.blit(img, img.get_rect(midbottom=(W // 2 + (-230 if i == 0 else 230), 470)))
            draw_text(s, "%d  -  %d" % (sc[0], sc[1]), 84, (W // 2, 375), WHITE, outline=6)
            if self.mode in ("bot", "local2"):
                hint = "ENTER: rövanş     ESC: karakter seçimi"
            else:
                me_ok = self.again[self.me]
                other_ok = self.again[1 - self.me]
                hint = "ENTER: rövanş     ESC: karakter seçimi"
                if me_ok:
                    hint = "Rakibin rövanş onayı bekleniyor..."
                elif other_ok:
                    hint = "Rakip rövanş istiyor!  ENTER: kabul"
            draw_text(s, hint, 24, (W // 2, 500), (220, 230, 250), outline=3, title=False)
        if self.paused:
            s.overlay((5, 8, 20, 170))
            draw_text(s, "DURAKLATILDI", 70, (W // 2, 280), GOLD, outline=6)
            draw_text(s, "ESC: devam     Q: ana menü", 28, (W // 2, 370), WHITE, outline=3, title=False)
        if self.quit_ask:
            frame(s, (W // 2 - 290, 290, 580, 140))
            draw_text(s, "Maçtan çıkılsın mı?", 34, (W // 2, 335), WHITE, outline=3)
            draw_text(s, "Q: çık     ESC: oyuna dön", 24, (W // 2, 385), (220, 230, 250), outline=2, title=False)


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
        self.crowd = fx.Crowd(res, W)
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
