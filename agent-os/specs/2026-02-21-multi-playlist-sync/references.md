# References for Multi-Playlist Sync

## Existing Implementations

### Sync Engine
- **Location:** `likedmusic/sync_engine.py`
- **Relevance:** Core pipeline to refactor — currently hardcoded to liked songs
- **Key patterns:** State-based dedup via video IDs, sequential Apple Music track addition for order preservation

### State Management
- **Location:** `likedmusic/state.py`
- **Relevance:** Atomic JSON writes, synced_songs tracking — will be extended for per-playlist orders
- **Key patterns:** `tempfile.mkstemp()` + rename for atomic writes, global `synced_songs` dict

### ytmusicapi
- **Location:** Installed package, docs at ytmusicapi.readthedocs.io
- **Relevance:** `get_playlist(id)` and `get_library_playlists()` methods needed for multi-playlist support
- **Key patterns:** `get_liked_songs()` is just `get_playlist("LM")`, same track dict shape for all playlists
