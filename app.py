from __future__ import annotations

import queue
import threading
from pathlib import Path
from urllib.parse import urlparse

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import yt_dlp


YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}


class YoutubeDownloaderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("680x390")
        self.root.minsize(600, 360)

        self.url_var = tk.StringVar()
        self.destination_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.format_var = tk.StringVar(value="video")
        self.status_var = tk.StringVar(value="YouTubeのURLを入力してください。")
        self.progress_var = tk.DoubleVar(value=0)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.is_downloading = False

        self._build_ui()
        self.root.after(100, self._process_events)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=24)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(1, weight=1)

        title = ttk.Label(
            container, text="YouTube Downloader", font=("", 18, "bold")
        )
        title.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 22))

        ttk.Label(container, text="YouTube URL").grid(
            row=1, column=0, sticky=tk.W, padx=(0, 12), pady=8
        )
        self.url_entry = ttk.Entry(container, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=1, columnspan=2, sticky=tk.EW, pady=8)

        ttk.Label(container, text="保存先").grid(
            row=2, column=0, sticky=tk.W, padx=(0, 12), pady=8
        )
        self.destination_entry = ttk.Entry(
            container, textvariable=self.destination_var
        )
        self.destination_entry.grid(row=2, column=1, sticky=tk.EW, pady=8)
        self.browse_button = ttk.Button(
            container, text="参照...", command=self._choose_destination
        )
        self.browse_button.grid(row=2, column=2, padx=(10, 0), pady=8)

        ttk.Label(container, text="保存形式").grid(
            row=3, column=0, sticky=tk.W, padx=(0, 12), pady=8
        )
        format_frame = ttk.Frame(container)
        format_frame.grid(row=3, column=1, columnspan=2, sticky=tk.W, pady=8)
        self.video_radio = ttk.Radiobutton(
            format_frame,
            text="動画（MP4）",
            variable=self.format_var,
            value="video",
        )
        self.video_radio.pack(side=tk.LEFT, padx=(0, 20))
        self.audio_radio = ttk.Radiobutton(
            format_frame,
            text="音声のみ（MP3）",
            variable=self.format_var,
            value="audio",
        )
        self.audio_radio.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(
            container,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        )
        self.progress.grid(
            row=4, column=0, columnspan=3, sticky=tk.EW, pady=(22, 8)
        )

        status_label = ttk.Label(
            container, textvariable=self.status_var, wraplength=620
        )
        status_label.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(0, 18))

        self.download_button = ttk.Button(
            container, text="ダウンロード開始", command=self._start_download
        )
        self.download_button.grid(row=6, column=0, columnspan=3, ipadx=24, ipady=5)

        self.url_entry.focus_set()
        self.root.bind("<Return>", lambda _event: self._start_download())

    def _choose_destination(self) -> None:
        selected = filedialog.askdirectory(
            title="保存先フォルダーを選択",
            initialdir=self.destination_var.get() or str(Path.home()),
        )
        if selected:
            self.destination_var.set(selected)

    @staticmethod
    def _is_youtube_url(value: str) -> bool:
        try:
            parsed = urlparse(value)
        except ValueError:
            return False
        return parsed.scheme in {"http", "https"} and parsed.hostname in YOUTUBE_HOSTS

    def _start_download(self) -> None:
        if self.is_downloading:
            return

        url = self.url_var.get().strip()
        destination_text = self.destination_var.get().strip()

        if not self._is_youtube_url(url):
            messagebox.showerror(
                "入力エラー", "有効なYouTubeのURLを入力してください。"
            )
            self.url_entry.focus_set()
            return
        if not destination_text:
            messagebox.showerror("入力エラー", "保存先フォルダーを指定してください。")
            return

        destination = Path(destination_text).expanduser()
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(
                "保存先エラー", f"保存先フォルダーを使用できません。\n{exc}"
            )
            return

        if not destination.is_dir():
            messagebox.showerror(
                "保存先エラー", "指定された保存先はフォルダーではありません。"
            )
            return

        self.is_downloading = True
        self.progress_var.set(0)
        self.status_var.set("ダウンロードを準備しています...")
        self._set_controls_enabled(False)

        worker = threading.Thread(
            target=self._download,
            args=(url, destination, self.format_var.get()),
            daemon=True,
        )
        worker.start()

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        self.url_entry.configure(state=state)
        self.destination_entry.configure(state=state)
        self.browse_button.configure(state=state)
        self.video_radio.configure(state=state)
        self.audio_radio.configure(state=state)
        self.download_button.configure(state=state)

    def _progress_hook(self, data: dict[str, object]) -> None:
        status = data.get("status")
        if status == "downloading":
            downloaded = data.get("downloaded_bytes")
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            if isinstance(downloaded, (int, float)) and isinstance(
                total, (int, float)
            ):
                percent = min(downloaded / total * 100, 100)
                self.events.put(("progress", percent))

            speed = data.get("_speed_str", "")
            eta = data.get("_eta_str", "")
            detail = "ダウンロード中"
            if speed:
                detail += f"  速度: {str(speed).strip()}"
            if eta:
                detail += f"  残り: {str(eta).strip()}"
            self.events.put(("status", detail))
        elif status == "finished":
            self.events.put(("progress", 100.0))
            self.events.put(("status", "変換・仕上げ処理を行っています..."))

    def _download(self, url: str, destination: Path, media_format: str) -> None:
        output_template = str(destination / "%(title)s [%(id)s].%(ext)s")
        options: dict[str, object] = {
            "outtmpl": output_template,
            "noplaylist": True,
            "windowsfilenames": True,
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

        if media_format == "audio":
            options.update(
                {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ],
                }
            )
        else:
            options.update(
                {
                    "format": (
                        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                        "best[ext=mp4]/bestvideo+bestaudio/best"
                    ),
                    "merge_output_format": "mp4",
                }
            )

        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                downloader.download([url])
        except Exception as exc:
            self.events.put(("error", str(exc)))
        else:
            self.events.put(("complete", str(destination)))

    def _process_events(self) -> None:
        try:
            while True:
                event, value = self.events.get_nowait()
                if event == "progress":
                    self.progress_var.set(float(value))
                elif event == "status":
                    self.status_var.set(str(value))
                elif event == "error":
                    self._finish_download()
                    self.status_var.set("ダウンロードに失敗しました。")
                    messagebox.showerror(
                        "ダウンロードエラー",
                        f"動画を保存できませんでした。\n\n{value}",
                    )
                elif event == "complete":
                    self.progress_var.set(100)
                    self._finish_download()
                    self.status_var.set("ダウンロードが完了しました。")
                    messagebox.showinfo(
                        "完了", f"ダウンロードが完了しました。\n保存先: {value}"
                    )
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_events)

    def _finish_download(self) -> None:
        self.is_downloading = False
        self._set_controls_enabled(True)


def main() -> None:
    root = tk.Tk()
    YoutubeDownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
