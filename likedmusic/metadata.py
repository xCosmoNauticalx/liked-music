"""Embed metadata and album art into M4A files."""

import re
import requests
from pathlib import Path
from mutagen.mp4 import MP4, MP4Cover

# Bare remix at start of string, NOT inside parens (e.g., "Subtronics Remix (feat. Inez)")
_BARE_REMIX_RE = re.compile(r"^([^(]+?)\s+(Remix|Flip|Edit)\b", re.IGNORECASE)

# Parenthesized remix (e.g., "(YDG & Kade Findley Remix)")
_PAREN_REMIX_RE = re.compile(r"\(([^)]+?)\s+(?:Remix|Flip|Edit)\)", re.IGNORECASE)


def _strip_pipe_tags(title: str) -> str:
    """Remove pipe-delimited tags from title (e.g., '| Dubstep | Channel').
    
    Splits the title string on the first occurrence of ' | ' and returns only
    the portion before the delimiter, with leading/trailing whitespace removed.
    This is commonly used to clean YouTube video titles that include genre or
    channel tags appended with pipe separators.
    
    Args:
        title: The title string potentially containing pipe-delimited tags.
    
    Returns:
        The cleaned title string with pipe-delimited tags removed and whitespace
        stripped. If no pipe delimiter is found, returns the original title with
        whitespace stripped.
    """
    return title.split(" | ", 1)[0].strip()


def _extract_remixers(text: str) -> list[str]:
    """Extract remixer names from parenthesized remix/flip/edit patterns.

    Searches for remix, flip, or edit credits enclosed in parentheses and extracts
    the individual remixer names. Multiple remixers separated by ' & ' are split
    into separate entries, while ' x ' is preserved as a collaboration marker.
    
    For example:
    - "(YDG & Kade Findley Remix)" -> ["YDG", "Kade Findley"]
    - "(Artist x Collaborator Remix)" -> ["Artist x Collaborator"]
    
    Args:
        text: The text string to search for parenthesized remix/flip/edit patterns.
            Typically a song title or description containing remix credits.
    
    Returns:
        A list of remixer names extracted from the text. Each name is stripped of
        leading and trailing whitespace. Returns an empty list if no remix patterns
        are found.
    """
    remixers = []
    for credit in _PAREN_REMIX_RE.findall(text):
        for name in credit.split(" & "):
            remixers.append(name.strip())
    return remixers


def parse_title_artist(title: str, artists: list[dict] | None) -> tuple[str, str]:
    """Parse and clean up title and artist fields from video metadata, handling remix patterns.

    This function processes video titles to extract clean song titles and artist names,
    with special handling for remix, flip, and edit credits. It handles multiple formatting
    patterns commonly found in YouTube video titles:
    
    - Case A: Title followed by bare remix info (e.g., "Song Name - Subtronics Remix")
    - Cases B/C/D: Artist followed by song title (e.g., "Artist Name - Song Title")
    
    The function also:
    - Extracts remixer credits from parenthesized patterns like "(Artist Remix)"
    - Strips pipe-delimited tags (e.g., "| Dubstep | Channel")
    - Combines and deduplicates artist names from multiple sources
    - Preserves collaboration markers (' x ') while splitting ' & ' separated names
    
    Args:
        title: The raw video title string to parse. May contain artist names, song titles,
            remix credits, and pipe-delimited tags in various formats.
        artists: Optional list of artist dictionaries from video metadata. Each dictionary
            should contain a "name" key with the artist's name. Can be None if no artist
            metadata is available.
    
    Returns:
        A tuple containing two strings:
        - The cleaned song title with remix credits properly formatted in parentheses
        - A comma-separated string of all artist names (original artists and remixers),
          deduplicated and in order of appearance. Returns empty string if no artists found.
    """
    artist_names = []
    if artists:
        artist_names = [artist["name"] for artist in artists if artist.get("name")]

    title = _strip_pipe_tags(title)

    if " - " not in title:
        remixers = _extract_remixers(title)
        all_artists = list(dict.fromkeys(artist_names + remixers))
        return title, ", ".join(all_artists) if all_artists else ""

    prefix, suffix = (p.strip() for p in title.split(" - ", 1))

    # Case A: suffix starts with bare remix (e.g., "Subtronics Remix (feat. Inez)")
    bare_match = _BARE_REMIX_RE.match(suffix)
    if bare_match:
        remixer_credit = bare_match.group(1).strip()
        remix_keyword = bare_match.group(2)
        remainder = suffix[bare_match.end():]
        clean_title = f"{prefix} ({remixer_credit} {remix_keyword}){remainder}"
        remixer_names = [n.strip() for n in remixer_credit.split(" & ")]
        all_artists = list(dict.fromkeys(artist_names + remixer_names))
        return clean_title, ", ".join(all_artists)

    # Cases B/C/D: prefix is artist, suffix is song title
    remixers = _extract_remixers(suffix)
    all_artists = list(dict.fromkeys([prefix] + remixers))
    return suffix, ", ".join(all_artists)


def get_best_thumbnail_url(thumbnails: list[dict] | None) -> str | None:
    """Select the highest-resolution thumbnail URL from a list of thumbnail dictionaries.
    
    Sorts the provided thumbnail dictionaries by width in descending order and returns
    the URL of the thumbnail with the largest width value. This ensures the best quality
    image is selected for use as album art or cover images.
    
    Args:
        thumbnails: A list of thumbnail dictionaries, where each dictionary is expected
            to contain at least a "width" key (integer) and a "url" key (string). Can be
            None if no thumbnails are available. Thumbnails without a "width" key are
            treated as having width 0.
    
    Returns:
        The URL string of the highest-resolution thumbnail, or None if the thumbnails
        list is None, empty, or if the best thumbnail dictionary does not contain a
        "url" key.
    """
    if not thumbnails:
        return None
    sorted_thumbs = sorted(thumbnails, key=lambda thumb: thumb.get("width", 0), reverse=True)
    return sorted_thumbs[0].get("url")


def embed_metadata(file_path: Path, title: str, artist: str, album: str | None = None, thumbnail_url: str | None = None) -> None:
    """Embed title, artist, album, and cover art metadata into an M4A audio file.
    
    This function writes ID3-style metadata tags to an M4A file using the MP4 container
    format. It sets the song title, artist name, and optionally the album name. If a
    thumbnail URL is provided, the function downloads the image and embeds it as cover
    art, automatically detecting whether to use PNG or JPEG format based on the HTTP
    content type header.
    
    The function modifies the file in place and saves the changes. If downloading or
    embedding the cover art fails, a warning is printed but the function continues to
    save the other metadata fields.
    
    Args:
        file_path: Path object pointing to the M4A file to be modified. The file must
            exist and be a valid MP4/M4A audio file that can be opened by mutagen.
        title: The song title to embed in the file's metadata. This value is written
            to the "\xa9nam" (name) tag.
        artist: The artist name to embed in the file's metadata. This value is written
            to the "\xa9ART" (artist) tag.
        album: Optional album name to embed in the file's metadata. If provided, this
            value is written to the "\xa9alb" (album) tag. If None or empty string,
            no album tag is written.
        thumbnail_url: Optional URL string pointing to an image to use as cover art.
            The image is downloaded via HTTP GET request and embedded in the file.
            Supports both PNG and JPEG formats, with automatic format detection based
            on the response's content-type header. If None, no cover art is embedded.
    
    Returns:
        None. The function modifies the file at file_path in place and does not return
        any value.
    
    Raises:
        The function does not explicitly raise exceptions but may propagate exceptions
        from mutagen.mp4.MP4 if the file cannot be opened or saved. Network or image
        download errors when fetching cover art are caught and logged as warnings
        without interrupting the metadata embedding process.
    """
    audio = MP4(str(file_path))

    audio["\xa9nam"] = [title]
    audio["\xa9ART"] = [artist]
    if album:
        audio["\xa9alb"] = [album]

    if thumbnail_url:
        try:
            resp = requests.get(thumbnail_url, timeout=10)
            resp.raise_for_status()
            image_data = resp.content

            # Detect format from content type
            content_type = resp.headers.get("content-type", "")
            if "png" in content_type:
                fmt = MP4Cover.FORMAT_PNG
            else:
                fmt = MP4Cover.FORMAT_JPEG

            audio["covr"] = [MP4Cover(image_data, imageformat=fmt)]
        except Exception as e:
            print(f"  Warning: Could not download album art for {title}: {e}")

    audio.save()
