# coding: utf-8
"""クローラーのテスト

Crawler.Crawler()の各種機能をテストする
実際に使用する派生クラスのテストについてはそれぞれのファイルに記述する
設定ファイルとして {CONFIG_FILE_NAME} にあるconfig.iniファイルを使用する
各種トークン類もAPI利用のテストのために使用する

Todo:
    * FavCrawler, RetweetCrawlerのテスト分離
    * PG_DB.dbのバックアップ機構
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
from datetime import datetime
from logging import WARNING, getLogger
from typing import List

import requests
from mock import MagicMock, PropertyMock, patch
from requests_oauthlib import OAuth1Session

from PictureGathering import Crawler

logger = getLogger("root")
logger.setLevel(WARNING)


class ConcreteCrawler(Crawler.Crawler):
    """テスト用の具体化クローラー

    Crawler.Crawler()の抽象クラスメソッドを最低限実装したテスト用の派生クラス

    Attributes:
        save_path (str): 画像保存先パス
        type (str): 継承先を表すタイプ識別
    """

    def __init__(self):
        super().__init__()
        self.save_path = os.getcwd()
        self.type = "Fav"  # Favorite取得としておく

    def UpdateDBExistMark(self, file_name):
        return "DBExistMark updated"

    def GetVideoURL(self, file_name):
        video_base_url = "https://video.twimg.com/ext_tw_video/1144527536388337664/pu/vid/626x882/{}"
        return video_base_url.format(file_name)

    def MakeDoneMessage(self):
        return "Crawler Test : done"

    def Crawl(self):
        return 0


class TestCrawler(unittest.TestCase):
    """テストメインクラス
    """

    def setUp(self):
        # requestsのResourceWarning抑制
        warnings.simplefilter("ignore", ResourceWarning)

    def __GetNoRetweetedTweetSample(self, img_url_s: str) -> dict:
        """ツイートオブジェクトのサンプルを生成する（RTフラグなし）

        Args:
            img_url_s (str): 画像URLサンプル

        Returns:
            dict: ツイートオブジェクト（サンプル）
        """

        # 一意にするための乱数
        r1 = "{:0>5}".format(random.randint(0, 99999))
        r2 = "{:0>5}".format(random.randint(0, 99999))
        r = "{:0>5}".format(random.randint(0, 99999))
        tweet_json = f"""{{
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
            "id": {int(r)},
            "id_str": "{r}",
            "user": {{
                "id_str": "12345_id_str_sample",
                "name": "shift_name_sample",
                "screen_name": "_shift4869_screen_name_sample"
            }},
            "text": "media_tweet_text_sample_{r}",
            "retweeted": false
        }}"""
        tweet_s = json.loads(tweet_json)
        return tweet_s

    def __GetNoMediaTweetSample(self) -> dict:
        """ツイートオブジェクトのサンプルを生成する（メディアなし、RTフラグあり）

        Returns:
            dict: ツイートオブジェクト（サンプル）
        """

        # 一意にするための乱数
        r = "{:0>5}".format(random.randint(0, 99999))
        tweet_json = f'''{{
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id": {int(r)},
            "id_str": "{r}",
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
            "id": {int(r)},
            "id_str": "{r}",
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

        r = "{:0>5}".format(random.randint(0, 99999))
        tweet_json = f'''{{
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id": {int(r)},
            "id_str": "{r}",
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

        r = "{:0>5}".format(random.randint(0, 99999))
        tweet_json = f'''{{
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id": {int(r)},
            "id_str": "{r}",
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

    def test_ConcreteCrawler(self):
        """ConcreteCrawlerのテスト
        """

        crawler = ConcreteCrawler()

        self.assertEqual("Fav", crawler.type)
        self.assertEqual("DBExistMark updated", crawler.UpdateDBExistMark(""))

        filename = "video_sample.mp4"
        video_base_url = "https://video.twimg.com/ext_tw_video/1144527536388337664/pu/vid/626x882/{}"
        self.assertEqual(video_base_url.format(filename), crawler.GetVideoURL(filename))
        self.assertEqual("Crawler Test : done", crawler.MakeDoneMessage())
        self.assertEqual(0, crawler.Crawl())

    def test_CrawlerInit(self):
        """Crawlerの初期状態のテスト

        Note:
            ConcreteCrawler()内で初期化されたconfigと、configparser.ConfigParser()で取得したconfigを比較する
            どちらのconfigも設定元は"./config/config.ini"である
            派生クラスで利用する設定値については別ファイルでテストする
        """

        crawler = ConcreteCrawler()

        # expect_config読み込みテスト
        CONFIG_FILE_NAME = "./config/config.ini"
        expect_config = configparser.ConfigParser()
        self.assertTrue(os.path.exists(CONFIG_FILE_NAME))
        self.assertFalse(
            expect_config.read("ERROR_PATH" + CONFIG_FILE_NAME, encoding="utf8")
        )
        expect_config.read(CONFIG_FILE_NAME, encoding="utf8")

        # 存在しないキーを指定するテスト
        with self.assertRaises(KeyError):
            print(expect_config["ERROR_KEY1"]["ERROR_KEY2"])

        # 設定値比較
        self.assertEqual(expect_config["twitter_token_keys"]["consumer_key"],
                         crawler.TW_CONSUMER_KEY)
        self.assertEqual(expect_config["twitter_token_keys"]["consumer_secret"],
                         crawler.TW_CONSUMER_SECRET)
        self.assertEqual(expect_config["twitter_token_keys"]["access_token"],
                         crawler.TW_ACCESS_TOKEN_KEY)
        self.assertEqual(expect_config["twitter_token_keys"]["access_token_secret"],
                         crawler.TW_ACCESS_TOKEN_SECRET)

        self.assertEqual(expect_config["line_token_keys"]["token_key"],
                         crawler.LN_TOKEN_KEY)

        self.assertEqual(expect_config["slack_webhook_url"]["webhook_url"],
                         crawler.SLACK_WEBHOOK_URL)

        self.assertEqual(expect_config["discord_webhook_url"]["webhook_url"],
                         crawler.DISCORD_WEBHOOK_URL)

        # self.assertEqual(os.path.abspath(expect_config["save_directory"]["save_fav_path"]),
        #                 crawler.save_path)
        # self.assertTrue(os.path.exists(crawler.save_path))
        # self.assertEqual(os.path.abspath(expect_config["save_directory"]["save_retweet_path"]),
        #                  crawler.save_retweet_path)
        # self.assertTrue(os.path.exists(crawler.save_retweet_path))

        self.assertEqual(expect_config["tweet_timeline"]["user_name"],
                         crawler.user_name)
        # self.assertEqual(int(expect_config["tweet_timeline"]["retweet_get_max_loop"]),
        #                  crawler.retweet_get_max_loop)
        # self.assertEqual(int(expect_config["tweet_timeline"]["fav_get_max_loop"]) + 1,
        #                  crawler.fav_get_max_loop)
        self.assertEqual(int(expect_config["tweet_timeline"]["count"]),
                         crawler.count)
        self.assertIn(crawler.config["tweet_timeline"]["kind_of_timeline"],
                      ["favorite", "home"])

        self.assertEqual(expect_config["timestamp"]["timestamp_created_at"],
                         crawler.config["timestamp"]["timestamp_created_at"])

        self.assertEqual(expect_config["notification"]["is_post_fav_done_reply"],
                         crawler.config["notification"]["is_post_fav_done_reply"])
        self.assertEqual(expect_config["notification"]["is_post_retweet_done_reply"],
                         crawler.config["notification"]["is_post_retweet_done_reply"])
        self.assertEqual(expect_config["notification"]["reply_to_user_name"],
                         crawler.config["notification"]["reply_to_user_name"])
        self.assertEqual(expect_config["notification"]["is_post_line_notify"],
                         crawler.config["notification"]["is_post_line_notify"])
        self.assertEqual(expect_config["notification"]["is_post_slack_notify"],
                         crawler.config["notification"]["is_post_slack_notify"])
        self.assertEqual(expect_config["notification"]["is_post_discord_notify"],
                         crawler.config["notification"]["is_post_discord_notify"])

        self.assertEqual(expect_config["holding"]["holding_file_num"],
                         crawler.config["holding"]["holding_file_num"])

        self.assertEqual(expect_config["processes"]["image_magick"],
                         crawler.config["processes"]["image_magick"])
        if crawler.config["processes"]["image_magick"] != "":
            self.assertTrue(os.path.exists(crawler.config["processes"]["image_magick"]))

        self.assertIsInstance(crawler.oath, OAuth1Session)

        self.assertEqual(0, crawler.add_cnt)
        self.assertEqual(0, crawler.del_cnt)
        self.assertEqual([], crawler.add_url_list)
        self.assertEqual([], crawler.del_url_list)

    def test_GetTwitterAPIResourceType(self):
        """使用するTwitterAPIのAPIリソースタイプ取得をチェックする
        """

        crawler = ConcreteCrawler()

        # リプライ先のユーザー情報を取得するAPI
        reply_user_name = crawler.config["notification"]["reply_to_user_name"]
        url = "https://api.twitter.com/1.1/users/show.json"
        params = {
            "screen_name": reply_user_name
        }
        self.assertEqual("users", crawler.GetTwitterAPIResourceType(url))

        # ふぁぼリスト取得API
        page = 1
        url = "https://api.twitter.com/1.1/favorites/list.json"
        params = {
            "screen_name": crawler.user_name,
            "page": page,
            "count": crawler.count,
            "include_entities": 1,
            "tweet_mode": "extended"
        }
        self.assertEqual("favorites", crawler.GetTwitterAPIResourceType(url))

        # 自分のタイムラインを取得するAPI（あまり使わない）
        url = "https://api.twitter.com/1.1/statuses/home_timeline.json"
        params = {
            "count": crawler.count,
            "include_entities": 1,
            "tweet_mode": "extended"
        }
        self.assertEqual("statuses", crawler.GetTwitterAPIResourceType(url))

        # 自分の最新ツイートを取得するAPI（ここからRTを抜き出す）
        max_id = -1
        url = "https://api.twitter.com/1.1/statuses/user_timeline.json"
        params = {
            "screen_name": crawler.user_name,
            "count": crawler.count,
            "max_id": max_id,
            "contributor_details": True,
            "include_rts": True,
            "tweet_mode": "extended"
        }
        self.assertEqual("statuses", crawler.GetTwitterAPIResourceType(url))

        # ツイートを削除するAPI
        url = "https://api.twitter.com/1.1/statuses/destroy/12345_id_str_sample.json"
        self.assertEqual("statuses", crawler.GetTwitterAPIResourceType(url))

        # レートリミットを取得するAPI
        # url = "https://api.twitter.com/1.1/application/rate_limit_status.json"
        # params = {
        #    "resources": self.GetTwitterAPIResourceType(url)
        # }

    def test_GetTwitterAPILimitContext(self):
        """Limitを取得するAPIの返り値を解釈して残数と開放時間を取得する処理をチェックする
        """

        crawler = ConcreteCrawler()

        url = "https://api.twitter.com/1.1/application/rate_limit_status.json"
        params = {
            "resources": "favorites"
        }

        # responce = crawler.oath.get(url, params=params)
        # favorites_limit_text_sample = responce.text
        favorites_limit_text_sample = f"""{{
            "resources": {{
                "favorites": {{
                    "\/favorites\/list": {{
                        "limit":75,
                        "remaining":70,
                        "reset":1563195985
                    }}
                }}
            }}
        }}"""

        remaining, reset = crawler.GetTwitterAPILimitContext(json.loads(favorites_limit_text_sample), params)
        self.assertEqual(70, remaining)
        self.assertEqual(1563195985, reset)

    def test_WaitUntilReset(self):
        """指定UNIX時間まで待機する処理の呼び出しをチェックする
        """

        crawler = ConcreteCrawler()

        with ExitStack() as stack:
            mocktime = stack.enter_context(patch("time.sleep"))

            dt_unix = time.mktime(datetime.now().timetuple()) + 1

            res = crawler.WaitUntilReset(dt_unix)
            mocktime.assert_called()
            self.assertEqual(0, res)

    def test_CheckTwitterAPILimit(self):
        """TwitterAPI制限を取得する機能をチェックする

        Notes:
            mock置き換えによりTwitterAPIが503を返す状況もシミュレートする
        """

        with ExitStack() as stack:
            mockTWARType = stack.enter_context(patch("PictureGathering.Crawler.Crawler.GetTwitterAPIResourceType"))
            mockoauth = stack.enter_context(patch("requests_oauthlib.OAuth1Session.get"))
            mockWaitUntilReset = stack.enter_context(patch("PictureGathering.Crawler.Crawler.WaitUntilReset"))
            mockTWALimitContext = stack.enter_context(patch("PictureGathering.Crawler.Crawler.GetTwitterAPILimitContext"))

            crawler = ConcreteCrawler()
            url = "https://api.twitter.com/1.1/favorites/list.json"

            mockTWARType.return_value = "favorites"

            # mock設定
            def responce_factory(status_code, text):
                responce = MagicMock()
                p_status_code = PropertyMock()
                p_status_code.return_value = status_code
                type(responce).status_code = p_status_code

                p_text = PropertyMock()
                p_text.return_value = text
                type(responce).text = p_text

                return responce

            text = f"""{{"text": "api_responce_text_sample"}}"""

            responce1 = responce_factory(503, text)
            responce2 = responce_factory(200, text)
            responce3 = responce_factory(200, text)
            responce4 = responce_factory(200, text)
            responce5 = responce_factory(404, text)

            mockoauth.side_effect = (responce1, responce2, responce3, responce4, responce5)
            mockWaitUntilReset.return_value = 0
            mockTWALimitContext.side_effect = ((70, 0), (0, 0), (75, 0))

            # 1回目(503からのcontinueで200、remaining=70)
            self.assertIsNotNone(crawler.CheckTwitterAPILimit(url))
            self.assertEqual(2, mockTWARType.call_count)
            self.assertEqual(2, mockoauth.call_count)
            self.assertEqual(1, mockWaitUntilReset.call_count)
            self.assertEqual(1, mockTWALimitContext.call_count)

            # 2回目(200、remaining=0->200、remaining=75)
            self.assertIsNotNone(crawler.CheckTwitterAPILimit(url))
            self.assertEqual(4, mockTWARType.call_count)
            self.assertEqual(4, mockoauth.call_count)
            self.assertEqual(2, mockWaitUntilReset.call_count)
            self.assertEqual(3, mockTWALimitContext.call_count)

            # 3回目(404)
            with self.assertRaises(Exception):
                crawler.CheckTwitterAPILimit(url)

    def test_WaitTwitterAPIUntilReset(self):
        """TwitterAPIが利用できるまで待つ機能をチェックする
        """

        with ExitStack() as stack:
            mockWaitUntilReset = stack.enter_context(patch("PictureGathering.Crawler.Crawler.WaitUntilReset"))
            mockTWALimit = stack.enter_context(patch("PictureGathering.Crawler.Crawler.CheckTwitterAPILimit"))

            crawler = ConcreteCrawler()

            # mock設定
            def responce_factory(url, headers):
                responce = MagicMock()
                p_url = PropertyMock()
                p_url.return_value = url
                type(responce).url = p_url

                p_headers = PropertyMock()
                p_headers.return_value = headers
                type(responce).headers = p_headers

                return responce

            headers100 = {"X-Rate-Limit-Remaining": "100",
                          "X-Rate-Limit-Reset": time.mktime(datetime.now().timetuple())}

            headers0 = {"X-Rate-Limit-Remaining": "0",
                        "X-Rate-Limit-Reset": time.mktime(datetime.now().timetuple())}

            url = "https://api.twitter.com/1.1/favorites/list.json"
            responce1 = responce_factory(url, headers100)
            responce2 = responce_factory(url, headers0)
            responce3 = MagicMock()
            p_url = PropertyMock()
            p_url.return_value = url
            type(responce3).url = p_url

            mockWaitUntilReset.return_value = 0
            mockTWALimit.return_value = 0

            # 1回目(headersあり、Remaining=100)
            self.assertIsNotNone(crawler.WaitTwitterAPIUntilReset(responce1))
            self.assertEqual(0, mockWaitUntilReset.call_count)
            self.assertEqual(0, mockTWALimit.call_count)

            # 2回目(headersあり、Remaining=0)
            self.assertIsNotNone(crawler.WaitTwitterAPIUntilReset(responce2))
            self.assertEqual(1, mockWaitUntilReset.call_count)
            self.assertEqual(1, mockTWALimit.call_count)

            # 3回目(headersなし)
            self.assertIsNotNone(crawler.WaitTwitterAPIUntilReset(responce3))
            self.assertEqual(1, mockWaitUntilReset.call_count)
            self.assertEqual(2, mockTWALimit.call_count)

    def test_TwitterAPIRequestMocked(self):
        """TwitterAPIが利用できない場合の挙動をチェックする

        Notes:
            mock置き換えによりTwitterAPIが503を返す状況をシミュレートする
        """

        with ExitStack() as stack:
            mockoauth = stack.enter_context(patch("requests_oauthlib.OAuth1Session.get"))
            mockTWAUntilReset = stack.enter_context(patch("PictureGathering.Crawler.Crawler.WaitTwitterAPIUntilReset"))

            crawler = ConcreteCrawler()

            # mock設定
            def responce_factory(status_code, text):
                responce = MagicMock()
                p_status_code = PropertyMock()
                p_status_code.return_value = status_code
                type(responce).status_code = p_status_code

                p_text = PropertyMock()
                p_text.return_value = text
                type(responce).text = p_text

                return responce

            text = f"""{{"text": "api_responce_text_sample"}}"""

            url = "https://api.twitter.com/1.1/favorites/list.json"
            responce1 = responce_factory(503, text)
            responce2 = responce_factory(200, text)
            responce3 = responce_factory(404, text)

            mockoauth.side_effect = (responce1, responce2, responce3)
            mockTWAUntilReset.return_value = 0

            params = {
                "screen_name": crawler.user_name,
                "page": 1,
                "count": crawler.count,
                "include_entities": 1
            }

            # 1回目(503からのcontinueで200)
            self.assertEqual(json.loads(text), crawler.TwitterAPIRequest(url, params))
            self.assertEqual(1, mockTWAUntilReset.call_count)

            # 2回目(404)
            with self.assertRaises(Exception):
                crawler.TwitterAPIRequest(url, params)

    def test_TwitterAPIRequestActual(self):
        """TwitterAPIの応答をチェックする

        Notes:
            mock置き換えはせず、実際にTwitterAPIを使用して応答を確認する（GETのみ）
        """

        crawler = ConcreteCrawler()
        fav_get_max_loop = int(crawler.config["tweet_timeline"]["fav_get_max_loop"]) + 1

        for i in range(1, fav_get_max_loop):
            url = "https://api.twitter.com/1.1/favorites/list.json"
            params = {
                "screen_name": crawler.user_name,
                "page": i,
                "count": crawler.count,
                "include_entities": 1,  # ツイートのメタデータ取得。これしないと複数枚の画像に対応できない。
                "tweet_mode": "extended"
            }
            self.assertIsNotNone(crawler.TwitterAPIRequest(url, params))

        url = "https://api.twitter.com/1.1/statuses/home_timeline.json"
        params = {
            "count": crawler.count,
            "include_entities": 1,
            "tweet_mode": "extended"
        }
        self.assertIsNotNone(crawler.TwitterAPIRequest(url, params))

        url = "https://api.twitter.com/1.1/users/show.json"
        params = {
            "screen_name": crawler.config["notification"]["reply_to_user_name"],
        }
        self.assertIsNotNone(crawler.TwitterAPIRequest(url, params))

    def test_GetMediaUrl(self):
        """メディアURL取得処理をチェックする
        """

        img_url_s = "http://www.img.filename.sample.com/media/sample.png"
        video_url_s = "https://video.twimg.com/ext_tw_video/1152052808385875970/pu/vid/998x714/sample.mp4"
        img_filename_s = os.path.basename(img_url_s)

        crawler = ConcreteCrawler()

        # typeなし
        media_tweet_json = f"""{{
            "media_url": "{img_url_s}"
        }}"""
        self.assertEqual("", crawler.GetMediaUrl(json.loads(media_tweet_json)))

        # media_urlなし(photo)
        media_tweet_json = f"""{{
            "type": "photo"
        }}"""
        self.assertEqual("", crawler.GetMediaUrl(json.loads(media_tweet_json)))

        # photo
        media_tweet_json = f"""{{
            "type": "photo",
            "media_url": "{img_url_s}"
        }}"""
        self.assertEqual(img_url_s, crawler.GetMediaUrl(json.loads(media_tweet_json)))

        # media_urlなし(video)
        media_tweet_json = f"""{{
            "type": "video"
        }}"""
        self.assertEqual("", crawler.GetMediaUrl(json.loads(media_tweet_json)))

        # video
        media_tweet_json = f"""{{
            "type": "video",
            "video_info": {{
                "variants":[{{
                    "content_type": "video/mp4",
                    "bitrate": 640,
                    "url": "{video_url_s}_640"
                }},
                {{
                    "content_type": "video/mp4",
                    "bitrate": 2048,
                    "url": "{video_url_s}_2048"
                }},
                {{
                    "content_type": "video/mp4",
                    "bitrate": 1024,
                    "url": "{video_url_s}_1024"
                }}
                ]
            }}
        }}"""
        self.assertEqual(video_url_s + "_2048", crawler.GetMediaUrl(json.loads(media_tweet_json)))

    def test_GetMediaTweet(self):
        """ツイートオブジェクトの階層解釈処理をチェックする
        """

        crawler = ConcreteCrawler()

        # ツイートサンプル作成
        s_media_url = "http://pbs.twimg.com/media/add_sample{}.jpg:orig"
        s_nrt_t = [self.__GetNoRetweetedTweetSample(s_media_url.format(i)) for i in range(3)]
        s_nm_t = [self.__GetNoMediaTweetSample() for i in range(3)]
        s_rt_t = [self.__GetRetweetTweetSample(s_media_url.format(i)) for i in range(3)]
        s_quote_t = [self.__GetQuoteTweetSample(s_media_url.format(i)) for i in range(3)]
        s_rt_quote_t = [self.__GetRetweetQuoteTweetSample(s_media_url.format(i)) for i in range(3)]
        s_tweet_list = s_nrt_t + s_nm_t + s_rt_t + s_quote_t + s_rt_quote_t
        random.shuffle(s_tweet_list)

        # 予想値取得用
        def GetMediaTweet(tweet: dict) -> List[dict]:
            result = []
            # ツイートオブジェクトにRTフラグが立っている場合
            if tweet.get("retweeted") and tweet.get("retweeted_status"):
                if tweet["retweeted_status"].get("extended_entities"):
                    result.append(tweet["retweeted_status"])  # (2)
                # ツイートオブジェクトに引用RTフラグも立っている場合
                if tweet["retweeted_status"].get("is_quote_status") and tweet["retweeted_status"].get("quoted_status"):
                    if tweet["retweeted_status"]["quoted_status"].get("extended_entities"):
                        result = result + GetMediaTweet(tweet["retweeted_status"])  # (4)
            # ツイートオブジェクトに引用RTフラグが立っている場合
            elif tweet.get("is_quote_status") and tweet.get("quoted_status"):
                if tweet["quoted_status"].get("extended_entities"):
                    result.append(tweet["quoted_status"])  # (3)
                # ツイートオブジェクトにRTフラグも立っている場合（仕様上、本来はここはいらない）
                if tweet["quoted_status"].get("retweeted") and tweet["quoted_status"].get("retweeted_status"):
                    if tweet["quoted_status"]["retweeted_status"].get("extended_entities"):
                        result = result + GetMediaTweet(tweet["quoted_status"])
            
            # ツイートオブジェクトにメディアがある場合
            if tweet.get("extended_entities"):
                if tweet["extended_entities"].get("media"):
                    if tweet not in result:
                        result.append(tweet)
            return result  # (1)

        # 実行
        for s_tweet in s_tweet_list:
            expect = GetMediaTweet(s_tweet)
            actual = crawler.GetMediaTweet(s_tweet)
            self.assertEqual(expect, actual)

    def test_InterpretTweets(self):
        """画像保存をチェックする
        """

        use_file_list = []

        # 初期化：前テストで使用したファイルが残っていた場合削除する
        sample_img = ["sample.png_1", "sample.png_2"]
        for file in sample_img:
            if os.path.exists(file):
                os.remove(file)

        with ExitStack() as stack:
            mocksql = stack.enter_context(patch("PictureGathering.DBController.DBController.DBFavUpsert"))
            mockurllib = stack.enter_context(patch("PictureGathering.Crawler.urllib.request.urlretrieve"))
            mocksystem = stack.enter_context(patch("PictureGathering.Crawler.os.system"))

            # mock設定
            mocksql.return_value = 0
            mocksystem.return_value = 0
            crawler = ConcreteCrawler()
            crawler.save_path = os.getcwd()

            def urlopen_sideeffect(url_orig, save_file_fullpath):
                url = url_orig.replace(":orig", "")
                save_file_path = os.path.join(crawler.save_path, os.path.basename(url))

                with open(save_file_path, "wb") as fout:
                    fout.write("test".encode())

                use_file_list.append(save_file_path)

                return save_file_path

            mockurllib.side_effect = urlopen_sideeffect

            tweets = []
            img_url_s = "http://www.img.filename.sample.com/media/sample.png"
            media_tweet_s = self.__GetNoRetweetedTweetSample(img_url_s)
            tweets.append(media_tweet_s)
            expect_save_num = len(media_tweet_s["extended_entities"]["media"])
            self.assertEqual(0, crawler.InterpretTweets(tweets))

            self.assertEqual(expect_save_num, crawler.add_cnt)
            self.assertEqual(expect_save_num, mocksql.call_count)
            self.assertEqual(expect_save_num, mockurllib.call_count)
            # self.assertEqual(expect_save_num, mocksystem.call_count)

        # 画像が保存できたかチェック
        for path in use_file_list:
            self.assertTrue(os.path.exists(path))

        # 後始末：テストで使用したファイルを削除する
        for path in use_file_list:
            os.remove(path)

    def test_GetExistFilelist(self):
        """save_pathにあるファイル名一覧取得処理をチェックする
        """

        crawler = ConcreteCrawler()

        xs = []
        for root, dir, files in os.walk(crawler.save_path):
            for f in files:
                path = os.path.join(root, f)
                xs.append((os.path.getmtime(path), path))
        os.walk(crawler.save_path).close()

        expect_filelist = []
        for mtime, path in sorted(xs, reverse=True):
            expect_filelist.append(path)

        self.assertEqual(expect_filelist, crawler.GetExistFilelist())

    def test_ShrinkFolder(self):
        """フォルダ内ファイルの数を一定にする機能をチェックする
        """

        with ExitStack() as stack:
            mockGetExistFilelist = stack.enter_context(patch("PictureGathering.Crawler.Crawler.GetExistFilelist"))
            # mockGetVideoURL = stack.enter_context(patch("test.Test_Crawler.ConcreteCrawler.GetVideoURL"))
            mockUpdateDBExistMark = stack.enter_context(patch("PictureGathering.Crawler.Crawler.UpdateDBExistMark"))
            mockos = stack.enter_context(patch("PictureGathering.Crawler.os.remove"))
            image_base_url = "http://pbs.twimg.com/media/{}:orig"
            video_base_url = "https://video.twimg.com/ext_tw_video/1144527536388337664/pu/vid/626x882/{}"

            crawler = ConcreteCrawler()
            holding_file_num = 10

            # フォルダ内に存在するファイルのサンプルを生成する
            # 保持すべきholding_file_numを超えるファイルがあるものとする
            # 画像と動画をそれぞれ作り、ランダムにピックアップする
            sample_num = holding_file_num * 2 // 3 * 2
            img_sample = ["sample_img_{}.png".format(i) for i in range(sample_num // 2 + 1)]
            video_sample = ["sample_video_{}.mp4".format(i) for i in range(sample_num // 2 + 1)]
            file_sample = random.sample(img_sample + video_sample, sample_num)  # 結合してシャッフル
            mockGetExistFilelist.return_value = file_sample

            # def GetVideoURLsideeffect(filename):
            #     return video_base_url.format(filename)

            # mockGetVideoURL.side_effect = GetVideoURLsideeffect
            mockUpdateDBExistMark = None

            self.assertEqual(0, crawler.ShrinkFolder(holding_file_num - 1))

            def MakeUrl(filename):
                if ".mp4" in filename:  # media_type == "video":
                    return video_base_url.format(filename)
                else:  # media_type == "photo":
                    return image_base_url.format(filename)

            expect_del_cnt = len(file_sample) - holding_file_num
            expect_del_url_list = file_sample[-expect_del_cnt:len(file_sample)]
            expect_del_url_list = list(map(MakeUrl, expect_del_url_list))
            expect_add_url_list = file_sample[0:holding_file_num]
            expect_add_url_list = list(map(MakeUrl, expect_add_url_list))

            self.assertEqual(expect_del_cnt, crawler.del_cnt)
            self.assertEqual(expect_del_url_list, crawler.del_url_list)
            # self.assertEqual(expect_add_url_list, crawler.add_url_list)

    def test_EndOfProcess(self):
        """取得後処理をチェックする
        """

        crawler = ConcreteCrawler()

        with ExitStack() as stack:
            mocklogger = stack.enter_context(patch.object(logger, "info"))
            mockwhtml = stack.enter_context(patch("PictureGathering.WriteHTML.WriteResultHTML"))
            mockcptweet = stack.enter_context(patch("PictureGathering.Crawler.Crawler.PostTweet"))
            mockcplnotify = stack.enter_context(patch("PictureGathering.Crawler.Crawler.PostLineNotify"))
            mockcpsnotify = stack.enter_context(patch("PictureGathering.Crawler.Crawler.PostSlackNotify"))
            mockcpdnotify = stack.enter_context(patch("PictureGathering.Crawler.Crawler.PostDiscordNotify"))
            mockamzf = stack.enter_context(patch("PictureGathering.Archiver.MakeZipFile"))
            mockamzf = stack.enter_context(patch("PictureGathering.GoogleDrive.UploadToGoogleDrive"))
            mocksql = stack.enter_context(patch("PictureGathering.DBController.DBController.DBDelSelect"))
            mockoauth = stack.enter_context(patch("requests_oauthlib.OAuth1Session.post"))

            # mock設定
            mocksql.return_value = []

            img_url_s = "http://www.img.filename.sample.com/media/sample.png"
            media_tweet_s = self.__GetNoRetweetedTweetSample(img_url_s)
            media_url_list = media_tweet_s["extended_entities"]["media"]
            for media_url in media_url_list:
                crawler.add_url_list.append(media_url["media_url"])
                crawler.del_url_list.append(media_url["media_url"])
            crawler.add_cnt = len(crawler.add_url_list)
            crawler.del_cnt = len(crawler.del_url_list)

            # TODO::

            self.assertEqual(0, crawler.EndOfProcess())

    def test_PostTweet(self):
        """ツイートポスト機能をチェックする
        """

        crawler = ConcreteCrawler()

        with ExitStack() as stack:
            mockctapi = stack.enter_context(patch("PictureGathering.Crawler.Crawler.TwitterAPIRequest"))
            mockoauth = stack.enter_context(patch("requests_oauthlib.OAuth1Session.post"))
            mocksql = stack.enter_context(patch("PictureGathering.DBController.DBController.DBDelUpsert"))

            # mock設定
            mockctapi.return_value = {"id_str": "12345_id_str_sample"}
            responce = MagicMock()
            status_code = PropertyMock()
            status_code.return_value = 200
            type(responce).status_code = status_code
            text = PropertyMock()
            text.return_value = f'{{"text": "sample"}}'
            type(responce).text = text
            mockoauth.return_value = responce
            mocksql.return_value = 0

            self.assertEqual(0, crawler.PostTweet("test"))
            mockctapi.assert_called_once()
            mockoauth.assert_called_once()
            mocksql.assert_called_once()

    def test_PostLineNotify(self):
        """LINE通知ポスト機能をチェックする
        """

        crawler = ConcreteCrawler()

        with ExitStack() as stack:
            mockreq = stack.enter_context(patch("PictureGathering.Crawler.requests.post"))

            # mock設定
            responce = MagicMock()
            status_code = PropertyMock()
            status_code.return_value = 200
            type(responce).status_code = status_code
            mockreq.return_value = responce

            str = "text"
            self.assertEqual(0, crawler.PostLineNotify(str))
            mockreq.assert_called_once()

    def test_PostSlackNotify(self):
        """Slack通知ポスト機能をチェックする
        """

        crawler = ConcreteCrawler()

        with ExitStack() as stack:
            mockslack = stack.enter_context(patch("PictureGathering.Crawler.slackweb.Slack.notify"))

            # mock設定
            mockslack.return_value = 0

            str = "text"
            self.assertEqual(0, crawler.PostSlackNotify(str))
            mockslack.assert_called_once_with(text="<!here> " + str)

    def test_PostDiscordNotify(self):
        """Discord通知ポスト機能をチェックする
        """

        crawler = ConcreteCrawler()

        with ExitStack() as stack:
            mockreq = stack.enter_context(patch("PictureGathering.Crawler.requests.post"))

            # mock設定
            responce = MagicMock()
            status_code = PropertyMock()
            status_code.return_value = 204  # 成功すると204 No Contentが返ってくる
            type(responce).status_code = status_code
            mockreq.return_value = responce

            str = "text"
            self.assertEqual(0, crawler.PostDiscordNotify(str))
            mockreq.assert_called_once()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
