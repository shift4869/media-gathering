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
import DBControl as DBControl

config = configparser.SafeConfigParser()
config.read("config.ini", encoding='utf8')

CONSUMER_KEY = config["token_keys"]["consumer_key"]
CONSUMER_SECRET = config["token_keys"]["consumer_secret"]
ACCESS_TOKEN_KEY = config["token_keys"]["access_token"]
ACCESS_TOKEN_SECRET = config["token_keys"]["access_token_secret"]

save_path = os.path.abspath(config["save_directory"]["save_path"])

user_name = config["tweet_timeline"]["user_name"]
get_pages = int(config["tweet_timeline"]["get_pages"]) + 1
# count * get_pages　だけツイートをさかのぼってくれる。
count = int(config["tweet_timeline"]["count"])

oath = OAuth1Session(
    CONSUMER_KEY,
    CONSUMER_SECRET,
    ACCESS_TOKEN_KEY,
    ACCESS_TOKEN_SECRET
)

add_cnt = 0
del_cnt = 0

add_url_list = []
del_url_list = []

dbname = 'PG_DB.db'
conn = sqlite3.connect(dbname)
c = conn.cursor()
p1 = 'img_filename,url,url_large,'
p2 = 'tweet_id,tweet_url,created_at,user_id,user_name,screan_name,tweet_text,'
p3 = 'saved_localpath,saved_created_at'
pn = '?,?,?,?,?,?,?,?,?,?,?,?'
sql = 'replace into Favorite (' + p1 + p2 + p3 + ') values (' + pn + ')'


def TwitterAPIRequest(url, params):
    responce = oath.get(url, params=params)

    if responce.status_code != 200:
        print("Error code: {0}".format(responce.status_code))
        return None

    res = json.loads(responce.text)
    return res


def FavTweetsGet(page):
    kind_of_api = config["tweet_timeline"]["kind_of_timeline"]
    if kind_of_api == "favorite":
        url = "https://api.twitter.com/1.1/favorites/list.json"
        params = {
            "screen_name": user_name,
            "page": page,
            "count": count,
            "include_entities": 1  # ツイートのメタデータ取得。これしないと複数枚の画像に対応できない。
        }
    elif kind_of_api == "home":
        url = "https://api.twitter.com/1.1/statuses/home_timeline.json"
        params = {
            "count": count,
            "include_entities": 1
        }
    else:
        print("kind_of_api is invalid .")
        return None

    return TwitterAPIRequest(url, params)


def ImageSaver(tweets):
    global add_cnt
    global add_url_list
    for tweet in tweets:
        try:
            image_list = tweet["extended_entities"]["media"]
            # ex) tweet["created_at"] = "Tue Sep 04 15:55:52 +0000 2012"
            td_format = '%a %b %d %H:%M:%S +0000 %Y'
            created_time = time.strptime(tweet["created_at"], td_format)
            atime = mtime = time.mktime(
                (created_time.tm_year,
                 created_time.tm_mon,
                 created_time.tm_mday,
                 created_time.tm_hour,
                 created_time.tm_min,
                 created_time.tm_sec,
                 0, 0, -1)
            )

            for image_dict in image_list:
                url = image_dict["media_url"]
                url_orig = url + ":orig"
                save_file_path = os.path.join(save_path, os.path.basename(url))
                save_file_fullpath = os.path.abspath(save_file_path)

                if not os.path.isfile(save_file_fullpath):
                    with urllib.request.urlopen(url_orig) as img:
                        with open(save_file_fullpath, 'wb') as fout:
                            fout.write(img.read())
                            add_url_list.append(url_orig)
                            # DB操作
                            DBControl.DBUpsert(url, tweet)

                    # image magickで画像変換
                    if config["processes"]["image_magick"]:
                        img_magick_path = config["processes"]["image_magick"]
                        os.system('"' + img_magick_path + '" -quality 60 ' +
                                  save_file_fullpath + " " +
                                  save_file_fullpath)

                    # 更新日時を上書き
                    if config["timestamp"].getboolean("timestamp_created_at"):
                        os.utime(save_file_fullpath, (atime, mtime))

                    print(os.path.basename(url_orig) + " -> done!")
                    add_cnt += 1
                # else :
                #     EndOfProcess(cnt)
        except KeyError:
            print("KeyError:画像を含んでいないツイートです。")
    # EndOfProcess(cnt)


def EndOfProcess():
    print("")

    now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    done_msg = "PictureGathering run.\n"
    done_msg += now_str
    done_msg += " Process Done !!\n"
    done_msg += "add {0} new images. ".format(add_cnt)
    done_msg += "delete {0} old images. \n".format(del_cnt)

    print(done_msg)

    WriteHTML.WriteHTML(del_url_list)
    with open('log.txt', 'a') as fout:
        if add_cnt != 0 or del_cnt != 0:
            fout.write("\n")
            fout.write(done_msg)

            if add_cnt != 0:
                fout.write("add url:\n")
                for url in add_url_list:
                    fout.write(url + "\n")

            if del_cnt != 0:
                fout.write("del url:\n")
                for url in del_url_list:
                    fout.write(url + "\n")

            if config["notification"].getboolean("is_post_done_reply_message"):
                PostTweet(done_msg)
                print("Reply posted.")
                fout.write("Reply posted.")

            if config["notification"].getboolean("post_done_direct_message"):
                PostDM(done_msg)
                print("DM posted.")
                fout.write("DM posted.")

    conn.close()
    sys.exit()


def PostTweet(str):
    url = "https://api.twitter.com/1.1/users/show.json"
    reply_user_name = config["notification"]["reply_to_user_name"]

    params = {
        "screen_name": reply_user_name,
    }
    res = TwitterAPIRequest(url, params=params)
    if res is None:
        return None

    url = "https://api.twitter.com/1.1/statuses/update.json"
    reply_to_status_id = res["id_str"]

    str = "@" + reply_user_name + " " + str

    params = {
        "status": str,
        "in_reply_to_status_id": reply_to_status_id,
    }
    responce = oath.post(url, params=params)

    if responce.status_code != 200:
        print("Error code: {0}".format(responce.status_code))
        return None


def PostDM(str):
    url = "https://api.twitter.com/1.1/direct_messages/new.json"
    params = {
        "screen_name": user_name,
        "text": str,
    }
    responce = oath.post(url, params=params)

    if responce.status_code != 200:
        print("Error code: {0}".format(responce.status_code))
        return None


def ShurinkFolder(holding_file_num):
    global del_cnt
    global del_url_list
    xs = []
    for root, dir, files in os.walk(save_path):
        for f in files:
            path = os.path.join(root, f)
            xs.append((os.path.getmtime(path), path))

    file_list = []
    for mtime, path in sorted(xs, reverse=True):
        file_list.append(path)

    for i, file in enumerate(file_list):
        if i > holding_file_num:
            os.remove(file)
            del_cnt += 1
            # フォルダに既に保存しているファイルにはURLの情報がない
            # ファイル名とドメインを結びつけてURLを手動で生成する
            # twitterの画像URLの仕様が変わったらここも変える必要がある
            # http://pbs.twimg.com/media/{file.basename}.jpg:orig
            base_url = 'http://pbs.twimg.com/media/'
            del_url_list.append(base_url + os.path.basename(file) + ":orig")


if __name__ == "__main__":
    for i in range(1, get_pages):
        tweets = FavTweetsGet(i)
        ImageSaver(tweets)
    ShurinkFolder(int(config["holding"]["holding_file_num"]))
    EndOfProcess()
