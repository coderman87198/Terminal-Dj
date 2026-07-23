import os
import threading
import time
from flask import Flask, render_template_string, request, jsonify, send_from_directory
import downloader
import mixer
import main as terminal_dj

app = Flask(__name__)
app.config['OUTPUT_DIR'] = os.path.join(os.path.dirname(__file__), 'finished_product')
downloaded_files = []
selected_tracks = []

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Terminal DJ</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #0f172a; color: #f8fafc; }
    .container { max-width: 980px; margin: 0 auto; padding: 24px; }
    .card { background: #111827; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
    h1, h2 { margin-top: 0; }
    input, textarea, button { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #475569; margin-top: 8px; }
    button { background: #38bdf8; color: #082f49; font-weight: bold; cursor: pointer; }
    .row { display: grid; gap: 12px; grid-template-columns: 1fr 1fr; }
    .result, .status { background: #020617; padding: 10px; border-radius: 8px; margin-top: 8px; }
    .result button { width: auto; padding: 6px 10px; margin-top: 0; }
    .result.selected { border: 1px solid #38bdf8; background: #0f172a; }
    .thumb { width: 100%; max-width: 220px; border-radius: 8px; margin-top: 8px; }
    .pill { display: inline-block; padding: 4px 8px; border-radius: 999px; background: #1e293b; margin-top: 8px; font-size: 0.85rem; }
    ul { padding-left: 18px; }
    .small { font-size: 0.9rem; color: #94a3b8; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h1>Terminal DJ</h1>
      <p class="small">A simple deployable page for searching YouTube, curating playlists, downloading audio, and creating a mixed MP3.</p>
    </div>

    <div class="card">
      <h2>Search YouTube</h2>
      <div class="row">
        <div>
          <label>Query</label>
          <input id="query" placeholder="e.g. lo-fi chill" />
        </div>
        <div>
          <label>Max results</label>
          <input id="maxResults" type="number" value="8" min="1" max="20" />
        </div>
      </div>
      <button id="searchButton">Search</button>
      <div id="searchResults"></div>
      <div id="selectedTracksPanel"></div>
      <button id="downloadSelectedButton">Download selected tracks</button>
      <div id="downloadStatus"></div>
    </div>

    <div class="card">
      <h2>Curate a playlist</h2>
      <textarea id="curatePrompt" rows="3" placeholder="Describe the kind of playlist you want"></textarea>
      <button id="curateButton">Create curated mix</button>
      <div id="curationStatus"></div>
    </div>

    <div class="card">
      <h2>Downloaded tracks</h2>
      <button id="mixButton">Build mix from downloaded tracks</button>
      <div id="mixStatus"></div>
    </div>

    <div class="card">
      <h2>Quick actions</h2>
      <button id="demoButton">Generate demo mix</button>
      <div id="demoStatus"></div>
    </div>
  </div>

  <script>
    let selectedTracks = [];

    document.addEventListener('DOMContentLoaded', () => {
      document.getElementById('searchButton').addEventListener('click', searchTracks);
      document.getElementById('downloadSelectedButton').addEventListener('click', downloadSelectedTracks);
      document.getElementById('curateButton').addEventListener('click', curatePlaylist);
      document.getElementById('mixButton').addEventListener('click', buildMix);
      document.getElementById('demoButton').addEventListener('click', runDemo);

      document.getElementById('searchResults').addEventListener('click', (event) => {
        const button = event.target.closest('button[data-action="toggle-track"]');
        if (!button) return;
        const item = JSON.parse(button.dataset.item);
        toggleTrackSelection(item);
      });
    });

    function renderSelectedTracks() {
      const panel = document.getElementById('selectedTracksPanel');
      if (!selectedTracks.length) {
        panel.innerHTML = '<div class="status">No tracks selected yet.</div>';
        return;
      }
      panel.innerHTML = `<div class="status"><strong>Selected tracks</strong><br>${selectedTracks.map((item, index) => `
        <div class="pill">${index + 1}. ${item.title}</div>
      `).join('')}</div>`;
    }

    function toggleTrackSelection(item) {
      const exists = selectedTracks.some(track => track.url === item.url);
      if (exists) {
        selectedTracks = selectedTracks.filter(track => track.url !== item.url);
      } else {
        selectedTracks.push(item);
      }
      renderSelectedTracks();
      if (typeof window.renderSearchResults === 'function') {
        window.renderSearchResults();
      }
    }

    async function searchTracks() {
      const query = document.getElementById('query').value.trim();
      const maxResults = document.getElementById('maxResults').value;
      const resultsBox = document.getElementById('searchResults');
      if (!query) return;
      resultsBox.innerHTML = '<div class="status">Searching...</div>';
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, max_results: parseInt(maxResults, 10) })
      });
      const data = await response.json();
      if (!data.results || !data.results.length) {
        resultsBox.innerHTML = '<div class="status">No results found.</div>';
        return;
      }
      window.renderSearchResults = () => {
        resultsBox.innerHTML = data.results.map((item, index) => {
          const isSelected = selectedTracks.some(track => track.url === item.url);
          return `
            <div class="result ${isSelected ? 'selected' : ''}">
              <strong>${index + 1}. ${item.title}</strong><br>
              <span class="small">${item.url}</span><br>
              ${item.thumbnail ? `<img class="thumb" src="${item.thumbnail}" alt="${item.title}">` : ''}
              <div style="margin-top:8px;">
                <button type="button" data-action="toggle-track" data-item='${JSON.stringify(item).replace(/'/g, "&apos;")}'>${isSelected ? 'Remove' : 'Select'}</button>
              </div>
            </div>
          `;
        }).join('');
      };
      window.renderSearchResults();
      renderSelectedTracks();
    }

    async function downloadSelectedTracks() {
      if (!selectedTracks.length) {
        document.getElementById('downloadStatus').innerHTML = '<div class="status">Select at least one track first.</div>';
        return;
      }
      const statusBox = document.getElementById('downloadStatus');
      statusBox.innerHTML = '<div class="status">Downloading selected tracks...</div>';
      const response = await fetch('/api/download-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tracks: selectedTracks })
      });
      const data = await response.json();
      statusBox.innerHTML = `<div class="status">${data.message}<br>${data.paths ? data.paths.join('<br>') : ''}</div>`;
    }

    async function buildMix() {
      const statusBox = document.getElementById('mixStatus');
      statusBox.innerHTML = '<div class="status">Creating mix...</div>';
      const response = await fetch('/api/mix', { method: 'POST' });
      const data = await response.json();
      const outputHtml = data.download_url ? `<a href="${data.download_url}" target="_blank" style="color:#38bdf8; display:inline-block; margin-top:8px; font-weight:bold;">Download mix</a>` : '';
      statusBox.innerHTML = `<div class="status">${data.message}<br>${data.output ? 'Output: ' + data.output : ''}<br>${outputHtml}</div>`;
    }

    async function curatePlaylist() {
      const prompt = document.getElementById('curatePrompt').value.trim();
      const statusBox = document.getElementById('curationStatus');
      if (!prompt) return;
      statusBox.innerHTML = '<div class="status">Creating playlist...</div>';
      const response = await fetch('/api/curate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      });
      const data = await response.json();
      statusBox.innerHTML = `<div class="status">${data.message}<br>${data.output ? 'Output: ' + data.output : ''}</div>`;
    }

    async function runDemo() {
      const statusBox = document.getElementById('demoStatus');
      statusBox.innerHTML = '<div class="status">Generating demo mix...</div>';
      const response = await fetch('/api/demo', { method: 'POST' });
      const data = await response.json();
      statusBox.innerHTML = `<div class="status">${data.message}<br>${data.output ? 'Output: ' + data.output : ''}</div>`;
    }
  </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/search', methods=['POST'])
def api_search():
    payload = request.get_json(silent=True) or {}
    query = payload.get('query', '').strip()
    max_results = int(payload.get('max_results', 8) or 8)
    results = downloader.search_youtube(query, max_results=max_results)
    return jsonify({'results': results})


@app.route('/api/download', methods=['POST'])
def api_download():
    payload = request.get_json(silent=True) or {}
    url = payload.get('url', '').strip()
    if not url:
        return jsonify({'message': 'Please provide a URL.'})

    path = downloader.download_audio(url, terminal_dj.DOWNLOAD_DIR)
    if path:
        downloaded_files.append(path)
        return jsonify({'message': 'Download completed.', 'path': path})
    return jsonify({'message': 'Download failed.'})


@app.route('/api/download-batch', methods=['POST'])
def api_download_batch():
    payload = request.get_json(silent=True) or {}
    tracks = payload.get('tracks', []) or []
    if not tracks:
        return jsonify({'message': 'Please select at least one track.'})

    paths = []
    for track in tracks:
        url = (track.get('url') or '').strip()
        if not url:
            continue
        path = downloader.download_audio(url, terminal_dj.DOWNLOAD_DIR)
        if path:
            downloaded_files.append(path)
            paths.append(path)

    if paths:
        return jsonify({'message': 'Downloads completed.', 'paths': paths})
    return jsonify({'message': 'No tracks could be downloaded.'})


@app.route('/download-mix/<path:filename>')
def download_mix(filename):
    return send_from_directory(app.config['OUTPUT_DIR'], filename, as_attachment=True)


@app.route('/api/mix', methods=['POST'])
def api_mix():
    if not downloaded_files:
        return jsonify({'message': 'No downloaded tracks available yet.'})

    output = mixer.crossfade_tracks(list(downloaded_files), crossfade_ms=3000, output_path='selected_mix.mp3')
    filename = os.path.basename(output)
    return jsonify({
        'message': 'Mix created.',
        'output': output,
        'download_url': f'/download-mix/{filename}'
    })


@app.route('/api/curate', methods=['POST'])
def api_curate():
    payload = request.get_json(silent=True) or {}
    prompt = payload.get('prompt', '').strip()
    if not prompt:
        return jsonify({'message': 'Please provide a prompt.'})

    output = terminal_dj.curated_flow(prompt)
    message = 'Curated playlist completed.' if output else 'No playlist could be created.'
    return jsonify({'message': message, 'output': output})


@app.route('/api/demo', methods=['POST'])
def api_demo():
    files = terminal_dj.create_demo_files(n=3, duration_ms=3000)
    output = mixer.crossfade_tracks(files, crossfade_ms=3000, output_path='mix_demo.mp3')
    return jsonify({'message': 'Demo mix created.', 'output': output})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
