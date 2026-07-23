import sys
import os
import argparse
import downloader
import mixer
import importlib

from pydub import AudioSegment

DOWNLOAD_DIR = "./downloads"
CURATED_PLAYLIST_COUNT = 5


def ascii_progress_bar(iteration, total, prefix='', suffix='', length=40, fill='█'):
    if total <= 0:
        return
    percent = int(100 * iteration / total)
    filled_length = int(length * iteration / total)
    bar = fill * filled_length + '-' * (length - filled_length)
    sys.stdout.write(f"\r{prefix} |{bar}| {percent}% {suffix}")
    sys.stdout.flush()
    if iteration >= total:
        sys.stdout.write("\n")


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
        results = downloader.search_youtube(
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
        path = downloader.download_audio(
            vid["url"],
            DOWNLOAD_DIR,
            preferred_runtime=preferred_runtime,
            remote_components=remote_components,
        )
        if path:
            files.append(path)
        ascii_progress_bar(idx, total, prefix="Downloading", suffix=vid['title'][:40])

    if not files:
        print("No files were downloaded. Aborting.")
        return None

    print("\nCrossfading curated playlist...")
    output = mixer.crossfade_tracks(files, crossfade_ms=3000, output_path="curated_mix.mp3")
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


def interactive_flow(preferred_runtime=None, remote_components=None):
    print("=== Terminal DJ ===")
    print("Build your mix by searching and selecting songs.")
    print("Type 'done' at any search prompt to finish.")
    print("Type 'curate' to generate an AI-style playlist automatically.\n")

    if preferred_runtime:
        print(f"Using JavaScript runtime: {preferred_runtime}\n")
    if remote_components:
        print(f"Remote components enabled: {remote_components}\n")

    playlist = []  # store chosen videos across multiple searches

    while True:
        try:
            query = input("Search YouTube (or type 'done' or 'curate'): ").strip()
        except EOFError:
            print("\nInput closed. Exiting interactive mode.")
            break

        if query.lower() == "done":
            break

        if query.lower() == "curate":
            prompt = input("Describe the playlist you want: ").strip()
            if prompt:
                curated_flow(
                    prompt,
                    preferred_runtime=preferred_runtime,
                    remote_components=remote_components,
                )
            continue

        print(f"\nSearching YouTube for: {query}")
        results = downloader.search_youtube(
            query,
            preferred_runtime=preferred_runtime,
            remote_components=remote_components,
        )

        if not results:
            print("No results found.\n")
            continue

        print("\nSearch Results:")
        for i, r in enumerate(results):
            print(f"{i+1}. {r['title']}")

        selection = input("\nPick songs (e.g. 1 3 5), or press Enter to skip: ").strip()
        if not selection:
            print("Skipping.\n")
            continue

        try:
            indexes = [int(x) - 1 for x in selection.split()]
        except ValueError:
            print("Invalid input. Use numbers like: 1 3 5\n")
            continue

        for i in indexes:
            if 0 <= i < len(results):
                playlist.append(results[i])
                print(f"Added: {results[i]['title']}")
            else:
                print(f"Ignoring invalid index: {i+1}")

        print("\nCurrent playlist:")
        for i, vid in enumerate(playlist):
            print(f"{i+1}. {vid['title']}")
        print()

    if not playlist:
        print("No songs selected. Exiting.")
        return

    print("\nDownloading all selected songs...")
    files = []
    for vid in playlist:
        print(f"Downloading: {vid['title']}")
        downloader_mod = downloader
        if not hasattr(downloader_mod, 'download_audio'):
            try:
                downloader_mod = importlib.reload(downloader_mod)
            except Exception as e:
                print(f"Could not reload downloader module: {e}")

        download_fn = None
        if hasattr(downloader_mod, 'download_audio'):
            download_fn = downloader_mod.download_audio
        else:
            # Fallback: load the source file into a fresh namespace and use its function
            try:
                src_path = getattr(downloader_mod, '__file__', None)
                if src_path:
                    with open(src_path, 'r') as f:
                        src = f.read()
                    ns = {}
                    exec(compile(src, src_path, 'exec'), ns)
                    download_fn = ns.get('download_audio')
            except Exception as e:
                print(f"Fallback load failed: {e}")

        if not download_fn:
            print("downloader.download_audio is missing; aborting download.")
            return

        path = download_fn(
            vid["url"],
            DOWNLOAD_DIR,
            preferred_runtime=preferred_runtime,
            remote_components=remote_components,
        )
        if path:
            files.append(path)

    print("\nCrossfading tracks...")
    output = mixer.crossfade_tracks(
        files,
        crossfade_ms=3000,
        output_path="mix.mp3"  # mixer.py handles folder placement
    )

    print(f"\nDone! Final mix created: {output}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Terminal DJ")
    parser.add_argument("--demo", action="store_true", help="Run demo with generated silent tracks")
    parser.add_argument(
        "--js-runtime",
        choices=["node", "deno", "bun", "quickjs"],
        help="Force a specific JS runtime for yt_dlp JavaScript challenge handling."
    )
    parser.add_argument(
        "--remote-components",
        default=None,
        help="Comma-separated yt_dlp remote components to enable, e.g. ejs:github.",
    )
    parser.add_argument(
        "--curate",
        default=None,
        help="Generate an AI-style curated playlist, e.g. 'funky upbeat songlist'.",
    )
    args = parser.parse_args(argv)

    if args.demo:
        print("Running demo mode: generating sample tracks...")
        files = create_demo_files()
        print("Crossfading demo tracks...")
        output = mixer.crossfade_tracks(files, crossfade_ms=3000, output_path="mix_demo.mp3")
        print(f"Demo complete: {output}")
        return

    if args.curate:
        curated_flow(
            args.curate,
            preferred_runtime=args.js_runtime,
            remote_components=args.remote_components,
        )
    else:
        interactive_flow(preferred_runtime=args.js_runtime, remote_components=args.remote_components)


if __name__ == "__main__":
    main()
