# coding: utf-8
"""Favクローラーのテスト

FavCrawler.FavCrawler()の各種機能をテストする
"""

import configparser
import freezegun
import json
import random
import sys
import unittest
from contextlib import ExitStack
from datetime import datetime
from logging import WARNING, getLogger
from pathlib import Path

from mock import MagicMock, PropertyMock, patch

from PictureGathering import FavCrawler

logger = getLogger(__name__)
logger.setLevel(WARNING)


class TestFavCrawler(unittest.TestCase):
    """FavCrawlerテストメインクラス
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
        
        Note:
            FavCrawler()内で初期化されたconfigと、configparser.ConfigParser()で取得したconfigを比較する
            どちらのconfigも設定元は"./config/config.ini"である
            FavCrawlerで利用する設定値のみテストする（基底クラスのテストは別ファイル）
        """
        with ExitStack() as stack:
            mockLSR = stack.enter_context(patch("PictureGathering.Crawler.Crawler.LinkSearchRegister"))

            fc = FavCrawler.FavCrawler()

            # expect_config読み込みテスト
            CONFIG_FILE_NAME = "./config/config.ini"
            expect_config = configparser.ConfigParser()
            self.assertTrue(Path(CONFIG_FILE_NAME).is_file())
            self.assertFalse(expect_config.read("ERROR_PATH" + CONFIG_FILE_NAME, encoding="utf8"))
            expect_config.read(CONFIG_FILE_NAME, encoding="utf8")

            # 存在しないキーを指定するテスト
            with self.assertRaises(KeyError):
                print(expect_config["ERROR_KEY1"]["ERROR_KEY2"])

            # 設定値比較
            expect = Path(expect_config["save_directory"]["save_fav_path"])
            actual = fc.save_path
            self.assertEqual(expect, actual)

            self.assertEqual("Fav", fc.type)

    def test_FavTweetsGet(self):
        """Favリスト取得機能をチェックする
        """
        with ExitStack() as stack:
            mockapireq = stack.enter_context(patch("PictureGathering.Crawler.Crawler.TwitterAPIRequest"))
            mockLSR = stack.enter_context(patch("PictureGathering.Crawler.Crawler.LinkSearchRegister"))
            mocklogger = stack.enter_context(patch.object(logger, "error"))

            fc = FavCrawler.FavCrawler()

            # favorite
            page = 1
            fc.config["tweet_timeline"]["kind_of_timeline"] = "favorite"
            s_url = "https://api.twitter.com/1.1/favorites/list.json"
            s_params = {
                "screen_name": fc.user_name,
                "page": page,
                "count": fc.count,
                "include_entities": 1,
                "tweet_mode": "extended"
            }
            mockapireq.reset_mock()
            fc.FavTweetsGet(page)
            mockapireq.assert_called_once_with(s_url, s_params)
            
            # home
            page = 1
            fc.config["tweet_timeline"]["kind_of_timeline"] = "home"
            s_url = "https://api.twitter.com/1.1/statuses/home_timeline.json"
            s_params = {
                "count": fc.count,
                "include_entities": 1,
                "tweet_mode": "extended"
            }
            mockapireq.reset_mock()
            fc.FavTweetsGet(page)
            mockapireq.assert_called_once_with(s_url, s_params)

            # error
            fc.config["tweet_timeline"]["kind_of_timeline"] = "error_status"
            mockapireq.reset_mock()
            res = fc.FavTweetsGet(page)
            self.assertIsNone(res)
            mockapireq.assert_not_called()

    def test_UpdateDBExistMark(self):
        """存在マーキング更新機能呼び出しをチェックする
        """
        with ExitStack() as stack:
            mockdbcc = stack.enter_context(patch("PictureGathering.FavDBController.FavDBController.FlagClear"))
            mockdbcu = stack.enter_context(patch("PictureGathering.FavDBController.FavDBController.FlagUpdate"))
            mockLSR = stack.enter_context(patch("PictureGathering.Crawler.Crawler.LinkSearchRegister"))

            fc = FavCrawler.FavCrawler()

            s_add_img_filename = ["sample1.jpg", "sample2.jpg", "sample3.jpg"]
            fc.UpdateDBExistMark(s_add_img_filename)

            mockdbcc.assert_called_once_with()
            mockdbcu.assert_called_once_with(s_add_img_filename, 1)

    def test_GetMediaURL(self):
        """メディアURL取得機能をチェックする
        """
        def MakeMediaURL(filename):
            dic = {"url": "https://video.twimg.com/ext_tw_video/1139678486296031232/pu/vid/640x720/{0}?tag=10".format(filename)}
            return [dic]

        with ExitStack() as stack:
            mockdbcv = stack.enter_context(patch("PictureGathering.FavDBController.FavDBController.SelectFromMediaURL"))
            mockLSR = stack.enter_context(patch("PictureGathering.Crawler.Crawler.LinkSearchRegister"))

            fc = FavCrawler.FavCrawler()
            s_filename = "sample.mp4"

            # 正常系
            mockdbcv.side_effect = MakeMediaURL
            expect = MakeMediaURL(s_filename)[0]["url"]
            actual = fc.GetMediaURL(s_filename)
            self.assertEqual(expect, actual)

            # エラーケース
            mockdbcv.side_effect = None
            expect = ""
            actual = fc.GetMediaURL(s_filename)
            self.assertEqual(expect, actual)

    def test_MakeDoneMessage(self):
        """終了メッセージ作成機能をチェックする
        """
        with freezegun.freeze_time("2020-10-28 15:32:58"):
            with ExitStack() as stack:
                mockLSR = stack.enter_context(patch("PictureGathering.Crawler.Crawler.LinkSearchRegister"))

                fc = FavCrawler.FavCrawler()

                s_add_url_list = ["http://pbs.twimg.com/media/add_sample{0}.jpg:orig".format(i) for i in range(5)]
                s_del_url_list = ["http://pbs.twimg.com/media/del_sample{0}.jpg:orig".format(i) for i in range(5)]
                s_pickup_url_list = random.sample(s_add_url_list, min(4, len(s_add_url_list)))
                mockrd = stack.enter_context(patch.object(FavCrawler.random, "sample", return_value=s_pickup_url_list))
                
                s_now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                s_done_msg = "Fav PictureGathering run.\n"
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

                fc.add_url_list = s_add_url_list
                fc.add_cnt = len(s_add_url_list)
                fc.del_url_list = s_del_url_list
                fc.del_cnt = len(s_del_url_list)
                actual = fc.MakeDoneMessage()

                self.assertEqual(expect, actual)

    def test_Crawl(self):
        """全体クロールの呼び出しをチェックする
        """
        with ExitStack() as stack:
            mocklogger = stack.enter_context(patch.object(logger, "info"))
            mockftg = stack.enter_context(patch("PictureGathering.FavCrawler.FavCrawler.FavTweetsGet"))
            mockimgsv = stack.enter_context(patch("PictureGathering.Crawler.Crawler.InterpretTweets"))
            mockshfol = stack.enter_context(patch("PictureGathering.Crawler.Crawler.ShrinkFolder"))
            mockeop = stack.enter_context(patch("PictureGathering.Crawler.Crawler.EndOfProcess"))
            mockLSR = stack.enter_context(patch("PictureGathering.Crawler.Crawler.LinkSearchRegister"))

            fc = FavCrawler.FavCrawler()

            s_fav_get_max_loop = 3
            s_holding_file_num = 300
            s_media_url_list = ["http://pbs.twimg.com/media/sample{0}.jpg:orig".format(i) for i in range(6)]
            s_fav_tweet_list = [self.__GetMediaTweetSample(s_media_url_list[i]) for i in range(6)]

            # page = [1, 2, 3]に対して、return_value = [ツイート1コ, ツイート2コ, ツイート3コ]とする
            s_side_effect = [[s_fav_tweet_list[0]],
                             [s_fav_tweet_list[1], s_fav_tweet_list[2]],
                             [s_fav_tweet_list[3], s_fav_tweet_list[4], s_fav_tweet_list[5]]]
            mockftg.side_effect = s_side_effect

            fc.config["tweet_timeline"]["fav_get_max_loop"] = str(s_fav_get_max_loop)
            fc.config["holding"]["holding_file_num"] = str(s_holding_file_num)
            res = fc.Crawl()

            # 返り値チェック
            self.assertEqual(0, res)

            # 各関数が想定通りの引数で呼び出されたことを確認する
            # print(mockftg.call_args_list)
            # print(mockimgsv.call_args_list)
            for i in range(1, s_fav_get_max_loop + 1):
                expect = i
                actual = mockftg.call_args_list[i - 1][0][0]
                self.assertEqual(expect, actual)

                expect = s_side_effect[i - 1]
                actual = mockimgsv.call_args_list[i - 1][0][0]
                self.assertEqual(expect, actual)

            # print(mockshfol.call_args_list)
            expect = s_holding_file_num
            actual = mockshfol.call_args_list[0][0][0]
            self.assertEqual(expect, actual)

            # print(mockeop.call_args_list)
            expect = ()
            actual = mockeop.call_args_list[0][0]
            self.assertEqual(expect, actual)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
