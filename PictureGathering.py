# coding: utf-8
from abc import ABCMeta, abstractmethod
import argparse
import configparser
from datetime import datetime
import json
import io
import os
import requests
from requests_oauthlib import OAuth1Session
import sqlite3
import sys
import time
import traceback
import urllib

import WriteHTML as WriteHTML
import DBControlar as DBControlar


class Crawler(metaclass=ABCMeta):
    CONFIG_FILE_NAME = "config.ini"

    def __init__(self):
        self.config = configparser.ConfigParser()
        try:
            self.db_cont = DBControlar.DBControlar()
            if not self.config.read(self.CONFIG_FILE_NAME, encoding="utf8"):
                raise IOError

            config = self.config["twitter_token_keys"]
            self.TW_CONSUMER_KEY = config["consumer_key"]
            self.TW_CONSUMER_SECRET = config["consumer_secret"]
            self.TW_ACCESS_TOKEN_KEY = config["access_token"]
            self.TW_ACCESS_TOKEN_SECRET = config["access_token_secret"]

            config = self.config["line_token_keys"]
            self.LN_TOKEN_KEY = config["token_key"]

            # self.save_path = os.path.abspath(self.config["save_directory"]["save_fav_path"])
            self.save_path = ""

            self.user_name = self.config["tweet_timeline"]["user_name"]
            self.count = int(self.config["tweet_timeline"]["count"])

            self.type = ""
        except IOError:
            print(self.CONFIG_FILE_NAME + " is not exist or cannot be opened.")
            exit(-1)
        except KeyError:
            ex, ms, tb = sys.exc_info()
            traceback.print_exception(ex, ms, tb)
            exit(-1)
        except Exception:
            ex, ms, tb = sys.exc_info()
            traceback.print_exception(ex, ms, tb)
            exit(-1)

        self.oath = OAuth1Session(
            self.TW_CONSUMER_KEY,
            self.TW_CONSUMER_SECRET,
            self.TW_ACCESS_TOKEN_KEY,
            self.TW_ACCESS_TOKEN_SECRET
        )

        self.add_cnt = 0
        self.del_cnt = 0

        self.add_url_list = []
        self.del_url_list = []

    def TwitterAPIRequest(self, url, params):
        responce = self.oath.get(url, params=params)

        if responce.status_code != 200:
            print("Error code: {0}".format(responce.status_code))
            return None

        res = json.loads(responce.text)
        return res

    def ImageSaver(self, tweets):
        for tweet in tweets:
            if "extended_entities" not in tweet:
                print("画像を含んでいないツイートです。")
                continue
            if "media" not in tweet["extended_entities"]:
                print("画像を含んでいないツイートです。")
                continue
            image_list = tweet["extended_entities"]["media"]

            # 画像つきツイートが投稿された日時を取得する
            # もしcreated_atが不正な形式だった場合、strptimeはValueErrorを返す
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
                if "media_url" not in image_dict:
                    print("画像を含んでいないツイートです。")
                    continue
                url = image_dict["media_url"]
                url_orig = url + ":orig"
                save_file_path = os.path.join(self.save_path, os.path.basename(url))
                save_file_fullpath = os.path.abspath(save_file_path)

                if not os.path.isfile(save_file_fullpath):
                    with urllib.request.urlopen(url_orig) as img:
                        with open(save_file_fullpath, 'wb') as fout:
                            fout.write(img.read())
                            self.add_url_list.append(url_orig)
                            # DB操作
                            self.db_cont.DBFavUpsert(url, tweet, save_file_fullpath)

                    # image magickで画像変換
                    img_magick_path = self.config["processes"]["image_magick"]
                    if img_magick_path:
                        os.system('"' + img_magick_path + '" -quality 60 ' +
                                  save_file_fullpath + " " +
                                  save_file_fullpath)

                    # 更新日時を上書き
                    config = self.config["timestamp"]
                    if config.getboolean("timestamp_created_at"):
                        os.utime(save_file_fullpath, (atime, mtime))

                    print(os.path.basename(url_orig) + " -> done!")
                    self.add_cnt += 1
        return 0

    def ShrinkFolder(self, holding_file_num):
        xs = []
        for root, dir, files in os.walk(self.save_path):
            for f in files:
                path = os.path.join(root, f)
                xs.append((os.path.getmtime(path), path))
        os.walk(self.save_path).close()

        file_list = []
        for mtime, path in sorted(xs, reverse=True):
            file_list.append(path)

        for i, file in enumerate(file_list):
            if i > holding_file_num:
                os.remove(file)
                self.del_cnt += 1
                # フォルダに既に保存しているファイルにはURLの情報がない
                # ファイル名とドメインを結びつけてURLを手動で生成する
                # twitterの画像URLの仕様が変わったらここも変える必要がある
                # http://pbs.twimg.com/media/{file.basename}.jpg:orig
                base_url = 'http://pbs.twimg.com/media/{}:orig'
                self.del_url_list.append(
                    base_url.format(os.path.basename(file)))
        return 0

    @abstractmethod
    def MakeDoneMessage(self):
        pass

    def EndOfProcess(self):
        print("")

        done_msg = self.MakeDoneMessage()

        print(done_msg)

        config = self.config["notification"]

        WriteHTML.WriteResultHTML(self.type, self.del_url_list)
        with open('log.txt', 'a') as fout:
            if self.add_cnt != 0 or self.del_cnt != 0:
                fout.write("\n")
                fout.write(done_msg)

                if self.add_cnt != 0:
                    fout.write("add url:\n")
                    for url in self.add_url_list:
                        fout.write(url + "\n")

                if self.del_cnt != 0:
                    fout.write("del url:\n")
                    for url in self.del_url_list:
                        fout.write(url + "\n")

                if config.getboolean("is_post_fav_done_reply"):
                    self.PostTweet(done_msg)
                    print("Reply posted.")
                    fout.write("Reply posted.")

                if config.getboolean("is_post_line_notify"):
                    self.PostLineNotify(done_msg)
                    print("Line Notify posted.")
                    fout.write("Line Notify posted.")

        # 古い通知リプライを消す
        if config.getboolean("is_post_fav_done_reply"):
            targets = self.db_cont.DBDelSelect()
            url = "https://api.twitter.com/1.1/statuses/destroy/{}.json"
            for target in targets:
                responce = self.oath.post(url.format(target[1]))  # tweet_id

        return 0

    def PostTweet(self, str):
        url = "https://api.twitter.com/1.1/users/show.json"
        reply_user_name = self.config["notification"]["reply_to_user_name"]

        params = {
            "screen_name": reply_user_name,
        }
        res = self.TwitterAPIRequest(url, params=params)
        if res is None:
            return None

        url = "https://api.twitter.com/1.1/statuses/update.json"
        reply_to_status_id = res["id_str"]

        str = "@" + reply_user_name + " " + str

        params = {
            "status": str,
            "in_reply_to_status_id": reply_to_status_id,
        }
        responce = self.oath.post(url, params=params)

        self.db_cont.DBDelInsert(json.loads(responce.text))

        if responce.status_code != 200:
            print("Error code: {0}".format(responce.status_code))
            return None

        return 0

    def PostLineNotify(self, str):
        url = "https://notify-api.line.me/api/notify"
        token = self.LN_TOKEN_KEY

        headers = {"Authorization": "Bearer " + token}
        payload = {"message": str}

        responce = requests.post(url, headers=headers, params=payload)

        if responce.status_code != 200:
            print("Error code: {0}".format(responce.status_code))
            return None

        return 0

    @abstractmethod
    def Crawl(self):
        pass


class FavCrawler(Crawler):
    def __init__(self):
        super().__init__()
        try:
            self.save_path = os.path.abspath(self.config["save_directory"]["save_fav_path"])
        except KeyError:
            ex, ms, tb = sys.exc_info()
            traceback.print_exception(ex, ms, tb)
            exit(-1)
        self.type = "Fav"

    def FavTweetsGet(self, page):
        kind_of_api = self.config["tweet_timeline"]["kind_of_timeline"]
        if kind_of_api == "favorite":
            url = "https://api.twitter.com/1.1/favorites/list.json"
            params = {
                "screen_name": self.user_name,
                "page": page,
                "count": self.count,
                "include_entities": 1  # ツイートのメタデータ取得。これしないと複数枚の画像に対応できない。
            }
        elif kind_of_api == "home":
            url = "https://api.twitter.com/1.1/statuses/home_timeline.json"
            params = {
                "count": self.count,
                "include_entities": 1
            }
        else:
            print("kind_of_api is invalid .")
            return None

        return self.TwitterAPIRequest(url, params)

    def MakeDoneMessage(self):
        now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        done_msg = "Fav PictureGathering run.\n"
        done_msg += now_str
        done_msg += " Process Done !!\n"
        done_msg += "add {0} new images. ".format(self.add_cnt)
        done_msg += "delete {0} old images. \n".format(self.del_cnt)
        return done_msg

    def Crawl(self):
        # count * get_pages だけツイートをさかのぼる。
        self.get_pages = int(self.config["tweet_timeline"]["get_pages"]) + 1
        for i in range(1, self.get_pages):
            tweets = self.FavTweetsGet(i)
            self.ImageSaver(tweets)
        self.ShrinkFolder(int(self.config["holding"]["holding_file_num"]))
        self.EndOfProcess()
        return 0


class RetweetCrawler(Crawler):
    def __init__(self):
        super().__init__()
        try:
            self.retweet_get_max_loop = int(self.config["tweet_timeline"]["retweet_get_max_loop"])
            self.save_path = os.path.abspath(self.config["save_directory"]["save_retweet_path"])
        except KeyError:
            ex, ms, tb = sys.exc_info()
            traceback.print_exception(ex, ms, tb)
            exit(-1)
        self.max_id = None
        self.type = "RT"

    def RetweetsGet(self):
        url = "https://api.twitter.com/1.1/statuses/user_timeline.json"
        rt_tweets = []
        holding_num = int(self.config["holding"]["holding_file_num"])

        for i in range(1, self.retweet_get_max_loop):
            params = {
                "screen_name": self.user_name,
                "count": self.count,
                "max_id": self.max_id,
                "contributor_details": True,
                "include_rts": True
            }
            timeline_tweeets = self.TwitterAPIRequest(url, params)

            for t in timeline_tweeets:
                if t['retweeted'] and ("retweeted_status" in t):
                    if "extended_entities" in t['retweeted_status']:
                        rt_tweets.append(t['retweeted_status'])

            self.max_id = timeline_tweeets[-1]['id'] - 1

            if len(rt_tweets) > holding_num:
                break

        # 古い順にする
        rt_tweets = reversed(rt_tweets)

        return rt_tweets

    def MakeDoneMessage(self):
        now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        done_msg = "Retweet PictureGathering run.\n"
        done_msg += now_str
        done_msg += " Process Done !!\n"
        done_msg += "add {0} new images. ".format(self.add_cnt)
        done_msg += "delete {0} old images. \n".format(self.del_cnt)
        return done_msg

    def Crawl(self):
        tweets = self.RetweetsGet()
        self.ImageSaver(tweets)
        self.ShrinkFolder(int(self.config["holding"]["holding_file_num"]))
        self.EndOfProcess()

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Twitter Crawler")
    arg_parser.add_argument("--type", choices=["Fav", "RT"], default="Fav",
                            help='Crawl target: Fav or RT')
    args = arg_parser.parse_args()

    c = None
    if args.type == "Fav":
        c = FavCrawler()
    elif args.type == "RT":
        c = RetweetCrawler()

    if c is not None:
        c.Crawl()
    else:
        arg_parser.print_help()
