"""Dokunmatik kontroller (Android ve KAFA_DOKUNMATIK=1 ile PC'de deneme).

- Mac icinde ekran dugmeleri: sol/sag (basili tut, kaydirilabilir), ziplama, sut,
  asirtma, omuz/kayma, super, duraklat.
- Menulerde/ara ekranlarda "dokunma alanlari": sahne cizerken kaydedilir, dokununca
  ilgili klavye tusu olayi uretilir (oyunun geri kalani klavye mantigiyla calisir).
"""
import os
import sys

import pygame

ANDROID = "ANDROID_ARGUMENT" in os.environ or hasattr(sys, "getandroidapilevel")
ENABLED = ANDROID or os.environ.get("KAFA_DOKUNMATIK") == "1"

W, H = 1280, 720

# eylem -> (x, y, yaricap) mantiksal koordinat
BUTTONS = {
    "l": (104, 622, 66),
    "r": (262, 622, 66),
    "j": (1038, 636, 60),
    "k": (1182, 592, 72),
    "d": (1190, 444, 50),     # asirtma
    "o": (902, 656, 46),      # omuz / kayma
    "s": (1050, 492, 50),     # super
    "p": (640, 136, 24),      # duraklat
}
# tek seferlik basmalar -> uretilecek tus
PRESS_KEYS = {"k": pygame.K_SPACE, "s": pygame.K_q, "o": pygame.K_e, "d": pygame.K_s, "p": pygame.K_ESCAPE}
SLIDE = ("l", "r")            # parmak kaydirilinca degisebilen dugmeler

fingers = {}                  # parmak id -> [x, y, eylem]
zones = []                    # [(rect, key, unicode)] - her karede yeniden doldurulur
active = False                # mac sahnesi dugmeleri cizdiyse True
_calib = None                 # None: SDL mantiksal koordinat verir varsayimi, "win": pencere koordinati
_last_down = None


def _to_logical(nx, ny, mode):
    if mode == "win":
        try:
            ww, wh = pygame.display.get_window_size()
        except Exception:
            return nx * W, ny * H
        s = min(ww / W, wh / H)
        ox, oy = (ww - W * s) / 2, (wh - H * s) / 2
        return (nx * ww - ox) / s, (ny * wh - oy) / s
    return nx * W, ny * H


def _hit(x, y, only=None):
    best, bd = None, 1e9
    for a, (bx, by, r) in BUTTONS.items():
        if only and a not in only:
            continue
        d = ((x - bx) ** 2 + (y - by) ** 2) ** 0.5
        if d < r * 1.3 and d < bd:
            best, bd = a, d
    return best


def held():
    return {f[2] for f in fingers.values() if f[2]}


def _post_key(key, uni=""):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, unicode=uni, mod=0, scancode=0))


def zone_hit(pos):
    for r, key, uni in reversed(zones):
        if r.collidepoint(pos):
            _post_key(key, uni)
            return True
    return False


def calibrate_mouse(pos):
    """Ilk parmak icin SDL ayrica fare olayi uretir (dogru donusturulmus). Ikisini
    karsilastirip parmak koordinatlarinin hangi uzayda geldigini ogreniriz."""
    global _calib, _last_down
    if _last_down is None or _calib is not None:
        return
    nx, ny = _last_down
    _last_down = None
    a = _to_logical(nx, ny, None)
    b = _to_logical(nx, ny, "win")
    da = abs(a[0] - pos[0]) + abs(a[1] - pos[1])
    db = abs(b[0] - pos[0]) + abs(b[1] - pos[1])
    if abs(da - db) > 6:
        _calib = "logical" if da < db else "win"


def finger_event(e):
    """FINGERDOWN/MOTION/UP. True donerse olay tuketildi."""
    global _last_down
    fid = (getattr(e, "touch_id", 0), e.finger_id)
    x, y = _to_logical(e.x, e.y, _calib if _calib == "win" else None)
    if e.type == pygame.FINGERDOWN:
        _last_down = (e.x, e.y)
        act = _hit(x, y) if active else None
        fingers[fid] = [x, y, act]
        if act in PRESS_KEYS:
            _post_key(PRESS_KEYS[act])
        return act is not None
    if e.type == pygame.FINGERMOTION:
        f = fingers.get(fid)
        if f is None:
            return False
        f[0], f[1] = x, y
        if active and f[2] in SLIDE:
            # sol/sag arasinda parmagi kaldirmadan gecis; disari kayinca son yon korunur
            f[2] = _hit(x, y, SLIDE) or f[2]
        return f[2] is not None
    if e.type == pygame.FINGERUP:
        f = fingers.pop(fid, None)
        return bool(f and f[2])
    return False


# PC'de fareyle deneme (KAFA_DOKUNMATIK=1): fare tek parmak gibi davranir
def mouse_event(e):
    if ANDROID or not active:
        return False
    fid = ("mouse", 0)
    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
        act = _hit(*e.pos)
        if act:
            fingers[fid] = [e.pos[0], e.pos[1], act]
            if act in PRESS_KEYS:
                _post_key(PRESS_KEYS[act])
            return True
    elif e.type == pygame.MOUSEMOTION and fid in fingers:
        f = fingers[fid]
        if f[2] in SLIDE:
            f[2] = _hit(*e.pos, only=SLIDE) or f[2]
        return True
    elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and fid in fingers:
        fingers.pop(fid)
        return True
    return False


def release_all():
    fingers.clear()


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
