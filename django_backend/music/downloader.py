import yt_dlp
import os
import re
import shutil


def safe_title(title):
    return re.sub(r'[\\/*?:"<>|]', "_", title)


def find_js_runtime(preferred_runtime=None):
    runtime_execs = {
        "node": "node",
        "deno": "deno",
        "bun": "bun",
        "quickjs": "qjs",
    }

    preference = []
    if preferred_runtime:
        preferred_runtime = preferred_runtime.lower()
        if preferred_runtime in runtime_execs:
            preference.append(preferred_runtime)

    preference.extend(r for r in runtime_execs if r not in preference)

    for runtime in preference:
        if shutil.which(runtime_execs[runtime]):
            return runtime

    return None


def get_yt_dlp_js_opts(preferred_runtime=None, remote_components=None):
    preferred_runtime = os.environ.get("YT_DLP_JS_RUNTIME", preferred_runtime)
    remote_components = os.environ.get("YT_DLP_REMOTE_COMPONENTS", remote_components)

    js_runtime = find_js_runtime(preferred_runtime)
    if js_runtime is None:
        print(
            "[Warning] No supported JavaScript runtime found; JS challenge pages may fail. "
            "Install node, deno, bun, or qjs to enable JavaScript challenge support."
        )
        return {}

    if remote_components is None:
        remote_components = "ejs:github"

    opts = {"js_runtimes": {js_runtime: {}}}
    if remote_components:
        if isinstance(remote_components, str):
            remote_components = [c.strip() for c in remote_components.split(",") if c.strip()]
        if remote_components:
            opts["remote_components"] = remote_components

    print(f"[Info] Using JavaScript runtime '{js_runtime}' for yt_dlp.")
    if opts.get("remote_components"):
        print(f"[Info] Enabling remote components: {opts['remote_components']}")

    return opts


def search_youtube(query, max_results=20, preferred_runtime=None, remote_components=None):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        **get_yt_dlp_js_opts(preferred_runtime=preferred_runtime, remote_components=remote_components),
    }

    # Primary attempt using yt_dlp
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            entries = info.get("entries", [])
            results = []

            for e in entries:
                if not e:
                    continue
                title = e.get("title")
                url = e.get("webpage_url")
                if title and url:
                    thumbnails = e.get("thumbnails") or []
                    thumbnail = None
                    if isinstance(thumbnails, list):
                        for item in thumbnails:
                            if isinstance(item, dict):
                                thumb_url = item.get("url")
                                if thumb_url:
                                    thumbnail = thumb_url
                                    break
                    elif isinstance(thumbnails, dict):
                        thumbnail = thumbnails.get("url")

                    if not thumbnail:
                        thumbnail = e.get("thumbnail")

                    results.append({"title": title, "url": url, "thumbnail": thumbnail})

            if results:
                return results
    except Exception as e:
        print(f"\n[Search Error] yt_dlp failed: {e}")

    # Fallback: lightweight HTML scrape + oEmbed lookup (works when yt_dlp cannot run on host)
    try:
        import requests
        from urllib.parse import quote_plus

        search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        resp = requests.get(search_url, timeout=10)
        if resp.status_code != 200:
            return []

        html = resp.text
        # Find unique video ids in page HTML
        import re
        ids = re.findall(r"/watch\?v=([A-Za-z0-9_-]{11})", html)
        seen = []
        for vid in ids:
            if vid not in seen:
                seen.append(vid)
            if len(seen) >= max_results:
                break

        results = []
        for vid in seen:
            try:
                oembed = requests.get(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={vid}&format=json", timeout=6)
                if oembed.status_code != 200:
                    continue
                jd = oembed.json()
                title = jd.get("title")
                thumbnail = jd.get("thumbnail_url")
                url = f"https://www.youtube.com/watch?v={vid}"
                results.append({"title": title, "url": url, "thumbnail": thumbnail})
            except Exception:
                continue

        return results
    except Exception as e:
        print(f"\n[Search Fallback Error] {e}")
        return []


def download_audio(url, outdir, preferred_runtime=None, remote_components=None):
    os.makedirs(outdir, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        **get_yt_dlp_js_opts(preferred_runtime=preferred_runtime, remote_components=remote_components),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        print(f"[Download Error] Skipping broken video: {e}")
        return None

    title = safe_title(info.get("title"))
    filename = os.path.join(outdir, f"{title}.mp3")
    return filename
