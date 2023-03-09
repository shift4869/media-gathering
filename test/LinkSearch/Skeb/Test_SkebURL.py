# coding: utf-8
"""SkebURL のテスト

SkebURLを表すクラスをテストする
"""
import sys
import unittest
import urllib.parse

from PictureGathering.LinkSearch.Skeb.Authorname import Authorname
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL
from PictureGathering.LinkSearch.Skeb.Workid import Workid
from PictureGathering.LinkSearch.URL import URL


class TestSkebURL(unittest.TestCase):
    def test_SkebURL(self):
        url_str = "https://skeb.jp/@author1/works/1?query=1"
        non_query_url = urllib.parse.urlunparse(
            urllib.parse.urlparse(str(url_str))._replace(query=None, fragment=None)
        )
        skeb_url = SkebURL.create(url_str)
        self.assertEqual(non_query_url, skeb_url.non_query_url)
        self.assertEqual(url_str, skeb_url.original_url)

        expect = Workid(1)
        self.assertEqual(expect, skeb_url.work_id)

        expect = Authorname("author1")
        self.assertEqual(expect, skeb_url.author_name)

        with self.assertRaises(ValueError):
            url_str = "https://www.google.co.jp/"
            skeb_url = SkebURL.create(url_str)

    def test_is_valid(self):
        url_str = "https://skeb.jp/@author1/works/1?query=1"
        self.assertTrue(SkebURL.is_valid(url_str))

        url_str = "https://www.google.co.jp/"
        self.assertFalse(SkebURL.is_valid(url_str))


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
