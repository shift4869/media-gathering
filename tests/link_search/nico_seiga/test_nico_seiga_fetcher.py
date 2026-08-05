import sys
import unittest
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from media_gathering.link_search.nico_seiga.nico_seiga_fetcher import NicoSeigaFetcher
from media_gathering.link_search.url import URL


class TestNicoSeigaFetcher(TestCase):
    def setUp(self):
        self.config = {
            "nico_seiga": {
                "user_session": "test_user_session",
            }
        }
        self.base_path = Path("./test_output")

    def test_init(self):
        mock_session = self.enterContext(
            patch("media_gathering.link_search.nico_seiga.nico_seiga_fetcher.NicoSeigaSession")
        )

        fetcher = NicoSeigaFetcher(
            self.config,
            self.base_path,
        )

        self.assertIsInstance(fetcher.base_path, Path)
        mock_session.assert_called_once_with(self.config)

        with self.assertRaises(TypeError):
            NicoSeigaFetcher(
                "invalid",
                self.base_path,
            )

        with self.assertRaises(TypeError):
            NicoSeigaFetcher(
                self.config,
                "invalid",
            )

    def test_is_target_url(self):
        fetcher = NicoSeigaFetcher(
            self.config,
            self.base_path,
        )

        url = URL("https://seiga.nicovideo.jp/seiga/im12345?query=1")
        self.assertTrue(fetcher.is_target_url(url))

        url = URL("https://www.example.com/test")
        self.assertFalse(fetcher.is_target_url(url))

    def test_fetch(self):
        mock_downloader = self.enterContext(
            patch("media_gathering.link_search.nico_seiga.nico_seiga_fetcher.NicoSeigaDownloader")
        )

        fetcher = NicoSeigaFetcher(
            self.config,
            self.base_path,
        )

        url = URL("https://seiga.nicovideo.jp/seiga/im12345?query=1")
        fetcher.fetch(url)
        mock_downloader.assert_called_once()
        mock_downloader.return_value.download.assert_called_once()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
