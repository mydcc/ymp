from yt_dlp import YoutubeDL
from requests import get
from bs4 import BeautifulSoup
import re , json ,tempfile, os
import ymp.config as config
from rich.progress import Progress, BarColumn, TextColumn, TransferSpeedColumn, TimeElapsedColumn

def spotifyparser(url):
    """
    Parses a Spotify playlist URL to extract track information.

    Note: This method is fragile as it relies on scraping the Spotify website,
    which can change at any time. A more robust solution would use the Spotify API.
    """
    print("Pinging "+url)
    try:
        spotifyhtml=get(url)
        soup=BeautifulSoup(spotifyhtml.content,"lxml")
        tags=soup('script')
        if len(tags) < 6:
            print("[red]Error: Spotify page structure changed. Cannot find script tags.")
            return []

        # Heuristic: Look for the script containing the entity data if index 5 fails
        target_content = None
        for tag in tags:
            if tag.contents and "Spotify.Entity =" in tag.contents[0]:
                target_content = tag.contents[0]
                break

        if not target_content:
            # Fallback to legacy index if search failed (though search should have found it)
            if len(tags) > 5 and tags[5].contents:
                target_content = tags[5].contents[0]

        if not target_content:
             print("[red]Error: Could not find Spotify Entity data.")
             return []

        x=re.findall("Spotify.Entity = (.*);", target_content)
        if not x:
             print("[red]Error: Could not extract JSON from Spotify script.")
             return []

        data=x[0]
        jsonfile=json.loads(data)

        print("Adding "+jsonfile['name']+" To Queue." )
        tracks=jsonfile['tracks']['items']

        tracklist=[]

        for track in tracks:
            trackname=track['track']['name']
            artistname=""
            for artist in track['track']['artists']:
                artistname=artistname+" "+artist['name']
            tracklist.append(trackname+artistname)

        return tracklist
    except Exception as e:
        print(f"Error parsing Spotify playlist: {e}")
        return []

def get_playlist_info(url):
    """Extracts video info from a playlist URL without downloading."""
    options = {
        'extract_flat': 'in_playlist',
        'quiet': True,
        'no_warnings': True,
    }
    with YoutubeDL(options) as ytdl:
        try:
            meta = ytdl.extract_info(url, download=False)
            return meta.get('entries', [])
        except Exception as e:
            print(f"Error fetching playlist info: {e}")
            return []

def extract_stream_info(link):
    """
    Fast extraction of stream URL for instant playback.
    Returns (meta_dict, stream_url).
    """
    options = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'noplaylist': True,
    }
    with YoutubeDL(options) as ytdl:
        try:
            # extract_info(download=False) usually returns the stream URL
            meta = ytdl.extract_info(link, download=False)
            if 'entries' in meta:
                meta = meta['entries'][0]

            return meta, meta.get('url')
        except Exception as e:
            print(f"Error fetching stream info: {e}")
            return None, None

def download(link, dir_path=None):
    """
    Downloads a song from YouTube using yt-dlp.
    """
    # Determine target directory
    if config.is_smart_download_enabled():
        target_dir = config.get_music_dir()
        os.makedirs(target_dir, exist_ok=True)
        config.manage_storage()
    else:
        target_dir = dir_path if dir_path else tempfile.gettempdir()

    options={
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(target_dir, '%(artist)s - %(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }, {
            'key': 'EmbedThumbnail',
        }],
        'writethumbnail': True,
        'add_metadata': True,
        'default_search': 'ytsearch',
        'quiet': True,
        'no_warnings': True,
        'nooverwrites': True, # Smart Cache: don't download if exists
        'continuedl': True,
    }

    filepath = None
    with YoutubeDL(options) as ytdl:
        try:
            # We assume 'link' can be a URL or a search query
            # If it's a search query, we might want to ensure we get the SAME video
            # as extract_stream_info did. Ideally we pass the direct video ID.
            # But for now, relying on 'default_search' is okay.
            meta = ytdl.extract_info(link, download=True)
            if 'entries' in meta:
                meta = meta['entries'][0]

            # Get the actual filename
            filepath = ytdl.prepare_filename(meta)
            filepath = os.path.splitext(filepath)[0] + '.mp3'

            return meta, filepath

        except Exception as e:
            print(f"Download Error: {e}")
            return None, None

def speed_text(speed):
    if speed is None:
        return ""
    return f"{speed / 1024:.1f} KiB/s"

def parse_pls(url_or_path):
    """
    Parses a PLS file (local path or URL) and returns a list of URLs/files.
    """
    content = ""
    # Check if it's a URL
    if url_or_path.startswith('http://') or url_or_path.startswith('https://'):
        try:
            print(f"Fetching PLS from {url_or_path}...")
            response = get(url_or_path, timeout=10)
            if response.status_code == 200:
                content = response.text
            else:
                print(f"[red]Error fetching PLS: Status code {response.status_code}")
                return []
        except Exception as e:
            print(f"[red]Error fetching PLS: {e}")
            return []
    # Check if it's a local file
    elif os.path.exists(url_or_path):
        try:
            with open(url_or_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"[red]Error reading PLS file: {e}")
            return []
    else:
        # Not a file or URL we can handle here
        return []

    urls = []
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        # Look for FileX=http://...
        # Case insensitive check for 'file'
        if line.lower().startswith('file'):
            parts = line.split('=', 1)
            if len(parts) == 2:
                urls.append(parts[1].strip())

    if urls:
        print(f"Found {len(urls)} entries in PLS file.")
    else:
        print("No entries found in PLS file.")

    return urls

def makedownload(permanent=False):
    """
    Deprecated: The new download logic handles directories via config.
    Kept for backward compatibility with existing main calls.
    """
    if permanent or config.is_smart_download_enabled():
        return config.get_music_dir()
    else:
        return tempfile.TemporaryDirectory()

def removedownload(dir):
    """Removes the temporary download directory if it is one."""
    if isinstance(dir, tempfile.TemporaryDirectory):
        try:
            dir.cleanup()
        except:
            pass
