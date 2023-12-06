import sys
import unittest
from contextlib import ExitStack
from logging import WARNING, getLogger
from pathlib import Path

from mock import patch

from media_gathering.link_search.Password import Password
from media_gathering.link_search.pixiv.PixivFetcher import PixivFetcher
from media_gathering.link_search.pixiv.PixivWorkURL import PixivWorkURL
from media_gathering.link_search.URL import URL
from media_gathering.link_search.Username import Username

logger = getLogger("media_gathering.link_search.pixiv.PixivFetcher")
logger.setLevel(WARNING)


class TestPixivFetcher(unittest.TestCase):
    def setUp(self):
        self.TBP = Path("./tests/link_search/pixiv")

    def get_instance(self):
        with ExitStack() as stack:
            m_login = stack.enter_context(patch("media_gathering.link_search.pixiv.PixivFetcher.PixivFetcher.login"))
            username = Username("ユーザー1_ID")
            password = Password("ユーザー1_PW")
            base_path = Path(self.TBP)
            fetcher = PixivFetcher(username, password, base_path)

            object.__setattr__(fetcher, "REFRESH_TOKEN_PATH", self.TBP / "refresh_token.ini")
            return fetcher

    def test_PixivFetcher(self):
        with ExitStack() as stack:
            m_login = stack.enter_context(patch("media_gathering.link_search.pixiv.PixivFetcher.PixivFetcher.login"))

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
            mock_aapi = stack.enter_context(patch("media_gathering.link_search.pixiv.PixivFetcher.AppPixivAPI"))
            mock_logger_error = stack.enter_context(patch.object(logger, "error"))

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

            mock_aapi().auth.reset_mock()
            mock_aapi().access_token = None
            with self.assertRaises(ValueError):
                actual = fetcher.login(username, password)

            mock_aapi().auth.side_effect = ValueError
            with self.assertRaises(ValueError):
                actual = fetcher.login(username, password)

            rt_path.unlink(missing_ok=True)

            with self.assertRaises(ValueError):
                actual = fetcher.login(username, password)

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
            m_pixiv_source_list = stack.enter_context(patch("media_gathering.link_search.pixiv.PixivFetcher.PixivSourceList"))
            m_pixiv_save_directory_path = stack.enter_context(patch("media_gathering.link_search.pixiv.PixivFetcher.PixivSaveDirectoryPath"))
            m_downloader = stack.enter_context(patch("media_gathering.link_search.pixiv.PixivFetcher.PixivWorkDownloader"))

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
