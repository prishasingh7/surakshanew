"""Merge raw SURAKSHA session JSON files into one dataset."""

from __future__ import annotations

import argparse
import random
from collections import Counter
from pathlib import Path

from dataset_common import backend_root, read_json, write_json

RAW_DIR = backend_root() / "data" / "raw"
DEFAULT_OUTPUT = RAW_DIR / "final_session_dataset.json"
DEFAULT_INPUTS = [
    RAW_DIR / "human_synthetic_data.json",
    RAW_DIR / "human_augmented_data.json",
    RAW_DIR / "public_human_data.json",
    RAW_DIR / "recorded_human_data.json",
    RAW_DIR / "recorded_human_augmented_data.json",
    RAW_DIR / "bot_data.json",
]


def _valid_session(session: object) -> bool:
    if not isinstance(session, dict):
        return False
    return set(session.keys()) == {"mouse", "keyboard", "device", "label"}


def merge_raw_datasets(
    input_paths: list[Path],
    output_path: Path = DEFAULT_OUTPUT,
    shuffle: bool = True,
    label_noise: float = 0.02,
    seed: int | None = None,
) -> list[dict[str, object]]:
    """Load, validate, merge, optionally shuffle, and save session JSON lists."""
    if seed is not None:
        random.seed(seed)

    merged = []
    for path in input_paths:
        if not path.exists():
            print(f"Skipping missing file: {path}")
            continue

        data = read_json(path)
        if not isinstance(data, list):
            raise ValueError(f"Expected JSON list in {path}")

        valid = [session for session in data if _valid_session(session)]
        skipped = len(data) - len(valid)
        if skipped:
            print(f"Skipped {skipped} invalid sessions from {path}")
        merged.extend(valid)

    if label_noise > 0 and merged:
        flip_count = max(1, int(len(merged) * label_noise))
        for index in random.sample(range(len(merged)), min(flip_count, len(merged))):
            merged[index]["label"] = 1 - int(merged[index]["label"])

    if shuffle:
        random.shuffle(merged)

    write_json(output_path, merged)
    counts = Counter(session["label"] for session in merged)
    print(f"Wrote {len(merged)} sessions to {output_path}")
    print(f"Label counts: {dict(counts)}")
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge raw SURAKSHA datasets.")
    parser.add_argument("--input", type=Path, nargs="*", default=DEFAULT_INPUTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-shuffle", action="store_true")
    parser.add_argument("--label-noise", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    merge_raw_datasets(
        input_paths=args.input,
        output_path=args.output,
        shuffle=not args.no_shuffle,
        label_noise=args.label_noise,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
