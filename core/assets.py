"""
assets.py
---------
Helpers for loading images, animation sequences, and sounds.

IMPORTANT: every loader fails gracefully. If a file/folder is missing,
it returns a coloured placeholder surface (or a silent dummy sound) so
the game still runs while you're still gathering art. Replace the
placeholders by simply dropping the real files into the paths in
settings.PATHS.
"""

import os
import pygame
from core import settings as S


# --------------------------------------------------------------------------
# Placeholder factory: a labelled coloured box, used when art is missing.
# --------------------------------------------------------------------------
def _placeholder(size=(64, 96), color=(150, 150, 150), label=""):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((*color, 255))
    pygame.draw.rect(surf, S.BLACK, surf.get_rect(), 2)
    if label:
        try:
            font = pygame.font.SysFont("consolas", 14)
            txt = font.render(label, True, S.BLACK)
            surf.blit(txt, (4, 4))
        except Exception:
            pass
    return surf


def load_image(path, size=None, color=(150, 150, 150), label="IMG"):
    """Load one image, scaled optionally. Returns placeholder if missing."""
    if os.path.exists(path):
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.smoothscale(img, size)
        return img
    return _placeholder(size or (64, 96), color, label)


def load_sequence(folder, size=None, color=(150, 150, 150), label="ANIM"):
    """
    Load all PNGs in a folder (sorted by filename) as an animation list.
    Matches the PNG-sequence approach described in your reference report.
    Returns a single-frame placeholder list if the folder is missing/empty.
    """
    frames = []
    if os.path.isdir(folder):
        names = sorted(f for f in os.listdir(folder)
                       if f.lower().endswith((".png", ".jpg", ".jpeg")))
        for n in names:
            img = pygame.image.load(os.path.join(folder, n)).convert_alpha()
            if size:
                img = pygame.transform.smoothscale(img, size)
            frames.append(img)
    if not frames:
        frames = [_placeholder(size or (64, 96), color, label)]
    return frames


def slice_sheet(path, frame_count=None, frame_w=None, size=None,
                color=(150, 150, 150), label="SHEET", margin=0, spacing=0,
                trim=False, pad=4):
    """
    Slice a HORIZONTAL sprite sheet (one row of frames) into a frame list.

    CraftPix packs ship as horizontal strips, e.g. a 768x128 sheet is
    6 frames of 128x128. Provide ONE of:
        frame_count : how many frames are in the strip (frame width is
                      derived from sheet_width / frame_count)
        frame_w     : explicit width of each frame in pixels

    margin  : transparent border around the whole sheet (px)
    spacing : gap between frames (px)
    size    : optional (w, h) to scale EACH frame to after slicing
    trim    : if True, crop every frame to ONE shared content bounding box
              (computed across all frames) so the character fills the frame
              and stays aligned across the animation. Removes the big
              transparent padding common in CraftPix frames.
    pad     : pixels of breathing room to keep around the shared bbox.

    Falls back to a single placeholder frame if the file is missing.
    """
    if not os.path.exists(path):
        return [_placeholder(size or (64, 96), color, label)]

    sheet = pygame.image.load(path).convert_alpha()
    sw, sh = sheet.get_size()
    fh = sh - margin * 2

    if frame_count and not frame_w:
        usable = sw - margin * 2 - spacing * (frame_count - 1)
        fw = usable // frame_count
    elif frame_w:
        fw = frame_w
        frame_count = (sw - margin * 2 + spacing) // (fw + spacing)
    else:
        fw, frame_count = sw, 1

    # first pass: cut raw frames
    raw = []
    for i in range(frame_count):
        x = margin + i * (fw + spacing)
        rect = pygame.Rect(x, margin, fw, fh)
        raw.append(sheet.subsurface(rect).copy())

    # optional trim: compute a SHARED bounding box over all frames so the
    # whole animation is cropped identically (keeps feet/limbs aligned)
    if trim:
        bbox = _shared_bbox(raw, pad)
        if bbox:
            bx, by, bw, bh = bbox
            cropped = []
            for fr in raw:
                sub = pygame.Surface((bw, bh), pygame.SRCALPHA)
                sub.blit(fr, (0, 0), pygame.Rect(bx, by, bw, bh))
                cropped.append(sub)
            raw = cropped

    # scale to requested display size
    frames = []
    for fr in raw:
        frames.append(pygame.transform.smoothscale(fr, size) if size else fr)
    return frames


def _shared_bbox(frames, pad=4):
    """Union bounding box of non-transparent pixels across all frames."""
    minx = miny = 10 ** 9
    maxx = maxy = -1
    for fr in frames:
        r = fr.get_bounding_rect(min_alpha=20)  # tight box of opaque pixels
        if r.width == 0 or r.height == 0:
            continue
        minx = min(minx, r.left)
        miny = min(miny, r.top)
        maxx = max(maxx, r.right)
        maxy = max(maxy, r.bottom)
    if maxx < 0:
        return None
    fw, fh = frames[0].get_size()
    minx = max(0, minx - pad)
    miny = max(0, miny - pad)
    maxx = min(fw, maxx + pad)
    maxy = min(fh, maxy + pad)
    return (minx, miny, maxx - minx, maxy - miny)


def load_animation(spec, size=None, color=(150, 150, 150), label="ANIM"):
    """
    Universal animation loader. Looks at `spec` and does the right thing,
    so you don't have to care whether assets came as a sheet or a folder.

    spec can be:
      - a string path to a FOLDER of PNGs           -> load_sequence()
      - a string path to a single sprite-sheet PNG  -> slice_sheet() (auto: 1 frame
            unless you pass a dict with frame info)
      - a dict: {"sheet": path, "frames": N}        -> slice_sheet(frame_count=N)
                {"sheet": path, "frame_w": W}        -> slice_sheet(frame_w=W)
                {"folder": path}                     -> load_sequence()
    """
    if isinstance(spec, dict):
        if "folder" in spec:
            return load_sequence(spec["folder"], size, color, label)
        if "sheet" in spec:
            return slice_sheet(spec["sheet"],
                               frame_count=spec.get("frames"),
                               frame_w=spec.get("frame_w"),
                               size=size, color=color, label=label,
                               margin=spec.get("margin", 0),
                               spacing=spec.get("spacing", 0),
                               trim=spec.get("trim", False),
                               pad=spec.get("pad", 4))
        return [_placeholder(size or (64, 96), color, label)]

    # plain string
    if os.path.isdir(spec):
        return load_sequence(spec, size, color, label)
    if spec.lower().endswith((".png", ".jpg", ".jpeg")) and os.path.exists(spec):
        return slice_sheet(spec, size=size, color=color, label=label)
    # missing -> placeholder
    return [_placeholder(size or (64, 96), color, label)]


def scale_frames_to_height(frames, target_h):
    """Scale a frame list so each frame is `target_h` px tall, preserving
    aspect ratio. Use this for character sheets so animations with different
    trimmed sizes (idle vs jump) keep consistent proportions on screen."""
    out = []
    for fr in frames:
        w, h = fr.get_size()
        if h == 0:
            out.append(fr)
            continue
        scale = target_h / h
        out.append(pygame.transform.smoothscale(
            fr, (max(1, int(w * scale)), target_h)))
    return out


class DummySound:
    """Stand-in so sfx.play() never crashes when a file is missing."""
    def play(self, *a, **k):
        pass
    def set_volume(self, *a, **k):
        pass


def load_sound(path, volume=0.6):
    if os.path.exists(path):
        try:
            snd = pygame.mixer.Sound(path)
            snd.set_volume(volume)
            return snd
        except Exception:
            return DummySound()
    return DummySound()


def play_music(path, volume=0.5, loop=True, fade_ms=600):
    """Load + play a streamed BGM track with fade-in. No-op if missing."""
    if os.path.exists(path):
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1 if loop else 0, fade_ms=fade_ms)
        except Exception:
            pass


def fade_music(ms=500):
    """Fade out current BGM (mirrors the fade-out technique in your report)."""
    try:
        pygame.mixer.music.fadeout(ms)
    except Exception:
        pass

def verify_assets():
    """Print a startup report of which assets were found vs. missing.
    Call once at game start so a silent placeholder fallback is obvious.
    Returns (found, missing) counts."""
    from core import settings as S
    found, missing = 0, 0
    print("=" * 56)
    print("ASSET CHECK  (root: %s)" % S.ASSET_ROOT)
    print("-" * 56)
    # animations
    for key, spec in S.ANIM.items():
        path = spec.get("sheet") or spec.get("folder", "")
        ok = os.path.exists(path)
        found += ok
        missing += not ok
        print(f"  [{'OK ' if ok else 'MISS'}] {key:14} {path}")
    # single images + audio
    for key, path in S.PATHS.items():
        ok = os.path.exists(path)
        found += ok
        missing += not ok
        tag = 'OK ' if ok else 'MISS'
        print(f"  [{tag}] {key:14} {path}")
    print("-" * 56)
    print(f"  {found} found, {missing} missing "
          f"(missing ones use placeholders/silent sound)")
    print("=" * 56)
    return found, missing
