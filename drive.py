import argparse
import os
import sys
import mimetypes
import subprocess
import webbrowser
from urllib.parse import urlparse
import requests


def guess_extension(url: str, content_type: str | None) -> str:
    # Try from URL path first
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    if ext and len(ext) <= 5:
        return ext

    # Then from Content-Type
    if content_type:
        ext2 = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext2:
            return ext2

    # Fallbacks
    return ""


def download_file(url: str, out_path: str, chunk_size: int = 1024 * 512) -> None:
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        content_type = r.headers.get("content-type")
        if not os.path.splitext(out_path)[1]:
            ext = guess_extension(url, content_type)
            if ext:
                out_path += ext

        downloaded = 0
        tmp_path = out_path + ".part"

        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = (downloaded / total) * 100
                        print(f"\rDownloading {os.path.basename(out_path)}: {pct:6.2f}% ", end="")
                    else:
                        print(f"\rDownloading {os.path.basename(out_path)}: {downloaded/1024/1024:,.2f} MB ", end="")

        os.replace(tmp_path, out_path)
        print()  # newline

    print(f"Saved: {out_path}")


def ensure_ffmpeg() -> str:
    # Returns ffmpeg executable name/path if available
    exe = "ffmpeg"
    try:
        subprocess.run([exe, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return exe
    except Exception:
        raise RuntimeError(
            "ffmpeg not found in PATH. Install ffmpeg and make sure it's available as `ffmpeg`."
        )


def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> None:
    ffmpeg = ensure_ffmpeg()

    # Merge: copy video stream, encode audio to AAC for wide compatibility
    cmd = [
        ffmpeg, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path
    ]

    print("Merging with ffmpeg...")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        raise RuntimeError("ffmpeg merge failed (see output above).")

    print(f"Done! Output: {output_path}")


def main():
    ap = argparse.ArgumentParser(description="Download separate video+audio URLs and merge into one MP4.")
    ap.add_argument("--video-url", required=True, help="Direct URL to the video file/stream (non-DRM).")
    ap.add_argument("--audio-url", required=True, help="Direct URL to the audio file/stream (non-DRM).")
    ap.add_argument("--out", default="merged_output.mp4", help="Output filename (default: merged_output.mp4)")
    ap.add_argument("--open-browser", action="store_true", help="Open both URLs in your default browser.")
    ap.add_argument("--video-name", default="downloaded_video", help="Base name for downloaded video file.")
    ap.add_argument("--audio-name", default="downloaded_audio", help="Base name for downloaded audio file.")
    args = ap.parse_args()

    if args.open_browser:
        webbrowser.open(args.video_url)
        webbrowser.open(args.audio_url)

    video_base = args.video_name
    audio_base = args.audio_name

    print("Downloading video...")
    download_file(args.video_url, video_base)
    # Find actual saved file (might have extension added)
    video_path = next((f for f in os.listdir(".") if f.startswith(video_base) and not f.endswith(".part")), None)
    if not video_path:
        raise RuntimeError("Video download file not found.")

    print("Downloading audio...")
    download_file(args.audio_url, audio_base)
    audio_path = next((f for f in os.listdir(".") if f.startswith(audio_base) and not f.endswith(".part")), None)
    if not audio_path:
        raise RuntimeError("Audio download file not found.")

    merge_audio_video(video_path, audio_path, args.out)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)