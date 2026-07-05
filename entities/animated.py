"""
animated.py
-----------
Base class for anything that plays frame-list animations (idle/walk/etc. as
separate lists, advanced by a per-frame timer).

A note on the previous "doubled/flickering" bug: nothing here caused it on its
own, but this class is where state changes land, so two things are worth
keeping correct:

  * set_state() now returns True only when the state ACTUALLY changes, so
    callers can react to a real transition instead of every frame.
  * animations advance exactly ONCE per draw call (callers must call animate()
    once per frame), so playback speed is stable.
"""

import pygame


class AnimatedSprite:
    def __init__(self, animations, start_state, frame_delay=6, state_delays=None):
        """
        animations  : dict[str, list[Surface]]
        start_state : key into animations
        frame_delay : default frames to wait before advancing one image
        state_delays: optional dict[str, int] overriding frame_delay per state
                      (e.g. a snappier attack swing)
        """
        self.animations = animations
        self.state = start_state
        self.frame_delay = frame_delay
        self.state_delays = state_delays or {}
        self.frame_index = 0
        self.frame_timer = 0
        self.facing_right = True
        self.finished = False   # True when a non-looping anim reaches its end

    def set_state(self, state, reset=True):
        """Switch animation state. Returns True if the state actually changed."""
        if state == self.state or state not in self.animations:
            return False
        self.state = state
        if reset:
            self.frame_index = 0
            self.frame_timer = 0
            self.finished = False
        return True

    def _delay(self):
        return self.state_delays.get(self.state, self.frame_delay)

    def current_frame_count(self):
        return len(self.animations.get(self.state, []))

    def animate(self, loop=True):
        frames = self.animations.get(self.state, [])
        if not frames:
            return None
        self.frame_timer += 1
        if self.frame_timer >= self._delay():
            self.frame_timer = 0
            self.frame_index += 1
            if self.frame_index >= len(frames):
                if loop:
                    self.frame_index = 0
                else:
                    self.frame_index = len(frames) - 1
                    self.finished = True
        # clamp in case the state changed without a reset
        if self.frame_index >= len(frames):
            self.frame_index = len(frames) - 1
        img = frames[self.frame_index]
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
        return img
