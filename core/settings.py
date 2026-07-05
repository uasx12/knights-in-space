"""
settings.py
-----------
Central configuration for Knights in Space - Combined (Stage 1 + Stage 2).
"""

import os as _os

# ---------- Display ----------
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60
TITLE = "Knights in Space"

# ---------- World / Physics ----------
GRAVITY = 0.8
MAX_FALL_SPEED = 18
TILE_SIZE = 64
LEVEL_WIDTH = 6400          # Stage 2 scroll length
GROUND_Y = 9 * TILE_SIZE    # = 576, aligned to tilemap surface

# ---------- Player ----------
PLAYER_SPEED = 5
PLAYER_RUN_SPEED = 8
PLAYER_JUMP = -18
PLAYER_MAX_HP = 3
PLAYER_DISPLAY_H = 120
PLAYER_INVULN_FRAMES = 60
PLAYER_ATTACK_FRAMES = 18
PLAYER_ATTACK_DAMAGE = 1
PLAYER_ATTACK_RANGE = 70

# ---------- Stage 2 Enemies (Mars zombies) ----------
ZOMBIE_HP = 2
ZOMBIE_SPEED = 1.5
ZOMBIE_DAMAGE = 1
ZOMBIE_DETECT_RANGE = 350
ZOMBIE_ATTACK_RANGE = 60
ZOMBIE_DISPLAY_H = 130

# ---------- Boss ----------
BOSS_HP = 20
BOSS_SPEED = 2
BOSS_CONTACT_DAMAGE = 1
BOSS_PROJECTILE_DAMAGE = 1
BOSS_THROW_COOLDOWN = 120
BOSS_ENRAGE_THRESHOLD = 0.4
BOSS_DISPLAY_H = 230
BOSS_PHASE2_SCALE = 1.35
BOSS_TINT_PHASE1 = (90, 175, 70)
BOSS_TINT_PHASE2 = (210, 55, 48)
BOSS_BOOST_PHASE2 = (80, 8, 6)
BOSS_PHASE2_THRESHOLD = 0.5
BOSS_NEAR_RANGE = 300
BOSS_SPECIAL_COOLDOWN = 130
BOSS_STOMP_WINDUP = 22
BOSS_STOMP_JUMP = 15
BOSS_STOMP_RECOVER = 24
BOSS_STOMP_DAMAGE = 1
BOSS_STOMP_RANGE = 520
BOSS_STOMP_SPEED = 18
BOSS_STOMP_SHAKE = 40
BOSS_JUMP_SPIKE_COUNT = 6
BOSS_JUMP_SPIKE_SPACING = 90
BOSS_JUMP_SPIKE_DURATION = 60
BOSS_MELEE_WINDUP = 16
BOSS_MELEE_RECOVER = 18
BOSS_MELEE_RANGE = 150
BOSS_MELEE_DAMAGE = 1
BOSS_DEFLECT_DAMAGE = 2
BOSS_SPIKE_WINDUP = 30
BOSS_SPIKE_RECOVER = 26
BOSS_SPIKE_COUNT = 4
BOSS_SPIKE_SPACING = 110
BOSS_SPIKE_DAMAGE = 1

# ---------- Projectiles ----------
PROJECTILE_SPEED = 7
PROJECTILE_GRAVITY = 0.25
POISON_PUDDLE_DURATION = 240
POISON_DAMAGE_PER_TICK = 1
POISON_TICK_INTERVAL = 45

# ---------- Effects ----------
SHAKE_DECAY = 0.85
HIT_FLASH_FRAMES = 8

# ---------- Obstacles ----------
SPIKE_DISPLAY_H = 120
SPIKE_GROUND_INSET = 12

# ---------- Low-health overlay ----------
LOW_HP_RED_MAX = 95
LOW_HP_VIGNETTE_MAX = 235

# ---------- Colors ----------
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 40, 40)
GREEN = (60, 200, 80)
POISON_GREEN = (120, 220, 60)
MARS_DUST = (180, 90, 60)
HUD_RED = (200, 30, 30)

# ---------- Asset paths ----------
_PROJECT_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
ASSET_ROOT = _os.path.join(_PROJECT_DIR, "assets")

# ---------- Stage 1 specific ----------
STAGE1_ASSET_ROOT = _os.path.join(ASSET_ROOT, "images")
STAGE1_ENEMY_H = 110        # display height for stage 1 zombie sprites
STAGE1_ENEMY_BASE_SPEED = 1.8
STAGE1_ENEMY_ATTACK_RANGE = 55
STAGE1_ENEMY_DETECT_RANGE = SCREEN_W   # always chases

# Stage 1 wave definitions — each wave adds more, faster, tougher enemies
STAGE1_WAVES = [
    {"count": 3, "speed": 1.8, "hp": 2},   # Wave 1 — warm-up
    {"count": 5, "speed": 2.3, "hp": 2},   # Wave 2 — pressure
    {"count": 7, "speed": 2.8, "hp": 2},   # Wave 3 — finale
]

# ==========================================================================
# ANIMATION SPECS
# ==========================================================================
ANIM = {
    # Knight (protagonist) — Stage 2 sprite sheets
    "knight_idle":   {"sheet": f"{ASSET_ROOT}/Character/knight/Idle.png",   "frames": 4,  "trim": True},
    "knight_walk":   {"sheet": f"{ASSET_ROOT}/Character/knight/Walk.png",   "frames": 8,  "trim": True},
    "knight_run":    {"sheet": f"{ASSET_ROOT}/Character/knight/Run.png",    "frames": 7,  "trim": True},
    "knight_jump":   {"sheet": f"{ASSET_ROOT}/Character/knight/Jump.png",   "frames": 6,  "trim": True},
    "knight_attack": {"sheet": f"{ASSET_ROOT}/Character/knight/Attack.png", "frames": 5,  "trim": True},
    "knight_hurt":   {"sheet": f"{ASSET_ROOT}/Character/knight/Hurt.png",   "frames": 2,  "trim": True},
    "knight_die":    {"sheet": f"{ASSET_ROOT}/Character/knight/Dead.png",   "frames": 6,  "trim": True},

    # Stage 2 zombie enemies — sprite sheets
    "zombie_idle":   {"sheet": f"{ASSET_ROOT}/Character/zombie/Idle.png",   "frames": 6,  "trim": True},
    "zombie_walk":   {"sheet": f"{ASSET_ROOT}/Character/zombie/Walk.png",   "frames": 5,  "trim": True},
    "zombie_attack": {"sheet": f"{ASSET_ROOT}/Character/zombie/Attack.png", "frames": 3,  "trim": True},
    "zombie_die":    {"sheet": f"{ASSET_ROOT}/Character/zombie/Dead.png",   "frames": 4,  "trim": True},
    "zombie_jump":   {"sheet": f"{ASSET_ROOT}/Character/zombie/Jump.png",   "frames": 8,  "trim": True},

    # Boss — reuses zombie sheets at larger scale
    "boss_idle":     {"sheet": f"{ASSET_ROOT}/Character/zombie/Idle.png",   "frames": 6,  "trim": True},
    "boss_attack":   {"sheet": f"{ASSET_ROOT}/Character/zombie/Attack.png", "frames": 3,  "trim": True},
    "boss_die":      {"sheet": f"{ASSET_ROOT}/Character/zombie/Dead.png",   "frames": 4,  "trim": True},

    # Erupting spikes
    "spike_erupt":   {"sheet": f"{ASSET_ROOT}/Stage2/spikes_erupt.png", "frames": 4, "trim": False},
}

# Single images / audio
PATHS = {
    # Stage 1 background (space/moon vista from KnightsInSpace)
    "bg_stage1":    f"{ASSET_ROOT}/images/image.png",

    # Stage 2 Mars backdrop
    "bg_mars":      f"{ASSET_ROOT}/Stage2/Mars_Terrain.png",
    "bg_far":       f"{ASSET_ROOT}/Stage2/bg_mars_far.png",
    "bg_mid":       f"{ASSET_ROOT}/Stage2/bg_mars_mid.png",
    "bg_near":      f"{ASSET_ROOT}/Stage2/bg_mars_near.png",

    # Tileset
    "tileset":      f"{ASSET_ROOT}/Stage2/tileset.png",
    "projectile":   f"{ASSET_ROOT}/Stage2/poison_glob.png",

    # Audio (shared)
    "bgm_stage1":   f"{ASSET_ROOT}/Audio/mars_explore.ogg",   # reuse Stage 2 bgm for Stage 1
    "bgm_stage2":   f"{ASSET_ROOT}/Audio/mars_explore.ogg",
    "bgm_boss":     f"{ASSET_ROOT}/Audio/boss_fight.ogg",
    "bgm_victory":  f"{ASSET_ROOT}/Audio/boss_fight.ogg",     # fallback

    # SFX
    "sfx_attack":   f"{ASSET_ROOT}/Audio/SFX/attack.wav",
    "sfx_hurt":     f"{ASSET_ROOT}/Audio/SFX/hurt.wav",
    "sfx_death":    f"{ASSET_ROOT}/Audio/SFX/game_over.wav",
    "sfx_jump":     f"{ASSET_ROOT}/Audio/SFX/attack.wav",
    "sfx_enemy_die":f"{ASSET_ROOT}/Audio/SFX/hurt.wav",
    "sfx_throw":    f"{ASSET_ROOT}/Audio/SFX/attack.wav",
    "sfx_splat":    f"{ASSET_ROOT}/Audio/SFX/hurt.wav",
    "sfx_poison":   f"{ASSET_ROOT}/Audio/SFX/hurt.wav",
    "sfx_pickup":   f"{ASSET_ROOT}/Audio/SFX/attack.wav",
    "sfx_boss_roar":f"{ASSET_ROOT}/Audio/SFX/game_over.wav",
    "sfx_game_over":f"{ASSET_ROOT}/Audio/SFX/game_over.wav",
}

# Tileset config
TILESET_TILE = 32
