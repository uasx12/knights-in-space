"""
poison_overlay.py
-----------------
Full-screen poison effect for when the knight is standing in a poison
puddle. Two parts:

  1. A pulsing green tint over the whole screen (sense of being poisoned).
  2. A green colour-channel emphasis, reusing the channel-isolation idea
     from your reference report (keep green, suppress red/blue) but done
     cheaply with a tint surface so it runs every frame at 60 FPS.

Use it as a stateful overlay: call .activate() while poisoned, .update()
each frame, and .draw(screen) after the world is rendered.
"""

import math
import pygame
from core import settings as S


class PoisonOverlay:
    def __init__(self):
        self.active = False
        self.t = 0  # animation clock for the pulse

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False

    def update(self):
        if self.active:
            self.t += 1
        else:
            # ease the clock back so it doesn't snap when re-triggered
            self.t = max(0, self.t - 2)

    def draw(self, surface):
        if not self.active and self.t <= 0:
            return
        # Pulsing alpha via sine wave -> gentle "throb" of the poison tint.
        pulse = (math.sin(self.t * 0.15) + 1) / 2     # 0..1
        alpha = int(40 + pulse * 50)                  # 40..90
        overlay = pygame.Surface((surface.get_width(),
                                  surface.get_height()), pygame.SRCALPHA)
        overlay.fill((*S.POISON_GREEN, alpha))
        # BLEND_MULT pushes the frame toward green (suppresses R/B),
        # echoing the channel-isolation look without per-pixel numpy work.
        surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        # A faint additive green glow on top for the "toxic" feel.
        glow = pygame.Surface((surface.get_width(),
                               surface.get_height()), pygame.SRCALPHA)
        glow.fill((20, 60, 10, int(pulse * 30)))
        surface.blit(glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
