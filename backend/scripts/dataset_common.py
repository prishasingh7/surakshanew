"""Shared helpers for SURAKSHA dataset generation scripts."""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

TIMEZONE = "Asia/Kolkata"
KEYWORD = "suraksha"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edg/124.0 Safari/537.36",
]

SCREEN_SIZES = [
    [1366, 768],
    [1440, 900],
    [1536, 864],
    [1920, 1080],
]


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def random_device() -> dict[str, object]:
    return {
        "userAgent": random.choice(USER_AGENTS),
        "screen": random.choice(SCREEN_SIZES),
        "timezone": TIMEZONE,
    }


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def clamp_int(value: float, minimum: int = 0) -> int:
    return max(minimum, int(round(value)))


def synthetic_human_keyboard(
    start_time: int,
    word: str = KEYWORD,
    dwell_range: tuple[int, int] = (65, 165),
    flight_range: tuple[int, int] = (45, 260),
    hesitation_chance: float = 0.18,
    paste_chance: float = 0.0,
    typo_chance: float = 0.0,
) -> list[dict[str, int | str]]:
    events: list[dict[str, int | str]] = []
    if paste_chance > 0 and random.random() < paste_chance:
        down = start_time
        up = start_time + random.randint(35, 110)
        return [{"key": "Paste", "down": down, "up": up}]

    current = start_time

    for index, key in enumerate(word):
        if index > 0:
            current += random.randint(*flight_range)
            if random.random() < hesitation_chance:
                current += random.randint(120, 420)

        dwell = random.randint(*dwell_range)
        down = current
        up = down + dwell
        events.append({"key": key, "down": down, "up": up})
        current = up

        if typo_chance > 0 and random.random() < typo_chance:
            typo_down = current + random.randint(35, 140)
            typo_up = typo_down + random.randint(45, 160)
            events.append({"key": "Backspace", "down": typo_down, "up": typo_up})
            current = typo_up

    return events


def synthetic_human_mouse(
    n_points: int | None = None,
    duration: int | None = None,
    screen: list[int] | None = None,
) -> list[dict[str, int]]:
    screen = screen or random.choice(SCREEN_SIZES)
    width, height = screen
    n_points = n_points or random.randint(42, 145)
    duration = duration or random.randint(2200, 8200)

    x = random.randint(80, max(100, width - 260))
    y = random.randint(80, max(100, height - 220))
    target_x = random.randint(80, max(100, width - 120))
    target_y = random.randint(80, max(100, height - 120))
    drift_x = (target_x - x) / max(1, n_points - 1)
    drift_y = (target_y - y) / max(1, n_points - 1)
    overshoot_x = random.uniform(-60, 60)
    overshoot_y = random.uniform(-40, 40)
    base_dt = duration / max(1, n_points - 1)

    mouse: list[dict[str, int]] = []
    current_time = 0
    for index in range(n_points):
        if index > 0:
            current_time += clamp_int(random.gauss(base_dt, base_dt * 0.45), 10)
            if random.random() < 0.12:
                current_time += random.randint(150, 1200)

        progress = index / max(1, n_points - 1)
        wave = math.sin(progress * math.pi * random.uniform(1.3, 3.0))
        curve = wave * random.uniform(8, 28)
        correction = 1.0 if progress < 0.72 else -0.55
        x += drift_x + random.gauss(0, 10) + curve + overshoot_x * 0.01 * correction
        y += drift_y + random.gauss(0, 10) - curve * 0.5 + overshoot_y * 0.01 * correction
        x = min(max(0, x), width - 1)
        y = min(max(0, y), height - 1)
        mouse.append({"x": clamp_int(x), "y": clamp_int(y), "t": clamp_int(current_time)})

    return mouse
