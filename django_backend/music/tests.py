from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from django.http import FileResponse
from django.test import RequestFactory, SimpleTestCase

from . import downloader
from .views import download_direct


class DownloadDirectViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("music.downloader.yt_dlp.YoutubeDL")
    def test_download_audio_handles_non_dict_info(self, mock_youtube_dl):
        class FakeYDL:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

            def extract_info(self, url, download=True):
                return "unexpected-result"

        mock_youtube_dl.return_value = FakeYDL()

        path, error = downloader.download_audio("https://example.com", "/tmp")

        self.assertIsNone(path)
        self.assertIn("unexpected result", error.lower())

    @patch("music.downloader.yt_dlp.YoutubeDL")
    def test_download_audio_returns_clean_message_for_extractor_error(self, mock_youtube_dl):
        class FakeYDL:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

            def extract_info(self, url, download=True):
                raise AttributeError("'str' object has no attribute 'get'")

        mock_youtube_dl.return_value = FakeYDL()

        path, error = downloader.download_audio("https://example.com", "/tmp")

        self.assertIsNone(path)
        self.assertIn("yt-dlp extractor encountered unexpected data", error)

    @patch("music.views.downloader.download_audio")
    def test_download_direct_returns_file_response(self, mock_download_audio):
        with NamedTemporaryFile(suffix=".mp3", delete=False) as handle:
            handle.write(b"fake mp3")
            temp_path = handle.name

        try:
            mock_download_audio.return_value = (temp_path, None)
            request = self.factory.post(
                "/api/download-direct/",
                data='{"url": "https://example.com", "title": "Test Track"}',
                content_type="application/json",
            )

            response = download_direct(request)

            self.assertEqual(response.status_code, 200)
            self.assertIsInstance(response, FileResponse)
            self.assertIn('filename="Test Track.mp3"', response["Content-Disposition"])
        finally:
            Path(temp_path).unlink(missing_ok=True)
