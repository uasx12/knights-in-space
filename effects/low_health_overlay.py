"""
low_health_overlay.py
----------------------
A full-screen "danger" effect that intensifies as the player's HP drops:

  * a red wash over the whole frame, and
  * a dark-red vignette that closes in from the edges,

both scaling with how hurt the player is (no effect at full HP). When the
player is on their last hit it adds a slow pulse so the screen feels like it's
throbbing.

Usage: build once with the screen size, then call
    overlay.draw(screen, player.hp, S.PLAYER_MAX_HP)
after the world is rendered and before the HUD.
"""

import math
import pygame
from core import settings as S


class LowHealthOverlay:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.t = 0
        self.vignette = self._build_vignette(w, h)

    @staticmethod
    def _build_vignette(w, h):
        """A dark-red radial vignette: opaque-ish at the edges, clear in the
        centre. Built once by stacking shrinking ellipses with falling alpha."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2
        steps = 90
        col = (60, 0, 0)
        for i in range(steps):
            t = i / (steps - 1)                 # 0 = biggest ring, 1 = centre
            rx = int(w * 0.85 * (1 - t)) + 1
            ry = int(h * 0.95 * (1 - t)) + 1
            alpha = int(255 * (1 - t))          # high at edge, 0 at centre
            rect = pygame.Rect(0, 0, rx * 2, ry * 2)
            rect.center = (cx, cy)
            pygame.draw.ellipse(surf, (*col, alpha), rect)
        return surf

    def draw(self, surface, hp, max_hp):
        intensity = (max_hp - hp) / max_hp        # 0 at full HP, 1 at 0 HP
        if intensity <= 0:
            self.t = 0
            return
        self.t += 1

        # slow throb when on the last hit
        pulse = 1.0
        if hp <= 1:
            pulse = 1.0 + 0.18 * math.sin(self.t * 0.12)
        k = max(0.0, min(1.0, intensity * pulse))

        # full-screen red wash
        red_a = int(S.LOW_HP_RED_MAX * k)
        if red_a > 0:
            wash = pygame.Surface((self.w, self.h))
            wash.fill((130, 0, 0))
            wash.set_alpha(red_a)
            surface.blit(wash, (0, 0))

        # dark-red edge vignette (scale its per-pixel alpha by k)
        vig_a = int(S.LOW_HP_VIGNETTE_MAX * k)
        if vig_a > 0:
            v = self.vignette.copy()
            v.fill((255, 255, 255, vig_a), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(v, (0, 0))
