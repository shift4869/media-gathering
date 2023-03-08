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
from PictureGathering.LinkSearch.Skeb.SkebSourceInfo import SkebSourceInfo


class TestSkebSourceInfo(unittest.TestCase):
    def test_SkebSourceInfo(self):
        pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
