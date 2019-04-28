# coding: utf-8
from datetime import datetime
from datetime import date
from datetime import timedelta
from mock import patch
import os
import unittest

import freezegun

import DBControlar


class TestDBControlar(unittest.TestCase):
    def setUp(self):
        self.img_url_s = 'http://www.img.filename.sample.com/media/sample.png'
        self.img_filename_s = os.path.basename(self.img_url_s)
        self.tweet_url_s = 'http://www.tweet.sample.com'
        self.save_file_fullpath_s = os.getcwd()
        self.tweet_s = self.__GetTweetSample(self.img_url_s)
        self.del_tweet_s = self.__GetDelTweetSample()

    def __GetTweetSample(self, img_url_s):
        # ツイートオブジェクトのサンプルを生成する
        tweet_s = {}
        tweet_s.setdefault("entities", {})
        tweet_s["entities"].setdefault("media", [])
        tweet_s["entities"]["media"].append({"expanded_url": self.tweet_url_s})
        tweet_s.setdefault("created_at", "Sat Nov 18 17:12:58 +0000 2018")
        tweet_s.setdefault("user", {})
        tweet_s.setdefault("id_str", "12345_id_str_sample")
        tweet_s["user"].setdefault("id_str", "12345_id_str_sample")
        tweet_s["user"].setdefault("name", "shift_name_sample")
        tweet_s["user"].setdefault("screen_name", "_shift4869_screen_name_sample")
        tweet_s.setdefault("text", "tweet_text_sample")
        return tweet_s

    def __GetDelTweetSample(self):
        # ツイートオブジェクトのサンプルを生成する
        tweet_s = {}
        tweet_s.setdefault("text", "@s_shift4869 PictureGathering run.\n2018/03/09 11:59:38 Process Done !!\nadd 1 new images. delete 0 old images.")
        tweet_s.setdefault("created_at", "Sat Nov 18 17:12:58 +0000 2018")
        tweet_s.setdefault("id_str", "12345_id_str_sample")
        return tweet_s

    def test_SQLText(self):
        # 使用するSQL構文をチェックする
        # 実際にDB操作はしないためモックは省略
        controlar = DBControlar.DBControlar()

        p1 = 'img_filename,url,url_large,'
        p2 = 'tweet_id,tweet_url,created_at,user_id,user_name,screan_name,tweet_text,'
        p3 = 'saved_localpath,saved_created_at'
        pn = '?,?,?,?,?,?,?,?,?,?,?,?'
        expect = 'replace into Favorite (' + p1 + p2 + p3 + ') values (' + pn + ')'
        actual = controlar._DBControlar__fav_sql
        self.assertEqual(expect, actual)

        p1 = 'img_filename,url,url_large,'
        p2 = 'tweet_id,tweet_url,created_at,user_id,user_name,screan_name,tweet_text,'
        p3 = 'saved_localpath,saved_created_at'
        pn = '?,?,?,?,?,?,?,?,?,?,?,?'
        expect = 'replace into Retweet (' + p1 + p2 + p3 + ') values (' + pn + ')'
        actual = controlar._DBControlar__retweet_sql
        self.assertEqual(expect, actual)

        p1 = 'tweet_id,delete_done,created_at,deleted_at,tweet_text,add_num,del_num'
        pn = '?,?,?,?,?,?,?'
        expect = 'replace into DeleteTarget (' + p1 + ') values (' + pn + ')'
        actual = controlar._DBControlar__del_sql
        self.assertEqual(expect, actual)

        limit_s = 300
        expect = 'select * from Favorite order by id desc limit {}'.format(limit_s)
        actual = controlar._DBControlar__GetFavoriteSelectSQL(limit_s)
        self.assertEqual(expect, actual)

        limit_s = 300
        expect = 'select * from Retweet where is_exist_saved_file = \'True\' order by id desc limit {}'.format(limit_s)
        actual = controlar._DBControlar__GetRetweetSelectSQL(limit_s)
        self.assertEqual(expect, actual)

        expect = 'update Retweet set is_exist_saved_file = 0 where img_filename = \'{}\''.format(self.img_filename_s)
        actual = controlar._DBControlar__GetRetweetFlagUpdateSQL(self.img_filename_s)
        self.assertEqual(expect, actual)

        with freezegun.freeze_time('2018-11-18 17:12:58'):
            url_orig_s = self.img_url_s + ":orig"
            td_format_s = '%a %b %d %H:%M:%S +0000 %Y'
            dts_format_s = '%Y-%m-%d %H:%M:%S'
            tca = self.tweet_s["created_at"]
            dst = datetime.strptime(tca, td_format_s)
            expect = (os.path.basename(self.img_url_s),
                      url_orig_s,
                      self.img_url_s + ":large",
                      self.tweet_s["id_str"],
                      self.tweet_s["entities"]["media"][0]["expanded_url"],
                      dst.strftime(dts_format_s),
                      self.tweet_s["user"]["id_str"],
                      self.tweet_s["user"]["name"],
                      self.tweet_s["user"]["screen_name"],
                      self.tweet_s["text"],
                      self.save_file_fullpath_s,
                      datetime.now().strftime(dts_format_s))
            actual = controlar._DBControlar__GetUpdateParam(self.img_url_s, self.tweet_s, self.save_file_fullpath_s)
            self.assertEqual(expect, actual)

    def test_DBFavUpsert(self):
        # DB操作をモックに置き換える
        with patch('DBControlar.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            mocksql.connect().commit.return_value = 'commit done'
            controlar = DBControlar.DBControlar()

            # DB操作を伴う操作を行う
            controlar.DBFavUpsert(self.img_url_s, self.tweet_s, self.save_file_fullpath_s)

            # DB操作が規定の引数で呼び出されたことを確認する
            param_s = controlar._DBControlar__GetUpdateParam(self.img_url_s, self.tweet_s, self.save_file_fullpath_s)
            fav_sql_s = controlar._DBControlar__fav_sql
            mocksql.connect().cursor().execute.assert_called_once_with(fav_sql_s, param_s)

    def test_DBFavSelect(self):
        # DB操作をモックに置き換える
        with patch('DBControlar.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            controlar = DBControlar.DBControlar()
            expect = ("rowid_sample",) + controlar._DBControlar__GetUpdateParam(self.img_url_s, self.tweet_s, self.save_file_fullpath_s)
            mocksql.connect().cursor().execute.return_value = [expect]

            # DB操作を伴う操作を行う
            limit_s = 300
            actual = controlar.DBFavSelect(limit_s)

            # DB操作が規定の引数で呼び出されたことを確認する
            fav_select_sql_s = controlar._DBControlar__GetFavoriteSelectSQL(limit_s)
            mocksql.connect().cursor().execute.assert_called_once_with(fav_select_sql_s)

            # 取得した値の確認
            self.assertEqual(self.img_url_s + ":orig", actual[0][2])
            self.assertEqual(self.tweet_url_s, actual[0][5])
            self.assertEqual(expect, actual[0])

    def test_DBRetweetUpsert(self):
        # DB操作をモックに置き換える
        with patch('DBControlar.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            mocksql.connect().commit.return_value = 'commit done'
            controlar = DBControlar.DBControlar()

            # DB操作を伴う操作を行う
            controlar.DBRetweetUpsert(self.img_url_s, self.tweet_s, self.save_file_fullpath_s)

            # DB操作が規定の引数で呼び出されたことを確認する
            param_s = controlar._DBControlar__GetUpdateParam(self.img_url_s, self.tweet_s, self.save_file_fullpath_s)
            retweet_sql_s = controlar._DBControlar__retweet_sql
            mocksql.connect().cursor().execute.assert_called_once_with(retweet_sql_s, param_s)

    def test_DBRetweetSelect(self):
        # DB操作をモックに置き換える
        with patch('DBControlar.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            controlar = DBControlar.DBControlar()
            expect = ("rowid_sample", "is_exist_save_file_flag_sample") + controlar._DBControlar__GetUpdateParam(self.img_url_s, self.tweet_s, self.save_file_fullpath_s)
            mocksql.connect().cursor().execute.return_value = [expect]

            # DB操作を伴う操作を行う
            limit_s = 300
            actual = controlar.DBRetweetSelect(limit_s)

            # DB操作が規定の引数で呼び出されたことを確認する
            retweet_select_sql_s = controlar._DBControlarar__GetRetweetSelectSQL(limit_s)
            mocksql.connect().cursor().execute.assert_called_once_with(retweet_select_sql_s)

            # 取得した値の確認
            self.assertEqual(self.img_url_s + ":orig", actual[0][3])
            self.assertEqual(self.tweet_url_s, actual[0][6])
            self.assertEqual(expect, actual[0])

    def test_DBRetweetFlagUpdate(self):
        # DB操作をモックに置き換える
        with patch('DBControlar.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            mocksql.connect().commit.return_value = 'commit done'
            controlar = DBControlar.DBControlar()

            # DB操作を伴う操作を行う
            controlar.DBRetweetFlagUpdate(self.img_filename_s)

            # DB操作が規定の引数で呼び出されたことを確認する
            retweet_flag_update_sql_s = controlar._DBControlar__GetRetweetFlagUpdateSQL(self.img_filename_s)
            mocksql.connect().cursor().execute.assert_called_once_with(retweet_flag_update_sql_s)

    def test_DBDelInsert(self):
        # DB操作をモックに置き換える
        with patch('DBControlar.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            mocksql.connect().commit.return_value = 'commit done'
            controlar = DBControlar.DBControlar()

            # DB操作を伴う操作を行う
            controlar.DBDelInsert(self.del_tweet_s)

            # DB操作が規定の引数で呼び出されたことを確認する
            param_s = controlar._DBControlar__GetDelUpdateParam(self.del_tweet_s)
            mocksql.connect().cursor().execute.assert_called_once_with(controlar._DBControlar__del_sql, param_s)

    def test_DBDelSelect(self):
        # DB操作をモックに置き換える
        with patch('DBControlar.sqlite3') as mocksql, freezegun.freeze_time('2018-11-18 17:12:58'):
            mocksql.connect().cursor().execute.return_value = 'execute sql done'
            mocksql.connect().commit.return_value = 'commit done'
            controlar = DBControlar.DBControlar()

            expect = ("rowid_sample",) + controlar._DBControlar__GetDelUpdateParam(self.del_tweet_s)
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
    unittest.main()
