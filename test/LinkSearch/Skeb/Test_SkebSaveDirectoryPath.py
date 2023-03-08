# coding: utf-8
import re
import shutil
import sys
import unittest
from pathlib import Path

from mock import MagicMock, mock_open, patch

from PictureGathering.LinkSearch.Skeb.Authorname import Authorname
from PictureGathering.LinkSearch.Skeb.SkebSaveDirectoryPath import SkebSaveDirectoryPath
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL
from PictureGathering.LinkSearch.Skeb.SkebSaveDirectoryPath import SkebSaveDirectoryPath


class TestSkebSaveDirectoryPath(unittest.TestCase):
    def test_SkebSaveDirectoryPath(self):
        pass

    def test_is_valid(self):
        pass

    def test_create(self):
        pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
