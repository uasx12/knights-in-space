"""
stage1_enemy.py
---------------
Wave enemy for Stage 1.  Uses the original KnightsInSpace zombie sprite
folders (individual PNG frames) while inheriting the Stage 2 AnimatedSprite
engine, physics helpers, and particle system so everything looks and feels
exactly like Stage 2.

Sprite folders (inside assets/images/Zombie/):
    Idle/      9 frames
    Walk/      10 frames
    Attack_1/  4 frames
    Dead/      5 frames
"""

import os
import pygame
from core import settings as S
from core import assets as A
from entities.animated import AnimatedSprite


class Stage1Enemy(AnimatedSprite):
    _next_id = 0

    def __init__(self, x, y, speed=None, hp=None):
        speed = speed or S.STAGE1_ENEMY_BASE_SPEED
        hp = hp or 2

        DISP_H = S.STAGE1_ENEMY_H
        root = S.STAGE1_ASSET_ROOT

        def load(folder):
            frames = A.load_sequence(os.path.join(root, "Zombie", folder))
            return A.scale_frames_to_height(frames, DISP_H)

        anims = {
            "idle":   load("Idle"),
            "walk":   load("Walk"),
            "attack": load("Attack_1"),
            "die":    load("Dead"),
        }

        super().__init__(anims, "walk", frame_delay=7,
                         state_delays={"attack": 6, "die": 9})

        self.id = Stage1Enemy._next_id
        Stage1Enemy._next_id += 1

        self.rect = pygame.Rect(x, y, 55, 85)
        self.base_speed = speed
        self.vx = -speed          # starts moving left; AI adjusts each frame
        self.vy = 0.0
        self.hp = hp
        self.alive = True
        self.dying = False
        self.attack_cd = 0

        self.sfx_die = A.load_sound(S.PATHS["sfx_enemy_die"], 0.5)

    # ---- damage ----------------------------------------------------------
    def take_damage(self, amount, particles=None, camera=None):
        if not self.alive:
            return
        self.hp -= amount
        if camera:
            camera.add_shake(4)
        if self.hp <= 0:
            self._kill(particles)

    def _kill(self, particles=None):
        self.alive = False
        self.dying = True
        self.set_state("die")
        self.sfx_die.play()
        if particles:
            particles.emit_death_burst(self.rect.centerx, self.rect.centery,
                                       color=(90, 160, 220))   # blue-ish for space theme

    # ---- AI + physics ---------------------------------------------------
    def update(self, player, platforms):
        if self.dying:
            return   # death anim plays via animate() in draw()

        if self.attack_cd > 0:
            self.attack_cd -= 1

        # gravity
        self.vy += S.GRAVITY
        self.vy = min(self.vy, S.MAX_FALL_SPEED)

        dist = player.rect.centerx - self.rect.centerx
        abs_dist = abs(dist)

        # --- state / AI ---
        if abs_dist <= S.STAGE1_ENEMY_ATTACK_RANGE and player.alive:
            self.vx = 0
            self.set_state("attack")
        else:
            # always chase player in stage 1 arena
            self.vx = self.base_speed if dist > 0 else -self.base_speed
            self.facing_right = dist > 0
            self.set_state("walk")

        # contact damage (body overlap, not from above)
        if self.attack_cd == 0 and player.alive and self.rect.colliderect(player.rect):
            player_on_top = player.rect.bottom <= self.rect.top + 20
            if not player_on_top:
                player.take_damage(1)
                self.attack_cd = 40

        # face movement direction
        if self.vx > 0:
            self.facing_right = True
        elif self.vx < 0:
            self.facing_right = False

        # horizontal move + wall collision
        self.rect.x += round(self.vx)
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vx > 0:
                    self.rect.right = p.left
                elif self.vx < 0:
                    self.rect.left = p.right

        # vertical move + floor collision
        self.rect.y += round(self.vy)
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vy > 0:
                    self.rect.bottom = p.top
                    self.vy = 0
                elif self.vy < 0:
                    self.rect.top = p.bottom
                    self.vy = 0

    # ---- draw -----------------------------------------------------------
    def draw(self, surface, cam_x=0):
        loop = self.state != "die"
        img = self.animate(loop=loop)
        if not img:
            return
        iw, ih = img.get_size()
        draw_x = self.rect.centerx - iw // 2 - cam_x
        draw_y = self.rect.bottom - ih
        surface.blit(img, (draw_x, draw_y))

    # ---- helpers --------------------------------------------------------
    @property
    def gone(self):
        """True once the death animation has fully played."""
        return self.dying and self.finished
