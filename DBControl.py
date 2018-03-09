# coding: utf-8
import configparser
from datetime import datetime
import json
import io
import os
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
def DBUpsert(url, tweet):
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
    PG.c.execute(PG.sql, param)
    PG.conn.commit()


def DBSelect(limit=200):
    query = 'select * from Favorite order by id desc limit {}'.format(limit)
    return PG.c.execute(query)
