"""System-level input using PyAutoGUI."""

from __future__ import annotations

import os
import random
import time


_SAFE_CLICK_HALF_RATIO = 0.30


def choose_click_point(
    center_x: int,
    center_y: int,
    width: int,
    height: int,
    excluded: set[tuple[int, int]] | None = None,
    rng=None,
) -> tuple[int, int]:
    """Choose a non-edge point in an element bounding box.

    ``center_x`` and ``center_y`` use the same center-coordinate convention as
    ``get_interactive_elements``. The returned point is sampled from the central
    60% of the box, leaving a 20% safety margin on every side. Points in
    ``excluded`` are skipped so a caller can avoid repeating positions.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")

    random_source = rng if rng is not None else random
    radius_x = int(width * _SAFE_CLICK_HALF_RATIO)
    radius_y = int(height * _SAFE_CLICK_HALF_RATIO)
    min_x, max_x = center_x - radius_x, center_x + radius_x
    min_y, max_y = center_y - radius_y, center_y + radius_y

    blocked = excluded if excluded is not None else set()
    columns = max_x - min_x + 1
    rows = max_y - min_y + 1
    point_count = columns * rows
    if len(blocked) >= point_count:
        blocked = set()

    # Usually succeeds immediately while preserving a natural random spread.
    for _ in range(16):
        point = (
            random_source.randint(min_x, max_x),
            random_source.randint(min_y, max_y),
        )
        if point not in blocked:
            return point

    # Near exhaustion, scan from a random offset to guarantee an unused result
    # without building a potentially large list of every point in the box.
    start = random_source.randrange(point_count)
    for offset in range(point_count):
        index = (start + offset) % point_count
        point = (min_x + index % columns, min_y + index // columns)
        if point not in blocked:
            return point

    raise RuntimeError("safe click area unexpectedly has no available point")


def _get_default_resolution() -> tuple[int, int]:
    """Get default resolution from XVFB_RESOLUTION env var (WxH format)."""
    xvfb_res = os.environ.get("XVFB_RESOLUTION", "1920x1080")
    parts = xvfb_res.split("x")
    width = int(parts[0]) if parts else 1920
    height = int(parts[1]) if len(parts) > 1 else 1080
    return width, height


class System:
    """System-level mouse and keyboard input via PyAutoGUI."""

    def __init__(self) -> None:
        self._pyautogui = None
        self._window_offset = {"x": 0, "y": 0}
        self._click_history: dict[
            tuple[int, int, int, int], set[tuple[int, int]]
        ] = {}

    @property
    def is_ready(self) -> bool:
        """Check if pyautogui is initialized."""
        return self._pyautogui is not None

    @property
    def window_offset(self) -> dict:
        """Get current window offset."""
        return self._window_offset

    @window_offset.setter
    def window_offset(self, value: dict) -> None:
        """Set window offset."""
        self._window_offset = value

    def init(self) -> None:
        """Initialize pyautogui after X display is available."""
        if self._pyautogui is not None:
            return

        xauth_path = os.path.expanduser("~/.Xauthority")
        if not os.path.exists(xauth_path):
            open(xauth_path, "a").close()
        os.environ.setdefault("XAUTHORITY", xauth_path)

        import pyautogui

        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        self._pyautogui = pyautogui

    def screen_coords(self, x: int, y: int) -> tuple[int, int]:
        """Convert viewport coords to screen coords."""
        return (x + self._window_offset["x"], y + self._window_offset["y"])

    def random_click_point(
        self, center_x: int, center_y: int, width: int, height: int
    ) -> tuple[int, int]:
        """Choose and remember a safe randomized point for an element box."""
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive")

        box = (center_x, center_y, width, height)
        if box not in self._click_history and len(self._click_history) >= 128:
            self._click_history.pop(next(iter(self._click_history)))
        history = self._click_history.setdefault(box, set())

        radius_x = int(width * _SAFE_CLICK_HALF_RATIO)
        radius_y = int(height * _SAFE_CLICK_HALF_RATIO)
        point_count = (radius_x * 2 + 1) * (radius_y * 2 + 1)
        if len(history) >= point_count:
            history.clear()

        point = choose_click_point(
            center_x,
            center_y,
            width,
            height,
            excluded=history,
        )
        history.add(point)
        return point

    def move_mouse(
        self,
        x: int,
        y: int,
        duration: float | None = None,
        target_jitter: int = 3,
    ) -> None:
        """Move mouse with human-like behavior."""
        if not self._pyautogui:
            return

        if duration is None:
            duration = random.uniform(0.2, 0.6)

        screen_x, screen_y = self.screen_coords(x, y)
        jitter = random.randint(-target_jitter, target_jitter) if target_jitter else 0
        target_x, target_y = screen_x + jitter, screen_y + jitter
        current_x, current_y = self._pyautogui.position()

        distance = ((target_x - current_x) ** 2 + (target_y - current_y) ** 2) ** 0.5
        steps = max(int(distance / 50), 10)

        for i in range(steps + 1):
            t = 1 - (1 - i / steps) ** 2
            jx = random.uniform(-1, 1) if i < steps else 0
            jy = random.uniform(-1, 1) if i < steps else 0
            new_x = current_x + (target_x - current_x) * t + jx
            new_y = current_y + (target_y - current_y) * t + jy
            self._pyautogui.moveTo(int(new_x), int(new_y), duration=0)
            time.sleep(duration / steps)

    def click(self, x: int | None = None, y: int | None = None) -> None:
        """Click at coordinates or current position."""
        if not self._pyautogui:
            return

        if x is None or y is None:
            self._pyautogui.click()
            return

        sx, sy = self.screen_coords(x, y)
        self._pyautogui.click(sx, sy)

    def scroll(self, amount: int, x: int | None = None, y: int | None = None) -> None:
        """Scroll at position."""
        if not self._pyautogui:
            return

        if x is not None and y is not None:
            self.move_mouse(x, y)
        self._pyautogui.scroll(amount)

    def send_key(self, key: str) -> None:
        """Send keyboard key or combo."""
        if not self._pyautogui:
            return

        if "+" in key:
            keys = key.split("+")
            self._pyautogui.hotkey(*keys)
            return

        self._pyautogui.press(key)

    def system_type(self, text: str, interval: float = 0.08) -> None:
        """Type text via PyAutoGUI with variable delays."""
        if not self._pyautogui:
            return

        for char in text:
            if len(char) == 1:
                self._pyautogui.press(char)
            else:
                self._pyautogui.typewrite(char)
            time.sleep(max(0.02, interval + random.uniform(-0.03, 0.05)))

    def get_resolution(self) -> dict:
        """Get resolution from XVFB_RESOLUTION env var."""
        w, h = _get_default_resolution()
        return {"width": w, "height": h}
