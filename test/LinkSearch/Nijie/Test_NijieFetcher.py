"""NijieFetcher のテスト
"""
import shutil
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

import httpx
from mock import MagicMock, call, mock_open, patch

from PictureGathering.LinkSearch.Nijie.NijieFetcher import NijieFetcher
from PictureGathering.LinkSearch.Nijie.NijieURL import NijieURL
from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username


class TestNijieFetcher(unittest.TestCase):
    def setUp(self):
        self.TBP = Path("./test/LinkSearch/Nijie")

    def tearDown(self):
        rmdir = [p for p in self.TBP.glob("*") if p.is_dir() and p.name != "__pycache__"]
        for p in rmdir:
            shutil.rmtree(p)

    def _get_instance(self):
        with ExitStack() as stack:
            self.mock_login = stack.enter_context(patch("PictureGathering.LinkSearch.Nijie.NijieFetcher.NijieFetcher.login"))

            self.username = Username("ユーザー1_ID")
            self.password = Password("ユーザー1_PW")
            self.base_path = Path(self.TBP)

            self.fetcher = NijieFetcher(self.username, self.password, self.base_path)
            return self.fetcher

    def test_NijieFetcher(self):
        # 正常系
        actual = self._get_instance()
        self.assertTrue(hasattr(actual, "cookies"))
        self.mock_login.assert_called_once_with(self.username, self.password)
        self.assertTrue(hasattr(actual, "base_path"))
        self.assertEqual(self.base_path, actual.base_path)

        expect = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}
        self.assertEqual(expect, actual.HEADERS)
        expect = "./config/nijie_cookie.json"
        self.assertEqual(expect, actual.NIJIE_COOKIE_PATH)

        # 異常系
        with self.assertRaises(TypeError):
            actual = NijieFetcher("invalid args", self.password, self.base_path)
        with self.assertRaises(TypeError):
            actual = NijieFetcher(self.username, "invalid args", self.base_path)
        with self.assertRaises(TypeError):
            actual = NijieFetcher(self.username, self.password, "invalid args")

    def test_login(self):
        fetcher = self._get_instance()
        ncp = self.TBP / fetcher.NIJIE_COOKIE_PATH
        object.__setattr__(fetcher, "NIJIE_COOKIE_PATH", str(ncp))

        with ExitStack() as stack:
            mock_path_open = stack.enter_context(patch("PictureGathering.LinkSearch.Nijie.NijieFetcher.Path.open", mock_open()))
            mock_get = stack.enter_context(patch("PictureGathering.LinkSearch.Nijie.NijieFetcher.httpx.get"))
            mock_post = stack.enter_context(patch("PictureGathering.LinkSearch.Nijie.NijieFetcher.httpx.post"))
            mock_nijie_cookie = stack.enter_context(patch("PictureGathering.LinkSearch.Nijie.NijieFetcher.NijieCookie"))

            # クッキーが存在しない場合
            ncp = Path(fetcher.NIJIE_COOKIE_PATH)
            if ncp.exists():
                shutil.rmtree(ncp.parent)

            mock_get_res = MagicMock()
            mock_get_res.url = "https://nijie.info/for_login_url?url=for_login_url"
            mock_get.side_effect = lambda url, headers, follow_redirects: mock_get_res

            jar = httpx.Cookies()
            jar.set(
                name="dummy_name",
                value="dummy_value",
                path="/",
                domain=".dummy.domain",
            )
            mock_post_res = MagicMock()
            mock_post_res.cookies = jar
            mock_post.side_effect = lambda url, data, follow_redirects: mock_post_res

            mock_nijie_cookie.side_effect = lambda cookies, headers: "dummy_nijie_cookies"
            actual = fetcher.login(self.username, self.password)

            mock_get.assert_called_once_with(
                "https://nijie.info/age_jump.php?url=",
                headers=fetcher.HEADERS,
                follow_redirects=True
            )
            mock_get_res.raise_for_status.assert_called_once_with()

            payload = {
                "email": self.username.name,
                "password": self.password.password,
                "save": "on",
                "ticket": "",
                "url": "for_login_url"
            }
            mock_post.assert_called_once_with(
                "https://nijie.info/login_int.php",
                data=payload,
                follow_redirects=True
            )
            mock_post_res.raise_for_status.assert_called_once_with()
            mock_nijie_cookie.assert_called_once_with(jar, fetcher.HEADERS)

        with ExitStack() as stack:
            mock_read_bytes = stack.enter_context(patch("PictureGathering.LinkSearch.Nijie.NijieFetcher.Path.read_bytes"))
            mock_nijie_cookie = stack.enter_context(patch("PictureGathering.LinkSearch.Nijie.NijieFetcher.NijieCookie"))

            read_data = '''[{
                "name": "dummy_name",
                "value": "dummy_value",
                "expires": null,
                "path": "/",
                "domain": ".dummy.domain"
            }]'''
            mock_read_bytes.return_value = read_data
            # クッキーが既に存在している場合
            ncp = Path(fetcher.NIJIE_COOKIE_PATH)
            ncp.parent.mkdir(parents=True, exist_ok=True)
            ncp.touch()

            actual = fetcher.login(self.username, self.password)

            jar = httpx.Cookies()
            jar.set(
                name="dummy_name",
                value="dummy_value",
                path="/",
                domain=".dummy.domain",
            )
            mock_nijie_cookie.assert_called_once_with(jar, fetcher.HEADERS)

            if ncp.exists():
                shutil.rmtree(ncp.parent)

            with self.assertRaises(TypeError):
                actual = fetcher.login("invalid argument", self.password)

            with self.assertRaises(TypeError):
                actual = fetcher.login(self.username, "invalid argument")

    def test_is_target_url(self):
        fetcher = self._get_instance()

        # 正常系
        nijie_url = f"https://nijie.info/view.php?id=11111111"
        url = URL(nijie_url)
        actual = fetcher.is_target_url(url)
        self.assertTrue(actual)

        nijie_url = f"https://nijie.info/view_popup.php?id=11111111"
        url = URL(nijie_url)
        actual = fetcher.is_target_url(url)
        self.assertTrue(actual)

        # 異常系
        nijie_url = f"https://invalid.url/view_popup.php?id=11111111"
        url = URL(nijie_url)
        actual = fetcher.is_target_url(url)
        self.assertFalse(actual)

        with self.assertRaises(TypeError):
            actual = fetcher.is_target_url("invalid argument")

    def test_fetch(self):
        with ExitStack() as stack:
            mock_nijie_downloader = stack.enter_context(patch("PictureGathering.LinkSearch.Nijie.NijieFetcher.NijieDownloader"))

            fetcher = self._get_instance()
            nijie_url = f"https://nijie.info/view_popup.php?id=11111111"
            url = URL(nijie_url)

            actual = fetcher.fetch(url)

            f_calls = mock_nijie_downloader.mock_calls
            self.assertEqual(2, len(f_calls))
            self.assertEqual(
                call(NijieURL.create(url), fetcher.base_path, fetcher.cookies),
                f_calls[0]
            )
            self.assertEqual(call().download(), f_calls[1])

            with self.assertRaises(TypeError):
                actual = fetcher.fetch(-1)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
