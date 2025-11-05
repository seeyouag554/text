"""Prepare a normalized dataset for speech model training.

This script normalizes transcripts and filters audio recordings using simple
heuristics. It expects a metadata file (CSV or JSON lines) with at least the
following fields:

* ``utt_id`` – unique utterance identifier
* ``text`` – transcript
* ``audio_path`` – path to the corresponding audio file

Example usage::

    python scripts/preprocess_dataset.py \
        --metadata data/metadata.csv \
        --audio-root data/wavs \
        --output data/clean_metadata.csv
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional

from text_pipeline import AudioAnalysisResult, analyze_audio_file, normalize_text


def _read_metadata(path: Path) -> Iterator[Dict[str, str]]:
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as fp:
            for line in fp:
                if not line.strip():
                    continue
                yield json.loads(line)
    else:
        with path.open("r", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                yield row


def _resolve_audio_path(entry: Dict[str, str], audio_root: Optional[Path]) -> Optional[Path]:
    raw_path = entry.get("audio_path") or entry.get("audio")
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_absolute() and audio_root:
        path = audio_root / path
    return path


def _should_keep(
    analysis: AudioAnalysisResult,
    *,
    min_duration: float,
    max_duration: float,
    min_rms: float,
    max_rms: float,
    max_clipped_ratio: float,
) -> bool:
    return analysis.is_acceptable(
        min_duration=min_duration,
        max_duration=max_duration,
        min_rms=min_rms,
        max_rms=max_rms,
        max_clipped_ratio=max_clipped_ratio,
    )


def preprocess_dataset(
    metadata_path: Path,
    output_path: Path,
    *,
    audio_root: Optional[Path],
    min_duration: float,
    max_duration: float,
    min_rms: float,
    max_rms: float,
    max_clipped_ratio: float,
    extra_abbreviations: Optional[Dict[str, str]] = None,
    skip_missing_audio: bool = True,
) -> List[Dict[str, str]]:
    """Run the preprocessing pipeline and save the clean dataset."""

    output_rows: List[Dict[str, str]] = []
    for entry in _read_metadata(metadata_path):
        utt_id = entry.get("utt_id") or entry.get("id")
        if not utt_id:
            raise ValueError("Metadata entry is missing 'utt_id' field")

        text = normalize_text(entry.get("text", ""), extra_abbreviations)
        audio_path = _resolve_audio_path(entry, audio_root)
        if audio_path is None:
            if skip_missing_audio:
                continue
            raise ValueError(f"Entry {utt_id} is missing an audio path")

        analysis = analyze_audio_file(audio_path)
        if analysis is None:
            if skip_missing_audio:
                continue
            raise ValueError(f"Unable to analyze audio file: {audio_path}")

        if not _should_keep(
            analysis,
            min_duration=min_duration,
            max_duration=max_duration,
            min_rms=min_rms,
            max_rms=max_rms,
            max_clipped_ratio=max_clipped_ratio,
        ):
            continue

        output_rows.append(
            {
                "utt_id": utt_id,
                "text": text,
                "audio_path": str(audio_path),
                "duration": f"{analysis.duration:.3f}",
                "rms": f"{analysis.rms:.4f}",
                "peak": f"{analysis.peak:.4f}",
                "clipped_ratio": f"{analysis.clipped_ratio:.4f}",
            }
        )

    if not output_rows:
        raise RuntimeError("No valid samples found; check thresholds or inputs")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "utt_id",
                "text",
                "audio_path",
                "duration",
                "rms",
                "peak",
                "clipped_ratio",
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    return output_rows


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True, help="Path to metadata.csv or metadata.jsonl")
    parser.add_argument("--output", type=Path, required=True, help="Destination for the cleaned metadata CSV")
    parser.add_argument("--audio-root", type=Path, default=None, help="Optional root directory for audio paths")
    parser.add_argument("--min-duration", type=float, default=1.0)
    parser.add_argument("--max-duration", type=float, default=20.0)
    parser.add_argument("--min-rms", type=float, default=0.01)
    parser.add_argument("--max-rms", type=float, default=0.8)
    parser.add_argument("--max-clipped-ratio", type=float, default=0.02)
    parser.add_argument(
        "--extra-abbreviation",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Custom abbreviation expansion entries",
    )
    parser.add_argument(
        "--keep-missing-audio",
        action="store_true",
        help="Fail instead of skipping when audio is missing or unreadable",
    )
    return parser.parse_args(argv)


def _parse_extra_abbreviations(entries: Iterable[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise ValueError(f"Invalid abbreviation mapping: {entry}")
        key, value = entry.split("=", 1)
        mapping[key.strip().lower()] = value.strip().lower()
    return mapping


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    extra_abbreviations = _parse_extra_abbreviations(args.extra_abbreviation)
    preprocess_dataset(
        args.metadata,
        args.output,
        audio_root=args.audio_root,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        min_rms=args.min_rms,
        max_rms=args.max_rms,
        max_clipped_ratio=args.max_clipped_ratio,
        extra_abbreviations=extra_abbreviations or None,
        skip_missing_audio=not args.keep_missing_audio,
    )


if __name__ == "__main__":
    main()
