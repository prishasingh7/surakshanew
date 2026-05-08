"""Convert public human datasets into SURAKSHA session JSON.

Supported sources:
- CMU/DSL Strong Password keystroke CSV.
- Balabit Mouse Dynamics Challenge folder.
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

from dataset_common import (
    backend_root,
    clamp_int,
    random_device,
    synthetic_human_keyboard,
    synthetic_human_mouse,
    write_json,
)

DEFAULT_CMU_PATH = Path("/Users/kumar/Downloads/DSL-StrongPasswordData.csv")
DEFAULT_BALABIT_PATH = Path("/Users/kumar/Downloads/Mouse-Dynamics-Challenge-master")
DEFAULT_OUTPUT = backend_root() / "data" / "raw" / "public_human_data.json"

CMU_KEYS = [
    ("period", "."),
    ("t", "t"),
    ("i", "i"),
    ("e", "e"),
    ("five", "5"),
    ("Shift.r", "R"),
    ("o", "o"),
    ("a", "a"),
    ("n", "n"),
    ("l", "l"),
    ("Return", "Return"),
]


def _seconds_to_ms(value: str | float) -> int:
    return clamp_int(float(value) * 1000)


def _cmu_row_to_keyboard(row: dict[str, str]) -> list[dict[str, int | str]]:
    down_times = [0]
    for index in range(1, len(CMU_KEYS)):
        previous_name = CMU_KEYS[index - 1][0]
        current_name = CMU_KEYS[index][0]
        dd_key = f"DD.{previous_name}.{current_name}"
        down_times.append(down_times[-1] + _seconds_to_ms(row[dd_key]))

    keyboard = []
    for index, (source_key, output_key) in enumerate(CMU_KEYS):
        down = down_times[index]
        up = down + _seconds_to_ms(row[f"H.{source_key}"])
        keyboard.append({"key": output_key, "down": down, "up": up})

    return keyboard


def convert_cmu_keystrokes(
    csv_path: Path = DEFAULT_CMU_PATH,
    max_samples: int | None = None,
) -> list[dict[str, object]]:
    """Convert CMU/DSL keystroke rows into SURAKSHA human sessions."""
    sessions = []
    with csv_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            device = random_device()
            mouse = synthetic_human_mouse(
                n_points=random.randint(18, 44),
                duration=random.randint(1200, 3600),
                screen=device["screen"],
            )
            keyboard = _cmu_row_to_keyboard(row)
            shift = mouse[-1]["t"] + random.randint(120, 700)
            keyboard = [
                {"key": event["key"], "down": event["down"] + shift, "up": event["up"] + shift}
                for event in keyboard
            ]
            sessions.append(
                {
                    "mouse": mouse,
                    "keyboard": keyboard,
                    "device": device,
                    "label": 1,
                }
            )
            if max_samples and len(sessions) >= max_samples:
                break

    return sessions


def _read_balabit_mouse_file(path: Path) -> list[dict[str, int]]:
    points = []
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get("state") != "Move":
                continue

            try:
                points.append(
                    {
                        "x": clamp_int(float(row["x"])),
                        "y": clamp_int(float(row["y"])),
                        "t": _seconds_to_ms(row["client timestamp"]),
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue

    return points


def _chunk_mouse_points(
    points: list[dict[str, int]],
    chunk_seconds: int,
    min_points: int,
) -> list[list[dict[str, int]]]:
    if not points:
        return []

    chunk_ms = chunk_seconds * 1000
    chunks = []
    current = []
    chunk_start = points[0]["t"]

    for point in points:
        if point["t"] - chunk_start > chunk_ms and len(current) >= min_points:
            base = current[0]["t"]
            chunks.append([{**item, "t": item["t"] - base} for item in current])
            current = []
            chunk_start = point["t"]
        current.append(point)

    if len(current) >= min_points:
        base = current[0]["t"]
        chunks.append([{**item, "t": item["t"] - base} for item in current])

    return chunks


def convert_balabit_mouse(
    folder_path: Path = DEFAULT_BALABIT_PATH,
    max_samples: int | None = None,
    chunk_seconds: int = 8,
    min_points: int = 12,
) -> list[dict[str, object]]:
    """Convert Balabit mouse files into SURAKSHA human sessions."""
    sessions = []
    files = sorted((folder_path / "training_files").glob("user*/session_*"))

    for path in files:
        points = _read_balabit_mouse_file(path)
        for chunk in _chunk_mouse_points(points, chunk_seconds, min_points):
            device = random_device()
            keyboard_start = chunk[-1]["t"] + random.randint(120, 900)
            sessions.append(
                {
                    "mouse": chunk,
                    "keyboard": synthetic_human_keyboard(start_time=keyboard_start),
                    "device": device,
                    "label": 1,
                }
            )
            if max_samples and len(sessions) >= max_samples:
                return sessions

    return sessions


def convert_public_datasets(
    cmu_path: Path = DEFAULT_CMU_PATH,
    balabit_path: Path = DEFAULT_BALABIT_PATH,
    output_path: Path = DEFAULT_OUTPUT,
    max_cmu: int | None = 3000,
    max_balabit: int | None = 3000,
    seed: int | None = None,
) -> list[dict[str, object]]:
    """Convert both public datasets and save one combined human JSON list."""
    if seed is not None:
        random.seed(seed)

    sessions = []
    if cmu_path.exists():
        sessions.extend(convert_cmu_keystrokes(cmu_path, max_samples=max_cmu))
    else:
        print(f"Skipping CMU dataset, file not found: {cmu_path}")

    if balabit_path.exists():
        sessions.extend(convert_balabit_mouse(balabit_path, max_samples=max_balabit))
    else:
        print(f"Skipping Balabit dataset, folder not found: {balabit_path}")

    write_json(output_path, sessions)
    return sessions


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert public datasets to SURAKSHA JSON.")
    parser.add_argument("--cmu-path", type=Path, default=DEFAULT_CMU_PATH)
    parser.add_argument("--balabit-path", type=Path, default=DEFAULT_BALABIT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-cmu", type=int, default=3000)
    parser.add_argument("--max-balabit", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    sessions = convert_public_datasets(
        cmu_path=args.cmu_path,
        balabit_path=args.balabit_path,
        output_path=args.output,
        max_cmu=args.max_cmu,
        max_balabit=args.max_balabit,
        seed=args.seed,
    )
    print(f"Wrote {len(sessions)} public human sessions to {args.output}")


if __name__ == "__main__":
    main()
