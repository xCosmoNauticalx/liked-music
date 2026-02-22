# Remix-Aware Metadata Parsing — Shaping Notes

## Scope

Enhance `parse_title_artist` to correctly handle remix/flip/edit tracks uploaded by aggregator channels on YouTube Music. Extract real artist names and remixer credits from title strings, strip channel tags, and preserve feat. credits.

## Decisions

- Always split on " - " when present in title (no blocklist of aggregator channels)
- Detect bare remix patterns (suffix starts with "Name Remix/Flip/Edit") as Case A vs. standard artist-title split
- " & " splits into separate artists; " x " is a collaboration marker (kept together)
- Remix keywords: Remix, Flip, Edit (case-insensitive)
- Always trust structured artist in Case A (bare remix); ignore structured artist in standard splits
- (feat. X) preserved in title, not extracted

## Context

- **Visuals:** None
- **References:** Existing `parse_title_artist` in `likedmusic/metadata.py`
- **Product alignment:** Supports MVP goal of syncing liked songs with correct metadata to Apple Music

## Standards Applied

- root/general — Keep code simple and readable
- root/error-handling — Use EAFP pattern
