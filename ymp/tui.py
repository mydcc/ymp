from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label, ProgressBar, Log
from textual.binding import Binding
from textual import work
from textual.reactive import reactive

import threading
import time
import asyncio
import os

# Import existing logic (will need adapting)
from ymp.playlistmanager import Playlist
import ymp.downloader as downloader
import ymp.player as player
import ymp.config as config

class YmpTui(App):
    """A Textual app for YMP (Your Music Player)."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #playlist-container {
        width: 30%;
        height: 100%;
        border: solid green;
        background: $surface;
    }

    #main-container {
        width: 70%;
        height: 100%;
        border: solid blue;
        padding: 1;
    }

    #now-playing {
        text-align: center;
        text-style: bold;
        color: yellow;
        margin-bottom: 1;
        height: 3;
        content-align: center middle;
        background: $boost;
        border: double yellow;
    }

    #progress-bar {
        width: 100%;
        margin-bottom: 1;
    }

    #status-bar {
        background: $panel;
        color: $text;
        height: 1;
    }

    #log-view {
        height: 1fr;
        border: solid gray;
        overflow-y: scroll;
    }

    ListView {
        height: 100%;
    }

    ListItem {
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("space", "toggle_pause", "Play/Pause"),
        Binding("n", "next_song", "Next"),
        Binding("b", "prev_song", "Previous"),
        Binding("s", "shuffle", "Shuffle"),
        Binding("right", "seek_forward", "+10s"),
        Binding("left", "seek_back", "-10s"),
    ]

    title = "YMP - Your Music Player"
    sub_title = "v0.92b1"

    current_song_title = reactive("No song playing")
    is_paused = reactive(False)
    progress_total = reactive(100)
    progress_current = reactive(0)

    def __init__(self, playlist_manager, download_dir, initial_queue=None):
        super().__init__()
        self.playlist = playlist_manager
        # Disable Rich output as we are in TUI
        self.playlist.enable_rich_ui = False

        self.download_dir = download_dir
        self.is_loading = False

        # Add initial items
        if initial_queue:
            for song in initial_queue:
                 self.playlist.addsong(song)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        with Horizontal():
            # Left Panel: Playlist
            with Vertical(id="playlist-container"):
                yield Label("[bold underline]Queue[/]", classes="box-title")
                yield ListView(id="playlist-view")

            # Right Panel: Player & Logs
            with Vertical(id="main-container"):
                yield Static("Now Playing:", classes="label")
                yield Static(self.current_song_title, id="now-playing")
                yield ProgressBar(total=100, show_eta=False, id="progress-bar")
                yield Log(id="log-view")

        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts."""
        self.update_playlist_view()
        self.log_message("YMP Started. Ready to play.")

        # Check for unexpanded playlists in the queue
        self.check_for_playlists()

        # Start the background player loop
        self.run_player_loop()

        # Start progress updater
        self.set_interval(0.5, self.update_progress)

    @work(thread=True)
    def check_for_playlists(self):
        """Checks queue for playlist URLs and expands them in background."""
        # This is a bit tricky because modifying the list while iterating is bad.
        # But we only need to do this once at startup mostly.

        # We look for "list=" items
        to_expand = []
        for idx, song in enumerate(self.playlist.queuedplaylist):
            if isinstance(song, str) and "list=" in song and ("http://" in song or "https://" in song):
                 to_expand.append((idx, song))

        if not to_expand:
            return

        self.app.call_from_thread(self.log_message, "Expanding playlists in background...")

        # Process expansion (simplified: append to end, remove original?)
        # For better UX, we should insert them in place, but that requires locking.
        # Let's just append for now or handle the first one found.

        for idx, url in to_expand:
             items = downloader.get_playlist_info(url)
             if items:
                 # We need to safely modify the list.
                 # Let's schedule a callback to update the main list
                 self.app.call_from_thread(self.expand_playlist_callback, url, items)

    def expand_playlist_callback(self, url, items):
        """Callback to safely update playlist on main thread."""
        # Find the URL and replace it or append
        try:
            # We remove the playlist URL
            if url in self.playlist.queuedplaylist:
                self.playlist.queuedplaylist.remove(url)
                # And extend with new items
                self.playlist.queuedplaylist.extend(items)
                self.update_playlist_view()
                self.log_message(f"Expanded playlist: {len(items)} songs added.")
        except Exception as e:
            self.log_message(f"Error expanding playlist: {e}")

    def log_message(self, msg: str) -> None:
        """Write to the log widget."""
        log = self.query_one(Log)
        log.write_line(msg)

    def update_playlist_view(self) -> None:
        """Syncs the UI list with the playlist manager."""
        list_view = self.query_one("#playlist-view", ListView)
        list_view.clear()

        # Optimization: Only show the first 100 items to prevent UI freezing with large playlists
        max_items = 100
        total_items = len(self.playlist.queuedplaylist)

        for idx, song in enumerate(self.playlist.queuedplaylist[:max_items]):
            title = song
            if isinstance(song, dict):
                title = song.get('title', song.get('url', 'Unknown'))

            list_view.append(ListItem(Label(f"{idx+1}. {title}")))

        if total_items > max_items:
            list_view.append(ListItem(Label(f"... and {total_items - max_items} more items")))

    @work(thread=True)
    def run_player_loop(self):
        """Background thread that manages the queue and playback."""
        # Main loop replacement
        while True:
            # Check if app is exiting
            if not getattr(self, "_running", True):
                break

            # Check if song finished
            if self.playlist.playobj and not self.playlist.playobj.is_playing() and not self.playlist.songpaused:
                self.app.call_from_thread(self.handle_song_finished)

            # Check if we need to start a song (Queue has items, nothing playing)
            elif not self.playlist.playobj and not self.playlist.songpaused and self.playlist.queuedplaylist and not self.is_loading:
                self.app.call_from_thread(self.start_next_song)

            time.sleep(0.5)

    def handle_song_finished(self):
        self.log_message("Song finished.")
        # Logic from original play() loop
        if self.playlist.repeat == 2:
            self.playlist.shiftlastplayedsong()
        elif self.playlist.repeat == 1:
            self.playlist.loopqueue()

        # Trigger next song logic via loop
        self.playlist.playobj = None # Reset
        self.update_playlist_view()

    def start_next_song(self):
        """Downloads and plays next song."""
        # This blocks, so we should run it in a worker or ensure it doesn't freeze UI
        # But we are already in call_from_thread from a worker...
        # actually start_next_song needs to do heavy lifting (download).
        # We should spawn a worker for the download.
        self.is_loading = True
        self.download_and_play()

    @work(thread=True)
    def download_and_play(self):
        if not self.playlist.queuedplaylist:
            # Should not happen if checked correctly before calling, but safe guard
            self.app.call_from_thread(self.set_loading_false)
            return

        song = self.playlist.returnsong() # Pops from queue

        # Update UI to show we popped it
        self.app.call_from_thread(self.update_playlist_view)
        self.app.call_from_thread(self.log_message, f"Fetching info for: {song}...")

        try:
            # Fast Stream Start
            meta_stream, stream_url = downloader.extract_stream_info(song)
            if meta_stream and stream_url:
                self.app.call_from_thread(self.log_message, f"Starting stream: {meta_stream.get('title')}")
                # Start playing stream immediately
                self.app.call_from_thread(self.play_stream, meta_stream, stream_url)

                # Background download for cache (fire and forget)
                self.background_cache(song)
            else:
                self.app.call_from_thread(self.log_message, "Stream info failed, falling back to download...")
                # Fallback
                dir_path = self.download_dir.name if hasattr(self.download_dir, 'name') else self.download_dir
                meta = self.playlist.downloadsong(song, dir_path)
                if meta:
                     self.app.call_from_thread(self.play_downloaded, meta, dir_path)
                else:
                     self.app.call_from_thread(self.log_message, f"Failed to download {song}")
                     self.app.call_from_thread(self.set_loading_false)
        except Exception as e:
            self.app.call_from_thread(self.log_message, f"Error starting song: {e}")
            self.app.call_from_thread(self.set_loading_false)

    @work(thread=True)
    def background_cache(self, song):
        """Downloads the song to cache in the background while it plays."""
        try:
             # We use the standard download function which handles smart cache logic
             downloader.download(song)
             # self.app.call_from_thread(self.log_message, "Cached in background.")
        except Exception:
             pass

    def set_loading_false(self):
        """Helper to reset loading state."""
        self.is_loading = False

    def play_stream(self, meta, url):
        """Plays a URL stream directly."""
        title = meta.get('title', 'Unknown')
        self.current_song_title = title
        self.query_one("#now-playing", Static).update(title)

        # Set the filepath to the URL so genmusic plays the stream
        self.playlist.filepath = url
        self.playlist.playsong(meta, None) # dir_path=None implies stream or not needed for URL

        self.progress_total = meta.get('duration', 100)
        self.query_one(ProgressBar).update(total=self.progress_total)
        self.is_loading = False

    def play_downloaded(self, meta, dir_path):
        title = meta.get('title', 'Unknown')
        self.current_song_title = title
        self.query_one("#now-playing", Static).update(title)
        self.log_message(f"Playing: {title}")

        # LRU Optimization: Touch the file to update mtime so it's not deleted by SmartDownload
        if self.playlist.filepath and os.path.exists(self.playlist.filepath):
            try:
                os.utime(self.playlist.filepath, None)
            except OSError:
                pass

        self.playlist.playsong(meta, dir_path)
        self.progress_total = meta.get('duration', 100)
        self.query_one(ProgressBar).update(total=self.progress_total)
        self.is_loading = False

    def update_progress(self):
        """Updates the progress bar."""
        if self.playlist.playobj and not self.playlist.songpaused:
             # Calculate progress
             if self.playlist.starttime:
                elapsed_ms = (time.time() - self.playlist.starttime) * 1000 + (self.playlist.resumetime or 0)
                elapsed_seconds = elapsed_ms / 1000
                self.progress_current = elapsed_seconds
                self.query_one(ProgressBar).update(progress=elapsed_seconds)

                # Preload logic check
                self.playlist.check_preload(elapsed_seconds)

    # --- Actions ---

    def action_toggle_pause(self):
        if self.playlist.songpaused:
             self.playlist.resumesong(None)
             self.log_message("Resumed.")
             self.is_paused = False
        else:
             self.playlist.pausesong()
             self.log_message("Paused.")
             self.is_paused = True

    def action_next_song(self):
        self.log_message("Skipping to next...")
        self.playlist.nextsong()
        # The loop will pick up the next song

    def action_prev_song(self):
        self.log_message("Skipping back...")
        self.playlist.previoussong()

    def action_shuffle(self):
        self.playlist.shuffleplaylist()
        self.update_playlist_view()
        self.log_message("Queue shuffled.")

    def action_seek_forward(self):
        self.playlist.seeksong(10, None)
        self.log_message("Seek +10s")

    def action_seek_back(self):
        self.playlist.seeksong(-10, None)
        self.log_message("Seek -10s")

    def action_quit(self):
        self.log_message("Exiting...")
        self.playlist.stop_all()
        downloader.removedownload(self.download_dir)
        self.exit()
