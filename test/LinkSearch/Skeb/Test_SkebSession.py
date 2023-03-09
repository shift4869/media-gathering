# coding: utf-8
import asyncio
import re
import shutil
import sys
import unittest
from contextlib import ExitStack
from logging import WARNING, getLogger
from pathlib import Path

import requests.cookies
import requests.utils
from mock import AsyncMock, MagicMock, call, patch
from requests.exceptions import RequestException
from requests_html import AsyncHTMLSession

from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.Skeb.SkebSession import SkebSession
from PictureGathering.LinkSearch.Username import Username

logger = getLogger("PictureGathering.LinkSearch.Skeb.SkebSession")
logger.setLevel(WARNING)


class TestSkebSession(unittest.TestCase):
    def setUp(self) -> None:
        self.TBP = Path("./test/LinkSearch/Skeb/PG_Skeb")
        self.TBP.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.TBP.exists():
            shutil.rmtree(self.TBP)

    def get_instance(self) -> SkebSession:
        with ExitStack() as stack:
            self.mock_is_valid_args = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.SkebSession._is_valid_args"))
            self.mock_get_session = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.SkebSession._get_session"))
            self.mock_is_valid_session = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.SkebSession._is_valid_session"))

            local_storage = [
                "user : dummy_user",
                "token : dummy_token",
                "cache-sprite-plyr : dummy_cache",
                "blockingUsers : dummy_blockingUsers",
            ]
            cookies = requests.cookies.RequestsCookieJar()
            c_dict = {
                "expires": 12345678,
                "path": "/",
                "domain": ".",
                "secure": True,
                "rest": {"HttpOnly": True},
            }
            cookies.set("_interslice_session", "dummy", **c_dict)
            cookies.set("_ga", "dummy", **c_dict)
            skeb_session = SkebSession(cookies, local_storage)
            skeb_session.loop.close()

            SkebSession.SKEB_COOKIE_PATH = str(self.TBP / "skeb_cookie.ini")
            SkebSession.SKEB_LOCAL_STORAGE_PATH = str(self.TBP / "skeb_localstorage.ini")
            return skeb_session

    def get_mock_page(self) -> AsyncMock:
        mock_page = AsyncMock(name="mock_page")
        skeb_session = self.get_instance()

        async def querySelectorAll(selector):
            return [AsyncMock(), AsyncMock()]
        mock_page.querySelectorAll.side_effect = querySelectorAll

        async def content():
            return [AsyncMock(), AsyncMock()]
        mock_page.content.side_effect = content

        async def cookies():
            res = []
            for c in skeb_session.cookies:
                d = {
                    "name": c.name,
                    "value": c.value,
                    "expires": c.expires,
                    "path": c.path,
                    "domain": c.domain,
                    "secure": bool(c.secure),
                    "httpOnly": bool(c._rest["HttpOnly"])
                }
                res.append(d)
            return res
        mock_page.cookies.side_effect = cookies

        async def evaluate(js, force_expr):
            return skeb_session.local_storage
        mock_page.evaluate.side_effect = evaluate
        return mock_page

    def test_SkebSession(self):
        local_storage = [
            "user : dummy_user",
            "token : dummy_token",
            "cache-sprite-plyr : dummy_cache",
            "blockingUsers : dummy_blockingUsers",
        ]
        cookies = requests.cookies.RequestsCookieJar()
        cookies.set("_interslice_session", "dummy")
        cookies.set("_ga", "dummy")
        skeb_session = self.get_instance()

        self.assertEqual(cookies, skeb_session.cookies)
        self.assertEqual(local_storage, skeb_session.local_storage)
        self.assertTrue(hasattr(skeb_session, "loop"))
        self.assertTrue(hasattr(skeb_session, "session"))

        expect = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}
        self.assertEqual(expect, skeb_session.headers)
        expect = "https://skeb.jp/"
        self.assertEqual(expect, skeb_session.TOP_URL)
        expect = str(self.TBP / "skeb_cookie.ini")
        self.assertEqual(expect, skeb_session.SKEB_COOKIE_PATH)
        expect = str(self.TBP / "skeb_localstorage.ini")
        self.assertEqual(expect, skeb_session.SKEB_LOCAL_STORAGE_PATH)

        self.mock_is_valid_args.assert_called_once_with()
        self.mock_get_session.assert_called_once_with()
        self.mock_is_valid_session.assert_called_once_with()

    def test_is_valid_args(self):
        skeb_session = self.get_instance()
        self.assertTrue(skeb_session._is_valid_args())

        cookies = requests.cookies.RequestsCookieJar()
        object.__setattr__(skeb_session, "cookies", cookies)
        with self.assertRaises(ValueError):
            skeb_session._is_valid_args()

        local_storage = []
        object.__setattr__(skeb_session, "local_storage", local_storage)
        with self.assertRaises(ValueError):
            skeb_session._is_valid_args()

        local_storage = "invalid_local_storage"
        object.__setattr__(skeb_session, "local_storage", local_storage)
        with self.assertRaises(TypeError):
            skeb_session._is_valid_args()

        cookies = "invalid_cookies"
        object.__setattr__(skeb_session, "cookies", cookies)
        with self.assertRaises(TypeError):
            skeb_session._is_valid_args()

    def test_is_valid_session(self):
        with ExitStack() as stack:
            mock_get = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.SkebSession.get"))
            mock_response = MagicMock()
            mock_find = MagicMock()
            mock_find.attrs = {
                "href": "/account",
            }
            mock_find.full_text = "アカウント"
            mock_response.html.find.side_effect = lambda key: [mock_find]
            mock_get.side_effect = lambda url: mock_response

            skeb_session = self.get_instance()
            self.assertTrue(skeb_session._is_valid_session())
            mock_get.assert_called_once_with(skeb_session.TOP_URL)
            mock_response.raise_for_status.assert_called_once_with()
            mock_response.html.find.assert_called_once_with("a")

            mock_response.html.find.side_effect = lambda key: []
            self.assertFalse(skeb_session._is_valid_session())

            mock_response.raise_for_status.side_effect = RequestException
            with self.assertRaises(RequestException):
                skeb_session._is_valid_session()

    def test_get_session(self):
        with ExitStack() as stack:
            mock_async_html_session = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.AsyncHTMLSession", spec=AsyncHTMLSession))
            mock_pyppeteer = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.pyppeteer.launch"))
            mock_page = AsyncMock(name="mock_page")
            mock_pyppeteer.return_value.newPage.side_effect = lambda: mock_page

            skeb_session = self.get_instance()
            loop = asyncio.new_event_loop()
            actual = loop.run_until_complete(skeb_session._get_session())
            loop.close()

            mock_pyppeteer.assert_called_once_with(headless=True)
            mock_pyppeteer.return_value.newPage.assert_called_once_with()
            mock_async_html_session.assert_called_once_with()

            self.assertTrue(isinstance(actual, AsyncHTMLSession))
            self.assertTrue(hasattr(actual, "_browser"))
            self.assertEqual(mock_pyppeteer.return_value, actual._browser)

            expect = []
            expect.append(call.goto(skeb_session.TOP_URL))
            javascript_func1 = "localStorage.setItem('{}', '{}');"
            for line in skeb_session.local_storage:
                elements = re.split(" : |\n", line)
                key = elements[0]
                value = elements[1]
                expect.append(call.evaluate(javascript_func1.format(key, value)))
            for c in skeb_session.cookies:
                d = {
                    "name": c.name,
                    "value": c.value,
                    "expires": c.expires,
                    "path": c.path,
                    "domain": c.domain,
                    "secure": bool(c.secure),
                    "httpOnly": bool(c._rest["HttpOnly"])
                }
                expect.append(call.setCookie(d))
            self.assertEqual(expect, mock_page.mock_calls)

    def test_async_get(self):
        request_url_str = "https://skeb.jp/@author1/works/1?query=1"
        skeb_session = self.get_instance()
        self.mock_get_session.return_value.get.return_value.raise_for_status = lambda: 0

        loop = asyncio.new_event_loop()
        actual = loop.run_until_complete(skeb_session._async_get(request_url_str))
        loop.close()

        mock_get = self.mock_get_session.return_value.get
        expect = [
            call(request_url_str, headers=skeb_session.headers, cookies=skeb_session.cookies),
            # call().raise_for_status(),
            call().html.arender(sleep=2),
        ]
        self.assertEqual(expect, mock_get.mock_calls)
        self.assertEqual(mock_get.return_value, actual)

    def test_get(self):
        with ExitStack() as stack:
            mock_async_get = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.SkebSession._async_get"))

            request_url_str = "https://skeb.jp/@author1/works/1?query=1"
            skeb_session = self.get_instance()
            object.__setattr__(skeb_session, "loop", asyncio.new_event_loop())
            actual = skeb_session.get(request_url_str)
            skeb_session.loop.close()
            mock_async_get.assert_called_once_with(request_url_str)
            self.assertEqual(mock_async_get.return_value, actual)

    def test_get_cookies_from_oauth(self):
        localstorage_get_js = """
            function allStorage() {
                var values = [],
                    keys = Object.keys(localStorage),
                    i = keys.length;

                while ( i-- ) {
                    values.push( keys[i] + ' : ' + localStorage.getItem(keys[i]) );
                }

                return values;
            }
            allStorage()
        """
        with ExitStack() as stack:
            mock_logger_info = stack.enter_context(patch.object(logger, "info"))
            mock_random = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.random.random", return_value=1))
            mock_async_html_session = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.AsyncHTMLSession", spec=AsyncHTMLSession))
            mock_pyppeteer = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.pyppeteer.launch"))
            mock_page = self.get_mock_page()
            mock_pyppeteer.return_value.newPage.side_effect = lambda: mock_page

            skeb_session = self.get_instance()
            scp = Path(SkebSession.SKEB_COOKIE_PATH)
            slsp = Path(SkebSession.SKEB_LOCAL_STORAGE_PATH)
            self.assertFalse(scp.is_file())
            self.assertFalse(slsp.is_file())

            username = Username("dummy_username")
            password = Password("dummy_password")
            loop = asyncio.new_event_loop()
            actual = loop.run_until_complete(
                SkebSession.get_cookies_from_oauth(username, password)
            )
            loop.close()
            expect = (skeb_session.cookies, skeb_session.local_storage)
            self.assertEqual(expect, actual)

            expect = [
                call.goto(SkebSession.TOP_URL),
                call.waitForNavigation(),
                call.content(),
                call.cookies(),
                call.querySelectorAll('button[class="button is-twitter"]'),
                call.waitForNavigation(),
                call.content(),
                call.cookies(),
                call.waitFor(3000),
                call.click('input[id="allow"]'),
                call.waitForNavigation(),
                call.waitFor(3000),
                call.type('input[name="text"]', username.name),
                call.waitFor(3000),
                call.click('div[style="color: rgb(255, 255, 255);"]'),
                call.waitFor(3000),
                call.type('input[name="password"]', password.password),
                call.waitFor(3000),
                call.click('div[style="color: rgb(255, 255, 255);"]'),
                call.waitForNavigation(),
                call.waitForNavigation(),
                call.content(),
                call.cookies(),
                call.waitFor(3000),
                call.evaluate(localstorage_get_js, force_expr=True)
            ]
            self.assertEqual(expect, mock_page.mock_calls)

            self.assertTrue(scp.is_file())
            self.assertTrue(slsp.is_file())

    def test_create(self):
        with ExitStack() as stack:
            mock_logger_info = stack.enter_context(patch.object(logger, "info"))
            mock_is_valid_args = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.SkebSession._is_valid_args"))
            mock_get_session = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.SkebSession._get_session"))
            mock_is_valid_session = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.SkebSession._is_valid_session"))
            mock_get_cookies_from_oauth = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.SkebSession.SkebSession.get_cookies_from_oauth"))

            skeb_session = self.get_instance()

            async def get_cookies_from_oauth(username, password):
                return skeb_session.cookies, skeb_session.local_storage
            mock_get_cookies_from_oauth.side_effect = get_cookies_from_oauth

            # クッキーとローカルストレージのファイルが存在しない場合
            scp = Path(SkebSession.SKEB_COOKIE_PATH)
            slsp = Path(SkebSession.SKEB_LOCAL_STORAGE_PATH)
            self.assertFalse(scp.is_file())
            self.assertFalse(slsp.is_file())

            username = Username("dummy_username")
            password = Password("dummy_password")
            actual = SkebSession.create(username, password)
            expect = skeb_session
            self.assertEqual(expect, actual)
            mock_get_cookies_from_oauth.assert_called_once_with(username, password)
            mock_get_cookies_from_oauth.reset_mock()
            actual.loop.close()

            # クッキーとローカルストレージファイル作成
            # ローカルストレージ情報を保存
            with slsp.open("w") as fout:
                for ls in skeb_session.local_storage:
                    fout.write(ls + "\n")

            # クッキー情報を保存
            def cookie_to_string(c):
                name = c.name
                value = c.value
                expires = c.expires
                path = c.path
                domain = c.domain
                httponly = bool(c._rest["HttpOnly"])
                secure = bool(c.secure)
                return f'name="{name}", value="{value}", expires={expires}, path="{path}", domain="{domain}", httponly="{httponly}", secure="{secure}"'
            with scp.open(mode="w") as fout:
                for c in skeb_session.cookies:
                    fout.write(cookie_to_string(c) + "\n")

            # クッキーとローカルストレージのファイルが存在している場合
            actual = SkebSession.create(username, password)
            expect = skeb_session
            self.assertEqual(expect, actual)
            mock_get_cookies_from_oauth.assert_not_called()
            actual.loop.close()

            # クッキーとローカルストレージのファイルが存在しているが
            # 設定に数回失敗してから成功するパターン
            RETRY_NUM = 5
            mock_is_valid_session.side_effect = [
                i > (RETRY_NUM / 2) for i in range(RETRY_NUM)
            ]
            actual = SkebSession.create(username, password)
            expect = skeb_session
            self.assertEqual(expect, actual)
            mock_get_cookies_from_oauth.assert_not_called()
            actual.loop.close()

            # クッキーとローカルストレージのファイルが存在しているが
            # 設定に失敗、その後、認証して再取得が成功するパターン
            async def get_cookies_from_oauth(username, password):
                mock_is_valid_session.side_effect = lambda: True
                return skeb_session.cookies, skeb_session.local_storage
            mock_get_cookies_from_oauth.side_effect = get_cookies_from_oauth
            mock_is_valid_session.side_effect = lambda: False

            actual = SkebSession.create(username, password)
            expect = skeb_session
            self.assertEqual(expect, actual)
            mock_get_cookies_from_oauth.assert_called_once_with(username, password)
            mock_get_cookies_from_oauth.reset_mock()
            actual.loop.close()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
