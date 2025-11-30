try:
    from mpris_server.adapters import MprisAdapter
    from mpris_server.events import EventAdapter
    from mpris_server.server import Server
    MPRIS_AVAILABLE = True
except ImportError:
    MPRIS_AVAILABLE = False
    # Mock classes for Type Hinting / Safe Import
    class MprisAdapter: pass
    class EventAdapter: pass
    class Server: pass

import threading

class YmpMprisAdapter(MprisAdapter):
    """
    Adapter linking the YMP TUI/PlaylistManager to the DBus MPRIS interface.
    """
    def __init__(self, tui_app):
        self.app = tui_app
        self.playlist = tui_app.playlist

    def CanQuit(self):
        return True

    def CanRaise(self):
        return False

    def CanSetFullscreen(self):
        return False

    def HasTrackList(self):
        return False # Keeping it simple for now

    def Identify(self):
        return "ymp"

    def DesktopEntry(self):
        return "ymp"

    def Quit(self):
        self.app.action_quit()

    # --- Player Interface ---

    def CanGoNext(self):
        return True

    def CanGoPrevious(self):
        return True

    def CanPause(self):
        return True

    def CanPlay(self):
        return True

    def CanSeek(self):
        return True

    def CanControl(self):
        return True

    def PlayPause(self):
        self.app.call_from_thread(self.app.action_toggle_pause)

    def Play(self):
        if self.playlist.songpaused:
            self.app.call_from_thread(self.app.action_toggle_pause)

    def Pause(self):
        if not self.playlist.songpaused:
             self.app.call_from_thread(self.app.action_toggle_pause)

    def Next(self):
        self.app.call_from_thread(self.app.action_next_song)

    def Previous(self):
        self.app.call_from_thread(self.app.action_prev_song)

    def Stop(self):
        self.app.call_from_thread(self.app.action_toggle_pause) # Just pause for now

    def Seek(self, offset_microseconds):
         # Offset is relative to current position
         # offset is in microseconds (1e-6 s)
         seconds = offset_microseconds / 1000000
         self.playlist.seeksong(seconds, None)


class MprisController:
    """
    Manages the MPRIS Server lifecycle.
    """
    def __init__(self, tui_app):
        self.app = tui_app
        self.server = None
        self.adapter = None

        if not MPRIS_AVAILABLE:
            tui_app.log_message("MPRIS not available (install mpris_server). Media keys disabled.")
            return

        try:
            self.adapter = YmpMprisAdapter(tui_app)
            self.server = Server("ymp", adapter=self.adapter)

            # Start loop in background
            self.thread = threading.Thread(target=self.server.loop, daemon=True)
            self.thread.start()
            tui_app.log_message("Media Keys (MPRIS) Enabled.")
        except Exception as e:
            tui_app.log_message(f"Failed to start MPRIS: {e}")
            self.server = None

    def update_metadata(self, title, duration=0, artist=""):
        if not self.server: return

        # Duration in microseconds
        duration_us = int(duration * 1000000) if duration else 0

        metadata = {
            'mpris:trackid': '/ymp/current',
            'mpris:length': duration_us,
            'mpris:artUrl': '', # Could add thumb path
            'xesam:title': title,
            'xesam:artist': [artist] if artist else [],
            'xesam:album': '',
        }
        self.server.update_metadata(metadata)

    def update_playback_status(self, is_playing):
        if not self.server: return
        status = "Playing" if is_playing else "Paused"
        self.server.update_playback_status(status)
