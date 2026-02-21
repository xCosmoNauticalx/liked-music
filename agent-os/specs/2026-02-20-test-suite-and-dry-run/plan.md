# Test Suite & Dry-Run Mode

## Goal
Add a pytest test suite covering all modules and a `--dry-run` CLI flag that previews sync operations without side effects.

## Scope
- pytest infrastructure (pyproject.toml dev deps, conftest fixtures)
- Unit tests for pure functions (metadata, state, sync_engine helpers)
- Unit tests with mocks (downloader, state I/O, apple_music, metadata embedding)
- Integration tests for the full sync pipeline
- `--dry-run` flag on the `sync` subcommand
- Dry-run-specific tests

## Out of Scope
- CI/CD pipeline configuration
- Code coverage thresholds
- End-to-end tests against real YouTube Music API
