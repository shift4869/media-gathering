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

    def __GetNoRetweetedTweetSample(self) -> dict:
        """ツイートオブジェクトのサンプルを生成する（RTフラグなし）

        Returns:
            dict: ツイートオブジェクト（サンプル）
        """

        # 一意にするための乱数
        r = "{:0>5}".format(random.randint(0, 99999))
        tweet_json = f'''{{
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id": 12345,
            "user": {{
                "id_str": "12345_id_str_sample",
                "name": "shift_name_sample",
                "screen_name": "_shift4869_screen_name_sample"
            }},
            "text": "no-retweeted_tweet_text_sample_{r}",
            "retweeted": false
        }}'''
        tweet_s = json.loads(tweet_json)
        return tweet_s

    def __GetNoMediaTweetSample(self) -> dict:
        """ツイートオブジェクトのサンプルを生成する（メディアなし）

        Returns:
            dict: ツイートオブジェクト（サンプル）
        """

        # 一意にするための乱数
        r = "{:0>5}".format(random.randint(0, 99999))
        tweet_json = f'''{{
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id": 12345,
            "user": {{
                "id_str": "12345_id_str_sample",
                "name": "shift_name_sample",
                "screen_name": "_shift4869_screen_name_sample"
            }},
            "text": "no-media_tweet_text_sample_{r}",
            "retweeted": true
        }}'''
        tweet_s = json.loads(tweet_json)
        return tweet_s

    def __GetMediaTweetSample(self, img_url_s: str) -> dict:
        """ツイートオブジェクトのサンプルを生成する

        Args:
            img_url_s (str): 画像URLサンプル

        Returns:
            dict: ツイートオブジェクト（サンプル）
        """

        # 一意にするための乱数
        r1 = "{:0>5}".format(random.randint(0, 99999))
        r2 = "{:0>5}".format(random.randint(0, 99999))
        r = "{:0>5}".format(random.randint(0, 99999))
        tweet_json = f'''{{
            "extended_entities": {{
                "media": [{{
                    "type": "photo",
                    "media_url": "{img_url_s}_{r1}"
                }},
                {{
                    "type": "photo",
                    "media_url": "{img_url_s}_{r2}"
                }}
                ]
            }},
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id": 12345,
            "user": {{
                "id_str": "12345_id_str_sample",
                "name": "shift_name_sample",
                "screen_name": "_shift4869_screen_name_sample"
            }},
            "text": "media_tweet_text_sample_{r}",
            "retweeted": true
        }}'''
        tweet_s = json.loads(tweet_json)
        return tweet_s

    def __GetRetweetTweetSample(self, img_url_s: str) -> dict:
        """RTツイートオブジェクトのサンプルを生成する

        Args:
            img_url_s (str): 画像URLサンプル

        Returns:
            dict: ツイートオブジェクト（サンプル）
        """

        tweet_json = f'''{{
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id": 12345,
            "id_str": "12345_id_str_sample",
            "user": {{
                "id_str": "12345_id_str_sample",
                "name": "shift_name_sample",
                "screen_name": "_shift4869_screen_name_sample"
            }},
            "full_text": "retweet_tweet_text_sample",
            "retweeted": true
        }}'''
        tweet_s = json.loads(tweet_json)
        tweet_s["retweeted_status"] = self.__GetMediaTweetSample(img_url_s)
        tweet_s["retweeted_status"]["retweeted"] = True
        return tweet_s

    def __GetQuoteTweetSample(self, img_url_s: str) -> dict:
        """引用RTツイートオブジェクトのサンプルを生成する

        Args:
            img_url_s (str): 画像URLサンプル

        Returns:
            dict: ツイートオブジェクト（サンプル）
        """

        tweet_json = f'''{{
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id": 12345,
            "id_str": "12345_id_str_sample",
            "user": {{
                "id_str": "12345_id_str_sample",
                "name": "shift_name_sample",
                "screen_name": "_shift4869_screen_name_sample"
            }},
            "full_text": "quoted_tweet_text_sample",
            "retweeted": true,
            "is_quote_status": true
        }}'''
        tweet_s = json.loads(tweet_json)
        tweet_s["quoted_status"] = self.__GetMediaTweetSample(img_url_s)
        return tweet_s

    def __GetRetweetQuoteTweetSample(self, img_url_s: str) -> dict:
        """引用RTツイートをRTしたオブジェクトのサンプルを生成する

        Args:
            img_url_s (str): 画像URLサンプル

        Returns:
            dict: ツイートオブジェクト（サンプル）
        """

        tweet_s = self.__GetRetweetTweetSample(img_url_s)
        tweet_s["retweeted_status"] = self.__GetQuoteTweetSample(img_url_s)
        tweet_s["full_text"] = "retweet_quoted_tweet_text_sample"
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
        expect = int(expect_config["tweet_timeline"]["retweet_get_max_loop"])
        actual = rc.retweet_get_max_loop
        self.assertEqual(expect, actual)

        expect = os.path.abspath(expect_config["save_directory"]["save_retweet_path"])
        actual = rc.save_path
        self.assertEqual(expect, actual)

        self.assertIsNone(rc.max_id)
        self.assertEqual("RT", rc.type)

    def test_RetweetsGet(self):
        """RT取得機能をチェックする
        """

        rc = RetweetCrawler.RetweetCrawler()

        with ExitStack() as stack:
            mockdbrfc = stack.enter_context(patch("PictureGathering.DBController.DBController.DBRetweetFlagClear"))
            mockdbrfu = stack.enter_context(patch("PictureGathering.DBController.DBController.DBRetweetFlagUpdate"))
            mockapireq = stack.enter_context(patch("PictureGathering.Crawler.Crawler.TwitterAPIRequest"))
            
            # GetExistFilelistはrc本来のものを使うが結果を保持して比較するためにモックにしておく
            s_exist_filepaths = rc.GetExistFilelist()
            mockdgefl = stack.enter_context(patch("PictureGathering.Crawler.Crawler.GetExistFilelist"))
            mockdgefl.return_value = s_exist_filepaths

            # 既存ファイル一覧を取得する
            s_exist_filenames = []
            for s_exist_filepath in s_exist_filepaths:
                s_exist_filenames.append(os.path.basename(s_exist_filepath))
            if s_exist_filenames:
                exist_oldest_filename = s_exist_filenames[-1]
            else:
                exist_oldest_filename = ""

            # 取得ツイートモック作成
            s_media_url = "http://pbs.twimg.com/media/add_sample{}.jpg:orig"
            s_nrt_t = [self.__GetNoRetweetedTweetSample() for i in range(3)]
            s_nm_t = [self.__GetNoMediaTweetSample() for i in range(3)]
            s_rt_t = [self.__GetRetweetTweetSample(s_media_url.format(i)) for i in range(3)]
            s_quote_t = [self.__GetQuoteTweetSample(s_media_url.format(i)) for i in range(3)]
            s_rt_quote_t = [self.__GetRetweetQuoteTweetSample(s_media_url.format(i)) for i in range(3)]
            s_t = s_nrt_t + s_nm_t + s_rt_t + s_quote_t + s_rt_quote_t
            random.shuffle(s_t)
            s_se = [[s_t[0]],
                    [s_t[1], s_t[2]],
                    [s_t[3], s_t[4], s_t[5]],
                    [s_t[6], s_t[7], s_t[8]],
                    [s_t[9], s_t[10], s_t[11]],
                    [s_t[12], s_t[13], s_t[14]]]
            mockapireq.side_effect = s_se

            # 変数設定
            s_holding_file_num = 300
            s_retweet_get_max_loop = len(s_se) + 1
            rc.config["holding"]["holding_file_num"] = str(s_holding_file_num)
            rc.retweet_get_max_loop = s_retweet_get_max_loop

            # 実行
            actual = rc.RetweetsGet()
            mockdbrfc.assert_called_once_with()
            mockdbrfu.assert_called_once_with(s_exist_filenames, 1)
            mockdgefl.assert_called_once_with()
            mockapireq.assert_called()
            self.assertEqual(len(s_se), mockapireq.call_count)

            # 予想値取得
            expect = []
            for s_ti in s_t:
                rs = rc.GetMediaTweet(s_ti)
                for r in rs:
                    if r.get("extended_entities"):
                        expect.append(r)
            expect.reverse()

            self.assertEqual(len(expect), len(actual))
            self.assertEqual(expect, actual)

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

        with ExitStack() as stack:
            mocklogger = stack.enter_context(patch.object(logger, "info"))
            mockrtg = stack.enter_context(patch("PictureGathering.RetweetCrawler.RetweetCrawler.RetweetsGet"))
            mockimgsv = stack.enter_context(patch("PictureGathering.Crawler.Crawler.InterpretTweets"))
            mockshfol = stack.enter_context(patch("PictureGathering.Crawler.Crawler.ShrinkFolder"))
            mockeop = stack.enter_context(patch("PictureGathering.Crawler.Crawler.EndOfProcess"))
        
            s_holding_file_num = 300
            s_media_url_list = ["http://pbs.twimg.com/media/sample{0}.jpg:orig".format(i) for i in range(6)]
            s_retweet_tweet_list = [self.__GetMediaTweetSample(s_media_url_list[i]) for i in range(6)]

            mockrtg.return_value = s_retweet_tweet_list

            rc.config["holding"]["holding_file_num"] = str(s_holding_file_num)
            res = rc.Crawl()

            # 返り値チェック
            self.assertEqual(0, res)

            # 各関数が想定通りの引数で呼び出されたことを確認する
            # print(mockrtg.call_args_list)
            # print(mockimgsv.call_args_list)
            expect = ()
            actual = mockrtg.call_args_list[0][0]
            self.assertEqual(expect, actual)

            expect = s_retweet_tweet_list
            actual = mockimgsv.call_args_list[0][0][0]
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
