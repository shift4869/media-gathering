# coding: utf-8
import configparser
from datetime import datetime
from datetime import date
from datetime import timedelta
import os
import re
import sqlite3

dbname = 'PG_DB.db'
conn = sqlite3.connect(dbname)
c = conn.cursor()
p1 = 'img_filename,url,url_large,'
p2 = 'tweet_id,tweet_url,created_at,user_id,user_name,screan_name,tweet_text,'
p3 = 'saved_localpath,saved_created_at'
pn = '?,?,?,?,?,?,?,?,?,?,?,?'
fav_sql = 'replace into Favorite (' + p1 + p2 + p3 + ') values (' + pn + ')'
p1 = 'tweet_id,delete_done,created_at,deleted_at,tweet_text,add_num,del_num'
pn = '?,?,?,?,?,?,?'
del_sql = 'replace into DeleteTarget (' + p1 + ') values (' + pn + ')'


# id	img_filename	url	url_large
# tweet_id	tweet_url	created_at	user_id	user_name	screan_name	tweet_text
# saved_localpath	saved_created_at
def DBFavUpsert(url, tweet, save_file_fullpath):
    url_orig = url + ":orig"
    td_format = '%a %b %d %H:%M:%S +0000 %Y'
    dts_format = '%Y-%m-%d %H:%M:%S'

    print(tweet["entities"]["media"][0]["expanded_url"])

    # DB操作
    tca = tweet["created_at"]
    dst = datetime.strptime(tca, td_format)
    param = (os.path.basename(url),
             url_orig,
             url+":large",
             tweet["id_str"],
             tweet["entities"]["media"][0]["expanded_url"],
             dst.strftime(dts_format),
             tweet["user"]["id_str"],
             tweet["user"]["name"],
             tweet["user"]["screen_name"],
             tweet["text"],
             save_file_fullpath,
             datetime.now().strftime(dts_format))
    c.execute(fav_sql, param)
    conn.commit()


def DBFavSelect(limit=200):
    query = 'select * from Favorite order by id desc limit {}'.format(limit)
    return list(c.execute(query))


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
    c.execute(del_sql, param)
    conn.commit()


def DBDelSelect():
    t = date.today() - timedelta(1)  # 2日前の通知ツイートを削除する
    # t = date.today() + timedelta(1)

    # 今日未満 = 昨日以前の通知ツイートをDBから取得
    s = "delete_done = 0 and created_at < '{}'".format(
            t.strftime('%Y-%m-%d'))
    query = "select * from DeleteTarget where " + s
    res = list(c.execute(query))
    conn.commit()

    # 消去フラグを立てる
    u = "delete_done = 1, deleted_at = '{}'".format(t.strftime('%Y-%m-%d'))
    query = "update DeleteTarget set {} where {}".format(
            u, s)
    c.execute(query)
    conn.commit()

    return res


def DBClose():
    conn.close()

if __name__ == "__main__":
    print(DBDelSelect())
