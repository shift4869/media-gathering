"""NijieCookie のテスト
"""
import sys
import unittest
from contextlib import ExitStack

import requests.cookies
from mock import MagicMock, call, patch

from PictureGathering.LinkSearch.Nijie.NijieCookie import NijieCookie


class TestNijieCookie(unittest.TestCase):
    def test_post_init(self):
        with ExitStack() as stack:
            mock_is_valid = stack.enter_context(patch("PictureGathering.LinkSearch.Nijie.NijieCookie.NijieCookie._is_valid"))
            nijie_cookie = NijieCookie(requests.cookies.RequestsCookieJar(), {"headers": "dummy_headers"})

            NIJIE_TOP_URL = "http://nijie.info/index.php"
            self.assertEqual(NIJIE_TOP_URL, nijie_cookie.NIJIE_TOP_URL)
            self.assertTrue(isinstance(nijie_cookie._cookies, requests.cookies.RequestsCookieJar))
            self.assertEqual({"headers": "dummy_headers"}, nijie_cookie._headers)
            mock_is_valid.assert_called_once_with()

    def test_is_valid(self):
        with ExitStack() as stack:
            mock_get = stack.enter_context(patch("PictureGathering.LinkSearch.Nijie.NijieCookie.requests.get"))
            NIJIE_TOP_URL = "http://nijie.info/index.php"
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.url = NIJIE_TOP_URL
            mock_res.text = "ニジエ - nijie"
            mock_get.side_effect = lambda url, headers, cookies: mock_res

            headers = {"headers": "dummy_headers"}
            cookies = requests.cookies.RequestsCookieJar()
            cookies.set(name="dummy_name", value="dummy_value")
            nijie_cookie = NijieCookie(cookies, headers)

            mock_get.assert_called_once_with(NIJIE_TOP_URL, headers=headers, cookies=cookies)
            r_calls = mock_res.mock_calls
            self.assertEqual(1, len(r_calls))
            self.assertEqual(call.raise_for_status(), r_calls[0])

            with self.assertRaises(ValueError):
                mock_res.status_code = 404
                nijie_cookie = NijieCookie(cookies, headers)

            with self.assertRaises(ValueError):
                cookies = requests.cookies.RequestsCookieJar()
                nijie_cookie = NijieCookie(cookies, headers)

            with self.assertRaises(TypeError):
                nijie_cookie = NijieCookie(cookies, "invalid_headers_type")

            with self.assertRaises(TypeError):
                nijie_cookie = NijieCookie("invalid_cookies_type", headers)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
