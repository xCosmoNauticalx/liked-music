# Applicable Standards

## Error Handling

Use EAFP (Easier to Ask Forgiveness than Permission) pattern — attempt the operation, catch exceptions, re-raise with user-friendly messages. Do not pre-check file existence with `.exists()` before opening.

Applied in `fetch_liked_songs`:
```python
try:
    ytm = YTMusic(str(BROWSER_AUTH_PATH))
except Exception as e:
    raise FileNotFoundError(...) from e
```

## Virtual Environment

All commands run inside `.venv/` (created via `python -m venv .venv`). Activate with `source .venv/bin/activate` before running pytest or CLI commands.

## Minimal Changes

Only change what is required. Do not refactor surrounding code, add docstrings to unchanged functions, or add extra error handling for scenarios that can't happen.
