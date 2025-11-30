import warnings
import ymp.downloader as downloader
from ymp.playlistmanager import Playlist
from ymp.player import wait
import ymp.config as config


import threading, argparse, json, sys, os
import subprocess
from urllib import request

from pyfiglet import Figlet
from colorama import init,deinit
from termcolor import colored
from ymp.lock import LockFile
from ymp.tui import YmpTui

musicplaylist = Playlist()
songavailable = threading.Event()

dir_obj=downloader.makedownload()
dir_path = dir_obj.name if hasattr(dir_obj, 'name') else dir_obj


def playspotify(link):
    """Parses a Spotify playlist and adds the songs to the queue."""
    spotifyplaylist=downloader.spotifyparser(link)
    musicplaylist.queuedplaylist.extend(spotifyplaylist)
    songavailable.set()

def playyoutube(link):
    """Fetches info for a YouTube playlist/video and adds it to the queue."""
    if "list=" in link:
        print("Fetching playlist info...")
        playlist_items = downloader.get_playlist_info(link)
        if playlist_items:
            musicplaylist.queuedplaylist.extend(playlist_items)
            print(f"Added {len(playlist_items)} songs to the queue.")
            songavailable.set()
    else:
        # It's a single video, add its URL as a string.
        # The download function will handle fetching the metadata.
        musicplaylist.addsong(link)
        songavailable.set()

def saveplaylist(name):
    """Saves the current playlist to a JSON file."""
    path = config.get_playlist_folder()
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    filepath = os.path.join(path, f'{name}.json')
    playlist_data = musicplaylist.returnplaylist()
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(playlist_data, f, ensure_ascii=False, indent=4)
    print(f"Playlist '{name}' successfully saved to {filepath}")

def loadplaylist(name):
    """Loads a playlist from a JSON file."""
    path = config.get_playlist_folder()
    filepath = os.path.join(path, f'{name}.json')
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            playlist_data = json.load(f)
            musicplaylist.queuedplaylist.extend(playlist_data)
            print(f"Successfully loaded playlist '{name}'")
            songavailable.set()
    except FileNotFoundError:
        print(colored(f"Playlist '{name}' not found at {filepath}", 'red'))
    except json.JSONDecodeError:
        print(colored(f"Error decoding playlist file: {filepath}", 'red'))

import time


def get_local_commit_path():
    """Gets the path to the file storing the local commit hash."""
    return os.path.join(config.CONFIG_DIR, 'version.txt')

def get_local_commit():
    """Reads the locally stored git commit hash."""
    path = get_local_commit_path()
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return f.read().strip()

def save_local_commit(commit_hash):
    """Saves the git commit hash of the current version."""
    path = get_local_commit_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(commit_hash)

def check_for_updates():
    """Checks for updates on GitHub and offers to upgrade."""
    print("Checking for updates...")
    try:
        # Get the latest commit hash from the master branch on GitHub
        url = "https://api.github.com/repos/pheinze/ymp/commits/master"
        with request.urlopen(url, timeout=5) as response:
            data = json.load(response)
            latest_commit = data['sha']
            commit_message = data['commit']['message']
            commit_date = data['commit']['author']['date']

        local_commit = get_local_commit()
        if not local_commit:
             local_commit = "Unknown (First Install or Dev)"

        if latest_commit != local_commit:
            print(colored("A new version is available!", "yellow", attrs=["bold"]))
            print(f"\n{colored('Current Version:', 'cyan')} {local_commit[:7]}")
            print(f"{colored('New Version:    ', 'green')} {latest_commit[:7]}")
            whats_new_header = colored("What's New:", attrs=['bold'])
            print(f"\n{whats_new_header}")
            print(f"{colored(commit_date, 'blue')}: {commit_message}\n")
            
            upgrade = input("Do you want to upgrade? (y/n): ").lower().strip()
            if upgrade == 'y':
                print("Upgrading from GitHub with pipx...")
                try:
                    subprocess.run(
                        ["pipx", "install", "--force", "git+https://github.com/pheinze/ymp.git"],
                        check=True
                    )
                    # After a successful upgrade, save the new commit hash
                    save_local_commit(latest_commit)
                    print(colored("Update successful! Please restart ymp if it was already running.", "green"))
                    sys.exit()
                except subprocess.CalledProcessError as e:
                    print(colored(f"Update failed: {e}", "red"))
                except FileNotFoundError:
                    print(colored("`pipx` command not found. Please upgrade manually.", "red"))
            else:
                print("Update skipped.")
        else:
            print(colored("You are using the latest version.", "green"))

    except Exception as e:
        print(colored(f"Could not check for updates: {e}", "red"))

def main():
    init()

    # Ensure single instance
    lock = LockFile(os.path.join(config.CONFIG_DIR, 'ymp.lock'))
    if not lock.acquire():
        print(colored("Error: YMP is already running.", "red"))
        sys.exit(1)

    f = Figlet(font='banner3-D')
    print(" ")
    print(colored(f.renderText('YMP'),'cyan'))
    print("\t\t\t\t\t\t- by pheinze")

    from . import __version__
    epilog_text = (
        'Thank you for using YMP! :)\n\n'
        'Support Development (Bitcoin): bc1qgrm2kvs27rfkpwtgp5u7w0rlzkgwrxqtls2q4f'
    )
    parser = argparse.ArgumentParser(
        prog='ymp', 
        description='Your Music Player', 
        epilog=epilog_text,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument("-s", action='store', metavar='link', help="Play a Spotify Playlist")
    parser.add_argument("-y", action='store', metavar='link', help="Play a Youtube Playlist")
    parser.add_argument("-p", action='store', nargs='+', metavar='song', help="Play multiple youtube links or a songs")
    parser.add_argument("-l", action='store', metavar='playlistname', help="Play a ymp generated playlist")
    parser.add_argument('-u', '--update', action='store_true', help="Check for updates")
    parser.add_argument('--donate', action='store_true', help="Show donation information")
    parser.add_argument('--config', action='store_true', help="Configure YMP settings interactively")
    parser.add_argument('--manual', action='store_true', help="Show the detailed user manual")
    
    # Allow URL/Query without -p flag
    parser.add_argument('query', nargs='?', help="Directly play a URL or search query")

    args = parser.parse_args()

    if args.manual:
        # Show manual (assuming MANUAL.md is in the package or we print a large text)
        from rich.console import Console
        from rich.markdown import Markdown
        console = Console()
        manual_text = """# YMP User Manual

## Overview
YMP (Your Music Player) is a versatile command-line music player.

## Smart Downloads
YMP can cache songs locally to save bandwidth and speed up playback.
Files are stored in `~/Music/ymp` (configurable).

- **Max Songs:** Limits the number of cached files. Oldest are deleted first.
- **Max Storage:** Limits the cache size in MB.
- **Preloading:** Automatically downloads the next song while the current one plays.

## Configuration
Run `ymp --config` to change settings.

## Keyboard Controls
- `play`/`pause`: Control playback
- `next`/`back`: Navigation
- `seek [sec]`: Jump forward/backward

## PLS Support
You can play internet radio playlists (.pls) by passing the URL or file path.
        """
        console.print(Markdown(manual_text))
        sys.exit()

    if args.config:
        print(colored("--- YMP Configuration Wizard ---", "cyan"))
        current = config.get_config()
        
        print(f"1. Music Directory [{config.get_music_dir()}]")
        print(f"2. Enable Smart Download [{config.is_smart_download_enabled()}]")
        print(f"3. Max Songs in Cache [{config.get_max_songs()}]")
        print(f"4. Max Storage (MB) [{config.get_max_storage_mb()}]")
        
        choice = input("Enter number to edit (or 'q' to quit): ").strip()
        
        if choice == '1':
            val = input("Enter new path: ").strip()
            config.update_setting('General', 'music_dir', val)
        elif choice == '2':
            val = input("Enable? (True/False): ").strip()
            config.update_setting('SmartDownload', 'enabled', val)
        elif choice == '3':
            val = input("Enter max songs (0=unlimited): ").strip()
            config.update_setting('SmartDownload', 'max_songs', val)
        elif choice == '4':
            val = input("Enter max MB (0=unlimited): ").strip()
            config.update_setting('SmartDownload', 'max_storage_mb', val)
            
        print("Settings saved.")
        sys.exit()

    if args.donate:
        print(colored("Support YMP development!", "yellow"))
        print(colored("Bitcoin Address: bc1qgrm2kvs27rfkpwtgp5u7w0rlzkgwrxqtls2q4f", "green"))
        sys.exit()

    if args.update:
        check_for_updates()
        sys.exit()

    # Handle 'query' positional argument as if it were -p
    if args.query and not (args.s or args.y or args.l or args.p):
        args.p = [args.query]

    # Pre-populate playlist if args exist
    initial_queue = []
    if args.s:
        # Spotify parsing logic needs to run here or be passed
        # Re-using playspotify logic but without threading events yet
        print("Parsing Spotify...")
        initial_queue.extend(downloader.spotifyparser(args.s))
    if args.y:
         if "list=" in args.y:
             print("Fetching playlist info...")
             items = downloader.get_playlist_info(args.y)
             if items: initial_queue.extend(items)
         else:
             initial_queue.append(args.y)
    if args.p:
        for songs in args.p:
            if songs.endswith('.pls'):
                 urls = downloader.parse_pls(songs)
                 initial_queue.extend(urls)
            elif "list=" in songs and ("http://" in songs or "https://" in songs):
                print("Fetching playlist info...")
                items = downloader.get_playlist_info(songs)
                if items:
                    initial_queue.extend(items)
                else:
                    initial_queue.append(songs)
            else:
                initial_queue.append(songs)

    if args.l:
        # Load playlist logic
        path = config.get_playlist_folder()
        filepath = os.path.join(path, f'{args.l}.json')
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)
                initial_queue.extend(playlist_data)
        except Exception as e:
            print(f"Error loading playlist: {e}")

    # Launch TUI
    import signal
    def signal_handler(sig, frame):
        try:
            deinit()
            musicplaylist.stop_all()
            downloader.removedownload(dir_obj)
            lock.release()
        except:
            pass
        os._exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    app = YmpTui(playlist_manager=musicplaylist, download_dir=dir_obj, initial_queue=initial_queue)
    try:
        app.run()
    finally:
        deinit()
        musicplaylist.stop_all()
        downloader.removedownload(dir_obj)
        lock.release()
        os._exit(0)

if __name__ == "__main__":
    main()
