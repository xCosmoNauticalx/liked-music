# References for Interactive Config Wizard

## Similar Implementations

### Existing setup subcommand

- **Location:** `likedmusic/cli.py`
- **Relevance:** Current CLI structure using argparse subparsers
- **Key patterns:** `cmd_setup` delegates to `setup_ytmusic_browser()`, lazy imports

### Playlist config module

- **Location:** `likedmusic/playlist_config.py`
- **Relevance:** YAML load/save with atomic writes, PlaylistConfig dataclass
- **Key patterns:** `save_config()` uses tempfile+rename, `load_config()` falls back to defaults
