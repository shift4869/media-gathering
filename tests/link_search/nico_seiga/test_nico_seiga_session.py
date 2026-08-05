import sys
import unittest
from unittest.mock import MagicMock, patch

import httpx

from media_gathering.link_search.nico_seiga.authorid import Authorid
from media_gathering.link_search.nico_seiga.authorname import Authorname
from media_gathering.link_search.nico_seiga.illustid import Illustid
from media_gathering.link_search.nico_seiga.illustname import Illustname
from media_gathering.link_search.nico_seiga.nico_seiga_session import NicoSeigaSession
from media_gathering.link_search.url import URL


class TestNicoSeigaSession(unittest.TestCase):
    CONFIG = {"nico_seiga": {"user_session": "test_session"}}

    def setUp(self):
        self.session = NicoSeigaSession(self.CONFIG)

    def tearDown(self):
        self.session._session.close()

    def test_is_valid(self):
        """_sessionがhttpx.Clientであること"""
        self.assertTrue(self.session._is_valid())

    def test_cookie_is_registered(self):
        """user_session Cookieが設定されていること"""
        cookies = self.session._session.cookies

        self.assertEqual(
            cookies.get("user_session"),
            "test_session",
        )

    def test_get_illust_info(self):
        """イラスト情報XML取得"""
        mock_get = self.enterContext(patch.object(httpx.Client, "get"))

        xml = """
        <response>
            <illust>
                <user_id>12345</user_id>
                <title>test title</title>
            </illust>
        </response>
        """

        response = MagicMock()
        response.text = xml
        response.raise_for_status.return_value = None

        mock_get.return_value = response

        result = self.session._get_illust_info(Illustid(999))

        self.assertEqual(
            result["response"]["illust"]["user_id"],
            "12345",
        )

        mock_get.assert_called_once_with("http://seiga.nicovideo.jp/api/illust/info?id=999")

    def test_get_author_id(self):
        """作者ID取得"""
        mock_get = self.enterContext(patch.object(httpx.Client, "get"))

        xml = """
        <response>
            <illust>
                <user_id>54321</user_id>
            </illust>
        </response>
        """

        response = MagicMock()
        response.text = xml
        response.raise_for_status.return_value = None

        mock_get.return_value = response

        result = self.session.get_author_id(Illustid(100))

        self.assertIsInstance(
            result,
            Authorid,
        )

        self.assertEqual(
            result.id,
            54321,
        )

    def test_get_author_name(self):
        """作者名取得"""
        mock_get = self.enterContext(patch.object(httpx.Client, "get"))

        xml = """
        <response>
            <user>
                <nickname>test_author</nickname>
            </user>
        </response>
        """

        response = MagicMock()
        response.text = xml
        response.raise_for_status.return_value = None

        mock_get.return_value = response

        result = self.session.get_author_name(Authorid(123))

        self.assertIsInstance(
            result,
            Authorname,
        )

        self.assertEqual(
            result.name,
            "test_author",
        )

    def test_get_illust_title(self):
        """タイトル取得"""
        mock_get = self.enterContext(patch.object(httpx.Client, "get"))

        xml = """
        <response>
            <illust>
                <title>sample title</title>
            </illust>
        </response>
        """

        response = MagicMock()
        response.text = xml
        response.raise_for_status.return_value = None

        mock_get.return_value = response

        result = self.session.get_illust_title(Illustid(100))

        self.assertIsInstance(
            result,
            Illustname,
        )

        self.assertEqual(
            result.name,
            "sample title",
        )

    def test_get_source_url(self):
        """画像直リンク取得"""
        mock_get = self.enterContext(patch.object(httpx.Client, "get"))

        html = """
        <html>
          <body>
            <div id="content">
              <div class="illust_view_big"
                   data-src="https://example.com/test.jpg">
              </div>
            </div>
          </body>
        </html>
        """

        response = MagicMock()
        response.text = html
        response.raise_for_status.return_value = None

        mock_get.return_value = response

        result = self.session.get_source_url(Illustid(123))

        self.assertIsInstance(
            result,
            URL,
        )

        self.assertEqual(
            result.original_url,
            "https://example.com/test.jpg",
        )

    def test_get_illust_binary(self):
        """画像バイナリ取得"""
        mock_get = self.enterContext(patch.object(httpx.Client, "get"))

        binary = b"\x89PNG\r\n"

        response = MagicMock()
        response.content = binary
        response.raise_for_status.return_value = None

        mock_get.return_value = response

        result = self.session.get_illust_binary(URL("https://example.com/test.png"))

        self.assertEqual(
            result,
            binary,
        )


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
