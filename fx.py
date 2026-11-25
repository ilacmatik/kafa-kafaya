"""Gorsel efekt yardimcilari: hareketli tribun, isima dokulari, vinyet."""
import json
import math
import random

import pygame

import gfx
from gfx import draw as gd

TEAM = {
    "red": [(225, 60, 60), (250, 250, 250), (185, 35, 40)],
    "blue": [(60, 115, 225), (245, 245, 252), (35, 70, 165)],
    "yellow": [(252, 205, 45), (45, 45, 55), (235, 165, 25)],
    "green": [(70, 175, 70), (250, 250, 250), (35, 120, 50)],
}
SKINS = [(255, 216, 172), (236, 186, 142), (198, 142, 100), (142, 96, 64)]
HAIRS = [(60, 40, 25), (25, 22, 25), (235, 200, 90), (150, 70, 30)]
OUT = (30, 24, 30)

_soft = {}
_glow = {}


def soft_dot(r, color):
    """Yumusak kenarli renkli daire (gfx.Img, normal alfa ile cizilir)."""
    r = max(1, int(r))
    key = (r, color)
    s = _soft.get(key)
    if s is None:
        R = max(1, int(round(r * gfx.K)))
        raw = pygame.Surface((R * 2, R * 2), pygame.SRCALPHA)
        for i in range(R, 0, -1):
            a = int(255 * (1 - i / R) ** 1.3) if i < R else 0
            pygame.draw.circle(raw, color + (max(0, min(255, a + 10)),), (R, R), i)
        s = gfx.Img(raw)
        _soft[key] = s
        if len(_soft) > 800:
            _soft.clear()
    return s


def glow(r, color):
    """Toplamali (BLEND_RGB_ADD) isima dokusu: merkez parlak, kenar siyah."""
    r = max(2, int(r))
    key = (r, color)
    s = _glow.get(key)
    if s is None:
        s = pygame.Surface((r * 2, r * 2))
        s.fill((0, 0, 0))
        for i in range(r, 0, -1):
            k = (1 - i / r) ** 1.8
            pygame.draw.circle(s, tuple(int(c * k) for c in color), (r, r), i)
        _glow[key] = s
        if len(_glow) > 300:
            _glow.clear()
    return s


def blit_glow(target, x, y, r, color):
    if isinstance(target, gfx.Canvas):
        k = gfx.K
        g = glow(r * k, color)
        R = g.get_width() / 2
        target.surf.blit(g, (int(x * k - R), int(y * k - R)), special_flags=pygame.BLEND_RGB_ADD)
    else:
        g = glow(r, color)
        target.blit(g, (int(x - r), int(y - r)), special_flags=pygame.BLEND_RGB_ADD)


def make_vignette(w, h, strength=95):
    small = pygame.Surface((160, 90), pygame.SRCALPHA)
    for y in range(90):
        for x in range(160):
            dx = (x - 79.5) / 80
            dy = (y - 44.5) / 45
            d = math.sqrt(dx * dx * 0.9 + dy * dy * 1.1)
            a = max(0.0, d - 0.62) / 0.6
            small.set_at((x, y), (0, 0, 10, int(min(1, a) ** 1.5 * strength)))
    return pygame.transform.smoothscale(small, (w, h))


class Crowd:
    def __init__(self, res, width, data="crowd_night.json", mask_file="crowd_mask_night.png", light=0.82):
        k = gfx.K
        self.k = k
        self.light = light
        mask = pygame.image.load(res("assets", mask_file)).convert_alpha()
        self.lh = mask.get_height()
        self.mask = pygame.transform.smoothscale(mask, (int(mask.get_width() * k), int(mask.get_height() * k)))
        self.layer = pygame.Surface(self.mask.get_size(), pygame.SRCALPHA)
        with open(res("assets", data), encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, list):
            secs, self.oy = d, 95
        else:
            secs, self.oy = d["secs"], d["oy"]
        rnd = random.Random(42)
        self.fans = []
        self.flags = []
        self.sprites = {}
        self.width = width
        for s in secs:
            sc = s.get("sc", 0.78 if s["tier"] == 0 else 0.92)
            step = 10.5 * sc
            rows = []
            y = s["y0"] + 12 * sc
            while y < s["y1"] + 14 * sc:
                rows.append(y)
                y += 11.5 * sc
            for ri, ry in enumerate(rows):
                x = s["x0"] - 4 + (step / 2 if ri % 2 else 0)
                while x < s["x1"] + 6:
                    fx = x + rnd.uniform(-2, 2)
                    key = (s["col"], rnd.choice((0, 0, 0, 1, 2)), rnd.randrange(4),
                           rnd.randrange(5), sc)
                    self.fans.append([fx, ry - self.oy + rnd.uniform(-1.5, 1.5), key,
                                      rnd.uniform(0, 6.28), rnd.uniform(5.5, 9.0),
                                      rnd.uniform(0.25, 0.95), rnd.random() < 0.06,
                                      rnd.random() < 0.18])
                    x += step
            # bayraklar
            if rnd.random() < 0.55:
                px = rnd.uniform(s["x0"] + 30, s["x1"] - 30)
                self.flags.append([px, s["y0"] + 20, s["col"], rnd.uniform(0, 6), sc,
                                   1 if rnd.random() < 0.5 else -1])
        self.t = 0.0
        self.excite = 0.15
        self.target = 0.15
        self.flash = []
        self.wave_x = None
        self.wave_t = 12.0
        self.boost_side = -1

    # ------------------------------------------------------------ sprite
    def _sprite(self, key, pose):
        k = key + (pose,)
        s = self.sprites.get(k)
        if s is not None:
            return s
        col, shade, skin, hair, sc = key
        shirt = TEAM[col][shade]
        team = TEAM[col][0]
        sk = SKINS[skin]
        Q = 3  # once 3 kat buyuk ciz, sonra kucult: kenarlar yumusak olur
        base = pygame.Surface((22 * Q, 34 * Q), pygame.SRCALPHA)
        cx = 11

        def P(x, y):
            return (int(x * Q), int(y * Q))

        def line(c, a_, b_, w):
            pygame.draw.line(base, c, P(*a_), P(*b_), w * Q)

        def circ(c, p, r):
            pygame.draw.circle(base, c, P(*p), r * Q)

        def rect(c, r, rad=0):
            pygame.draw.rect(base, c, (r[0] * Q, r[1] * Q, r[2] * Q, r[3] * Q), 0, border_radius=rad * Q)

        if pose in (1, 2):
            for side in (-1, 1):
                sx, sy = cx + side * 5, 20
                ex, ey = cx + side * 9, 7 if pose == 1 else 6
                line(OUT, (sx, sy), (ex, ey), 5)
                line(shirt, (sx, sy), (ex, ey), 3)
                circ(OUT, (ex, ey), 3)
                circ(sk, (ex, ey), 2)
        rect(OUT, (cx - 7, 18, 14, 16), 5)
        rect(shirt, (cx - 6, 19, 12, 15), 4)
        if shade == 1:
            line(team, (cx - 6, 24), (cx + 5, 24), 3)
        circ(OUT, (cx, 13), 7)
        circ(HAIRS[hair] if hair < 4 else team, (cx, 12), 6)
        circ(sk, (cx, 14), 5)
        # gozler
        circ(OUT, (cx + 2, 14), 1)
        if hair == 4:
            rect(team, (cx - 6, 7, 12, 4), 2)
        if pose == 2:
            rect(OUT, (0, 2, 22, 7), 2)
            rect(team, (1, 3, 20, 5))
            for xx in range(3, 20, 6):
                rect((250, 250, 250), (xx, 3, 2, 5))
        ks = sc * self.k
        base = pygame.transform.smoothscale(base, (max(1, round(22 * ks)), max(1, round(34 * ks))))
        if self.light < 1:
            v = int(255 * self.light)
            base.fill((v, v, min(255, v + 18), 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.sprites[k] = base
        return base

    # ------------------------------------------------------------ guncelle
    def kick(self, amount, side=-1):
        self.target = max(self.target, amount)
        if amount >= 0.9:
            self.excite = 1.0
            self.boost_side = side
        for _ in range(int(amount * 25)):
            self.flash.append([random.uniform(0, self.width), random.uniform(30, self.lh - 20), random.uniform(0.1, 0.25)])

    def update(self, dt):
        self.t += dt
        self.target += (0.15 - self.target) * min(1, dt * 0.35)
        self.excite += (self.target - self.excite) * min(1, dt * 4)
        rate = 1.0 + self.excite ** 2 * 60
        n = rate * dt
        while n > 0:
            if random.random() < n:
                self.flash.append([random.uniform(0, self.width), random.uniform(30, self.lh - 20),
                                   random.uniform(0.08, 0.2)])
            n -= 1
        for f in self.flash:
            f[2] -= dt
        self.flash = [f for f in self.flash if f[2] > 0][-80:]
        if self.wave_x is None:
            self.wave_t -= dt
            if self.wave_t <= 0 and self.excite < 0.35:
                self.wave_x = -80.0
        else:
            self.wave_x += 520 * dt
            if self.wave_x > self.width + 80:
                self.wave_x = None
                self.wave_t = random.uniform(18, 30)

    def draw(self, target):
        L = self.layer
        k = self.k
        ex = self.excite
        self._tick = getattr(self, "_tick", 0) + 1
        if self._tick % 2 == 1:
            self._draw_fans()
        if isinstance(target, gfx.Canvas):
            target.surf.blit(L, (0, int(self.oy * k)))
        else:
            target.blit(L, (0, self.oy))
        self._draw_extras(target, ex)

    def _draw_fans(self):
        L = self.layer
        k = self.k
        L.fill((0, 0, 0, 0))
        t = self.t
        ex = self.excite
        amp = 1.0 + ex * 7.5
        wx = self.wave_x
        for f in self.fans:
            x, y, key, ph, spd, thr, always, scarf = f
            b = abs(math.sin(t * spd + ph))
            up = ex > thr
            jump = amp * b if (up or always) else 0.6 * math.sin(t * 1.3 + ph) + 0.6
            pose = 0
            if up or always:
                pose = 2 if scarf else 1
            if wx is not None and abs(x - wx) < 55:
                k = 1 - abs(x - wx) / 55
                jump = max(jump, 9 * k)
                pose = 1 if k > 0.3 else pose
            img = self._sprite(key, pose)
            L.blit(img, (int(x * k - img.get_width() / 2), int((y - jump) * k - img.get_height())))
        L.blit(self.mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    def _draw_extras(self, target, ex):
        t = self.t
        # bayraklar (tribunun ustune tasar)
        for fl in self.flags:
            px, py, col, ph, sc, d = fl
            wave_amp = 2 + ex * 5
            top = py - 34 * sc - (abs(math.sin(t * 7 + ph)) * ex * 6)
            gd.line(target, (60, 50, 50), (px, py + 10), (px, top), 2)
            Lw, Hh = 34 * sc, 20 * sc
            pts_top, pts_bot = [], []
            for k in range(7):
                u = k / 6
                off = math.sin(t * (6 + ex * 6) + ph - u * 3) * wave_amp * u
                pts_top.append((px + d * Lw * u, top + off))
                pts_bot.append((px + d * Lw * u, top + Hh + off))
            poly = pts_top + pts_bot[::-1]
            gd.polygon(target, TEAM[col][0], poly)
            mid_t = [(x, y + Hh * 0.38) for x, y in pts_top]
            mid_b = [(x, y + Hh * 0.62) for x, y in pts_top]
            gd.polygon(target, (250, 250, 250), mid_t + mid_b[::-1])
            gd.lines(target, OUT, True, poly, 1)
        for x, y, life in self.flash:
            r = 5 + life * 30
            blit_glow(target, x, y + self.oy - 10, r, (255, 255, 235))
