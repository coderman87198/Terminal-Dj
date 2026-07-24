import os
from pathlib import Path
from pydub import AudioSegment

from .downloader import download_audio, search_youtube
from .mixer import crossfade_tracks

REPO_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = str(REPO_ROOT / "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
CURATED_PLAYLIST_COUNT = 5


def ascii_progress_bar(iteration, total, prefix='', suffix='', length=40, fill='█'):
    if total <= 0:
        return
    percent = int(100 * iteration / total)
    filled_length = int(length * iteration / total)
    bar = fill * filled_length + '-' * (length - filled_length)
    os.sys.stdout.write(f"\r{prefix} |{bar}| {percent}% {suffix}")
    os.sys.stdout.flush()
    if iteration >= total:
        os.sys.stdout.write("\n")


def build_curated_playlist(prompt, count=CURATED_PLAYLIST_COUNT, preferred_runtime=None, remote_components=None):
    search_variants = [
        prompt,
        f"{prompt} songs",
        f"{prompt} playlist",
        f"{prompt} music",
    ]

    playlist = []
    seen_urls = set()

    print(f"Curating playlist for: {prompt}")
    for idx, query in enumerate(search_variants, start=1):
        ascii_progress_bar(idx - 1, len(search_variants), prefix="Searching", suffix=query)
        results = search_youtube(
            query,
            preferred_runtime=preferred_runtime,
            remote_components=remote_components,
        )

        for r in results:
            if len(playlist) >= count:
                break
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                playlist.append(r)

        ascii_progress_bar(idx, len(search_variants), prefix="Searching", suffix=query)
        if len(playlist) >= count:
            break

    if not playlist:
        print("No songs could be curated from the prompt. Please try a different description.")
    else:
        print(f"\nCurated playlist ({len(playlist)} songs):")
        for i, vid in enumerate(playlist, start=1):
            print(f"{i}. {vid['title']}")

    return playlist


def curated_flow(prompt, preferred_runtime=None, remote_components=None):
    playlist = build_curated_playlist(
        prompt,
        preferred_runtime=preferred_runtime,
        remote_components=remote_components,
    )
    if not playlist:
        return

    print("\nDownloading curated playlist...")
    files = []
    total = len(playlist)
    for idx, vid in enumerate(playlist, start=1):
        ascii_progress_bar(idx - 1, total, prefix="Downloading", suffix=vid['title'][:40])
        print(f"\nDownloading: {vid['title']}")
        path, error = download_audio(
            vid["url"],
            DOWNLOAD_DIR,
            preferred_runtime=preferred_runtime,
            remote_components=remote_components,
        )
        if path:
            files.append(path)
        else:
            print(f"Download failed for {vid['url']}: {error}")
        ascii_progress_bar(idx, total, prefix="Downloading", suffix=vid['title'][:40])

    if not files:
        print("No files were downloaded. Aborting.")
        return None

    print("\nCrossfading curated playlist...")
    output = crossfade_tracks(files, crossfade_ms=3000, output_path="curated_mix.mp3")
    print(f"\nDone! Curated mix created: {output}")
    return output


def create_demo_files(n=3, duration_ms=3000):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    files = []
    for i in range(n):
        path = os.path.join(DOWNLOAD_DIR, f"demo_{i+1}.mp3")
        silent = AudioSegment.silent(duration=duration_ms)
        silent.export(path, format="mp3")
        files.append(path)
    return files
