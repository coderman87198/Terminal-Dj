import yt_dlp
import os
import re
import shutil
import logging

logger = logging.getLogger(__name__)


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


def get_yt_dlp_cookie_opts():
    cookiefile = os.getenv("YT_DLP_COOKIEFILE")
    cookies_from_browser = os.getenv("YT_DLP_COOKIES_FROM_BROWSER")
    opts = {}
    if cookiefile:
        opts["cookiefile"] = cookiefile
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = cookies_from_browser
    return opts


def _normalize_extractor_args(value):
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return {}
        if ':' in value and '=' in value:
            extractor_name, raw_setting = value.split(':', 1)
            setting_name, setting_value = raw_setting.split('=', 1)
            return {extractor_name: {setting_name: [setting_value]}}
    return {"youtube": {"player_client": ["android", "web"]}}


def get_yt_dlp_extractor_args():
    extractor_args = os.environ.get("YT_DLP_EXTRACTOR_ARGS")
    return {"extractor_args": _normalize_extractor_args(extractor_args)}


def _extract_video_id(url):
    if not isinstance(url, str):
        return None
    match = re.search(r"(?:v=|/)([A-Za-z0-9_-]{11})(?:[/?#]|$)", url)
    if match:
        return match.group(1)
    return None


def search_youtube(query, max_results=20, preferred_runtime=None, remote_components=None):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
        "noplaylist": True,
        **get_yt_dlp_js_opts(preferred_runtime=preferred_runtime, remote_components=remote_components),
        **get_yt_dlp_cookie_opts(),
        **get_yt_dlp_extractor_args(),
    }
    if not isinstance(ydl_opts.get("extractor_args"), dict):
        ydl_opts["extractor_args"] = {"youtube": {"player_client": ["android", "web"]}}

    # Primary attempt using yt_dlp
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            if not isinstance(info, dict):
                logger.warning("yt_dlp returned non-dict search info for query %s", query)
                return []
            entries = info.get("entries", [])
            results = []

            for e in entries:
                if not isinstance(e, dict):
                    logger.warning("Skipping non-dictionary entry during search results processing.")
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


def _find_downloaded_file(outdir, video_id, requested_ext=None):
    candidates = []
    if requested_ext:
        candidates.append(requested_ext)
    candidates.extend(['mp3', 'm4a', 'webm', 'opus', 'wav', 'aac', 'mp4'])
    seen = set()
    for ext in candidates:
        if not ext or ext in seen:
            continue
        seen.add(ext)
        candidate = os.path.join(outdir, f"{video_id}.{ext}")
        if os.path.exists(candidate):
            return candidate
    # fallback: return any file that begins with the video id
    prefix = os.path.join(outdir, f"{video_id}.")
    for file_name in os.listdir(outdir):
        if file_name.startswith(f"{video_id}."):
            return os.path.join(outdir, file_name)
    return None


def download_audio(url, outdir, preferred_runtime=None, remote_components=None):
    os.makedirs(outdir, exist_ok=True)

    cookie_path = os.getenv("YT_DLP_COOKIEFILE")
    if cookie_path:
        cookie_path = os.path.expanduser(cookie_path)
    else:
        cookie_path = None

    cookie_opts = get_yt_dlp_cookie_opts()
    if cookie_path is None and not cookie_opts.get("cookiesfrombrowser"):
        return None, (
            "No YouTube cookie source is configured. Set YT_DLP_COOKIEFILE to a Netscape-format cookies file or set YT_DLP_COOKIES_FROM_BROWSER before downloading."
        )

    if cookie_path and not os.path.exists(cookie_path):
        return None, (
            f"The configured YouTube cookie file was not found at {cookie_path}. "
            "Set YT_DLP_COOKIEFILE to the correct path for your cookies file."
        )

    ffmpeg_available = shutil.which('ffmpeg') is not None
    base_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(outdir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        **get_yt_dlp_js_opts(preferred_runtime=preferred_runtime, remote_components=remote_components),
        **cookie_opts,
        **get_yt_dlp_extractor_args(),
    }
    if cookie_path:
        base_opts["cookiefile"] = cookie_path

    if not isinstance(base_opts.get("extractor_args"), dict):
        base_opts["extractor_args"] = {"youtube": {"player_client": ["android", "web"]}}

    if ffmpeg_available:
        base_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    else:
        logger.warning("ffmpeg not available; downloading best audio without mp3 conversion.")

    candidate_opts = [dict(base_opts)]

    fallback_opts = dict(base_opts)
    fallback_opts["extractor_args"] = {"youtube": {"player_client": ["android"]}}
    candidate_opts.append(fallback_opts)

    last_error = None
    for attempt, ydl_opts in enumerate(candidate_opts, start=1):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception as exc:
            logger.exception("download_audio failed for %s (attempt %s)", url, attempt)
            last_error = str(exc) or repr(exc)
            continue

        if not isinstance(info, dict):
            logger.warning("yt_dlp returned unexpected info type for %s: %s", url, type(info).__name__)
            video_id = _extract_video_id(url)
            if video_id:
                filename = _find_downloaded_file(outdir, video_id, requested_ext='mp3')
                if filename:
                    return filename, None
            return None, 'yt_dlp returned an unexpected result for the requested URL. Please try again or use a different video.'

        video_id = info.get('id') or safe_title(info.get('title') or os.path.basename(url))
        requested_ext = None
        if ffmpeg_available:
            requested_ext = 'mp3'
        else:
            requested_ext = info.get('ext')

        filename = _find_downloaded_file(outdir, video_id, requested_ext=requested_ext)
        if filename:
            return filename, None

        last_error = f"Downloaded file not found after extraction: id={video_id} requested_ext={requested_ext}"
        logger.warning(last_error)
        break

    if last_error and ("has no attribute 'get'" in last_error or "'str' object has no attribute 'get'" in last_error):
        friendly = (
            "yt-dlp extractor encountered unexpected data while parsing the video. "
            "This can happen when yt-dlp internals change or when the page response is malformed. "
            "Try updating yt-dlp, enabling a JavaScript runtime (set YT_DLP_JS_RUNTIME=node), "
            "or providing cookies via YT_DLP_COOKIEFILE / YT_DLP_COOKIES_FROM_BROWSER."
        )
        return None, f"{friendly} (internal: {last_error})"

    return None, last_error or 'Download failed.'
