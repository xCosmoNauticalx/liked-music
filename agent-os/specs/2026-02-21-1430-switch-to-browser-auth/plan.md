# Switch LikedMusic from OAuth to Browser Auth

## Context

YouTube Music's server-side API changed and broke OAuth-based requests (`get_liked_songs` returns HTTP 400 "Request contains an invalid argument"). Browser-based auth (cookie/header extraction from a live browser session) still works. This plan removes OAuth entirely and replaces it with ytmusicapi's browser auth setup, eliminating the `--client-id` / `--client-secret` CLI args in the process. A duplicate `_get_credentials` function in `cli.py` is also fixed as part of this work.

---

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-21-1430-switch-to-browser-auth/` with:
- `plan.md` — this full plan
- `shape.md` — shaping notes from our conversation
- `standards.md` — applicable standards (error-handling, virtual-env)
- `references.md` — reference to existing OAuth setup flow

---

## Task 2: Rename constant in `config.py`

**File:** `likedmusic/config.py`

Rename `OAUTH_PATH = DATA_DIR / "oauth.json"` → `BROWSER_AUTH_PATH = DATA_DIR / "browser.json"`

This cascades to all other files. Do this first.

---

## Task 3: Replace auth logic in `ytmusic.py`

**File:** `likedmusic/ytmusic.py`

**Imports:**
- Remove: `OAuthCredentials, setup_oauth`
- Add: `setup` (from ytmusicapi)
- Change: `OAUTH_PATH` → `BROWSER_AUTH_PATH`

**Delete** `setup_ytmusic_oauth(client_id, client_secret)`, replace with:
```python
def setup_ytmusic_browser() -> None:
    """Run interactive browser headers setup and save to disk."""
    setup(filepath=str(BROWSER_AUTH_PATH))
    print(f"Browser auth headers saved to {BROWSER_AUTH_PATH}")
```

**Update** `fetch_liked_songs` — remove credential params, use EAFP pattern (per error-handling standard), no `oauth_credentials`:
```python
def fetch_liked_songs() -> list[dict]:
    try:
        ytm = YTMusic(str(BROWSER_AUTH_PATH))
    except Exception as e:
        raise FileNotFoundError(
            f"Browser auth headers not found at {BROWSER_AUTH_PATH}. "
            "Run 'likedmusic setup' first."
        ) from e
    response = ytm.get_liked_songs(limit=5000)
    tracks = response.get("tracks", [])
    print(f"Fetched {len(tracks)} liked songs from YouTube Music")
    return tracks
```

---

## Task 4: Remove credential params from `sync_engine.py`

**File:** `likedmusic/sync_engine.py`

Update `run_sync` signature — remove `client_id: str, client_secret: str`:
```python
def run_sync(max_workers: int = MAX_DOWNLOAD_WORKERS, dry_run: bool = False) -> None:
```

Update the call on line 47:
```python
tracks = ytmusic.fetch_liked_songs()
```

---

## Task 5: Overhaul `cli.py`

**File:** `likedmusic/cli.py`

1. **Remove** `import os` (only used by `_get_credentials`)
2. **Delete both copies** of `_get_credentials` (lines 9–70; it's duplicated — a bug)
3. **Rewrite `cmd_setup`** — no credentials, call `setup_ytmusic_browser()`:
   ```python
   def cmd_setup(args: argparse.Namespace) -> None:
       """Run browser auth setup flow."""
       from likedmusic.ytmusic import setup_ytmusic_browser
       ensure_dirs()
       setup_ytmusic_browser()
   ```
4. **Rewrite `cmd_sync`** — no credentials:
   ```python
   def cmd_sync(args: argparse.Namespace) -> None:
       """Run full sync pipeline."""
       from likedmusic.sync_engine import run_sync
       run_sync(max_workers=args.workers, dry_run=args.dry_run)
   ```
5. **Remove** `--client-id` and `--client-secret` from both subparsers
6. **Update** setup subparser help: `"Set up browser auth headers"`

---

## Task 6: Update tests

**File:** `tests/test_sync_integration.py`

9 call sites to update — all `run_sync("id", "secret")` → `run_sync()` and `run_sync("id", "secret", dry_run=True)` → `run_sync(dry_run=True)`.

The mock patch target (`likedmusic.sync_engine.ytmusic.fetch_liked_songs`) stays the same.

---

## Verification

```bash
source .venv/bin/activate

# Run tests
pytest tests/ -v

# Verify CLI help updated (no --client-id / --client-secret)
likedmusic setup --help
likedmusic sync --help

# End-to-end dry run (requires browser.json already set up)
likedmusic sync --dry-run
```

## Critical Files

- `likedmusic/config.py` — constant rename (do first)
- `likedmusic/ytmusic.py` — core auth logic replacement
- `likedmusic/sync_engine.py` — remove credential params from `run_sync`
- `likedmusic/cli.py` — remove duplicate function + credential args
- `tests/test_sync_integration.py` — update 9 `run_sync` call sites
