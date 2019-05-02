# coding: utf-8
import configparser
from datetime import datetime
import json
import io
import os
import requests
import pprint
from requests_oauthlib import OAuth1Session
import sqlite3
import sys
import time
import traceback
import urllib

import WriteHTML as WriteHTML
import DBControlar as DBControlar
from Crawler import Crawler


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


if __name__ == "__main__":
    c = FavCrawler()
    c.Crawl()
