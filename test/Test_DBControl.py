# coding: utf-8
import json
import os
import sys
import unittest
from contextlib import ExitStack
from datetime import date, datetime, timedelta
from logging import WARNING, getLogger

import freezegun
from mock import MagicMock, PropertyMock, patch

from PictureGathering import DBController

logger = getLogger("root")
logger.setLevel(WARNING)


class TestDBController(unittest.TestCase):
    def setUp(self):
        pass

    def __GetTweetSample(self, img_url_s):
        # ツイートオブジェクトのサンプルを生成する
        tweet_url_s = 'http://www.tweet.sample.com'
        tweet_json = f'''{{
            "entities": {{
                "media": [{{
                    "expanded_url": "{tweet_url_s}"
                }}]
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

    def test_SQLText(self):
        # 使用するSQL構文をチェックする
        # 実際にDB操作はしないためmockは省略
        controlar = DBController.DBController()

        p1 = 'img_filename,url,url_thumbnail,'
        p2 = 'tweet_id,tweet_url,created_at,user_id,user_name,screan_name,tweet_text,'
        p3 = 'saved_localpath,saved_created_at'
        pn = '?,?,?,?,?,?,?,?,?,?,?,?'
        expect = 'replace into Favorite (' + p1 + p2 + p3 + ') values (' + pn + ')'
        actual = controlar._DBController__fav_sql
        self.assertEqual(expect, actual)

        p1 = 'img_filename,url,url_thumbnail,'
        p2 = 'tweet_id,tweet_url,created_at,user_id,user_name,screan_name,tweet_text,'
        p3 = 'saved_localpath,saved_created_at'
        pn = '?,?,?,?,?,?,?,?,?,?,?,?'
        expect = 'replace into Retweet (' + p1 + p2 + p3 + ') values (' + pn + ')'
        actual = controlar._DBController__retweet_sql
        self.assertEqual(expect, actual)

        p1 = 'tweet_id,delete_done,created_at,deleted_at,tweet_text,add_num,del_num'
        pn = '?,?,?,?,?,?,?'
        expect = 'replace into DeleteTarget (' + p1 + ') values (' + pn + ')'
        actual = controlar._DBController__del_sql
        self.assertEqual(expect, actual)

        limit_s = 300
        expect = 'select * from Favorite order by created_at desc limit {}'.format(limit_s)
        actual = controlar._DBController__GetFavoriteSelectSQL(limit_s)
        self.assertEqual(expect, actual)

        limit_s = 300
        expect = 'select * from Retweet where is_exist_saved_file = 1 order by created_at desc limit {}'.format(limit_s)
        actual = controlar._DBController__GetRetweetSelectSQL(limit_s)
        self.assertEqual(expect, actual)

        set_flag = 0
        file_list = ["sample_1.png", "sample_2.png"]
        filename = "'" + "','".join(file_list) + "'"
        expect = 'update Retweet set is_exist_saved_file = {} where img_filename in ({})'.format(set_flag, filename)
        actual = controlar._DBController__GetRetweetFlagUpdateSQL(filename, set_flag)
        self.assertEqual(expect, actual)

        with freezegun.freeze_time('2018-11-18 17:12:58'):
            img_url_s = 'http://www.img.filename.sample.com/media/sample.png'
            url_orig_s = img_url_s + ":orig"
            url_thumbnail_s = img_url_s + ":large"
            file_name_s = os.path.basename(url_orig_s)
            td_format_s = '%a %b %d %H:%M:%S +0000 %Y'
            dts_format_s = '%Y-%m-%d %H:%M:%S'
            tweet_s = self.__GetTweetSample(img_url_s)
            save_file_fullpath_s = os.getcwd()
            tca = tweet_s["created_at"]
            dst = datetime.strptime(tca, td_format_s)
            expect = (file_name_s,
                      url_orig_s,
                      url_thumbnail_s,
                      tweet_s["id_str"],
                      tweet_s["entities"]["media"][0]["expanded_url"],
                      dst.strftime(dts_format_s),
                      tweet_s["user"]["id_str"],
                      tweet_s["user"]["name"],
                      tweet_s["user"]["screen_name"],
                      tweet_s["text"],
                      save_file_fullpath_s,
                      datetime.now().strftime(dts_format_s))
            actual = controlar._DBController__GetUpdateParam(file_name_s, url_orig_s, url_thumbnail_s, tweet_s, save_file_fullpath_s)
            self.assertEqual(expect, actual)

    def test_DBFavUpsert(self):
        # DB操作をmockに置き換える
        with ExitStack() as stack:
            mocksql = stack.enter_context(patch('PictureGathering.DBController.sqlite3'))
            fg = stack.enter_context(freezegun.freeze_time('2018-11-18 17:12:58'))

            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            mocksql.connect().commit.return_value = 'commit done'
            controlar = DBController.DBController()

            # DB操作を伴う操作を行う
            img_url_s = 'http://www.img.filename.sample.com/media/sample.png'
            url_orig_s = img_url_s + ":orig"
            url_thumbnail_s = img_url_s + ":large"
            file_name_s = os.path.basename(url_orig_s)
            tweet_s = self.__GetTweetSample(img_url_s)
            save_file_fullpath_s = os.getcwd()
            controlar.DBFavUpsert(file_name_s, url_orig_s, url_thumbnail_s, tweet_s, save_file_fullpath_s)

            # DB操作が規定の引数で呼び出されたことを確認する
            param_s = controlar._DBController__GetUpdateParam(file_name_s, url_orig_s, url_thumbnail_s, tweet_s, save_file_fullpath_s)
            fav_sql_s = controlar._DBController__fav_sql
            mocksql.connect().cursor().execute.assert_called_once_with(fav_sql_s, param_s)

    def test_DBFavSelect(self):
        # DB操作をmockに置き換える
        with patch('PictureGathering.DBController.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'

            controlar = DBController.DBController()
            
            img_url_s = 'http://www.img.filename.sample.com/media/sample.png'
            url_orig_s = img_url_s + ":orig"
            url_thumbnail_s = img_url_s + ":large"
            file_name_s = os.path.basename(url_orig_s)
            tweet_s = self.__GetTweetSample(img_url_s)
            save_file_fullpath_s = os.getcwd()
            expect = ("rowid_sample",) + controlar._DBController__GetUpdateParam(file_name_s, url_orig_s, url_thumbnail_s, tweet_s, save_file_fullpath_s)
            mocksql.connect().cursor().execute.return_value = [expect]

            # DB操作を伴う操作を行う
            limit_s = 300
            actual = controlar.DBFavSelect(limit_s)

            # DB操作が規定の引数で呼び出されたことを確認する
            fav_select_sql_s = controlar._DBController__GetFavoriteSelectSQL(limit_s)
            mocksql.connect().cursor().execute.assert_called_once_with(fav_select_sql_s)

            # 取得した値の確認
            tweet_url_s = 'http://www.tweet.sample.com'
            self.assertEqual(img_url_s + ":orig", actual[0][2])
            self.assertEqual(tweet_url_s, actual[0][5])
            self.assertEqual(expect, actual[0])

    def test_DBRetweetUpsert(self):
        # DB操作をmockに置き換える
        with patch('PictureGathering.DBController.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            mocksql.connect().commit.return_value = 'commit done'
            controlar = DBController.DBController()

            # DB操作を伴う操作を行う
            img_url_s = 'http://www.img.filename.sample.com/media/sample.png'
            url_orig_s = img_url_s + ":orig"
            url_thumbnail_s = img_url_s + ":large"
            file_name_s = os.path.basename(url_orig_s)
            
            tweet_s = self.__GetTweetSample(img_url_s)
            save_file_fullpath_s = os.getcwd()
            controlar.DBRetweetUpsert(file_name_s, url_orig_s, url_thumbnail_s, tweet_s, save_file_fullpath_s)

            # DB操作が規定の引数で呼び出されたことを確認する
            param_s = controlar._DBController__GetUpdateParam(file_name_s, url_orig_s, url_thumbnail_s, tweet_s, save_file_fullpath_s)
            retweet_sql_s = controlar._DBController__retweet_sql
            mocksql.connect().cursor().execute.assert_called_once_with(retweet_sql_s, param_s)

    def test_DBRetweetSelect(self):
        # DB操作をmockに置き換える
        with patch('PictureGathering.DBController.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            
            controlar = DBController.DBController()

            img_url_s = 'http://www.img.filename.sample.com/media/sample.png'
            url_orig_s = img_url_s + ":orig"
            url_thumbnail_s = img_url_s + ":large"
            file_name_s = os.path.basename(url_orig_s)
            
            tweet_s = self.__GetTweetSample(img_url_s)
            save_file_fullpath_s = os.getcwd()
            expect = ("rowid_sample", "is_exist_save_file_flag_sample") + \
                controlar._DBController__GetUpdateParam(file_name_s, url_orig_s, url_thumbnail_s, tweet_s, save_file_fullpath_s)
            mocksql.connect().cursor().execute.return_value = [expect]

            # DB操作を伴う操作を行う
            limit_s = 300
            actual = controlar.DBRetweetSelect(limit_s)

            # DB操作が規定の引数で呼び出されたことを確認する
            retweet_select_sql_s = controlar._DBController__GetRetweetSelectSQL(limit_s)
            mocksql.connect().cursor().execute.assert_called_once_with(retweet_select_sql_s)

            # 取得した値の確認
            tweet_url_s = 'http://www.tweet.sample.com'
            self.assertEqual(img_url_s + ":orig", actual[0][3])
            self.assertEqual(tweet_url_s, actual[0][6])
            self.assertEqual(expect, actual[0])

    def test_DBRetweetFlagUpdate(self):
        # DB操作をmockに置き換える
        with patch('PictureGathering.DBController.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            mocksql.connect().commit.return_value = 'commit done'
            controlar = DBController.DBController()

            # DB操作を伴う操作を行う
            set_flag = 0
            file_list = ["sample_1.png", "sample_2.png"]
            filename = "'" + "','".join(file_list) + "'"
            controlar.DBRetweetFlagUpdate(file_list, set_flag)

            # DB操作が規定の引数で呼び出されたことを確認する
            retweet_flag_update_sql_s = controlar._DBController__GetRetweetFlagUpdateSQL(filename, set_flag)
            mocksql.connect().cursor().execute.assert_called_once_with(retweet_flag_update_sql_s)

    def test_DBRetweetFlagClear(self):
        # DB操作をmockに置き換える
        with patch('PictureGathering.DBController.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            mocksql.connect().commit.return_value = 'commit done'
            controlar = DBController.DBController()

            # DB操作を伴う操作を行う
            controlar.DBRetweetFlagClear()

            # DB操作が規定の引数で呼び出されたことを確認する
            retweet_flag_clear_sql_s = controlar._DBController__GetRetweetFlagClearSQL()
            mocksql.connect().cursor().execute.assert_called_once_with(retweet_flag_clear_sql_s)

    def test_DBDelInsert(self):
        # DB操作をmockに置き換える
        with patch('PictureGathering.DBController.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            mocksql.connect().commit.return_value = 'commit done'
            controlar = DBController.DBController()

            # DB操作を伴う操作を行う
            del_tweet_s = self.__GetDelTweetSample()
            controlar.DBDelInsert(del_tweet_s)

            # DB操作が規定の引数で呼び出されたことを確認する
            param_s = controlar._DBController__GetDelUpdateParam(del_tweet_s)
            mocksql.connect().cursor().execute.assert_called_once_with(controlar._DBController__del_sql, param_s)

    def test_DBDelSelect(self):
        # DB操作をmockに置き換える
        with patch('PictureGathering.DBController.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            mocksql.connect().commit.return_value = 'commit done'
            controlar = DBController.DBController()

            del_tweet_s = self.__GetDelTweetSample()
            expect = ("rowid_sample",) + controlar._DBController__GetDelUpdateParam(del_tweet_s)
            mocksql.connect().cursor().execute.return_value = [expect]

            t = date.today() - timedelta(1)
            w = "delete_done = 0 and created_at < '{}'".format(t.strftime('%Y-%m-%d'))
            expect_select_sql_s = "select * from DeleteTarget where " + w
            u = "delete_done = 1, deleted_at = '{}'".format(t.strftime('%Y-%m-%d'))
            expect_update_sql_s = "update DeleteTarget set {} where {}".format(u, w)

            # DB操作を伴う操作を行う
            actual = controlar.DBDelSelect()

            # DB操作が規定の引数で呼び出されたことを確認する
            mocksql.connect().cursor().execute.assert_any_call(expect_select_sql_s)
            mocksql.connect().cursor().execute.assert_any_call(expect_update_sql_s)

            # 取得した値の確認
            self.assertEqual(expect, actual[0])


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main()
