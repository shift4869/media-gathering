import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

from mock import MagicMock, mock_open, patch

from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.Pixiv.PixivFetcher import PixivFetcher
from PictureGathering.LinkSearch.Pixiv.PixivWorkURL import PixivWorkURL
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username


class TestPixivFetcher(unittest.TestCase):
    def setUp(self):
        self.TBP = Path("./test/LinkSearch/Pixiv")

    def get_instance(self):
        with ExitStack() as stack:
            m_login = stack.enter_context(patch("PictureGathering.LinkSearch.Pixiv.PixivFetcher.PixivFetcher.login"))
            username = Username("ユーザー1_ID")
            password = Password("ユーザー1_PW")
            base_path = Path(self.TBP)
            fetcher = PixivFetcher(username, password, base_path)

            object.__setattr__(fetcher, "REFRESH_TOKEN_PATH", self.TBP / "refresh_token.ini")
            return fetcher

    def test_PixivFetcher(self):
        with ExitStack() as stack:
            m_login = stack.enter_context(patch("PictureGathering.LinkSearch.Pixiv.PixivFetcher.PixivFetcher.login"))

            REFRESH_TOKEN_PATH = "./config/refresh_token.ini"
            username = Username("ユーザー1_ID")
            password = Password("ユーザー1_PW")
            base_path = Path(self.TBP)

            # 正常系
            actual = PixivFetcher(username, password, base_path)
            self.assertEqual(True, hasattr(actual, "aapi"))
            m_login.assert_called_once_with(username, password)
            self.assertEqual(True, hasattr(actual, "base_path"))
            self.assertEqual(base_path, actual.base_path)
            self.assertEqual(REFRESH_TOKEN_PATH, actual.REFRESH_TOKEN_PATH)

            # 異常系
            with self.assertRaises(TypeError):
                actual = PixivFetcher("invalid args", password, base_path)
            with self.assertRaises(TypeError):
                actual = PixivFetcher(username, "invalid args", base_path)
            with self.assertRaises(TypeError):
                actual = PixivFetcher(username, password, "invalid args")

    def test_login(self):
        with ExitStack() as stack:
            m_aapi = stack.enter_context(patch("PictureGathering.LinkSearch.Pixiv.PixivFetcher.AppPixivAPI"))
            m_open = stack.enter_context(patch("PictureGathering.LinkSearch.Pixiv.PixivFetcher.Path.open", mock_open()))

            username = Username("ユーザー1_ID")
            password = Password("ユーザー1_PW")
            fetcher = self.get_instance()

            refresh_token_path = Path(fetcher.REFRESH_TOKEN_PATH)
            refresh_token_path.touch(exist_ok=True)

            expect = m_aapi()
            actual = fetcher.login(username, password)
            self.assertEqual(expect, actual)

            refresh_token_path.unlink(missing_ok=True)

    def test_is_target_url(self):
        fetcher = self.get_instance()

        # 正常系
        work_url = f"https://www.pixiv.net/artworks/86704541?query=1"
        url = URL(work_url)
        actual = fetcher.is_target_url(url)
        self.assertEqual(True, actual)

        # 異常系
        work_url = f"https://invalid.url/"
        url = URL(work_url)
        actual = fetcher.is_target_url(url)
        self.assertEqual(False, actual)

    def test_fetch(self):
        with ExitStack() as stack:
            m_pixiv_source_list = stack.enter_context(patch("PictureGathering.LinkSearch.Pixiv.PixivFetcher.PixivSourceList"))
            m_pixiv_save_directory_path = stack.enter_context(patch("PictureGathering.LinkSearch.Pixiv.PixivFetcher.PixivSaveDirectoryPath"))
            m_downloader = stack.enter_context(patch("PictureGathering.LinkSearch.Pixiv.PixivFetcher.PixivWorkDownloader"))

            fetcher = self.get_instance()

            work_url = f"https://www.pixiv.net/artworks/86704541?query=1"
            pixiv_work_url = PixivWorkURL.create(work_url)
            actual = fetcher.fetch(work_url)
            self.assertEqual(None, actual)
            m_pixiv_source_list.create.assert_called_once_with(fetcher.aapi, pixiv_work_url)
            m_pixiv_save_directory_path.create.assert_called_once_with(fetcher.aapi, pixiv_work_url, fetcher.base_path)
            m_downloader.assert_called_once_with(fetcher.aapi, m_pixiv_source_list.create(), m_pixiv_save_directory_path.create())
            m_downloader().download.assert_called_once_with()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
