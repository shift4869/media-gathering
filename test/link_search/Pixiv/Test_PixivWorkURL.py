"""PixivWorkURL のテスト

PixivWorkURLを表すクラスをテストする
"""
import sys
import unittest
import urllib.parse

from media_gathering.link_search.Pixiv.PixivWorkURL import PixivWorkURL


class TestPixivWorkURL(unittest.TestCase):
    def test_PixivWorkURL(self):
        # 正常系
        # クエリなし
        url_str = "https://www.pixiv.net/artworks/86704541"
        url = PixivWorkURL.create(url_str)
        self.assertEqual(url_str, url.non_query_url)
        self.assertEqual(url_str, url.original_url)

        # クエリ付き
        url_str = "https://www.pixiv.net/artworks/86704541?some_query=1"
        non_query_url = urllib.parse.urlunparse(
            urllib.parse.urlparse(str(url_str))._replace(query=None, fragment=None)
        )
        url = PixivWorkURL.create(url_str)
        self.assertEqual(non_query_url, url.non_query_url)
        self.assertEqual(url_str, url.original_url)

        # 異常系
        # PixivWorkURLアドレスでない
        with self.assertRaises(ValueError):
            url_str = "https://www.google.co.jp/"
            url = PixivWorkURL.create(url_str)

    def test_is_valid(self):
        url_str = "https://www.pixiv.net/artworks/86704541"
        self.assertEqual(True, PixivWorkURL.is_valid(url_str))

        url_str = "https://www.google.co.jp/"
        self.assertEqual(False, PixivWorkURL.is_valid(url_str))


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
