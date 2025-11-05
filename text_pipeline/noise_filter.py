"""Audio quality heuristics for preparing training sets."""
from __future__ import annotations

import audioop
import contextlib
import dataclasses
import math
import wave
from pathlib import Path
from typing import Iterable, Iterator, Optional


@dataclasses.dataclass
class AudioAnalysisResult:
    """Summary of audio quality measurements."""

    path: Path
    duration: float
    rms: float
    peak: float
    clipped_ratio: float

    def is_acceptable(
        self,
        *,
        min_duration: float = 1.0,
        max_duration: float = 20.0,
        min_rms: float = 0.01,
        max_rms: float = 0.8,
        max_clipped_ratio: float = 0.02,
    ) -> bool:
        """Return ``True`` if the sample satisfies basic quality thresholds."""

        if not (min_duration <= self.duration <= max_duration):
            return False
        if not (min_rms <= self.rms <= max_rms):
            return False
        if self.clipped_ratio > max_clipped_ratio:
            return False
        return True


def _iter_samples(frames: bytes, sample_width: int) -> Iterator[int]:
    if sample_width == 1:
        # 8-bit audio is unsigned; shift to signed representation
        for value in frames:
            yield value - 128
    else:
        step = sample_width
        for i in range(0, len(frames), step):
            chunk = frames[i : i + step]
            if len(chunk) < step:
                break
            yield int.from_bytes(chunk, byteorder="little", signed=True)


def _compute_clipped_ratio(samples: Iterable[int], max_amplitude: int) -> float:
    clipped = 0
    total = 0
    threshold = max_amplitude - 1
    for sample in samples:
        total += 1
        if abs(sample) >= threshold:
            clipped += 1
    if total == 0:
        return 0.0
    return clipped / total


def analyze_audio_file(path: str | Path) -> Optional[AudioAnalysisResult]:
    """Return heuristic audio quality statistics for the ``path``.

    ``None`` is returned when the file cannot be analyzed (for example if the
    file is missing or an unsupported codec is used).
    """

    path = Path(path)
    if not path.exists():
        return None

    with contextlib.closing(wave.open(str(path), "rb")) as wav:
        frame_rate = wav.getframerate()
        frame_count = wav.getnframes()
        sample_width = wav.getsampwidth()
        channels = wav.getnchannels()
        frames = wav.readframes(frame_count)

    if frame_rate == 0:
        return None

    duration = frame_count / float(frame_rate)
    try:
        rms = audioop.rms(frames, sample_width)
        peak = audioop.max(frames, sample_width)
    except audioop.error:
        return None

    max_possible = float(1 << (8 * sample_width - 1))
    normalized_rms = rms / max_possible
    normalized_peak = peak / max_possible

    clipped_ratio = _compute_clipped_ratio(
        _iter_samples(frames, sample_width), int(max_possible)
    )

    if channels > 1:
        normalized_rms /= math.sqrt(channels)

    return AudioAnalysisResult(
        path=path,
        duration=duration,
        rms=normalized_rms,
        peak=normalized_peak,
        clipped_ratio=clipped_ratio,
    )
