# coding: utf-8
from abc import ABCMeta, abstractmethod
import configparser
from datetime import datetime
import json
import os
import requests
from requests_oauthlib import OAuth1Session
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

            self.user_name = self.config["tweet_timeline"]["user_name"]
            self.count = int(self.config["tweet_timeline"]["count"])

            self.save_path = ""
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
                            if self.type == "Fav":
                                self.db_cont.DBFavUpsert(url, tweet, save_file_fullpath)
                            elif self.type == "RT":
                                self.db_cont.DBRetweetUpsert(url, tweet, save_file_fullpath)

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

        # フォルダに既に保存しているファイルにはURLの情報がない
        # ファイル名とドメインを結びつけてURLを手動で生成する
        # twitterの画像URLの仕様が変わったらここも変える必要がある
        # http://pbs.twimg.com/media/{file.basename}.jpg:orig
        base_url = 'http://pbs.twimg.com/media/{}:orig'
        del_img_filename = []
        add_img_filename = []
        for i, file in enumerate(file_list):
            if i > holding_file_num:
                os.remove(file)
                self.del_cnt += 1
                self.del_url_list.append(base_url.format(os.path.basename(file)))
                del_img_filename.append(os.path.basename(file))
            else:
                self.add_url_list.append(base_url.format(os.path.basename(file)))
                add_img_filename.append(os.path.basename(file))

        # 存在マーキングを更新する
        if self.type == "RT":
            self.db_cont.DBRetweetFlagClear()
            self.db_cont.DBRetweetFlagUpdate(add_img_filename, 1)

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

                if self.type == "Fav" and config.getboolean("is_post_fav_done_reply"):
                    self.PostTweet(done_msg)
                    print("Reply posted.")
                    fout.write("Reply posted.")

                if self.type == "RT" and config.getboolean("is_post_retweet_done_reply"):
                    self.PostTweet(done_msg)
                    print("Reply posted.")
                    fout.write("Reply posted.")

                if config.getboolean("is_post_line_notify"):
                    self.PostLineNotify(done_msg)
                    print("Line Notify posted.")
                    fout.write("Line Notify posted.")

        # 古い通知リプライを消す
        if config.getboolean("is_post_fav_done_reply") or config.getboolean("is_post_retweet_done_reply"):
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

if __name__ == "__main__":
    # c = Crawler()
    # c.Crawl()
    pass
