# coding: utf-8
"""IllustConvertor のテスト
"""
import sys
import unittest

from PictureGathering.LinkSearch.Skeb.IllustConvertor import IllustConvertor


class TestIllustConvertor(unittest.TestCase):
    def test_IllustConvertor(self):
        pass

    def test_convert(self):
        pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
