"""Generate synthetic human-like SURAKSHA sessions."""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from dataset_common import backend_root, random_device, synthetic_human_keyboard, synthetic_human_mouse, write_json

DEFAULT_OUTPUT = backend_root() / "data" / "raw" / "human_synthetic_data.json"


def synthetic_human_session() -> dict[str, object]:
    """Create one varied, imperfect human-like interaction session."""
    device = random_device()
    profile = random.choices(
        population=[
            "balanced",
            "fast_typer",
            "slow_typer",
            "paste_heavy",
            "mouse_only",
            "keyboard_only",
        ],
        weights=[0.52, 0.12, 0.12, 0.09, 0.08, 0.07],
        k=1,
    )[0]

    mouse = synthetic_human_mouse(
        n_points=random.randint(45, 150),
        duration=random.randint(2200, 8400),
        screen=device["screen"],
    )

    if profile == "keyboard_only":
        mouse = []

    keyboard = []
    if profile != "mouse_only":
        keyboard_start = (mouse[-1]["t"] if mouse else 0) + random.randint(80, 1200)
        keyboard_kwargs = {
            "start_time": keyboard_start,
            "hesitation_chance": random.uniform(0.12, 0.28),
            "paste_chance": 0.0,
            "typo_chance": random.uniform(0.02, 0.12),
        }

        if profile == "fast_typer":
            keyboard_kwargs["dwell_range"] = (45, 110)
            keyboard_kwargs["flight_range"] = (25, 130)
        elif profile == "slow_typer":
            keyboard_kwargs["dwell_range"] = (90, 220)
            keyboard_kwargs["flight_range"] = (90, 340)
            keyboard_kwargs["hesitation_chance"] = random.uniform(0.2, 0.35)
        elif profile == "paste_heavy":
            keyboard_kwargs["paste_chance"] = 0.7
            keyboard_kwargs["dwell_range"] = (40, 100)
            keyboard_kwargs["flight_range"] = (20, 100)

        keyboard = synthetic_human_keyboard(**keyboard_kwargs)

    return {
        "mouse": mouse,
        "keyboard": keyboard,
        "device": device,
        "label": 1,
    }


def generate_synthetic_humans(
    n_samples: int,
    output_path: Path = DEFAULT_OUTPUT,
    seed: int | None = None,
) -> list[dict[str, object]]:
    """Generate and save synthetic human sessions."""
    if seed is not None:
        random.seed(seed)

    sessions = [synthetic_human_session() for _ in range(n_samples)]
    write_json(output_path, sessions)
    return sessions


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic human data.")
    parser.add_argument("-n", "--n-samples", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    sessions = generate_synthetic_humans(args.n_samples, args.output, args.seed)
    print(f"Generated {len(sessions)} synthetic human sessions at {args.output}")


if __name__ == "__main__":
    main()
