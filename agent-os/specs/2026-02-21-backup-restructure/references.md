# References for Backup Restructure

## Similar Implementations

### Current state module
- **Location:** `likedmusic/state.py`
- **Relevance:** Being rewritten — current atomic write pattern (tempfile + rename) will be extended with checksum + .bak
- **Key patterns:** EAFP for file loading, const keys for JSON fields

### Sync engine backup logic
- **Location:** `likedmusic/sync_engine.py` (`_backup_file`, `_download_new_songs`, `sync_playlist`)
- **Relevance:** Backup dir usage changes from per-playlist subdirs to flat `Backup/` folder
- **Key patterns:** `_sanitize_filename()` for safe filenames, `shutil.copy2` for backups

### Playlist config
- **Location:** `likedmusic/playlist_config.py`
- **Relevance:** `backup_dir` is already configurable; atomic write pattern to reuse
- **Key patterns:** `save_config()` uses same tempfile + rename pattern

### Config wizard
- **Location:** `likedmusic/config_wizard.py`
- **Relevance:** No changes needed — doesn't touch state files
