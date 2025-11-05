# Speech Dataset Preparation Toolkit

This repository provides reference utilities for preparing high-quality
speech-text datasets, focusing on the three core steps of a typical TTS/ASR
corpus creation pipeline:

1. **Audio collection** – capture clean speech at a consistent sample rate
   (16 kHz or 48 kHz are common). Use a treated recording environment, apply
   peak normalization, and export lossless WAV files.
2. **Alignment** – force-align transcripts with recordings using tools such as
   [Montreal Forced Aligner](https://montreal-forced-aligner.readthedocs.io/).
   Store the generated TextGrid/JSON annotations alongside the audio to enable
   downstream validation and trimming.
3. **Preprocessing** – normalize the transcript text and filter noisy audio
   automatically before model training.

The scripts in this repository help automate the third step by producing a
clean metadata file that is compatible with many open-source TTS/ASR toolkits.

## Installation

The utilities rely only on the Python standard library. Create a virtual
environment and install the project in editable mode if you plan to extend it:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

1. Export a metadata file (`metadata.csv` or `metadata.jsonl`) containing
   `utt_id`, `text`, and `audio_path` columns.
2. Place aligned TextGrid/JSON files next to the WAVs (optional but recommended
   for manual checks).
3. Run the preprocessing script:

```bash
python scripts/preprocess_dataset.py \
    --metadata data/metadata.csv \
    --audio-root data/wavs \
    --output data/clean_metadata.csv \
    --min-duration 1.0 \
    --max-duration 15.0 \
    --min-rms 0.01 \
    --max-rms 0.8
```

Custom abbreviation expansions can be supplied with repeated
`--extra-abbreviation KEY=VALUE` flags. The resulting CSV includes duration,
RMS, peak, and clipping statistics for traceability.

## Alignment Tips

* Train a domain-specific acoustic model in Montreal Forced Aligner when
  working with accented speech to improve boundary accuracy.
* Inspect a random subset of TextGrids in Praat to validate the alignments
  before large-scale trimming.
* For long recordings, slice the audio into <30 second segments to maintain
  alignment stability.

## License

This project is provided under the MIT License.
