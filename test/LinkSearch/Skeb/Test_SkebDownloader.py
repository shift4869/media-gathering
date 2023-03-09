# coding: utf-8
"""SkebDownloader のテスト
"""
import shutil
import sys
import unittest
from contextlib import ExitStack
from logging import WARNING, getLogger
from pathlib import Path

from mock import MagicMock, call, patch

from PictureGathering.LinkSearch.Skeb.SaveFilename import Extension, SaveFilename
from PictureGathering.LinkSearch.Skeb.SkebDownloader import DownloadResult, SkebDownloader
from PictureGathering.LinkSearch.Skeb.SkebSaveDirectoryPath import SkebSaveDirectoryPath
from PictureGathering.LinkSearch.Skeb.SkebSession import SkebSession
from PictureGathering.LinkSearch.Skeb.SkebSourceInfo import SkebSourceInfo
from PictureGathering.LinkSearch.Skeb.SkebSourceList import SkebSourceList
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL
from PictureGathering.LinkSearch.URL import URL

logger = getLogger("PictureGathering.LinkSearch.Skeb.SkebDownloader")
logger.setLevel(WARNING)


class TestSkebDownloader(unittest.TestCase):
    def setUp(self) -> None:
        self.base_path = Path("./test/LinkSearch/Skeb/PG_Skeb")
        self.base_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.base_path.exists():
            shutil.rmtree(self.base_path)

    def test_DownloadResult(self):
        expect = ["SUCCESS", "PASSED"]
        actual = [r.name for r in DownloadResult]
        self.assertEqual(expect, actual)

    def test_SkebDownloader(self):
        skeb_url = SkebURL.create("https://skeb.jp/@author1/works/1")
        source_list = MagicMock(spec=SkebSourceList)
        save_directory_path = SkebSaveDirectoryPath.create(skeb_url, self.base_path)
        session = MagicMock(spec=SkebSession)
        dl_file_pathlist = []
        downloader = SkebDownloader(skeb_url, source_list, save_directory_path, session)

        self.assertEqual(skeb_url, downloader.skeb_url)
        self.assertEqual(source_list, downloader.source_list)
        self.assertEqual(save_directory_path, downloader.save_directory_path)
        self.assertEqual(session, downloader.session)
        self.assertEqual(dl_file_pathlist, downloader.dl_file_pathlist)

    def test_is_valid(self):
        skeb_url = SkebURL.create("https://skeb.jp/@author1/works/1")
        source_list = MagicMock(spec=SkebSourceList)
        save_directory_path = SkebSaveDirectoryPath.create(skeb_url, self.base_path)
        session = MagicMock(spec=SkebSession)
        dl_file_pathlist = []
        downloader = SkebDownloader(skeb_url, source_list, save_directory_path, session)

        self.assertTrue(downloader._is_valid())

        with self.assertRaises(TypeError):
            downloader = SkebDownloader("invalid_arg", source_list, save_directory_path, session)
        with self.assertRaises(TypeError):
            downloader = SkebDownloader(skeb_url, "invalid_arg", save_directory_path, session)
        with self.assertRaises(TypeError):
            downloader = SkebDownloader(skeb_url, source_list, "invalid_arg", session)
        with self.assertRaises(TypeError):
            downloader = SkebDownloader(skeb_url, source_list, save_directory_path, "invalid_arg")

    def test_download(self):
        with ExitStack() as stack:
            mock_logger_info = stack.enter_context(patch.object(logger, "info"))
            mock_sleep = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebDownloader.sleep"))
            mock_get = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebDownloader.requests.get"))

            def requests_get(url: str, headers: dict) -> MagicMock:
                r = MagicMock()
                r.content = url.encode()
                return r
            mock_get.side_effect = requests_get

            # 単一（1回目）
            skeb_url = SkebURL.create("https://skeb.jp/@author1/works/1")
            direct_url = URL("https://si.imgix.net/direct/@author1/works/1.webp")
            source_info_list = SkebSourceInfo(direct_url, Extension.WEBP)
            source_list = SkebSourceList([source_info_list])
            save_directory_path = SkebSaveDirectoryPath.create(skeb_url, self.base_path)
            session = MagicMock(spec=SkebSession)
            downloader = SkebDownloader(skeb_url, source_list, save_directory_path, session)

            actual = downloader.download()
            expect = DownloadResult.SUCCESS
            self.assertEqual(expect, actual)

            author_name = skeb_url.author_name
            work_id = skeb_url.work_id
            sd_path = Path(save_directory_path.path)
            url: URL = source_list[0].url
            src_ext: Extension = source_list[0].extension
            file_name = SaveFilename.create(author_name, work_id, -1, src_ext).name
            dst_path = sd_path.parent / file_name
            self.assertTrue(dst_path.is_file())
            self.assertEqual([dst_path], downloader.dl_file_pathlist)
            mock_get.assert_called_once_with(url.original_url, headers=downloader.session.headers)
            mock_get.reset_mock()

            # 単一（2回目）
            actual = downloader.download()
            expect = DownloadResult.PASSED
            self.assertEqual(expect, actual)
            mock_get.assert_not_called()
            mock_get.reset_mock()

            # 単一（小説作品）
            skeb_url = SkebURL.create("https://skeb.jp/@author1/works/2")
            direct_url = URL("https://si.imgix.net/direct/@author1/works/2.txt?p=dummy_main_text")
            source_info_list = SkebSourceInfo(direct_url, Extension.TXT)
            source_list = SkebSourceList([source_info_list])
            save_directory_path = SkebSaveDirectoryPath.create(skeb_url, self.base_path)
            session = MagicMock(spec=SkebSession)
            downloader = SkebDownloader(skeb_url, source_list, save_directory_path, session)

            actual = downloader.download()
            expect = DownloadResult.SUCCESS
            self.assertEqual(expect, actual)

            author_name = skeb_url.author_name
            work_id = skeb_url.work_id
            sd_path = Path(save_directory_path.path)
            url: URL = source_list[0].url
            src_ext: Extension = source_list[0].extension
            file_name = SaveFilename.create(author_name, work_id, -1, src_ext).name
            dst_path = sd_path.parent / file_name
            self.assertTrue(dst_path.is_file())
            self.assertEqual([dst_path], downloader.dl_file_pathlist)
            with dst_path.open("r") as fin:
                actual = fin.read()
                expect = "dummy_main_text"
                self.assertEqual(expect, actual)
            mock_get.assert_not_called()
            mock_get.reset_mock()

            # 複数作品（1回目）
            skeb_url = SkebURL.create("https://skeb.jp/@author1/works/3")
            direct_url = "https://si.imgix.net/direct/@author1/works/{}.webp"
            source_info_list = [
                SkebSourceInfo(URL(direct_url.format(i)), Extension.WEBP)
                for i in range(15)
            ]
            source_list = SkebSourceList(source_info_list)
            save_directory_path = SkebSaveDirectoryPath.create(skeb_url, self.base_path)
            session = MagicMock(spec=SkebSession)
            downloader = SkebDownloader(skeb_url, source_list, save_directory_path, session)

            actual = downloader.download()
            expect = DownloadResult.SUCCESS
            self.assertEqual(expect, actual)

            author_name = skeb_url.author_name
            work_id = skeb_url.work_id
            sd_path = Path(save_directory_path.path)
            expect_dl_file_pathlist = []
            expect_calls = []
            for i, src in enumerate(source_list):
                url: URL = src.url
                src_ext: Extension = src.extension
                file_name = SaveFilename.create(author_name, work_id, i, src_ext).name
                dst_path = sd_path / file_name
                self.assertTrue(dst_path.is_file())
                expect_dl_file_pathlist.append(dst_path)
                expect_calls.append(call(url.original_url, headers=downloader.session.headers))
            self.assertEqual(expect_dl_file_pathlist, downloader.dl_file_pathlist)
            self.assertEqual(expect_calls, mock_get.mock_calls)
            mock_get.reset_mock()

            # 複数作品（2回目）
            actual = downloader.download()
            expect = DownloadResult.PASSED
            self.assertEqual(expect, actual)
            mock_get.assert_not_called()
            mock_get.reset_mock()

            # エラー
            downloader = SkebDownloader(skeb_url, SkebSourceList([]), save_directory_path, session)
            with self.assertRaises(ValueError):
                actual = downloader.download()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
