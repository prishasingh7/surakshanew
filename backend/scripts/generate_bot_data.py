"""Generate harder synthetic bot interaction sessions for SURAKSHA."""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path
from typing import Callable

from dataset_common import (
    backend_root,
    clamp_int,
    read_json,
    synthetic_human_keyboard,
    write_json,
)

KEYWORD = "suraksha"
DEFAULT_OUTPUT_PATH = backend_root() / "data" / "raw" / "bot_data.json"
REFERENCE_PATHS = [
    backend_root() / "data" / "raw" / "recorded_human_data.json",
    backend_root() / "data" / "raw" / "human_synthetic_data.json",
]

SUSPICIOUS_USER_AGENTS = [
    "Mozilla/5.0 HeadlessChrome/124.0 Selenium",
    "Mozilla/5.0 (X11; Linux x86_64) HeadlessChrome/124.0",
    "Mozilla/5.0 Selenium WebDriver",
    "Mozilla/5.0 Playwright Chromium",
]

NORMAL_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edg/124.0 Safari/537.36",
]

SCREENS = [
    [1920, 1080],
    [1366, 768],
    [1536, 864],
]

BASE_REPLAY_TRAJECTORY = [
    (140, 240),
    (185, 255),
    (230, 275),
    (275, 300),
    (320, 330),
    (365, 360),
    (410, 395),
    (455, 430),
    (500, 465),
    (545, 505),
]

Session = dict[str, object]
BotGenerator = Callable[..., Session]


def _speed_to_dt(speed: str) -> int:
    return {"slow": 135, "normal": 95, "fast": 65}.get(speed, 95)


def _device() -> dict[str, object]:
    suspicious = random.random() < 0.55
    user_agent = random.choice(SUSPICIOUS_USER_AGENTS if suspicious else NORMAL_USER_AGENTS)
    return {
        "userAgent": user_agent,
        "screen": random.choice(SCREENS),
        "timezone": "Asia/Kolkata",
    }


def _load_reference_sessions() -> list[Session]:
    sessions: list[Session] = []
    for path in REFERENCE_PATHS:
        if not path.exists():
            continue
        data = read_json(path)
        if isinstance(data, list):
            sessions.extend([item for item in data if isinstance(item, dict)])
    return sessions


def _sample_reference_sessions(references: list[Session], require_mouse: bool = False, require_keyboard: bool = False) -> Session | None:
    candidates = []
    for session in references:
        mouse = session.get("mouse", [])
        keyboard = session.get("keyboard", [])
        if require_mouse and len(mouse) < 2:
            continue
        if require_keyboard and len(keyboard) < 1:
            continue
        candidates.append(session)
    return random.choice(candidates) if candidates else None


def _resample_path(points: list[tuple[float, float]], n_points: int) -> list[tuple[float, float]]:
    if not points:
        return []
    if n_points <= 1:
        return [points[0]]

    output = []
    max_index = len(points) - 1
    for index in range(n_points):
        source_position = index * max_index / max(1, n_points - 1)
        left_index = math.floor(source_position)
        right_index = min(max_index, left_index + 1)
        ratio = source_position - left_index
        left = points[left_index]
        right = points[right_index]
        x = left[0] + (right[0] - left[0]) * ratio
        y = left[1] + (right[1] - left[1]) * ratio
        output.append((x, y))
    return output


def _normalize_mouse(
    points: list[tuple[float, float]],
    n_points: int,
    base_dt: int,
    dt_scale_range: tuple[float, float],
    jitter: float,
    drop_rate: float,
    pause_chance: float,
    pause_range: tuple[int, int],
    zigzag: float,
    overshoot: float = 0.0,
) -> list[dict[str, int]]:
    sampled = _resample_path(points, n_points)
    output = []
    current_time = 0

    for index, (x, y) in enumerate(sampled):
        if 0 < index < len(sampled) - 1 and random.random() < drop_rate:
            continue

        if index > 0:
            current_time += clamp_int(base_dt * random.uniform(*dt_scale_range), 8)
            if random.random() < pause_chance:
                current_time += random.randint(*pause_range)

        progress = index / max(1, len(sampled) - 1)
        wave = math.sin(progress * math.pi * random.uniform(1.4, 3.6))
        correction = overshoot * (1 if progress < 0.72 else -0.55)
        output.append(
            {
                "x": clamp_int(x + random.gauss(0, jitter) + wave * zigzag + correction),
                "y": clamp_int(y + random.gauss(0, jitter) - wave * zigzag * 0.6 - correction * 0.4),
                "t": current_time,
            }
        )

    if len(output) < 2 and sampled:
        output = [
            {"x": clamp_int(x), "y": clamp_int(y), "t": clamp_int(index * base_dt)}
            for index, (x, y) in enumerate(sampled[: max(2, min(3, len(sampled)))])
        ]
    return output


def _reference_mouse(reference: Session) -> list[tuple[float, float]]:
    return [(float(event["x"]), float(event["y"])) for event in reference.get("mouse", [])]


def _reference_keyboard(reference: Session, start_time: int) -> list[dict[str, int | str]]:
    keyboard = reference.get("keyboard", [])
    if not keyboard:
        return synthetic_human_keyboard(
            start_time=start_time,
            dwell_range=(70, 150),
            flight_range=(40, 200),
            hesitation_chance=0.16,
        )

    first_down = int(keyboard[0]["down"])
    output = []
    for event in keyboard:
        down = start_time + (int(event["down"]) - first_down)
        up = start_time + (int(event["up"]) - first_down)
        output.append({"key": str(event["key"]), "down": down, "up": up})
    return output


def _bot_keyboard(start_time: int, style: str, references: list[Session]) -> list[dict[str, int | str]]:
    if style == "low_variance" and random.random() < 0.35:
        style = "humanish"
    if style == "low_variance" and random.random() < 0.12:
        style = "human_reference"

    if style == "human_reference":
        reference = _sample_reference_sessions(references, require_keyboard=True)
        if reference is not None:
            return _reference_keyboard(reference, start_time)

    if style == "humanish":
        return synthetic_human_keyboard(
            start_time=start_time,
            dwell_range=(60, 155),
            flight_range=(35, 220),
            hesitation_chance=0.14,
            paste_chance=0.08,
            typo_chance=0.04,
        )

    return synthetic_human_keyboard(
        start_time=start_time,
        dwell_range=(70, 145),
        flight_range=(45, 190),
        hesitation_chance=0.1,
        paste_chance=0.03,
        typo_chance=0.03,
    )


def _session(mouse: list[dict[str, int]], keyboard: list[dict[str, int | str]]) -> Session:
    return {"mouse": mouse, "keyboard": keyboard, "device": _device(), "label": 0}


def linear_bot(
    n_points: int = 72,
    speed: str = "normal",
    noise_level: float = 2.0,
    duration: int | None = None,
    references: list[Session] | None = None,
) -> Session:
    """Straight-ish motion with enough noise to overlap humans."""
    start_x = random.randint(70, 260)
    start_y = random.randint(80, 320)
    end_x = start_x + random.randint(380, 900)
    end_y = start_y + random.randint(180, 520)
    points = _resample_path([(start_x, start_y), (end_x, end_y)], n_points)
    base_dt = duration // max(1, n_points - 1) if duration else _speed_to_dt(speed)
    mouse = _normalize_mouse(
        points=points,
        n_points=n_points,
        base_dt=base_dt,
        dt_scale_range=(0.7, 1.45),
        jitter=max(1.5, noise_level),
        drop_rate=random.uniform(0.01, 0.05),
        pause_chance=0.08,
        pause_range=(100, 420),
        zigzag=random.uniform(0.5, 2.5),
        overshoot=random.uniform(0.0, 8.0),
    )
    keyboard = _bot_keyboard((mouse[-1]["t"] if mouse else 0) + 120, "low_variance", references or [])
    return _session(mouse, keyboard)


def curve_bot(
    n_points: int = 84,
    speed: str = "normal",
    noise_level: float = 2.5,
    duration: int | None = None,
    references: list[Session] | None = None,
) -> Session:
    """Smooth curve with mild imperfection and overshoot."""
    start = (random.randint(80, 200), random.randint(120, 260))
    control_1 = (random.randint(240, 420), random.randint(80, 260))
    control_2 = (random.randint(460, 720), random.randint(250, 520))
    end = (random.randint(540, 980), random.randint(280, 640))
    points = []
    for index in range(n_points):
        u = index / max(1, n_points - 1)
        x = (
            (1 - u) ** 3 * start[0]
            + 3 * (1 - u) ** 2 * u * control_1[0]
            + 3 * (1 - u) * u**2 * control_2[0]
            + u**3 * end[0]
        )
        y = (
            (1 - u) ** 3 * start[1]
            + 3 * (1 - u) ** 2 * u * control_1[1]
            + 3 * (1 - u) * u**2 * control_2[1]
            + u**3 * end[1]
        )
        points.append((x, y))
    base_dt = duration // max(1, n_points - 1) if duration else _speed_to_dt(speed)
    mouse = _normalize_mouse(
        points=points,
        n_points=n_points,
        base_dt=base_dt,
        dt_scale_range=(0.75, 1.35),
        jitter=max(1.2, noise_level),
        drop_rate=random.uniform(0.01, 0.04),
        pause_chance=0.06,
        pause_range=(80, 300),
        zigzag=random.uniform(0.8, 3.2),
        overshoot=random.uniform(4.0, 18.0),
    )
    keyboard = _bot_keyboard((mouse[-1]["t"] if mouse else 0) + 140, "low_variance", references or [])
    return _session(mouse, keyboard)


def replay_bot(
    n_points: int = 80,
    speed: str = "normal",
    noise_level: float = 1.5,
    duration: int | None = None,
    references: list[Session] | None = None,
) -> Session:
    """Replay a fixed base path with mild timing distortion."""
    points = [(float(x), float(y)) for x, y in BASE_REPLAY_TRAJECTORY]
    base_dt = duration // max(1, n_points - 1) if duration else _speed_to_dt(speed)
    mouse = _normalize_mouse(
        points=points,
        n_points=n_points,
        base_dt=base_dt,
        dt_scale_range=(0.8, 1.25),
        jitter=max(0.8, noise_level),
        drop_rate=random.uniform(0.0, 0.03),
        pause_chance=0.04,
        pause_range=(80, 240),
        zigzag=random.uniform(0.3, 1.5),
        overshoot=random.uniform(0.0, 6.0),
    )
    keyboard = _bot_keyboard((mouse[-1]["t"] if mouse else 0) + 120, "low_variance", references or [])
    return _session(mouse, keyboard)


def randomized_bot(
    n_points: int = 90,
    speed: str = "normal",
    noise_level: float = 3.5,
    duration: int | None = None,
    references: list[Session] | None = None,
) -> Session:
    """Low-entropy noisy bot that still lacks true human inconsistency."""
    start_x = random.randint(90, 240)
    start_y = random.randint(120, 300)
    points = []
    x = start_x
    y = start_y
    dx = random.uniform(7, 14)
    dy = random.uniform(4, 11)
    for index in range(n_points):
        correction = -1 if index and index % random.randint(11, 18) == 0 else 1
        x += dx + random.gauss(0, noise_level) * correction
        y += dy + random.gauss(0, noise_level * 0.8)
        points.append((x, y))
    base_dt = duration // max(1, n_points - 1) if duration else _speed_to_dt(speed)
    mouse = _normalize_mouse(
        points=points,
        n_points=n_points,
        base_dt=base_dt,
        dt_scale_range=(0.72, 1.5),
        jitter=max(2.0, noise_level),
        drop_rate=random.uniform(0.01, 0.06),
        pause_chance=0.09,
        pause_range=(100, 450),
        zigzag=random.uniform(1.2, 4.0),
        overshoot=random.uniform(4.0, 14.0),
    )
    keyboard = _bot_keyboard((mouse[-1]["t"] if mouse else 0) + 150, "humanish", references or [])
    return _session(mouse, keyboard)


def human_mimic_bot(
    n_points: int = 88,
    speed: str = "normal",
    noise_level: float = 3.0,
    duration: int | None = None,
    references: list[Session] | None = None,
) -> Session:
    """Human-like bot with pauses, jitter, and corrections."""
    reference = _sample_reference_sessions(references or [], require_mouse=True)
    if reference is not None:
        points = _reference_mouse(reference)
    else:
        points = [(float(x), float(y)) for x, y in BASE_REPLAY_TRAJECTORY]
    base_dt = duration // max(1, n_points - 1) if duration else _speed_to_dt(speed)
    mouse = _normalize_mouse(
        points=points,
        n_points=n_points,
        base_dt=base_dt,
        dt_scale_range=(0.68, 1.55),
        jitter=max(2.0, noise_level),
        drop_rate=random.uniform(0.02, 0.08),
        pause_chance=0.1,
        pause_range=(120, 520),
        zigzag=random.uniform(1.5, 4.8),
        overshoot=random.uniform(8.0, 24.0),
    )
    keyboard = _bot_keyboard((mouse[-1]["t"] if mouse else 0) + 120, "humanish", references or [])
    return _session(mouse, keyboard)


def replay_bot_distortion(
    n_points: int = 78,
    speed: str = "normal",
    noise_level: float = 2.4,
    duration: int | None = None,
    references: list[Session] | None = None,
) -> Session:
    """Replay a human path, then distort timing and geometry unevenly."""
    reference = _sample_reference_sessions(references or [], require_mouse=True)
    if reference is not None:
        points = _reference_mouse(reference)
    else:
        points = [(float(x), float(y)) for x, y in BASE_REPLAY_TRAJECTORY]
    base_dt = duration // max(1, n_points - 1) if duration else _speed_to_dt(speed)
    mouse = _normalize_mouse(
        points=points,
        n_points=n_points,
        base_dt=base_dt,
        dt_scale_range=(0.7, 1.4),
        jitter=max(1.5, noise_level),
        drop_rate=random.uniform(0.04, 0.1),
        pause_chance=0.07,
        pause_range=(70, 350),
        zigzag=random.uniform(0.8, 3.8),
        overshoot=random.uniform(4.0, 16.0),
    )
    keyboard = _bot_keyboard((mouse[-1]["t"] if mouse else 0) + 100, "humanish", references or [])
    return _session(mouse, keyboard)


def hybrid_bot(
    n_points: int = 82,
    speed: str = "normal",
    noise_level: float = 2.8,
    duration: int | None = None,
    references: list[Session] | None = None,
) -> Session:
    """Synthetic mouse paired with real human keyboard timing."""
    start_x = random.randint(80, 260)
    start_y = random.randint(110, 320)
    points = []
    x = start_x
    y = start_y
    for index in range(n_points):
        x += random.uniform(8, 16) + math.sin(index / 5.0) * random.uniform(2, 7)
        y += random.uniform(5, 12) + math.cos(index / 6.0) * random.uniform(2, 6)
        if index and index % random.randint(12, 20) == 0:
            x -= random.uniform(10, 26)
            y += random.uniform(-12, 16)
        points.append((x, y))
    base_dt = duration // max(1, n_points - 1) if duration else _speed_to_dt(speed)
    mouse = _normalize_mouse(
        points=points,
        n_points=n_points,
        base_dt=base_dt,
        dt_scale_range=(0.74, 1.45),
        jitter=max(1.8, noise_level),
        drop_rate=random.uniform(0.01, 0.05),
        pause_chance=0.08,
        pause_range=(100, 420),
        zigzag=random.uniform(1.0, 3.5),
        overshoot=random.uniform(6.0, 18.0),
    )
    keyboard = _bot_keyboard((mouse[-1]["t"] if mouse else 0) + 100, "human_reference", references or [])
    return _session(mouse, keyboard)


def generate_dataset(
    n_samples: int,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    seed: int | None = None,
) -> list[Session]:
    """Generate synthetic bot sessions and save them as a JSON list."""
    if seed is not None:
        random.seed(seed)

    references = _load_reference_sessions()
    generators: list[BotGenerator] = [
        linear_bot,
        curve_bot,
        replay_bot,
        randomized_bot,
        human_mimic_bot,
        replay_bot_distortion,
        hybrid_bot,
    ]
    speeds = ["slow", "normal", "fast"]
    sessions = []

    for _ in range(n_samples):
        generator = random.choice(generators)
        sessions.append(
            generator(
                n_points=random.randint(48, 120),
                speed=random.choice(speeds),
                noise_level=random.choice([1.5, 2.0, 2.5, 3.0, 3.5, 4.0]),
                duration=random.choice([None, 2600, 3200, 4200, 5400, 7000]),
                references=references,
            )
        )

    write_json(output_path, sessions)
    return sessions


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic bot data.")
    parser.add_argument("-n", "--n-samples", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    sessions = generate_dataset(args.n_samples, output_path=args.output, seed=args.seed)
    print(f"Generated {len(sessions)} bot sessions at {args.output}")


if __name__ == "__main__":
    main()
