# Project Guidelines & Agent Instructions

## Repository Layout & Navigation Pointers

- **Git Repository Root**: `Translation-App/`
  - All source code, tests, configs, and git commits live in `Translation-App/`.
  - Always run git commands, linters, and pytest with working directory set to `Translation-App/`.
- **Governance & Shared Resources (Workspace Root)**:
  - Issues & Specs: `../.scratch/` (see `../docs/agents/issue-tracker.md`).
  - Architecture Decisions: `../docs/adr/` (see `../docs/agents/domain.md`).
  - Domain Glossary: `../GLOSSARY.md`.
  - Coding Standards: `CODING_STANDARDS.md`.
  - Model weights & tools: `../models/`, `../tools/`.

---

## Quality Checks & Commands

Run all commands from `Translation-App/`:
- **Code Linter**: `python scripts/check.py` or `python -m ruff check backend`
- **Unit & Integration Tests**: `python -m pytest backend/tests`
- **Fast Unit Tests**: `python -m pytest backend/tests -m "not slow"`
- **Mobile Typecheck**: `npm run typecheck` (in `mobile/`)

---

## Agent Architecture & Standards

- **Issue tracker**: Follow vertical slicing and issue conventions in `.scratch/`.
- **Triage labels**: Canonical labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `../docs/agents/triage-labels.md`.
- **Domain docs**: Single-context layout (`GLOSSARY.md` + `docs/adr/`).
- **Review Standards**: Enforce rules defined in `CODING_STANDARDS.md` (no magic numbers, complete vertical slices, cross-platform portability, VRAM/device abstraction).
