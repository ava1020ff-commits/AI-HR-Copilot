# Repository Guidelines

## Project Structure & Module Organization

AI-HR is a Python + Streamlit scaffold. `app.py` renders the homepage. `pages/` reserves space for Streamlit pages; `services/` and `database/` are placeholder packages for business logic and persistence. `tests/` contains smoke tests. `.streamlit/config.toml` controls local serving and appearance. No AI calls, uploads, or database connections are implemented. Add functionality only when requested.

## Build, Test, and Development Commands

Use Python 3.11 or 3.12. Run these PowerShell commands from the repository root:

- `python -m venv .venv`: create an isolated environment.
- `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`: install runtime and test dependencies.
- `.\.venv\Scripts\python.exe -m streamlit run app.py`: serve the homepage at `http://127.0.0.1:8501`.
- `.\.venv\Scripts\python.exe -m pytest -q`: run tests.
- `git diff --check`: check tracked changes for whitespace errors.

No separate build step is required. Environment activation is optional. Update `README.md` when setup changes.

## Coding Style & Naming Conventions

Use four-space indentation, UTF-8 files, and type hints for new functions. Name functions and modules with `snake_case`, classes with `PascalCase`, and constants with `UPPER_SNAKE_CASE`. Keep presentation in page scripts and reusable logic in service or database modules. Use Chinese UI copy consistent with the homepage. No formatter or linter is configured; avoid unrelated formatting edits.

## Testing Guidelines

Use pytest with `test_*.py` files and `test_*` functions. Streamlit AppTest checks homepage execution and rendered elements. Add deterministic tests alongside new behavior, including boundary and error cases. Never depend on production services or real personal data. No coverage threshold is configured. Report the verification commands actually run.

## Commit & Pull Request Guidelines

There is no commit history from which to infer a convention. Use short, imperative commit subjects, such as `Add initial project setup`, and keep commits focused. Pull requests should explain the change, its motivation, verification performed, and any configuration requirements. Link relevant issues and include screenshots for visible UI changes.

## Security & Configuration

Never commit credentials, local environment files, or real employee or candidate records. Use synthetic test fixtures and document required configuration with placeholder values. Add suitable ignore rules when introducing tooling or generated artifacts.
