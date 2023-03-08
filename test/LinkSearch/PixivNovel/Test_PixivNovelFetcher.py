# coding: utf-8
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

from mock import MagicMock, mock_open, patch

from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.PixivNovel.PixivNovelFetcher import PixivNovelFetcher
from PictureGathering.LinkSearch.PixivNovel.PixivNovelURL import PixivNovelURL
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username


class TestPixivNovelFetcher(unittest.TestCase):
    def setUp(self):
        self.TBP = Path("./test/LinkSearch/PixivNovel")

    def get_instance(self) -> PixivNovelFetcher:
        with ExitStack() as stack:
            self.mock_login = stack.enter_context(patch("PictureGathering.LinkSearch.PixivNovel.PixivNovelFetcher.PixivNovelFetcher.login"))

            username = Username("ユーザー1_ID")
            password = Password("ユーザー1_PW")
            base_path = Path(self.TBP)
            fetcher = PixivNovelFetcher(username, password, base_path)
            object.__setattr__(fetcher, "REFRESH_TOKEN_PATH", str(self.TBP / "refresh_token.ini"))

            return fetcher

    def test_PixivNovelFetcher(self):
        with ExitStack() as stack:
            mock_login = stack.enter_context(patch("PictureGathering.LinkSearch.PixivNovel.PixivNovelFetcher.PixivNovelFetcher.login"))

            REFRESH_TOKEN_PATH = "./config/refresh_token.ini"
            username = Username("ユーザー1_ID")
            password = Password("ユーザー1_PW")
            base_path = Path(self.TBP)

            fetcher = PixivNovelFetcher(username, password, base_path)
            self.assertTrue(hasattr(fetcher, "aapi"))
            mock_login.assert_called_once_with(username, password)
            self.assertTrue(hasattr(fetcher, "base_path"))
            self.assertEqual(base_path, fetcher.base_path)
            self.assertEqual(REFRESH_TOKEN_PATH, fetcher.REFRESH_TOKEN_PATH)

            with self.assertRaises(TypeError):
                fetcher = PixivNovelFetcher("invalid args", password, base_path)
            with self.assertRaises(TypeError):
                fetcher = PixivNovelFetcher(username, "invalid args", base_path)
            with self.assertRaises(TypeError):
                fetcher = PixivNovelFetcher(username, password, "invalid args")

    def test_login(self):
        with ExitStack() as stack:
            mock_aapi = stack.enter_context(patch("PictureGathering.LinkSearch.PixivNovel.PixivNovelFetcher.AppPixivAPI"))

            username = Username("ユーザー1_ID")
            password = Password("ユーザー1_PW")
            fetcher = self.get_instance()

            refresh_token = "dummy_refresh_token"
            rt_path = Path(fetcher.REFRESH_TOKEN_PATH)
            with rt_path.open(mode="w") as fout:
                fout.write(refresh_token)

            actual = fetcher.login(username, password)
            mock_aapi().auth.assert_called_once_with(refresh_token=refresh_token)
            expect = mock_aapi()
            self.assertEqual(expect, actual)

            rt_path.unlink(missing_ok=True)

    def test_is_target_url(self):
        fetcher = self.get_instance()

        work_url = "https://www.pixiv.net/novel/show.php?id=3195243"
        url = URL(work_url)
        actual = fetcher.is_target_url(url)
        self.assertTrue(actual)

        work_url = "https://invalid.url/"
        url = URL(work_url)
        actual = fetcher.is_target_url(url)
        self.assertFalse(actual)

    def test_fetch(self):
        with ExitStack() as stack:
            mock_save_directory_path = stack.enter_context(patch("PictureGathering.LinkSearch.PixivNovel.PixivNovelFetcher.PixivNovelSaveDirectoryPath.create"))
            mock_downloader = stack.enter_context(patch("PictureGathering.LinkSearch.PixivNovel.PixivNovelFetcher.PixivNovelDownloader"))

            mock_save_directory_path.side_effect = lambda aapi, novel_url, base_path: str(self.TBP)
            fetcher = self.get_instance()

            work_url = "https://www.pixiv.net/novel/show.php?id=3195243"
            actual = fetcher.fetch(URL(work_url))
            self.assertIsNone(actual)

            novel_url = PixivNovelURL.create(work_url)
            mock_save_directory_path.assert_called_once_with(fetcher.aapi, novel_url, fetcher.base_path)
            mock_downloader.assert_called_once_with(fetcher.aapi, novel_url, str(self.TBP))
            mock_downloader().download.assert_called_once_with()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
