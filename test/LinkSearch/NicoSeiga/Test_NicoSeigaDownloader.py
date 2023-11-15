"""NicoSeigaDownloader のテスト

ニコニコ静画作品をDLするクラスをテストする
"""
import shutil
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

from mock import MagicMock, mock_open, patch

from PictureGathering.LinkSearch.NicoSeiga.Authorid import Authorid
from PictureGathering.LinkSearch.NicoSeiga.Authorname import Authorname
from PictureGathering.LinkSearch.NicoSeiga.Illustname import Illustname
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaDownloader import DownloadResult, NicoSeigaDownloader
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaInfo import NicoSeigaInfo
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSaveDirectoryPath import NicoSeigaSaveDirectoryPath
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSession import NicoSeigaSession
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaURL import NicoSeigaURL


class TestNicoSeigaDownloader(unittest.TestCase):
    def setUp(self):
        self.TBP = Path("./test")

    def tearDown(self):
        pass

    def test_DownloadResult(self):
        expect = ["SUCCESS", "PASSED"]
        actual = [r.name for r in DownloadResult]
        self.assertEqual(expect, actual)

    def test_NicoSeigaDownloader(self):
        nicoseiga_url = NicoSeigaURL.create("https://seiga.nicovideo.jp/seiga/im11111111")
        base_path = Path("./test")
        session = None
        with ExitStack() as stack:
            m_sessionlogin = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSession.NicoSeigaSession.login"))
            m_is_valid = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSession.NicoSeigaSession._is_valid"))
            session = NicoSeigaSession("username", "password")

        downloader = NicoSeigaDownloader(nicoseiga_url, base_path, session)

        self.assertEqual(nicoseiga_url, downloader.nicoseiga_url)
        self.assertEqual(base_path, downloader.base_path)
        self.assertEqual(session, downloader.session)

    def test_is_valid(self):
        nicoseiga_url = NicoSeigaURL.create("https://seiga.nicovideo.jp/seiga/im11111111")
        base_path = Path("./test")
        session = None
        with ExitStack() as stack:
            m_sessionlogin = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSession.NicoSeigaSession.login"))
            m_is_valid = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSession.NicoSeigaSession._is_valid"))
            session = NicoSeigaSession("username", "password")

        downloader = NicoSeigaDownloader(nicoseiga_url, base_path, session)

        # 正常系
        self.assertEqual(True, downloader._is_valid())

        # 異常系
        # 作品ページ指定が不正
        with self.assertRaises(TypeError):
            downloader = NicoSeigaDownloader("invalid args", base_path, session)

        # 保存ディレクトリベースパス指定が不正
        with self.assertRaises(TypeError):
            downloader = NicoSeigaDownloader(nicoseiga_url, "invalid args", session)

        # セッション指定が不正
        with self.assertRaises(TypeError):
            downloader = NicoSeigaDownloader(nicoseiga_url, base_path, "invalid args")

    def test_download(self):
        nicoseiga_url = NicoSeigaURL.create("https://seiga.nicovideo.jp/seiga/im11111111")
        base_path = Path("./test")
        author_id = Authorid(12345678)
        illust_id = nicoseiga_url.illust_id
        illust_name = Illustname("作品名1")
        author_name = Authorname("作成者1")
        illust_info = NicoSeigaInfo(illust_id, illust_name, author_id, author_name)
        save_directory_path = NicoSeigaSaveDirectoryPath.create(illust_info, base_path)

        session = MagicMock()
        session.get_author_id.side_effect = lambda id: author_id
        session.get_illust_title.side_effect = lambda id: illust_name
        session.get_author_name.side_effect = lambda id: author_name
        session.get_source_url.side_effect = lambda id: None
        session.get_illust_binary.side_effect = lambda url: b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"
        with ExitStack() as stack:
            m_is_valid = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaDownloader.NicoSeigaDownloader._is_valid"))
            # m_mkdir = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaDownloader.Path.mkdir"))
            # m_open = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaDownloader.Path.open", mock_open()))
            m_logger_info = stack.enter_context(patch("PictureGathering.LinkSearch.NicoSeiga.NicoSeigaDownloader.logger.info"))

            # 初回DL想定
            downloader = NicoSeigaDownloader(nicoseiga_url, base_path, session)
            expect = DownloadResult.SUCCESS
            actual = downloader.download()
            self.assertEqual(expect, actual)

            # 2回目DL想定
            expect = DownloadResult.PASSED
            actual = downloader.download()
            self.assertEqual(expect, actual)

            # 後始末
            sd_path = save_directory_path.path
            if sd_path.parent.exists():
                shutil.rmtree(sd_path.parent)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
