"""
projectile.py
-------------
Boss poison attack, in two parts:

  PoisonGlob   - an arcing projectile (gravity-affected) the boss throws.
                 On impact it spawns a PoisonPuddle and an impact splatter.
  PoisonPuddle - a lingering hazard on the ground. While the player's feet
                 overlap it, the player gets poisoned (handled in level).
"""

import pygame
from core import settings as S
from core import assets as A


def _make_acid_glob(d=30):
    """Render a refined, glossy acid droplet (radial gradient body, dark rim,
    bright specular highlight) instead of a flat placeholder box."""
    s = pygame.Surface((d, d), pygame.SRCALPHA)
    cx = cy = d // 2
    R = d // 2 - 1

    # soft outer glow
    glow = pygame.Surface((d, d), pygame.SRCALPHA)
    pygame.draw.circle(glow, (150, 240, 70, 60), (cx, cy), R)
    s.blit(glow, (0, 0))

    # body: edge (dark acid) -> centre (bright acid) radial gradient
    edge = (38, 110, 18)
    core = (170, 245, 90)
    for i in range(R, 0, -1):
        t = i / R                      # 1 at edge, ~0 at centre
        col = (int(core[0] + (edge[0] - core[0]) * t),
               int(core[1] + (edge[1] - core[1]) * t),
               int(core[2] + (edge[2] - core[2]) * t))
        pygame.draw.circle(s, (*col, 255), (cx, cy), i)

    # crisp dark rim
    pygame.draw.circle(s, (26, 80, 12), (cx, cy), R, 2)

    # specular highlight (upper-left), and a small secondary glint
    hl = pygame.Surface((d, d), pygame.SRCALPHA)
    pygame.draw.ellipse(hl, (235, 255, 205, 200),
                        (cx - R // 2, cy - int(R * 0.7),
                         max(3, R), max(2, int(R * 0.55))))
    pygame.draw.circle(hl, (255, 255, 230, 160),
                       (cx + R // 3, cy + R // 4), max(1, R // 6))
    s.blit(hl, (0, 0))
    return s


class PoisonGlob:
    _BASE_IMG = None   # refined glob, rendered once and shared

    def __init__(self, x, y, target_x, target_y):
        self.rect = pygame.Rect(x, y, 30, 30)
        if PoisonGlob._BASE_IMG is None:
            PoisonGlob._BASE_IMG = _make_acid_glob(30)
        self.image = PoisonGlob._BASE_IMG.copy()
        # aim a lobbed shot toward the target
        dx = target_x - x
        self.vx = S.PROJECTILE_SPEED if dx >= 0 else -S.PROJECTILE_SPEED
        # initial upward velocity so it arcs
        self.vy = -6.0
        self.alive = True
        self.deflected = False   # once True it flies back and damages the boss
        self.sfx_splat = A.load_sound(S.PATHS["sfx_splat"])

    def deflect(self, toward_x, toward_y):
        """Knock the glob back toward (toward_x, toward_y) - the boss. After a
        deflect the glob damages the boss instead of the player."""
        self.deflected = True
        dx = toward_x - self.rect.centerx
        sgn = 1 if dx >= 0 else -1
        # send it back briskly and re-arc upward so it reaches the tall ogre
        self.vx = sgn * max(abs(self.vx), S.PROJECTILE_SPEED + 3)
        self.vy = -6.5
        # brighten it so a deflected (now-friendly) glob reads differently
        bright = self.image.copy()
        wash = pygame.Surface(bright.get_size(), pygame.SRCALPHA)
        wash.fill((180, 255, 140, 120))
        bright.blit(wash, (0, 0))
        self.image = bright

    def update(self, platforms, particles):
        self.vy += S.PROJECTILE_GRAVITY
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)

        # trailing poison particles
        particles.emit_poison(self.rect.centerx, self.rect.centery, count=2)

        # impact with ground/platforms
        for p in platforms:
            if self.rect.colliderect(p):
                self._impact(particles, p.top)
                return
        # fell off the bottom of the world
        if self.rect.top > S.SCREEN_H + 200:
            self.alive = False

    def _impact(self, particles, ground_y):
        self.alive = False
        self.sfx_splat.play()
        particles.emit_impact(self.rect.centerx, self.rect.centery,
                              color=(120, 220, 60))
        self.spawned_puddle = PoisonPuddle(self.rect.centerx, ground_y)

    def draw(self, surface, cam_x):
        surface.blit(self.image, (self.rect.x - cam_x, self.rect.y))


class PoisonPuddle:
    def __init__(self, cx, ground_y):
        self.width = 90
        self.rect = pygame.Rect(cx - self.width // 2, ground_y - 12,
                                self.width, 16)
        self.timer = S.POISON_PUDDLE_DURATION
        self.alive = True

    def update(self, particles):
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False
        # occasional bubbles rising off the puddle
        if self.timer % 8 == 0:
            particles.emit_poison(self.rect.centerx, self.rect.top, count=3)

    def draw(self, surface, cam_x):
        # fade out as it expires
        fade = self.timer / S.POISON_PUDDLE_DURATION
        base_a = max(40, int(190 * fade))
        s = pygame.Surface((self.rect.width, self.rect.height + 6),
                           pygame.SRCALPHA)
        r = s.get_rect()
        # dark acid rim -> brighter glossy centre
        pygame.draw.ellipse(s, (30, 90, 20, base_a), r)
        inner = r.inflate(-int(r.width * 0.22), -int(r.height * 0.34))
        pygame.draw.ellipse(s, (*S.POISON_GREEN, base_a), inner)
        sheen = inner.inflate(-int(inner.width * 0.4), -int(inner.height * 0.5))
        sheen.centery = inner.top + inner.height // 3
        pygame.draw.ellipse(s, (190, 245, 120, max(0, base_a - 60)), sheen)
        surface.blit(s, (self.rect.x - cam_x, self.rect.y - 6))
