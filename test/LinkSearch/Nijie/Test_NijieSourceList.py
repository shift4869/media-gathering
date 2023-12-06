"""NijieSourceList のテスト
"""
import sys
import unittest

from media_gathering.LinkSearch.Nijie.NijieSourceList import NijieSourceList
from media_gathering.LinkSearch.URL import URL


class TestNijieSourceList(unittest.TestCase):
    def test_NijieSourceList(self):
        url_base = "https://nijie.info/view_popup.php?id={}"
        urls = [URL(url_base.format(i)) for i in range(10)]
        actual = NijieSourceList(urls)
        self.assertEqual(urls, actual._list)

        with self.assertRaises(ValueError):
            urls.append("invalid_URL")
            actual = NijieSourceList(urls)

        with self.assertRaises(TypeError):
            actual = NijieSourceList("invalid_argument")

    def test_create(self):
        url_base = "https://nijie.info/view_popup.php?id={}"
        urls = [URL(url_base.format(i)) for i in range(10)]
        expect = NijieSourceList(urls)
        actual = NijieSourceList.create(urls)
        self.assertEqual(expect, actual)

        urls = [url_base.format(i) for i in range(10)]
        actual = NijieSourceList.create(urls)
        self.assertEqual(expect, actual)

        expect = NijieSourceList([])
        actual = NijieSourceList.create([])
        self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            actual = NijieSourceList.create([-1])

        with self.assertRaises(TypeError):
            actual = NijieSourceList.create(-1)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
