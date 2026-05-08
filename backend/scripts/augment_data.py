"""Augment SURAKSHA session JSON data."""

from __future__ import annotations

import argparse
import copy
import random
from pathlib import Path

from dataset_common import backend_root, clamp_int, random_device, read_json, write_json

DEFAULT_INPUT = backend_root() / "data" / "raw" / "human_synthetic_data.json"
DEFAULT_OUTPUT = backend_root() / "data" / "raw" / "human_augmented_data.json"


def _profile_settings(profile: str, label: int) -> dict[str, float | int | tuple[int, int]]:
    if profile == "recorded":
        return {
            "mouse_jitter_min": 2,
            "mouse_jitter_max": 3,
            "time_scale_min": 0.85,
            "time_scale_max": 1.2,
            "drop_rate_min": 0.02,
            "drop_rate_max": 0.06,
            "pause_chance": 0.03,
            "pause_range": (80, 300),
            "dwell_jitter": 15,
            "flight_jitter": 35,
            "keyboard_pause_chance": 0.04,
            "keyboard_pause_range": (80, 250),
        }

    if label == 1:
        return {
            "mouse_jitter_min": 2,
            "mouse_jitter_max": 8,
            "time_scale_min": 0.8,
            "time_scale_max": 1.25,
            "drop_rate_min": 0.02,
            "drop_rate_max": 0.12,
            "pause_chance": 0.06,
            "pause_range": (120, 900),
            "dwell_jitter": 26,
            "flight_jitter": 65,
            "keyboard_pause_chance": 0.11,
            "keyboard_pause_range": (120, 600),
        }

    return {
        "mouse_jitter_min": 0,
        "mouse_jitter_max": 2,
        "time_scale_min": 0.9,
        "time_scale_max": 1.1,
        "drop_rate_min": 0.0,
        "drop_rate_max": 0.04,
        "pause_chance": 0.0,
        "pause_range": (0, 0),
        "dwell_jitter": 6,
        "flight_jitter": 10,
        "keyboard_pause_chance": 0.0,
        "keyboard_pause_range": (0, 0),
    }


def _augment_mouse(
    mouse: list[dict[str, int]],
    label: int,
    settings: dict[str, float | int | tuple[int, int]],
) -> list[dict[str, int]]:
    if len(mouse) < 2:
        return copy.deepcopy(mouse)

    jitter = random.randint(int(settings["mouse_jitter_min"]), int(settings["mouse_jitter_max"]))
    time_scale = random.uniform(float(settings["time_scale_min"]), float(settings["time_scale_max"]))
    drop_rate = random.uniform(float(settings["drop_rate_min"]), float(settings["drop_rate_max"]))
    pause_range = settings["pause_range"]

    output = []
    for index, point in enumerate(mouse):
        if 0 < index < len(mouse) - 1 and random.random() < drop_rate:
            continue

        pause = 0
        if random.random() < float(settings["pause_chance"]):
            pause = random.randint(int(pause_range[0]), int(pause_range[1]))

        output.append(
            {
                "x": clamp_int(point["x"] + random.randint(-jitter, jitter)),
                "y": clamp_int(point["y"] + random.randint(-jitter, jitter)),
                "t": clamp_int(point["t"] * time_scale + pause),
            }
        )

    output.sort(key=lambda point: point["t"])
    return output


def _augment_keyboard(
    keyboard: list[dict[str, int | str]],
    settings: dict[str, float | int | tuple[int, int]],
) -> list[dict[str, int | str]]:
    if not keyboard:
        return []

    dwell_jitter = int(settings["dwell_jitter"])
    flight_jitter = int(settings["flight_jitter"])
    keyboard_pause_range = settings["keyboard_pause_range"]
    output: list[dict[str, int | str]] = []
    previous_up = None

    for index, event in enumerate(keyboard):
        dwell = int(event["up"]) - int(event["down"])
        dwell += random.randint(-dwell_jitter, dwell_jitter)
        dwell = max(25, dwell)

        if index == 0:
            down = int(event["down"]) + random.randint(-flight_jitter, flight_jitter)
        else:
            original_flight = int(event["down"]) - int(keyboard[index - 1]["up"])
            flight = max(20, original_flight + random.randint(-flight_jitter, flight_jitter))
            if random.random() < float(settings["keyboard_pause_chance"]):
                flight += random.randint(int(keyboard_pause_range[0]), int(keyboard_pause_range[1]))
            down = int(previous_up) + flight

        down = max(0, down)
        up = down + dwell
        output.append({"key": str(event["key"]), "down": clamp_int(down), "up": clamp_int(up)})
        previous_up = up

    return output


def augment_session(session: dict[str, object], profile: str = "standard") -> dict[str, object]:
    """Create one statistically similar variation of a session."""
    label = int(session.get("label", 1))
    settings = _profile_settings(profile, label)
    return {
        "mouse": _augment_mouse(session.get("mouse", []), label, settings),
        "keyboard": _augment_keyboard(session.get("keyboard", []), settings),
        "device": random_device(),
        "label": label,
    }


def augment_dataset(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    multiplier: int = 4,
    include_original: bool = False,
    profile: str = "standard",
    seed: int | None = None,
) -> list[dict[str, object]]:
    """Augment every input session `multiplier` times and save the result."""
    if seed is not None:
        random.seed(seed)

    sessions = read_json(input_path)
    if not isinstance(sessions, list):
        raise ValueError(f"Expected a JSON list in {input_path}")

    output = copy.deepcopy(sessions) if include_original else []
    for session in sessions:
        for _ in range(multiplier):
            output.append(augment_session(session, profile=profile))

    write_json(output_path, output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Augment SURAKSHA session data.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--multiplier", type=int, default=4)
    parser.add_argument("--include-original", action="store_true")
    parser.add_argument("--profile", choices=["standard", "recorded"], default="standard")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    output = augment_dataset(
        input_path=args.input,
        output_path=args.output,
        multiplier=args.multiplier,
        include_original=args.include_original,
        profile=args.profile,
        seed=args.seed,
    )
    print(f"Wrote {len(output)} augmented sessions to {args.output}")


if __name__ == "__main__":
    main()
