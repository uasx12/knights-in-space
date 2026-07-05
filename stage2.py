"""
stage2.py
---------
The Stage 2 (Mars) level controller. This is the piece you call from your
main menu / stage manager. It ties together every system:

  player, zombies, boss, projectiles, poison puddles, obstacles,
  particles, camera (shake + flash), parallax background, HUD, audio.

Flow (linear -> boss):
  EXPLORE  : scroll right through the Mars base, fighting zombies and
             dodging obstacles, until reaching the boss trigger zone.
  BOSS     : boss music kicks in; defeat the green ogre.
  WIN      : victory banner + music.
  GAME_OVER: if the knight's HP hits 0.

Run this file directly to test:  python -m stage2   (from project root)
"""

import sys
import pygame

from core import settings as S
from core import assets as A
from core import hud
from core.background import ParallaxBackground
from effects.camera import Camera
from effects.particles import ParticleManager
from effects.poison_overlay import PoisonOverlay
from effects.low_health_overlay import LowHealthOverlay
from entities.player import Player
from entities.zombie import Zombie
from entities.boss import Boss
from entities.obstacles import Spikes, SteamVent, HealthPickup


# --------------------------------------------------------------------------
# LEVEL LAYOUT
# Edit these lists to design your linear level. Coordinates are world-space.
# --------------------------------------------------------------------------
def build_terrain():
    """
    Build the Stage 2 terrain as a paintable tile grid, then return both the
    TileMap (for drawing) and its solid collision Rects.

    Symbols (see core/tilemap.TILE_DEFS):
        '#' solid ground   '=' ledge   'x' crate/wall   '.' air

    The grid is generated to span the whole linear level. Edit `ledges` to
    place platforms, or replace this whole function with a hand-painted grid
    (a list of equal-length strings) for full manual control.
    """
    from core.tilemap import TileMap, GRID_TILE

    cols = S.LEVEL_WIDTH // GRID_TILE
    rows = -(-S.SCREEN_H // GRID_TILE) + 1   # ceil + 1 so ground fills to the screen bottom

    # ground occupies the bottom rows, with scattered visual variety
    ground_row = S.GROUND_Y // GRID_TILE
    import random as _r
    _r.seed(42)
    grid = []
    for r in range(rows):
        if r == ground_row:
            # surface row: mostly regolith, occasional pebbled/rubble variants
            row = "".join(_r.choice("###g#r#") for _ in range(cols))
            grid.append(row)
        elif r > ground_row:
            grid.append("#" * cols)   # solid fill below surface
        else:
            grid.append("." * cols)

    # carve raised ledges: (start_col, rows_up_from_ground, length)
    # These are platforms to jump ONTO (1-2 tiles up, always reachable).
    ledges = [
        (14, 2, 4),
        (23, 3, 3),
        (40, 2, 4),
        (59, 3, 3),
    ]
    grid = [list(row) for row in grid]
    for start_c, up, length in ledges:
        rr = ground_row - up
        for c in range(start_c, min(start_c + length, cols)):
            if 0 <= rr < rows:
                grid[rr][c] = "="

    # Obstacle walls. IMPORTANT: max jump height clears ~2 tiles, so every
    # wall is at most 2 tiles tall. A 2-tile wall gets a 1-tile "step" block
    # in front of it so the player can hop up then over (fair, never blocked).
    def stack(col, height, sym):
        for h in range(height):
            rr = ground_row - 1 - h
            if 0 <= rr < rows and 0 <= col < cols:
                grid[rr][col] = sym

    def wall_with_step(col, height):
        """Place a wall; if 2 tall, add a 1-tall step on the approach side."""
        stack(col, height, "W")
        if height >= 2:
            stack(col - 2, 1, "x")   # crate step in front to climb up

    wall_with_step(30, 1)   # simple 1-tile hull wall (easy hop)
    wall_with_step(50, 2)   # 2-tile wall WITH a step crate in front of it

    # (The old flat yellow hazard-stripe strip that used to sit here has been
    # replaced by real erupting spikes -- see the spike row in build_obstacles
    # -- so the ground stays normal regolith and every spike hazard now uses
    # the Spikes.png art.)

    grid = ["".join(row) for row in grid]

    tm = TileMap(grid)
    return tm, tm.solid_rects()


def build_zombies():
    return [
        Zombie(700,  S.GROUND_Y - 90),
        Zombie(1300, S.GROUND_Y - 90),
        Zombie(2100, S.GROUND_Y - 90),
        Zombie(2900, S.GROUND_Y - 90),
        Zombie(3600, S.GROUND_Y - 90),
        Zombie(4300, S.GROUND_Y - 90),
    ]


def build_obstacles():
    # Erupting spikes in OPEN ground with clear run-up/landing. Each rises on a
    # timed cycle (telegraphed by a rubble mound) and is staggered so they don't
    # all fire at once. ground_y is the floor surface; the spike grows up from it.
    # EVERY upward hazard now uses the Spikes.png art: the two that replaced the
    # old flat hazard strip (x~2200-2320) and the two that replaced the old
    # default-drawn steam vents (x1700, x3700).
    spikes = [
        Spikes(1180, S.GROUND_Y, 96, phase=0),
        Spikes(1700, S.GROUND_Y, 96, phase=88),    # former steam vent
        Spikes(2200, S.GROUND_Y, 96, phase=40),    # former hazard strip
        Spikes(2320, S.GROUND_Y, 96, phase=130),   # former hazard strip
        Spikes(3700, S.GROUND_Y, 96, phase=20),    # former steam vent
        Spikes(4200, S.GROUND_Y, 96, phase=90),
    ]
    # Steam vents removed: those upward hazards are now erupting spikes above,
    # so there are no default-rendered hazards left.
    vents = []
    # Health pickups float just above the ground in OPEN stretches (clear of
    # spikes, vents, walls and especially the low 2-up ledges, under which the
    # player can't stand). The middle one used to sit beneath the col-40 ledge
    # and could only be reached by crouching, so it's moved past that ledge.
    hover = S.GROUND_Y - 56
    pickups = [
        HealthPickup(1460, hover),   # between the first spike and the steam vent
        HealthPickup(2950, hover),   # open ground past the col-40 ledge, before the wall
        HealthPickup(4540, hover),   # open ground after the last spike
    ]
    return spikes, vents, pickups


BOSS_TRIGGER_X = 5200   # crossing this x starts the boss fight
BOSS_SPAWN_X = 5900


class Stage2:
    STATE_EXPLORE = "explore"
    STATE_BOSS = "boss"
    STATE_WIN = "win"
    STATE_GAMEOVER = "gameover"

    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock

        A.verify_assets()   # prints which assets loaded vs. missing

        self.bg = ParallaxBackground()
        self.camera = Camera(S.LEVEL_WIDTH)
        self.particles = ParticleManager()
        self.poison_overlay = PoisonOverlay()
        self.low_health = LowHealthOverlay(S.SCREEN_W, S.SCREEN_H)

        self.player = Player(80, S.GROUND_Y - 100)
        self.tilemap, self.platforms = build_terrain()
        self.zombies = build_zombies()
        self.spikes, self.vents, self.pickups = build_obstacles()

        self.boss = None
        self.projectiles = []
        self.puddles = []

        self.score = 0
        self.state = self.STATE_EXPLORE
        self.end_timer = 0

        self.sfx_game_over = A.load_sound(S.PATHS["sfx_game_over"], 0.7)

        A.play_music(S.PATHS["bgm_stage2"], volume=0.5)

    # ---- main loop ------------------------------------------------------
    def run(self):
        running = True
        while running:
            self.clock.tick(S.FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        self.player.jump()
                    if event.key == pygame.K_f:
                        self.player.attack()
                    if event.key == pygame.K_ESCAPE:
                        running = False

            self.update()
            self.draw()

            if self.state in (self.STATE_WIN, self.STATE_GAMEOVER):
                self.end_timer += 1
                # auto-exit a few seconds after the banner shows
                if self.end_timer > S.FPS * 4:
                    running = False

        A.fade_music(500)
        return self.state  # "win" / "gameover" so your manager can react

    # ---- update ---------------------------------------------------------
    def update(self):
        keys = pygame.key.get_pressed()

        if self.state not in (self.STATE_WIN, self.STATE_GAMEOVER):
            self.player.handle_input(keys)
            self.player.update(self.platforms)

        # camera follows player, clamped
        self.camera.follow(self.player.rect)
        self.camera.update()
        self.particles.update()

        cam_x = self.camera.x  # base (un-shaken) scroll for logic/draw

        # --- obstacles ---
        for sp in self.spikes:
            sp.update(self.player, self.camera)
        for v in self.vents:
            v.update(self.player, self.camera)
        for pk in self.pickups:
            pk.update(self.player, self.particles)

        # --- zombies ---
        for z in self.zombies:
            if z.alive or z.dying:
                z.update(self.player, self.platforms)
                # melee hit detection: player's attack hitbox vs zombie
                if self.player.attack_hitbox and z.alive and \
                   z.id not in self.player.already_hit and \
                   self.player.attack_hitbox.colliderect(z.rect):
                    z.take_damage(S.PLAYER_ATTACK_DAMAGE, self.particles, self.camera)
                    self.player.already_hit.add(z.id)
                    if not z.alive:
                        self.score += 100
                        self.particles.emit_slash(z.rect.centerx, z.rect.centery,
                                                  self.player.facing_right)
        # remove fully-dead zombies
        self.zombies = [z for z in self.zombies if not z.gone]

        # --- state transitions ---
        if self.state == self.STATE_EXPLORE:
            if self.player.rect.centerx >= BOSS_TRIGGER_X:
                self._start_boss()

        elif self.state == self.STATE_BOSS and self.boss:
            self.boss.update(self.player, self.platforms, self.particles,
                             self.camera)
            # collect any new poison globs the boss threw
            for glob in self.boss.collect_projectiles():
                self.projectiles.append(glob)
            # melee hit on boss
            if self.player.attack_hitbox and self.boss.alive and \
               self.player.attack_hitbox.colliderect(self.boss.rect):
                if "boss" not in self.player.already_hit:
                    self.boss.take_damage(S.PLAYER_ATTACK_DAMAGE,
                                          self.particles, self.camera)
                    self.player.already_hit.add("boss")
                    self.particles.emit_slash(self.boss.rect.centerx,
                                              self.boss.rect.centery,
                                              self.player.facing_right)
            if self.boss.gone:
                self._win()

        # --- projectiles + puddles ---
        for glob in self.projectiles:
            glob.update(self.platforms, self.particles)
            # player melee swing DEFLECTS an incoming acid glob back at the boss
            if glob.alive and not glob.deflected and self.boss and \
               self.player.attack_hitbox and \
               self.player.attack_hitbox.colliderect(glob.rect):
                glob.deflect(self.boss.rect.centerx, self.boss.rect.centery)
                self.particles.emit_slash(glob.rect.centerx, glob.rect.centery,
                                          self.player.facing_right)
            # a deflected glob that reaches the boss damages it
            elif glob.alive and glob.deflected and self.boss and self.boss.alive and \
                    glob.rect.colliderect(self.boss.rect):
                self.boss.take_damage(S.BOSS_DEFLECT_DAMAGE,
                                      self.particles, self.camera)
                self.particles.emit_impact(glob.rect.centerx, glob.rect.centery,
                                           color=(160, 240, 100))
                glob.alive = False
            # direct hit on player (deflected globs no longer harm the player)
            elif glob.alive and not glob.deflected and self.player.alive and \
                    glob.rect.colliderect(self.player.rect):
                self.player.take_damage(S.BOSS_PROJECTILE_DAMAGE, self.camera)
                self.particles.emit_impact(glob.rect.centerx, glob.rect.centery)
                glob.alive = False
            # spawn puddle on impact
            if not glob.alive and hasattr(glob, "spawned_puddle"):
                self.puddles.append(glob.spawned_puddle)
                del glob.spawned_puddle
        self.projectiles = [g for g in self.projectiles if g.alive]

        # poison puddles
        standing_in_poison = False
        for pud in self.puddles:
            pud.update(self.particles)
            feet = pygame.Rect(self.player.rect.x, self.player.rect.bottom - 8,
                               self.player.rect.width, 8)
            if pud.alive and feet.colliderect(pud.rect):
                standing_in_poison = True
        self.puddles = [p for p in self.puddles if p.alive]

        if standing_in_poison and self.player.alive:
            self.player.apply_poison(self.camera)
            self.poison_overlay.activate()
        else:
            self.player.clear_poison()
            self.poison_overlay.deactivate()
        self.poison_overlay.update()

        # --- death check ---
        if not self.player.alive and self.state != self.STATE_GAMEOVER:
            # let the die animation finish, then game over
            if self.player.finished:
                self.state = self.STATE_GAMEOVER
                A.fade_music(400)
                self.sfx_game_over.play()   # game-over jingle

    def _start_boss(self):
        self.state = self.STATE_BOSS
        self.boss = Boss(BOSS_SPAWN_X, S.GROUND_Y - 170)
        A.fade_music(400)
        A.play_music(S.PATHS["bgm_boss"], volume=0.6)

    def _win(self):
        self.state = self.STATE_WIN
        self.score += 1000
        A.fade_music(500)
        A.play_music(S.PATHS["bgm_victory"], volume=0.6, loop=False)

    # ---- draw -----------------------------------------------------------
    def draw(self):
        screen = self.screen
        screen.fill(S.BLACK)

        # camera offset incl. shake for the world layer
        cam_x = self.camera.cam_x  # entities subtract this; includes shake

        # parallax (uses base scroll, not shake, so it stays stable)
        self.bg.draw(screen, self.camera.x)

        # terrain (tilemap; uses tileset art or coloured fallback blocks)
        self.tilemap.draw(screen, cam_x)

        # obstacles
        for sp in self.spikes:
            sp.draw(screen, cam_x)
        for v in self.vents:
            v.draw(screen, cam_x)
        for pk in self.pickups:
            pk.draw(screen, cam_x)

        # puddles (under entities)
        for pud in self.puddles:
            pud.draw(screen, cam_x)

        # zombies
        for z in self.zombies:
            z.draw(screen, cam_x)

        # boss
        if self.boss:
            self.boss.draw(screen, cam_x)

        # projectiles
        for glob in self.projectiles:
            glob.draw(screen, cam_x)

        # player
        self.player.draw(screen, cam_x)

        # particles (on top of world)
        self.particles.draw(screen, cam_x)

        # poison full-screen overlay
        self.poison_overlay.draw(screen)

        # camera red damage flash
        self.camera.draw_flash(screen)

        # low-HP danger overlay: screen reddens & darkens as HP falls
        if self.state != self.STATE_WIN:
            self.low_health.draw(screen, self.player.hp, S.PLAYER_MAX_HP)

        # HUD
        hud.draw_hud(screen, self.player, self.score)
        hud.draw_controls(screen)
        if self.boss and self.state == self.STATE_BOSS:
            self.boss.draw_health_bar(screen)

        # banners
        if self.state == self.STATE_WIN:
            hud.draw_banner(screen, "STAGE 2 CLEAR!", S.GREEN,
                            sub=f"Score: {self.score}")
        elif self.state == self.STATE_GAMEOVER:
            hud.draw_banner(screen, "GAME OVER", S.RED,
                            sub="Press ESC or wait to retry")

        pygame.display.flip()


# --------------------------------------------------------------------------
# Standalone test entry point
# --------------------------------------------------------------------------
def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass
    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    pygame.display.set_caption(S.TITLE)
    clock = pygame.time.Clock()
    result = Stage2(screen, clock).run()
    print("Stage 2 ended with state:", result)
    pygame.quit()


if __name__ == "__main__":
    main()
