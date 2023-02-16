# coding: utf-8
"""NicoSeigaDownloader のテスト

ニコニコ静画作品をDLするクラスをテストする
"""
import shutil
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

from mock import MagicMock, PropertyMock, mock_open, patch

from PictureGathering.LinkSearch.FetcherBase import FetcherBase
from PictureGathering.LinkSearch.NicoSeiga.Authorid import Authorid
from PictureGathering.LinkSearch.NicoSeiga.Authorname import Authorname
from PictureGathering.LinkSearch.NicoSeiga.Illustname import Illustname
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaDownloader import NicoSeigaDownloader
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaFetcher import NicoSeigaFetcher
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSession import NicoSeigaSession
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaURL import NicoSeigaURL
from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username


class TestNicoSeigaFetcher(unittest.TestCase):
    def setUp(self):
        self.TBP = Path("./test")

    def tearDown(self):
        pass

    def test_NicoSeigaFetcher(self):
        with ExitStack() as stack:
            m_session = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaFetcher.NicoSeigaSession"))

            username = Username("ユーザー1_ID")
            password = Password("ユーザー1_PW")
            base_path = Path(self.TBP)

            # 正常系
            actual = NicoSeigaFetcher(username, password, base_path)
            self.assertEqual(True, hasattr(actual, "session"))
            m_session.assert_called_once_with(username, password)
            self.assertEqual(True, hasattr(actual, "base_path"))
            self.assertEqual(base_path, actual.base_path)

            # 異常系
            with self.assertRaises(TypeError):
                actual = NicoSeigaFetcher("invalid args", password, base_path)
            with self.assertRaises(TypeError):
                actual = NicoSeigaFetcher(username, "invalid args", base_path)
            with self.assertRaises(TypeError):
                actual = NicoSeigaFetcher(username, password, "invalid args")

    def test_is_target_url(self):
        with ExitStack() as stack:
            m_session = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaFetcher.NicoSeigaSession"))

            username = Username("ユーザー1_ID")
            password = Password("ユーザー1_PW")
            base_path = Path(self.TBP)
            fetcher = NicoSeigaFetcher(username, password, base_path)

            # 正常系
            illust_url = f"https://seiga.nicovideo.jp/seiga/im11111111?query=1"
            url = URL(illust_url)
            actual = fetcher.is_target_url(url)
            self.assertEqual(True, actual)

            # 異常系
            illust_url = f"https://invalid.url/seiga/im11111111?query=1"
            url = URL(illust_url)
            actual = fetcher.is_target_url(url)
            self.assertEqual(False, actual)

    def test_fetch(self):
        with ExitStack() as stack:
            m_session = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaFetcher.NicoSeigaSession"))
            m_downloader = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaFetcher.NicoSeigaDownloader"))

            username = Username("ユーザー1_ID")
            password = Password("ユーザー1_PW")
            base_path = Path(self.TBP)
            fetcher = NicoSeigaFetcher(username, password, base_path)

            illust_url = f"https://seiga.nicovideo.jp/seiga/im11111111?query=1"
            nicoseiga_url = NicoSeigaURL.create(illust_url)
            actual = fetcher.fetch(illust_url)
            self.assertEqual(None, actual)
            m_downloader.assert_called_once_with(nicoseiga_url, base_path, fetcher.session)
            m_downloader().download.assert_called_once_with()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
