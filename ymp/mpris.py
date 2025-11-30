import threading
import importlib

# Placeholder classes
class MprisAdapter: pass

MPRIS_AVAILABLE = False
_MprisAdapter = object
_Server = object

def _try_import_mpris():
    global MPRIS_AVAILABLE, _MprisAdapter, _Server
    try:
        # Dynamic import to catch SyntaxError during module loading
        # This is necessary because mpris_server uses Python 3.12 syntax
        # which crashes the app on Python 3.11 even if inside a try/except block
        # at top level if bytecode compilation fails.
        mpris_adapters = importlib.import_module("mpris_server.adapters")
        mpris_server = importlib.import_module("mpris_server.server")

        _MprisAdapter = mpris_adapters.MprisAdapter
        _Server = mpris_server.Server
        MPRIS_AVAILABLE = True
    except (ImportError, SyntaxError, Exception):
        MPRIS_AVAILABLE = False


# We define the adapter dynamically or as a mixin to avoid
# inheriting from a class that might not exist or be broken.
class YmpMprisAdapterBase:
    """
    Adapter linking the YMP TUI/PlaylistManager to the DBus MPRIS interface.
    Implements the methods required by MprisAdapter.
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
        return False

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
        self.app.call_from_thread(self.app.action_toggle_pause)

    def Seek(self, offset_microseconds):
         seconds = offset_microseconds / 1000000
         self.playlist.seeksong(seconds, None)


class MprisController:
    """
    Manages the MPRIS Server lifecycle.
    """
    def __init__(self, tui_app):
        self.app = tui_app
        self.server = None

        # Try importing now
        _try_import_mpris()

        if not MPRIS_AVAILABLE:
            tui_app.log_message("MPRIS not available (optional dependency missing or incompatible). Media keys disabled.")
            return

        try:
            # Create the adapter class dynamically to inherit from the real MprisAdapter
            class RealYmpMprisAdapter(YmpMprisAdapterBase, _MprisAdapter):
                pass

            self.adapter = RealYmpMprisAdapter(tui_app)
            self.server = _Server("ymp", adapter=self.adapter)

            # Start loop in background
            self.thread = threading.Thread(target=self.server.loop, daemon=True)
            self.thread.start()
            tui_app.log_message("Media Keys (MPRIS) Enabled.")
        except Exception as e:
            tui_app.log_message(f"Failed to start MPRIS: {e}")
            self.server = None

    def update_metadata(self, title, duration=0, artist=""):
        if not self.server: return

        duration_us = int(duration * 1000000) if duration else 0

        metadata = {
            'mpris:trackid': '/ymp/current',
            'mpris:length': duration_us,
            'mpris:artUrl': '',
            'xesam:title': title,
            'xesam:artist': [artist] if artist else [],
            'xesam:album': '',
        }
        try:
            self.server.update_metadata(metadata)
        except:
            pass

    def update_playback_status(self, is_playing):
        if not self.server: return
        status = "Playing" if is_playing else "Paused"
        try:
            self.server.update_playback_status(status)
        except:
            pass
