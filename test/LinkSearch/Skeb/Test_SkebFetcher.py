# coding: utf-8
"""SkebFetcher のテスト
"""
import sys
import unittest

from PictureGathering.LinkSearch.Skeb.SkebFetcher import SkebFetcher


class TestSkebFetcher(unittest.TestCase):
    def test_SkebFetcher(self):
        pass

    def test_is_target_url(self):
        pass

    def test_fetch(self):
        pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
