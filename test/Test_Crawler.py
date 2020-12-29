# coding: utf-8
"""クローラーのテスト

Crawler.Crawler()の各種機能をテストする
実際に使用する派生クラスのテストについてはそれぞれのファイルに記述する
設定ファイルとして {CONFIG_FILE_NAME} にあるconfig.iniファイルを使用する
各種トークン類もAPI利用のテストのために使用する
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

    def __GetNoMediaTweetWithPixivSample(self) -> dict:
        """ツイートオブジェクトのサンプルを生成する（メディアなし、RTフラグなし、本文にpixivリンクあり）

        Args:
            img_url_s (str): 画像URLサンプル

        Returns:
            dict: ツイートオブジェクト（サンプル）
        """
        tweet_s = self.__GetNoMediaTweetSample()
        r = "{:0>8}".format(random.randint(0, 99999999))
        url = "https://www.pixiv.net/artworks/{}".format(r)
        tweet_s["text"] = tweet_s["text"] + " " + url
        tweet_s["retweeted"] = False
        tweet_s["entities"] = {"urls": []}
        tweet_s["entities"]["urls"].append({"expanded_url": url})
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
        self.assertIsInstance(crawler.config, configparser.ConfigParser)
        self.assertIsInstance(expect_config, configparser.ConfigParser)

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

        self.assertEqual(expect_config["holding"]["holding_file_num"],
                         crawler.config["holding"]["holding_file_num"])

        # dbはTest_DBControlで確認

        self.assertEqual(expect_config["tweet_timeline"]["user_name"],
                         crawler.user_name)
        self.assertEqual(expect_config["tweet_timeline"]["fav_get_max_loop"],
                         crawler.config["tweet_timeline"]["fav_get_max_loop"])
        self.assertEqual(expect_config["tweet_timeline"]["retweet_get_max_loop"],
                         crawler.config["tweet_timeline"]["retweet_get_max_loop"])
        self.assertEqual(int(expect_config["tweet_timeline"]["count"]),
                         crawler.count)
        self.assertIn(crawler.config["tweet_timeline"]["kind_of_timeline"],
                      ["favorite", "home"])

        self.assertEqual(expect_config["timestamp"]["timestamp_created_at"],
                         crawler.config["timestamp"]["timestamp_created_at"])

        # pixivはTest_PixivAPIControllerで確認

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

        # TODO::archiverのテストを独立させる
        self.assertEqual(expect_config["archive"]["is_archive"],
                         crawler.config["archive"]["is_archive"])
        self.assertEqual(expect_config["archive"]["archive_temp_path"],
                         crawler.config["archive"]["archive_temp_path"])
        self.assertEqual(expect_config["archive"]["is_send_google_drive"],
                         crawler.config["archive"]["is_send_google_drive"])
        self.assertEqual(expect_config["archive"]["google_service_account_credentials"],
                         crawler.config["archive"]["google_service_account_credentials"])

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

        # favリスト取得API
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

        # response = crawler.oath.get(url, params=params)
        # favorites_limit_text_sample = response.text
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

        # 正常系
        remaining, reset = crawler.GetTwitterAPILimitContext(json.loads(favorites_limit_text_sample), params)
        self.assertEqual(70, remaining)
        self.assertEqual(1563195985, reset)

        # res_textとparamsの対応が一致しない
        params["resources"] = "error"
        remaining, reset = crawler.GetTwitterAPILimitContext(json.loads(favorites_limit_text_sample), params)
        self.assertEqual(-1, remaining)
        self.assertEqual(-1, reset)

        # paramsに"resources"が存在しない
        del params["resources"]
        remaining, reset = crawler.GetTwitterAPILimitContext(json.loads(favorites_limit_text_sample), params)
        self.assertEqual(-1, remaining)
        self.assertEqual(-1, reset)

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
            mockWaitUntilReset = stack.enter_context(patch("PictureGathering.Crawler.Crawler.WaitUntilReset"))
            mockTWALimitContext = stack.enter_context(patch("PictureGathering.Crawler.Crawler.GetTwitterAPILimitContext"))
            mockoauth = stack.enter_context(patch("requests_oauthlib.OAuth1Session.get"))

            crawler = ConcreteCrawler()
            url = "https://api.twitter.com/1.1/favorites/list.json"

            mockTWARType.return_value = "favorites"

            # mock設定
            def response_factory(status_code, text):
                response = MagicMock()
                p_status_code = PropertyMock()
                p_status_code.return_value = status_code
                type(response).status_code = p_status_code

                p_text = PropertyMock()
                p_text.return_value = text
                type(response).text = p_text

                return response

            text = f"""{{"text": "api_response_text_sample"}}"""

            response1 = response_factory(503, text)
            response2 = response_factory(200, text)
            response3 = response_factory(200, text)
            response4 = response_factory(200, text)
            response5 = response_factory(404, text)

            mockoauth.side_effect = (response1, response2, response3, response4, response5)
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
            def response_factory(url, headers):
                response = MagicMock()
                p_url = PropertyMock()
                p_url.return_value = url
                type(response).url = p_url

                p_headers = PropertyMock()
                p_headers.return_value = headers
                type(response).headers = p_headers

                return response

            headers100 = {"X-Rate-Limit-Remaining": "100",
                          "X-Rate-Limit-Reset": time.mktime(datetime.now().timetuple())}

            headers0 = {"X-Rate-Limit-Remaining": "0",
                        "X-Rate-Limit-Reset": time.mktime(datetime.now().timetuple())}

            url = "https://api.twitter.com/1.1/favorites/list.json"
            response1 = response_factory(url, headers100)
            response2 = response_factory(url, headers0)
            response3 = MagicMock()
            p_url = PropertyMock()
            p_url.return_value = url
            type(response3).url = p_url

            mockWaitUntilReset.return_value = 0
            mockTWALimit.return_value = 0

            # 1回目(headersあり、Remaining=100)
            self.assertIsNotNone(crawler.WaitTwitterAPIUntilReset(response1))
            self.assertEqual(0, mockWaitUntilReset.call_count)
            self.assertEqual(0, mockTWALimit.call_count)

            # 2回目(headersあり、Remaining=0)
            self.assertIsNotNone(crawler.WaitTwitterAPIUntilReset(response2))
            self.assertEqual(1, mockWaitUntilReset.call_count)
            self.assertEqual(1, mockTWALimit.call_count)

            # 3回目(headersなし)
            self.assertIsNotNone(crawler.WaitTwitterAPIUntilReset(response3))
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
            def response_factory(status_code, text):
                response = MagicMock()
                p_status_code = PropertyMock()
                p_status_code.return_value = status_code
                type(response).status_code = p_status_code

                p_text = PropertyMock()
                p_text.return_value = text
                type(response).text = p_text

                return response

            text = f"""{{"text": "api_response_text_sample"}}"""

            url = "https://api.twitter.com/1.1/favorites/list.json"
            response1 = response_factory(503, text)
            response2 = response_factory(200, text)
            response3 = response_factory(404, text)

            mockoauth.side_effect = (response1, response2, response3)
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
                "include_entities": 1,
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
        animated_gif_url_s = "https://video.twimg.com/tweet_video/sample.mp4"

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

        # media_urlなし(animated_gif)
        media_tweet_json = f"""{{
            "type": "animated_gif"
        }}"""
        self.assertEqual("", crawler.GetMediaUrl(json.loads(media_tweet_json)))

        # animated_gif
        media_tweet_json = f"""{{
            "type": "animated_gif",
            "video_info": {{
                "variants":[{{
                    "content_type": "video/mp4",
                    "bitrate": 0,
                    "url": "{animated_gif_url_s}"
                }}
                ]
            }}
        }}"""
        self.assertEqual(animated_gif_url_s, crawler.GetMediaUrl(json.loads(media_tweet_json)))

    def test_GetMediaTweet(self):
        """ツイートオブジェクトの階層解釈処理をチェックする
        """

        crawler = ConcreteCrawler()

        # ツイートサンプル作成
        s_media_url = "http://pbs.twimg.com/media/add_sample{}.jpg:orig"
        s_nrt_t = [self.__GetNoRetweetedTweetSample(s_media_url.format(i)) for i in range(3)]
        s_nm_t = [self.__GetNoMediaTweetSample() for i in range(3)]
        s_nm_with_pixiv_t = [self.__GetNoMediaTweetWithPixivSample() for i in range(3)]
        s_rt_t = [self.__GetRetweetTweetSample(s_media_url.format(i)) for i in range(3)]
        s_quote_t = [self.__GetQuoteTweetSample(s_media_url.format(i)) for i in range(3)]
        s_rt_quote_t = [self.__GetRetweetQuoteTweetSample(s_media_url.format(i)) for i in range(3)]
        s_tweet_list = s_nrt_t + s_nm_t + s_nm_with_pixiv_t + s_rt_t + s_quote_t + s_rt_quote_t
        random.shuffle(s_tweet_list)

        # 予想値取得用
        def GetMediaTweet(tweet: dict, id_str_list: list = None) -> List[dict]:
            result = []
            # デフォルト引数の処理
            if id_str_list is None:
                id_str_list = []
            # ツイートオブジェクトにメディアがある場合
            if tweet.get("extended_entities"):
                if tweet["extended_entities"].get("media"):
                    if tweet["id_str"] not in id_str_list:
                        result.append(tweet)
                        id_str_list.append(tweet["id_str"])
            # ツイートオブジェクトにRTフラグが立っている場合
            if tweet.get("retweeted") and tweet.get("retweeted_status"):
                if tweet["retweeted_status"].get("extended_entities"):
                    result.append(tweet["retweeted_status"])
                    id_str_list.append(tweet["retweeted_status"]["id_str"])
                # ツイートオブジェクトに引用RTフラグも立っている場合
                if tweet["retweeted_status"].get("is_quote_status") and tweet["retweeted_status"].get("quoted_status"):
                    if tweet["retweeted_status"]["quoted_status"].get("extended_entities"):
                        result = result + GetMediaTweet(tweet["retweeted_status"], id_str_list)
            # ツイートオブジェクトに引用RTフラグが立っている場合
            elif tweet.get("is_quote_status") and tweet.get("quoted_status"):
                if tweet["quoted_status"].get("extended_entities"):
                    result.append(tweet["quoted_status"])
                    id_str_list.append(tweet["quoted_status"]["id_str"])
                # ツイートオブジェクトにRTフラグも立っている場合（仕様上、本来はここはいらない）
                if tweet["quoted_status"].get("retweeted") and tweet["quoted_status"].get("retweeted_status"):
                    if tweet["quoted_status"]["retweeted_status"].get("extended_entities"):
                        result = result + GetMediaTweet(tweet["quoted_status"], id_str_list)
            # ツイートにpixivのリンクがある場合
            if tweet.get("entities"):
                if tweet["entities"].get("urls"):
                    url = tweet["entities"]["urls"][0].get("expanded_url")
                    from PictureGathering import PixivAPIController
                    IsPixivURL = PixivAPIController.PixivAPIController.IsPixivURL
                    if IsPixivURL(url):
                        if tweet["id_str"] not in id_str_list:
                            result.append(tweet)
                            id_str_list.append(tweet["id_str"])
            return result

        # 実行
        for s_tweet in s_tweet_list:
            expect = GetMediaTweet(s_tweet)
            actual = crawler.GetMediaTweet(s_tweet)
            self.assertEqual(expect, actual)

    def test_TweetMediaSaver(self):
        """画像保存をチェックする
        """

        use_file_list = []

        with ExitStack() as stack:
            mockurllib = stack.enter_context(patch("PictureGathering.Crawler.urllib.request.urlopen"))
            mocksystem = stack.enter_context(patch("PictureGathering.Crawler.os.system"))
            mockshutil = stack.enter_context(patch("PictureGathering.Crawler.shutil"))
            mocksql = stack.enter_context(patch("PictureGathering.DBController.DBController.DBFavUpsert"))

            # mock設定
            mocksystem.return_value = 0
            mockshutil.return_value = 0
            mocksql.return_value = 0
            crawler = ConcreteCrawler()
            crawler.save_path = os.getcwd()

            def urlopen_sideeffect(url_orig, timeout=60):
                url = url_orig.replace(":orig", "")
                save_file_path = os.path.join(crawler.save_path, os.path.basename(url))

                with open(save_file_path, "wb") as fout:
                    fout.write(save_file_path.encode())

                use_file_list.append(save_file_path)

                return open(save_file_path, "rb")

            mockurllib.side_effect = urlopen_sideeffect

            img_url_s = "http://www.img.filename.sample.com/media/sample.png"
            video_url_s = "https://video.twimg.com/ext_tw_video/1152052808385875970/pu/vid/998x714/sample_video.mp4"
            animated_gif_url_s = "https://video.twimg.com/tweet_video/sample_gif.mp4"

            # ツイートサンプルの用意
            # 最後にすでに存在するメディアを重複保存しようとしたときのテスト用の要素を追加する
            media_tweet_list_s = []
            for url_s in [img_url_s, video_url_s, animated_gif_url_s]:
                media_tweet_list_s.append(self.__GetNoRetweetedTweetSample(url_s))
            media_tweet_list_s.append(media_tweet_list_s[0])

            # video
            media_tweet_json = f"""{{
                "type": "video",
                "media_url": "{video_url_s}",
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
            media_tweet_list_s[1]["extended_entities"]["media"][0] = json.loads(media_tweet_json)
            del media_tweet_list_s[1]["extended_entities"]["media"][1]
        
            # animated_gif
            media_tweet_json = f"""{{
                "type": "animated_gif",
                "media_url": "{animated_gif_url_s}",
                "video_info": {{
                    "variants":[{{
                        "content_type": "video/mp4",
                        "bitrate": 0,
                        "url": "{animated_gif_url_s}"
                    }}
                    ]
                }}
            }}"""
            media_tweet_list_s[2]["extended_entities"]["media"][0] = json.loads(media_tweet_json)
            del media_tweet_list_s[2]["extended_entities"]["media"][1]

            for i, media_tweet_s in enumerate(media_tweet_list_s):
                # media_tweet_s = self.__GetNoRetweetedTweetSample(url_s)
                td_format_s = "%a %b %d %H:%M:%S +0000 %Y"
                created_time_s = time.strptime(media_tweet_s["created_at"], td_format_s)
                atime_s = mtime_s = time.mktime(
                    (created_time_s.tm_year,
                        created_time_s.tm_mon,
                        created_time_s.tm_mday,
                        created_time_s.tm_hour,
                        created_time_s.tm_min,
                        created_time_s.tm_sec,
                        0, 0, -1)
                )

                # 実行
                l_flag = (i == len(media_tweet_list_s) - 1)
                expect = 1 if l_flag else 0
                for media_dict in media_tweet_s["extended_entities"]["media"]:
                    actual = crawler.TweetMediaSaver(media_tweet_s, media_dict, atime_s, mtime_s)
                    self.assertEqual(expect, actual)  # 重複保存

                # 呼び出し確認
                expect_save_num = 0 if l_flag else len(media_tweet_s["extended_entities"]["media"])
                self.assertEqual(expect_save_num, crawler.add_cnt)
                self.assertEqual(expect_save_num, mocksql.call_count)
                self.assertEqual(expect_save_num, mockurllib.call_count)
                crawler.add_cnt = 0
                mocksql.reset_mock()
                mockurllib.reset_mock()

        # メディアが保存できたかチェック
        for path in use_file_list:
            self.assertTrue(os.path.exists(path))

        # 後始末：テストで使用したファイルを削除する
        for path in use_file_list:
            os.remove(path)

    def test_InterpretTweets(self):
        """ツイートオブジェクトの解釈をチェックする
        """
        crawler = ConcreteCrawler()

        # ツイートサンプル作成
        s_media_url = "http://pbs.twimg.com/media/add_sample{}.jpg:orig"
        s_nrt_t = [self.__GetNoRetweetedTweetSample(s_media_url.format(i)) for i in range(3)]
        s_nm_t = [self.__GetNoMediaTweetSample() for i in range(3)]
        s_nm_with_pixiv_t = [self.__GetNoMediaTweetWithPixivSample() for i in range(3)]
        s_rt_t = [self.__GetRetweetTweetSample(s_media_url.format(i)) for i in range(3)]
        s_quote_t = [self.__GetQuoteTweetSample(s_media_url.format(i)) for i in range(3)]
        s_rt_quote_t = [self.__GetRetweetQuoteTweetSample(s_media_url.format(i)) for i in range(3)]
        s_tweet_list = s_nrt_t + s_nm_t + s_nm_with_pixiv_t + s_rt_t + s_quote_t + s_rt_quote_t
        random.shuffle(s_tweet_list)

        # TweetMediaSaverを呼び出すまでのツイートオブジェクト解釈結果を収集
        def GetTweetMediaSaverCalledArg(tweets: List[dict]) -> int:
            res_list = []
            for tweet in tweets:
                media_tweets = crawler.GetMediaTweet(tweet)
                if not media_tweets:
                    continue

                td_format = "%a %b %d %H:%M:%S +0000 %Y"
                mt = media_tweets[0]
                created_time = time.strptime(mt["created_at"], td_format)
                atime = mtime = time.mktime(
                    (created_time.tm_year,
                        created_time.tm_mon,
                        created_time.tm_mday,
                        created_time.tm_hour,
                        created_time.tm_min,
                        created_time.tm_sec,
                        0, 0, -1)
                )

                for media_tweet in media_tweets:
                    if "extended_entities" not in media_tweet:
                        # logger.debug("メディアを含んでいないツイートです。")
                        continue
                    if "media" not in media_tweet["extended_entities"]:
                        # logger.debug("メディアを含んでいないツイートです。")
                        continue

                    media_list = media_tweet["extended_entities"]["media"]
                    for media_dict in media_list:
                        arg = (media_tweet, media_dict, atime, mtime)
                        res_list.append(arg)
            return res_list

        with ExitStack() as stack:
            mockms = stack.enter_context(patch("PictureGathering.Crawler.Crawler.TweetMediaSaver"))
            mockpa = stack.enter_context(patch("PictureGathering.PixivAPIController.PixivAPIController.DownloadIllusts"))
            mockms.return_value = 0
            mockpa.return_value = 0

            expect_called_arg = GetTweetMediaSaverCalledArg(s_tweet_list)

            actual = crawler.InterpretTweets(s_tweet_list)
            actual_called_arg = []
            for called_arg in mockms.call_args_list:
                actual_called_arg.append(called_arg[0])

            self.assertEqual(len(expect_called_arg), len(actual_called_arg))
            self.assertEqual(expect_called_arg, actual_called_arg)

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
            mockgdutgd = stack.enter_context(patch("PictureGathering.GoogleDrive.UploadToGoogleDrive"))
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
            response = MagicMock()
            status_code = PropertyMock()
            status_code.return_value = 200
            type(response).status_code = status_code
            text = PropertyMock()
            text.return_value = f'{{"text": "sample"}}'
            type(response).text = text
            mockoauth.return_value = response
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
            response = MagicMock()
            status_code = PropertyMock()
            status_code.return_value = 200
            type(response).status_code = status_code
            mockreq.return_value = response

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
            response = MagicMock()
            status_code = PropertyMock()
            status_code.return_value = 204  # 成功すると204 No Contentが返ってくる
            type(response).status_code = status_code
            mockreq.return_value = response

            str = "text"
            self.assertEqual(0, crawler.PostDiscordNotify(str))
            mockreq.assert_called_once()


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
