"""
hud.py
------
Heads-up display matching your storyboard mockup:
  HP: [hearts]  (n/3 Lives)
  SCORE: 00xxxx
Plus simple poison and stage-clear banners.
"""

import pygame
from core import settings as S


def draw_hud(surface, player, score):
    font = pygame.font.SysFont("consolas", 22, bold=True)

    # HP hearts
    surface.blit(font.render("HP:", True, S.WHITE), (20, 16))
    for i in range(S.PLAYER_MAX_HP):
        x = 70 + i * 34
        filled = i < player.hp
        col = S.HUD_RED if filled else (70, 70, 70)
        pygame.draw.circle(surface, col, (x, 24), 7)
        pygame.draw.circle(surface, col, (x + 12, 24), 7)
        pygame.draw.polygon(surface, col, [(x - 7, 27), (x + 19, 27), (x + 6, 40)])

    # lives text
    lives_txt = font.render(f"({player.hp}/{S.PLAYER_MAX_HP} Lives)", True, S.WHITE)
    surface.blit(lives_txt, (70 + S.PLAYER_MAX_HP * 34 + 10, 16))

    # score
    score_txt = font.render(f"SCORE: {score:06d}", True, S.WHITE)
    surface.blit(score_txt, (20, 48))

    # poison indicator
    if player.poisoned:
        pf = pygame.SysFont = pygame.font.SysFont("consolas", 18, bold=True)
        ptxt = pf.render("POISONED", True, S.POISON_GREEN)
        surface.blit(ptxt, (20, 80))


def draw_controls(surface):
    """Compact, semi-transparent controls legend pinned to the top-right."""
    rows = [
        ("Move",    "A / D  or  \u2190 \u2192"),
        ("Run",     "Shift"),
        ("Jump",    "Space / W / \u2191"),
        ("Attack",  "F   (deflects acid!)"),
        ("Quit",    "Esc"),
    ]
    label_font = pygame.font.SysFont("consolas", 16, bold=True)
    key_font = pygame.font.SysFont("consolas", 16)
    title_font = pygame.font.SysFont("consolas", 15, bold=True)

    pad = 10
    line_h = 22
    title = title_font.render("CONTROLS", True, (255, 220, 120))
    label_w = max(label_font.size(r[0])[0] for r in rows)
    key_w = max(key_font.size(r[1])[0] for r in rows)
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


def draw_banner(surface, text, color=S.WHITE, sub=None):
    """Centre-screen banner for WIN / GAME OVER states."""
    big = pygame.font.SysFont("consolas", 64, bold=True)
    t = big.render(text, True, color)
    surface.blit(t, t.get_rect(center=(S.SCREEN_W // 2, S.SCREEN_H // 2 - 20)))
    if sub:
        small = pygame.font.SysFont("consolas", 26)
        st = small.render(sub, True, S.WHITE)
        surface.blit(st, st.get_rect(center=(S.SCREEN_W // 2, S.SCREEN_H // 2 + 50)))
