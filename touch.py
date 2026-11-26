"""Dokunmatik kontroller (Android ve KAFA_DOKUNMATIK=1 ile PC'de deneme).

Mac icinde:
- Solda serbest joystick (PUBG gibi): sol alt bolgeye nereye dokunursan orada acilir,
  surukle: sola/saga kos, yukari it: zipla (basili tutulan ziplama gibi).
- Sagda PUBG tarzi dugme kumesi: buyuk SUT, cevresinde ZIPLA, ASIRT, SUPER, OMUZ.
- Ustte duraklat.
Her ekranda: ekranin sol/sag kenarindan iceri cekmek = geri (ESC).
Menulerde "dokunma alanlari": sahne cizerken kaydedilir, dokununca klavye tusu uretilir.
"""
import math
import os
import sys

import pygame

ANDROID = "ANDROID_ARGUMENT" in os.environ or hasattr(sys, "getandroidapilevel")
ENABLED = ANDROID or os.environ.get("KAFA_DOKUNMATIK") == "1"

W, H = 1280, 720
CAM_UP = 130 if ENABLED else 0     # mac sahnesi bu kadar yukari kayar, altta kontrol seridi kalir

# --- sag dugme kumesi: eylem -> (x, y, yaricap) ---
BUTTONS = {
    "k": (1188, 650, 60),     # sut (buyuk)
    "j": (1068, 674, 44),     # zipla
    "d": (1082, 574, 40),     # asirtma
    "s": (1198, 548, 38),     # super
    "o": (962, 678, 38),      # omuz / kayma
    "p": (640, 128, 24),      # duraklat
}
PRESS_KEYS = {"k": pygame.K_SPACE, "s": pygame.K_q, "o": pygame.K_e, "d": pygame.K_s, "p": pygame.K_ESCAPE}

# --- joystick ---
JOY_HOME = (150, 640)      # bos dururken tabanin yeri
JOY_R = 74                 # tabanin yaricapi (topuz bu kadar uzaklasabilir)
JOY_ZONE = pygame.Rect(0, 360, 520, 360)   # bu bolgeye dokunus joystick'i acar
DEAD = 0.28                # olu bolge (yaricapin orani)
JUMP_T = 0.55              # yukari itme esigi

fingers = {}               # parmak id -> [x, y, eylem]
joy = None                 # {"id", "cx", "cy", "kx", "ky"}
zones = []                 # [(rect, key, unicode)] - her karede yeniden doldurulur
active = False             # mac sahnesi kontrolleri cizdiyse True
_edge = {}                 # kenardan cekme takibi: parmak id -> (x0, y0)
_calib = None


def _hit(x, y):
    best, bd = None, 1e9
    for a, (bx, by, r) in BUTTONS.items():
        d = math.hypot(x - bx, y - by)
        if d < r * 1.25 and d < bd:
            best, bd = a, d
    return best


def joy_vec():
    """(-1..1, -1..1) topuz yonu; joystick bos ise (0, 0)."""
    if not joy:
        return 0.0, 0.0
    return (joy["kx"] - joy["cx"]) / JOY_R, (joy["ky"] - joy["cy"]) / JOY_R


def held():
    h = {f[2] for f in fingers.values() if f[2]}
    vx, vy = joy_vec()
    if vx < -DEAD:
        h.add("l")
    elif vx > DEAD:
        h.add("r")
    if vy < -JUMP_T:
        h.add("j")
    return h


def _post_key(key, uni=""):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, unicode=uni, mod=0, scancode=0))


def zone_hit(pos):
    for r, key, uni in reversed(zones):
        if r.collidepoint(pos):
            _post_key(key, uni)
            return True
    return False


def calibrate_mouse(pos):
    return


def _joy_move(x, y):
    dx, dy = x - joy["cx"], y - joy["cy"]
    d = math.hypot(dx, dy)
    if d > JOY_R:
        dx, dy = dx * JOY_R / d, dy * JOY_R / d
    joy["kx"], joy["ky"] = joy["cx"] + dx, joy["cy"] + dy


def _down(fid, x, y):
    global joy
    if not active and (x < W * 0.03 or x > W * 0.97):
        _edge[fid] = (x, y)
    if not active:
        return False
    act = _hit(x, y)
    if act:
        fingers[fid] = [x, y, act]
        if act in PRESS_KEYS:
            _post_key(PRESS_KEYS[act])
        return True
    if joy is None and JOY_ZONE.collidepoint(x, y):
        # serbest joystick: dokunulan yerde acilir (kenarlara tasmasin)
        cx = min(max(x, JOY_R + 12), JOY_ZONE.right - JOY_R)
        cy = min(max(y, JOY_ZONE.top + JOY_R), H - JOY_R - 8)
        joy = {"id": fid, "cx": cx, "cy": cy, "kx": cx, "ky": cy}
        _joy_move(x, y)
        return True
    return False


def _move(fid, x, y):
    if joy and joy["id"] == fid:
        _joy_move(x, y)
        return True
    f = fingers.get(fid)
    if f:
        f[0], f[1] = x, y
        return True
    return False


def _up(fid, x, y):
    global joy
    e0 = _edge.pop(fid, None)
    if e0 is not None and abs(x - e0[0]) > 140 and abs(y - e0[1]) < 160:
        _post_key(pygame.K_ESCAPE)          # kenardan iceri cekme = geri
    if joy and joy["id"] == fid:
        joy = None
        return True
    return fingers.pop(fid, None) is not None


def finger_event(e):
    """FINGERDOWN/MOTION/UP. SDL (SCALED) konumu oyun alanina gore 0..1 verir."""
    fid = (getattr(e, "touch_id", 0), e.finger_id)
    x, y = e.x * W, e.y * H
    if e.type == pygame.FINGERDOWN:
        return _down(fid, x, y)
    if e.type == pygame.FINGERMOTION:
        return _move(fid, x, y)
    if e.type == pygame.FINGERUP:
        return _up(fid, x, y)
    return False


# PC'de fareyle deneme (KAFA_DOKUNMATIK=1): fare tek parmak gibi davranir
def mouse_event(e):
    if ANDROID:
        return False
    fid = ("mouse", 0)
    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
        return _down(fid, *e.pos)
    if e.type == pygame.MOUSEMOTION and (fid in fingers or (joy and joy["id"] == fid)):
        return _move(fid, *e.pos)
    if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
        return _up(fid, *e.pos)
    return False


def release_all():
    global joy
    fingers.clear()
    _edge.clear()
    joy = None


def android_multicast_lock():
    """Android'de UDP yayin (otomatik oyun bulma) paketlerini alabilmek icin."""
    if not ANDROID:
        return None
    try:
        from jnius import autoclass
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        ctx = autoclass("android.content.Context")
        wifi = activity.getApplicationContext().getSystemService(ctx.WIFI_SERVICE)
        lock = wifi.createMulticastLock("kafakafaya")
        lock.setReferenceCounted(False)
        lock.acquire()
        return lock
    except Exception:
        return None


def android_ips():
    """Android: tum ag arayuzlerinin IPv4 adresleri (hotspot arayuzu dahil)."""
    out = []
    try:
        from jnius import autoclass
        NI = autoclass("java.net.NetworkInterface")
        it = NI.getNetworkInterfaces()
        while it.hasMoreElements():
            ni = it.nextElement()
            if not ni.isUp() or ni.isLoopback():
                continue
            addrs = ni.getInetAddresses()
            while addrs.hasMoreElements():
                a = addrs.nextElement().getHostAddress()
                if a and ":" not in a:
                    out.append(a)
    except Exception:
        pass
    return out


def android_gateways():
    """Android: bagli olunan Wi-Fi'nin ag gecidi (hotspot acan telefonun adresi)."""
    try:
        from jnius import autoclass
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        ctx = autoclass("android.content.Context")
        wifi = activity.getApplicationContext().getSystemService(ctx.WIFI_SERVICE)
        g = wifi.getDhcpInfo().gateway & 0xFFFFFFFF
        if g:
            return ["%d.%d.%d.%d" % (g & 255, (g >> 8) & 255, (g >> 16) & 255, (g >> 24) & 255)]
    except Exception:
        pass
    return []

