# coding: utf-8
"""SkebFetcher のテスト
"""
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

from mock import patch

from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.Skeb.SkebFetcher import SkebFetcher
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username


class TestSkebFetcher(unittest.TestCase):
    def setUp(self):
        self.TBP = Path("./test/LinkSearch/Skeb/PG_skeb")

    def get_instance(self) -> SkebFetcher:
        with ExitStack() as stack:
            self.mock_skeb_session = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebFetcher.SkebSession"))

            username = Username("ユーザー1_ID")
            password = Password("ユーザー1_PW")
            base_path = Path(self.TBP)
            fetcher = SkebFetcher(username, password, base_path)
            return fetcher

    def test_SkebFetcher(self):
        with ExitStack() as stack:
            mock_skeb_session = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebFetcher.SkebSession"))

            username = Username("ユーザー1_ID")
            password = Password("ユーザー1_PW")
            base_path = Path(self.TBP)

            fetcher = SkebFetcher(username, password, base_path)
            self.assertTrue(hasattr(fetcher, "session"))
            mock_skeb_session.create.assert_called_once_with(username, password)
            self.assertTrue(hasattr(fetcher, "base_path"))
            self.assertEqual(base_path, fetcher.base_path)

            with self.assertRaises(TypeError):
                fetcher = SkebFetcher("invalid args", password, base_path)
            with self.assertRaises(TypeError):
                fetcher = SkebFetcher(username, "invalid args", base_path)
            with self.assertRaises(TypeError):
                fetcher = SkebFetcher(username, password, "invalid args")

    def test_is_target_url(self):
        fetcher = self.get_instance()

        work_url = "https://skeb.jp/@author1/works/1?query=1"
        url = URL(work_url)
        actual = fetcher.is_target_url(url)
        self.assertTrue(actual)

        work_url = "https://invalid.url/"
        url = URL(work_url)
        actual = fetcher.is_target_url(url)
        self.assertFalse(actual)

    def test_fetch(self):
        with ExitStack() as stack:
            mock_skeb_source_list = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebFetcher.SkebSourceList.create"))
            mock_save_directory_path = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebFetcher.SkebSaveDirectoryPath.create"))
            mock_downloader = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebFetcher.SkebDownloader"))
            mock_converter = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebFetcher.Converter"))

            mock_skeb_source_list.side_effect = lambda skeb_url, session: "skeb_source_list"
            mock_save_directory_path.side_effect = lambda skeb_url, base_path: str(self.TBP)
            fetcher = self.get_instance()

            work_url = "https://skeb.jp/@author1/works/1?query=1"
            actual = fetcher.fetch(URL(work_url))
            self.assertIsNone(actual)

            skeb_url = SkebURL.create(work_url)
            mock_skeb_source_list.assert_called_once_with(skeb_url, fetcher.session)
            mock_save_directory_path.assert_called_once_with(skeb_url, fetcher.base_path)
            mock_downloader.assert_called_once_with(skeb_url, "skeb_source_list", str(self.TBP), fetcher.session)
            dl_file_pathlist = mock_downloader().dl_file_pathlist
            mock_converter.assert_called_once_with(dl_file_pathlist)
            mock_converter().convert.assert_called_once_with()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
