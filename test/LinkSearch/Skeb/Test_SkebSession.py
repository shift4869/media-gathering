# coding: utf-8
import re
import shutil
import sys
import unittest
from pathlib import Path

from mock import MagicMock, mock_open, patch

from PictureGathering.LinkSearch.Skeb.Authorname import Authorname
from PictureGathering.LinkSearch.Skeb.SkebSaveDirectoryPath import SkebSaveDirectoryPath
from PictureGathering.LinkSearch.Skeb.SkebSession import SkebSession
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL


class TestSkebSession(unittest.TestCase):
    def test_SkebSession(self):
        pass

    def test_is_valid_args(self):
        pass

    def test_is_valid_session(self):
        pass

    def test_get_session(self):
        pass

    def test_async_get(self):
        pass

    def test_get(self):
        pass

    def test_get_cookies_from_oauth(self):
        pass

    def test_create(self):
        pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
