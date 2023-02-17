# coding: utf-8
import shutil
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

from mock import patch

from PictureGathering.noapi.LocalStorage import LocalStorage


class TestLocalStorage(unittest.TestCase):
    def setUp(self):
        self.TWITTER_LOCAL_STORAGE_PATH = "./test/config/twitter_localstorage.ini"
        self.slsp = Path(self.TWITTER_LOCAL_STORAGE_PATH)
        self.slsp.parent.mkdir(parents=True, exist_ok=True)
        LocalStorage.TWITTER_LOCAL_STORAGE_PATH = self.TWITTER_LOCAL_STORAGE_PATH

    def tearDown(self):
        if self.slsp.parent.exists():
            shutil.rmtree(self.slsp.parent)

    def get_dummy_local_storage(self):
        local_storage = ["dummy_name : dummy_value"]
        return local_storage

    def test_init(self):
        local_storage = self.get_dummy_local_storage()
        actual = LocalStorage(local_storage)
        expect = self.TWITTER_LOCAL_STORAGE_PATH
        self.assertEqual(expect, LocalStorage.TWITTER_LOCAL_STORAGE_PATH)
        self.assertEqual(local_storage, actual.local_storage)

        actual = LocalStorage([])
        expect = []
        self.assertEqual(expect, actual.local_storage)

        with self.assertRaises(ValueError):
            actual = LocalStorage(None)
        with self.assertRaises(TypeError):
            actual = LocalStorage("invalid args")

    def test_is_valid_local_storage(self):
        local_storage = self.get_dummy_local_storage()
        actual = LocalStorage(local_storage)
        self.assertTrue(actual._is_valid_local_storage())

        with ExitStack() as stack:
            mock_post_init = stack.enter_context(patch("PictureGathering.noapi.LocalStorage.LocalStorage.__post_init__"))
            actual = LocalStorage(["invalid_local_storage"])
            self.assertFalse(actual._is_valid_local_storage())

    def test_validate_line(self):
        local_storage = self.get_dummy_local_storage()
        for line in local_storage:
            actual = LocalStorage.validate_line(line)
            self.assertTrue(actual)
        actual = LocalStorage.validate_line("invalid_line")
        self.assertFalse(actual)

    def test_load(self):
        local_storage = self.get_dummy_local_storage()

        with self.assertRaises(FileNotFoundError):
            actual = LocalStorage.load()

        with self.slsp.open(mode="w") as fout:
            for line in local_storage:
                fout.write(line + "\n")

        expect = [line + "\n" for line in local_storage]
        actual = LocalStorage.load()
        self.assertEqual(expect, actual)

        with self.slsp.open(mode="w") as fout:
            fout.write("invalid_local_storage_format")

        expect = []
        actual = LocalStorage.load()
        self.assertEqual(expect, actual)

    def test_save(self):
        local_storage = self.get_dummy_local_storage()

        expect = local_storage
        actual = LocalStorage.save(local_storage)
        self.assertEqual(expect, actual)
        self.assertTrue(self.slsp.exists())
        with self.slsp.open(mode="r") as fin:
            for line, ls_line in zip(fin, local_storage):
                expect = ls_line + "\n"
                actual = line
                self.assertEqual(expect, actual)
                self.assertTrue(LocalStorage.validate_line(actual))

        self.slsp.unlink(missing_ok=True)

        expect = []
        actual = LocalStorage.save([])
        self.assertEqual(expect, actual)
        self.assertTrue(self.slsp.exists())

        self.slsp.unlink(missing_ok=True)
        local_storage = ["invalid_local_storage"]
        with self.assertRaises(ValueError):
            actual = LocalStorage.save(local_storage)

    def test_create(self):
        return
        local_storage = self.get_dummy_local_storage()

        with self.assertRaises(FileNotFoundError):
            actual = LocalStorage.create()

        with self.slsp.open(mode="w") as fout:
            for c in cookies:
                fout.write(LocalStorage.cookie_to_string(c) + "\n")

        expect = LocalStorage(cookies)
        actual = LocalStorage.create()
        self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
