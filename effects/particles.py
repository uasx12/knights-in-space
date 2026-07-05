"""
particles.py
------------
Reusable particle system for Stage 2 visual effects.

This mirrors the ParticleManager pattern in your reference report:
one manager holds many lightweight particle objects, each with its own
position, velocity, lifetime, size and colour. The manager updates and
draws them all, and removes dead ones.

Provided emitters:
  - emit_slash()       -> attack effect (white/yellow arc sparks)
  - emit_death_burst() -> enemy death effect (dissolving dust)
  - emit_poison()      -> green bubbling poison particles
  - emit_impact()      -> small hit-spark when projectile lands
"""

import math
import random
import pygame
from core import settings as S


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "size", "color", "life",
                 "max_life", "gravity", "shrink", "fade")

    def __init__(self, x, y, vx, vy, size, color, life,
                 gravity=0.0, shrink=0.0, fade=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.size = size
        self.color = color
        self.life = life
        self.max_life = life
        self.gravity = gravity
        self.shrink = shrink
        self.fade = fade

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.size -= self.shrink
        self.life -= 1
        return self.life > 0 and self.size > 0.5

    def draw(self, surface, cam_x):
        if self.fade:
            alpha = max(0, int(255 * (self.life / self.max_life)))
        else:
            alpha = 255
        s = pygame.Surface((int(self.size * 2), int(self.size * 2)),
                           pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha),
                           (int(self.size), int(self.size)), int(self.size))
        surface.blit(s, (self.x - cam_x - self.size, self.y - self.size))


class ParticleManager:
    def __init__(self):
        self.particles = []

    def update(self):
        self.particles = [p for p in self.particles if p.update()]

    def draw(self, surface, cam_x):
        for p in self.particles:
            p.draw(surface, cam_x)

    def clear(self):
        self.particles.clear()

    # ---- Emitters -------------------------------------------------------

    def emit_slash(self, x, y, facing_right=True):
        """Attack effect: a short arc of bright sparks in the swing direction."""
        base_angle = 0 if facing_right else math.pi
        for _ in range(14):
            ang = base_angle + random.uniform(-0.7, 0.7)
            spd = random.uniform(3, 7)
            self.particles.append(Particle(
                x, y,
                math.cos(ang) * spd, math.sin(ang) * spd,
                size=random.uniform(2, 5),
                color=random.choice([(255, 255, 200), (255, 220, 120),
                                     (255, 255, 255)]),
                life=random.randint(10, 18),
                shrink=0.25,
            ))

    def emit_death_burst(self, x, y, color=(120, 200, 90)):
        """Death effect: a dissolving cloud that drifts and falls."""
        for _ in range(26):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(1, 5)
            self.particles.append(Particle(
                x, y,
                math.cos(ang) * spd, math.sin(ang) * spd - 2,
                size=random.uniform(3, 7),
                color=color,
                life=random.randint(25, 45),
                gravity=0.18,
                shrink=0.12,
            ))

    def emit_poison(self, x, y, count=6):
        """Poison effect: green bubbles rising and popping."""
        for _ in range(count):
            self.particles.append(Particle(
                x + random.uniform(-12, 12), y,
                random.uniform(-0.6, 0.6), random.uniform(-1.8, -0.6),
                size=random.uniform(2, 5),
                color=random.choice([S.POISON_GREEN, (90, 180, 50),
                                     (160, 240, 100)]),
                life=random.randint(20, 40),
                shrink=0.08,
            ))

    def emit_impact(self, x, y, color=(120, 220, 60)):
        """Small splatter when a projectile hits something."""
        for _ in range(16):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2, 6)
            self.particles.append(Particle(
                x, y,
                math.cos(ang) * spd, math.sin(ang) * spd,
                size=random.uniform(2, 5),
                color=color,
                life=random.randint(12, 22),
                gravity=0.3,
                shrink=0.15,
            ))
