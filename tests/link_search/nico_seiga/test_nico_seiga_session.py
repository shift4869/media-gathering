"""NicoSeigaSession のテスト

NicoSeigaSessionを表すクラスをテストする
"""

import sys
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, call, patch

import httpx

from media_gathering.link_search.nico_seiga.authorid import Authorid
from media_gathering.link_search.nico_seiga.authorname import Authorname
from media_gathering.link_search.nico_seiga.illustid import Illustid
from media_gathering.link_search.nico_seiga.illustname import Illustname
from media_gathering.link_search.nico_seiga.nico_seiga_session import NicoSeigaSession
from media_gathering.link_search.password import Password
from media_gathering.link_search.url import URL
from media_gathering.link_search.username import Username


class TestNicoSeigaSession(unittest.TestCase):
    def _get_session(self):
        with ExitStack() as stack:
            mock_session = stack.enter_context(
                patch("media_gathering.link_search.nico_seiga.nico_seiga_session.httpx.Client")
            )
            mock_is_valid = stack.enter_context(
                patch("media_gathering.link_search.nico_seiga.nico_seiga_session.NicoSeigaSession._is_valid")
            )

            IMAGE_INFO_API_ENDPOINT_BASE = "http://seiga.nicovideo.jp/api/illust/info?id="
            USERNAME_API_ENDPOINT_BASE = "https://seiga.nicovideo.jp/api/user/info?id="
            IMAGE_SOUECE_API_ENDPOINT_BASE = "https://seiga.nicovideo.jp/image/source?id="

            def return_get_html(url, headers):
                r = MagicMock()
                if IMAGE_INFO_API_ENDPOINT_BASE in url:
                    r.text = "<image><user_id>1234567</user_id><title>title_1</title></image>"
                elif USERNAME_API_ENDPOINT_BASE in url:
                    r.text = "<user><nickname>author_name_1</nickname></user>"
                elif IMAGE_SOUECE_API_ENDPOINT_BASE in url:
                    r.text = '<div id="content"><div class="illust_view_big" data-src="http://source_url"></div></div>'
                else:
                    r.content = "sample image bytes".encode()

                return r

            return_get = MagicMock()
            return_get.get = return_get_html

            mock_session.side_effect = lambda follow_redirects, timeout, transport: return_get
            username = Username("dummy_name")
            password = Password("dummy_pass")
            return NicoSeigaSession(username, password)

    def test_NicoSeigaSession(self):
        session = self._get_session()

        AppleWebKit_header = "AppleWebKit/537.36 (KHTML, like Gecko)"
        chrome_header = "Chrome/88.0.4324.190 Safari/537.36"
        HEADERS = {"User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) {AppleWebKit_header} {chrome_header}"}
        LOGIN_ENDPOINT = "https://account.nicovideo.jp/api/v1/login?show_button_twitter=1&site=niconico&show_button_facebook=1&next_url=&mail_or_tel=1"
        IMAGE_INFO_API_ENDPOINT_BASE = "http://seiga.nicovideo.jp/api/illust/info?id="
        USERNAME_API_ENDPOINT_BASE = "https://seiga.nicovideo.jp/api/user/info?id="
        IMAGE_SOUECE_API_ENDPOINT_BASE = "https://seiga.nicovideo.jp/image/source?id="
        self.assertIsNotNone(session._session)
        self.assertEqual(HEADERS, session.HEADERS)
        self.assertEqual(LOGIN_ENDPOINT, session.LOGIN_ENDPOINT)
        self.assertEqual(IMAGE_INFO_API_ENDPOINT_BASE, session.IMAGE_INFO_API_ENDPOINT_BASE)
        self.assertEqual(USERNAME_API_ENDPOINT_BASE, session.USERNAME_API_ENDPOINT_BASE)
        self.assertEqual(IMAGE_SOUECE_API_ENDPOINT_BASE, session.IMAGE_SOUECE_API_ENDPOINT_BASE)

    def test_is_valid(self):
        session = self._get_session()

        object.__setattr__(session, "_session", httpx.Client())
        actual = session._is_valid()
        self.assertTrue(actual)

        with self.assertRaises(TypeError):
            object.__setattr__(session, "_session", None)
            actual = session._is_valid()

    def test_login(self):
        session = self._get_session()
        session_mock: MagicMock = session._session
        mock_calls = session_mock.mock_calls

        username = "dummy_name"
        password = "dummy_pass"
        params = {
            "mail_tel": username,
            "password": password,
        }
        self.assertEqual(call.post(session.LOGIN_ENDPOINT, data=params, headers=session.HEADERS), mock_calls[0])
        self.assertEqual(call.post().raise_for_status(), mock_calls[1])

    def test_get_author_id(self):
        session = self._get_session()
        illust_id = Illustid(12345678)

        expect = Authorid(1234567)
        actual = session.get_author_id(illust_id)
        self.assertEqual(expect, actual)

    def test_get_author_name(self):
        session = self._get_session()
        author_id = Authorid(1234567)

        expect = Authorname("author_name_1")
        actual = session.get_author_name(author_id)
        self.assertEqual(expect, actual)

    def test_get_illust_title(self):
        session = self._get_session()
        illust_id = Illustid(12345678)

        expect = Illustname("title_1")
        actual = session.get_illust_title(illust_id)
        self.assertEqual(expect, actual)

    def test_get_source_url(self):
        session = self._get_session()
        illust_id = Illustid(12345678)

        expect = URL("http://source_url")
        actual = session.get_source_url(illust_id)
        self.assertEqual(expect, actual)

    def test_get_illust_binary(self):
        session = self._get_session()
        source_url = URL("http://source_url")

        expect = "sample image bytes".encode()
        actual = session.get_illust_binary(source_url)
        self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
