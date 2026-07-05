"""
player.py
---------
The knight protagonist for Stage 2.

Handles: run/walk, jump + gravity, melee attack (with a timed hitbox),
taking damage with invulnerability frames, poison ticks, and death.

Animation states expected: idle, walk, run, jump, attack, hurt, die
(matching the sprite sheet rows in your storyboard).
"""

import pygame
from core import settings as S
from core import assets as A
from entities.animated import AnimatedSprite


class Player(AnimatedSprite):
    def __init__(self, x, y):
        # Load each animation TRIMMED (tight crop, no forced size), then
        # scale every frame to a consistent on-screen height so proportions
        # stay correct across idle/walk/jump/attack. PLAYER_DISPLAY_H sets
        # how tall the knight appears.
        DISP_H = S.PLAYER_DISPLAY_H
        def load_scaled(key, fb_color, fb_label):
            frames = A.load_animation(S.ANIM[key], None, fb_color, fb_label)
            return A.scale_frames_to_height(frames, DISP_H)
        anims = {
            "idle":   load_scaled("knight_idle",   (90, 90, 200), "KN-IDLE"),
            "walk":   load_scaled("knight_walk",   (90, 90, 200), "KN-WALK"),
            "run":    load_scaled("knight_run",    (90, 90, 200), "KN-RUN"),
            "jump":   load_scaled("knight_jump",   (90, 90, 200), "KN-JUMP"),
            "attack": load_scaled("knight_attack", (120, 120, 240), "KN-ATK"),
            "hurt":   load_scaled("knight_hurt",   (200, 90, 90), "KN-HURT"),
            "die":    load_scaled("knight_die",    (60, 60, 60), "KN-DIE"),
        }
        super().__init__(anims, "idle", frame_delay=5,
                         # snappier swing so the 5-frame attack reads fully
                         # inside the attack window; brief, punchy hurt.
                         state_delays={"attack": 3, "hurt": 4})

        self.rect = pygame.Rect(x, y, 60, 100)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False

        self.hp = S.PLAYER_MAX_HP
        self.alive = True
        self.invuln = 0
        self.hurt_timer = 0        # frames left to keep showing the hurt pose

        # attack state
        self.attacking = False
        self.attack_timer = 0
        self.attack_hitbox = None
        self.already_hit = set()   # enemy ids hit by the current swing

        # poison state
        self.poisoned = False
        self.poison_tick = 0

        # jump feel: coyote time (jump shortly after leaving a ledge) and
        # jump buffer (press slightly before landing and it still fires)
        self.coyote = 0          # frames since last grounded
        self.jump_buffer = 0     # frames since jump was pressed

        # sfx
        self.sfx_attack = A.load_sound(S.PATHS["sfx_attack"])
        self.sfx_hurt = A.load_sound(S.PATHS["sfx_hurt"])
        self.sfx_jump = A.load_sound(S.PATHS["sfx_jump"], 0.5)
        self.sfx_death = A.load_sound(S.PATHS["sfx_death"])

    # ---- input ----------------------------------------------------------
    def handle_input(self, keys):
        if not self.alive or self.attacking:
            self.vx = 0
            return
        running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed = S.PLAYER_RUN_SPEED if running else S.PLAYER_SPEED
        self.vx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -speed
            self.facing_right = False
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = speed
            self.facing_right = True

    def jump(self):
        # buffer the press; the actual launch happens in update() if grounded
        # or within coyote-time. This makes jumps feel responsive.
        if self.alive and not self.attacking:
            self.jump_buffer = 6

    def attack(self):
        if self.attacking or not self.alive:
            return
        self.attacking = True
        self.attack_timer = S.PLAYER_ATTACK_FRAMES
        self.already_hit.clear()
        self.set_state("attack")
        self.sfx_attack.play()

    # ---- damage / status ------------------------------------------------
    def take_damage(self, amount, camera=None):
        if self.invuln > 0 or not self.alive:
            return False
        self.hp -= amount
        self.invuln = S.PLAYER_INVULN_FRAMES
        self.sfx_hurt.play()
        if camera:
            camera.flash()
            camera.add_shake(8)
        if self.hp <= 0:
            self.die()
        else:
            self.hurt_timer = 16
            self.set_state("hurt")
        return True

    def apply_poison(self, camera=None):
        """Called each frame the player stands in a poison puddle."""
        self.poisoned = True
        self.poison_tick += 1
        if self.poison_tick >= S.POISON_TICK_INTERVAL:
            self.poison_tick = 0
            self.take_damage(S.POISON_DAMAGE_PER_TICK, camera)

    def clear_poison(self):
        self.poisoned = False
        self.poison_tick = 0

    def die(self):
        self.alive = False
        self.set_state("die")
        self.sfx_death.play()

    # ---- physics / update ----------------------------------------------
    def update(self, platforms):
        # gravity
        self.vy += S.GRAVITY
        self.vy = min(self.vy, S.MAX_FALL_SPEED)

        # horizontal move + collision (round, not truncate, so sub-pixel
        # speeds don't silently vanish)
        self.rect.x += round(self.vx)
        self._collide_axis(platforms, self.vx, 0)

        # vertical move + collision
        self.rect.y += round(self.vy)
        landed = False
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vy > 0:
                    self.rect.bottom = p.top
                    self.vy = 0
                    landed = True
                elif self.vy < 0:
                    self.rect.top = p.bottom
                    self.vy = 0

        # STABLE ground check (this is the fix for the old flicker/"doubled"
        # animation): instead of relying on the exact-edge collision result
        # of this frame -- which oscillated True/False because the feet rest
        # precisely on the tile's top edge -- probe one pixel below the feet.
        # That always overlaps the floor while standing, so on_ground stays
        # solidly True and the state machine no longer thrashes idle<->jump.
        self.on_ground = landed or self._ground_probe(platforms)

        # ---- jump launch with coyote time + input buffer ----
        if self.on_ground:
            self.coyote = 6
        elif self.coyote > 0:
            self.coyote -= 1
        if self.jump_buffer > 0:
            self.jump_buffer -= 1
        if self.jump_buffer > 0 and self.coyote > 0 and not self.attacking:
            self.vy = S.PLAYER_JUMP
            self.on_ground = False
            self.coyote = 0
            self.jump_buffer = 0
            self.sfx_jump.play()

        # attack timing + active hitbox window
        if self.attacking:
            self.attack_timer -= 1
            if self.attack_timer > 4:
                reach = S.PLAYER_ATTACK_RANGE
                hx = self.rect.right if self.facing_right else self.rect.left - reach
                self.attack_hitbox = pygame.Rect(hx, self.rect.y + 20, reach, 60)
            else:
                self.attack_hitbox = None
            if self.attack_timer <= 0:
                self.attacking = False
                self.attack_hitbox = None
        else:
            self.attack_hitbox = None

        if self.invuln > 0:
            self.invuln -= 1
        if self.hurt_timer > 0:
            self.hurt_timer -= 1

        self._choose_state()

    def _ground_probe(self, platforms):
        """True if solid ground sits directly beneath the feet."""
        foot = self.rect.copy()
        foot.height = 2
        foot.top = self.rect.bottom      # 2px sliver just below the feet
        return any(foot.colliderect(p) for p in platforms)

    def _collide_axis(self, platforms, dx, dy):
        for p in platforms:
            if not self.rect.colliderect(p):
                continue
            if dx != 0:
                # Only treat it as a wall if there's REAL vertical overlap, not
                # a 1-2px graze where the feet rest on the surface. This keeps
                # the floor from ever acting like a wall and shoving the walker
                # sideways.
                overlap = min(self.rect.bottom, p.bottom) - max(self.rect.top, p.top)
                if overlap > 6:
                    if dx > 0:
                        self.rect.right = p.left
                    elif dx < 0:
                        self.rect.left = p.right
            if dy > 0:
                self.rect.bottom = p.top
                self.vy = 0
                self.on_ground = True
            elif dy < 0:
                self.rect.top = p.bottom
                self.vy = 0

    def _choose_state(self):
        # Priority: dead > attacking > hurt (briefly) > airborne > run > walk > idle.
        # Each branch is mutually exclusive, so the state can no longer be
        # overwritten twice in one frame (the source of the old jitter).
        if not self.alive:
            self.set_state("die", reset=False)
            return
        if self.attacking:
            self.set_state("attack", reset=False)
            return
        if self.hurt_timer > 0:
            self.set_state("hurt", reset=False)
            return
        if not self.on_ground:
            self.set_state("jump")
        elif abs(self.vx) >= S.PLAYER_RUN_SPEED:
            self.set_state("run")
        elif abs(self.vx) > 0:
            self.set_state("walk")
        else:
            self.set_state("idle")

    # ---- draw -----------------------------------------------------------
    def draw(self, surface, cam_x):
        loop = self.state not in ("attack", "die", "hurt")
        img = self.animate(loop=loop)
        if img is None:
            return
        # flicker while invulnerable for clear hit feedback
        if self.invuln > 0 and (self.invuln // 4) % 2 == 0:
            img = img.copy()
            img.set_alpha(120)
        # foot-anchor: center sprite horizontally on the collision rect and
        # align the sprite's bottom to the rect's bottom, so variable-width
        # frames (jump/attack) stay grounded and centered.
        iw, ih = img.get_size()
        draw_x = self.rect.centerx - iw // 2 - cam_x
        draw_y = self.rect.bottom - ih
        surface.blit(img, (draw_x, draw_y))
