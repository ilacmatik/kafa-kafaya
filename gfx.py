"""Cozunurlukten bagimsiz cizim katmani.

Oyun kodu her seyi 1280x720 "mantiksal" koordinatlarla cizer. Canvas bu
koordinatlari K ile carpip gercek (fiziksel) yuzeye cizer; Img ise gorselin
yuksek cozunurluklu halini tasir ama boyutunu mantiksal birimle soyler.
Boylece 1920x1080 ekranda her sey keskin cizilir.
"""
import pygame

K = 1.0


def set_scale(k):
    global K
    K = float(k)


def _p(v):
    return int(round(v * K))


def _pt(p):
    return (p[0] * K, p[1] * K)


def _rect(r):
    r = pygame.Rect(r)
    return pygame.Rect(_p(r.x), _p(r.y), max(1, _p(r.w)), max(1, _p(r.h)))


class Img:
    """Yuksek cozunurluklu gorsel; boyutu mantiksal birimde."""
    __slots__ = ("hi", "w", "h")

    def __init__(self, hi):
        self.hi = hi
        self.w = hi.get_width() / K
        self.h = hi.get_height() / K

    def get_width(self):
        return int(round(self.w))

    def get_height(self):
        return int(round(self.h))

    def get_size(self):
        return (self.get_width(), self.get_height())

    def get_rect(self, **kw):
        r = pygame.Rect(0, 0, self.get_width(), self.get_height())
        for k, v in kw.items():
            setattr(r, k, v)
        return r

    def set_alpha(self, a):
        self.hi.set_alpha(a)

    def copy(self):
        return Img(self.hi.copy())


def load(path, logical_size=None, alpha=True):
    """Dosyadan yukle; logical_size verilirse K katina olcekle."""
    s = pygame.image.load(path)
    s = s.convert_alpha() if alpha else s.convert()
    if logical_size is not None:
        s = pygame.transform.smoothscale(s, (max(1, _p(logical_size[0])), max(1, _p(logical_size[1]))))
    return Img(s)


def from_surface(surf, logical_size):
    """Ham (kaynak) yuzeyi mantiksal boyuta gore K katinda Img yap."""
    return Img(pygame.transform.smoothscale(surf, (max(1, _p(logical_size[0])), max(1, _p(logical_size[1])))))


class Canvas:
    """Mantiksal koordinatlarla cizilen fiziksel yuzey."""

    def __init__(self, surf):
        self.surf = surf
        self._dims = {}

    def get_width(self):
        return int(round(self.surf.get_width() / K))

    def get_height(self):
        return int(round(self.surf.get_height() / K))

    def get_size(self):
        return (self.get_width(), self.get_height())

    def get_rect(self, **kw):
        r = pygame.Rect(0, 0, self.get_width(), self.get_height())
        for k, v in kw.items():
            setattr(r, k, v)
        return r

    def blit(self, img, dest, area=None, special_flags=0):
        if isinstance(dest, pygame.Rect):
            x, y = dest.x, dest.y
        else:
            x, y = dest[0], dest[1]
        if isinstance(img, Img):
            src = img.hi
        elif isinstance(img, Canvas):
            src = img.surf
        else:
            # mantiksal cozunurlukte cizilmis gecici yuzey: buyut
            if K != 1.0:
                a = img.get_alpha()
                src = pygame.transform.smoothscale(img, (max(1, _p(img.get_width())), max(1, _p(img.get_height()))))
                if a is not None and a < 255:
                    src.set_alpha(a)
            else:
                src = img
        self.surf.blit(src, (_p(x), _p(y)), None, special_flags)
        return pygame.Rect(int(x), int(y), int(src.get_width() / K), int(src.get_height() / K))

    def fill(self, color, rect=None, special_flags=0):
        if rect is None:
            self.surf.fill(color, None, special_flags)
        else:
            self.surf.fill(color, _rect(rect), special_flags)

    def overlay(self, rgba):
        """Tum ekrana yari saydam renk (onbellekli)."""
        s = self._dims.get(rgba)
        if s is None:
            s = pygame.Surface(self.surf.get_size(), pygame.SRCALPHA)
            s.fill(rgba)
            self._dims[rgba] = s
        self.surf.blit(s, (0, 0))

    def add_full(self, rgb):
        """Tum ekrana toplamali renk (parlama)."""
        s = self._dims.get(("add",))
        if s is None:
            s = pygame.Surface(self.surf.get_size())
            self._dims[("add",)] = s
        s.fill(rgb)
        self.surf.blit(s, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


# ------------------------------------------------------------------ cizim
def _target(s):
    return (s.surf, True) if isinstance(s, Canvas) else (s, False)


class _Draw:
    @staticmethod
    def rect(s, color, rect, width=0, border_radius=0):
        t, sc = _target(s)
        if sc:
            return pygame.draw.rect(t, color, _rect(rect), max(0, _p(width)) if width else 0,
                                    border_radius=_p(border_radius))
        return pygame.draw.rect(t, color, rect, width, border_radius=border_radius)

    @staticmethod
    def circle(s, color, center, radius, width=0):
        t, sc = _target(s)
        if sc:
            return pygame.draw.circle(t, color, _pt(center), radius * K, max(1, _p(width)) if width else 0)
        return pygame.draw.circle(t, color, center, radius, width)

    @staticmethod
    def ellipse(s, color, rect, width=0):
        t, sc = _target(s)
        if sc:
            return pygame.draw.ellipse(t, color, _rect(rect), max(1, _p(width)) if width else 0)
        return pygame.draw.ellipse(t, color, rect, width)

    @staticmethod
    def line(s, color, a, b, width=1):
        t, sc = _target(s)
        if sc:
            return pygame.draw.line(t, color, _pt(a), _pt(b), max(1, _p(width)))
        return pygame.draw.line(t, color, a, b, width)

    @staticmethod
    def lines(s, color, closed, pts, width=1):
        t, sc = _target(s)
        if sc:
            return pygame.draw.lines(t, color, closed, [_pt(p) for p in pts], max(1, _p(width)))
        return pygame.draw.lines(t, color, closed, pts, width)

    @staticmethod
    def polygon(s, color, pts, width=0):
        t, sc = _target(s)
        if sc:
            return pygame.draw.polygon(t, color, [_pt(p) for p in pts], max(1, _p(width)) if width else 0)
        return pygame.draw.polygon(t, color, pts, width)


draw = _Draw()


# ------------------------------------------------------------------ donusum
class _Transform:
    @staticmethod
    def rotate(img, ang):
        if isinstance(img, Img):
            return Img(pygame.transform.rotate(img.hi, ang))
        return pygame.transform.rotate(img, ang)

    @staticmethod
    def rotozoom(img, ang, scale):
        if isinstance(img, Img):
            return Img(pygame.transform.rotozoom(img.hi, ang, scale))
        return pygame.transform.rotozoom(img, ang, scale)

    @staticmethod
    def flip(img, fx, fy):
        if isinstance(img, Img):
            return Img(pygame.transform.flip(img.hi, fx, fy))
        return pygame.transform.flip(img, fx, fy)

    @staticmethod
    def smoothscale(img, size):
        if isinstance(img, Img):
            return Img(pygame.transform.smoothscale(img.hi, (max(1, _p(size[0])), max(1, _p(size[1])))))
        return pygame.transform.smoothscale(img, (max(1, int(size[0])), max(1, int(size[1]))))

    scale = smoothscale


transform = _Transform()


def text(font_render_fn, txt, color):
    return Img(font_render_fn(txt, True, color))
