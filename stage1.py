"""
stage1.py
---------
Stage 1 — Space Arena

Uses the full Stage 2 engine (player controls, HUD, camera shake, particles,
low-health overlay) with:
  • Stage 1 background  (the space/moon vista from KnightsInSpace)
  • Stage 1 enemy sprites (original KnightsInSpace Zombie PNG folders)
  • Wave system: 3 escalating waves; all waves cleared → stage win

Controls (same as Stage 2):
    A / D  or  ← →     move
    Shift               run
    Space / W / ↑       jump
    F                   attack
    ESC                 quit / return to menu
"""

import os
import pygame


from core import settings as S
from core import assets as A
from core import hud
from effects.camera import Camera
from effects.particles import ParticleManager
from effects.low_health_overlay import LowHealthOverlay
from entities.player import Player
from entities.stage1_enemy import Stage1Enemy
from entities.obstacles import HealthPickup


# --------------------------------------------------------------------------
# Arena layout — flat floor + a few jump platforms
# --------------------------------------------------------------------------
def build_platforms():
    """Return a list of solid pygame.Rects for the Stage 1 arena."""
    GY = S.GROUND_Y
    SW = S.SCREEN_W
    SH = S.SCREEN_H
    T = S.TILE_SIZE

    rects = [
        # Floor — full width, tall enough that nothing falls through
        pygame.Rect(0, GY, SW, SH - GY + 200),
        # Invisible side walls so the player can't walk off screen
        pygame.Rect(-T, 0, T, SH + 200),
        pygame.Rect(SW, 0, T, SH + 200),
        # Platforms (px: left, top, width, height)
        pygame.Rect(160,  GY - 160, 200, 24),   # left platform
        pygame.Rect(560,  GY - 210, 200, 24),   # centre platform (higher)
        pygame.Rect(920,  GY - 160, 200, 24),   # right platform
    ]
    return rects


# Colours used when drawing platforms (space-base theme)
_PLATFORM_COLORS = {
    "fill":    (55,  65, 95),
    "edge":    (100, 120, 190),
    "floor":   (30,  35, 55),
    "floor_edge": (80, 100, 160),
}


def draw_platforms(surface, platforms):
    """Draw the arena geometry (no camera scroll for Stage 1)."""
    GY = S.GROUND_Y
    SW = S.SCREEN_W
    for p in platforms:
        if p.top >= GY:
            # Draw the ground as a sci-fi floor strip
            pygame.draw.rect(surface, _PLATFORM_COLORS["floor"], p)
            pygame.draw.line(surface, _PLATFORM_COLORS["floor_edge"],
                             p.topleft, p.topright, 3)
        elif 0 < p.left < SW - p.width:
            # Jump platform
            pygame.draw.rect(surface, _PLATFORM_COLORS["fill"], p)
            pygame.draw.rect(surface, _PLATFORM_COLORS["edge"], p, 2)
            # light shine on top
            pygame.draw.line(surface, (160, 190, 255),
                             (p.left + 4, p.top + 2),
                             (p.right - 4, p.top + 2), 1)


# --------------------------------------------------------------------------
# Background
# --------------------------------------------------------------------------
_bg_cache = {}


def load_background():
    key = "stage1_bg"
    if key not in _bg_cache:
        path = S.PATHS["bg_stage1"]
        if os.path.exists(path):
            raw = pygame.image.load(path).convert()
            _bg_cache[key] = pygame.transform.smoothscale(raw, (S.SCREEN_W, S.SCREEN_H))
        else:
            # Fallback: deep-space gradient
            surf = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
            for y in range(S.SCREEN_H):
                t = y / S.SCREEN_H
                col = (int(5 + 10 * (1 - t)), int(5 + 8 * (1 - t)), int(20 + 30 * (1 - t)))
                pygame.draw.line(surf, col, (0, y), (S.SCREEN_W, y))
            # scatter of stars
            import random
            random.seed(7)
            for _ in range(180):
                sx = random.randint(0, S.SCREEN_W)
                sy = random.randint(0, int(S.SCREEN_H * 0.75))
                br = random.randint(140, 255)
                pygame.draw.circle(surf, (br, br, br), (sx, sy), random.choice([1, 1, 1, 2]))
            _bg_cache[key] = surf
    return _bg_cache[key]


# --------------------------------------------------------------------------
# Wave spawner
# --------------------------------------------------------------------------
def spawn_wave(wave_idx):
    """Return a fresh list of Stage1Enemy objects for wave `wave_idx`."""
    spec = S.STAGE1_WAVES[wave_idx]
    count = spec["count"]
    speed = spec["speed"]
    hp = spec["hp"]

    enemies = []
    GY = S.GROUND_Y
    SW = S.SCREEN_W

    for i in range(count):
        # Alternate spawning from left and right edges, staggered horizontally
        if i % 2 == 0:
            x = 40 + (i // 2) * 80      # from left, off-screen
        else:
            x = SW - 120 - (i // 2) * 80  # from right, off-screen
        e = Stage1Enemy(x, GY - 90, speed=speed, hp=hp)
        enemies.append(e)
    return enemies


def build_stage1_pickups(wave_idx):
    """Return Stage 1 health pickups for the current wave."""
    positions = [
        (244, S.GROUND_Y - 32 - 160),   # left platform
        (644, S.GROUND_Y - 32 - 210),   # centre platform
        (1004, S.GROUND_Y - 32 - 160),  # right platform
    ]
    if 0 <= wave_idx < len(positions):
        return [HealthPickup(*positions[wave_idx])]
    return []


# --------------------------------------------------------------------------
# HUD helpers
# --------------------------------------------------------------------------
def draw_wave_hud(surface, wave_idx, total_waves, enemies_left):
    font = pygame.font.SysFont("consolas", 20, bold=True)
    txt = font.render(f"Wave {wave_idx + 1}/{total_waves}  —  Enemies: {enemies_left}",
                      True, (200, 220, 255))
    surface.blit(txt, (S.SCREEN_W // 2 - txt.get_width() // 2, 16))


def draw_banner(surface, main_text, color, sub=None):
    big = pygame.font.SysFont("consolas", 64, bold=True)
    t = big.render(main_text, True, color)
    surface.blit(t, t.get_rect(center=(S.SCREEN_W // 2, S.SCREEN_H // 2 - 30)))
    if sub:
        small = pygame.font.SysFont("consolas", 26)
        st = small.render(sub, True, S.WHITE)
        surface.blit(st, st.get_rect(center=(S.SCREEN_W // 2, S.SCREEN_H // 2 + 46)))


def draw_stage1_controls(surface):
    """Same controls panel as Stage 2."""
    rows = [
        ("Move",   "A / D  or  \u2190 \u2192"),
        ("Run",    "Shift"),
        ("Jump",   "Space / W / \u2191"),
        ("Attack", "F"),
        ("Quit",   "Esc"),
    ]
    label_font = pygame.font.SysFont("consolas", 16, bold=True)
    key_font   = pygame.font.SysFont("consolas", 16)
    title_font = pygame.font.SysFont("consolas", 15, bold=True)

    pad = 10
    line_h = 22
    title = title_font.render("CONTROLS", True, (255, 220, 120))
    label_w = max(label_font.size(r[0])[0] for r in rows)
    key_w   = max(key_font.size(r[1])[0]   for r in rows)
    panel_w = max(title.get_width(), label_w + 16 + key_w) + pad * 2
    panel_h = pad * 2 + line_h * (len(rows) + 1)

    x = S.SCREEN_W - panel_w - 16
    y = 16

    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 120))
    pygame.draw.rect(panel, (255, 220, 120, 90), panel.get_rect(), 1)
    surface.blit(panel, (x, y))

    surface.blit(title, (x + pad, y + pad))
    ry = y + pad + line_h
    for label, keys in rows:
        surface.blit(label_font.render(label, True, S.WHITE), (x + pad, ry))
        surface.blit(key_font.render(keys, True, (190, 200, 210)),
                     (x + pad + label_w + 16, ry))
        ry += line_h


# --------------------------------------------------------------------------
# Main Stage 1 class
# --------------------------------------------------------------------------
class Stage1:
    # internal states
    _INTRO      = "intro"       # wave number banner shown before wave starts
    _FIGHTING   = "fighting"    # player vs enemies
    _WAVE_CLEAR = "wave_clear"  # brief "Wave N Complete!" pause
    _WIN        = "win"         # all waves cleared
    _GAMEOVER   = "gameover"    # player died

    _BANNER_DURATION = 120      # frames a banner stays visible (2 s @ 60 fps)

    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock

        self.bg = load_background()
        self.platforms = build_platforms()

        # Stage 2-identical systems
        self.camera = Camera(S.SCREEN_W)   # level_width = screen_w → no scroll
        self.particles = ParticleManager()
        self.low_health = LowHealthOverlay(S.SCREEN_W, S.SCREEN_H)

        self.player = Player(S.SCREEN_W // 2 - 30, S.GROUND_Y - 110)
        self.score = 0

        self.wave_idx = 0
        self.total_waves = len(S.STAGE1_WAVES)
        self.enemies = []
        self.pickups = []

        self.state = self._INTRO
        self.banner_timer = self._BANNER_DURATION

        self.sfx_game_over = A.load_sound(S.PATHS["sfx_game_over"], 0.7)

        self.sfx_attack = A.load_sound(os.path.join(S.ASSET_ROOT, "Audio", "SFX", "attack.wav"))
        self.sfx_hurt = A.load_sound(os.path.join(S.ASSET_ROOT, "Audio", "SFX", "hurt.wav"))
        self.sfx_heartbeat = A.load_sound(os.path.join(S.ASSET_ROOT, "Audio", "Heartbeat.wav"))
        self.sfx_zombie = A.load_sound(os.path.join(S.ASSET_ROOT, "Audio", "zombiesound.mp3"))
        self.last_hp = self.player.hp

        A.play_music(os.path.join(S.ASSET_ROOT, "Audio", "moon_wave1.mp3"), volume=0.5, loop=True)

    # ---- main loop -------------------------------------------------------
    def run(self):
        running = True
        while running:
            self.clock.tick(S.FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys; sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        self.player.jump()
                    if event.key == pygame.K_f:
                        self.player.attack()
                    if event.key == pygame.K_ESCAPE:
                        running = False

            self.update()
            self.draw()

            # Auto-exit after win/gameover banner finishes
            if self.state in (self._WIN, self._GAMEOVER):
                self.banner_timer -= 1
                if self.banner_timer <= 0:
                    running = False

        A.fade_music(500)
        pygame.mixer.music.stop()
        self.sfx_zombie.stop()
        self.sfx_heartbeat.stop()
        self.sfx_hurt.stop()
        return self.state   # "win" or "gameover" (or "intro"/"fighting" if ESC)

    # ---- update ----------------------------------------------------------
    def update(self):
        keys = pygame.key.get_pressed()

        if self.state == self._FIGHTING:
            self.player.handle_input(keys)
            self.player.update(self.platforms)

        self.camera.follow(self.player.rect)
        self.camera.update()
        self.particles.update()
        
        if self.player.hp < self.last_hp:
            self.sfx_hurt.play()
            self.sfx_zombie.play()

            if self.player.hp <= 1:
                self.sfx_heartbeat.play()
            
            self.last_hp = self.player.hp
        elif self.player.hp > self.last_hp:
            self.last_hp = self.player.hp

        if self.state == self._FIGHTING:
            for pk in self.pickups:
                pk.update(self.player, self.particles)
            self.pickups = [pk for pk in self.pickups if pk.alive]

            for e in self.enemies:
                if e.alive or e.dying:
                    e.update(self.player, self.platforms)
                    # melee hit detection (same as Stage 2)
                    if (self.player.attack_hitbox and e.alive and
                            e.id not in self.player.already_hit and
                            self.player.attack_hitbox.colliderect(e.rect)):
                        e.take_damage(S.PLAYER_ATTACK_DAMAGE, self.particles, self.camera)
                        self.player.already_hit.add(e.id)
                        if not e.alive:
                            self.score += 100
                            self.particles.emit_slash(e.rect.centerx, e.rect.centery,
                                                      self.player.facing_right)
            # remove fully-dead enemies
            self.enemies = [e for e in self.enemies if not e.gone]

            # wave cleared?
            if not self.enemies:
                if self.wave_idx + 1 < self.total_waves:
                    self.state = self._WAVE_CLEAR
                    self.banner_timer = self._BANNER_DURATION
                else:
                    self._win()

            # player died?
            if not self.player.alive and self.player.finished:
                self.state = self._GAMEOVER
                self.banner_timer = int(S.FPS * 5)
                A.fade_music(400)
                self.sfx_game_over.play()

        elif self.state == self._INTRO:
            self.banner_timer -= 1
            if self.banner_timer <= 0:
                # Spawn the wave, pickups, and start fighting
                self.enemies = spawn_wave(self.wave_idx)
                self.pickups = build_stage1_pickups(self.wave_idx)
                self.state = self._FIGHTING

        elif self.state == self._WAVE_CLEAR:
            self.banner_timer -= 1
            if self.banner_timer <= 0:
                self.wave_idx += 1
                if self.wave_idx == 1:
                    A.play_music(os.path.join(S.ASSET_ROOT, "Audio", "moon_wave2.mp3"), volume=0.5, loop=True)
                elif self.wave_idx == 2:
                    A.play_music(os.path.join(S.ASSET_ROOT, "Audio", "moon_wave3.mp3"), volume=0.5, loop=True)
                self.state = self._INTRO
                self.banner_timer = self._BANNER_DURATION

    def _win(self):
        self.state = self._WIN
        self.score += 500 * self.total_waves
        self.banner_timer = int(S.FPS * 4)
        A.fade_music(600)

    # ---- draw ------------------------------------------------------------
    def draw(self):
        screen = self.screen
        screen.fill(S.BLACK)

        cam_x = self.camera.cam_x    # 0 for Stage 1 (fixed screen), but retains shake

        # Background
        screen.blit(self.bg, (0, 0))

        # Arena geometry
        draw_platforms(screen, self.platforms)

        # Health pickups
        for pk in self.pickups:
            pk.draw(screen, cam_x)

        # Enemies
        for e in self.enemies:
            e.draw(screen, cam_x)

        # Player
        self.player.draw(screen, cam_x)

        # Particles
        self.particles.draw(screen, cam_x)

        # Camera damage flash
        self.camera.draw_flash(screen)

        # Low-HP danger overlay
        if self.state not in (self._WIN, self._GAMEOVER):
            self.low_health.draw(screen, self.player.hp, S.PLAYER_MAX_HP)

        # HUD (hearts + score — identical to Stage 2)
        hud.draw_hud(screen, self.player, self.score)
        draw_stage1_controls(screen)

        # Wave counter
        if self.state in (self._FIGHTING, self._WAVE_CLEAR):
            alive_count = sum(1 for e in self.enemies if e.alive)
            draw_wave_hud(screen, self.wave_idx, self.total_waves, alive_count)

        # Banners
        if self.state == self._INTRO:
            progress = 1.0 - self.banner_timer / self._BANNER_DURATION
            alpha = int(min(255, progress * 4 * 255))
            draw_banner(screen,
                        f"WAVE {self.wave_idx + 1}",
                        (200, 230, 255),
                        sub="Get ready!" if self.wave_idx == 0 else f"Wave {self.wave_idx + 1} of {self.total_waves}")

        elif self.state == self._WAVE_CLEAR:
            draw_banner(screen,
                        f"WAVE {self.wave_idx + 1} CLEAR!",
                        S.GREEN,
                        sub="Next wave incoming..." if self.wave_idx + 1 < self.total_waves else "")

        elif self.state == self._WIN:
            draw_banner(screen,
                        "STAGE 1 CLEAR!",
                        S.GREEN,
                        sub=f"Score: {self.score}  —  Press F to advance to Stage 2")

        elif self.state == self._GAMEOVER:
            draw_banner(screen,
                        "GAME OVER",
                        S.RED,
                        sub="Press ESC to return to menu")

        pygame.display.flip()


# --------------------------------------------------------------------------
# Standalone test
# --------------------------------------------------------------------------
def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass
    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    pygame.display.set_caption("Knights in Space - Stage 1")
    clock = pygame.time.Clock()
    result = Stage1(screen, clock).run()
    print("Stage 1 ended:", result)
    pygame.quit()


if __name__ == "__main__":
    main()
