"""
camera.py
---------
Side-scrolling camera for the linear Mars level, plus two screen-wide
feedback effects you prioritised:

  - Screen shake  : trauma-based offset that decays each frame. Call
                    camera.add_shake(amount) on big hits / boss slams.
  - Damage flash  : red full-screen overlay that fades out. Call
                    camera.flash() when the player takes damage.

The camera follows the player but clamps to the level bounds so you
never scroll past the start or end of the linear stage.
"""

import random
import pygame
from core import settings as S


class Camera:
    def __init__(self, level_width, screen_w=S.SCREEN_W):
        self.level_width = level_width
        self.screen_w = screen_w
        self.x = 0.0                # world-space left edge of the view
        self.shake = 0.0            # current shake magnitude
        self.flash_timer = 0        # frames remaining on red flash

    def follow(self, target_rect):
        """Centre horizontally on target, clamped to level bounds."""
        desired = target_rect.centerx - self.screen_w // 2
        self.x = max(0, min(desired, self.level_width - self.screen_w))

    def add_shake(self, amount):
        self.shake = min(self.shake + amount, 30)

    def flash(self, frames=S.HIT_FLASH_FRAMES):
        self.flash_timer = frames

    def update(self):
        self.shake *= S.SHAKE_DECAY
        if self.shake < 0.5:
            self.shake = 0.0
        if self.flash_timer > 0:
            self.flash_timer -= 1

    @property
    def offset(self):
        """Returns the (x, y) pixel offset to apply when blitting the world.
        Shake jitters the whole frame; subtract camera.x for scrolling."""
        ox = -self.x
        oy = 0
        if self.shake > 0:
            ox += random.uniform(-self.shake, self.shake)
            oy += random.uniform(-self.shake, self.shake)
        return ox, oy

    @property
    def cam_x(self):
        """Convenience: integer world->screen x shift, shake included."""
        sx = -self.x
        if self.shake > 0:
            sx += random.uniform(-self.shake, self.shake)
        return -sx  # entities subtract this value: screen_x = world_x - cam_x

    def draw_flash(self, surface):
        """Overlay the fading red damage flash. Call last, after the world."""
        if self.flash_timer > 0:
            alpha = int(140 * (self.flash_timer / S.HIT_FLASH_FRAMES))
            overlay = pygame.Surface((surface.get_width(),
                                      surface.get_height()), pygame.SRCALPHA)
            overlay.fill((*S.RED, alpha))
            surface.blit(overlay, (0, 0))
