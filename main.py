import webview
import os
import sys
import threading
import time
import json
import subprocess
import webbrowser
import yt_dlp
import yt_dlp.utils

# =========================================================
# APPLICATION STATE
# =========================================================
stop_requested = False
downloading = False
window = None
last_update_time = 0
current_index = 1
current_total = 1

# =========================================================
# FIND APPLICATION DIRECTORY
# =========================================================
def application_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_ffmpeg_path():
    return os.path.join(application_path(), "ffmpeg")

# =========================================================
# FORMAT SELECTION (MP3 & MP4)
# =========================================================
def get_format(quality):
    # Audio Only (MP3)
    if "MP3" in quality or "Audio" in quality:
        return "bestaudio/best"
    # Video Qualities
    if "1080p" in quality:
        return "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    if "720p" in quality:
        return "bestvideo[height<=720]+bestaudio/best[height<=720]"
    if "480p" in quality:
        return "bestvideo[height<=480]+bestaudio/best[height<=480]"
    if "360p" in quality:
        return "bestvideo[height<=360]+bestaudio/best[height<=360]"
    # Default to Best Available Video + Audio
    return "bestvideo*+bestaudio/best"

def format_bytes(size):
    if not size: return "0 MB"
    mb = size / (1024 * 1024)
    if mb < 1024: return f"{mb:.1f} MB"
    return f"{mb / 1024:.2f} GB"

def format_speed(speed):
    if not speed: return "--"
    return f"{speed / (1024 * 1024):.2f} MB/s"

# =========================================================
# PROGRESS HOOKS (Throttled & Instant Abort)
# =========================================================
def progress_hook(data):
    global stop_requested, last_update_time, current_index, current_total
    if stop_requested:
        raise yt_dlp.utils.DownloadCancelled("DOWNLOAD_STOPPED_BY_USER")

    status = data.get("status")
    if status == "downloading":
        now = time.time()
        downloaded = data.get("downloaded_bytes", 0)
        total = data.get("total_bytes") or data.get("total_bytes_estimate")

        if stop_requested:
            raise yt_dlp.utils.DownloadCancelled("DOWNLOAD_STOPPED_BY_USER")

        # Throttle IPC calls to ~5 times per second (every 0.20s) for fluid UI without IPC flood
        is_finished = total and downloaded >= total
        if not is_finished and (now - last_update_time) < 0.20:
            return
        last_update_time = now

        speed = data.get("speed")
        eta = data.get("eta")
        filename = data.get("filename", "")

        name = os.path.basename(filename) if filename else "Target Stream"
        # Clean temporary internal format tags (.f137.mp4, .f140.m4a, .part) from title display
        for ext in [".f137.mp4", ".f140.m4a", ".f251.webm", ".f248.webm", ".part", ".temp"]:
            if name.endswith(ext):
                name = name[:-len(ext)]
                break

        video_text = f"[{current_index}/{current_total}] {name}" if current_total > 1 else name
        percentage = (downloaded / total * 100) if total else 0
        eta_text = f"{eta//60:02d}:{eta%60:02d}" if eta is not None else "--:--"
        size_text = f"{format_bytes(downloaded)} / {format_bytes(total)}" if total else format_bytes(downloaded)

        if window:
            safe_text = json.dumps(video_text)
            safe_speed = json.dumps(format_speed(speed))
            safe_eta = json.dumps(eta_text)
            safe_size = json.dumps(size_text)
            window.evaluate_js(f"updateProgress({percentage:.1f}, {safe_text}, {safe_speed}, {safe_eta}, {safe_size});")

    elif status == "finished":
        if window:
            window.evaluate_js('updateProgress(100.0, null, "-- MB/s", "00:00", null);')

def postprocessor_hook(data):
    global stop_requested
    if stop_requested:
        raise yt_dlp.utils.DownloadCancelled("DOWNLOAD_STOPPED_BY_USER")
    status = data.get("status")
    if status == "started":
        if window:
            window.evaluate_js('updateStatusText("CONVERTING / MERGING (FFMPEG)...");')

# =========================================================
# UI EXPOSED FUNCTIONS (Called by HTML/JS)
# =========================================================
class Api:
    def open_external_url(self, url):
        """Safely opens an external link in the user's default browser."""
        try:
            if url and (url.startswith("http://") or url.startswith("https://")):
                webbrowser.open(url)
        except Exception:
            pass

    def get_default_folder(self):
        """Returns standard user Downloads folder path."""
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.isdir(downloads):
            return downloads
        return os.path.expanduser("~")

    def kill_child_ffmpeg(self):
        """Instantly terminates any active ffmpeg process without freezing the app."""
        try:
            CREATE_NO_WINDOW = 0x08000000
            subprocess.run(
                ["taskkill", "/F", "/IM", "ffmpeg.exe", "/T"], 
                capture_output=True, 
                creationflags=CREATE_NO_WINDOW
            )
        except Exception:
            pass

    def fetch_playlist_info(self, url):
        """Fetches metadata in background thread without freezing UI."""
        if not url or not url.startswith("http"):
            if window:
                window.evaluate_js('showPlaylistError("Invalid target URL protocol.")')
            return

        if window:
            window.evaluate_js('showPlaylistLoading()')
        
        threading.Thread(target=self._fetch_info_thread, args=(url,), daemon=True).start()

    def _fetch_info_thread(self, url):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'ignoreerrors': True,
                'ffmpeg_location': get_ffmpeg_path(),
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    if window:
                        window.evaluate_js(f"showPlaylistError({json.dumps('Target metadata unreachable.')});")
                    return

                if 'entries' in info and info.get('entries'):
                    title = info.get('title') or 'Target Playlist'
                    videos = [entry for entry in info['entries'] if entry is not None]
                    count = len(videos)
                    if window:
                        window.evaluate_js(f"showPlaylistInfo({json.dumps(title)}, {count});")
                else:
                    title = info.get('title') or 'Single Target Media'
                    if window:
                        window.evaluate_js(f"showPlaylistInfo({json.dumps(title)}, 1, true);")
                        
        except Exception as e:
            if window:
                window.evaluate_js(f"showPlaylistError({json.dumps(str(e))});")

    def select_folder(self):
        """Native folder dialog without Tkinter freezing/deadlock."""
        try:
            if window:
                result = window.create_file_dialog(webview.FOLDER_DIALOG)
                if result and len(result) > 0:
                    return result[0]
                return ""
        except Exception:
            pass

        # Fallback to Tkinter if needed
        try:
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder = filedialog.askdirectory()
            root.destroy()
            return folder or ""
        except Exception:
            return ""

    def paste_url(self):
        """Native Windows clipboard retrieval with zero window flicker."""
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            CF_UNICODETEXT = 13
            if user32.OpenClipboard(None):
                try:
                    handle = user32.GetClipboardData(CF_UNICODETEXT)
                    if handle:
                        kernel32.GlobalLock.restype = wintypes.LPCWSTR
                        text_ptr = kernel32.GlobalLock(handle)
                        text = str(text_ptr) if text_ptr else ""
                        kernel32.GlobalUnlock(handle)
                        return text
                finally:
                    user32.CloseClipboard()
        except Exception:
            pass

        # Fallback to Tkinter
        try:
            from tkinter import Tk
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            url = root.clipboard_get()
            root.destroy()
            return url or ""
        except Exception:
            return ""

    def start_download(self, url, folder, quality):
        global downloading, stop_requested
        if downloading: return

        if not url or not folder:
            if window:
                window.evaluate_js('showError("Target URL and destination path required.")')
            return

        stop_requested = False
        downloading = True
        
        if window:
            window.evaluate_js('setDownloadingState(true)')
        threading.Thread(target=self._download_thread, args=(url, folder, quality), daemon=True).start()

    def stop_download(self):
        """Instant Stop: kills subprocesses and updates UI in 0 milliseconds."""
        global stop_requested, downloading
        if downloading:
            stop_requested = True
            downloading = False
            self.kill_child_ffmpeg()
            if window:
                window.evaluate_js('downloadStopped()')

    def _download_thread(self, url, folder, quality):
        """Downloads videos one-by-one sequentially to 100% completion before moving to the next."""
        global downloading, stop_requested, current_index, current_total
        try:
            is_mp3 = "MP3" in quality or "Audio" in quality
            
            # Base options for downloading an individual media stream at high speed
            base_opts = {
                "format": get_format(quality),
                "noplaylist": True,  # Process individual video strictly
                "continuedl": True,
                "nooverwrites": True,
                "progress_hooks": [progress_hook],
                "postprocessor_hooks": [postprocessor_hook],
                "ffmpeg_location": get_ffmpeg_path(),
                "retries": 10,
                "quiet": True,
                "ignoreerrors": False,
                # High speed fragment downloads & optimized buffer
                "concurrent_fragment_downloads": 8,
                "buffersize": 1024 * 1024,
                "http_chunk_size": 10485760,
            }

            if is_mp3:
                bitrate = "320" if "320" in quality else "192"
                base_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate,
                }]
            else:
                base_opts["merge_output_format"] = "mp4"

            # Step 1: Fast metadata extraction to inspect playlist / video entries
            if window:
                window.evaluate_js('updateStatusText("ANALYZING TARGET STREAMS...");')

            extract_opts = {
                'extract_flat': True,
                'quiet': True,
                'skip_download': True,
                'ignoreerrors': True,
                'ffmpeg_location': get_ffmpeg_path(),
            }

            with yt_dlp.YoutubeDL(extract_opts) as ydl_extractor:
                info = ydl_extractor.extract_info(url, download=False)

            if not info:
                downloading = False
                if window:
                    window.evaluate_js('showError("Failed to extract target stream information.");')
                return

            if stop_requested:
                downloading = False
                if window:
                    window.evaluate_js('downloadStopped()')
                return

            # Extract list of items
            entries = []
            if 'entries' in info and info.get('entries'):
                entries = [e for e in info['entries'] if e]
                is_playlist = True
            else:
                entries = [info]
                is_playlist = False

            current_total = len(entries)

            # Step 2: Download each item strictly ONE-BY-ONE
            for idx, entry in enumerate(entries, 1):
                if stop_requested:
                    break

                current_index = idx

                # Determine video stream URL
                v_url = entry.get('url', '')
                v_id = entry.get('id', '')
                if v_url and v_url.startswith('http'):
                    target_url = v_url
                elif v_id:
                    target_url = f"https://www.youtube.com/watch?v={v_id}"
                else:
                    target_url = url

                target_title = entry.get('title') or f"Target_{idx}"

                # Update UI for current video
                if window:
                    status_msg = f"HARVESTING [{idx}/{current_total}]..." if is_playlist else "HARVESTING MEDIA..."
                    window.evaluate_js(f'updateStatusText({json.dumps(status_msg)});')
                    window.evaluate_js(f'setCurrentVideo({json.dumps(f"[{idx}/{current_total}] {target_title}")});')
                    window.evaluate_js('updateProgress(0.0, null, "-- MB/s", "--:--", "0 MB");')

                # Configure template for this specific video
                video_opts = dict(base_opts)
                if is_playlist:
                    video_opts["outtmpl"] = os.path.join(folder, f"{idx:03d} - %(title)s.%(ext)s")
                else:
                    video_opts["outtmpl"] = os.path.join(folder, "%(title)s.%(ext)s")

                # Execute complete download and postprocessing for THIS video
                try:
                    with yt_dlp.YoutubeDL(video_opts) as ydl_video:
                        ydl_video.download([target_url])
                except Exception as e:
                    if stop_requested or "DOWNLOAD_STOPPED" in str(e) or "DownloadCancelled" in str(e):
                        break
                    else:
                        continue

                # Finished current video
                if stop_requested:
                    break

                if window and is_playlist and idx < current_total:
                    window.evaluate_js(f'updateStatusText({json.dumps(f"VERIFIED [{idx}/{current_total}] // PREPARING NEXT...")});')
                    time.sleep(0.3)

            downloading = False
            if stop_requested:
                if window:
                    window.evaluate_js('downloadStopped()')
            else:
                if window:
                    window.evaluate_js('downloadFinished()')

        except Exception as e:
            downloading = False
            if stop_requested or "DOWNLOAD_STOPPED" in str(e):
                if window:
                    window.evaluate_js('downloadStopped()')
            else:
                if window:
                    window.evaluate_js(f'showError({json.dumps(str(e))})')

# =========================================================
# MAIN RUN
# =========================================================
if __name__ == '__main__':
    api = Api()
    html_file = os.path.join(application_path(), 'index.html')
    window = webview.create_window(
        'YT Downloader - by Mian Moazzam', 
        html_file, 
        js_api=api, 
        width=960, 
        height=740,
        resizable=True
    )
    webview.start()
