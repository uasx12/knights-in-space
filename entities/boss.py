"""
boss.py
-------
The green ogre final boss for Stage 2.

Behaviour (stationary "acid turret"):
  - The ogre DOES NOT MOVE horizontally. It holds its ground in an IDLE pose
    and turns to face the player.
  - It constantly SPITS ACID (a ranged PoisonGlob) at the player. A well-timed
    player melee swing can DEFLECT an incoming glob back into the ogre (handled
    in the level: PoisonGlob.deflect + a boss take_damage on contact).
  - When the player gets CLOSE it punishes them with a STOMP: it JUMPS and
    slams down, and the landing fires a floor shockwave with a strong screen
    shake (only hits a grounded player - jump to dodge).
  - PHASE 2 (at/below half HP): the ogre roars and changes into a SPIKEY form,
    its acid spit speeds up, and while the player is close it adds two more
    close moves - erupting ground SPIKES, and a MELEE swipe (with the attack
    animation) - cycling Stomp -> Spikes -> Melee.
  - Death triggers a big particle burst + screen shake; the level then plays
    the victory sequence.

It exposes pending_projectiles so the level can collect new acid globs. The
boss owns and draws its own close-range hazards (stomp shockwave + erupted
spikes), so the level controller needs no extra wiring for them.
"""

import math
import pygame
from core import settings as S
from core import assets as A
from entities.animated import AnimatedSprite
from entities.projectile import PoisonGlob
from entities.obstacles import BossSpike


class Boss(AnimatedSprite):
    def __init__(self, x, y):
        # No dedicated boss art was supplied, so the Amalgamation reuses the
        # zombie sheets: scaled up to a hulking size and tinted. Drop a real
        # boss pack into settings.ANIM["boss_*"] later and this still works.
        DISP_H = S.BOSS_DISPLAY_H
        BIG_H = int(DISP_H * S.BOSS_PHASE2_SCALE)   # Phase 2 is visibly bigger

        def load_raw(key, label):
            frames = A.load_animation(S.ANIM[key], None, (150, 150, 150), label)
            return A.scale_frames_to_height(frames, DISP_H)   # grey, scaled

        raw = {
            "idle":   load_raw("boss_idle",   "BOSS-IDLE"),
            "attack": load_raw("boss_attack", "BOSS-ATK"),
            "die":    load_raw("boss_die",    "BOSS-DIE"),
        }

        # Phase 1: normal size, green tint
        self.anims_normal = {
            k: [self._tint(f, S.BOSS_TINT_PHASE1) for f in frames]
            for k, frames in raw.items()
        }
        # Phase 2: BIGGER + RED tint (a clean, readable enraged transformation -
        # not a hairy/black procedural "spikey" form). Swap in a real spikey
        # boss sheet here later if you get one.
        self.anims_phase2 = {
            k: [self._tint(f, S.BOSS_TINT_PHASE2, S.BOSS_BOOST_PHASE2)
                for f in A.scale_frames_to_height(frames, BIG_H)]
            for k, frames in raw.items()
        }

        super().__init__(self.anims_normal, "idle", frame_delay=8,
                         state_delays={"attack": 6, "die": 9})

        self.rect = pygame.Rect(x, y, 130, 170)
        self.vx = 0.0          # the ogre never moves horizontally
        self.vy = 0.0
        self.on_ground = False
        self.hp = S.BOSS_HP
        self.max_hp = S.BOSS_HP
        self.alive = True
        self.dying = False
        self.enraged = False   # set True on Phase 2 (speeds up the acid spit)

        self.throw_cd = S.BOSS_THROW_COOLDOWN
        self.contact_cd = 0
        self.spit_anim = 0     # frames left showing the spit pose
        self.pending_projectiles = []

        # ---- Phase 2 / close-range special state ----
        self.phase = 1
        self.special = None          # None | "stomp" | "spikes" | "melee"
        self.special_timer = 0       # frame counter within the current special
        self.special_cd = S.BOSS_SPECIAL_COOLDOWN
        self._special_fired = False  # has this special's payload gone off yet
        self._p2_idx = 0             # rotates the Phase-2 close moves
        self._stomp_jumped = False   # has the stomp leap launched
        self._stomp_was_air = False  # was the boss airborne during the stomp
        self.boss_spikes = []        # BossSpike hazards currently on the floor
        self.shockwaves = []         # active stomp shockwaves

        self.sfx_roar = A.load_sound(S.PATHS["sfx_boss_roar"])
        self.sfx_die = A.load_sound(S.PATHS["sfx_enemy_die"])
        self.sfx_spit = A.load_sound(S.PATHS["sfx_throw"])
        self.sfx_stomp = A.load_sound(S.PATHS["sfx_attack"])
        self._roared = False

    @staticmethod
    def _tint(frame, rgb, boost=(0, 0, 0)):
        """Multiply a (grey) frame toward an RGB colour, preserving the original
        alpha silhouette and internal shading. An optional additive `boost`
        lifts the colour so it reads bright (used so the red form isn't dark)."""
        out = frame.copy()
        tint = pygame.Surface(out.get_size(), pygame.SRCALPHA)
        tint.fill((rgb[0], rgb[1], rgb[2], 255))
        out.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        if any(boost):
            add = pygame.Surface(out.get_size(), pygame.SRCALPHA)
            add.fill((boost[0], boost[1], boost[2], 255))
            out.blit(add, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return out

    def take_damage(self, amount, particles, camera=None):
        if not self.alive:
            return
        self.hp -= amount
        if camera:
            camera.add_shake(5)
        # Phase 2 (half HP): roar, change form, enrage, unlock close moves
        if self.phase < 2 and self.hp <= self.max_hp * S.BOSS_PHASE2_THRESHOLD \
           and self.hp > 0:
            self._enter_phase2(particles, camera)
        if self.hp <= 0:
            self._die(particles, camera)

    def _enter_phase2(self, particles, camera):
        self.phase = 2
        self.enraged = True
        # swap to the BIGGER, RED form (poses/frame-counts match, index is safe)
        self.animations = self.anims_phase2
        self.frame_timer = 0
        # grow the body rect to match the bigger sprite, keeping the feet on the
        # ground and the centre fixed so it doesn't clip into terrain
        cx, bottom = self.rect.centerx, self.rect.bottom
        self.rect.width = int(130 * S.BOSS_PHASE2_SCALE)
        self.rect.height = int(170 * S.BOSS_PHASE2_SCALE)
        self.rect.centerx = cx
        self.rect.bottom = bottom
        self.sfx_roar.play()
        if particles:
            particles.emit_impact(self.rect.centerx, self.rect.centery,
                                  color=(240, 80, 60))
            particles.emit_death_burst(self.rect.centerx, self.rect.centery,
                                       color=(200, 40, 40))
        if camera:
            camera.add_shake(20)

    def _die(self, particles, camera):
        self.alive = False
        self.dying = True
        self.set_state("die")
        self.sfx_die.play()
        particles.emit_death_burst(self.rect.centerx, self.rect.centery,
                                   color=(110, 190, 90))
        particles.emit_impact(self.rect.centerx, self.rect.centery,
                              color=(160, 240, 100))
        if camera:
            camera.add_shake(25)

    # ---- main update ----------------------------------------------------
    def update(self, player, platforms, particles, camera=None):
        if not self._roared:
            self.sfx_roar.play()
            self._roared = True

        # close-range hazards keep animating/expiring even as the boss dies
        self._update_hazards(player, particles, camera)

        if self.dying:
            return

        # gravity (used by the stomp leap); the ogre NEVER walks horizontally
        self.vy += S.GRAVITY
        self.vy = min(self.vy, S.MAX_FALL_SPEED)
        self.vx = 0

        dist = player.rect.centerx - self.rect.centerx
        self.facing_right = dist > 0
        near = abs(dist) <= S.BOSS_NEAR_RANGE

        # passive contact damage: touching the stationary ogre hurts
        if self.contact_cd > 0:
            self.contact_cd -= 1
        player_on_top = player.rect.bottom <= self.rect.top + 30
        if self.contact_cd == 0 and player.alive and not player_on_top and \
           self.rect.colliderect(player.rect):
            player.take_damage(S.BOSS_CONTACT_DAMAGE, camera)
            self.contact_cd = 45

        if self.special is not None:
            self._run_special(player, particles, camera)
        else:
            if self.special_cd > 0:
                self.special_cd -= 1
            # CLOSE -> trigger a close-range special; otherwise spit acid
            if near and self.special_cd <= 0 and player.alive:
                self.special = self._pick_close_special()
                self.special_timer = 0
                self._special_fired = False
                self._stomp_jumped = False
                self._stomp_was_air = False
                self.set_state("attack")
            else:
                self._spit_acid(player)

        # pose when not mid-special
        if self.special is None:
            if self.spit_anim > 0:
                self.spit_anim -= 1
                self.set_state("attack")
            else:
                self.set_state("idle")

        # vertical move + collide only (no horizontal movement at all)
        self.on_ground = False
        self.rect.y += round(self.vy)
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vy > 0:
                    self.rect.bottom = p.top
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = p.bottom
                    self.vy = 0

    # ---- ranged acid spit ----------------------------------------------
    def _spit_acid(self, player):
        throw_cd_max = S.BOSS_THROW_COOLDOWN // (2 if self.enraged else 1)
        self.throw_cd -= 1
        if self.throw_cd <= 0 and player.alive:
            self.throw_cd = throw_cd_max
            mx = self.rect.centerx + (40 if self.facing_right else -40)
            my = self.rect.top + 50
            glob = PoisonGlob(mx, my, player.rect.centerx, player.rect.centery)
            self.pending_projectiles.append(glob)
            self.sfx_spit.play()
            self.spit_anim = 16

    # ---- close-range specials ------------------------------------------
    def _pick_close_special(self):
        """Stomp only pre-Phase 2; cycle Stomp/Spikes/Melee once in Phase 2."""
        if self.phase >= 2:
            seq = ("stomp", "spikes", "melee")
            choice = seq[self._p2_idx % len(seq)]
            self._p2_idx += 1
            return choice
        return "stomp"

    def _end_special(self):
        self.special = None
        self.special_timer = 0
        self._special_fired = False
        self.special_cd = S.BOSS_SPECIAL_COOLDOWN
        self.set_state("idle")

    def _run_special(self, player, particles, camera):
        self.special_timer += 1
        self.set_state("attack")
        if self.special == "stomp":
            self._run_stomp(player, particles, camera)
        elif self.special == "spikes":
            self._run_spikes(player, particles, camera)
        elif self.special == "melee":
            self._run_melee(player, particles, camera)

    # -- STOMP (jump, then slam on landing) --
    def _run_stomp(self, player, particles, camera):
        windup = S.BOSS_STOMP_WINDUP
        # crouch telegraph
        if not self._stomp_jumped:
            if self.special_timer < windup:
                if self.special_timer % 7 == 0 and camera:
                    camera.add_shake(3)
                return
            # leap
            self._stomp_jumped = True
            self.vy = -S.BOSS_STOMP_JUMP
            self._stomp_was_air = False
            return
        # airborne phase
        if not self.on_ground:
            self._stomp_was_air = True
            return
        # landed -> SLAM (fires once)
        if self._stomp_was_air and not self._special_fired:
            self._special_fired = True
            self._land_frame = self.special_timer
            self.sfx_stomp.play()
            self.sfx_roar.play()
            ground_y = self.rect.bottom
            self.shockwaves.append({"x": self.rect.centerx,
                                    "y": ground_y, "r": 0.0, "hit": False})
            if particles:
                particles.emit_impact(self.rect.centerx, ground_y,
                                      color=(190, 160, 120))
                particles.emit_death_burst(self.rect.centerx, ground_y,
                                           color=(170, 140, 100))
            if camera:
                camera.add_shake(S.BOSS_STOMP_SHAKE)   # stronger screen shake
            # Phase 2 only: landing erupts a ~1-second field of ground spikes
            if self.phase >= 2:
                self._spawn_landing_spikes(ground_y)
        # recover after the slam
        if self._special_fired and \
           self.special_timer - self._land_frame >= S.BOSS_STOMP_RECOVER:
            self._end_special()

    def _spawn_landing_spikes(self, ground_y):
        """A field of ground spikes that erupts when the ogre LANDS from a Stomp
        (Phase 2 only) and stays up for ~BOSS_JUMP_SPIKE_DURATION frames (~1s)."""
        n = S.BOSS_JUMP_SPIKE_COUNT
        # total lifetime = rise(10) + up_time + fall(12); solve for up_time
        up_time = max(4, S.BOSS_JUMP_SPIKE_DURATION - 10 - 12)
        for i in range(n):
            cx = self.rect.centerx + (i - (n - 1) / 2) * S.BOSS_JUMP_SPIKE_SPACING
            stagger = int(abs(i - (n - 1) / 2)) * 3
            self.boss_spikes.append(
                BossSpike(int(cx), ground_y, delay=stagger, up_time=up_time))

    # -- MELEE (Phase 2 close swipe, uses the attack animation) --
    def _run_melee(self, player, particles, camera):
        windup = S.BOSS_MELEE_WINDUP
        total = windup + S.BOSS_MELEE_RECOVER
        if self.special_timer < windup:
            return
        if not self._special_fired:
            self._special_fired = True
            reach = S.BOSS_MELEE_RANGE
            if self.facing_right:
                hx = self.rect.right
            else:
                hx = self.rect.left - reach
            swing = pygame.Rect(hx, self.rect.top + 30, reach, self.rect.height - 30)
            if player.alive and swing.colliderect(player.rect):
                player.take_damage(S.BOSS_MELEE_DAMAGE, camera)
            if particles:
                particles.emit_slash(
                    self.rect.right if self.facing_right else self.rect.left,
                    self.rect.centery, self.facing_right)
            if camera:
                camera.add_shake(8)
        if self.special_timer >= total:
            self._end_special()

    # -- SPIKES (Phase 2, when player is close) --
    def _run_spikes(self, player, particles, camera):
        windup = S.BOSS_SPIKE_WINDUP
        total = windup + S.BOSS_SPIKE_RECOVER
        if self.special_timer < windup:
            if self.special_timer == windup // 2 and particles:
                base = player.rect.centerx
                ground_y = self.rect.bottom
                n = S.BOSS_SPIKE_COUNT
                for i in range(n):
                    cx = base + (i - (n - 1) / 2) * S.BOSS_SPIKE_SPACING
                    particles.emit_impact(int(cx), ground_y, color=(150, 120, 90))
            return
        if not self._special_fired:
            self._special_fired = True
            self.sfx_stomp.play()
            base = player.rect.centerx
            ground_y = self.rect.bottom
            n = S.BOSS_SPIKE_COUNT
            for i in range(n):
                cx = base + (i - (n - 1) / 2) * S.BOSS_SPIKE_SPACING
                stagger = int(abs(i - (n - 1) / 2)) * 5   # ripple from centre
                self.boss_spikes.append(
                    BossSpike(int(cx), ground_y, delay=stagger))
            if camera:
                camera.add_shake(10)
        if self.special_timer >= total:
            self._end_special()

    # ---- update transient close-range hazards --------------------------
    def _update_hazards(self, player, particles, camera):
        for sp in self.boss_spikes:
            sp.update(player, camera)
        self.boss_spikes = [s for s in self.boss_spikes if not s.done]

        for sw in self.shockwaves:
            sw["r"] += S.BOSS_STOMP_SPEED
            if particles and int(sw["r"]) % 24 < S.BOSS_STOMP_SPEED:
                for sgn in (-1, 1):
                    particles.emit_poison(int(sw["x"] + sgn * sw["r"]),
                                          int(sw["y"]) - 6, count=2)
            if not sw["hit"] and player.alive and player.on_ground:
                if abs(player.rect.centerx - sw["x"]) <= sw["r"]:
                    if player.take_damage(S.BOSS_STOMP_DAMAGE, camera):
                        sw["hit"] = True
        self.shockwaves = [s for s in self.shockwaves if s["r"] < S.BOSS_STOMP_RANGE]

    def collect_projectiles(self):
        out = self.pending_projectiles
        self.pending_projectiles = []
        return out

    # ---- draw -----------------------------------------------------------
    def draw(self, surface, cam_x):
        for sw in self.shockwaves:
            self._draw_shockwave(surface, cam_x, sw)
        for sp in self.boss_spikes:
            sp.draw(surface, cam_x)

        loop = self.state != "die"
        img = self.animate(loop=loop)
        if not img:
            return
        iw, ih = img.get_size()
        draw_x = self.rect.centerx - iw // 2 - cam_x
        draw_y = self.rect.bottom - ih
        surface.blit(img, (draw_x, draw_y))

    @staticmethod
    def _draw_shockwave(surface, cam_x, sw):
        r = int(sw["r"])
        frac = 1.0 - min(1.0, r / max(1, S.BOSS_STOMP_RANGE))
        alpha = max(0, int(200 * frac))
        if alpha <= 0:
            return
        cx = sw["x"] - cam_x
        gy = int(sw["y"])
        for sgn in (-1, 1):
            fx = int(cx + sgn * r)
            ring = pygame.Surface((40, 60), pygame.SRCALPHA)
            pygame.draw.arc(ring, (210, 180, 130, alpha),
                            (0, 0, 40, 60), 0, math.pi * 2, 5)
            surface.blit(ring, (fx - 20, gy - 50))

    def draw_health_bar(self, surface):
        if not self.alive and self.finished:
            return
        bar_w, bar_h = 600, 22
        x = (S.SCREEN_W - bar_w) // 2
        y = 24
        pygame.draw.rect(surface, (40, 40, 40), (x - 3, y - 3, bar_w + 6, bar_h + 6))
        pygame.draw.rect(surface, (90, 0, 0), (x, y, bar_w, bar_h))
        frac = max(0, self.hp / self.max_hp)
        col = (200, 120, 0) if self.enraged else S.HUD_RED
        pygame.draw.rect(surface, col, (x, y, int(bar_w * frac), bar_h))
        mid_x = x + int(bar_w * S.BOSS_PHASE2_THRESHOLD)
        pygame.draw.line(surface, S.WHITE, (mid_x, y - 2), (mid_x, y + bar_h + 2), 2)
        try:
            font = pygame.font.SysFont("consolas", 16, bold=True)
            tag = "  [ENRAGED]" if self.phase >= 2 else ""
            label = font.render("AMALGAMATION" + tag, True, S.WHITE)
            surface.blit(label, (x, y + bar_h + 4))
        except Exception:
            pass

    @property
    def gone(self):
        return self.dying and self.finished
