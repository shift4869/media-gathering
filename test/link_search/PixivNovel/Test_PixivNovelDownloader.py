import re
import shutil
import sys
import unittest
from contextlib import ExitStack
from logging import WARNING, getLogger
from pathlib import Path

from bs4 import BeautifulSoup
from mock import MagicMock, call, patch
from pixivpy3 import AppPixivAPI

from media_gathering.link_search.PixivNovel.Authorid import Authorid
from media_gathering.link_search.PixivNovel.Authorname import Authorname
from media_gathering.link_search.PixivNovel.Novelid import Novelid
from media_gathering.link_search.PixivNovel.Noveltitle import Noveltitle
from media_gathering.link_search.PixivNovel.PixivNovelDownloader import DownloadResult, PixivNovelDownloader
from media_gathering.link_search.PixivNovel.PixivNovelSaveDirectoryPath import PixivNovelSaveDirectoryPath
from media_gathering.link_search.PixivNovel.PixivNovelURL import PixivNovelURL
from media_gathering.link_search.URL import URL

logger = getLogger("media_gathering.link_search.PixivNovel.PixivNovelDownloader")
logger.setLevel(WARNING)


class TestPixivNovelDownloader(unittest.TestCase):
    def mock_aapi(self) -> MagicMock:
        aapi = MagicMock(spec=AppPixivAPI)

        def novel_detail(novel_id: int):
            text = f"novel {novel_id}'s main text."
            r = MagicMock()
            work = MagicMock()
            work.user.name = "作者名1"
            work.user.id = 11111111
            work.id = novel_id
            work.title = "作品名1"
            work.create_date = "2023-03-07T00:00:00+09:00"
            work.page_count = 2
            work.text_length = len(text)
            work.caption = f"novel {novel_id}'s caption."
            r.novel = work
            r.error = False
            return r

        def novel_text(novel_id: int):
            r = MagicMock()
            r.novel_text = f"novel {novel_id}'s main text."
            r.error = False
            return r

        aapi.novel_detail.side_effect = novel_detail
        aapi.novel_text.side_effect = novel_text
        return aapi

    def test_DownloadResult(self):
        expect = ["SUCCESS", "PASSED"]
        actual = [r.name for r in DownloadResult]
        self.assertEqual(expect, actual)

    def test_PixivNovelDownloader(self):
        aapi = MagicMock(spec=AppPixivAPI)
        novel_url = MagicMock(spec=PixivNovelURL)
        save_directory_path = MagicMock(spec=PixivNovelSaveDirectoryPath)

        actual = PixivNovelDownloader(aapi, novel_url, save_directory_path)

        self.assertEqual(aapi, actual.aapi)
        self.assertEqual(novel_url, actual.novel_url)
        self.assertEqual(save_directory_path, actual.save_directory_path)

    def test_is_valid(self):
        aapi = MagicMock(spec=AppPixivAPI)
        novel_url = MagicMock(spec=PixivNovelURL)
        save_directory_path = MagicMock(spec=PixivNovelSaveDirectoryPath)

        actual = PixivNovelDownloader(aapi, novel_url, save_directory_path)

        self.assertTrue(actual._is_valid())

        with self.assertRaises(TypeError):
            actual = PixivNovelDownloader("invalid argument", novel_url, save_directory_path)
        with self.assertRaises(TypeError):
            actual = PixivNovelDownloader(aapi, "invalid argument", save_directory_path)
        with self.assertRaises(TypeError):
            actual = PixivNovelDownloader(aapi, novel_url, "invalid argument")

    def test_download(self):
        with ExitStack() as stack:
            mock_logger_info = stack.enter_context(patch.object(logger, "info"))

            source_url = "https://www.pixiv.net/novel/show.php?id=1234567&query=1"
            novel_url = PixivNovelURL(URL(source_url))
            novel_id = novel_url.novel_id.id

            base_path = Path("./test/link_search/PixivNovel")
            sd_path = base_path / "./作者名1(11111111)/作品名1(12345678)/"
            if sd_path.parent.is_dir():
                shutil.rmtree(sd_path.parent)
            save_directory_path = PixivNovelSaveDirectoryPath(sd_path)

            aapi = self.mock_aapi()

            actual = PixivNovelDownloader(aapi, novel_url, save_directory_path).download()
            expect = DownloadResult.SUCCESS
            self.assertIs(expect, actual)

            expect = [
                call.novel_detail(novel_id),
                call.novel_text(novel_id)
            ]
            self.assertEqual(expect, aapi.mock_calls)
            aapi.reset_mock()

            ext = ".txt"
            name = f"{sd_path.name}{ext}"
            with (sd_path.parent / name).open("r", encoding="utf-8") as fin:
                actual = fin.read()
            text = f"novel {novel_id}'s main text."
            info_tag = f"[info]\n" \
                       f"author:作者名1(11111111)\n" \
                       f"id:{novel_id}\n" \
                       f"title:作品名1\n" \
                       f"create_date:2023-03-07T00:00:00+09:00\n" \
                       f"page_count:2\n" \
                       f"text_length:{len(text)}\n"
            soup = BeautifulSoup(f"novel {novel_id}'s caption.", "html.parser")
            caption = f"[caption]\n" \
                      f"{soup.prettify()}\n"
            expect = info_tag + "\n" + caption + "\n[text]\n" + f"novel {novel_id}'s main text.\n"
            self.assertEqual(expect, actual)

            actual = PixivNovelDownloader(aapi, novel_url, save_directory_path).download()
            expect = DownloadResult.PASSED
            self.assertIs(expect, actual)
            aapi.reset_mock()

            with self.assertRaises(ValueError):
                r = MagicMock()
                r.error = True
                aapi.novel_text.side_effect = lambda novel_id: r
                actual = PixivNovelDownloader(aapi, novel_url, save_directory_path).download()

            with self.assertRaises(ValueError):
                r = MagicMock()
                r.error = True
                aapi.novel_detail.side_effect = lambda novel_id: r
                actual = PixivNovelDownloader(aapi, novel_url, save_directory_path).download()

            if sd_path.parent.is_dir():
                shutil.rmtree(sd_path.parent)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
