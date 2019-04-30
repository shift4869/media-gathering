# coding: utf-8
import configparser
from datetime import datetime
from datetime import date
from datetime import timedelta
import json
from mock import patch
import os
from requests_oauthlib import OAuth1Session
import unittest

import freezegun

import DBControlar
import PictureGathering_fav


class TestCrawler(unittest.TestCase):
    def setUp(self):
        self.CONFIG_FILE_NAME = "config.ini"

        self.img_url_s = 'http://www.img.filename.sample.com/media/sample.png'
        self.img_filename_s = os.path.basename(self.img_url_s)
        self.tweet_url_s = 'http://www.tweet.sample.com'
        self.save_file_fullpath_s = os.getcwd()
        self.tweet_s = self.__GetTweetSample(self.img_url_s)
        self.del_tweet_s = self.__GetDelTweetSample()
        self.media_tweet_s = self.__GetMediaTweetSample(self.img_url_s)

    def __GetMediaTweetSample(self, img_url_s):
        # ツイートオブジェクトのサンプルを生成する
        tweet_json = f'''{{
            "extended_entities": {{
                "media": [{{
                    "media_url": "{img_url_s}_1"
                }},
                {{
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

    def __GetTweetSample(self, img_url_s):
        # ツイートオブジェクトのサンプルを生成する
        tweet_json = f'''{{
            "entities": {{
                "media": {{
                    "expanded_url": "{self.tweet_url_s}"
                }}
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

    def __GetDelTweetSample(self):
        # ツイートオブジェクトのサンプルを生成する
        tweet_json = f'''{{
            "created_at": "Sat Nov 18 17:12:58 +0000 2018",
            "id_str": "12345_id_str_sample",
            "text": "@s_shift4869 PictureGathering run.\\n2018/03/09 11:59:38 Process Done !!\\nadd 1 new images. delete 0 old images."
        }}'''
        tweet_s = json.loads(tweet_json)
        return tweet_s

    def test_CrawlerInit(self):
        # Crawlerの初期状態をテストする
        crawler = PictureGathering_fav.Crawler()

        # config
        expect_config = configparser.ConfigParser()
        self.assertTrue(os.path.exists(self.CONFIG_FILE_NAME))
        self.assertFalse(
            expect_config.read("ERROR_PATH" + self.CONFIG_FILE_NAME, encoding="utf8")
        )
        expect_config.read(self.CONFIG_FILE_NAME, encoding="utf8")

        with self.assertRaises(KeyError):
            print(expect_config["ERROR_KEY1"]["ERROR_KEY2"])

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

        self.assertEqual(os.path.abspath(expect_config["save_directory"]["save_fav_path"]),
                         crawler.save_fav_path)
        self.assertTrue(os.path.exists(crawler.save_fav_path))
        # self.assertEqual(os.path.abspath(expect_config["save_directory"]["save_retweet_path"]),
        #                  crawler.save_retweet_path)
        # self.assertTrue(os.path.exists(crawler.save_retweet_path))

        self.assertEqual(expect_config["tweet_timeline"]["user_name"],
                         crawler.user_name)
        # self.assertEqual(int(expect_config["tweet_timeline"]["retweet_get_max_loop"]),
        #                  crawler.retweet_get_max_loop)
        self.assertEqual(int(expect_config["tweet_timeline"]["get_pages"]) + 1,
                         crawler.get_pages)
        self.assertEqual(int(expect_config["tweet_timeline"]["count"]),
                         crawler.count)
        self.assertIn(crawler.config["tweet_timeline"]["kind_of_timeline"],
                      ["favorite", "home"])

        self.assertIn(expect_config["timestamp"]["timestamp_created_at"],
                      crawler.config["timestamp"]["timestamp_created_at"])

        self.assertIn(expect_config["notification"]["is_post_fav_done_reply"],
                      crawler.config["notification"]["is_post_fav_done_reply"])
        self.assertIn(expect_config["notification"]["is_post_retweet_done_reply"],
                      crawler.config["notification"]["is_post_retweet_done_reply"])
        self.assertIn(expect_config["notification"]["reply_to_user_name"],
                      crawler.config["notification"]["reply_to_user_name"])
        self.assertIn(expect_config["notification"]["is_post_line_notify"],
                      crawler.config["notification"]["is_post_line_notify"])

        self.assertIn(expect_config["holding"]["holding_file_num"],
                      crawler.config["holding"]["holding_file_num"])

        self.assertIn(expect_config["processes"]["image_magick"],
                      crawler.config["processes"]["image_magick"])
        if crawler.config["processes"]["image_magick"] != "":
            self.assertTrue(os.path.exists(crawler.config["processes"]["image_magick"]))

        self.assertIsInstance(crawler.oath, OAuth1Session)

    def test_TwitterAPIRequest(self):
        pass
        # TwitterAPIの応答をチェックする
        # crawler = PictureGathering_fav.Crawler()

        # url = "https://api.twitter.com/1.1/favorites/list.json"
        # params = {
        #     "screen_name": self.user_name,
        #     "page": page,
        #     "count": self.count,
        #     "include_entities": 1  # ツイートのメタデータ取得。複数枚の画像取得用。
        # }

        # p1 = 'img_filename,url,url_large,'
        # p2 = 'tweet_id,tweet_url,created_at,user_id,user_name,screan_name,tweet_text,'
        # p3 = 'saved_localpath,saved_created_at'
        # pn = '?,?,?,?,?,?,?,?,?,?,?,?'
        # expect = 'replace into Favorite (' + p1 + p2 + p3 + ') values (' + pn + ')'
        # actual = controlar._DBControlar__fav_sql
        # self.assertEqual(expect, actual)

        # with freezegun.freeze_time('2018-11-18 17:12:58'):
        #     url_orig_s = self.img_url_s + ":orig"
        #     td_format_s = '%a %b %d %H:%M:%S +0000 %Y'
        #     dts_format_s = '%Y-%m-%d %H:%M:%S'
        #     tca = self.tweet_s["created_at"]
        #     dst = datetime.strptime(tca, td_format_s)
        #     expect = (os.path.basename(self.img_url_s),
        #               url_orig_s,
        #               self.img_url_s + ":large",
        #               self.tweet_s["id_str"],
        #               self.tweet_s["entities"]["media"][0]["expanded_url"],
        #               dst.strftime(dts_format_s),
        #               self.tweet_s["user"]["id_str"],
        #               self.tweet_s["user"]["name"],
        #               self.tweet_s["user"]["screen_name"],
        #               self.tweet_s["text"],
        #               self.save_file_fullpath_s,
        #               datetime.now().strftime(dts_format_s))
        #     actual = controlar._DBControlar__GetUpdateParam(self.img_url_s, self.tweet_s, self.save_file_fullpath_s)
        #     self.assertEqual(expect, actual)

    # def test_DBFavUpsert(self):
    #     # DB操作をモックに置き換える
    #     with patch('DBControlar.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
    #         mocksql.connect().cursor().execute.return_value = 'execute sql done'
    #         mocksql.connect().commit.return_value = 'commit done'
    #         controlar = DBControlar.DBControlar()

    #         # DB操作を伴う操作を行う
    #         controlar.DBFavUpsert(self.img_url_s, self.tweet_s, self.save_file_fullpath_s)

    #         # DB操作が規定の引数で呼び出されたことを確認する
    #         param_s = controlar._DBControlar__GetUpdateParam(self.img_url_s, self.tweet_s, self.save_file_fullpath_s)
    #         fav_sql_s = controlar._DBControlar__fav_sql
    #         mocksql.connect().cursor().execute.assert_called_once_with(fav_sql_s, param_s)


if __name__ == "__main__":
    unittest.main()
