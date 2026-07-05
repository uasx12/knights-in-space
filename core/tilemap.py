"""
tilemap.py
----------
Grid-based terrain for Stage 2. Lets you paint the level with a text grid
and renders it from a tileset image. Each character in the grid maps to a
tile (or empty space). Solid tiles also produce collision Rects for the
player/enemies.

If the tileset image is missing, tiles draw as Mars-toned coloured blocks
so the level is still playable while you source art.

USAGE in stage2.py:
    tm = TileMap(LEVEL_GRID)
    platforms = tm.solid_rects()      # feed these to player/enemy collision
    tm.draw(screen, cam_x)            # draw terrain

The tileset is assumed to be a grid of TILESET_TILE-sized tiles. Set which
tile index each symbol uses in TILE_DEFS below.
"""

import pygame
from core import settings as S
from core import assets as A


# Map a grid symbol -> (tile_index_in_tileset, is_solid, fallback_color)
# tile_index is read left-to-right, top-to-bottom in the tileset image.
# Indices match tools/make_mars_tileset.py output order.
TILE_DEFS = {
    "#": (0, True,  (156, 74, 49)),    # Mars regolith ground
    "=": (1, True,  (110, 118, 130)),  # metal catwalk / ledge
    "x": (2, True,  (138, 96, 60)),    # supply crate / wall
    "H": (3, True,  (214, 178, 58)),   # hazard-stripe floor panel
    "C": (4, False, (120, 224, 232)),  # energy conduit (decor, non-solid)
    "r": (5, True,  (120, 55, 38)),    # rubble ground variant
    "W": (6, True,  (110, 118, 130)),  # riveted hull wall
    "g": (7, True,  (181, 92, 62)),    # pebbled ground variant
    ".": (None, False, None),          # empty (air)
    " ": (None, False, None),          # empty (air)
}

GRID_TILE = S.TILE_SIZE   # on-screen size of each tile (px)


class TileMap:
    def __init__(self, grid_rows, tileset_path=None):
        """
        grid_rows : list of equal-length strings; each char is a tile symbol.
                    Row 0 is the TOP of the level.
        """
        self.grid = grid_rows
        self.rows = len(grid_rows)
        self.cols = max((len(r) for r in grid_rows), default=0)
        self.tile_imgs = self._load_tiles(tileset_path or S.PATHS["tileset"])

    def _load_tiles(self, path):
        """Slice the tileset into a list of GRID_TILE-sized tile surfaces."""
        import os
        imgs = {}
        if os.path.exists(path):
            sheet = pygame.image.load(path).convert_alpha()
            sw, sh = sheet.get_size()
            ts = S.TILESET_TILE
            per_row = max(1, sw // ts)
            for sym, (idx, solid, _) in TILE_DEFS.items():
                if idx is None:
                    continue
                tx = (idx % per_row) * ts
                ty = (idx // per_row) * ts
                if tx + ts <= sw and ty + ts <= sh:
                    tile = sheet.subsurface(pygame.Rect(tx, ty, ts, ts)).copy()
                    imgs[sym] = pygame.transform.scale(tile, (GRID_TILE, GRID_TILE))
        return imgs  # may be empty -> fallback colours used

    def solid_rects(self):
        """Build collision Rects for every solid tile."""
        rects = []
        for r, row in enumerate(self.grid):
            for c, ch in enumerate(row):
                defn = TILE_DEFS.get(ch)
                if defn and defn[1]:  # is_solid
                    rects.append(pygame.Rect(c * GRID_TILE, r * GRID_TILE,
                                             GRID_TILE, GRID_TILE))
        return self._merge_horizontal(rects)

    @staticmethod
    def _merge_horizontal(rects):
        """Merge adjacent same-row tiles into longer Rects (fewer collisions)."""
        if not rects:
            return rects
        rects.sort(key=lambda r: (r.y, r.x))
        merged = [rects[0].copy()]
        for r in rects[1:]:
            last = merged[-1]
            if r.y == last.y and r.x == last.right:
                last.width += r.width
            else:
                merged.append(r.copy())
        return merged

    @property
    def pixel_width(self):
        return self.cols * GRID_TILE

    def draw(self, surface, cam_x):
        # only draw tiles within the visible window for performance
        first_col = max(0, int(cam_x // GRID_TILE))
        last_col = min(self.cols, int((cam_x + S.SCREEN_W) // GRID_TILE) + 1)
        for r in range(self.rows):
            row = self.grid[r]
            for c in range(first_col, min(last_col, len(row))):
                ch = row[c]
                defn = TILE_DEFS.get(ch)
                if not defn or defn[0] is None:
                    continue
                x = c * GRID_TILE - cam_x
                y = r * GRID_TILE
                img = self.tile_imgs.get(ch)
                if img:
                    surface.blit(img, (x, y))
                else:
                    # fallback coloured block
                    pygame.draw.rect(surface, defn[2], (x, y, GRID_TILE, GRID_TILE))
                    pygame.draw.rect(surface, (40, 30, 28),
                                     (x, y, GRID_TILE, GRID_TILE), 1)
