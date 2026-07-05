"""
background.py
-------------
Parallax Mars backdrop for Stage 2.

Unified asset path: the game ships with a single hand-painted vista
(assets/Stage2/Mars_Terrain.png). From that one image this module builds a
layered parallax background:

  * a FAR layer (the sky + distant mountains) that drifts slowly, and
  * a NEAR layer (the full vista) that drifts a little faster,

so the scene gains depth as the camera scrolls. Each layer is mirror-tiled
(every other copy is flipped) which makes it repeat seamlessly no matter how
wide the level is, with no visible seam where the edges meet.

Fallbacks (so the game always runs):
  * If explicit bg_far/bg_mid/bg_near images are supplied, those are used.
  * Else if Mars_Terrain.png is present, layers are derived from it.
  * Else solid Mars-toned gradients are drawn.
"""

import os
import pygame
from core import settings as S


def _gradient(color, top_factor=1.15):
    """Seamless full-screen Mars-toned gradient (used only if no art at all)."""
    surf = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    r, g, b = color
    for y in range(S.SCREEN_H):
        t = 1.0 + (top_factor - 1.0) * (1 - y / S.SCREEN_H)
        col = (min(255, int(r * t)), min(255, int(g * t)), min(255, int(b * t)))
        pygame.draw.line(surf, col, (0, y), (S.SCREEN_W, y))
    return surf


def _scale_to_height(img, h):
    w0, h0 = img.get_size()
    w = max(1, int(w0 * (h / h0)))
    return pygame.transform.smoothscale(img, (w, h))


class _Layer:
    """One mirror-tiled parallax layer."""
    def __init__(self, image, factor, y=0):
        self.img = image
        self.flipped = pygame.transform.flip(image, True, False)
        self.factor = factor
        self.y = y
        self.w = image.get_width()

    def draw(self, surface, cam_x):
        if self.w <= 0:
            return
        # mirror-tiling: copies alternate normal / flipped so edges always
        # match -> a seamless, endlessly repeating backdrop.
        shift = cam_x * self.factor
        start_index = int(shift // self.w)
        offset = -(shift - start_index * self.w)
        x = offset - self.w          # one extra copy to the left
        i = start_index - 1
        while x < S.SCREEN_W:
            img = self.img if (i % 2 == 0) else self.flipped
            surface.blit(img, (int(x), self.y))
            x += self.w
            i += 1


class ParallaxBackground:
    def __init__(self):
        self.sky = None
        self.layers = []

        explicit = all(os.path.exists(S.PATHS[k])
                       for k in ("bg_far", "bg_mid", "bg_near"))
        if explicit:
            self.layers = [
                _Layer(_scale_to_height(
                    pygame.image.load(S.PATHS["bg_far"]).convert(), S.SCREEN_H), 0.2),
                _Layer(_scale_to_height(
                    pygame.image.load(S.PATHS["bg_mid"]).convert(), S.SCREEN_H), 0.5),
                _Layer(_scale_to_height(
                    pygame.image.load(S.PATHS["bg_near"]).convert(), S.SCREEN_H), 0.8),
            ]
            return

        if os.path.exists(S.PATHS["bg_mars"]):
            src = pygame.image.load(S.PATHS["bg_mars"]).convert()
            sw, sh = src.get_size()

            # solid sky fill behind everything, sampled from the image's top
            top_col = src.get_at((sw // 2, 2))[:3]
            self.sky = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
            self.sky.fill(top_col)

            # NEAR layer: the full vista, scaled to screen height.
            near = _scale_to_height(src, S.SCREEN_H)

            # FAR layer: just the sky + distant mountains (top ~62% of the
            # source), scaled to fill the screen, slightly hazed/lightened so
            # it reads as "far away". Drifts slower than the near layer.
            far_src = src.subsurface(pygame.Rect(0, 0, sw, int(sh * 0.62)))
            far = pygame.transform.smoothscale(far_src, (S.SCREEN_W * 2, S.SCREEN_H))
            haze = pygame.Surface(far.get_size(), pygame.SRCALPHA)
            haze.fill((255, 180, 140, 60))   # warm dusty haze
            far.blit(haze, (0, 0))

            self.layers = [
                _Layer(far, 0.15),
                _Layer(near, 0.40),
            ]
            return

        # last-ditch fallback: coloured gradients
        self.layers = [
            _Layer(_gradient((110, 55, 46)), 0.2),
            _Layer(_gradient((150, 76, 54)), 0.5),
        ]

    def draw(self, surface, cam_x):
        if self.sky is not None:
            surface.blit(self.sky, (0, 0))
        for layer in self.layers:
            layer.draw(surface, cam_x)
