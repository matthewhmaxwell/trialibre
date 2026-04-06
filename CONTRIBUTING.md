# Contributing to Trialibre

Trialibre is a project of the **American Institute for Medical Research (AIMR)**, a non-profit organization. Thank you for considering contributing — every contribution helps connect more patients with clinical trials.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/trialibre.git`
3. Install the backend in dev mode: `cd backend && pip install -e ".[dev]"`
4. Install frontend deps: `cd frontend && npm install`
5. Run tests: `pytest tests/`
6. Start developing: `trialibre serve --reload`

## Development Workflow

1. Create a branch from `main`: `git checkout -b feature/your-feature`
2. Make your changes
3. Run the linter: `ruff check backend/src/`
4. Run tests: `pytest tests/ -v`
5. Build the frontend: `cd frontend && npm run build`
6. Commit with a clear message
7. Open a pull request

## What We're Looking For

### High-Impact Contributions
- **New LLM providers** — Add support for Google Gemini, Mistral, Cohere, etc.
- **New languages** — Add translation files and test with clinical notes in your language
- **New trial registries** — EU Clinical Trials Register, ICTRP, ANZCTR, etc.
- **Ingestion formats** — CDISC ODM, REDCap exports, Epic FHIR bundles
- **Evaluation data** — Annotated patient-trial pairs for more disease areas

### Always Welcome
- Bug fixes with a test that reproduces the issue
- Documentation improvements
- Accessibility improvements
- Performance optimizations with benchmarks

### Before Starting Large Changes
Open an issue first to discuss your approach. This saves time for everyone.

## Code Style

- **Python**: We use `ruff` for linting. Run `ruff check --fix backend/src/` before committing.
- **TypeScript**: Standard React patterns, functional components, hooks.
- **CSS**: Tailwind utility classes. No custom CSS unless necessary.
- **Tests**: Every new feature should include tests. Every bug fix should include a regression test.

## Project Structure

- `backend/src/ctm/` — Python backend
- `backend/tests/` — pytest tests
- `backend/sandbox/` — Sample data (patients, trials, ground truth)
- `frontend/src/` — React frontend
- `frontend/src/i18n/` — Translation files

## Adding a New Language

1. Copy `frontend/src/i18n/en.json` to `frontend/src/i18n/{lang}.json`
2. Translate all strings
3. Register it in `frontend/src/i18n/index.ts`
4. Add the language code to the `LanguageSwitcher` component
5. Test with clinical notes in that language

## Disclaimer

Trialibre is a screening tool. It does not provide medical advice and should not be used as a substitute for clinical judgment. All matches require verification by a qualified clinician.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Contact

For questions about contributing, reach out to the AIMR engineering team via GitHub Issues or at the [American Institute for Medical Research](https://aimr.org).
