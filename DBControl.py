# coding: utf-8
import configparser
from datetime import datetime
from datetime import date
from datetime import timedelta
import json
import io
import os
import re
from requests_oauthlib import OAuth1Session
import sqlite3
import sys
import time
import urllib

import WriteHTML as WriteHTML
import PictureGathering as PG


def TweetURLGet(id_str):
    url = "https://api.twitter.com/1.1/statuses/show.json"
    params = {
        "id": id_str,
    }

    tweet = PG.TwitterAPIRequest(url, params)
    return tweet["entities"]["media"][0]["expanded_url"]


# id	img_filename	url	url_large
# tweet_id	tweet_url	created_at	user_id	user_name	screan_name	tweet_text
# saved_localpath	saved_created_at
def DBFavUpsert(url, tweet):
    url_orig = url + ":orig"
    save_file_path = os.path.join(PG.save_path, os.path.basename(url))
    save_file_fullpath = os.path.abspath(save_file_path)
    td_format = '%a %b %d %H:%M:%S +0000 %Y'
    dts_format = '%Y-%m-%d %H:%M:%S'

    # DB操作
    tca = tweet["created_at"]
    dst = datetime.strptime(tca, td_format)
    param = (os.path.basename(url),
             url_orig,
             url+":large",
             tweet["id_str"],
             TweetURLGet(tweet["id_str"]),
             dst.strftime(dts_format),
             tweet["user"]["id_str"],
             tweet["user"]["name"],
             tweet["user"]["screen_name"],
             tweet["text"],
             save_file_fullpath,
             datetime.now().strftime(dts_format))
    PG.c.execute(PG.fav_sql, param)
    PG.conn.commit()


def DBFavSelect(limit=200):
    query = 'select * from Favorite order by id desc limit {}'.format(limit)
    return PG.c.execute(query)


def DBDelInsert(tweet):
    pattern = ' +[0-9] '
    text = tweet["text"]
    add_num = int(re.findall(pattern, text)[0])
    del_num = int(re.findall(pattern, text)[1])
    td_format = '%a %b %d %H:%M:%S +0000 %Y'
    dts_format = '%Y-%m-%d %H:%M:%S'

    # DB操作
    tca = tweet["created_at"]
    dst = datetime.strptime(tca, td_format)
    param = (tweet["id_str"],
             False,
             dst.strftime(dts_format),
             None,
             tweet["text"],
             add_num,
             del_num)
    PG.c.execute(PG.del_sql, param)
    PG.conn.commit()


def DBDelSelect():
    t = date.today()
    # t = date.today() + timedelta(1)
    # y = t - timedelta(1)
    # print(t.strftime('%Y-%m-%d'))
    # print(y.strftime('%Y-%m-%d'))

    # 今日未満 = 昨日以前の通知ツイートをDBから取得
    s = "delete_done = 0 and created_at < '{}'".format(
            t.strftime('%Y-%m-%d'))
    query = "select * from DeleteTarget where " + s
    res = list(PG.c.execute(query))
    PG.conn.commit()

    # 消去フラグを立てる
    u = "delete_done = 1, deleted_at = '{}'".format(t.strftime('%Y-%m-%d'))
    query = "update DeleteTarget set {} where {}".format(
            u, s)
    PG.c.execute(query)
    PG.conn.commit()

    return res

if __name__ == "__main__":
    print(DBDelSelect())
