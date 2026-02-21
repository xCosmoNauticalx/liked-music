# Shape

## Components

### pytest Infrastructure
- `pyproject.toml` gains `[project.optional-dependencies]` with `dev = ["pytest"]`
- `tests/conftest.py` provides `tmp_state_dir` fixture patching `STATE_PATH` and `DOWNLOADS_DIR`

### Unit Tests — Pure Functions
- `tests/test_metadata.py` — `parse_title_artist`, `get_best_thumbnail_url`
- `tests/test_state.py` — `get_synced_video_ids`, `mark_synced`, `update_playlist_order`
- `tests/test_sync_engine.py` — `_sanitize_filename`

### Unit Tests — Mocked
- `tests/test_downloader.py` — mock `yt_dlp.YoutubeDL`
- `tests/test_state_io.py` — `load_state`/`save_state` with `tmp_path`
- `tests/test_apple_music.py` — mock `subprocess.run`
- `tests/test_metadata_embed.py` — mock `requests.get`, `mutagen.mp4.MP4`

### Integration Tests
- `tests/test_sync_integration.py` — mock all external boundaries, test full pipeline flows

### Dry-Run Mode
- `likedmusic/cli.py` — `--dry-run` argument on sync subcommand
- `likedmusic/sync_engine.py` — `dry_run` parameter, early return with `[DRY RUN]` messages
