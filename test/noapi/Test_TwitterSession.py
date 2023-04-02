# coding: utf-8
import asyncio
import re
import sys
import unittest
import warnings
from contextlib import ExitStack

import requests.cookies
from mock import AsyncMock, MagicMock, call, patch
from requests_html import HTML, AsyncHTMLSession

from PictureGathering.noapi.Cookies import Cookies
from PictureGathering.noapi.LocalStorage import LocalStorage
from PictureGathering.noapi.Password import Password
from PictureGathering.noapi.TwitterSession import TwitterSession
from PictureGathering.noapi.Username import Username


class TestTwitterSession(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter("ignore", RuntimeWarning)
        self.username: Username = Username("dummy_username")
        self.password: Password = Password("dummy_password")
        self.cookies = MagicMock(name="dummy_cookies", spec=Cookies)
        self.local_storage = MagicMock(name="dummy_local_storage", spec=LocalStorage)

        with ExitStack() as stack:
            mock_post_init = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.TwitterSession.__post_init__"))
            self.twitter_session = TwitterSession(self.username, self.password, self.cookies, self.local_storage)

    def test_init(self):
        expect = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}
        self.assertEqual(expect, self.twitter_session.HEADERS)
        expect = "https://twitter.com/"
        self.assertEqual(expect, self.twitter_session.TOP_URL)
        expect = "https://twitter.com/i/flow/login"
        self.assertEqual(expect, self.twitter_session.LOGIN_URL)
        expect = "https://twitter.com/{}/likes"
        self.assertEqual(expect, self.twitter_session.LIKES_URL_TEMPLATE)

    def test_post_init(self):
        with ExitStack() as stack:
            mock_is_valid_args = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.TwitterSession._is_valid_args"))
            mock_get_session = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.TwitterSession._get_session"))
            mock_is_valid_session = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.TwitterSession._is_valid_session"))

            self.twitter_session.__post_init__()

            mock_is_valid_args.assert_called_once()
            mock_get_session.assert_called_once()
            mock_is_valid_session.assert_called_once()

            self.assertTrue(isinstance(self.twitter_session.loop, asyncio.AbstractEventLoop))
            self.assertIsNotNone(self.twitter_session.session)

            mock_is_valid_session.return_value = False
            with self.assertRaises(ValueError):
                self.twitter_session.__post_init__()

    def test_is_valid_args(self):
        username: Username = Username("dummy_username")
        password: Password = Password("dummy_password")
        cookies = MagicMock(name="dummy_cookies", spec=Cookies)
        local_storage = MagicMock(name="dummy_local_storage", spec=LocalStorage)

        with ExitStack() as stack:
            mock_post_init = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.TwitterSession.__post_init__"))
            twitter_session = TwitterSession(username, password, cookies, local_storage)
            actual = twitter_session._is_valid_args()
            self.assertTrue(actual)

            with self.assertRaises(TypeError):
                twitter_session = TwitterSession("invalid_args", password, cookies, local_storage)
                actual = twitter_session._is_valid_args()
            with self.assertRaises(TypeError):
                twitter_session = TwitterSession(username, "invalid_args", cookies, local_storage)
                actual = twitter_session._is_valid_args()
            with self.assertRaises(TypeError):
                twitter_session = TwitterSession(username, password, "invalid_args", local_storage)
                actual = twitter_session._is_valid_args()
            with self.assertRaises(TypeError):
                twitter_session = TwitterSession(username, password, cookies, "invalid_args")
                actual = twitter_session._is_valid_args()

    def test_is_valid_session(self):
        r1 = MagicMock()
        r2 = MagicMock()
        html = f"""
            <div aria-label="アカウントメニュー">
            <img alt="{self.twitter_session.username.name}">
            </div>
        """
        r2.html = HTML(html=html)

        def coroutine_close(x):
            x.close()
            return r2

        r1.run_until_complete.side_effect = coroutine_close
        object.__setattr__(self.twitter_session, "loop", r1)
        actual = self.twitter_session._is_valid_session()
        self.assertTrue(actual)

        html = "invalid html"
        r2.html = HTML(html=html)
        r1.run_until_complete.side_effect = coroutine_close
        object.__setattr__(self.twitter_session, "loop", r1)
        actual = self.twitter_session._is_valid_session()
        self.assertFalse(actual)

    def test_get_session(self):
        with ExitStack() as stack:
            mock_post_init = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.TwitterSession.__post_init__"))
            mock_pyppeteer = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.pyppeteer", AsyncMock()))

            # cookies
            def get_dummy_cookies():
                cookies = requests.cookies.RequestsCookieJar()
                cookies.set(
                    "dummy_name",
                    "dummy_value",
                    expires=123456,
                    path="/",
                    domain=".",
                    secure=True,
                    rest={"HttpOnly": True}
                )
                return cookies
            cookies = Cookies(get_dummy_cookies())

            # local_storage
            def get_dummy_local_storage():
                local_storage = ["dummy_name : dummy_value"]
                return local_storage
            local_storage = LocalStorage(get_dummy_local_storage())

            self.twitter_session = TwitterSession(self.username, self.password, cookies, local_storage)

            loop = asyncio.new_event_loop()
            actual = loop.run_until_complete(
                self.twitter_session._get_session()
            )

            self.assertTrue(isinstance(actual, AsyncHTMLSession))
            self.assertIsNotNone(actual._browser)

            actual_mock_calls = mock_pyppeteer.mock_calls
            self.assertEqual(7, len(actual_mock_calls))
            self.assertEqual(call.launch(headless=True), actual_mock_calls[0])
            self.assertEqual(call.launch().newPage(), actual_mock_calls[1])
            url = self.twitter_session.TOP_URL
            self.assertEqual(call.launch().newPage().goto(url), actual_mock_calls[2])

            javascript_func1 = "localStorage.setItem('{}', '{}');"
            elements = re.split(" : |\n", local_storage.local_storage[0])
            key = elements[0]
            value = elements[1]
            script = javascript_func1.format(key, value)
            self.assertEqual(call.launch().newPage().evaluate(script, force_expr=True), actual_mock_calls[3])

            d = {}
            for c in cookies.cookies:
                d = {
                    "name": c.name,
                    "value": c.value,
                    "expires": c.expires,
                    "path": c.path,
                    "domain": c.domain,
                    "secure": bool(c.secure),
                    "httpOnly": bool(c._rest["HttpOnly"])
                }
            self.assertEqual(call.launch().newPage().setCookie(d), actual_mock_calls[4])

            url = self.twitter_session.LIKES_URL_TEMPLATE.format(self.twitter_session.username.name)
            self.assertEqual(call.launch().newPage().goto(url), actual_mock_calls[5])
            self.assertEqual(call.launch().newPage().waitForNavigation(), actual_mock_calls[6])

        pass

    def test_async_get(self):
        url = self.twitter_session.LIKES_URL_TEMPLATE.format(self.username.name)
        r = AsyncMock()
        object.__setattr__(self.twitter_session, "session", r)
        loop = asyncio.new_event_loop()
        actual = loop.run_until_complete(
            self.twitter_session._async_get(url)
        )
        actual_calls = r.get.mock_calls
        self.assertEqual(2, len(actual_calls))
        self.assertEqual(call(url, headers=self.twitter_session.headers, cookies=self.cookies.cookies), actual_calls[0])
        self.assertEqual(call().raise_for_status(), actual_calls[1])

    def test_get(self):
        url = self.twitter_session.LIKES_URL_TEMPLATE.format(self.username.name)
        with ExitStack() as stack:
            mock_async_get = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.TwitterSession._async_get"))

            loop = asyncio.new_event_loop()
            actual = loop.run_until_complete(
                self.twitter_session.get(url)
            )
            mock_async_get.assert_called_once_with(url)

    def test_prepare(self):
        with ExitStack() as stack:
            mock_async_get = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.TwitterSession._async_get"))

            loop = asyncio.new_event_loop()
            actual = loop.run_until_complete(
                self.twitter_session.prepare()
            )
            actual_calls = mock_async_get.mock_calls
            self.assertEqual(2, len(actual_calls))
            self.assertEqual(call(self.twitter_session.TOP_URL), actual_calls[0])
            self.assertEqual(call().html.arender(), actual_calls[1])

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
            mock_logger_info = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.logger.info"))
            mock_pyppeteer = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.pyppeteer", AsyncMock()))
            mock_local_storage = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.LocalStorage"))
            mock_cookies = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.Cookies"))
            mock_random = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.random.random"))
            FIXED_RANDOM_NUM = 1
            mock_random.return_value = FIXED_RANDOM_NUM

            loop = asyncio.new_event_loop()
            actual_cookies, actual_local_storage = loop.run_until_complete(
                TwitterSession.get_cookies_from_oauth(self.username, self.password)
            )

            login_url = TwitterSession.LOGIN_URL
            username_selector = 'input[name="text"]'
            username_click_selector = 'div[style="color: rgb(255, 255, 255);"]'
            password_selector = 'input[name="password"]'
            password_click_selector = 'div[style="color: rgb(255, 255, 255);"]'
            expect_calls = [
                call.launch(headless=True),
                call.launch().newPage(),
                call.launch().newPage().goto(login_url),
                call.launch().newPage().waitForNavigation(),
                call.launch().newPage().content(),
                call.launch().newPage().cookies(),
                call.launch().newPage().waitFor(FIXED_RANDOM_NUM * 3 * 1000),
                call.launch().newPage().type(username_selector, self.username.name),
                call.launch().newPage().waitFor(FIXED_RANDOM_NUM * 3 * 1000),
                call.launch().newPage().click(username_click_selector),
                call.launch().newPage().waitFor(FIXED_RANDOM_NUM * 3 * 1000),
                call.launch().newPage().type(password_selector, self.password.password),
                call.launch().newPage().waitFor(FIXED_RANDOM_NUM * 3 * 1000),
                call.launch().newPage().click(password_click_selector),
                call.launch().newPage().waitForNavigation(),
                call.launch().newPage().waitFor(3000),
                call.launch().newPage().content(),
                call.launch().newPage().cookies(),
                call.launch().newPage().evaluate(localstorage_get_js, force_expr=True),
                call.launch().newPage().evaluate().__bool__(),
                call.launch().newPage().cookies().__bool__(),
            ]
            actual_calls = mock_pyppeteer.mock_calls
            for expect, actual in zip(expect_calls, actual_calls, strict=True):
                self.assertEqual(expect, actual)

            mock_local_storage.save.assert_called_once()
            mock_cookies.save.assert_called_once()
            self.assertEqual(mock_cookies.create(), actual_cookies)
            self.assertEqual(mock_local_storage.create(), actual_local_storage)

    def test_create(self):
        with ExitStack() as stack:
            mock_logger_info = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.logger.info"))
            mock_cookies = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.Cookies"))
            mock_local_storage = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.LocalStorage"))
            mock_twitter_session = stack.enter_context(patch("PictureGathering.noapi.TwitterSession.TwitterSession"))

            actual = TwitterSession.create(self.username, self.password)
            mock_cookies.create.assert_called_once_with()
            mock_local_storage.create.assert_called_once_with()
            mock_twitter_session.assert_called_once_with(
                self.username, self.password,
                mock_cookies.create(),
                mock_local_storage.create()
            )
            expect = mock_twitter_session(self.username, self.password, mock_cookies.create(), mock_local_storage.create())
            self.assertEqual(expect, actual)

            mock_cookies.reset_mock()
            mock_local_storage.reset_mock()
            mock_twitter_session.reset_mock()

            dummy_cookies = "dummy_cookies"
            dummy_local_storage = "dummy_local_storage"

            async def get_cookies_from_oauth(username, password):
                return dummy_cookies, dummy_local_storage
            mock_cookies.create.side_effect = [Exception, FileNotFoundError, 0]
            mock_twitter_session.get_cookies_from_oauth.side_effect = get_cookies_from_oauth

            actual = TwitterSession.create(self.username, self.password)
            mock_cookies.create.assert_called_with()
            mock_local_storage.create.assert_not_called()
            mock_twitter_session.assert_called_once_with(
                self.username, self.password,
                dummy_cookies,
                dummy_local_storage
            )


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
