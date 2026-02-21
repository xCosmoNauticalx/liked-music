# Shaping Notes: Switch to Browser Auth

## Problem

YouTube Music's OAuth-based API (`get_liked_songs`) started returning HTTP 400 "Request contains an invalid argument". This is a server-side change by Google. Browser-based auth (extracting cookies/headers from a live browser session) continues to work.

## Solution

Replace `ytmusicapi`'s OAuth flow with its browser auth flow:
- `setup_oauth(...)` → `setup(filepath=...)`
- `YTMusic(path, oauth_credentials={...})` → `YTMusic(path)`
- `oauth.json` → `browser.json`

## Side Effects Fixed

- Duplicate `_get_credentials` function in `cli.py` removed
- `--client-id` and `--client-secret` CLI args removed (no longer needed)

## No-Gos

- No changes to download, metadata, Apple Music, or state logic
- No changes to test structure — only call-site updates
- No backwards compatibility shims for old `oauth.json`
