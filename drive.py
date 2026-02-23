import requests
from tqdm import tqdm
import subprocess
import os
from pathlib import Path

def clean_url(url: str) -> str:
    if "&range=" in url:
        url = url.split("&range=")[0]
    url = url.replace("\\u0026", "&").replace("%26", "&")
    return url.strip('" \'')

def download_stream(url: str, filename: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Referer": "https://drive.google.com/",
        "Origin": "https://drive.google.com",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",
        "Range": "bytes=0-",           # ← THIS FIXES THE 403
        "sec-fetch-site": "cross-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "video"
    }
    print(f"📥 Downloading {filename} (with Range fix)...")
    
    with requests.get(url, stream=True, headers=headers) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(filename, "wb") as f, tqdm(
            desc=filename, total=total, unit="iB", unit_scale=True, unit_divisor=1024
        ) as bar:
            for chunk in r.iter_content(chunk_size=8192 * 4):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))

def merge(video: str, audio: str, output: str):
    print("🔄 Merging video + audio...")
    cmd = ["ffmpeg", "-y", "-i", video, "-i", audio, "-c", "copy", output]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"✅ MERGED → {output}")
    except FileNotFoundError:
        print("❌ ffmpeg missing! Install it.")
    except Exception as e:
        print(f"❌ Merge failed: {e}")

print("🚀 FIXED PRIVATE VIEW-ONLY DOWNLOADER (403-proof) 🚀\n")

video_url = input("Paste fresh VIDEO URL (mime=video): ").strip()
audio_url = input("Paste fresh AUDIO URL (mime=audio): ").strip()

video_url = clean_url(video_url)
audio_url = clean_url(audio_url)

save_name = input("\nSave as (e.g. my_private_video.mp4): ").strip() or "gdrive_video.mp4"
if not save_name.lower().endswith(".mp4"):
    save_name += ".mp4"

temp_v = "temp_video.mp4"
temp_a = "temp_audio.m4a"

try:
    download_stream(video_url, temp_v)
    download_stream(audio_url, temp_a)
    merge(temp_v, temp_a, save_name)
    
    os.remove(temp_v)
    os.remove(temp_a)
    print(f"\n🎉 DONE BRO! Saved → {save_name}")
    print("   Open it and chill 💪")
except requests.exceptions.HTTPError as err:
    print(f"\n❌ Still 403? → Get the URLs EVEN FASTER next time (copy → paste → run in <10 seconds)")
except Exception as e:
    print(f"\nError: {e}")