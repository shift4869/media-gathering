import re
import shutil
import sys
import unittest
from contextlib import ExitStack
from logging import WARNING, getLogger
from pathlib import Path

from mock import MagicMock, call, patch
from pixivpy3 import AppPixivAPI

from PictureGathering.LinkSearch.Pixiv.Authorid import Authorid
from PictureGathering.LinkSearch.Pixiv.Authorname import Authorname
from PictureGathering.LinkSearch.Pixiv.PixivUgoiraDownloader import DownloadResult, PixivUgoiraDownloader
from PictureGathering.LinkSearch.Pixiv.Workid import Workid
from PictureGathering.LinkSearch.Pixiv.Worktitle import Worktitle

logger = getLogger("PictureGathering.LinkSearch.Pixiv.PixivUgoiraDownloader")
logger.setLevel(WARNING)


class TestPixivUgoiraDownloader(unittest.TestCase):
    def mock_aapi(self, original_image_url, work_title, author_id, author_name, illust_type="ugoira", error_occur=False) -> MagicMock:
        aapi = MagicMock(spec=AppPixivAPI)
        illust = MagicMock()
        illust.user.name = author_name
        illust.user.id = author_id
        illust.title = work_title
        illust.type = illust_type
        illust.meta_single_page.original_image_url = original_image_url

        works = MagicMock()
        works.error = error_occur
        works.illust = illust

        metadata = MagicMock()
        metadata.ugoira_metadata.frames = [{"delay": 10} for i in range(10)]

        def download(url: str, path: str):
            name = url.rsplit("/", 1)[1]
            p = Path(path) / name
            with p.open("w") as fout:
                fout.write(url)

        aapi.illust_detail.side_effect = lambda work_id: works
        aapi.ugoira_metadata.side_effect = lambda work_id: metadata
        aapi.download.side_effect = download
        return aapi

    def test_DownloadResult(self):
        expect = ["SUCCESS", "PASSED"]
        actual = [r.name for r in DownloadResult]
        self.assertEqual(expect, actual)

    def test_PixivUgoiraDownloader(self):
        work_id = Workid(123456789)
        base_path = Path("./test/LinkSearch/Pixiv")
        aapi = MagicMock(spec=AppPixivAPI)

        actual = PixivUgoiraDownloader(aapi, work_id, base_path)

        self.assertEqual(aapi, actual.aapi)
        self.assertEqual(work_id, actual.work_id)
        self.assertEqual(base_path, actual.base_path)

    def test_is_valid(self):
        work_id = Workid(123456789)
        base_path = Path("./test/LinkSearch/Pixiv")
        aapi = MagicMock(spec=AppPixivAPI)

        actual = PixivUgoiraDownloader(aapi, work_id, base_path)

        self.assertTrue(actual._is_valid())

        with self.assertRaises(TypeError):
            actual = PixivUgoiraDownloader("invalid argument", work_id, base_path)
        with self.assertRaises(TypeError):
            actual = PixivUgoiraDownloader(aapi, "invalid argument", base_path)
        with self.assertRaises(TypeError):
            actual = PixivUgoiraDownloader(aapi, work_id, "invalid argument")

    def test_download(self):
        with ExitStack() as stack:
            mock_sleep = stack.enter_context(patch("PictureGathering.LinkSearch.Pixiv.PixivUgoiraDownloader.sleep"))
            mock_image = stack.enter_context(patch("PictureGathering.LinkSearch.Pixiv.PixivUgoiraDownloader.Image"))
            mock_logger_info = stack.enter_context(patch.object(logger, "info"))

            work_id = Workid(123456789)
            work_title = Worktitle("作品名1")
            author_id = Authorid(1234567)
            author_name = Authorname("作者名1")
            original_image_url = "https://www.pixiv.net/artworks/12346578_ugoira0.jpg"
            mock_aapi = self.mock_aapi(
                original_image_url,
                work_title.title,
                author_id.id,
                author_name.name
            )

            base_path = Path("./test/LinkSearch/Pixiv")
            sd_path = base_path / f"./{work_title.title}({work_id.id})/"
            if sd_path.is_dir():
                shutil.rmtree(sd_path)

            actual = PixivUgoiraDownloader(mock_aapi, work_id, base_path).download()
            expect = DownloadResult.SUCCESS
            self.assertIs(expect, actual)

            ugoira_url = original_image_url.rsplit("0", 1)
            frame_urls = [ugoira_url[0] + str(i) + ugoira_url[1] for i in range(10)]
            a_calls = mock_aapi.mock_calls
            self.assertEqual(12, len(a_calls))
            self.assertEqual(call.illust_detail(work_id.id), a_calls[0])
            self.assertEqual(call.ugoira_metadata(work_id.id), a_calls[1])
            for i in range(10):
                self.assertEqual(call.download(frame_urls[i], path=str(sd_path)), a_calls[2 + i])

            frames = []
            fr = [(sp.stat().st_mtime, str(sp)) for sp in sd_path.glob("*") if sp.is_file()]
            for mtime, path in sorted(fr, reverse=False):
                frames.append(path)
            name = f"{work_title.title}({work_id.id}).gif"
            image_list = []
            delays = [10 for _ in range(10)]
            i_calls = mock_image.mock_calls
            self.assertEqual(21, len(i_calls))
            self.assertEqual(call.open(frames[0]), i_calls[0])
            self.assertEqual(call.open().copy(), i_calls[1])
            index = 2
            for f in frames[1:]:
                self.assertEqual(call.open(f), i_calls[index])
                self.assertEqual(call.open().copy(), i_calls[index + 1])
                index = index + 2
            # first.save の呼び出し確認は省略

            # 2回目の呼び出し想定
            actual = PixivUgoiraDownloader(mock_aapi, work_id, base_path).download()
            expect = DownloadResult.PASSED
            self.assertIs(expect, actual)

            mock_aapi = self.mock_aapi(
                original_image_url,
                work_title.title,
                author_id.id,
                author_name.name,
                "not ugoira"
            )
            actual = PixivUgoiraDownloader(mock_aapi, work_id, base_path).download()
            expect = DownloadResult.PASSED
            self.assertIs(expect, actual)

            mock_aapi = self.mock_aapi(
                original_image_url,
                work_title.title,
                author_id.id,
                author_name.name,
                "ugoira",
                True
            )
            with self.assertRaises(ValueError):
                actual = PixivUgoiraDownloader(mock_aapi, work_id, base_path).download()

            if sd_path.is_dir():
                shutil.rmtree(sd_path)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
