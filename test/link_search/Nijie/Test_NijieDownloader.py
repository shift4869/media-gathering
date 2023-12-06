"""NijieDownloader のテスト
"""
import shutil
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

from mock import MagicMock, patch

from media_gathering.link_search.Nijie.NijieCookie import NijieCookie
from media_gathering.link_search.Nijie.NijieDownloader import DownloadResult, NijieDownloader
from media_gathering.link_search.Nijie.NijieURL import NijieURL


class TestNijieDownloader(unittest.TestCase):
    def setUp(self):
        self.TBP = Path("./test/link_search/Nijie")

    def tearDown(self):
        rmdir = [p for p in self.TBP.glob("*") if p.is_dir() and p.name != "__pycache__"]
        for p in rmdir:
            shutil.rmtree(p)

    def test_DownloadResult(self):
        expect = ["SUCCESS", "PASSED"]
        actual = [r.name for r in DownloadResult]
        self.assertEqual(expect, actual)

    def test_NijieDownloader(self):
        nijie_url = NijieURL.create("http://nijie.info/view_popup.php?id=12345678")
        base_path = Path(self.TBP)
        cookies = MagicMock(spec=NijieCookie)

        actual = NijieDownloader(nijie_url, base_path, cookies)

        self.assertEqual(nijie_url, actual.nijie_url)
        self.assertEqual(base_path, actual.base_path)
        self.assertEqual(cookies, actual.cookies)

    def test_is_valid(self):
        nijie_url = NijieURL.create("http://nijie.info/view_popup.php?id=12345678")
        base_path = Path(self.TBP)
        cookies = MagicMock(spec=NijieCookie)

        actual = NijieDownloader(nijie_url, base_path, cookies)

        self.assertTrue(actual._is_valid())

        with self.assertRaises(TypeError):
            actual = NijieDownloader("invalid argument", base_path, cookies)
        with self.assertRaises(TypeError):
            actual = NijieDownloader(nijie_url, "invalid argument", cookies)
        with self.assertRaises(TypeError):
            actual = NijieDownloader(nijie_url, base_path, "invalid argument")

    def test_download(self):
        with ExitStack() as stack:
            mock_session = stack.enter_context(patch("media_gathering.link_search.Nijie.NijieDownloader.httpx.Client"))
            mock_logger_info = stack.enter_context(patch("media_gathering.link_search.Nijie.NijieDownloader.logger.info"))
            mock_sleep = stack.enter_context(patch("media_gathering.link_search.Nijie.NijieDownloader.sleep"))

            work_id = 10000000

            mock_res = MagicMock()
            mock_res.text = """
                <title>作品名1 | 作者名1 | ニジエ</title>
                <div id="img_filter" data-index='0'>
                <a href="javascript:void(0);">
                <img src="//pic.nijie.net/04/nijie/23m02/24/11111111/illust/sample_01.jpg" border="0" />
                </a>
                </div>
            """
            mock_res.content = b"dummy_content"
            mock_get = MagicMock()
            mock_get.get.side_effect = lambda url, headers, cookies: mock_res
            mock_session.side_effect = lambda follow_redirects, timeout, transport: mock_get

            nijie_url = NijieURL.create(f"http://nijie.info/view_popup.php?id={work_id}")
            base_path = Path(self.TBP)
            cookies = MagicMock(spec=NijieCookie)
            cookies._headers = {"dummy_headers": "dummy_headers"}
            cookies._cookies = {"dummy_cookies": "dummy_cookies"}

            # 一枚絵初回DL想定
            actual = NijieDownloader(nijie_url, base_path, cookies).download()
            expect = DownloadResult.SUCCESS
            self.assertIs(expect, actual)

            # 一枚絵2回目DL想定
            actual = NijieDownloader(nijie_url, base_path, cookies).download()
            expect = DownloadResult.PASSED
            self.assertIs(expect, actual)

            # 漫画形式初回DL想定
            work_id = 20000000
            nijie_url = NijieURL.create(f"http://nijie.info/view_popup.php?id={work_id}")
            mock_res.text = """
                <title>作品名2 | 作者名2 | ニジエ</title>
                <div id="img_filter" data-index='0'>
                <a href="javascript:void(0);">
                <img src="//pic.nijie.net/04/nijie/23m02/24/22222222/illust/sample_01.jpg" border="0" />
                </a></div>
                <div id="img_filter" data-index='0'>
                <a href="javascript:void(0);">
                <img src="//pic.nijie.net/04/nijie/23m02/24/22222222/illust/sample_02.jpg" border="0" />
                </a></div>
                <div id="img_filter" data-index='0'>
                <a href="javascript:void(0);">
                <img src="//pic.nijie.net/04/nijie/23m02/24/22222222/illust/sample_03.jpg" border="0" />
                </a></div>
                <div id="img_filter" data-index='0'>
                <a href="javascript:void(0);">
                <img src="//pic.nijie.net/04/nijie/23m02/24/22222222/illust/sample_04.jpg" border="0" />
                </a></div>
            """
            actual = NijieDownloader(nijie_url, base_path, cookies).download()
            expect = DownloadResult.SUCCESS
            self.assertIs(expect, actual)

            # 漫画形式2回目DL想定
            actual = NijieDownloader(nijie_url, base_path, cookies).download()
            expect = DownloadResult.PASSED
            self.assertIs(expect, actual)

            # 後始末


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
