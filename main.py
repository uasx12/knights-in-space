"""
main.py
-------
Knights in Space — Combined Edition
Menu → Stage 1 (wave arena) → Stage 2 (Mars scrolling level + boss)

Run from the project root:
    python main.py
"""

import sys
import pygame

# Initialise before any module that imports pygame
pygame.init()
try:
    pygame.mixer.init()
except Exception:
    pass

from core import settings as S
from core import assets as A


# --------------------------------------------------------------------------
# Menu
# --------------------------------------------------------------------------
_menu_bg_cache = {}

def _get_menu_bg(screen):
    key = "menu"
    if key not in _menu_bg_cache:
        import os
        path = S.PATHS["bg_stage1"]
        if os.path.exists(path):
            raw = pygame.image.load(path).convert()
            _menu_bg_cache[key] = pygame.transform.smoothscale(
                raw, (screen.get_width(), screen.get_height()))
        else:
            surf = pygame.Surface((screen.get_width(), screen.get_height()))
            surf.fill((8, 8, 28))
            import random; random.seed(42)
            for _ in range(200):
                sx = random.randint(0, screen.get_width())
                sy = random.randint(0, screen.get_height())
                br = random.randint(120, 255)
                pygame.draw.circle(surf, (br, br, br), (sx, sy),
                                   random.choice([1, 1, 1, 2]))
            _menu_bg_cache[key] = surf
    return _menu_bg_cache[key]


BUTTON_W = 280
BUTTON_H = 60

BUTTONS = [
    {"label": "NEW GAME",     "action": "play"},
    {"label": "STAGE SELECT", "action": "select"},
    {"label": "QUIT",         "action": "quit"},
]

_OVERLAY    = (5,   5,   20,  170)
_BTN_NORM   = (20,  20,  50,  200)
_BTN_HOVER  = (60,  70,  140, 230)
_BORDER     = (160, 180, 255, 255)
_TEXT       = (255, 255, 255)
_TITLE_COL  = (190, 215, 255)


def draw_menu(screen):
    W, H = screen.get_size()
    screen.blit(_get_menu_bg(screen), (0, 0))

    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill(_OVERLAY)
    screen.blit(overlay, (0, 0))

    title_f = pygame.font.SysFont("impact", 68)
    sub_f   = pygame.font.SysFont("arial",  20)
    btn_f   = pygame.font.SysFont("arial",  24, bold=True)

    # Title
    t = title_f.render("KNIGHTS IN SPACE", True, _TITLE_COL)
    screen.blit(t, t.get_rect(center=(W // 2, 155)))

    sub = sub_f.render("Stage 1: Space Arena  |  Stage 2: Mars Expedition", True,
                        (140, 170, 220))
    screen.blit(sub, sub.get_rect(center=(W // 2, 218)))
    pygame.draw.line(screen, (90, 110, 200), (W//2 - 200, 240), (W//2 + 200, 240), 1)

    bx   = W // 2 - BUTTON_W // 2
    mpos = pygame.mouse.get_pos()
    rects = []

    for i, btn in enumerate(BUTTONS):
        by   = 270 + i * (BUTTON_H + 20)
        rect = pygame.Rect(bx, by, BUTTON_W, BUTTON_H)
        rects.append(rect)
        hov  = rect.collidepoint(mpos)

        surf = pygame.Surface((BUTTON_W, BUTTON_H), pygame.SRCALPHA)
        surf.fill(_BTN_HOVER if hov else _BTN_NORM)
        screen.blit(surf, rect.topleft)
        pygame.draw.rect(screen, _BORDER, rect, 2, border_radius=4)

        lbl = btn_f.render(btn["label"], True, _TEXT)
        screen.blit(lbl, lbl.get_rect(center=rect.center))

    return rects


def handle_menu_click(pos, rects):
    for i, r in enumerate(rects):
        if r.collidepoint(pos):
            return BUTTONS[i]["action"]
    return None


# --------------------------------------------------------------------------
# Stage-select overlay (shown on top of the menu)
# --------------------------------------------------------------------------
SEL_BUTTONS = [
    {"label": "STAGE 1 — Space Arena", "action": "stage1"},
    {"label": "STAGE 2 — Mars Expedition", "action": "stage2"},
    {"label": "BACK",                    "action": "back"},
]


def draw_stage_select(screen):
    W, H = screen.get_size()
    # dim the menu behind
    dim = pygame.Surface((W, H), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 180))
    screen.blit(dim, (0, 0))

    panel_w, panel_h = 520, 310
    px = (W - panel_w) // 2
    py = (H - panel_h) // 2
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((12, 14, 36, 240))
    pygame.draw.rect(panel, _BORDER, panel.get_rect(), 2, border_radius=6)
    screen.blit(panel, (px, py))

    hf = pygame.font.SysFont("impact", 32)
    hdr = hf.render("SELECT STAGE", True, _TITLE_COL)
    screen.blit(hdr, hdr.get_rect(center=(W // 2, py + 36)))

    btn_f = pygame.font.SysFont("arial", 21, bold=True)
    mpos = pygame.mouse.get_pos()
    rects = []

    for i, btn in enumerate(SEL_BUTTONS):
        bw, bh = 380, 52
        bx_ = (W - bw) // 2
        by_ = py + 80 + i * (bh + 16)
        rect = pygame.Rect(bx_, by_, bw, bh)
        rects.append(rect)
        hov = rect.collidepoint(mpos)
        surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        surf.fill(_BTN_HOVER if hov else _BTN_NORM)
        screen.blit(surf, rect.topleft)
        pygame.draw.rect(screen, _BORDER, rect, 2, border_radius=4)
        lbl = btn_f.render(btn["label"], True, _TEXT)
        screen.blit(lbl, lbl.get_rect(center=rect.center))

    return rects


def handle_select_click(pos, rects):
    for i, r in enumerate(rects):
        if r.collidepoint(pos):
            return SEL_BUTTONS[i]["action"]
    return None


# --------------------------------------------------------------------------
# Transition screen between stages
# --------------------------------------------------------------------------
def draw_transition(screen, text, sub, color=S.GREEN):
    screen.fill(S.BLACK)
    big   = pygame.font.SysFont("consolas", 60, bold=True)
    small = pygame.font.SysFont("consolas", 26)
    t  = big.render(text, True, color)
    st = small.render(sub, True, S.WHITE)
    screen.blit(t,  t.get_rect(center=(S.SCREEN_W // 2, S.SCREEN_H // 2 - 30)))
    screen.blit(st, st.get_rect(center=(S.SCREEN_W // 2, S.SCREEN_H // 2 + 44)))
    pygame.display.flip()


# --------------------------------------------------------------------------
# Run a stage and wait for a keypress before returning
# --------------------------------------------------------------------------
def run_stage1(screen, clock):
    from stage1 import Stage1
    result = Stage1(screen, clock).run()
    return result   # "win", "gameover", or other if ESC pressed


def run_stage2(screen, clock):
    from stage2 import Stage2
    result = Stage2(screen, clock).run()
    return result   # "win", "gameover"


# --------------------------------------------------------------------------
# Main game loop
# --------------------------------------------------------------------------
def main():
    screen = pygame.display.set_mode((S.SCREEN_W, S.SCREEN_H))
    pygame.display.set_caption(S.TITLE)
    clock = pygame.time.Clock()

    MENU       = "menu"
    SELECTING  = "selecting"   # stage-select overlay

    state      = MENU
    menu_rects = []
    sel_rects  = []
    running    = True

    while running:
        clock.tick(S.FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state == SELECTING:
                        state = MENU
                    else:
                        running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == MENU:
                    action = handle_menu_click(event.pos, menu_rects)
                    if action == "play":
                        # Linear run: Stage 1 → if won → Stage 2 → back to menu
                        r1 = run_stage1(screen, clock)
                        if r1 == "win":
                            draw_transition(screen,
                                            "STAGE 1 CLEAR!",
                                            "Prepare for Stage 2: Mars…   (any key)",
                                            S.GREEN)
                            _wait_key(clock)
                            r2 = run_stage2(screen, clock)
                            if r2 == "win":
                                draw_transition(screen,
                                                "VICTORY!",
                                                "Both stages cleared!   (any key)",
                                                (255, 215, 0))
                                _wait_key(clock)
                        # fall back to menu regardless
                    elif action == "select":
                        state = SELECTING
                    elif action == "quit":
                        running = False

                elif state == SELECTING:
                    action = handle_select_click(event.pos, sel_rects)
                    if action == "stage1":
                        r = run_stage1(screen, clock)
                        if r == "win":
                            draw_transition(screen,
                                            "STAGE 1 CLEAR!",
                                            "Any key to return to menu",
                                            S.GREEN)
                            _wait_key(clock)
                        state = MENU
                    elif action == "stage2":
                        r = run_stage2(screen, clock)
                        if r == "win":
                            draw_transition(screen,
                                            "STAGE 2 CLEAR!",
                                            "Any key to return to menu",
                                            S.GREEN)
                            _wait_key(clock)
                        state = MENU
                    elif action == "back":
                        state = MENU

        # --- draw ---
        if state == MENU:
            menu_rects = draw_menu(screen)
        elif state == SELECTING:
            menu_rects = draw_menu(screen)   # keep menu drawn behind panel
            sel_rects  = draw_stage_select(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


def _wait_key(clock):
    """Block until the player presses any key."""
    while True:
        clock.tick(S.FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                return
            if event.type == pygame.MOUSEBUTTONDOWN:
                return


if __name__ == "__main__":
    main()
