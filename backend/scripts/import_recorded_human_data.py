"""Import recorded human sessions from frontend recorder exports."""

from __future__ import annotations

import argparse
from pathlib import Path

from dataset_common import TIMEZONE, backend_root, write_json

DEFAULT_INPUTS = [
    Path("/Users/kumar/Downloads/Shireesh-Kumar-all-sessions-2026-05-05T16-16-25-535Z.json"),
    Path("/Users/kumar/Downloads/Prisha-Singh-all-sessions-2026-05-05T19-53-36-580Z.json"),
]
DEFAULT_OUTPUT = backend_root() / "data" / "raw" / "recorded_human_data.json"


def _load_json(path: Path) -> object:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _clean_mouse(mouse: object, base_time: int) -> list[dict[str, int]]:
    if not isinstance(mouse, list):
        return []

    cleaned = []
    for event in mouse:
        if not isinstance(event, dict):
            continue
        try:
            cleaned.append(
                {
                    "x": int(round(float(event["x"]))),
                    "y": int(round(float(event["y"]))),
                    "t": max(0, int(round(float(event["t"]))) - base_time),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    cleaned.sort(key=lambda event: event["t"])
    return cleaned


def _clean_keyboard(keyboard: object, base_time: int) -> list[dict[str, int | str]]:
    if not isinstance(keyboard, list):
        return []

    cleaned = []
    for event in keyboard:
        if not isinstance(event, dict):
            continue
        try:
            key = str(event["key"])
            down = int(round(float(event["down"]))) - base_time
            up = int(round(float(event["up"]))) - base_time
        except (KeyError, TypeError, ValueError):
            continue

        dwell = up - down
        if down < 0 or up < down:
            continue
        if dwell < 10 or dwell > 2000:
            continue

        cleaned.append({"key": key, "down": down, "up": up})

    cleaned.sort(key=lambda event: event["down"])
    return cleaned


def _clean_device(device: object) -> dict[str, object]:
    if not isinstance(device, dict):
        device = {}

    screen = device.get("screen", [1536, 864])
    if not isinstance(screen, list) or len(screen) != 2:
        screen = [1536, 864]

    return {
        "userAgent": str(device.get("userAgent", "")),
        "screen": [int(screen[0]), int(screen[1])],
        "timezone": TIMEZONE,
    }


def _session_base_time(session: dict[str, object]) -> int:
    times = []
    for event in session.get("mouse", []):
        if isinstance(event, dict) and "t" in event:
            times.append(int(round(float(event["t"]))))
    for event in session.get("keyboard", []):
        if isinstance(event, dict) and "down" in event:
            times.append(int(round(float(event["down"]))))
    return min(times) if times else 0


def clean_recorded_session(session: object) -> dict[str, object] | None:
    """Normalize one recorded session into the project training schema."""
    if not isinstance(session, dict):
        return None

    base_time = _session_base_time(session)
    mouse = _clean_mouse(session.get("mouse", []), base_time)
    keyboard = _clean_keyboard(session.get("keyboard", []), base_time)

    # Password managers, paste flows, or keyboard-only tests can legitimately
    # leave one behavior channel empty. Keep the session if either channel has
    # enough signal to represent real human activity.
    if len(mouse) < 2 and len(keyboard) < 2:
        return None

    return {
        "mouse": mouse,
        "keyboard": keyboard,
        "device": _clean_device(session.get("device", {})),
        "label": 1,
    }


def import_recorded_humans(
    input_paths: list[Path] = DEFAULT_INPUTS,
    output_path: Path = DEFAULT_OUTPUT,
) -> list[dict[str, object]]:
    """Import, clean, validate, and save recorded human sessions."""
    sessions = []
    skipped = 0

    for path in input_paths:
        if not path.exists():
            print(f"Skipping missing recorded file: {path}")
            continue

        data = _load_json(path)
        if not isinstance(data, list):
            raise ValueError(f"Expected a JSON list in {path}")

        for raw_session in data:
            cleaned = clean_recorded_session(raw_session)
            if cleaned is None:
                skipped += 1
                continue
            sessions.append(cleaned)

    write_json(output_path, sessions)
    print(f"Wrote {len(sessions)} recorded human sessions to {output_path}")
    if skipped:
        print(f"Skipped {skipped} incomplete or invalid recorded sessions")
    return sessions


def main() -> None:
    parser = argparse.ArgumentParser(description="Import recorded human sessions.")
    parser.add_argument("--input", type=Path, nargs="*", default=DEFAULT_INPUTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    import_recorded_humans(input_paths=args.input, output_path=args.output)


if __name__ == "__main__":
    main()
