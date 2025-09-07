# Repository Guidelines

## Project Structure & Module Organization
- `app_new.py` / `app.py`: Streamlit entry points (Docker uses `app_new.py`).
- `src/`: Application code
  - `core/`: app factory, config, logging, session, error handling
  - `services/`: OpenAI/vision/search/district logic (no UI)
  - `components/`: Streamlit UI components (`*_ui.py`)
- `pages/`: Streamlit multipage routes.
- `test/`: Pytest tests (e.g., `test_vision_pipeline.py`).
- `models/`, `uploads/`, `downloads/`, `temp/`: runtime assets and data.

## Build, Test, and Development Commands
- Setup (Python 3.11):
  - `python -m venv venv && venv/Scripts/activate` (Windows)
  - `pip install -r requirements.txt`
- Run locally:
  - `streamlit run app_new.py` (or `run.bat` on Windows)
- Tests (pytest):
  - `pytest -q` or `python -m pytest`
  - Example: `pytest -k vision -q`
- Docker (optional):
  - `docker build -t ecoguide .`
  - `docker run -e OPENAI_API_KEY=... -p 8501:8501 ecoguide`

## Coding Style & Naming Conventions
- Python 3.11, 4‑space indentation, PEP 8, add type hints.
- Modules/functions: `snake_case`; classes: `CamelCase`.
- UI code in `src/components` and `pages`; keep `src/services` free of Streamlit imports.
- Keep functions small and pure; handle I/O at edges. Add docstrings for public APIs.

## Testing Guidelines
- Framework: `pytest` with `test_*.py` under `test/`.
- Prefer fast, deterministic tests; use `monkeypatch` to avoid network and model loads (see `test_vision_pipeline.py`).
- Place fixtures and helpers near tests or in `test/conftest.py` if added.
- Ensure all tests pass before opening a PR.

## Commit & Pull Request Guidelines
- Commits: present‑tense, concise; Conventional Commits when reasonable (e.g., `feat(security): ...`, `fix(ui): ...`).
- PRs must include:
  - Clear description and rationale, linked issues (e.g., `Closes #123`).
  - Screenshots/GIFs for UI changes.
  - Notes on config/env changes and any new commands.
  - Passing tests; no secrets or large binaries.

## Security & Configuration Tips
- Secrets: use `.streamlit/secrets.toml` (Streamlit Cloud) or `.env` locally; never commit secrets.
- Relevant env vars: `OPENAI_API_KEY`, `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_SEARCH_ENGINE_ID`, `BING_SEARCH_API_KEY`.
- Central config lives in `src/core/config.py`; resolve API keys via `src/core/utils.resolve_api_key()`.
