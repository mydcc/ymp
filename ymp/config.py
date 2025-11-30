import configparser
import os
import shutil

CONFIG_DIR = os.path.expanduser('~/.config/ymp')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.ini')

DEFAULT_CONFIG = {
    'General': {
        'music_dir': os.path.expanduser('~/Music/ymp'),
        'playlist_dir': os.path.expanduser('~/.config/ymp/playlists'),
    },
    'SmartDownload': {
        'enabled': 'True',
        'permanent_mode': 'False', # If True, disables auto-deletion (runtime override)
        'max_songs': '10',  # Number of songs to keep
        'max_storage_mb': '0', # 0 = unlimited/disabled
        'preload_enabled': 'True',
        'preload_trigger_seconds': '10', # Start loading next song when current song > 10s played
    }
}

def get_config():
    """Reads the configuration file and returns a config object."""
    config = configparser.ConfigParser()

    # Load defaults first
    config.read_dict(DEFAULT_CONFIG)

    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    else:
        save_config(config) # Create file if missing

    return config

def save_config(config):
    """Saves the configuration object to file."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

def update_setting(section, key, value):
    """Updates a single setting."""
    config = get_config()
    if not config.has_section(section):
        config.add_section(section)
    config.set(section, key, str(value))
    save_config(config)

# --- Helper accessors ---

def get_music_dir():
    return os.path.expanduser(get_config()['General']['music_dir'])

def get_playlist_dir():
    path = os.path.expanduser(get_config()['General']['playlist_dir'])
    os.makedirs(path, exist_ok=True)
    return path

# Runtime flag to override configuration
_runtime_permanent = False

def set_runtime_permanent_storage(enabled):
    global _runtime_permanent
    _runtime_permanent = enabled

def is_smart_download_enabled():
    if _runtime_permanent:
        return True # It is enabled in the sense that we download, but deletion is handled separately
    return get_config().getboolean('SmartDownload', 'enabled')

def is_permanent_mode():
    return _runtime_permanent or get_config().getboolean('SmartDownload', 'permanent_mode', fallback=False)

def get_max_songs():
    return get_config().getint('SmartDownload', 'max_songs')

def get_max_storage_mb():
    return get_config().getint('SmartDownload', 'max_storage_mb')

def is_preload_enabled():
    return get_config().getboolean('SmartDownload', 'preload_enabled')

def get_preload_trigger():
    return get_config().getint('SmartDownload', 'preload_trigger_seconds')

def check_disk_usage(path):
    """Returns used disk space in MB for a directory."""
    total_size = 0
    if not os.path.exists(path):
        return 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024)

def manage_storage():
    """Enforces Smart Download limits (max songs / max storage)."""
    if is_permanent_mode():
        return # Skip cleanup in permanent mode

    music_dir = get_music_dir()
    if not os.path.exists(music_dir):
        return

    config = get_config()
    max_songs = config.getint('SmartDownload', 'max_songs')
    max_mb = config.getint('SmartDownload', 'max_storage_mb')

    # Recursively find mp3 files to handle nested directories
    files = []
    for dirpath, _, filenames in os.walk(music_dir):
        for f in filenames:
            if f.endswith('.mp3'):
                files.append(os.path.join(dirpath, f))
    # Sort by creation time (oldest first) - though access time might be better for cache?
    # Using modification time as proxy for "downloaded time"
    files.sort(key=os.path.getmtime)

    # 1. Check Song Count
    if max_songs > 0:
        while len(files) > max_songs:
            oldest = files.pop(0)
            try:
                print(f"[SmartDownload] Removing old song: {os.path.basename(oldest)}")
                os.remove(oldest)
            except OSError as e:
                print(f"Error deleting {oldest}: {e}")

    # 2. Check Storage Size (only if songs limit didn't clear enough)
    if max_mb > 0:
        current_mb = check_disk_usage(music_dir)
        while current_mb > max_mb and files:
            oldest = files.pop(0)
            size_mb = os.path.getsize(oldest) / (1024 * 1024)
            try:
                print(f"[SmartDownload] Storage limit exceeded. Removing: {os.path.basename(oldest)}")
                os.remove(oldest)
                current_mb -= size_mb
            except OSError as e:
                print(f"Error deleting {oldest}: {e}")
