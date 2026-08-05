import shutil
import sys
import unittest
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from media_gathering.link_search.nico_seiga.authorid import Authorid
from media_gathering.link_search.nico_seiga.authorname import Authorname
from media_gathering.link_search.nico_seiga.illustid import Illustid
from media_gathering.link_search.nico_seiga.illustname import Illustname
from media_gathering.link_search.nico_seiga.nico_seiga_downloader import DownloadResult, NicoSeigaDownloader
from media_gathering.link_search.nico_seiga.nico_seiga_session import NicoSeigaSession
from media_gathering.link_search.nico_seiga.nico_seiga_url import NicoSeigaURL
from media_gathering.link_search.url import URL


class TestNicoSeigaDownloader(TestCase):
    def setUp(self):
        self.base_path = Path("./test_output")
        self.url = NicoSeigaURL.create("https://seiga.nicovideo.jp/seiga/im12345?query=1")
        self.session = Mock(spec=NicoSeigaSession)
        self.session.get_author_id.return_value = Authorid(11111)
        self.session.get_illust_title.return_value = Illustname("test title")
        self.session.get_author_name.return_value = Authorname("test author")
        self.session.get_source_url.return_value = URL("https://seiga.nicovideo.jp/seiga/im12345?query=1")
        self.session.get_illust_binary.return_value = b"\x89PNG\r\n\x1a\n"
        self.mock_logger = self.enterContext(
            patch("media_gathering.link_search.nico_seiga.nico_seiga_downloader.logger")
        )

    def tearDown(self):
        if self.base_path.exists():
            shutil.rmtree(self.base_path)

    def test_init(self):
        downloader = NicoSeigaDownloader(
            self.url,
            self.base_path,
            self.session,
        )

        self.assertTrue(downloader._is_valid())

        with self.assertRaises(TypeError):
            NicoSeigaDownloader(
                "invalid",
                self.base_path,
                self.session,
            )

        with self.assertRaises(TypeError):
            NicoSeigaDownloader(
                self.url,
                "invalid",
                self.session,
            )

        with self.assertRaises(TypeError):
            NicoSeigaDownloader(
                self.url,
                self.base_path,
                "invalid",
            )

    def test_download_success(self):
        mock_extension = self.enterContext(
            patch("media_gathering.link_search.nico_seiga.nico_seiga_downloader.IllustExtension.create")
        )
        mock_extension.return_value.extension = ".png"

        downloader = NicoSeigaDownloader(
            self.url,
            self.base_path,
            self.session,
        )

        result = downloader.download()
        self.assertEqual(
            result,
            DownloadResult.SUCCESS,
        )

    def test_download_skip_existing_file(self):
        downloader = NicoSeigaDownloader(
            self.url,
            self.base_path,
            self.session,
        )

        # 1回目DLしてファイル作成
        result1 = downloader.download()
        self.assertEqual(
            result1,
            DownloadResult.SUCCESS,
        )
        self.session.get_illust_binary.assert_called_once()

        # Mockの呼び出し履歴をリセット
        self.session.get_illust_binary.reset_mock()
        # 2回目は存在判定でPASS
        result2 = downloader.download()
        self.assertEqual(
            result2,
            DownloadResult.PASSED,
        )
        # 再DLされていないことを確認
        self.session.get_illust_binary.assert_not_called()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
