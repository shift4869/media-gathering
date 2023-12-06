import re
import shutil
import sys
import unittest
from contextlib import ExitStack
from logging import WARNING, getLogger
from pathlib import Path

from mock import MagicMock, call, patch
from pixivpy3 import AppPixivAPI

from media_gathering.LinkSearch.Pixiv.PixivSaveDirectoryPath import PixivSaveDirectoryPath
from media_gathering.LinkSearch.Pixiv.PixivSourceList import PixivSourceList
from media_gathering.LinkSearch.Pixiv.PixivWorkDownloader import DownloadResult, PixivWorkDownloader
from media_gathering.LinkSearch.Pixiv.Workid import Workid
from media_gathering.LinkSearch.URL import URL

logger = getLogger("PictureGathering.LinkSearch.Pixiv.PixivWorkDownloader")
logger.setLevel(WARNING)


class TestPixivWorkDownloader(unittest.TestCase):
    def mock_aapi(self) -> MagicMock:
        aapi = MagicMock(spec=AppPixivAPI)

        def download(url: str, path: str, name: str):
            p = Path(path) / name
            with p.open("w") as fout:
                fout.write(url)

        aapi.download.side_effect = download
        return aapi

    def test_DownloadResult(self):
        expect = ["SUCCESS", "PASSED"]
        actual = [r.name for r in DownloadResult]
        self.assertEqual(expect, actual)

    def test_PixivWorkDownloader(self):
        aapi = MagicMock(spec=AppPixivAPI)
        source_list = MagicMock(spec=PixivSourceList)
        save_directory_path = MagicMock(spec=PixivSaveDirectoryPath)

        actual = PixivWorkDownloader(aapi, source_list, save_directory_path)

        self.assertEqual(aapi, actual.aapi)
        self.assertEqual(source_list, actual.source_list)
        self.assertEqual(save_directory_path, actual.save_directory_path)

    def test_is_valid(self):
        aapi = MagicMock(spec=AppPixivAPI)
        source_list = MagicMock(spec=PixivSourceList)
        save_directory_path = MagicMock(spec=PixivSaveDirectoryPath)

        actual = PixivWorkDownloader(aapi, source_list, save_directory_path)

        self.assertTrue(actual._is_valid())

        with self.assertRaises(TypeError):
            actual = PixivWorkDownloader("invalid argument", source_list, save_directory_path)
        with self.assertRaises(TypeError):
            actual = PixivWorkDownloader(aapi, "invalid argument", save_directory_path)
        with self.assertRaises(TypeError):
            actual = PixivWorkDownloader(aapi, source_list, "invalid argument")

    def test_download(self):
        with ExitStack() as stack:
            mock_sleep = stack.enter_context(patch("PictureGathering.LinkSearch.Pixiv.PixivWorkDownloader.sleep"))
            mock_ugoira = stack.enter_context(patch("PictureGathering.LinkSearch.Pixiv.PixivWorkDownloader.PixivUgoiraDownloader"))
            mock_logger_info = stack.enter_context(patch.object(logger, "info"))

            # 一枚絵
            source_url = "https://i.pximg.net/c/600x1200_90/img-master/img/2023/03/01/00/00/00/12345678_p0_master1200.jpg"
            source_list = PixivSourceList([URL(source_url)])

            base_path = Path("./test/LinkSearch/Pixiv")
            sd_path = base_path / "./作者名1(11111111)/作品名1(12345678)/"
            if sd_path.parent.is_dir():
                shutil.rmtree(sd_path.parent)
            save_directory_path = PixivSaveDirectoryPath(sd_path)

            aapi = self.mock_aapi()

            actual = PixivWorkDownloader(aapi, source_list, save_directory_path).download()
            expect = DownloadResult.SUCCESS
            self.assertIs(expect, actual)

            url = source_list[0].non_query_url
            ext = Path(url).suffix
            name = f"{sd_path.name}{ext}"
            work_id = Workid(int(re.findall(r'.*\(([0-9]*)\)$', sd_path.name)[0]))
            self.assertEqual(1, len(aapi.mock_calls))
            self.assertEqual(call.download(url, path=str(sd_path.parent), name=name), aapi.mock_calls[0])
            self.assertEqual(2, len(mock_ugoira.mock_calls))
            self.assertEqual(call(aapi, work_id, sd_path.parent), mock_ugoira.mock_calls[0])
            self.assertEqual(call().download(), mock_ugoira.mock_calls[1])
            aapi.reset_mock()
            mock_ugoira.reset_mock()

            actual = PixivWorkDownloader(aapi, source_list, save_directory_path).download()
            expect = DownloadResult.PASSED
            self.assertIs(expect, actual)
            aapi.assert_not_called()
            mock_ugoira.assert_not_called()

            if sd_path.parent.is_dir():
                shutil.rmtree(sd_path.parent)

            # 漫画形式
            source_url_base = "https://i.pximg.net/c/600x1200_90/img-master/img/2023/03/01/00/00/00/12345678_p{}_master1200.jpg"
            source_urls = [URL(source_url_base.format(i)) for i in range(10)]
            source_list = PixivSourceList(source_urls)

            actual = PixivWorkDownloader(aapi, source_list, save_directory_path).download()
            expect = DownloadResult.SUCCESS
            self.assertIs(expect, actual)

            self.assertEqual(len(source_list), len(aapi.mock_calls))
            for i, url in enumerate(source_list):
                ext = Path(url.non_query_url).suffix
                name = "{}_{:03}{}".format(sd_path.name, i + 1, ext)
                self.assertEqual(call.download(url.non_query_url, path=str(sd_path), name=name), aapi.mock_calls[i])
            mock_ugoira.assert_not_called()
            aapi.reset_mock()

            actual = PixivWorkDownloader(aapi, source_list, save_directory_path).download()
            expect = DownloadResult.PASSED
            self.assertIs(expect, actual)
            aapi.assert_not_called()
            mock_ugoira.assert_not_called()

            # 異常系
            with self.assertRaises(ValueError):
                actual = PixivWorkDownloader(aapi, PixivSourceList([]), save_directory_path).download()

            if sd_path.parent.is_dir():
                shutil.rmtree(sd_path.parent)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
