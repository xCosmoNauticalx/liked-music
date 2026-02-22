# Configurable Multi-Playlist Sync

## Context

LikedMusic currently only syncs the liked songs playlist with hardcoded paths and playlist names. The user wants to:
1. Make the Apple Music playlist name and backup directory configurable via a YAML config file
2. Support syncing additional YouTube Music playlists beyond just liked songs
3. Deduplicate downloads across playlists (reuse files already downloaded for liked songs)
4. Auto-create Apple Music playlists if they don't exist (with user confirmation)
5. Resolve YTM playlists by name (not ID) and cache resolved IDs

No config file = tool behaves exactly as it does today (backward compatible).

## Standards

@agent-os/standards/general.md
@agent-os/standards/error-handling.md
@agent-os/standards/virtual-env.md

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-21-multi-playlist-sync/` with plan.md, shape.md, standards.md, references.md.

## Task 2: Add PyYAML Dependency

**File: `pyproject.toml`**

Add `"pyyaml"` to `dependencies` list. Source `.venv` first, then install:

```bash
source .venv/bin/activate && pip install -e .
```

## Task 3: Create Playlist Config Module

**New file: `likedmusic/playlist_config.py`**

Dataclass and YAML loading/saving:

```python
@dataclass
class PlaylistConfig:
    name: str                        # Human label, used as key in state
    source: str                      # "liked" or a YTM playlist name
    playlist_id: str | None = None   # Cached YTM playlist ID (None until resolved)
    apple_music_playlist: str = ""   # Target Apple Music playlist name
```

Top-level config also has a `backup_dir` (parent directory). Each playlist gets backed up into a subfolder named after the playlist: `{backup_dir}/{playlist_name}/`.

Functions:
- `load_config() -> tuple[list[PlaylistConfig], Path]` — Parse `~/.likedmusic/config.yml`. Returns (playlists, backup_dir). Return defaults if no file exists.
- `save_config(playlists, backup_dir)` — Write YAML back (atomic write). Used to cache resolved `playlist_id`.
- `get_default_config() -> tuple[list[PlaylistConfig], Path]` — Single liked-songs config matching current hardcoded values.

Config format:
```yaml
backup_dir: ~/Music/LikedMusic-Backup   # parent dir; playlists get subfolders

playlists:
  - name: YTM Liked Songs
    source: liked
    apple_music_playlist: YTM Liked Songs

  - name: EDM Bangers
    source: EDM Bangers
    playlist_id: PLQwVIlKxHM6qv   # cached after first resolve
    apple_music_playlist: EDM Bangers
```

Backup structure on disk:
```
~/Music/LikedMusic-Backup/
├── YTM Liked Songs/
│   ├── Artist - Song [vid1].m4a
│   └── ...
└── EDM Bangers/
    ├── Artist - Song [vid2].m4a
    └── ...
```

Also add `CONFIG_PATH = DATA_DIR / "config.yml"` to `likedmusic/config.py`.

## Task 4: Extend YouTube Music Module

**File: `likedmusic/ytmusic.py`**

Extract shared `_get_ytm_client() -> YTMusic` helper (auth check + instantiation).

Add:
- `fetch_playlist_songs(playlist_id: str) -> list[dict]` — Calls `YTMusic.get_playlist(playlist_id, limit=5000)`, returns `tracks` list. Same shape as `fetch_liked_songs()`.
- `resolve_playlist_id(playlist_name: str) -> str` — Calls `get_library_playlists(limit=None)`, matches by `title`. Raises `ValueError` with available names if not found.

`fetch_liked_songs()` updated to use `_get_ytm_client()` but otherwise unchanged.

## Task 5: Extend State Module for Per-Playlist Orders

**File: `likedmusic/state.py`**

`synced_songs` stays **global** (enables cross-playlist dedup). Playlist order becomes per-playlist.

New state schema (additive, backward compatible):
```json
{
  "synced_songs": {"video_id": {...}},
  "last_sync": "timestamp",
  "playlist_order": ["vid1", "vid2"],
  "playlist_orders": {
    "YTM Liked Songs": ["vid1", "vid2"],
    "EDM Bangers": ["vid3", "vid4"]
  }
}
```

Add:
- `get_playlist_order(state, playlist_name) -> list[str]` — Read from `playlist_orders[name]`, fall back to top-level `playlist_order` for "YTM Liked Songs" backward compat.

Modify:
- `update_playlist_order(state, video_ids, playlist_name=None)` — Add optional `playlist_name` param. Writes to `playlist_orders[name]`. Also updates top-level `playlist_order` when `playlist_name` is None or "YTM Liked Songs" (backward compat).

## Task 6: Refactor Sync Engine for Multi-Playlist

**File: `likedmusic/sync_engine.py`**

### 6a: Extract `sync_playlist(playlist_cfg, sync_state, max_workers, dry_run)`

Single-playlist sync logic extracted from `run_sync()`:

1. Resolve `playlist_id` if `source != "liked"` and not cached → call `resolve_playlist_id()`, cache via `save_config()`
2. Fetch tracks: `fetch_liked_songs()` if `source == "liked"`, else `fetch_playlist_songs(playlist_id)`
3. Determine new songs using **global** `synced_songs` (cross-playlist dedup)
4. For songs already downloaded (in `synced_songs` but not in this playlist yet): skip download, but still add to this playlist's Apple Music playlist
5. Download only truly new songs
6. Embed metadata, backup to `backup_dir / playlist_cfg.name /`
7. Mark synced in global `synced_songs`
8. Ensure Apple Music playlist exists — if not, ask user to create (via `input()` prompt). In dry-run mode, just note it.
9. Add tracks to Apple Music playlist
10. Reorder using per-playlist order from `get_playlist_order()`
11. Update per-playlist order via `update_playlist_order(state, order, playlist_cfg.name)`

### 6b: Parameterize `_backup_file()`

Add `backup_dir: Path` parameter instead of using global `BACKUP_DIR`.

### 6c: Refactor `run_sync()` as orchestrator

```python
def run_sync(
    max_workers=MAX_DOWNLOAD_WORKERS,
    dry_run=False,
    playlist_name=None,    # NEW: sync specific playlist by name
    sync_all=False,        # NEW: sync all configured playlists
) -> None:
```

Logic:
- No flags (default) → sync liked songs only
- `--all` → sync all configured playlists
- `--playlist "Name"` → sync specific playlist by name
- Load config via `load_config()`, filter targets, loop calling `sync_playlist()` for each
- Save state once at the end

## Task 7: Update CLI

**File: `likedmusic/cli.py`**

Add mutually exclusive group to `sync` subcommand:
- `--all` — sync all configured playlists
- `--playlist "Name"` — sync a specific playlist by name

Pass through to `run_sync(sync_all=args.sync_all, playlist_name=args.playlist)`.

## Task 8: Add Tests

**New file: `tests/test_playlist_config.py`**
- `test_load_config_no_file_returns_default`
- `test_load_config_parses_yaml`
- `test_load_config_expands_tilde`
- `test_load_config_validates_required_fields`
- `test_save_config_caches_playlist_id`

**Updates to `tests/test_ytmusic.py`**
- `test_resolve_playlist_id_found`
- `test_resolve_playlist_id_not_found`
- `test_fetch_playlist_songs`

**Updates to `tests/test_state.py`**
- `test_get_playlist_order_from_playlist_orders`
- `test_get_playlist_order_fallback`
- `test_update_playlist_order_with_name`
- `test_update_playlist_order_backward_compat`

## Task 9: Run All Tests

```bash
source .venv/bin/activate && python -m pytest tests/ -v
```

Verify all existing + new tests pass.

## Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `pyyaml` dependency |
| `likedmusic/config.py` | Add `CONFIG_PATH` constant |
| `likedmusic/playlist_config.py` | **New** — PlaylistConfig dataclass, YAML load/save |
| `likedmusic/ytmusic.py` | Add `_get_ytm_client()`, `fetch_playlist_songs()`, `resolve_playlist_id()` |
| `likedmusic/state.py` | Add `get_playlist_order()`, update `update_playlist_order()` signature |
| `likedmusic/sync_engine.py` | Extract `sync_playlist()`, refactor `run_sync()`, parameterize `_backup_file()` |
| `likedmusic/cli.py` | Add `--all` and `--playlist` args |
| `tests/test_playlist_config.py` | **New** — config loading/saving tests |
| `tests/test_ytmusic.py` | Add playlist resolution tests |
| `tests/test_state.py` | Add per-playlist order tests |

## Verification

1. `python -m pytest tests/ -v` — all tests pass
2. `likedmusic sync --dry-run` — behaves same as before (no config file needed)
3. Create `~/.likedmusic/config.yml` with a second playlist, run `likedmusic sync --all --dry-run` — should show both playlists
4. `likedmusic sync --playlist "EDM Bangers" --dry-run` — syncs only that playlist
