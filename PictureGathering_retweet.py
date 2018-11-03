# coding: utf-8
import configparser
from datetime import datetime
import json
import io
import os
import pprint
from requests_oauthlib import OAuth1Session
import sqlite3
import sys
import time
import traceback
import urllib

import WriteHTML as WriteHTML
import DBControl as DBControl


class Crawler:
    CONFIG_FILE_NAME = "config.ini"

    add_cnt = 0
    del_cnt = 0

    add_url_list = []
    del_url_list = []

    def __init__(self):
        self.config = configparser.SafeConfigParser()
        try:
            if not self.config.read(self.CONFIG_FILE_NAME, encoding="utf8"):
                raise IOError

            config = self.config["token_keys"]
            self.CONSUMER_KEY = config["consumer_key"]
            self.CONSUMER_SECRET = config["consumer_secret"]
            self.ACCESS_TOKEN_KEY = config["access_token"]
            self.ACCESS_TOKEN_SECRET = config["access_token_secret"]

            self.save_retweet_path = os.path.abspath(self.config["save_directory"]["save_retweet_path"])

            # count * retweet_get_max_loop　だけツイートをさかのぼる。
            self.user_name = self.config["tweet_timeline"]["user_name"]
            self.retweet_get_max_loop = int(self.config["tweet_timeline"]["retweet_get_max_loop"])
            self.count = int(self.config["tweet_timeline"]["count"])
        except IOError:
            print(CONFIG_FILE_NAME + " is not exist or cannot be opened.")
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
            self.CONSUMER_KEY,
            self.CONSUMER_SECRET,
            self.ACCESS_TOKEN_KEY,
            self.ACCESS_TOKEN_SECRET
        )

        self.max_id = None

    def TwitterAPIRequest(self, url, params):
        responce = self.oath.get(url, params=params)

        if responce.status_code != 200:
            print("Error code: {0}".format(responce.status_code))
            return None

        res = json.loads(responce.text)
        return res

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

            # pprint.pprint(rt_tweets)
            if len(rt_tweets) > holding_num:
                break

        # 古い順にする
        rt_tweets = reversed(rt_tweets)

        return rt_tweets

    def ImageSaver(self, tweets):
        for tweet in tweets:
            if "extended_entities" not in tweet:
                print("画像を含んでいないツイートです。")
                continue

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
                save_file_path = os.path.join(self.save_retweet_path, os.path.basename(url))
                save_file_fullpath = os.path.abspath(save_file_path)

                if not os.path.isfile(save_file_fullpath):
                    with urllib.request.urlopen(url_orig) as img:
                        with open(save_file_fullpath, 'wb') as fout:
                            fout.write(img.read())
                            self.add_url_list.append(url_orig)
                            # DB操作
                            DBControl.DBRetweetUpsert(url, tweet, save_file_fullpath)

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

    def EndOfProcess(self):
        print("")

        now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        done_msg = "Retweet PictureGathering run.\n"
        done_msg += now_str
        done_msg += " Process Done !!\n"
        done_msg += "add {0} new images. ".format(self.add_cnt)
        done_msg += "delete {0} old images. \n".format(self.del_cnt)

        print(done_msg)

        config = self.config["notification"]

        WriteHTML.WriteRetweetHTML(self.del_url_list)
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

                if config.getboolean("is_post_retweet_done_reply"):
                    self.PostTweet(done_msg)
                    print("Reply posted.")
                    fout.write("Reply posted.")

        # 古い通知リプライを消す
        if config.getboolean("is_post_retweet_done_reply"):
            targets = DBControl.DBDelSelect()
            url = "https://api.twitter.com/1.1/statuses/destroy/{}.json"
            for target in targets:
                responce = self.oath.post(url.format(target[1]))  # tweet_id

        DBControl.DBClose()
        # sys.exit()

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

        DBControl.DBDelInsert(json.loads(responce.text))

        if responce.status_code != 200:
            print("Error code: {0}".format(responce.status_code))
            return None

    def ShrinkFolder(self, holding_file_num):
        xs = []
        for root, dir, files in os.walk(self.save_retweet_path):
            for f in files:
                path = os.path.join(root, f)
                xs.append((os.path.getmtime(path), path))

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
                self.del_url_list.append(base_url.format(os.path.basename(file)))

                # DB内の存在フラグも更新する
                DBControl.DBRetweetFlagUpdate(os.path.basename(file))

    def Crawl(self):
        tweets = self.RetweetsGet()
        self.ImageSaver(tweets)
        self.ShrinkFolder(int(self.config["holding"]["holding_file_num"]))
        self.EndOfProcess()


if __name__ == "__main__":
    c = Crawler()
    c.Crawl()
