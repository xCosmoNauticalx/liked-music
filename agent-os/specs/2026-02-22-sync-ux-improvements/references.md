# References for Sync UX Improvements

## CLI main loop

- **Location:** `likedmusic/cli.py`
- **Relevance:** Quit option, menu loop, MENU_STYLE

## Sync action

- **Location:** `likedmusic/actions/sync.py`
- **Relevance:** Full rewrite target; pre-fetch flow, checkbox UI

## Sync engine

- **Location:** `likedmusic/sync_engine.py`
- **Relevance:** `sync_playlist()` and `run_sync()` for download_only + Ctrl+C handling

## State module

- **Location:** `likedmusic/state.py`
- **Relevance:** `mark_synced()`, `synced_songs` schema for pending field
