import json
import os
import sys
from pathlib import Path

from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.append(str(WORKSPACE_ROOT))

from . import downloader
from . import mixer
from . import main as terminal_dj

OUTPUT_DIR = os.path.join(WORKSPACE_ROOT, 'finished_product')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def index(request):
    return render(request, 'music/index.html')


def download_mix(request, filename):
    source = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(source):
        raise Http404('File not found')
    return FileResponse(open(source, 'rb'), as_attachment=True, filename=filename)


@csrf_exempt
def search_tracks(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        payload = {}

    query = (payload.get('query') or '').strip()
    max_results = int(payload.get('max_results') or 8)
    if not query:
        return JsonResponse({'results': []})

    results = downloader.search_youtube(query, max_results=max_results)
    return JsonResponse({'results': results})


@csrf_exempt
def download_track(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        payload = {}

    tracks = payload.get('tracks') or []
    if tracks:
        paths = []
        for item in tracks:
            url = (item.get('url') or '').strip()
            if not url:
                continue
            path = downloader.download_audio(url, terminal_dj.DOWNLOAD_DIR)
            if path:
                paths.append(path)
        if paths:
            return JsonResponse({'message': 'Downloads completed.', 'paths': paths})
        return JsonResponse({'message': 'No tracks could be downloaded.'}, status=500)

    url = (payload.get('url') or '').strip()
    if not url:
        return JsonResponse({'message': 'Please provide a URL.'}, status=400)

    path = downloader.download_audio(url, terminal_dj.DOWNLOAD_DIR)
    if path:
        return JsonResponse({'message': 'Download completed.', 'path': path})
    return JsonResponse({'message': 'Download failed.'}, status=500)


@csrf_exempt
def build_mix(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        payload = {}

    tracks = payload.get('tracks', []) or []
    if not tracks:
        return JsonResponse({'message': 'No tracks provided.'}, status=400)

    downloaded_files = []
    for track in tracks:
        url = (track.get('url') or '').strip()
        if not url:
            continue
        path = downloader.download_audio(url, terminal_dj.DOWNLOAD_DIR)
        if path:
            downloaded_files.append(path)

    if not downloaded_files:
        return JsonResponse({'message': 'No downloadable tracks found.'}, status=500)

    output = mixer.crossfade_tracks(downloaded_files, crossfade_ms=3000, output_path='django_mix.mp3')
    filename = os.path.basename(output)
    return JsonResponse({
        'message': 'Mix created.',
        'output': output,
        'download_url': f'/download-mix/{filename}/'
    })


@csrf_exempt
def curate_playlist(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        payload = {}

    prompt = (payload.get('prompt') or '').strip()
    if not prompt:
        return JsonResponse({'message': 'Please provide a prompt.'}, status=400)

    output = terminal_dj.curated_flow(prompt)
    message = 'Curated playlist completed.' if output else 'No playlist could be created.'
    return JsonResponse({'message': message, 'output': output})


@csrf_exempt
def demo_mix(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    files = terminal_dj.create_demo_files(n=3, duration_ms=3000)
    output = mixer.crossfade_tracks(files, crossfade_ms=3000, output_path='mix_demo.mp3')
    filename = os.path.basename(output)
    return JsonResponse({
        'message': 'Demo mix created.',
        'output': output,
        'download_url': f'/download-mix/{filename}/'
    })
