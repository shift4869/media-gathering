# coding: utf-8
"""GoogleDrive APIのテスト

GoogleDrive APIの各種機能をテストする
設定ファイルとして ./config/credentials.json を使用する
各種機能、テストの中でもGoogleDrive APIを実際に呼び出してテストする
"""

import configparser
import json
import os
import random
import sys
import time
import unittest
import warnings
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from logging import WARNING, getLogger
from pathlib import Path
from typing import List

import requests
from apiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from mock import MagicMock, PropertyMock, patch
from requests_oauthlib import OAuth1Session

from PictureGathering import Crawler

logger = getLogger("root")
logger.setLevel(WARNING)


class TestGoogleDrive(unittest.TestCase):
    """テストメインクラス
    """

    def setUp(self):
        pass

    def test_UploadToGoogleDrive(self):
        """GoogleDriveへのアップロード機能をチェックする
        """
        pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
