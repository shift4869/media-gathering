# coding: utf-8
"""Favクローラーのテスト

FavCrawler.FavCrawler()の各種機能をテストする
"""

import os
import random
import sys
import unittest
from contextlib import ExitStack
from datetime import datetime
from logging import WARNING, getLogger

from mock import MagicMock, PropertyMock, patch

from PictureGathering import FavCrawler

logger = getLogger("root")
logger.setLevel(WARNING)


class TestCrawler(unittest.TestCase):
    """テストメインクラス
    """

    def setUp(self):
        pass

    def __GetMediaTweetSample(self, img_url_s):
        """ツイートオブジェクトのサンプルを生成する

        Args:
            img_url_s (str): 画像URLサンプル

        Returns:
            dict: ツイートオブジェクト（サンプル）
        """

        tweet_json = f'''{{
            "extended_entities": {{
                "media": [{{
                    "type": "photo",
                    "media_url": "{img_url_s}_1"
                }},
                {{
                    "type": "photo",
                    "media_url": "{img_url_s}_2"
                }}
                ]
            }},
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id_str": "12345_id_str_sample",
            "user": {{
                "id_str": "12345_id_str_sample",
                "name": "shift_name_sample",
                "screen_name": "_shift4869_screen_name_sample"
            }},
            "text": "tweet_text_sample"
        }}'''
        tweet_s = json.loads(tweet_json)
        return tweet_s

    def test_FavCrawlerInit(self):
        """FavCrawlerの初期状態のテスト
        """
        pass
        # self.assertEqual([], crawler.del_url_list)

    def test_FavTweetsGet(self):
        """Favリスト取得機能をチェックする
        """
        pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
