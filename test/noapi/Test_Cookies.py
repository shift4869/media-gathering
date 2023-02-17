# coding: utf-8
import re
import shutil
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

import requests.cookies
from mock import patch

from PictureGathering.noapi.Cookies import Cookies


class TestCookies(unittest.TestCase):
    def setUp(self):
        self.TWITTER_COOKIE_PATH = "./test/config/twitter_cookie.ini"
        self.scp = Path(self.TWITTER_COOKIE_PATH)
        self.scp.parent.mkdir(parents=True, exist_ok=True)
        Cookies.TWITTER_COOKIE_PATH = self.TWITTER_COOKIE_PATH

    def tearDown(self):
        if self.scp.parent.exists():
            shutil.rmtree(self.scp.parent)

    def get_dummy_cookies(self):
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

    def test_init(self):
        cookies = self.get_dummy_cookies()
        actual = Cookies(cookies)
        expect = self.TWITTER_COOKIE_PATH
        self.assertEqual(expect, Cookies.TWITTER_COOKIE_PATH)
        expect = ["name", "value", "expires", "path", "domain", "httponly", "secure"]
        self.assertEqual(expect, Cookies.COOKIE_KEYS_LIST)
        expect = cookies
        self.assertEqual(expect, actual.cookies)

        with self.assertRaises(ValueError):
            actual = Cookies(None)
        with self.assertRaises(TypeError):
            actual = Cookies("invalid args")

    def test_is_valid_cookies(self):
        cookies = self.get_dummy_cookies()
        actual = Cookies(cookies)
        self.assertTrue(actual._is_valid_cookies())

        with ExitStack() as stack:
            mock_post_init = stack.enter_context(patch("PictureGathering.noapi.Cookies.Cookies.__post_init__"))
            mock_cookie_to_string = stack.enter_context(patch("PictureGathering.noapi.Cookies.Cookies.cookie_to_string"))
            mock_cookie_to_string.side_effect = lambda x: x
            actual = Cookies(["invalid args"])
            self.assertFalse(actual._is_valid_cookies())

    def test_cookies_list_to_requests_cookie_jar(self):
        cookies = self.get_dummy_cookies()
        cookies_list = []
        cookies_list.append(
            {
                "name": "dummy_name",
                "value": "dummy_value",
                "expires": 123456,
                "path": "/",
                "domain": ".",
                "secure": True,
                "httpOnly": True,
            }
        )
        expect = cookies
        actual = Cookies.cookies_list_to_requests_cookie_jar(cookies_list)
        self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = Cookies.cookies_list_to_requests_cookie_jar([])

        with self.assertRaises(TypeError):
            actual = Cookies.cookies_list_to_requests_cookie_jar(-1)

        with self.assertRaises(TypeError):
            actual = Cookies.cookies_list_to_requests_cookie_jar(["invalid_args"])

        with self.assertRaises(ValueError):
            actual = Cookies.cookies_list_to_requests_cookie_jar([{"invalid_dict": -1}])

    def test_cookie_to_string(self):
        cookies = self.get_dummy_cookies()
        for cookie in cookies:
            name = cookie.name
            value = cookie.value
            expires = cookie.expires
            path = cookie.path
            domain = cookie.domain
            httponly = cookie._rest["HttpOnly"]
            secure = cookie.secure
            expect = f'name="{name}", value="{value}", expires={expires}, path="{path}", domain="{domain}", httponly="{httponly}", secure="{secure}"'
            actual = Cookies.cookie_to_string(cookie)
            self.assertEqual(expect, actual)

    def test_validate_line(self):
        cookies = self.get_dummy_cookies()
        for cookie in cookies:
            line = Cookies.cookie_to_string(cookie)
            actual = Cookies.validate_line(line)
            self.assertTrue(actual)
        actual = Cookies.validate_line("invalid_line")
        self.assertFalse(actual)

    def test_validate_element(self):
        cookies = self.get_dummy_cookies()
        for cookie in cookies:
            line = Cookies.cookie_to_string(cookie)
            elements = re.split("[,\n]", line)
            for element in elements:
                actual = Cookies.validate_element(element)
                self.assertTrue(actual)
        actual = Cookies.validate_element("invalid_element")
        self.assertFalse(actual)

    def test_load(self):
        cookies = self.get_dummy_cookies()

        with self.assertRaises(FileNotFoundError):
            actual = Cookies.load()

        with self.scp.open(mode="w") as fout:
            for c in cookies:
                fout.write(Cookies.cookie_to_string(c) + "\n")

        expect = cookies
        actual = Cookies.load()
        self.assertEqual(expect, actual)

        with self.scp.open(mode="w") as fout:
            fout.write("invalid_cookies_format")

        expect = requests.cookies.RequestsCookieJar()
        actual = Cookies.load()
        self.assertEqual(expect, actual)

        with self.scp.open(mode="w") as fout:
            fout.write("invalid_key=invalid_value")

        with ExitStack() as stack:
            mock_validate_line = stack.enter_context(patch("PictureGathering.noapi.Cookies.Cookies.validate_line"))
            mock_validate_element = stack.enter_context(patch("PictureGathering.noapi.Cookies.Cookies.validate_element"))
            mock_validate_line.return_value = True
            mock_validate_element.return_value = True
            with self.assertRaises(ValueError):
                actual = Cookies.load()

    def test_save(self):
        cookies = self.get_dummy_cookies()

        expect = cookies
        actual = Cookies.save(cookies)
        self.assertEqual(expect, actual)
        self.assertTrue(self.scp.exists())
        with self.scp.open(mode="r") as fin:
            for line, cookie in zip(fin, cookies):
                expect = Cookies.cookie_to_string(cookie) + "\n"
                actual = line
                self.assertEqual(expect, actual)
                self.assertTrue(Cookies.validate_line(actual))

        self.scp.unlink(missing_ok=True)

        cookies_list = []
        cookies_list.append(
            {
                "name": "dummy_name",
                "value": "dummy_value",
                "expires": 123456,
                "path": "/",
                "domain": ".",
                "secure": True,
                "httpOnly": True,
            }
        )

        expect = Cookies.cookies_list_to_requests_cookie_jar(cookies_list)
        actual = Cookies.save(cookies_list)
        self.assertEqual(expect, actual)
        self.assertTrue(self.scp.exists())
        with self.scp.open(mode="r") as fin:
            for line, cookie in zip(fin, cookies):
                expect = Cookies.cookie_to_string(cookie) + "\n"
                actual = line
                self.assertEqual(expect, actual)
                self.assertTrue(Cookies.validate_line(actual))

    def test_create(self):
        cookies = self.get_dummy_cookies()

        with self.assertRaises(FileNotFoundError):
            actual = Cookies.create()

        with self.scp.open(mode="w") as fout:
            for c in cookies:
                fout.write(Cookies.cookie_to_string(c) + "\n")

        expect = Cookies(cookies)
        actual = Cookies.create()
        self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
