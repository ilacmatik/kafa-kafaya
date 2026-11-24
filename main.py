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

import pygame

import net
import sim

W, H = sim.W, sim.H
FPS = 60
STEP = 1.0 / 60
VERSION = 1
DURATIONS = [60, 90, 120, 180]
LEVELS = ["KOLAY", "NORMAL", "ZOR"]

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
    key = (txt, size, color, outline, ocolor, title)
    s = _tcache.get(key)
    if s is not None:
        return s
    f = get_font(size, title)
    base = f.render(txt, True, color)
    if outline:
        o = f.render(txt, True, ocolor)
        s = pygame.Surface((base.get_width() + outline * 2, base.get_height() + outline * 2), pygame.SRCALPHA)
        for dx, dy in ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)):
            s.blit(o, (outline + dx * outline, outline + dy * outline))
        s.blit(base, (outline, outline))
    else:
        s = base
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
    s = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(s, color, s.get_rect(), 0, border_radius=radius)
    if border:
        pygame.draw.rect(s, border, s.get_rect(), bw, border_radius=radius)
    surf.blit(s, r.topleft)


# ====================================================================== ses
class Sound:
    def __init__(self):
        self.ok = False
        self.muted = False
        self.snd = {}
        self.last = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 2, 512)
            freq, size, ch = pygame.mixer.get_init()
            self.freq, self.ch = freq, ch
            if abs(size) != 16:
                return
            pygame.mixer.set_num_channels(16)
            self._build()
            self.ok = True
        except Exception:
            self.ok = False

    def _mk(self, samples, vol=0.6):
        import array
        a = array.array("h")
        for v in samples:
            v = int(max(-1.0, min(1.0, v * vol)) * 32000)
            for _ in range(self.ch):
                a.append(v)
        return pygame.mixer.Sound(buffer=a.tobytes())

    def _build(self):
        sr = self.freq
        rnd = random.Random(7)

        def n(sec):
            return int(sr * sec)

        def thump(f0, f1, dur, noise=0.3):
            out, ph = [], 0.0
            N = n(dur)
            for i in range(N):
                t = i / N
                f = f0 + (f1 - f0) * t
                ph += 2 * math.pi * f / sr
                env = (1 - t) ** 3
                out.append((math.sin(ph) + noise * (rnd.random() * 2 - 1) * (1 - t) ** 8) * env)
            return out

        def tones(freqs, dur, decay=4.0):
            N = n(dur)
            return [sum(math.sin(2 * math.pi * f * i / sr) for f in freqs) / len(freqs) * math.exp(-decay * i / sr)
                    for i in range(N)]

        def noise(dur, lp=0.1, env=None):
            out, y = [], 0.0
            N = n(dur)
            for i in range(N):
                y += lp * ((rnd.random() * 2 - 1) - y)
                t = i / N
                e = env(t) if env else 1.0
                out.append(y * e)
            m = max(1e-6, max(abs(v) for v in out))
            return [v / m for v in out]

        def whistle(dur):
            N = n(dur)
            out, ph = [], 0.0
            for i in range(N):
                t = i / sr
                f = 2900 + 120 * math.sin(2 * math.pi * 32 * t)
                ph += 2 * math.pi * f / sr
                e = min(1, t * 40) * min(1, (dur - t) * 20)
                out.append(math.sin(ph) * e * 0.6 + (rnd.random() - 0.5) * 0.15 * e)
            return out

        def sweep(f0, f1, dur):
            N = n(dur)
            out, ph = [], 0.0
            for i in range(N):
                t = i / N
                ph += 2 * math.pi * (f0 + (f1 - f0) * t) / sr
                out.append(math.sin(ph) * (1 - t) * min(1, t * 30))
            return out

        def mix(*parts):
            L = max(len(p) for p in parts)
            return [sum(p[i] for p in parts if i < len(p)) for i in range(L)]

        s = self.snd
        s["kick"] = self._mk(thump(150, 55, 0.16, 0.6), 0.9)
        s["head"] = self._mk(thump(260, 130, 0.11, 0.3), 0.7)
        s["bounce"] = self._mk(thump(110, 70, 0.09, 0.2), 0.45)
        s["post"] = self._mk(tones([880, 1320, 2093], 0.45, 7), 0.5)
        s["whistle"] = self._mk(whistle(0.45), 0.45)
        s["end"] = self._mk(whistle(0.25) + [0] * n(0.08) + whistle(0.25) + [0] * n(0.08) + whistle(0.7), 0.45)
        crowd = noise(2.2, 0.08, lambda t: min(1, t * 6) * (1 - t) ** 1.2)
        horn = [v * 0.5 for v in tones([233, 293, 349], 1.2, 1.2)]
        s["goal"] = self._mk(mix(crowd, horn), 0.75)
        s["super_fire"] = self._mk(mix(noise(0.6, 0.35, lambda t: (1 - t) ** 2), sweep(200, 900, 0.5)), 0.6)
        s["super_ice"] = self._mk(mix(tones([1568, 2093, 2637], 0.6, 5), sweep(1200, 400, 0.4)), 0.5)
        s["freeze"] = self._mk(noise(0.35, 0.9, lambda t: (1 - t) ** 3), 0.4)
        s["fire_hit"] = self._mk(mix(thump(90, 40, 0.3, 0.9), noise(0.3, 0.5, lambda t: (1 - t) ** 2)), 0.8)
        s["pu"] = self._mk(sweep(500, 500, 0.07) + sweep(750, 750, 0.07) + sweep(1000, 1000, 0.12), 0.4)
        s["pu_spawn"] = self._mk(tones([1318, 1760], 0.25, 9), 0.3)
        s["jump"] = self._mk(sweep(300, 520, 0.09), 0.18)
        s["swing"] = self._mk(noise(0.12, 0.25, lambda t: math.sin(t * math.pi)), 0.18)
        s["shield"] = self._mk(tones([660, 990], 0.3, 8), 0.45)
        s["block"] = self._mk(thump(200, 80, 0.2, 0.8), 0.8)
        s["armed"] = self._mk(sweep(300, 1200, 0.3), 0.35)
        s["click"] = self._mk(sweep(900, 700, 0.05), 0.3)
        s["golden"] = self._mk(tones([523, 659, 784, 1046], 0.9, 2), 0.5)
        amb = noise(4.0, 0.05)
        fade = n(0.3)
        amb = [v * min(1, i / fade, (len(amb) - i) / fade) for i, v in enumerate(amb)]
        s["crowd"] = self._mk(amb, 0.10)

    def play(self, name, gap=0.05):
        if not self.ok or self.muted or name not in self.snd:
            return
        now = time.time()
        if now - self.last.get(name, 0) < gap:
            return
        self.last[name] = now
        self.snd[name].play()

    def ambience(self, on):
        if not self.ok:
            return
        self.snd["crowd"].stop()
        if on and not self.muted:
            self.snd["crowd"].play(loops=-1)

    def toggle(self):
        self.muted = not self.muted
        if self.ok:
            if self.muted:
                pygame.mixer.stop()


# ====================================================================== gorseller
class Assets:
    def __init__(self):
        L = lambda f: pygame.image.load(res("assets", f))
        self.stadium = L("stadium.jpg").convert()
        mb = L("menu_bg.jpg").convert()
        dark = pygame.Surface((W, H), pygame.SRCALPHA)
        dark.fill((10, 15, 40, 120))
        mb.blit(dark, (0, 0))
        self.menu_bg = mb
        self.idle, self.kick, self.idle_ice, self.kick_ice = [], [], [], []
        self.big, self.portrait = [], []
        self.kick_anchor = []
        for i in range(6):
            idle = L("p%d_idle.png" % i).convert_alpha()
            kick = L("p%d_kick.png" % i).convert_alpha()
            sc = sim.CHARACTERS[i]["scale"]
            f = sim.BASE_H * sc / idle.get_height()
            iw = pygame.transform.smoothscale(idle, (round(idle.get_width() * f), round(idle.get_height() * f)))
            kw = pygame.transform.smoothscale(kick, (round(kick.get_width() * f), round(kick.get_height() * f)))
            self.idle.append(iw)
            self.kick.append(kw)
            self.idle_ice.append(self._ice(iw))
            self.kick_ice.append(self._ice(kw))
            self.kick_anchor.append(0.40)
            bh = 215
            self.big.append(pygame.transform.smoothscale(idle, (round(idle.get_width() * bh / idle.get_height()), bh)))
            head = idle.subsurface(pygame.Rect(0, 0, idle.get_width(), int(idle.get_height() * 0.45))).copy()
            ph = 58
            self.portrait.append(pygame.transform.smoothscale(head, (round(head.get_width() * ph / head.get_height()), ph)))
        d = sim.BALL_R * 2 + 2
        self.ball = pygame.transform.smoothscale(L("ball.png").convert_alpha(), (d, d))
        self.ball_fire = self._fit(L("ball_fire.png").convert_alpha(), int(d * 1.45))
        self.ball_ice = self._fit(L("ball_ice.png").convert_alpha(), int(d * 1.45))
        self.fx_fire = self._fit(L("fx_fire.png").convert_alpha(), 150)
        self.fx_ice = self._fit(L("fx_ice.png").convert_alpha(), 140)
        self.ice_block = self._fit(L("fx_ice.png").convert_alpha(), 120)
        self.pu = {k: self._fit(L(f).convert_alpha(), 66) for k, f in
                   (("speed", "pu_speed.png"), ("jump", "pu_jump.png"), ("shield", "pu_shield.png"),
                    ("freeze", "pu_freeze.png"), ("gold", "orb_gold.png"))}
        self.pu_small = {k: pygame.transform.smoothscale(v, (30, 30)) for k, v in self.pu.items()}
        self.flag = self._fit(L("flag.png").convert_alpha(), 70)
        self.icon_fire = self._fit(L("ball_fire.png").convert_alpha(), 30)
        self.icon_ice = self._fit(L("ball_ice.png").convert_alpha(), 30)
        self._flip_cache = {}

    @staticmethod
    def _fit(img, size):
        w, h = img.get_size()
        f = size / max(w, h)
        return pygame.transform.smoothscale(img, (max(1, round(w * f)), max(1, round(h * f))))

    @staticmethod
    def _ice(img):
        s = img.copy()
        s.fill((150, 200, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
        s.fill((40, 70, 110, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return s

    def flipped(self, img):
        k = id(img)
        f = self._flip_cache.get(k)
        if f is None:
            f = pygame.transform.flip(img, True, False)
            self._flip_cache[k] = f
        return f


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


class Button:
    def __init__(self, rect, text, cb, color=(40, 120, 230)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.cb = cb
        self.color = color

    def draw(self, s, hot, t):
        r = self.rect.copy()
        if hot:
            r.inflate_ip(14 + 4 * math.sin(t * 6), 8)
        sh = r.move(0, 6)
        pygame.draw.rect(s, (10, 14, 30), sh, 0, border_radius=18)
        c = tuple(min(255, int(v * (1.25 if hot else 1))) for v in self.color)
        pygame.draw.rect(s, c, r, 0, border_radius=18)
        hl = pygame.Rect(r.x + 6, r.y + 4, r.w - 12, r.h // 2 - 4)
        hs = pygame.Surface(hl.size, pygame.SRCALPHA)
        pygame.draw.rect(hs, (255, 255, 255, 50), hs.get_rect(), 0, border_radius=14)
        s.blit(hs, hl.topleft)
        pygame.draw.rect(s, GOLD if hot else (230, 235, 255), r, 4, border_radius=18)
        draw_text(s, self.text, 30, r.center)


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


def draw_title(s, y, t, size=86):
    bob = math.sin(t * 2.2) * 4
    draw_text(s, "KAFA KAFAYA", size, (W // 2, y + bob), GOLD, outline=6)
    draw_text(s, "F U T B O L", 26, (W // 2, y + size * 0.62 + bob), WHITE, outline=3)


class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        a = app
        x = W // 2 - 190
        mk = lambda i, txt, cb, col=(40, 120, 230): Button((x, 238 + i * 72, 380, 58), txt, cb, col)
        self.list = ButtonList([
            mk(0, "MAÇ KUR", lambda: a.go(HostWaitScene(a)), (230, 110, 30)),
            mk(1, "MAÇA KATIL", lambda: a.go(JoinScene(a)), (230, 110, 30)),
            mk(2, "BİLGİSAYARA KARŞI", lambda: a.go(SelectScene(a, "bot"))),
            mk(3, "TEK PC 2 KİŞİ", lambda: a.go(SelectScene(a, "local2"))),
            mk(4, "KONTROLLER", lambda: a.go(HelpScene(a)), (70, 80, 110)),
            mk(5, "ÇIKIŞ", a.quit, (150, 40, 50)),
        ])
        self.t = 0
        self.balls = [[random.uniform(0, W), random.uniform(-H, 0), random.uniform(-40, 40), random.uniform(0, 6)]
                      for _ in range(6)]

    def handle(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.quit()
            return
        self.list.handle(e, self.app)

    def update(self, dt):
        self.t += dt
        for b in self.balls:
            b[1] += 160 * dt
            b[0] += b[2] * dt
            b[3] += dt * 3
            if b[1] > H + 40:
                b[0], b[1] = random.uniform(0, W), -40

    def draw(self, s):
        A = self.app.assets
        s.blit(A.menu_bg, (0, 0))
        for b in self.balls:
            img = pygame.transform.rotate(A.ball, -math.degrees(b[3]))
            img.set_alpha(110)
            s.blit(img, img.get_rect(center=(b[0], b[1])))
        l = A.big[0]
        r = A.flipped(A.big[1])
        s.blit(l, l.get_rect(midbottom=(210, 640 + math.sin(self.t * 3) * 6)))
        s.blit(r, r.get_rect(midbottom=(W - 210, 640 + math.sin(self.t * 3 + 1.5) * 6)))
        draw_title(s, 120, self.t)
        self.list.draw(s, 1 / FPS)
        draw_text(s, "F11: tam ekran   M: ses aç/kapa", 18, (W // 2, H - 20), (200, 210, 230), outline=2, title=False)


class HelpScene(Scene):
    def handle(self, e):
        if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.app.go(MenuScene(self.app))

    def draw(self, s):
        s.blit(self.app.assets.menu_bg, (0, 0))
        panel(s, (140, 60, W - 280, H - 120), (10, 15, 35, 220), 24, GOLD)
        draw_text(s, "KONTROLLER", 50, (W // 2, 110), GOLD, outline=4)
        rows = [
            ("İKİ PC / BİLGİSAYARA KARŞI", None),
            ("Hareket", "A / D  veya  ← / →"),
            ("Zıpla", "W  veya  ↑"),
            ("Şut", "BOŞLUK"),
            ("Süper güç", "S  veya  ↓  (bar dolunca)"),
            ("TEK PC 2 KİŞİ", None),
            ("1. Oyuncu", "A/D hareket, W zıpla, BOŞLUK şut, S süper"),
            ("2. Oyuncu", "←/→ hareket, ↑ zıpla, ENTER şut, ↓ süper"),
        ]
        y = 170
        for a, b in rows:
            if b is None:
                draw_text(s, a, 26, (W // 2, y), (255, 170, 60), outline=3)
                y += 44
            else:
                draw_text(s, a, 24, (W // 2 - 170, y), WHITE, anchor="midright", outline=2, title=False)
                draw_text(s, b, 24, (W // 2 - 140, y), (180, 230, 255), anchor="midleft", outline=2, title=False)
                y += 38
        draw_text(s, "Topu güç simgelerine çarptır: HIZ, ZIPLAMA, BUZ KALKAN, DONDURMA, SÜPER", 20,
                  (W // 2, y + 18), (255, 230, 150), outline=2, title=False)
        draw_text(s, "Süper şut rakibe gelirken tam zamanında ŞUT tuşuna basarak karşılanabilir!", 20,
                  (W // 2, y + 48), (255, 230, 150), outline=2, title=False)
        draw_text(s, "Geri dönmek için bir tuşa bas", 22, (W // 2, H - 90), (200, 210, 230), outline=2, title=False)


class MessageScene(Scene):
    def __init__(self, app, title, msg):
        super().__init__(app)
        self.title, self.msg = title, msg

    def handle(self, e):
        if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.app.go(MenuScene(self.app))

    def draw(self, s):
        s.blit(self.app.assets.menu_bg, (0, 0))
        panel(s, (240, 220, W - 480, 260), (10, 15, 35, 230), 24, (255, 90, 90))
        draw_text(s, self.title, 44, (W // 2, 285), (255, 120, 110), outline=4)
        y = 350
        for line in self.msg.split("\n"):
            draw_text(s, line, 22, (W // 2, y), WHITE, outline=2, title=False)
            y += 32
        draw_text(s, "Devam etmek için bir tuşa bas", 20, (W // 2, 450), (190, 200, 220), outline=2, title=False)


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
        s.blit(self.app.assets.menu_bg, (0, 0))
        draw_title(s, 80, self.t, 64)
        panel(s, (200, 180, W - 400, 420), (10, 15, 35, 225), 24, GOLD)
        if self.host.error:
            draw_text(s, "MAÇ KURULAMADI", 40, (W // 2, 240), (255, 110, 100), outline=4)
            draw_text(s, self.host.error, 20, (W // 2, 300), WHITE, outline=2, title=False)
            draw_text(s, "Oyun zaten açık olabilir. ESC ile geri dön.", 22, (W // 2, 350), WHITE, outline=2,
                      title=False)
            return
        dots = "." * (int(self.t * 2) % 4)
        draw_text(s, "RAKİP BEKLENİYOR" + dots, 40, (W // 2 - 0, 235), WHITE, outline=4)
        # donen top
        img = pygame.transform.rotate(self.app.assets.ball, -self.t * 300)
        s.blit(img, img.get_rect(center=(W // 2, 300)))
        draw_text(s, "Bu bilgisayarın IP adresi:", 24, (W // 2, 355), (190, 210, 235), outline=2, title=False)
        ip_txt = "   /   ".join(self.ips[:3]) if self.ips else "Ağ bağlantısı bulunamadı!"
        draw_text(s, ip_txt, 44, (W // 2, 400), GOLD, outline=4)
        draw_text(s, "Diğer PC'de  MAÇA KATIL  seçin. Maç listede otomatik görünür,", 20, (W // 2, 455),
                  WHITE, outline=2, title=False)
        draw_text(s, "görünmezse yukarıdaki IP adresini yazarak bağlanın.", 20, (W // 2, 482), WHITE, outline=2,
                  title=False)
        draw_text(s, "MAÇ SÜRESİ:  <  %d sn  >" % DURATIONS[self.dur_i], 28, (W // 2, 545), (120, 220, 255),
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
        s.blit(self.app.assets.menu_bg, (0, 0))
        draw_title(s, 70, self.t, 56)
        panel(s, (200, 150, W - 400, 500), (10, 15, 35, 225), 24, GOLD)
        draw_text(s, "AĞDAKİ MAÇLAR", 32, (W // 2, 190), WHITE, outline=3)
        hosts = self.finder.hosts()
        self.rows = []
        if not hosts:
            dots = "." * (int(self.t * 2) % 4)
            draw_text(s, "Aranıyor" + dots, 24, (W // 2, 250), (180, 190, 210), outline=2, title=False)
        for i, (ip, name, port) in enumerate(hosts[:4]):
            r = pygame.Rect(W // 2 - 300, 225 + i * 56, 600, 48)
            hot = i == self.sel and not self.ip
            pygame.draw.rect(s, (230, 110, 30) if hot else (40, 60, 110), r, 0, border_radius=12)
            pygame.draw.rect(s, GOLD if hot else (120, 140, 190), r, 3, border_radius=12)
            draw_text(s, "%s   (%s)" % (name, ip), 24, r.center, WHITE, outline=2)
            self.rows.append((r, ip))
        y = 470
        draw_text(s, "veya IP adresini yaz:", 22, (W // 2, y), (190, 210, 235), outline=2, title=False)
        box = pygame.Rect(W // 2 - 200, y + 22, 400, 56)
        pygame.draw.rect(s, (245, 245, 250), box, 0, border_radius=12)
        pygame.draw.rect(s, GOLD, box, 4, border_radius=12)
        cur = "|" if int(self.t * 2) % 2 == 0 else " "
        f = get_font(34, True)
        ts = f.render(self.ip + cur, True, DARK)
        s.blit(ts, ts.get_rect(center=box.center))
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
        self.cards = [pygame.Rect(48 + i * 202, 150, 182, 330) for i in range(6)]

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
        s.blit(A.menu_bg, (0, 0))
        draw_text(s, "KARAKTERİNİ SEÇ", 52, (W // 2, 70), GOLD, outline=5)
        labels = {"bot": ("SEN", "BİLGİSAYAR"), "local2": ("1. OYUNCU", "2. OYUNCU"),
                  "host": ("SEN", "RAKİP"), "client": ("RAKİP", "SEN")}[self.mode]
        for i, r in enumerate(self.cards):
            sel0 = self.pick[0] == i
            sel1 = self.pick[1] == i
            hot = sel0 or sel1
            rr = r.inflate(10, 10) if hot else r
            panel(s, rr, (25, 35, 70, 225) if hot else (15, 20, 40, 200), 18)
            if sel0 and sel1:
                pygame.draw.rect(s, P_COLORS[0], rr, 5, border_radius=18)
                pygame.draw.rect(s, P_COLORS[1], rr.inflate(-10, -10), 4, border_radius=14)
            elif sel0 or sel1:
                pygame.draw.rect(s, P_COLORS[0 if sel0 else 1], rr, 5, border_radius=18)
            else:
                pygame.draw.rect(s, (70, 80, 120), rr, 2, border_radius=18)
            img = A.big[i]
            bob = math.sin(self.t * 4 + i) * 3 if hot else 0
            s.blit(img, img.get_rect(midbottom=(r.centerx, r.y + 238 + bob)))
            draw_text(s, sim.DISPLAY_NAMES[i], 26, (r.centerx, r.y + 258), WHITE, outline=3)
            for j, (lab, val) in enumerate(zip(("HIZ", "ZIPLA", "ŞUT"), sim.STAT_BARS[i])):
                y = r.y + 284 + j * 15
                draw_text(s, lab, 12, (r.x + 14, y), (200, 210, 230), anchor="midleft", outline=1, title=False)
                for k in range(5):
                    c = GOLD if k < val else (60, 70, 100)
                    pygame.draw.rect(s, c, (r.x + 70 + k * 20, y - 5, 17, 10), 0, border_radius=3)
            ic = A.icon_fire if sim.CHARACTERS[i]["power"] == "fire" else A.icon_ice
            s.blit(ic, ic.get_rect(center=(r.right - 22, r.y + 22)))
            if sel0:
                tag = pygame.Rect(0, 0, 112, 30)
                tag.midbottom = (r.centerx - (30 if sel1 else 0), rr.y + 2)
                pygame.draw.rect(s, P_COLORS[0], tag, 0, border_radius=10)
                draw_text(s, labels[0], 16, tag.center, outline=2)
            if sel1:
                tag = pygame.Rect(0, 0, 112, 30)
                tag.midbottom = (r.centerx + (30 if sel0 else 0), rr.y + 2 - (32 if sel0 else 0))
                pygame.draw.rect(s, P_COLORS[1], tag, 0, border_radius=10)
                draw_text(s, labels[1], 16, tag.center, outline=2)
        # hazir durumu
        y = 540
        for who in (0, 1):
            x = W // 2 - 300 if who == 0 else W // 2 + 300
            if self.mode == "bot" and who == 1:
                txt, col = "ZORLUK: %s  (Z)" % LEVELS[self.level], (255, 200, 120)
            elif self.ready[who]:
                txt, col = "%s: HAZIR!" % labels[who], (120, 255, 140)
            else:
                txt, col = "%s: seçiyor..." % labels[who], (220, 220, 230)
            draw_text(s, txt, 26, (x, y), col, outline=3)
        pw = sim.CHARACTERS[self.pick[self.me]]["power"]
        draw_text(s, "Süper gücün: %s" % ("ATEŞ ŞUTU (rakibi savurur)" if pw == "fire" else "BUZ ŞUTU (rakibi dondurur)"),
                  22, (W // 2, 590), FIRE_C if pw == "fire" else ICE_C, outline=2, title=False)
        if self.mode == "local2":
            hint = "1. oyuncu: A/D seç, BOŞLUK hazır    2. oyuncu: ←/→ seç, ENTER hazır"
        elif self.mode == "bot":
            hint = "←/→ seç, ENTER hazır    ↑/↓ rakip karakteri    Z zorluk    T süre"
        else:
            hint = "←/→ seç, ENTER hazır" + ("    T süre" if self.mode == "host" else "")
        draw_text(s, hint, 20, (W // 2, 635), (200, 210, 230), outline=2, title=False)
        draw_text(s, "Maç süresi: %d sn%s     ESC: geri" % (self.dur, "  (T)" if self.mode != "client" else ""), 20,
                  (W // 2, 668), (200, 210, 230), outline=2, title=False)


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
        self.frame = pygame.Surface((W, H))
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

    def _burst(self, x, y, n, colors, speed=300, life=0.6, size=5, g=600, kind="dot"):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(0.3, 1) * speed
            self.parts.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v - speed * 0.3,
                                       random.uniform(0.5, 1) * life, random.choice(colors), size, g, kind))

    def _process(self, snap):
        snd = self.app.sound
        bx, by = snap["b"][0], snap["b"][1]
        ph = snap["ph"]
        if ph != self.prev_phase:
            if ph == "ready":
                self._say("HAZIR", WHITE, 1.2)
            elif ph == "play" and self.prev_phase == "ready":
                self._say("BAŞLA!", GOLD, 0.8)
            elif ph == "over":
                pass
            self.prev_phase = ph
        for ev in snap.get("ev", []):
            name = ev.split(":")[0]
            if name in ("kick", "head", "bounce", "post", "whistle", "super_fire", "super_ice", "freeze",
                        "fire_hit", "jump", "swing", "shield", "block", "armed", "end", "golden", "pu_spawn"):
                snd.play(name, 0.08 if name in ("head", "bounce") else 0.04)
            if name == "kick":
                self._burst(bx, by, 8, [(255, 255, 255), (220, 230, 200)], 220, 0.4, 4)
            elif name == "head":
                self._burst(bx, by, 5, [(255, 255, 255)], 160, 0.3, 3)
            elif name == "bounce" and by > sim.GROUND - 40:
                self._burst(bx, sim.GROUND, 6, [(150, 120, 80), (110, 160, 70)], 140, 0.4, 4, 500)
            elif name == "post":
                self._burst(bx, by, 10, [(255, 255, 200), GOLD], 260, 0.4, 3)
            elif name == "goal":
                snd.play("goal", 0)
                who = snap.get("scr", 0)
                gx = W - 40 if who == 0 else 40
                for _ in range(3):
                    self._burst(gx, sim.GOAL_TOP + 40, 40,
                                [(255, 80, 80), (80, 160, 255), GOLD, (120, 255, 120), WHITE], 650, 1.6, 7, 500,
                                "confetti")
                if self.mode == "local2":
                    msg = "%d. OYUNCU" % (who + 1)
                elif who == self.me:
                    msg = "SEN ATTIN!"
                else:
                    msg = "RAKİP ATTI"
                self._say("GOOOL!", GOLD, 2.2)
                self.floaters.append([msg, W // 2, 330, 2.0, P_COLORS[who]])
                self.shake = 0.5
            elif name in ("super_fire", "super_ice"):
                c = [FIRE_C, (255, 220, 80)] if name == "super_fire" else [ICE_C, WHITE]
                self._burst(bx, by, 26, c, 420, 0.6, 6)
                self.shake = max(self.shake, 0.25)
            elif name == "fire_hit":
                self._burst(bx, by, 30, [FIRE_C, (255, 60, 30), (255, 230, 90)], 500, 0.7, 7)
                self.shake = 0.35
            elif name == "freeze":
                for p in snap["p"]:
                    pass
                self._burst(bx, by, 24, [ICE_C, WHITE], 380, 0.7, 5, 300, "shard")
            elif name == "block":
                self._burst(bx, by, 18, [WHITE, GOLD], 380, 0.5, 5)
                self.floaters.append(["KURTARIŞ!", bx, by - 40, 1.2, WHITE])
            elif name == "shield":
                self._burst(bx, by, 14, [ICE_C, WHITE], 260, 0.5, 4, 200, "shard")
            elif name == "golden":
                self._say("ALTIN GOL!", GOLD, 2.2)
            elif name == "pu":
                _, kind, who = ev.split(":")
                snd.play("pu", 0)
                who = int(who)
                p = snap["p"][who]
                self.floaters.append([PU_TEXT.get(kind, kind), p[0], p[1] - 200, 1.6, P_COLORS[who]])
                self._burst(bx, by, 20, [GOLD, WHITE, (120, 255, 200)], 300, 0.6, 5)
            elif name == "armed":
                pass
            elif name == "land":
                pass
        self.shake = max(self.shake, snap.get("shk", 0) or 0)

    def _update_fx(self, dt):
        for p in self.parts:
            p.vy += p.g * dt
            if p.kind == "confetti":
                p.vx *= (1 - 2.0 * dt)
                p.vy = min(p.vy, 160)
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.rot += p.vr * dt
            p.life -= dt
        self.parts = [p for p in self.parts if p.life > 0 and p.y < H + 20]
        if len(self.parts) > 600:
            self.parts = self.parts[-600:]
        if self.banner:
            self.banner[2] -= dt
            if self.banner[2] <= 0:
                self.banner = None
        for f in self.floaters:
            f[2] -= 40 * dt
            f[3] -= dt
        self.floaters = [f for f in self.floaters if f[3] > 0]
        self.shake = max(0.0, self.shake - dt)
        # super/ates izleri
        if self.snap:
            b = self.snap["b"]
            if b[3] == 1:
                for _ in range(3):
                    self.parts.append(Particle(b[0] + random.uniform(-10, 10), b[1] + random.uniform(-10, 10),
                                               random.uniform(-60, 60), random.uniform(-90, 0), 0.35,
                                               random.choice([FIRE_C, (255, 220, 80), (255, 80, 30)]), 6, -100))
            elif b[3] == 2:
                for _ in range(2):
                    self.parts.append(Particle(b[0] + random.uniform(-12, 12), b[1] + random.uniform(-12, 12),
                                               random.uniform(-40, 40), random.uniform(-40, 40), 0.45,
                                               random.choice([ICE_C, WHITE]), 4, 0, "shard"))
            for p in self.snap["p"]:
                if p[10] > 0 and abs(p[2]) > 100 and p[8]:
                    self.parts.append(Particle(p[0] - (12 if p[2] > 0 else -12), p[1] - random.uniform(5, 60),
                                               -p[2] * 0.2, 0, 0.25, (255, 230, 120), 3, 0))

    # -------------------------------------------------- cizim
    def draw(self, screen):
        A = self.app.assets
        s = self.frame
        s.blit(A.stadium, (0, 0))
        snap = self.snap
        if snap is None:
            screen.blit(s, (0, 0))
            draw_text(screen, "Bağlanıyor...", 40, (W // 2, H // 2), WHITE)
            return
        self._draw_goal_back(s, snap)
        # golgeler
        b = snap["b"]
        for x, y, wdt in [(p[0], p[1], 70) for p in snap["p"]] + [(b[0], b[1], 40)]:
            hgt = max(0.0, sim.GROUND - y)
            k = max(0.25, 1 - hgt / 420)
            sh = pygame.Surface((int(wdt * k) + 2, int(14 * k) + 2), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, int(90 * k)), sh.get_rect())
            s.blit(sh, sh.get_rect(center=(x, sim.GROUND + 2)))
        # guc simgesi
        if snap.get("pu"):
            kind, px, py, life = snap["pu"]
            img = A.pu.get(kind)
            if img and (life > 2 or int(self.t * 8) % 2 == 0):
                bob = math.sin(self.t * 3) * 8
                glow = pygame.Surface((110, 110), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 255, 200, int(60 + 40 * math.sin(self.t * 6))), (55, 55), 50)
                s.blit(glow, glow.get_rect(center=(px, py + bob)))
                s.blit(img, img.get_rect(center=(px, py + bob)))
        for i, p in enumerate(snap["p"]):
            self._draw_player(s, i, p)
        self._draw_ball(s, b)
        self._draw_goal_front(s, snap)
        # parcaciklar
        for p in self.parts:
            a = max(0.0, min(1.0, p.life / p.max))
            if p.kind == "confetti":
                r = pygame.Rect(0, 0, p.size, int(p.size * 1.6 * abs(math.cos(math.radians(p.rot)))) + 1)
                r.center = (p.x, p.y)
                pygame.draw.rect(s, p.color, r)
            elif p.kind == "shard":
                pts = [(p.x + math.cos(math.radians(p.rot + k * 120)) * p.size * (1.6 if k == 0 else 0.7),
                        p.y + math.sin(math.radians(p.rot + k * 120)) * p.size * (1.6 if k == 0 else 0.7))
                       for k in range(3)]
                pygame.draw.polygon(s, p.color, pts)
            else:
                rad = max(1, int(p.size * (0.4 + 0.6 * a)))
                pygame.draw.circle(s, p.color, (int(p.x), int(p.y)), rad)
        self._draw_hud(s, snap)
        ox = oy = 0
        if self.shake > 0:
            m = 10 * min(1, self.shake * 2.5)
            ox, oy = random.uniform(-m, m), random.uniform(-m, m)
        screen.fill((0, 0, 0))
        screen.blit(s, (ox, oy))
        self._draw_overlays(screen, snap)

    def _draw_goal_back(self, s, snap):
        GD, GT, GR = sim.GOAL_D, sim.GOAL_TOP, sim.GROUND
        net = pygame.Surface((GD, GR - GT), pygame.SRCALPHA)
        net.fill((255, 255, 255, 28))
        for x in range(0, GD, 14):
            pygame.draw.line(net, (255, 255, 255, 120), (x, 0), (x, GR - GT), 2)
        for y in range(0, GR - GT, 14):
            pygame.draw.line(net, (255, 255, 255, 120), (0, y), (GD, y), 2)
        s.blit(net, (0, GT))
        s.blit(net, (W - GD, GT))
        # arka direk
        for x in (6, W - 6):
            pygame.draw.line(s, (200, 200, 210), (x, GT), (x, GR), 6)
        for i in range(2):
            if snap["sh"][i] > 0:
                x = sim.GOAL_D + 2 if i == 0 else W - sim.GOAL_D - 2
                wall = pygame.Surface((22, GR - GT), pygame.SRCALPHA)
                al = 150 if snap["sh"][i] > 1.5 or int(self.t * 10) % 2 else 60
                wall.fill((140, 220, 255, al))
                s.blit(wall, wall.get_rect(midtop=(x, GT)))
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
            pygame.draw.rect(s, (30, 30, 40), roof.inflate(4, 4), 0, border_radius=6)
            pygame.draw.rect(s, (245, 245, 250), roof, 0, border_radius=6)
            pygame.draw.line(s, (30, 30, 40), (postx, GT - 2), (postx, GR), 12)
            pygame.draw.line(s, (245, 245, 250), (postx, GT - 2), (postx, GR), 8)
            pygame.draw.line(s, (255, 90, 90), (postx, GT + 20), (postx, GT + 40), 8)
            pygame.draw.line(s, (255, 90, 90), (postx, GT + 70), (postx, GT + 90), 8)

    def _draw_player(self, s, i, p):
        A = self.app.assets
        x, y, vx, face, kick_t, frozen, meter, armed, on_ground, char, speed_t, jump_t, stun, run_t = p
        kicking = kick_t > 0.04
        if frozen > 0:
            img = A.kick_ice[char] if kicking else A.idle_ice[char]
        else:
            img = A.kick[char] if kicking else A.idle[char]
        flip = face < 0
        if flip:
            img = A.flipped(img)
        tilt = 0
        bob = 0
        if on_ground and abs(vx) > 40 and frozen <= 0:
            bob = abs(math.sin(run_t * 14)) * 5
            tilt = math.sin(run_t * 14) * 4
        if stun > 0:
            tilt = math.sin(self.t * 30) * 12
        if not on_ground and not kicking:
            tilt = -6 * face if vx * face > 0 else 0
        # super aura
        if armed > 0:
            pw = sim.CHARACTERS[char]["power"]
            c = FIRE_C if pw == "fire" else ICE_C
            aura = pygame.Surface((180, 220), pygame.SRCALPHA)
            r = 80 + math.sin(self.t * 12) * 8
            pygame.draw.ellipse(aura, c + (70,), pygame.Rect(90 - r * 0.8, 110 - r, r * 1.6, r * 2))
            pygame.draw.ellipse(aura, c + (140,), pygame.Rect(90 - r * 0.8, 110 - r, r * 1.6, r * 2), 4)
            s.blit(aura, aura.get_rect(center=(x, y - 82)))
        if tilt:
            img = pygame.transform.rotate(img, -tilt * (1 if not flip else -1))
        rect = img.get_rect()
        if kicking:
            ax = A.kick_anchor[char]
            rect.bottom = int(y - bob)
            if flip:
                rect.left = int(x - rect.w * (1 - ax))
            else:
                rect.left = int(x - rect.w * ax)
        else:
            rect.midbottom = (int(x), int(y - bob))
        s.blit(img, rect)
        if frozen > 0:
            ice = A.fx_ice
            s.blit(ice, ice.get_rect(center=(x, y - 70)))
            draw_text(s, "%.1f" % frozen, 18, (x, y - 175), ICE_C, outline=2)
        if stun > 0:
            for k in range(3):
                a = self.t * 8 + k * 2.1
                pygame.draw.circle(s, GOLD, (int(x + math.cos(a) * 26), int(y - 170 + math.sin(a) * 8)), 5)
        if jump_t > 0:
            pygame.draw.ellipse(s, (120, 255, 160), (x - 30, y - 6, 60, 12), 3)
        # isaretci
        label = None
        if self.mode == "local2":
            label = "P%d" % (i + 1)
        elif i == self.me:
            label = "SEN"
        if label:
            ty = y - (sim.BASE_H * sim.CHARACTERS[char]["scale"]) - 26 + math.sin(self.t * 5) * 3
            pygame.draw.polygon(s, P_COLORS[i], [(x - 9, ty + 10), (x + 9, ty + 10), (x, ty + 20)])
            draw_text(s, label, 18, (x, ty), P_COLORS[i], outline=3)

    def _draw_ball(self, s, b):
        A = self.app.assets
        x, y, ang, mode, vx, vy = b
        if mode in (1, 2):
            sp = math.hypot(vx, vy) or 1
            dx, dy = -vx / sp, -vy / sp
            trail = A.fx_fire if mode == 1 else A.fx_ice
            a = math.degrees(math.atan2(-dy, dx))
            tr = pygame.transform.rotate(trail, a)
            L = trail.get_width() * 0.38
            s.blit(tr, tr.get_rect(center=(x + dx * L, y + dy * L)))
            img = A.ball_fire if mode == 1 else A.ball_ice
        else:
            img = A.ball
        img = pygame.transform.rotate(img, -math.degrees(ang) % 360)
        s.blit(img, img.get_rect(center=(int(x), int(y))))

    def _draw_hud(self, s, snap):
        A = self.app.assets
        sc = snap["sc"]
        # skor tablosu
        cx = W // 2
        board = pygame.Rect(cx - 230, 10, 460, 78)
        panel(s, board, (12, 16, 34, 235), 18, GOLD, 4)
        tm = snap["tm"]
        if snap["gg"]:
            tt, tc = "ALTIN GOL", GOLD
        else:
            sec = max(0, int(math.ceil(tm)))
            tt, tc = "%d:%02d" % (sec // 60, sec % 60), (255, 90, 80) if sec <= 10 else WHITE
        timer = pygame.Rect(0, 0, 120 if not snap["gg"] else 150, 44)
        timer.center = (cx, board.centery)
        pygame.draw.rect(s, (40, 46, 70), timer, 0, border_radius=12)
        pygame.draw.rect(s, (90, 100, 140), timer, 2, border_radius=12)
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
            pygame.draw.circle(s, P_COLORS[i], circ.center, 40)
            pygame.draw.circle(s, (12, 16, 34), circ.center, 35)
            s.blit(por, por.get_rect(center=(px, board.centery + 2)))
            pygame.draw.circle(s, GOLD, circ.center, 40, 3)
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
            pygame.draw.rect(s, (12, 16, 34), bar.inflate(6, 6), 0, border_radius=8)
            fill = bar.copy()
            fill.w = int(bw * meter / 100)
            if i == 1:
                fill.right = bar.right
            full = meter >= 100 or armed > 0
            fc = col if not full else tuple(min(255, int(c * (1 + 0.3 * math.sin(self.t * 10)))) for c in col)
            if fill.w > 0:
                pygame.draw.rect(s, fc, fill, 0, border_radius=6)
            pygame.draw.rect(s, (230, 230, 240), bar.inflate(6, 6), 2, border_radius=8)
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
        if snap["ph"] == "ready" and snap["pt"] > 0 and self.banner is None:
            draw_text(s, str(int(math.ceil(snap["pt"]))), 80, (W // 2, 180), WHITE, outline=6)
        if snap["ph"] == "over":
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((5, 8, 20, 150))
            s.blit(dim, (0, 0))
            win = snap["win"]
            if win == 2:
                t, c = "BERABERE", WHITE
            elif self.mode == "local2":
                t, c = "%d. OYUNCU KAZANDI!" % (win + 1), P_COLORS[win]
            elif win == self.me:
                t, c = "KAZANDIN!", GOLD
            else:
                t, c = "KAYBETTİN", (255, 110, 100)
            panel(s, (W // 2 - 330, 180, 660, 360), (12, 16, 34, 240), 26, GOLD, 4)
            draw_text(s, t, 72, (W // 2, 250), c, outline=6)
            sc = snap["sc"]
            A = self.app.assets
            for i in (0, 1):
                img = A.big[snap["p"][i][9]]
                if i == 1:
                    img = A.flipped(img)
                img = pygame.transform.smoothscale(img, (int(img.get_width() * 0.62), int(img.get_height() * 0.62)))
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
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((5, 8, 20, 170))
            s.blit(dim, (0, 0))
            draw_text(s, "DURAKLATILDI", 70, (W // 2, 280), GOLD, outline=6)
            draw_text(s, "ESC: devam     Q: ana menü", 28, (W // 2, 370), WHITE, outline=3, title=False)
        if self.quit_ask:
            panel(s, (W // 2 - 280, 300, 560, 120), (12, 16, 34, 235), 20, (255, 100, 90), 4)
            draw_text(s, "Maçtan çıkılsın mı?", 34, (W // 2, 335), WHITE, outline=3)
            draw_text(s, "Q: çık     ESC: oyuna dön", 24, (W // 2, 385), (220, 230, 250), outline=2, title=False)


# ====================================================================== uygulama
class App:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        flags = pygame.SCALED | pygame.RESIZABLE
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Kafa Kafaya Futbol")
        try:
            pygame.display.set_icon(pygame.image.load(res("assets", "ball.png")))
        except Exception:
            pass
        self.screen.fill(DARK)
        draw_text(self.screen, "Yükleniyor...", 40, (W // 2, H // 2))
        pygame.display.flip()
        self.assets = Assets()
        self.sound = Sound()
        self.clock = pygame.time.Clock()
        self.running = True
        self.bot_level = 1
        self.scene = MenuScene(self)

    def go(self, scene):
        old = self.scene
        self.scene = scene
        if old is not None and old is not scene:
            old.leave()

    def quit(self):
        self.running = False

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                    try:
                        pygame.display.toggle_fullscreen()
                    except pygame.error:
                        pass
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
