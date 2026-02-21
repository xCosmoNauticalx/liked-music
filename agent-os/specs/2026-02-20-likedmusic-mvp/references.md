# LikedMusic MVP — References

## ytmusicapi

- **Docs:** https://ytmusicapi.readthedocs.io/
- **PyPI:** `ytmusicapi>=1.11.0`
- **OAuth setup:** `ytmusicapi.setup_oauth(client_id, client_secret, filepath)` — interactive browser flow
- **Key method:** `YTMusic(oauth_path).get_liked_songs(limit=5000)` returns `{tracks: [{videoId, title, artists: [{name}], album: {name}, thumbnails: [{url, width, height}]}]}`
- **Note:** `title` field may contain "Artist - Title" combined format in some cases

## yt-dlp

- **Docs:** https://github.com/yt-dlp/yt-dlp
- **Python API:** `yt_dlp.YoutubeDL(opts).download([url])`
- **Key options:**
  - `format: bestaudio/best`
  - `postprocessors: [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a'}]`
  - `outtmpl: {output_dir}/{video_id}.%(ext)s`
- **Thread safety:** Each thread needs its own `YoutubeDL` instance
- **Dependency:** Requires `ffmpeg` installed (`brew install ffmpeg`)

## mutagen

- **Docs:** https://mutagen.readthedocs.io/
- **M4A tags via `mutagen.mp4.MP4`:**
  - `\xa9nam` → title
  - `\xa9ART` → artist
  - `\xa9alb` → album
  - `covr` → cover art (`MP4Cover` with `IMAGEFORMAT_JPEG` or `IMAGEFORMAT_PNG`)

## AppleScript / Music.app

- **Add file:** `tell application "Music" to add POSIX file "/path/to/file.m4a"`
- **Create playlist:** `tell application "Music" to make new playlist with properties {name:"X"}`
- **Add to playlist:** `tell application "Music" to add POSIX file "/path" to playlist "X"`
- **Move track:** `tell application "Music" to move track N of playlist "X" to end of playlist "X"`
- **List tracks:** `tell application "Music" to get name of every track of playlist "X"`
- **Execution:** `subprocess.run(['osascript', '-e', script])`

## System Requirements

- macOS (for Music.app / AppleScript)
- Python >= 3.10
- ffmpeg (`brew install ffmpeg`)
