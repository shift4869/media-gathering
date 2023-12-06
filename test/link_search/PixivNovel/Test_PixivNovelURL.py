"""PixivNovelURL のテスト

PixivNovelURLを表すクラスをテストする
"""
import sys
import unittest
import urllib.parse

from media_gathering.link_search.PixivNovel.Novelid import Novelid
from media_gathering.link_search.PixivNovel.PixivNovelURL import PixivNovelURL


class TestPixivNovelURL(unittest.TestCase):
    def test_PixivNovelURL(self):
        # 正常系
        url_str = "https://www.pixiv.net/novel/show.php?id=12345678"
        non_query_url = urllib.parse.urlunparse(
            urllib.parse.urlparse(str(url_str))._replace(query=None, fragment=None)
        )
        url = PixivNovelURL.create(url_str)
        self.assertEqual(non_query_url, url.non_query_url)
        self.assertEqual(url_str, url.original_url)

        q = urllib.parse.urlparse(url_str).query
        qs = urllib.parse.parse_qs(q)
        novel_id_num = int(qs.get("id", [-1])[0])
        expect = Novelid(novel_id_num)
        self.assertEqual(expect, url.novel_id)

        # 異常系
        # PixivNovelURLアドレスでない
        with self.assertRaises(ValueError):
            url_str = "https://www.google.co.jp/"
            url = PixivNovelURL.create(url_str)

    def test_is_valid(self):
        url_str = "https://www.pixiv.net/novel/show.php?id=12345678"
        self.assertEqual(True, PixivNovelURL.is_valid(url_str))

        url_str = "https://www.google.co.jp/"
        self.assertEqual(False, PixivNovelURL.is_valid(url_str))


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
