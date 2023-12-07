"""NijieURL のテスト

NijieURLを表すクラスをテストする
"""
import sys
import unittest
import urllib.parse

from media_gathering.link_search.nijie.nijie_url import NijieURL
from media_gathering.link_search.nijie.workid import Workid
from media_gathering.link_search.url import URL


class TestNijieURL(unittest.TestCase):
    def test_NijieURL(self):
        # 正常系
        # 通常ページ
        url_str = "https://nijie.info/view.php?id=12345678"
        url = NijieURL.create(url_str)
        self.assertEqual("https://nijie.info/view.php", url.non_query_url)
        self.assertEqual(url_str, url.original_url)

        qs = urllib.parse.urlparse(url_str).query
        qd = urllib.parse.parse_qs(qs)
        work_id_num = int(qd.get("id", [-1])[0])
        expect = Workid(work_id_num)
        self.assertEqual(expect, url.work_id)

        # 詳細ページ
        url_str = "http://nijie.info/view_popup.php?id=12345678"
        url = NijieURL.create(url_str)
        self.assertEqual(url_str, url.original_url)

        # 異常系
        # NijieURLアドレスでない
        with self.assertRaises(ValueError):
            url_str = "https://www.google.co.jp/"
            url = NijieURL.create(url_str)

    def test_is_valid(self):
        url_str = "https://nijie.info/view.php?id=12345678"
        self.assertEqual(True, NijieURL.is_valid(url_str))

        url_str = "http://nijie.info/view_popup.php?id=12345678"
        self.assertEqual(True, NijieURL.is_valid(url_str))

        url_str = "https://www.google.co.jp/"
        self.assertEqual(False, NijieURL.is_valid(url_str))

    def test_create(self):
        url_str = "https://nijie.info/view.php?id=12345678"
        actual1 = NijieURL.create(url_str)
        url = URL(url_str)
        actual2 = NijieURL.create(url)
        self.assertEqual(actual1, actual2)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
