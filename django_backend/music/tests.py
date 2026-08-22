from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest.mock import patch

from django.http import FileResponse
from django.test import RequestFactory, SimpleTestCase

from . import downloader
from .views import download_direct


class DownloaderConfigurationTests(SimpleTestCase):
    def test_browser_cookie_configuration_uses_yt_dlp_tuple(self):
        with patch.dict("os.environ", {"YT_DLP_COOKIES_FROM_BROWSER": "chrome:Default"}, clear=False):
            options = downloader.get_yt_dlp_cookie_opts()

        self.assertEqual(options["cookiesfrombrowser"], ("chrome", "Default"))

    def test_cookie_contents_are_written_to_private_file(self):
        with patch.dict("os.environ", {"YT_DLP_COOKIE_CONTENTS": "# Netscape HTTP Cookie File\n"}, clear=True):
            options = downloader.get_yt_dlp_cookie_opts()

        self.assertTrue(Path(options["cookiefile"]).is_file())
        self.assertEqual(Path(options["cookiefile"]).stat().st_mode & 0o777, 0o600)

    def test_empty_auto_detected_cookie_file_is_ignored(self):
        with TemporaryDirectory() as directory:
            Path(directory, "cookies.txt").touch()
            with patch.dict("os.environ", {}, clear=True), patch("pathlib.Path.cwd", return_value=Path(directory)):
                options = downloader.get_yt_dlp_cookie_opts()

        self.assertNotIn("cookiefile", options)


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

        with NamedTemporaryFile(suffix=".txt", delete=False) as handle:
            handle.write(b"cookie-data")
            cookie_path = handle.name

        try:
            with patch.dict("os.environ", {"YT_DLP_COOKIEFILE": cookie_path}, clear=False):
                path, error = downloader.download_audio("https://example.com", "/tmp")
        finally:
            Path(cookie_path).unlink(missing_ok=True)

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

        with NamedTemporaryFile(suffix=".txt", delete=False) as handle:
            handle.write(b"cookie-data")
            cookie_path = handle.name

        try:
            with patch.dict("os.environ", {"YT_DLP_COOKIEFILE": cookie_path}, clear=False):
                path, error = downloader.download_audio("https://example.com", "/tmp")
        finally:
            Path(cookie_path).unlink(missing_ok=True)

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
