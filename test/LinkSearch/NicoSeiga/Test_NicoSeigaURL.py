"""NicoSeigaURL のテスト

NicoSeigaURLを表すクラスをテストする
"""
import sys
import unittest
import urllib.parse

from media_gathering.LinkSearch.NicoSeiga.NicoSeigaURL import NicoSeigaURL


class TestNicoSeigaURL(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_NicoSeigaURL(self):
        # 正常系
        # クエリなし
        url_str = "https://seiga.nicovideo.jp/seiga/im12345678"
        url = NicoSeigaURL.create(url_str)
        self.assertEqual(url_str, url.non_query_url)
        self.assertEqual(url_str, url.original_url)

        # クエリなし
        url_str = "http://nico.ms/im12345678"
        url = NicoSeigaURL.create(url_str)
        self.assertEqual(url_str, url.non_query_url)
        self.assertEqual(url_str, url.original_url)

        # クエリ付き
        url_str = "https://seiga.nicovideo.jp/seiga/im12345678?some_query=1"
        non_query_url = urllib.parse.urlunparse(
            urllib.parse.urlparse(str(url_str))._replace(query=None, fragment=None)
        )
        url = NicoSeigaURL.create(url_str)
        self.assertEqual(non_query_url, url.non_query_url)
        self.assertEqual(url_str, url.original_url)

        # 異常系
        # NicoSeigaURLアドレスでない
        with self.assertRaises(ValueError):
            url_str = "https://www.google.co.jp/"
            url = NicoSeigaURL.create(url_str)

    def test_is_valid(self):
        url_str = "https://seiga.nicovideo.jp/seiga/im12345678"
        self.assertEqual(True, NicoSeigaURL.is_valid(url_str))

        url_str = "http://nico.ms/im12345678"
        self.assertEqual(True, NicoSeigaURL.is_valid(url_str))

        url_str = "https://www.google.co.jp/"
        self.assertEqual(False, NicoSeigaURL.is_valid(url_str))


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
