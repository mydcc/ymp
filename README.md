# YMP - Your Music Player

A command-line music player for YouTube, Spotify playlists, and local/remote audio streams.

## Features

- **YouTube Playback:** Play single videos or entire playlists/mixes via URL.
- **Smart Downloads:** Intelligently caches songs locally (`~/Music/ymp`) to save data and speed up playback.
  - **Auto-Cleanup:** Automatically deletes oldest songs when a limit (Count or MB) is reached.
  - **Preloading:** Downloads the next song in the background for gapless playback.
- **Search:** Search for songs by title/artist directly (no URL needed).
- **PLS Support:** Play `.pls` playlist files (local or remote URLs), ideal for internet radio.
- **Playlist Management:** Queue management, save/load functionality, and repeat modes.
- **Interactive Config:** Easily configure storage paths and limits via `ymp --config`.
- **Self-Update:** Keep YMP up-to-date with `ymp --update`.
- **Cross-Platform:** Compatible with Linux, macOS, and Windows.

## Installation

### Prerequisites

1. **Python 3.11** (recommended).
2. **FFmpeg** (required for audio processing).

**Debian/Ubuntu:**
```bash
sudo apt-get update && sudo apt-get install -y libasound2-dev ffmpeg python3-pip
```

### Install (Recommended)

Use `pipx` to install YMP in an isolated environment:

```bash
pipx install git+https://github.com/pheinze/ymp.git
```

## Usage

You can start YMP in interactive mode by simply typing `ymp`, or pass arguments directly.

### Command Line Arguments

- **Play a Song / Search directly (No flag needed):**
  ```bash
  ymp "Fairground Attraction - Perfect"
  ```

- **Play a YouTube Video:**
  ```bash
  ymp https://music.youtube.com/watch?v=txapREGWHp0
  ```

- **Play a `.pls` Radio Stream:**
  ```bash
  ymp http://example.com/radio.pls
  ```

- **Play a YouTube Playlist:**
  ```bash
  ymp -y "https://www.youtube.com/playlist?list=PL..."
  # or via direct argument (auto-detects playlist):
  ymp "https://www.youtube.com/playlist?list=PL..."
  ```

- **Play Multiple Links / Songs:**
  ```bash
  ymp -p "Song 1" "Song 2" "https://youtube.com/watch?v=..."
  ```

- **Configure YMP (Storage, Limits):**
  ```bash
  ymp --config
  ```

- **Show Manual:**
  ```bash
  ymp --manual
  ```

- **Update YMP:**
  ```bash
  ymp --update
  ```

### Smart Downloads & Configuration

YMP automatically manages your music cache to ensure instant playback. By default, it stores files in `~/Music/ymp` and keeps the last 10 songs.

Use `ymp --config` to adjust:
*   **Music Directory:** Change where songs are stored.
*   **Max Songs:** Set how many songs to keep (e.g., 50 or 0 for unlimited).
*   **Max Storage:** Set a limit in MB (e.g., 500 MB).

### Interactive Commands

Once running, control the player by typing commands:

| Command | Action |
| :--- | :--- |
| `play` / `pause` | Resume or pause playback |
| `next` / `back` | Skip to next or previous song |
| `seek 10` | Fast forward 10 seconds |
| `seek -10` | Rewind 10 seconds |
| `shuffle` | Shuffle the current queue |
| `save` / `load` | Save or load playlists |
| `download` | Download current song (to permanent folder) |
| `[url]` | Paste a URL (YouTube, .mp3, .pls) to add it to the queue |

## Support

If you enjoy using YMP, feel free to support the development!

**Bitcoin:** `bc1qgrm2kvs27rfkpwtgp5u7w0rlzkgwrxqtls2q4f`
