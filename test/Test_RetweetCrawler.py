# coding: utf-8
"""RTクローラーのテスト

RetweetCrawler.RetweetCrawler()の各種機能をテストする
"""

import configparser
import freezegun
import json
import os
import random
import sys
import unittest
from contextlib import ExitStack
from datetime import datetime
from logging import WARNING, getLogger

from mock import MagicMock, PropertyMock, patch

from PictureGathering import RetweetCrawler

logger = getLogger("root")
logger.setLevel(WARNING)


class TestRetweetCrawler(unittest.TestCase):
    """RetweetCrawlerテストメインクラス
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

    def test_RetweetCrawlerInit(self):
        """RetweetCrawlerの初期状態のテスト
        
        Note:
            RetweetCrawler()内で初期化されたconfigと、configparser.ConfigParser()で取得したconfigを比較する
            どちらのconfigも設定元は"./config/config.ini"である
            RetweetCrawlerで利用する設定値のみテストする（基底クラスのテストは別ファイル）
        """

        rc = RetweetCrawler.RetweetCrawler()

        # expect_config読み込みテスト
        CONFIG_FILE_NAME = "./config/config.ini"
        expect_config = configparser.ConfigParser()
        self.assertTrue(os.path.exists(CONFIG_FILE_NAME))
        self.assertFalse(expect_config.read("ERROR_PATH" + CONFIG_FILE_NAME, encoding="utf8"))
        expect_config.read(CONFIG_FILE_NAME, encoding="utf8")

        # 存在しないキーを指定するテスト
        with self.assertRaises(KeyError):
            print(expect_config["ERROR_KEY1"]["ERROR_KEY2"])

        # 設定値比較
        expect = os.path.abspath(expect_config["save_directory"]["save_retweet_path"])
        actual = rc.save_path
        self.assertEqual(expect, actual)

        self.assertEqual("RT", rc.type)

    def test_RetweetsGet(self):
        """RT取得機能をチェックする
        """

        rc = RetweetCrawler.RetweetCrawler()
        pass

    def test_UpdateDBExistMark(self):
        """存在マーキング更新機能呼び出しをチェックする
        """

        rc = RetweetCrawler.RetweetCrawler()

        with ExitStack() as stack:
            mockdbcc = stack.enter_context(patch("PictureGathering.DBController.DBController.DBRetweetFlagClear"))
            mockdbcu = stack.enter_context(patch("PictureGathering.DBController.DBController.DBRetweetFlagUpdate"))

            s_add_img_filename = ["sample1.jpg", "sample2.jpg", "sample3.jpg"]
            rc.UpdateDBExistMark(s_add_img_filename)

            mockdbcc.assert_called_once_with()
            mockdbcu.assert_called_once_with(s_add_img_filename, 1)

    def test_GetVideoURL(self):
        """動画URL取得機能をチェックする
        """

        rc = RetweetCrawler.RetweetCrawler()

        def MakeVideoURL(filename):
            dic = {"url": "https://video.twimg.com/ext_tw_video/1139678486296031232/pu/vid/640x720/{0}?tag=10".format(filename)}
            return [dic]

        with ExitStack() as stack:
            mockdbcv = stack.enter_context(patch("PictureGathering.DBController.DBController.DBRetweetVideoURLSelect"))
            s_filename = "sample.mp4"

            # 正常系
            mockdbcv.side_effect = MakeVideoURL
            expect = MakeVideoURL(s_filename)[0]["url"]
            actual = rc.GetVideoURL(s_filename)
            self.assertEqual(expect, actual)

            # エラーケース
            mockdbcv.side_effect = None
            expect = ""
            actual = rc.GetVideoURL(s_filename)
            self.assertEqual(expect, actual)

    def test_MakeDoneMessage(self):
        """終了メッセージ作成機能をチェックする
        """

        rc = RetweetCrawler.RetweetCrawler()

        with freezegun.freeze_time("2020-10-28 15:32:58"):
            with ExitStack() as stack:
                s_add_url_list = ["http://pbs.twimg.com/media/add_sample{0}.jpg:orig".format(i) for i in range(5)]
                s_del_url_list = ["http://pbs.twimg.com/media/del_sample{0}.jpg:orig".format(i) for i in range(5)]
                s_pickup_url_list = random.sample(s_add_url_list, min(4, len(s_add_url_list)))
                mockrd = stack.enter_context(patch.object(RetweetCrawler.random, "sample", return_value=s_pickup_url_list))
                
                s_now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                s_done_msg = "Retweet PictureGathering run.\n"
                s_done_msg += s_now_str
                s_done_msg += " Process Done !!\n"
                s_done_msg += "add {0} new images. ".format(len(s_add_url_list))
                s_done_msg += "delete {0} old images.".format(len(s_del_url_list))
                s_done_msg += "\n"

                random_pickup = True
                if random_pickup:
                    # pickup_url_list = random.sample(self.add_url_list, min(4, len(self.add_url_list)))
                    for pickup_url in s_pickup_url_list:
                        pickup_url = str(pickup_url).replace(":orig", "")
                        s_done_msg += pickup_url + "\n"
                expect = s_done_msg

                rc.add_url_list = s_add_url_list
                rc.add_cnt = len(s_add_url_list)
                rc.del_url_list = s_del_url_list
                rc.del_cnt = len(s_del_url_list)
                actual = rc.MakeDoneMessage()

                self.assertEqual(expect, actual)

    def test_Crawl(self):
        """全体クロールの呼び出しをチェックする
        """

        rc = RetweetCrawler.RetweetCrawler()

        # with ExitStack() as stack:
        #   mocklogger = stack.enter_context(patch.object(logger, "info"))
        #   mockftg = stack.enter_context(patch("PictureGathering.RetweetCrawler.RetweetCrawler.FavTweetsGet"))
        #    mockimgsv = stack.enter_context(patch("PictureGathering.Crawler.Crawler.ImageSaver"))
        #    mockshfol = stack.enter_context(patch("PictureGathering.Crawler.Crawler.ShrinkFolder"))
        #   mockeop = stack.enter_context(patch("PictureGathering.Crawler.Crawler.EndOfProcess"))
        pass


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
