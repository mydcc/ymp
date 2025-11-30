import time
import os
import sys
import subprocess
import signal

# Check for audio device on Linux
AUDIO_AVAILABLE = True
if sys.platform == 'linux' and not os.path.exists('/dev/snd'):
    AUDIO_AVAILABLE = False

class MockPlayObj:
    """Mock playback object for environments without audio."""
    def __init__(self, duration_seconds=100):
        self.start_time = time.time()
        self.duration = duration_seconds
        self.running = True

    def is_playing(self):
        if not self.running:
            return False
        return True # Infinite for streams/mock

    def stop(self):
        self.running = False

    def wait_done(self):
        while self.is_playing():
            time.sleep(0.1)

class FFplayProcess:
    """Wrapper around ffplay subprocess."""
    def __init__(self, process):
        self.process = process
        self.paused = False

    def is_playing(self):
        if self.process.poll() is not None:
            return False
        return True

    def stop(self):
        if self.is_playing():
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()

def genmusic(filepath, start_time_ms):
    """
    Starts playback using ffplay.
    Returns (playobj, start_time_epoch).
    """
    if not AUDIO_AVAILABLE:
        return MockPlayObj(), time.time()

    cmd = ['ffplay', '-nodisp', '-autoexit', '-hide_banner', '-loglevel', 'error']

    # Seek if needed (ffplay takes seconds)
    if start_time_ms > 0:
        start_seconds = start_time_ms / 1000.0
        cmd.extend(['-ss', str(start_seconds)])

    cmd.append(filepath)

    try:
        # Start ffplay in a new process group so signals (like Ctrl+C) don't kill it immediately
        # if the python script handles them.
        start_new_session = False
        if sys.platform != 'win32':
            start_new_session = True

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=start_new_session
        )
        return FFplayProcess(process), time.time()
    except Exception as e:
        print(f"Error starting ffplay: {e}")
        return MockPlayObj(), time.time()

def pausemusic(playobj):
    """
    Pauses playback.
    Note: For ffplay subprocess, 'pausing' effectively means stopping.
    True pausing via SIGSTOP is flaky across platforms and doesn't work for streams easily.
    We return the stop time so resume can try to seek back (if not live stream).
    """
    if playobj and isinstance(playobj, FFplayProcess):
        playobj.stop()
    elif playobj:
        playobj.stop()

    return time.time()

def wait():
    """Wait for current playback."""
    time.sleep(0.1)
