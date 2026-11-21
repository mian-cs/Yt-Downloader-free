# ⚡ YT Downloader

A high-speed desktop application designed to download YouTube playlists and individual videos/audio tracks with multi-format conversion and a Cyberpunk HUD interface.

**Developer:** **Mian Moazzam**  
**Portfolio & Socials:**  
- 🌐 **Website:** [mianmoazzam.me](https://mianmoazzam.me)  
- ⚡ **GitHub:** [@mian-cs](https://github.com/mian-cs)  
- 💼 **LinkedIn:** [in/mian-cs](https://www.linkedin.com/in/mian-cs)  
- 📷 **Instagram:** [@mian.cs_](https://www.instagram.com/mian.cs_)  

**Copyright:** **© 2026 Mian Moazzam. All Rights Reserved.**

---

## 🌟 Key Features

- **Futuristic Interface**: Sleek Cyberpunk HUD terminal interface with 3D matrix particles powered by Three.js.
- **🌓 Light & Dark Mode**: Instant one-click theme switcher directly in the interface with persistent state.
- **Prominent Developer Branding**: "Developed by Mian Moazzam • All Rights Reserved" visible directly on the user interface.
- **Playlist & Single Video Harvesting**: Supports entire YouTube playlists or single video downloads.
- **Multiple Payload Formats**:
  - **MP4 Video**: 1080p Full HD, 720p HD, 480p, 360p, or Best Available.
  - **MP3 Audio**: Ultra Studio Quality (320 kbps) & High Quality (192 kbps).
- **Zero-Freeze Stop**: Instant Stop button that cleanly terminates active background downloads without freezing the UI.
- **Real-Time Telemetry**: Live progress percentage, transfer speed (MB/s), ETA countdown, and downloaded size counters.
- **Native OS Dialogs**: Windows native folder selection and clipboard paste integration.

---

## 🛠️ Prerequisites

1. **Python 3.10+**
2. **FFmpeg**: Required for audio extraction (MP3) and video/audio stream merging.

---

## 🚀 Installation & Usage

### 1. Clone the Repository
```bash
git clone https://github.com/mian-cs/YT-Downloader-free.git
cd YT-Downloader-free
```

### 2. Install Required Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup FFmpeg
The application looks for FFmpeg binaries inside an `ffmpeg/` folder in the project root:
1. Download FFmpeg builds from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or [ffmpeg.org](https://ffmpeg.org/download.html).
2. Place `ffmpeg.exe` and `ffprobe.exe` inside the `ffmpeg/` directory:
```
YT-Downloader/
├── ffmpeg/
│   ├── ffmpeg.exe
│   └── ffprobe.exe
├── index.html
├── style.css
├── main.py
└── ...
```

### 4. Run the Application
```bash
python main.py
```

---

## 📦 Building Standalone Windows Executable (.exe)

To build a single executable file:

```bash
pip install pyinstaller
pyinstaller "Playlist Downloader.spec"
```

The compiled standalone executable will be generated inside the `dist/` directory.

---

## ⚖️ License & Rights
© 2026 **Mian Moazzam**. All Rights Reserved.  
Distributed under the MIT License. See [LICENSE](LICENSE) for details.
