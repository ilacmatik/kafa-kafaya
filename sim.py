"""Kafa Kafaya - oyun simulasyonu (pygame'den bagimsiz).

Host (veya tek PC modu) bu simulasyonu calistirir; istemci sadece
snapshot() ciktisini cizer.
"""
import math
import random

W, H = 1280, 720
GROUND = 652
GOAL_D = 102          # kale cizgisi (on direk ic yuzu) x konumu
GOAL_H = 188          # kale agzi yuksekligi
ROOF_T = 26           # ust direk kalinligi (gorselle ayni)
GOAL_TOP = GROUND - GOAL_H

BALL_R = 20
BALL_G = 1250.0
PLAYER_G = 1750.0
BALL_MAX = 1700.0

SUPER_SPEED = 1150.0
SUPER_TIME = 1.0
METER_PER_SEC = 3.0
METER_PER_TOUCH = 3.0

BACK_SPEED = 1.28       # geri kosu hiz carpani

PU_KINDS = ["speed", "jump", "shield", "freeze", "gold"]

# isim, hiz, ziplama, sut gucu, boy carpani, kafa carpani, super tipi
CHARACTERS = [
    {"name": "ALEV",   "speed": 335, "jump": 650, "kick": 1.12, "scale": 1.00, "head": 1.00, "power": "fire"},
    {"name": "KAPTAN", "speed": 320, "jump": 655, "kick": 1.06, "scale": 1.02, "head": 1.05, "power": "magnet"},
    {"name": "DUVAR",  "speed": 300, "jump": 700, "kick": 0.95, "scale": 1.00, "head": 1.12, "power": "glove"},
    {"name": "SARI",   "speed": 322, "jump": 715, "kick": 1.00, "scale": 1.03, "head": 1.00, "power": "ice"},
    {"name": "SIMSEK", "speed": 385, "jump": 645, "kick": 0.95, "scale": 0.95, "head": 0.95, "power": "bolt"},
    {"name": "TANK",   "speed": 275, "jump": 610, "kick": 1.30, "scale": 1.08, "head": 1.10, "power": "quake"},
]
# ekranda gosterilen isimler (Turkce karakterli)
DISPLAY_NAMES = ["ALEV", "KAPTAN", "DUVAR", "SARI", "ŞİMŞEK", "TANK"]
STAT_BARS = [  # hiz, ziplama, sut (0-5) - secim ekrani icin
    (4, 3, 4), (3, 3, 4), (2, 5, 2), (3, 5, 3), (5, 2, 2), (1, 1, 5),
]

BASE_H = 160.0


def clamp(v, a, b):
    return a if v < a else b if v > b else v


class Player:
    def __init__(self, idx, char):
        self.idx = idx
        self.char = char
        c = CHARACTERS[char]
        self.stats = c
        self.h = BASE_H * c["scale"]
        self.head_r = 27.0 * c["head"] * c["scale"]
        self.body_r = 29.0 * c["scale"]
        self.dir = 1 if idx == 0 else -1     # hucum yonu
        self.reset()
        self.meter = 0.0

    def reset(self):
        self.x = 330.0 if self.idx == 0 else W - 330.0
        self.y = float(GROUND)
        self.vx = 0.0
        self.vy = 0.0
        self.face = self.dir
        self.on_ground = True
        self.kick_t = 0.0
        self.kick_hit = False
        self.frozen = 0.0
        self.stun = 0.0
        self.speed_t = 0.0
        self.jump_t = 0.0
        self.armed = 0.0
        self.run_t = 0.0
        self.touch_cd = 0.0
        self.contact = -9.0
        self.jump_prev = False
        self.air_jumps = 0
        self.charging = False
        self.charge = 0.0
        self.kick_power = 1.0
        self.magnet_t = 0.0
        self.lob = False
        self.lob_shot = False
        self.move = 0

    # carpisma daireleri
    def head(self):
        return self.x + self.face * 3, self.y - self.h + self.head_r + 4, self.head_r

    def body(self):
        """Govde (bel-gogus): yerdeki top bunun altindan gecebilir."""
        return self.x, self.y - self.h * 0.47, 22.0 * self.stats["scale"]

    def legs(self):
        """Bacaklar: sadece yerdeyken topu durdurur (ziplayinca top altindan gecer)."""
        return self.x, self.y - 20, 17.0 * self.stats["scale"]

    def foot(self):
        return self.x + self.face * 38 * self.stats["scale"], self.y - 32, 44.0

    @property
    def disabled(self):
        return self.frozen > 0 or self.stun > 0


class Ball:
    def __init__(self):
        self.reset()

    def reset(self, x=W / 2, y=250.0):
        self.x = x
        self.y = y
        self.vx = random.choice((-1, 1)) * random.uniform(20, 60)
        self.vy = 0.0
        self.ang = 0.0
        self.spin = 0.0        # + ust falso (yere dusunce ileri kacar), - ters falso
        self.ignore_t = 0.0
        self.ignore_p = -1
        self.squeeze_cd = 0.0
        self.mode = 0          # 0 normal, 1 ates, 2 buz
        self.mode_t = 0.0
        self.owner = -1        # super sutu atan
        self.hit_cd = [0.0, 0.0]


class World:
    def __init__(self, char0, char1, duration=90):
        self.players = [Player(0, char0), Player(1, char1)]
        self.ball = Ball()
        self.score = [0, 0]
        self.duration = duration
        self.time_left = float(duration)
        self.phase = "ready"
        self.phase_t = 2.6
        self.golden = False
        self.winner = -1
        self.last_touch = -1
        self.events = []
        self.pu = None             # [tur, x, y, omur]
        self.pu_timer = random.uniform(7, 11)
        self.shield = [0.0, 0.0]   # kendi kalesini koruyan buz duvari
        self.glove = [0.0, 0.0]    # DUVAR'in dev eldiveni (gorsel)
        self.scorer = -1
        self.clock = 0.0
        self.last_kind = "shot"
        self.shake = 0.0
        self.events.append("whistle")

    # ------------------------------------------------------------ girdiler
    def apply_input(self, i, left, right, jump, kick_pressed, super_pressed, kick_held=None):
        p = self.players[i]
        jump_edge = jump and not p.jump_prev
        p.jump_prev = jump
        if self.phase in ("ready", "over"):
            p.vx = 0
            p.charging = False
            return
        if p.disabled:
            p.vx *= 0.85
            return
        spd = p.stats["speed"] * (1.45 if p.speed_t > 0 else 1.0)
        move = (1 if right else 0) - (1 if left else 0)
        back = move != 0 and move != p.dir
        if back:
            spd *= BACK_SPEED   # savunmaya donerken daha hizli
        target = move * spd
        # hafif ivmelenme (geri donuste daha cevik)
        acc = (0.45 if back else 0.35) if p.on_ground else (0.26 if back else 0.18)
        p.vx += (target - p.vx) * acc
        p.move = move
        p.face = p.dir   # oyuncu her zaman rakip kaleye bakar
        jmul = 1.28 if p.jump_t > 0 else 1.0
        if kick_held is not None and p.charging and kick_held:
            # sut tusu basiliyken yukari: ziplama yerine asirtma sutu hazirla
            if jump:
                p.lob = True
            jump = jump_edge = False
        if jump and p.on_ground:
            p.vy = -p.stats["jump"] * jmul
            p.on_ground = False
            p.air_jumps = 1
            self.events.append("jump")
        elif jump_edge and not p.on_ground and p.air_jumps > 0:
            # cift ziplama
            p.air_jumps = 0
            p.vy = -p.stats["jump"] * 0.82 * jmul
            self.events.append("jump2:%d" % i)
        # sut: basili tut = sarj, birak = vur (dokunus = normal sut)
        if kick_held is None:
            if kick_pressed and p.kick_t <= 0:
                self._swing(p, 0.0)
        else:
            if kick_pressed and not p.charging and p.kick_t <= 0:
                p.charging = True
                p.charge = 0.0
            if p.charging and not kick_held:
                p.charging = False
                self._swing(p, p.charge)
        if super_pressed and p.meter >= 100 and p.armed <= 0 and p.magnet_t <= 0:
            self._use_power(p)

    # ------------------------------------------------------------ yardimcilar
    def _use_power(self, p):
        pw = p.stats["power"]
        b = self.ball
        o = self.players[1 - p.idx]
        p.meter = 0
        if pw in ("fire", "ice"):
            p.armed = 5.0
            self.events.append("armed")
            if math.hypot(b.x - p.x, b.y - (p.y - p.h * 0.5)) < 150:
                self._super_shot(p)
        elif pw == "magnet":
            p.magnet_t = 3.0
            b.mode = 0
            self.last_touch = p.idx
            self.events.append("magnet:%d" % p.idx)
        elif pw == "glove":
            self.shield[p.idx] = 4.5
            self.glove[p.idx] = 4.5
            self.events.append("glove:%d" % p.idx)
        elif pw == "bolt":
            fx = p.x
            tx = clamp(b.x - p.dir * 48, 40, W - 40)
            p.x = tx
            if b.y > GROUND - 160:
                p.y, p.vy, p.on_ground = GROUND, 0, True
            p.speed_t = max(p.speed_t, 3.0)
            self.events.append("bolt:%d:%d" % (p.idx, int(fx)))
        elif pw == "quake":
            self.events.append("quake:%d" % p.idx)
            self.shake = 0.6
            if o.y >= GROUND - 30 and o.frozen <= 0:
                o.stun = 1.3
                o.vy = -260
                o.on_ground = False
                o.vx = 320 * (1 if o.x > p.x else -1)
            if b.y > GROUND - 220 and not b.mode:
                b.vy = -760
                b.vx *= 0.4
                b.spin = 0

    def _swing(self, p, charge):
        p.kick_t = 0.24
        p.kick_hit = False
        p.lob_shot = p.lob
        p.lob = False
        # 0.12 sn'den kisa basis normal sut; tam sarj %45 daha guclu
        p.kick_power = 1.0 + 0.45 * max(0.0, (charge - 0.15) / 0.85)
        self.events.append("swing")

    def _super_shot(self, p):
        b = self.ball
        p.armed = 0
        kind = 1 if p.stats["power"] == "fire" else 2
        gx = W - GOAL_D * 0.5 if p.idx == 0 else GOAL_D * 0.5
        gy = GROUND - random.uniform(40, GOAL_H - 50)
        dx, dy = gx - b.x, gy - b.y
        d = math.hypot(dx, dy) or 1
        b.vx = dx / d * SUPER_SPEED
        b.vy = dy / d * SUPER_SPEED
        b.mode = kind
        b.mode_t = SUPER_TIME
        b.owner = p.idx
        self.last_touch = p.idx
        self.last_kind = "super"
        self.events.append("super_fire" if kind == 1 else "super_ice")
        self.shake = 0.25

    def _touch(self, p):
        p.contact = self.clock
        if p.touch_cd <= 0:
            p.meter = min(100.0, p.meter + METER_PER_TOUCH)
            p.touch_cd = 0.35
        self.last_touch = p.idx
        if p.armed > 0:
            self._super_shot(p)
            return True
        return False

    def _circle_vs_ball(self, cx, cy, r, pvx, pvy, e=0.55):
        b = self.ball
        dx, dy = b.x - cx, b.y - cy
        d = math.hypot(dx, dy)
        rr = r + BALL_R
        if d >= rr or d == 0:
            return False
        nx, ny = dx / d, dy / d
        b.x += nx * (rr - d)
        b.y += ny * (rr - d)
        rvx, rvy = b.vx - pvx, b.vy - pvy
        vn = rvx * nx + rvy * ny
        if vn < 0:
            b.vx -= (1 + e) * vn * nx
            b.vy -= (1 + e) * vn * ny
        # minimum cikis hizi (topun oyuncuya yapismasini engeller)
        vn2 = (b.vx - pvx) * nx + (b.vy - pvy) * ny
        if vn2 < 140:
            b.vx += nx * (140 - vn2)
            b.vy += ny * (140 - vn2)
        return True

    def _rect_vs_ball(self, x0, y0, x1, y1, e=0.6):
        b = self.ball
        cx = clamp(b.x, x0, x1)
        cy = clamp(b.y, y0, y1)
        dx, dy = b.x - cx, b.y - cy
        d = math.hypot(dx, dy)
        if d >= BALL_R:
            return False
        if d == 0:
            # merkez dikdortgen icinde: yukari it
            b.y = y0 - BALL_R
            b.vy = -abs(b.vy) * e
            return True
        nx, ny = dx / d, dy / d
        b.x += nx * (BALL_R - d)
        b.y += ny * (BALL_R - d)
        vn = b.vx * nx + b.vy * ny
        if vn < 0:
            b.vx -= (1 + e) * vn * nx
            b.vy -= (1 + e) * vn * ny
            if abs(vn) > 200:
                self.events.append("post")
        return True

    def _kick(self, p, rel):
        """Temas noktasina ve harekete gore sut (varsayilan: yukari-ileri)."""
        b = self.ball
        pw = p.stats["kick"]
        q = 1.0 - 0.4 * clamp(rel, 0.0, 1.0)       # tam temas = guclu sut
        h = p.y - b.y                               # topun ayak seviyesinden yuksekligi
        if h < 40:
            ang, kind = 50.0, "shot"     # yerdeki top: havalanir
        elif h < 85:
            ang, kind = 34.0, "shot"     # diz hizasi
        else:
            ang, kind = 16.0, "volley"   # havadaki top: vole
        spin = 0.1
        mv = p.move * p.dir
        if p.lob_shot:
            p.lob_shot = False
            ang, q, spin, kind = 64.0, q * 1.0, -0.8, "lob"
        elif mv < 0:
            ang, q, spin, kind = 66.0, q * 0.9, -0.9, "lob"            # geri giderken: yuksek asirtma
        elif mv > 0 and abs(p.vx) > 150:
            ang, q, spin = ang - 8, q * 1.08, 0.6                       # kosarak: daha sert
            if kind == "shot":
                kind = "drive"
        if not p.on_ground:
            ang -= 4
        speed = 900 * pw * q * p.kick_power
        if p.kick_power > 1.3:
            kind = "power"
            self.events.append("kick_hard")
        r = math.radians(ang)
        b.vx = p.dir * speed * math.cos(r) + p.vx * 0.25
        b.vy = -speed * math.sin(r) + (p.vy * 0.2 if p.vy < 0 else 0)
        b.spin = spin
        b.mode = 0
        b.ignore_t, b.ignore_p = 0.12, p.idx
        self.last_kind = kind
        self.events.append("kick")
        self._touch(p)

    def _smash(self, p):
        """Havada kafa + sut: topu asagi-ileri gomer."""
        b = self.ball
        pw = p.stats["kick"] * p.kick_power
        b.vx = p.dir * 880 * pw
        b.vy = 260 if b.y < GROUND - 200 else -120
        b.spin = 0.4
        b.mode = 0
        b.ignore_t, b.ignore_p = 0.15, p.idx
        self.last_kind = "smash"
        self.events.append("smash")
        self._touch(p)

    def _flick(self, p):
        """Arkada kalan topu topukla kafanin ustunden one asirt."""
        b = self.ball
        b.x = p.x - p.dir * 6
        b.y = min(b.y, p.y - 45)
        b.vx = p.dir * (340 + abs(p.vx) * 0.3)
        b.vy = -990
        b.spin = -0.3
        b.mode = 0
        b.ignore_t, b.ignore_p = 0.45, p.idx
        self.last_kind = "flick"
        self.events.append("kick")
        self._touch(p)

    def _goal_rects(self):
        return [
            (0, GOAL_TOP - ROOF_T, GOAL_D + 20, GOAL_TOP),
            (W - GOAL_D - 20, GOAL_TOP - ROOF_T, W, GOAL_TOP),
        ]

    # ------------------------------------------------------------ adim
    def step(self, dt):
        self.clock += dt
        if self.phase == "over":
            self._step_players(dt)
            return
        if self.phase == "ready":
            self.phase_t -= dt
            if self.phase_t <= 0:
                self.phase = "play"
                self.events.append("whistle")
            return
        if self.phase == "play":
            self.time_left -= dt
            if self.time_left <= 0 and not self.golden:
                self.time_left = 0
                if self.score[0] != self.score[1]:
                    self._end()
                    return
                self.golden = True
                self.events.append("golden")
        if self.phase == "goal":
            self.phase_t -= dt
            if self.phase_t > 2.4 - 0.7:
                dt *= 0.3  # gol aninda agir cekim
            if self.phase_t <= 0:
                if self.golden or (self.time_left <= 0 and self.score[0] != self.score[1]):
                    self._end()
                    return
                self._kickoff()
                return

        for p in self.players:
            p.meter = min(100.0, p.meter + METER_PER_SEC * dt) if self.phase == "play" else p.meter
            if p.charging:
                p.charge = min(1.0, p.charge + dt / 0.4)
            for attr in ("kick_t", "frozen", "stun", "speed_t", "jump_t", "armed", "touch_cd", "magnet_t"):
                v = getattr(p, attr)
                if v > 0:
                    setattr(p, attr, max(0.0, v - dt))
        for i in range(2):
            if self.shield[i] > 0:
                self.shield[i] = max(0.0, self.shield[i] - dt)
            if self.glove[i] > 0:
                self.glove[i] = max(0.0, self.glove[i] - dt)

        self._step_players(dt)
        sub = 3
        for _ in range(sub):
            self._step_ball(dt / sub)
        self._step_powerup(dt)

    def _step_players(self, dt):
        a, b = self.players
        for p in self.players:
            prev_y = p.y
            prev_top = p.y - p.h
            p.vy += PLAYER_G * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            if abs(p.vx) > 30 and p.on_ground:
                p.run_t += dt
            p.on_ground = False
            if p.y >= GROUND:
                p.air_jumps = 0
                if p.vy > 300:
                    self.events.append("land")
                p.y = GROUND
                p.vy = 0
                p.on_ground = True
            p.x = clamp(p.x, 28, W - 28)
            # kale catisi: ustune basma / kafa carpmasi
            for gx0, gy0, gx1, gy1 in self._goal_rects():
                if gx0 - 18 < p.x < gx1 + 18:
                    if prev_y <= gy0 + 1 and p.y >= gy0 and p.vy >= 0:
                        p.y = gy0
                        p.vy = 0
                        p.on_ground = True
                    elif prev_top >= gy1 - 1 and p.y - p.h < gy1 and p.vy < 0:
                        p.y = gy1 + p.h
                        p.vy = 0
        # oyuncu - oyuncu
        dx = b.x - a.x
        if abs(dx) < 72 and (a.y - a.h < b.y and b.y - b.h < a.y):
            over = 72 - abs(dx)
            s = 1 if dx >= 0 else -1
            a.x -= s * over / 2
            b.x += s * over / 2
            a.x = clamp(a.x, 28, W - 28)
            b.x = clamp(b.x, 28, W - 28)

    def _step_ball(self, dt):
        b = self.ball
        for i in range(2):
            if b.hit_cd[i] > 0:
                b.hit_cd[i] -= dt
        if b.ignore_t > 0:
            b.ignore_t -= dt
        if b.squeeze_cd > 0:
            b.squeeze_cd -= dt
        mag = None
        for q in self.players:
            if q.magnet_t > 0 and not q.disabled:
                mag = q
        if mag is not None and not b.mode:
            tx = mag.x + mag.dir * 34
            ty = mag.y - 26 if mag.on_ground else mag.y - mag.h * 0.35
            b.vx += ((tx - b.x) * 60 - b.vx) * min(1.0, dt * 14)
            b.vy += ((ty - b.y) * 60 - b.vy) * min(1.0, dt * 14)
            b.spin = 0
        elif b.mode:
            b.mode_t -= dt
            if b.mode_t <= 0:
                b.mode = 0
        else:
            b.vy += BALL_G * dt + b.spin * 430 * dt
            b.vx *= (1 - 0.12 * dt)
            b.spin *= (1 - 0.6 * dt)
        b.x += b.vx * dt
        b.y += b.vy * dt
        b.ang += (b.vx / BALL_R + b.spin * 12 * (1 if b.vx >= 0 else -1)) * dt

        # zemin
        if b.y + BALL_R > GROUND:
            b.y = GROUND - BALL_R
            if b.vy > 0:
                if b.vy > 160:
                    self.events.append("bounce")
                    if b.spin:
                        b.vx += (1 if b.vx >= 0 else -1) * b.spin * 160
                        b.spin *= 0.4
                b.vy = -b.vy * 0.68
                if abs(b.vy) < 60:
                    b.vy = 0
            b.vx *= (1 - 1.1 * dt)
            if b.mode:
                b.mode = 0
        # tavan
        if b.y - BALL_R < 0:
            b.y = BALL_R
            b.vy = abs(b.vy) * 0.7
        # yan duvarlar (kale icinde file yumusak)
        for side in (0, 1):
            wall = BALL_R if side == 0 else W - BALL_R
            hit = b.x < wall if side == 0 else b.x > wall
            if hit:
                inside_goal = b.y > GOAL_TOP
                e = 0.25 if inside_goal else 0.75
                b.x = wall
                b.vx = (abs(b.vx) if side == 0 else -abs(b.vx)) * e
                if b.mode:
                    b.mode = 0
                if not inside_goal:
                    self.events.append("bounce")
        # kale catisi / ust direk
        for r in self._goal_rects():
            if self._rect_vs_ball(*r):
                if b.mode:
                    b.mode = 0

        # buz kalkani
        for i in range(2):
            if self.shield[i] > 0 and self.phase == "play":
                if i == 0 and b.x - BALL_R < GOAL_D + 8 and b.y > GOAL_TOP and b.vx < 0:
                    b.x = GOAL_D + 8 + BALL_R
                    b.vx = abs(b.vx) * 0.8
                    b.mode = 0
                    self.events.append("shield")
                if i == 1 and b.x + BALL_R > W - GOAL_D - 8 and b.y > GOAL_TOP and b.vx > 0:
                    b.x = W - GOAL_D - 8 - BALL_R
                    b.vx = -abs(b.vx) * 0.8
                    b.mode = 0
                    self.events.append("shield")

        # oyuncular
        for p in self.players:
            opp_super = b.mode and b.owner != p.idx
            if opp_super and b.hit_cd[p.idx] <= 0:
                hx, hy, hr = p.head()
                bx, by, br = p.body()
                lx, ly, lr = p.legs()
                if (math.hypot(b.x - hx, b.y - hy) < hr + BALL_R or
                        math.hypot(b.x - bx, b.y - by) < br + BALL_R or
                        math.hypot(b.x - lx, b.y - ly) < lr + BALL_R):
                    b.hit_cd[p.idx] = 0.5
                    if p.kick_t > 0.05 and not p.disabled:
                        # zamanlamayla super sut karsilanir
                        b.mode = 0
                        b.vx = -b.vx * 0.6
                        b.vy = -400
                        self.events.append("block")
                        self._touch(p)
                    elif b.mode == 1:
                        p.stun = 0.9
                        p.vx = 520 * (1 if b.vx > 0 else -1)
                        p.vy = -380
                        p.on_ground = False
                        self.events.append("fire_hit")
                    else:
                        p.frozen = 2.2
                        self.events.append("freeze")
                    continue
            if b.mode and b.owner != p.idx:
                continue
            if mag is not None and mag is not p:
                continue  # miknatis: rakip topa dokunamaz
            if mag is p and not (p.kick_t > 0 and not p.kick_hit):
                continue  # miknatisli oyuncu topu suruyor
            if b.ignore_t > 0 and b.ignore_p in (p.idx, -2):
                continue  # sut/topuk sonrasi top vuranin govdesinden gecsin
            touched = False
            # sut
            if p.kick_t > 0 and not p.kick_hit and not p.disabled and not p.on_ground:
                hx, hy, hr = p.head()
                if b.y < p.y - p.h * 0.55 and math.hypot(b.x - hx, b.y - hy) < hr + BALL_R + 14:
                    p.kick_hit = True
                    self._smash(p)
                    continue
            if p.kick_t > 0 and not p.kick_hit and not p.disabled:
                fx, fy, fr = p.foot()
                dist = math.hypot(b.x - fx, b.y - fy)
                if dist < fr + BALL_R or mag is p:
                    p.kick_hit = True
                    if mag is p:
                        p.magnet_t = 0
                        p.kick_power = max(p.kick_power, 1.4)
                        dist = 0
                    self._kick(p, dist / (fr + BALL_R))
                    continue
                # top arkada (kendi kale tarafimda) ve alcakta: topukla one asirt
                back = (b.x - p.x) * p.dir
                if -78 < back < 6 and p.y - b.y < 95 and abs(b.y - (p.y - 30)) < 75:
                    p.kick_hit = True
                    self._flick(p)
                    continue
            hx, hy, hr = p.head()
            if self._circle_vs_ball(hx, hy, hr, p.vx, p.vy, 0.75):
                touched = True
                self.last_kind = "head"
                b.spin *= 0.3
                if p.vy < -50:
                    b.vy += p.vy * 0.35
                if abs(b.vx) + abs(b.vy) > 450:
                    self.events.append("head")
            bx, by, br = p.body()
            if self._circle_vs_ball(bx, by, br, p.vx, p.vy, 0.45):
                touched = True
            if p.on_ground or p.y > b.y + 4:
                lx, ly, lr = p.legs()
                if self._circle_vs_ball(lx, ly, lr, p.vx, p.vy, 0.4):
                    touched = True
            if touched:
                if self.last_touch != p.idx:
                    self.last_kind = "body"
                if self._touch(p):
                    pass
        # iki oyuncunun arasinda sikisan top yukari firlar (itisip gol atilmasin)
        pa, pc = self.players
        if (not b.mode and b.squeeze_cd <= 0 and (b.x - pa.x) * (b.x - pc.x) < 0
                and abs(pa.x - pc.x) < 150 and b.y > GROUND - 125
                and self.clock - pa.contact < 0.25 and self.clock - pc.contact < 0.25):
            b.y = min(b.y, GROUND - BALL_R - 4)
            b.vy = -780
            b.vx = random.uniform(-90, 90)
            b.spin = 0
            b.ignore_t, b.ignore_p = 0.3, -2
            b.squeeze_cd = 0.6
            self.last_touch = -1
            self.events.append("pop")
        # son sinir kontrolu (oyuncu topu zemine/duvara itmis olabilir)
        if b.y + BALL_R > GROUND:
            b.y = GROUND - BALL_R
            if b.vy > 0:
                b.vy = -b.vy * 0.5
        if b.x < BALL_R:
            b.x = BALL_R
            b.vx = abs(b.vx) * 0.5
        elif b.x > W - BALL_R:
            b.x = W - BALL_R
            b.vx = -abs(b.vx) * 0.5
        # hiz siniri
        sp = math.hypot(b.vx, b.vy)
        lim = SUPER_SPEED * 1.05 if b.mode else BALL_MAX
        if sp > lim:
            b.vx *= lim / sp
            b.vy *= lim / sp

        # gol kontrolu
        if self.phase == "play":
            if b.x < GOAL_D - BALL_R * 0.6 and b.y > GOAL_TOP + 2:
                self._goal(1)
            elif b.x > W - GOAL_D + BALL_R * 0.6 and b.y > GOAL_TOP + 2:
                self._goal(0)

    def _step_powerup(self, dt):
        if self.phase != "play":
            return
        b = self.ball
        if self.pu is None:
            self.pu_timer -= dt
            if self.pu_timer <= 0:
                kind = random.choice(PU_KINDS)
                self.pu = [kind, random.uniform(330, W - 330), random.uniform(260, 420), 9.0]
                self.events.append("pu_spawn")
        else:
            self.pu[3] -= dt
            if self.pu[3] <= 0:
                self.pu = None
                self.pu_timer = random.uniform(6, 10)
                return
            if math.hypot(b.x - self.pu[1], b.y - self.pu[2]) < BALL_R + 32:
                self._collect(self.pu[0])
                self.pu = None
                self.pu_timer = random.uniform(7, 12)

    def _collect(self, kind):
        i = self.last_touch
        if i < 0:
            i = 0 if self.ball.vx > 0 else 1
        p = self.players[i]
        o = self.players[1 - i]
        if kind == "speed":
            p.speed_t = 7.0
        elif kind == "jump":
            p.jump_t = 7.0
        elif kind == "shield":
            self.shield[i] = 6.0
        elif kind == "freeze":
            o.frozen = 2.5
            self.events.append("freeze")
        elif kind == "gold":
            p.meter = 100.0
        self.events.append("pu:%s:%d" % (kind, i))

    def _goal(self, who):
        self.goal_modes = getattr(self, "goal_modes", []) + [self.ball.mode]
        b = self.ball
        sp = int(math.hypot(b.vx, b.vy))
        kind = "super" if b.mode else getattr(self, "last_kind", "shot")
        own = 1 if (self.last_touch >= 0 and self.last_touch != who) else 0
        self.goal_info = "%d:%s:%d:%d" % (who, kind, sp, own)
        self.score[who] += 1
        self.scorer = who
        self.phase = "goal"
        self.phase_t = 2.4
        self.events.append("goal:" + self.goal_info)
        self.ball.mode = 0
        self.shake = 0.5

    def _kickoff(self):
        for p in self.players:
            p.reset()
        self.ball.reset()
        self.shield = [0.0, 0.0]
        self.glove = [0.0, 0.0]
        self.phase = "ready"
        self.phase_t = 1.4
        self.last_touch = -1
        self.scorer = -1

    def _end(self):
        self.phase = "over"
        if self.score[0] > self.score[1]:
            self.winner = 0
        elif self.score[1] > self.score[0]:
            self.winner = 1
        else:
            self.winner = 2
        self.events.append("end")
        for p in self.players:
            p.frozen = p.stun = 0

    # ------------------------------------------------------------ snapshot
    def snapshot(self):
        b = self.ball
        ps = []
        for p in self.players:
            ps.append([round(p.x, 1), round(p.y, 1), round(p.vx), p.face, round(p.kick_t, 2),
                       round(p.frozen, 2), round(p.meter, 1), round(p.armed, 2), 1 if p.on_ground else 0,
                       p.char, round(p.speed_t, 1), round(p.jump_t, 1), round(p.stun, 2), round(p.run_t, 2),
                       round(p.charge, 2) if p.charging else -1, 1 if p.lob else 0])
        ev = self.events
        self.events = []
        shk, self.shake = self.shake, 0.0
        return {
            "ph": self.phase, "pt": round(self.phase_t, 2), "tm": round(self.time_left, 2),
            "gg": 1 if self.golden else 0, "sc": list(self.score), "win": self.winner,
            "b": [round(b.x, 1), round(b.y, 1), round(b.ang, 2), b.mode, round(b.vx), round(b.vy)],
            "p": ps,
            "pu": None if self.pu is None else [self.pu[0], round(self.pu[1]), round(self.pu[2]), round(self.pu[3], 1)],
            "sh": [round(self.shield[0], 1), round(self.shield[1], 1)],
            "gl": [round(self.glove[0], 1), round(self.glove[1], 1)],
            "mg": [round(q.magnet_t, 2) for q in self.players],
            "scr": self.scorer, "ev": ev, "shk": round(shk, 2),
        }


# ---------------------------------------------------------------- bot
class Bot:
    """Basit ama oynanabilir yapay zeka."""

    def __init__(self, idx, level=1):
        self.idx = idx
        self.level = level  # 0 kolay, 1 normal, 2 zor
        self.react = [0.22, 0.12, 0.05][level]
        self.err = [70, 35, 12][level]
        self.t = 0.0
        self.offset = 0.0
        self.jump_hold = 0

    def think(self, w, dt):
        p = w.players[self.idx]
        b = w.ball
        self.t -= dt
        if self.t <= 0:
            self.t = self.react
            self.offset = random.uniform(-self.err, self.err) * 0.5
        d = p.dir
        own_goal_x = 0 if self.idx == 0 else W
        # topun kisa sure sonraki konumunu tahmin et
        look = 0.18 + 0.1 * self.level
        px = clamp(b.x + b.vx * look, 40, W - 40)
        # topun arkasina gec (kendi kale tarafi)
        target = px - d * (38 + self.offset)
        ball_behind = (b.x - p.x) * d < -10
        danger = abs(b.x - own_goal_x) < 420
        if ball_behind and danger:
            target = px - d * 55
        coming = b.vx * d < -250 and (b.x - own_goal_x) * d < 640
        if coming and not ball_behind:
            # geri cekil, top ile kale arasinda kal
            target = min(px, p.x) if d == 1 else max(px, p.x)
            target = clamp(target - d * 60, GOAL_D + 20, W - GOAL_D - 20)
        if b.mode and b.owner != self.idx:
            # super sut geliyor: ziplayarak kacmaya/karsilamaya calis
            target = p.x
        left = target < p.x - 12
        right = target > p.x + 12
        dx = b.x - p.x
        dist = math.hypot(dx, b.y - (p.y - p.h * 0.6))
        jump = False
        if abs(dx) < 110 and b.y < p.y - p.h * 0.75 and b.vy > -250 and b.y > p.y - p.h - 190:
            jump = random.random() < 0.35 + 0.25 * self.level
        if b.mode and b.owner != self.idx and abs(dx) < 260:
            jump = random.random() < 0.15 * (self.level + 1)
        kick = False
        if dist < 95 and dx * d > -5:
            kick = random.random() < 0.25 + 0.2 * self.level
        if b.mode and b.owner != self.idx and abs(dx) < 120 and self.level >= 1:
            kick = random.random() < 0.3 * self.level
        pw = p.stats["power"]
        sup = False
        if p.meter >= 100:
            if pw in ("fire", "ice", "magnet"):
                sup = dist < 140 and dx * d > 0
            elif pw == "bolt":
                sup = abs(dx) > 320 and (b.x - own_goal_x) * d > 200
            elif pw == "glove":
                sup = b.vx * d < -300 and abs(b.x - own_goal_x) < 520
            elif pw == "quake":
                o = w.players[1 - self.idx]
                sup = abs(o.x - b.x) < 120 and abs(p.x - b.x) < 260
        return left, right, jump, kick, sup
