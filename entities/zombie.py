"""
zombie.py
---------
Mars zombie enemy. Simple but readable AI:
  - Patrols back and forth until the player enters detection range.
  - Then chases the player horizontally.
  - Attacks (deals contact damage) when close.
  - Plays a death animation + emits a death particle burst when killed.
"""

import pygame
from core import settings as S
from core import assets as A
from entities.animated import AnimatedSprite


class Zombie(AnimatedSprite):
    _next_id = 0

    def __init__(self, x, y, patrol_range=160):
        # Load each animation trimmed (consistent crop), then scale every frame
        # to one display height so the creature keeps correct proportions across
        # idle/walk/attack/death (the old code forced every frame to 80x100,
        # which squashed the art).
        DISP_H = S.ZOMBIE_DISPLAY_H

        def load_scaled(key, color, label):
            frames = A.load_animation(S.ANIM[key], None, color, label)
            return A.scale_frames_to_height(frames, DISP_H)

        anims = {
            "idle":   load_scaled("zombie_idle",   (90, 160, 90), "Z-IDLE"),
            "walk":   load_scaled("zombie_walk",   (90, 160, 90), "Z-WALK"),
            "attack": load_scaled("zombie_attack", (130, 200, 90), "Z-ATK"),
            "die":    load_scaled("zombie_die",    (70, 100, 70), "Z-DIE"),
        }
        super().__init__(anims, "walk", frame_delay=7,
                         state_delays={"attack": 6, "die": 8})

        self.id = Zombie._next_id
        Zombie._next_id += 1

        self.rect = pygame.Rect(x, y, 60, 90)
        self.spawn_x = x
        self.patrol_range = patrol_range
        self.vx = -S.ZOMBIE_SPEED
        self.vy = 0.0
        self.hp = S.ZOMBIE_HP
        self.alive = True
        self.dying = False
        self.attack_cd = 0

        self.sfx_die = A.load_sound(S.PATHS["sfx_enemy_die"])

    def take_damage(self, amount, particles, camera=None):
        if not self.alive:
            return
        self.hp -= amount
        if camera:
            camera.add_shake(4)
        if self.hp <= 0:
            self.kill_enemy(particles)

    def kill_enemy(self, particles):
        self.alive = False
        self.dying = True
        self.set_state("die")
        self.sfx_die.play()
        particles.emit_death_burst(self.rect.centerx, self.rect.centery,
                                   color=(110, 190, 90))

    def update(self, player, platforms):
        if self.dying:
            # play death anim once, then mark fully gone via .finished
            return

        # gravity
        self.vy += S.GRAVITY
        self.vy = min(self.vy, S.MAX_FALL_SPEED)

        dist = player.rect.centerx - self.rect.centerx
        abs_dist = abs(dist)

        if self.attack_cd > 0:
            self.attack_cd -= 1

        if abs_dist <= S.ZOMBIE_ATTACK_RANGE and player.alive:
            # close enough to swing: stop and play the attack pose
            self.vx = 0
            self.set_state("attack")
        elif abs_dist <= S.ZOMBIE_DETECT_RANGE and player.alive:
            # chase
            self.vx = S.ZOMBIE_SPEED if dist > 0 else -S.ZOMBIE_SPEED
            self.facing_right = dist > 0
            self.set_state("walk")
        else:
            # patrol around spawn point
            self.set_state("walk")
            if self.rect.x < self.spawn_x - self.patrol_range:
                self.vx = S.ZOMBIE_SPEED
                self.facing_right = True
            elif self.rect.x > self.spawn_x + self.patrol_range:
                self.vx = -S.ZOMBIE_SPEED
                self.facing_right = False

        # Contact damage only on a REAL body-to-body overlap, and never when
        # the player is above the zombie (jumping on/over its head must be
        # safe). This fixes the old bug where standing on top instantly hurt
        # the player, because range was judged on horizontal distance alone.
        if self.attack_cd == 0 and player.alive and \
           self.rect.colliderect(player.rect):
            player_on_top = player.rect.bottom <= self.rect.top + 24
            if not player_on_top:
                player.take_damage(S.ZOMBIE_DAMAGE)
                self.attack_cd = 40

        # face the way we're moving (covers patrol, chase and idle cases)
        if self.vx > 0:
            self.facing_right = True
        elif self.vx < 0:
            self.facing_right = False

        # move + collide
        self.rect.x += round(self.vx)
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vx > 0:
                    self.rect.right = p.left
                elif self.vx < 0:
                    self.rect.left = p.right
        self.rect.y += round(self.vy)
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vy > 0:
                    self.rect.bottom = p.top
                    self.vy = 0
                elif self.vy < 0:
                    self.rect.top = p.bottom
                    self.vy = 0

    def draw(self, surface, cam_x):
        loop = self.state != "die"
        img = self.animate(loop=loop)
        if not img:
            return
        # foot-anchor: centre the sprite on the collision rect and align its
        # bottom to the rect bottom so variable-width frames stay grounded.
        iw, ih = img.get_size()
        draw_x = self.rect.centerx - iw // 2 - cam_x
        draw_y = self.rect.bottom - ih
        surface.blit(img, (draw_x, draw_y))

    @property
    def gone(self):
        """True once the death animation has finished playing."""
        return self.dying and self.finished
