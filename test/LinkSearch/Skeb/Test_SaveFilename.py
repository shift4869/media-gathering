# coding: utf-8
"""SaveFilename のテスト
"""
import sys
import unittest

from PictureGathering.LinkSearch.Skeb.Authorname import Authorname
from PictureGathering.LinkSearch.Skeb.SaveFilename import Extension, SaveFilename
from PictureGathering.LinkSearch.Skeb.Workid import Workid


class TestSaveFilename(unittest.TestCase):
    def test_Extension(self):
        expect = [
            ("UNKNOWN", ".unknown"),
            ("WEBP", ".webp"),
            ("PNG", ".png"),
            ("MP4", ".mp4"),
            ("TXT", ".txt"),
        ]
        actual = [(r.name, r.value) for r in Extension]
        self.assertEqual(expect, actual)

    def test_SaveFilename(self):
        filename = "作者名1_123.webp"
        save_filename = SaveFilename(filename)
        self.assertEqual(filename, save_filename.name)

        filename = "作者名1_123_001.webp"
        save_filename = SaveFilename(filename)
        self.assertEqual(filename, save_filename.name)

    def test_is_valid(self):
        filename = "作者名1_123.webp"
        save_filename = SaveFilename(filename)
        self.assertTrue(save_filename._is_valid())

        with self.assertRaises(TypeError):
            save_filename = SaveFilename(-1)

    def test_create(self):
        def get_filename(name: Authorname, id: Workid, index: int = -1, extension: Extension = Extension.UNKNOWN):
            filename = ""
            if index == -1:
                filename = f"{author_name.name}_{work_id.id:03}{extension.value}"
            else:
                filename = f"{author_name.name}_{work_id.id:03}_{index:03}{extension.value}"
            return filename

        author_name = Authorname("作者名1")
        work_id = Workid(123)
        extension = Extension.WEBP

        for i in range(-1, 15):
            save_filename = SaveFilename.create(author_name, work_id, i, extension)
            actual = save_filename.name
            expect = get_filename(author_name, work_id, i, extension)
            self.assertEqual(expect, actual)

        with self.assertRaises(TypeError):
            save_filename = SaveFilename.create("invalid_arg", work_id, -1, extension)
        with self.assertRaises(TypeError):
            save_filename = SaveFilename.create(author_name, "invalid_arg", -1, extension)
        with self.assertRaises(TypeError):
            save_filename = SaveFilename.create(author_name, work_id, "invalid_arg", extension)
        with self.assertRaises(TypeError):
            save_filename = SaveFilename.create(author_name, work_id, -1, "invalid_arg")


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
