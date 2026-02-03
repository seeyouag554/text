# Caffeine Intake Tracker

This repository contains a minimal FastAPI backend that lets users track their daily caffeine intake while checking it against health limits.

## Getting started

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run the API locally:

   ```bash
   uvicorn app.main:app --reload
   ```

   The server listens on `http://127.0.0.1:8000` and exposes the interactive docs at `/docs`.

3. Run the automated tests:

   ```bash
   pytest
   ```

## Core features

- Create and update users with weight and preferred sleep time.
- Register caffeine templates (coffee drinks, energy drinks, etc.).
- Log intake records and receive feedback on:
  - **Single serving** limit (`≤200mg` or `≤3mg/kg`).
  - **Daily total** limit (`≤400mg` or `≤5.7mg/kg`).
  - Whether the record is **within the 6-hour no-caffeine window** before the configured sleep time.
- Fetch per-day summaries to understand total consumption and whether limits were exceeded.

The business rules align with the thresholds described in `docs/caffeine_app_plan.md` and serve as a foundation for building the full application described there.
