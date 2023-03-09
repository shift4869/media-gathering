# coding: utf-8
import sys
import unittest

from PictureGathering.LinkSearch.Skeb.SaveFilename import Extension
from PictureGathering.LinkSearch.Skeb.SkebSourceInfo import SkebSourceInfo
from PictureGathering.LinkSearch.URL import URL


class TestSkebSourceInfo(unittest.TestCase):
    def test_SkebSourceInfo(self):
        url = URL("https://skeb.jp/source_link/dummy01?query=1")
        ext = Extension.WEBP
        source_info = SkebSourceInfo(url, ext)
        self.assertEqual(url, source_info.url)
        self.assertEqual(ext, source_info.extension)

    def test_is_valid(self):
        url = URL("https://skeb.jp/source_link/dummy01?query=1")
        ext = Extension.WEBP
        source_info = SkebSourceInfo(url, ext)
        self.assertTrue(source_info._is_valid())

        with self.assertRaises(TypeError):
            source_info = SkebSourceInfo("invalid_arg", ext)
        with self.assertRaises(TypeError):
            source_info = SkebSourceInfo(url, "invalid_arg")


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
