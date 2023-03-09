# coding: utf-8
import sys
import unittest
from pathlib import Path

from PictureGathering.LinkSearch.Skeb.SkebSaveDirectoryPath import SkebSaveDirectoryPath
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL


class TestSkebSaveDirectoryPath(unittest.TestCase):
    def test_SkebSaveDirectoryPath(self):
        base_path = Path("./test/LinkSearch/Skeb/PG_Skeb")
        sd_path = base_path / "./author1/001/"
        save_directory_path = SkebSaveDirectoryPath(sd_path)
        self.assertEqual(sd_path, save_directory_path.path)

    def test_is_valid(self):
        base_path = Path("./test/LinkSearch/Skeb/PG_Skeb")
        sd_path = base_path / "./author1/001/"
        save_directory_path = SkebSaveDirectoryPath(sd_path)
        self.assertTrue(save_directory_path._is_valid())

        with self.assertRaises(TypeError):
            save_directory_path = SkebSaveDirectoryPath("invalid argument")

    def test_create(self):
        skeb_url = SkebURL.create("https://skeb.jp/@author1/works/1?query=1")
        base_path = Path("./test/LinkSearch/Skeb/PG_Skeb")
        sd_path = base_path / "./author1/001/"

        save_directory_path = SkebSaveDirectoryPath.create(skeb_url, base_path)
        self.assertEqual(sd_path, save_directory_path.path)

        with self.assertRaises(TypeError):
            save_directory_path = SkebSaveDirectoryPath.create("invalid argument", base_path)
        with self.assertRaises(TypeError):
            save_directory_path = SkebSaveDirectoryPath.create(skeb_url, "invalid argument")


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
