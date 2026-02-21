# References

## Previous OAuth Setup Flow (Removed)

The original implementation used:
- `ytmusicapi.setup_oauth(client_id, client_secret, filepath)` for interactive setup
- `ytmusicapi.OAuthCredentials` passed as `oauth_credentials` to `YTMusic()`
- Credentials stored at `~/.likedmusic/oauth.json`
- CLI flags `--client-id` and `--client-secret` (also read from env vars)

## New Browser Auth Flow

- `ytmusicapi.setup(filepath)` for interactive setup (prompts user to paste browser request headers)
- `YTMusic(filepath)` with no extra credentials
- Auth stored at `~/.likedmusic/browser.json`
- No CLI flags needed

## ytmusicapi Docs

Browser auth setup: https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html
