# coding: utf-8
"""RTクローラーのテスト

RetweetCrawler.RetweetCrawler()の各種機能をテストする
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

from PictureGathering import RetweetCrawler, PixivAPIController

logger = getLogger("root")
logger.setLevel(WARNING)


class TestRetweetCrawler(unittest.TestCase):
    """RetweetCrawlerテストメインクラス
    """

    def setUp(self):
        pass

    def __GetExtendedEntitiesSample(self, media_url: str = "", media_type: str = "None") -> dict:
        """ツイートオブジェクトのサンプルの一部を生成する

        Args:
            media_url (str): 画像URLサンプル
            media_type (str): メディアタイプ{"None", "photo", "video", "animated_gif"}

        Returns:
            dict: ツイートオブジェクトのextended_entities部分（サンプル）、"None"指定時orエラー時空辞書
        """
        # extended_entities
        tweet_json = ""
        if media_type == "photo":
            r1 = "{:0>5}".format(random.randint(0, 99999))
            r2 = "{:0>5}".format(random.randint(0, 99999))
            tweet_json = f'''{{
                "extended_entities": {{
                    "media": [{{
                        "type": "photo",
                        "media_url": "{media_url}_{r1}"
                    }},
                    {{
                        "type": "photo",
                        "media_url": "{media_url}_{r2}"
                    }}]
                }}
            }}'''
        elif media_type == "video":
            tweet_json = f'''{{
                "extended_entities": {{
                    "media": [{{
                        "type": "video",
                        "media_url": "{media_url}",
                        "video_info": {{
                            "variants":[{{
                                "content_type": "video/mp4",
                                "bitrate": 640,
                                "url": "{media_url}_640"
                            }},
                            {{
                                "content_type": "video/mp4",
                                "bitrate": 2048,
                                "url": "{media_url}_2048"
                            }},
                            {{
                                "content_type": "video/mp4",
                                "bitrate": 1024,
                                "url": "{media_url}_1024"
                            }}]
                        }}
                    }}]
                }}
            }}'''
        elif media_type == "animated_gif":
            tweet_json = f'''{{
                "extended_entities": {{
                    "media": [{{
                        "type": "animated_gif",
                        "media_url": "{media_url}",
                        "video_info": {{
                            "variants":[{{
                                "content_type": "video/mp4",
                                "bitrate": 0,
                                "url": "{media_url}"
                            }}]
                        }}
                    }}]
                }}
            }}'''
        elif media_type == "None":
            pass
        else:
            return {}

        if tweet_json != "":
            extended_entities = json.loads(tweet_json)
            return extended_entities
        else:
            return {}

    def __GetTweetSample(self, media_url: str = "", media_type: str = "None", is_retweeted: bool = False, is_quoted: bool = False, is_pixiv: bool = False) -> dict:
        """ツイートオブジェクトのサンプルを生成する

        Args:
            media_url (str): 画像URLサンプル
            media_type (str): メディアタイプ{"None", "photo", "video", "animated_gif"}
            is_retweeted (bool): RTフラグ
            is_quoted (bool): 引用RTフラグ
            is_pixiv (bool): 本文中にpixivリンクを含めるか

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
            "text": "tweet_text_sample_{r}",
            "retweeted": false
        }}'''
        base_tweet = json.loads(tweet_json)  # ベース生成
        tweet = dict(base_tweet)

        # media_url
        if media_type != "None":
            tweet["media_url"] = media_url

            # extended_entities
            extended_entities = self.__GetExtendedEntitiesSample(media_url, media_type)

            if "extended_entities" in extended_entities:
                tweet["extended_entities"] = extended_entities["extended_entities"]
            else:
                return {}
        
        # RTフラグ, 引用RTフラグ
        extended_entities = self.__GetExtendedEntitiesSample(media_url, "photo")
        media_tweet = dict(tweet)
        r = "{:0>5}".format(random.randint(0, 99999))
        media_tweet["id"] = int(r)
        media_tweet["id_str"] = r
        media_tweet["text"] = media_tweet["text"] + "_" + r
        media_tweet["extended_entities"] = extended_entities["extended_entities"]
        if is_retweeted and (not is_quoted):
            tweet["retweeted_status"] = media_tweet
            tweet["retweeted_status"]["retweeted"] = True
            tweet["retweeted"] = True
        elif (not is_retweeted) and is_quoted:
            tweet["quoted_status"] = media_tweet
            tweet["quoted_status"]["retweeted"] = True
            tweet["retweeted"] = True
            tweet["is_quote_status"] = True
        elif is_retweeted and is_quoted:
            quoted_tweet = dict(media_tweet)
            quoted_tweet["quoted_status"] = media_tweet
            quoted_tweet["quoted_status"]["retweeted"] = True
            quoted_tweet["retweeted"] = True
            quoted_tweet["is_quote_status"] = True
            del quoted_tweet["extended_entities"]
            tweet["retweeted_status"] = quoted_tweet
            # tweet["retweeted_status"]["retweeted"] = True
            tweet["retweeted"] = True
        else:
            pass

        # pixivリンク
        if is_pixiv:
            r = "{:0>8}".format(random.randint(0, 99999999))
            pixiv_url = "https://www.pixiv.net/artworks/{}".format(r)
            tweet["text"] = tweet["text"] + " " + pixiv_url
            tweet_json = f'''{{
                "entities": {{
                    "urls": [{{
                        "expanded_url": "{pixiv_url}"
                    }}]
                }}
            }}'''
            entities = json.loads(tweet_json)
            tweet["entities"] = entities["entities"]

        return tweet

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
        self.assertTrue(Path(CONFIG_FILE_NAME).is_file())
        self.assertFalse(expect_config.read("ERROR_PATH" + CONFIG_FILE_NAME, encoding="utf8"))
        expect_config.read(CONFIG_FILE_NAME, encoding="utf8")

        # 存在しないキーを指定するテスト
        with self.assertRaises(KeyError):
            print(expect_config["ERROR_KEY1"]["ERROR_KEY2"])

        # 設定値比較
        expect = int(expect_config["tweet_timeline"]["retweet_get_max_loop"])
        actual = rc.retweet_get_max_loop
        self.assertEqual(expect, actual)

        expect = Path(expect_config["save_directory"]["save_retweet_path"])
        actual = rc.save_path
        self.assertEqual(expect, actual)

        self.assertIsNone(rc.max_id)
        self.assertEqual("RT", rc.type)

    def test_RetweetsGet(self):
        """RT取得機能をチェックする
        """

        rc = RetweetCrawler.RetweetCrawler()

        with ExitStack() as stack:
            mockdbrfc = stack.enter_context(patch("PictureGathering.RetweetDBController.RetweetDBController.FlagClear"))
            mockdbrfu = stack.enter_context(patch("PictureGathering.RetweetDBController.RetweetDBController.FlagUpdate"))
            mockapireq = stack.enter_context(patch("PictureGathering.Crawler.Crawler.TwitterAPIRequest"))
            
            # GetExistFilelistはrc本来のものを使うが結果を保持して比較するためにモックにしておく
            s_exist_filepaths = rc.GetExistFilelist()
            mockdgefl = stack.enter_context(patch("PictureGathering.Crawler.Crawler.GetExistFilelist"))
            mockdgefl.return_value = s_exist_filepaths

            # 既存ファイル一覧を取得する
            s_exist_filenames = []
            for s_exist_filepath in s_exist_filepaths:
                s_exist_filenames.append(Path(s_exist_filepath).name)
            if s_exist_filenames:
                exist_oldest_filename = s_exist_filenames[-1]
            else:
                exist_oldest_filename = ""

            # 取得ツイートサンプル作成
            s_media_url = "http://pbs.twimg.com/media/add_sample{}.jpg:orig"
            s_nrt_t = [self.__GetTweetSample(s_media_url.format(i), "photo") for i in range(3)]
            s_nm_t = [self.__GetTweetSample(s_media_url.format(i), "None") for i in range(3)]
            s_rt_t = [self.__GetTweetSample(s_media_url.format(i), "photo", True) for i in range(3)]
            s_quote_t = [self.__GetTweetSample(s_media_url.format(i), "photo", False, True) for i in range(3)]
            s_rt_quote_t = [self.__GetTweetSample(s_media_url.format(i), "photo", True, True) for i in range(3)]
            s_rt_pixiv_t = [self.__GetTweetSample(s_media_url.format(i), "None", True, False, True) for i in range(3)]
            s_t = s_nrt_t + s_nm_t + s_rt_t + s_quote_t + s_rt_quote_t + s_rt_pixiv_t
            random.shuffle(s_t)
            import copy
            s_t_expect = copy.deepcopy(s_t)
            s_se = [[s_t[0]],
                    [s_t[1], s_t[2]],
                    [s_t[3], s_t[4], s_t[5]],
                    [s_t[6], s_t[7], s_t[8]],
                    [s_t[9], s_t[10], s_t[11]],
                    [s_t[12], s_t[13], s_t[14]],
                    [s_t[15], s_t[16], s_t[17]]]
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
            s_expect_filenames = []
            for t in s_t_expect:
                rt_flag = t.get("retweeted")
                quote_flag = t.get("is_quote_status")
                if not (rt_flag or quote_flag):
                    continue

                media_tweets = rc.GetMediaTweet(t)
                
                if not media_tweets:
                    continue

                for media_tweet in media_tweets:
                    media_tweet["created_at"] = media_tweets[0]["created_at"]

                    entities = media_tweet.get("extended_entities")
                    include_new_flag = False
                    if not entities:
                        if media_tweet.get("entities").get("urls"):
                            e_urls = media_tweet["entities"]["urls"]
                            IsPixivURL = PixivAPIController.PixivAPIController.IsPixivURL
                            for element in e_urls:
                                expanded_url = element.get("expanded_url")
                                if IsPixivURL(expanded_url):
                                    include_new_flag = True
                        pass
                    else:
                        for entity in entities["media"]:
                            media_url = rc.GetMediaUrl(entity)
                            filename = Path(media_url).name

                            if filename not in s_exist_filenames:
                                if filename not in s_expect_filenames:
                                    include_new_flag = True
                                    s_expect_filenames.append(filename)

                    if include_new_flag:
                        if media_tweet.get("retweeted") and media_tweet.get("retweeted_status"):
                            media_tweet["retweeted"] = False
                            media_tweet["retweeted_status"] = {"modified_by_crawler": True}
                        if media_tweet.get("is_quote_status") and media_tweet.get("quoted_status"):
                            media_tweet["is_quote_status"] = False
                            media_tweet["quoted_status"] = {"modified_by_crawler": True}
                        
                        expect.append(media_tweet)

            expect.reverse()

            self.assertEqual(len(expect), len(actual))
            self.assertEqual(expect, actual)

    def test_UpdateDBExistMark(self):
        """存在マーキング更新機能呼び出しをチェックする
        """

        rc = RetweetCrawler.RetweetCrawler()

        with ExitStack() as stack:
            mockdbcc = stack.enter_context(patch("PictureGathering.RetweetDBController.RetweetDBController.FlagClear"))
            mockdbcu = stack.enter_context(patch("PictureGathering.RetweetDBController.RetweetDBController.FlagUpdate"))

            s_add_img_filename = ["sample1.jpg", "sample2.jpg", "sample3.jpg"]
            rc.UpdateDBExistMark(s_add_img_filename)

            mockdbcc.assert_called_once_with()
            mockdbcu.assert_called_once_with(s_add_img_filename, 1)

    def test_GetVideoURL(self):
        """動画URL取得機能をチェックする
        """

        rc = RetweetCrawler.RetweetCrawler()

        def MakeMediaURL(filename):
            dic = {"url": "https://video.twimg.com/ext_tw_video/1139678486296031232/pu/vid/640x720/{0}?tag=10".format(filename)}
            return [dic]

        with ExitStack() as stack:
            mockdbcv = stack.enter_context(patch("PictureGathering.RetweetDBController.RetweetDBController.SelectFromMediaURL"))
            s_filename = "sample.mp4"

            # 正常系
            mockdbcv.side_effect = MakeMediaURL
            expect = MakeMediaURL(s_filename)[0]["url"]
            actual = rc.GetMediaURL(s_filename)
            self.assertEqual(expect, actual)

            # エラーケース
            mockdbcv.side_effect = None
            expect = ""
            actual = rc.GetMediaURL(s_filename)
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
            s_retweet_tweet_list = [self.__GetTweetSample(s_media_url_list[i], "photo") for i in range(6)]

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
