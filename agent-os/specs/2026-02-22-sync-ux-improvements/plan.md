# Sync UX Improvements

Fix quit/ESC behavior, improve menu styling, add rich sync selection UI with counts,
download-only mode, pending songs tracking, and workers prompt in sync flow.

## Key Changes

1. CLI quit sentinel + MENU_STYLE (inverted blue on confirm)
2. State: `apple_music_added` field, `get_pending_songs()`, `mark_apple_music_added()`
3. Sync engine: `download_only` param, `add_pending_to_apple_music()`, graceful Ctrl+C
4. Sync action: pre-fetch YTM counts, checkbox with counts/pending, workers + mode prompts
5. Wizard: remove workers prompt
