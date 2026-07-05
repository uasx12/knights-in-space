"""
obstacles.py
------------
Additional Stage 2 challenges/obstacles:

  Spikes      - static floor hazard; damages player on contact (with i-frames).
  SteamVent   - periodically erupts; only dangerous while erupting (telegraphed).
  HealthPickup- restores 1 HP, then disappears with a sparkle.

All are lightweight and drawn relative to the camera.
"""

import pygame
from core import settings as S
from core import assets as A


class Spikes:
    """A ground spike that erupts UPWARD on a timed cycle.

    Cycle: a harmless rubble mound (telegraph) -> the spike thrusts up through
    its growth frames -> holds fully extended -> retracts -> repeats. It only
    damages the player while raised, so the rubble phase is the safe window to
    cross. Uses the sliced Spikes.png art; falls back to drawn triangles if the
    art is missing.
    """

    _frames = None   # shared, scaled once across all spikes

    @classmethod
    def _load_frames(cls):
        if cls._frames is None:
            raw = A.load_animation(S.ANIM["spike_erupt"], None,
                                   (170, 90, 70), "SPIKE")
            h = raw[0].get_height() or 1
            s = S.SPIKE_DISPLAY_H / h          # one uniform scale -> baseline kept
            cls._frames = [pygame.transform.smoothscale(
                f, (max(1, int(f.get_width() * s)),
                    max(1, int(f.get_height() * s)))) for f in raw]
        return cls._frames

    def __init__(self, x, ground_y, width=96, phase=0):
        self.ground_y = ground_y
        self.width = width
        self.cx = x + width // 2
        self.frames = self._load_frames()
        self.n = len(self.frames)

        # timing (frames @ 60fps)
        self.down_time = 80      # rubble / safe-to-cross window (telegraph)
        self.rise_time = 16      # thrust up
        self.up_time = 64        # held fully extended
        self.fall_time = 16      # retract
        self.cycle = self.down_time + self.rise_time + self.up_time + self.fall_time
        self.t = phase % self.cycle

        self.ext = 0.0           # 0 = down, 1 = fully erupted
        self.frame_index = 0
        # footprint reference rect (collision uses a derived rect per frame)
        self.rect = pygame.Rect(x, ground_y - 24, width, 24)

    def update(self, player, camera):
        self.t += 1
        cyc = self.t % self.cycle
        if cyc < self.down_time:
            self.ext = 0.0
        elif cyc < self.down_time + self.rise_time:
            self.ext = (cyc - self.down_time) / self.rise_time
        elif cyc < self.down_time + self.rise_time + self.up_time:
            self.ext = 1.0
        else:
            f = (cyc - self.down_time - self.rise_time - self.up_time) / self.fall_time
            self.ext = max(0.0, 1.0 - f)

        self.frame_index = int(round(self.ext * (self.n - 1)))

        # dangerous only once the spike has risen enough to skewer
        if self.ext >= 0.55 and player.alive and self._damage_rect().colliderect(player.rect):
            player.take_damage(1, camera)   # take_damage handles i-frames

    def _damage_rect(self):
        img = self.frames[self.frame_index]
        cur_h = int(img.get_height() * 0.9)
        dmg = pygame.Rect(0, 0, max(20, int(self.width * 0.45)), cur_h)
        dmg.midbottom = (self.cx, self.ground_y)
        return dmg

    def draw(self, surface, cam_x):
        img = self.frames[self.frame_index]
        iw, ih = img.get_size()
        # sink the base slightly into the floor so it doesn't look like it's
        # levitating (purely visual; collision still uses ground_y)
        surface.blit(img, (self.cx - iw // 2 - cam_x,
                           self.ground_y - ih + S.SPIKE_GROUND_INSET))


class BossSpike:
    """A single-shot spike erupted by the boss during Phase 2.

    Unlike the looping environmental `Spikes`, this rises once on a short
    timeline (rubble telegraph -> thrust up -> brief hold -> retract) and then
    reports `done` so the owner can drop it. It shares the same sliced
    Spikes.png frames so it looks identical to the level's ground spikes.
    """

    def __init__(self, cx, ground_y, delay=0, width=96, up_time=26):
        self.cx = cx
        self.ground_y = ground_y
        self.width = width
        self.frames = Spikes._load_frames()
        self.n = len(self.frames)

        # one-shot timeline (frames @ 60fps). `up_time` controls how long the
        # spike stays fully raised, so the total lifetime can be tuned (e.g.
        # the boss's jump spawns a ~1-second field of spikes).
        self.delay = delay       # telegraph wait before this spike rises
        self.rise_time = 10
        self.up_time = up_time
        self.fall_time = 12
        self.t = 0
        self.ext = 0.0
        self.frame_index = 0
        self.done = False

    def update(self, player, camera=None):
        self.t += 1
        c = self.t - self.delay
        if c < 0:
            self.ext = 0.0
        elif c < self.rise_time:
            self.ext = c / self.rise_time
        elif c < self.rise_time + self.up_time:
            self.ext = 1.0
        elif c < self.rise_time + self.up_time + self.fall_time:
            f = (c - self.rise_time - self.up_time) / self.fall_time
            self.ext = max(0.0, 1.0 - f)
        else:
            self.ext = 0.0
            self.done = True

        self.frame_index = int(round(self.ext * (self.n - 1)))

        if self.ext >= 0.55 and player.alive and \
           self._damage_rect().colliderect(player.rect):
            player.take_damage(S.BOSS_SPIKE_DAMAGE, camera)

    def _damage_rect(self):
        img = self.frames[self.frame_index]
        cur_h = int(img.get_height() * 0.9)
        dmg = pygame.Rect(0, 0, max(20, int(self.width * 0.45)), cur_h)
        dmg.midbottom = (self.cx, self.ground_y)
        return dmg

    def draw(self, surface, cam_x):
        img = self.frames[self.frame_index]
        iw, ih = img.get_size()
        surface.blit(img, (self.cx - iw // 2 - cam_x, self.ground_y - ih))


class SteamVent:
    def __init__(self, x, ground_y, cycle=120, active_frames=40, height=140):
        self.x = x
        self.ground_y = ground_y
        self.cycle = cycle
        self.active_frames = active_frames
        self.height = height
        self.t = 0
        self.hit_cd = 0

    @property
    def erupting(self):
        return (self.t % self.cycle) < self.active_frames

    @property
    def warning(self):
        # short telegraph just before eruption
        phase = self.t % self.cycle
        return self.active_frames <= phase < self.active_frames + 20 and not self.erupting

    def update(self, player, camera):
        self.t += 1
        if self.hit_cd > 0:
            self.hit_cd -= 1
        if self.erupting and player.alive and self.hit_cd == 0:
            steam_rect = pygame.Rect(self.x - 20, self.ground_y - self.height,
                                     40, self.height)
            if steam_rect.colliderect(player.rect):
                player.take_damage(1, camera)
                self.hit_cd = S.PLAYER_INVULN_FRAMES

    def draw(self, surface, cam_x):
        sx = self.x - cam_x
        # vent base
        pygame.draw.rect(surface, (80, 80, 90), (sx - 22, self.ground_y - 10, 44, 10))
        if self.erupting:
            # rising steam column
            phase = (self.t % self.cycle) / self.active_frames
            h = int(self.height * min(1.0, phase * 2))
            s = pygame.Surface((40, h), pygame.SRCALPHA)
            s.fill((230, 230, 240, 150))
            surface.blit(s, (sx - 20, self.ground_y - h))


class HealthPickup:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.alive = True
        self.bob = 0
        self.sfx = A.load_sound(S.PATHS["sfx_pickup"])

    def update(self, player, particles):
        self.bob += 1
        # forgiving pickup radius so brushing past collects it
        if self.alive and self.rect.inflate(16, 16).colliderect(player.rect):
            if player.hp < S.PLAYER_MAX_HP:
                player.hp += 1
                self.alive = False
                self.sfx.play()
                particles.emit_impact(self.rect.centerx, self.rect.centery,
                                      color=(255, 80, 80))

    def draw(self, surface, cam_x):
        if not self.alive:
            return
        import math
        oy = int(math.sin(self.bob * 0.1) * 4)
        cx = self.rect.centerx - cam_x
        cy = self.rect.centery + oy
        # simple heart shape using two circles + a triangle
        pygame.draw.circle(surface, S.HUD_RED, (cx - 7, cy - 4), 8)
        pygame.draw.circle(surface, S.HUD_RED, (cx + 7, cy - 4), 8)
        pygame.draw.polygon(surface, S.HUD_RED,
                            [(cx - 14, cy - 1), (cx + 14, cy - 1), (cx, cy + 14)])
