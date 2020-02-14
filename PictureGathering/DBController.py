# coding: utf-8
import configparser
import os
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta


class DBController:
    dbname = 'PG_DB.db'

    def __init__(self):
        self.__fav_sql = self.__GetFavoriteUpsertSQL()
        self.__retweet_sql = self.__GetRetweetUpsertSQL()
        self.__del_sql = self.__GetDeleteTargetUpsertSQL()

    def __GetFavoriteUpsertSQL(self):
        p1 = 'img_filename,url,url_thumbnail,'
        p2 = 'tweet_id,tweet_url,created_at,user_id,user_name,screan_name,tweet_text,'
        p3 = 'saved_localpath,saved_created_at'
        pn = '?,?,?,?,?,?,?,?,?,?,?,?'
        return 'replace into Favorite (' + p1 + p2 + p3 + ') values (' + pn + ')'

    def __GetRetweetUpsertSQL(self):
        p1 = 'img_filename,url,url_thumbnail,'
        p2 = 'tweet_id,tweet_url,created_at,user_id,user_name,screan_name,tweet_text,'
        p3 = 'saved_localpath,saved_created_at'
        pn = '?,?,?,?,?,?,?,?,?,?,?,?'
        return 'replace into Retweet (' + p1 + p2 + p3 + ') values (' + pn + ')'

    def __GetDeleteTargetUpsertSQL(self):
        p1 = 'tweet_id,delete_done,created_at,deleted_at,tweet_text,add_num,del_num'
        pn = '?,?,?,?,?,?,?'
        return 'replace into DeleteTarget (' + p1 + ') values (' + pn + ')'

    def __GetFavoriteSelectSQL(self, limit=300):
        return 'select * from Favorite order by created_at desc limit {}'.format(limit)

    def __GetFavoriteVideoURLSelectSQL(self, filename):
        # filenameはシングルクォート必要、カンマ区切りOK
        return 'select * from Favorite where img_filename = {}'.format(filename)

    def __GetRetweetSelectSQL(self, limit=300):
        return 'select * from Retweet where is_exist_saved_file = 1 order by created_at desc limit {}'.format(limit)

    def __GetRetweetVideoURLSelectSQL(self, filename):
        # filenameはシングルクォート必要、カンマ区切りOK
        return 'select * from Retweet where img_filename = {}'.format(filename)

    def __GetRetweetFlagUpdateSQL(self, filename="", set_flag=0):
        # filenameはシングルクォート必要、カンマ区切りOK
        return 'update Retweet set is_exist_saved_file = {} where img_filename in ({})'.format(set_flag, filename)

    def __GetRetweetFlagClearSQL(self):
        return 'update Retweet set is_exist_saved_file = 0'

    def __GetUpdateParam(self, file_name, url_orig, url_thumbnail, tweet, save_file_fullpath):
        # img_filename,url,url_thumbnail,tweet_id,tweet_url,created_at,
        # user_id,user_name,screan_name,tweet_text,saved_localpath,saved_created_at
        td_format = '%a %b %d %H:%M:%S +0000 %Y'
        dts_format = '%Y-%m-%d %H:%M:%S'
        tca = tweet["created_at"]
        dst = datetime.strptime(tca, td_format)
        text = tweet["text"] if "text" in tweet else tweet["full_text"]
        param = (file_name,
                 url_orig,
                 url_thumbnail,
                 tweet["id_str"],
                 tweet["entities"]["media"][0]["expanded_url"],
                 dst.strftime(dts_format),
                 tweet["user"]["id_str"],
                 tweet["user"]["name"],
                 tweet["user"]["screen_name"],
                 text,
                 save_file_fullpath,
                 datetime.now().strftime(dts_format))
        return param

    def __GetDelUpdateParam(self, tweet):
        pattern = ' +[0-9]* '
        text = tweet["text"]
        add_num = int(re.findall(pattern, text)[0])
        del_num = int(re.findall(pattern, text)[1])
        td_format = '%a %b %d %H:%M:%S +0000 %Y'
        dts_format = '%Y-%m-%d %H:%M:%S'

        tca = tweet["created_at"]
        dst = datetime.strptime(tca, td_format)
        param = (tweet["id_str"],
                 False,
                 dst.strftime(dts_format),
                 None,
                 tweet["text"],
                 add_num,
                 del_num)
        return param

    def DBFavUpsert(self, file_name, url_orig, url_thumbnail, tweet, save_file_fullpath):
        with closing(sqlite3.connect(self.dbname)) as conn:
            c = conn.cursor()
            param = self.__GetUpdateParam(file_name, url_orig, url_thumbnail, tweet, save_file_fullpath)
            c.execute(self.__fav_sql, param)
            conn.commit()

    def DBFavSelect(self, limit=300):
        with closing(sqlite3.connect(self.dbname)) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            query = self.__GetFavoriteSelectSQL(limit)
            res = list(c.execute(query))
        return res

    def DBFavVideoURLSelect(self, filename):
        with closing(sqlite3.connect(self.dbname)) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            query = self.__GetFavoriteVideoURLSelectSQL(filename)
            res = list(c.execute(query))
        return res

    # id	img_filename	url	url_thumbnail
    # tweet_id	tweet_url	created_at	user_id	user_name	screan_name	tweet_text
    # saved_localpath	saved_created_at
    def DBRetweetUpsert(self, file_name, url_orig, url_thumbnail, tweet, save_file_fullpath):
        with closing(sqlite3.connect(self.dbname)) as conn:
            c = conn.cursor()
            param = self.__GetUpdateParam(file_name, url_orig, url_thumbnail, tweet, save_file_fullpath)
            c.execute(self.__retweet_sql, param)
            conn.commit()

    def DBRetweetSelect(self, limit=300):
        with closing(sqlite3.connect(self.dbname)) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            query = self.__GetRetweetSelectSQL(limit)
            res = list(c.execute(query))
        return res

    def DBRetweetVideoURLSelect(self, filename):
        with closing(sqlite3.connect(self.dbname)) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            query = self.__GetRetweetVideoURLSelectSQL(filename)
            res = list(c.execute(query))
        return res

    def DBRetweetFlagUpdate(self, file_list=[], set_flag=0):
        filename = "'" + "','".join(file_list) + "'"
        with closing(sqlite3.connect(self.dbname)) as conn:
            c = conn.cursor()
            query = self.__GetRetweetFlagUpdateSQL(filename, set_flag)
            c.execute(query)
            conn.commit()

    def DBRetweetFlagClear(self):
        with closing(sqlite3.connect(self.dbname)) as conn:
            c = conn.cursor()
            query = self.__GetRetweetFlagClearSQL()
            c.execute(query)
            conn.commit()

    def DBDelInsert(self, tweet):
        with closing(sqlite3.connect(self.dbname)) as conn:
            c = conn.cursor()
            param = self.__GetDelUpdateParam(tweet)
            c.execute(self.__del_sql, param)
            conn.commit()

    def DBDelSelect(self):
        with closing(sqlite3.connect(self.dbname)) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            # 2日前の通知ツイートを削除する(1日前の日付より前)
            t = date.today() - timedelta(1)

            # 今日未満 = 昨日以前の通知ツイートをDBから取得
            w = "delete_done = 0 and created_at < '{}'".format(t.strftime('%Y-%m-%d'))
            query = "select * from DeleteTarget where " + w
            res = list(c.execute(query))
            conn.commit()

            # 消去フラグを立てる
            u = "delete_done = 1, deleted_at = '{}'".format(t.strftime('%Y-%m-%d'))
            query = "update DeleteTarget set {} where {}".format(u, w)
            c.execute(query)
            conn.commit()
        return res

if __name__ == "__main__":
    db_cont = DBController()
