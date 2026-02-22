# Enhanced Remix-Aware Metadata Parsing

## Context

Many liked songs on YouTube Music are remixes uploaded by aggregator channels (Dubstep uNk, The Dub Rebellion, etc.). The current `parse_title_artist` function does a simple `" - "` split, which loses remix artist credits and sometimes picks up channel names as the artist. The goal is to correctly extract original artists, remixer names, and clean titles from various YouTube Music title formats common in electronic/dubstep music.

## Standards

@agent-os/standards/general.md
@agent-os/standards/error-handling.md

## Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-21-remix-metadata-parsing/` with:
- **plan.md** — This plan
- **shape.md** — Shaping notes from our conversation
- **standards.md** — Relevant standards content
- **references.md** — Reference to existing `parse_title_artist` in metadata.py

## Task 2: Rewrite `parse_title_artist` in `likedmusic/metadata.py`

Add `import re` and two module-level compiled regexes:

```python
_BARE_REMIX_RE = re.compile(r'^([^(]+?)\s+(Remix|Flip|Edit)\b', re.IGNORECASE)
_PAREN_REMIX_RE = re.compile(r'\(([^)]+?)\s+(?:Remix|Flip|Edit)\)', re.IGNORECASE)
```

Add two helpers:

- **`_strip_pipe_tags(title)`** — Split on `" | "`, keep first part. Strips tags like `"| Dubstep | Channel Name"`.
- **`_extract_remixers(text)`** — Use `_PAREN_REMIX_RE.findall()` to find remix parentheticals, split each match on `" & "` (NOT `" x "`) to get individual remixer names.

Rewrite `parse_title_artist` with this logic:

1. Extract structured artist names from `artists` param
2. Strip pipe tags from title
3. If no `" - "` in title → return `(title, structured_artists)` (unchanged)
4. Split on first `" - "` → `prefix`, `suffix`
5. **Case A** — `suffix` starts with bare remix (`_BARE_REMIX_RE` matches):
   - `prefix` is the song title, `suffix` is remix info
   - Wrap remix in parens: `"crystallized (Subtronics Remix) (feat. Inez)"`
   - Artist list = structured artists + remixers (deduplicated with `dict.fromkeys`)
6. **Cases B/C/D** — standard artist-title split:
   - `prefix` is the artist, `suffix` is the song title
   - Extract remixers from song title via `_extract_remixers()`
   - Artist list = `[prefix]` + remixers (deduplicated). Structured artists ignored.

Key rules:
- `" & "` splits into separate artists; `" x "` keeps them as one collaboration
- `(feat. X)` preserved in title as-is (regex only matches Remix/Flip/Edit parens)
- Case-insensitive matching for remix keywords
- No aggregator blocklist needed

### Expected behavior for the four examples:

| Input title | Input artist | Output title | Output artist |
|---|---|---|---|
| `crystallized - Subtronics Remix (feat. Inez)` | John Summit | `crystallized (Subtronics Remix) (feat. Inez)` | John Summit, Subtronics |
| `Labrinth - Mount Everest (YDG & Kade Findley Remix)` | YDG | `Mount Everest (YDG & Kade Findley Remix)` | Labrinth, YDG, Kade Findley |
| `HAVEN. - I Run (HerShe x Roto FLIP) \| Dubstep \| The Cue List` | The Cue List | `I Run (HerShe x Roto FLIP)` | HAVEN., HerShe x Roto |
| `Artemas - I like the way you kiss me (YDG Remix)` | Dubstep uNk | `I like the way you kiss me (YDG Remix)` | Artemas, YDG |

## Task 3: Update Tests in `tests/test_metadata.py`

Existing tests in `TestParseTitleArtist` should still pass (backward compatible). Add:

- **`TestRemixParsing`** — 4 tests covering each example case above
- **`TestRemixEdgeCases`** — Tests for: bare Flip/Edit keywords, `" & "` with 3+ remixers, `" x "` collaboration preserved, pipe tags without remix, `(feat. X)` not extracted as remixer, multiple dashes only split first, deduplication of remixer already in artist list

## Task 4: Run Tests

```bash
source .venv/bin/activate && python -m pytest tests/test_metadata.py -v
```

Verify all existing + new tests pass.

## Files to Modify

- `likedmusic/metadata.py` — Core parsing logic
- `tests/test_metadata.py` — New test classes

## Files Unchanged (callers verified compatible)

- `likedmusic/sync_engine.py` — Calls `parse_title_artist(title, artists)` → same signature, no changes needed
