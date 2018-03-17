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

            self.CONSUMER_KEY = self.config["token_keys"]["consumer_key"]
            self.CONSUMER_SECRET = self.config["token_keys"]["consumer_secret"]
            self.ACCESS_TOKEN_KEY = self.config["token_keys"]["access_token"]
            self.ACCESS_TOKEN_SECRET = self.config["token_keys"]["access_token_secret"]

            self.save_path = os.path.abspath(self.config["save_directory"]["save_path"])

            # count * get_pages　だけツイートをさかのぼる。
            self.user_name = self.config["tweet_timeline"]["user_name"]
            self.get_pages = int(self.config["tweet_timeline"]["get_pages"]) + 1
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

    def TwitterAPIRequest(self, url, params):
        responce = self.oath.get(url, params=params)

        if responce.status_code != 200:
            print("Error code: {0}".format(responce.status_code))
            return None

        res = json.loads(responce.text)
        return res

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

    def ImageSaver(self, tweets):
        # global add_cnt
        # global add_url_list
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
                    save_file_path = os.path.join(self.save_path, os.path.basename(url))
                    save_file_fullpath = os.path.abspath(save_file_path)

                    if not os.path.isfile(save_file_fullpath):
                        with urllib.request.urlopen(url_orig) as img:
                            with open(save_file_fullpath, 'wb') as fout:
                                fout.write(img.read())
                                self.add_url_list.append(url_orig)
                                # DB操作
                                DBControl.DBFavUpsert(url, tweet)

                        # image magickで画像変換
                        if self.config["processes"]["image_magick"]:
                            img_magick_path = self.config["processes"]["image_magick"]
                            os.system('"' + img_magick_path + '" -quality 60 ' +
                                      save_file_fullpath + " " +
                                      save_file_fullpath)

                        # 更新日時を上書き
                        if self.config["timestamp"].getboolean("timestamp_created_at"):
                            os.utime(save_file_fullpath, (atime, mtime))

                        print(os.path.basename(url_orig) + " -> done!")
                        self.add_cnt += 1
                    # else :
                    #     EndOfProcess(cnt)
            except KeyError:
                print("KeyError:画像を含んでいないツイートです。")
        # EndOfProcess(cnt)

    def EndOfProcess(self):
        print("")

        now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        done_msg = "PictureGathering run.\n"
        done_msg += now_str
        done_msg += " Process Done !!\n"
        done_msg += "add {0} new images. ".format(self.add_cnt)
        done_msg += "delete {0} old images. \n".format(self.del_cnt)

        print(done_msg)

        WriteHTML.WriteHTML(self.del_url_list)
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

                if self.config["notification"].getboolean("is_post_done_reply_message"):
                    PostTweet(done_msg)
                    print("Reply posted.")
                    fout.write("Reply posted.")

        # 古い通知リプライを消す
        if self.config["notification"].getboolean("is_post_done_reply_message"):
            targets = DBControl.DBDelSelect()
            url = "https://api.twitter.com/1.1/statuses/destroy/{}.json"
            for target in targets:
                responce = self.oath.post(url.format(target[1]))  # tweet_id

        DBControl.DBClose()
        sys.exit()

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

    def ShurinkFolder(self, holding_file_num):
        # global del_cnt
        # global del_url_list
        xs = []
        for root, dir, files in os.walk(self.save_path):
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
                base_url = 'http://pbs.twimg.com/media/'
                self.del_url_list.append(base_url + os.path.basename(file) + ":orig")

    def Crawl(self):
        for i in range(1, self.get_pages):
            tweets = self.FavTweetsGet(i)
            self.ImageSaver(tweets)
        self.ShurinkFolder(int(self.config["holding"]["holding_file_num"]))
        self.EndOfProcess()

if __name__ == "__main__":
    # for i in range(1, get_pages):
    #     tweets = FavTweetsGet(i)
    #     ImageSaver(tweets)
    # ShurinkFolder(int(config["holding"]["holding_file_num"]))
    # EndOfProcess()
    c = Crawler()
    c.Crawl()

