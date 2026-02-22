# Interactive Config Wizard

## Context

LikedMusic now supports multi-playlist sync via `~/.likedmusic/config.yml`, but users must create this file manually. We need an interactive CLI wizard — styled like Claude Code's onboarding — that guides users through creating their config. This makes the tool approachable and eliminates YAML hand-editing.

## Standards

@agent-os/standards/general.md
@agent-os/standards/error-handling.md
@agent-os/standards/virtual-env.md

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-21-interactive-config-wizard/` with plan.md, shape.md, standards.md, references.md.

## Task 2: Add Dependencies

**File: `pyproject.toml`**

Add `"questionary>=2.0.0"` and `"rich>=13.0.0"` to `dependencies`.

```bash
source .venv/bin/activate && pip install -e .
```

**Why questionary:** Simpler API than InquirerPy, single dep (`prompt_toolkit`), clean checkbox/confirm/text prompts.
**Why rich:** Panels, tables, spinners, styled text for polished output.

## Task 3: Extend `playlist_config.py` for `max_workers`

**File: `likedmusic/playlist_config.py`**

Add `max_workers` as a top-level YAML key (sibling to `backup_dir`, `playlists`).

- `load_config()` returns 3-tuple: `(playlists, backup_dir, max_workers)`
- `save_config()` accepts `max_workers` param and writes it
- `get_default_config()` returns `MAX_DOWNLOAD_WORKERS` as third element
- Default: `MAX_DOWNLOAD_WORKERS` (4) from `config.py`

Updated YAML structure:
```yaml
backup_dir: ~/Music/LikedMusic-Backup
max_workers: 4
playlists:
  - name: YTM Liked Songs
    source: liked
    apple_music_playlist: YTM Liked Songs
```

## Task 4: Update Call Sites for New `load_config` Signature

**Files: `likedmusic/sync_engine.py`, `likedmusic/cli.py`**

- `sync_engine.py`: Unpack `playlists, backup_dir, max_workers = load_config()`
- `run_sync()`: Use config `max_workers` as default, CLI `--workers` overrides
- `cli.py`: Pass `args.workers` only when explicitly provided (use `None` as argparse default, fall back to config value)

## Task 5: Create Config Wizard Module

**New file: `likedmusic/config_wizard.py`**

### Wizard Flow

```
Step 0: Banner (rich Panel with ASCII art + welcome message)
Step 1: Auth check — verify browser.json exists, run setup_ytmusic_browser() if missing
Step 2: Max workers — questionary.text() with validation (1-16), default 4
Step 3: Fetch playlists — rich Status spinner while calling ytm.get_library_playlists()
Step 4: Playlist select — questionary.checkbox() with "YTM Liked Songs" always first + pre-checked
Step 5: Apple Music names — questionary.text() per playlist, defaults to YTM name
Step 6: Summary — rich Table showing full config, questionary.confirm()
Step 7: Save — call save_config(), print success message
```

Note: Backup directory is NOT prompted — it stays at the default. Backup structure will be redesigned in a separate plan.

### Module Structure

```python
console = Console()

def _ensure_auth() -> bool
def _fetch_library_playlists() -> list[dict]
def _prompt_max_workers() -> int
def _prompt_playlist_selection(library_playlists: list[dict]) -> list[dict]
def _prompt_apple_music_names(selected: list[dict]) -> list[PlaylistConfig]
def _show_summary(playlists, max_workers) -> bool
def run_wizard() -> None
```

### Key Details

- Every `questionary.ask()` result is checked for `None` (non-TTY / Ctrl+C) — abort gracefully
- Playlist fetch wrapped in try/except — if auth expired, tell user to run `likedmusic setup`
- "YTM Liked Songs" uses `source="liked"`, all others use `source=<playlist_name>`
- Resolved `playlistId` from the library fetch is stored in `PlaylistConfig.playlist_id`

## Task 6: Update CLI with `config` Subcommand + Auto-Trigger

**File: `likedmusic/cli.py`**

Add `config` subparser:
```python
config_parser = subparsers.add_parser("config", help="Interactive config wizard")
config_parser.set_defaults(func=cmd_config)
```

Add auto-trigger guard in `cmd_sync`:
```python
if not CONFIG_PATH.exists():
    import questionary
    if questionary.confirm("No config found. Run setup wizard?", default=True).ask():
        from likedmusic.config_wizard import run_wizard
        run_wizard()
```

Update `--workers` default to `None` so we can detect explicit vs. default:
```python
sync_parser.add_argument("--workers", type=int, default=None, ...)
```

In `cmd_sync`, resolve workers: `args.workers or config_max_workers or MAX_DOWNLOAD_WORKERS`.

## Task 7: Add Tests

**New file: `tests/test_config_wizard.py`**
- `test_ensure_auth_found` — browser.json exists, returns True
- `test_ensure_auth_missing_triggers_setup` — calls setup_ytmusic_browser
- `test_prompt_playlist_selection_always_includes_liked` — "YTM Liked Songs" in output
- `test_run_wizard_end_to_end` — all prompts mocked, verify save_config called correctly
- `test_none_return_aborts` — simulate Ctrl+C (questionary returns None)

**Update: `tests/test_playlist_config.py`**
- Update unpacking for 3-tuple return from `load_config`
- Add `test_max_workers_roundtrip`
- Add `test_max_workers_default`

**Update: `tests/test_sync_integration.py`**
- Update `load_config` mock return value to 3-tuple

## Task 8: Run All Tests

```bash
source .venv/bin/activate && python -m pytest tests/ -v
```

## Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `questionary`, `rich` deps |
| `likedmusic/playlist_config.py` | Add `max_workers` to load/save/default |
| `likedmusic/sync_engine.py` | Update `load_config` unpacking, workers precedence |
| `likedmusic/cli.py` | Add `config` subcommand, auto-trigger, workers override |
| `likedmusic/config_wizard.py` | **New** — full wizard implementation |
| `tests/test_config_wizard.py` | **New** — wizard tests |
| `tests/test_playlist_config.py` | Update for 3-tuple, add max_workers tests |
| `tests/test_sync_integration.py` | Update load_config mock |

## Verification

1. `python -m pytest tests/ -v` — all tests pass
2. `likedmusic config` — runs wizard interactively, creates config.yml
3. `rm ~/.likedmusic/config.yml && likedmusic sync --dry-run` — auto-prompts wizard
4. `likedmusic sync --workers 8 --dry-run` — CLI flag overrides config value
5. `cat ~/.likedmusic/config.yml` — verify YAML structure is correct
