# coding: utf-8
from datetime import datetime
import os
import sys
import traceback

from Crawler import Crawler


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

    def GetVideoURL(self, filename):
        # 'https://video.twimg.com/ext_tw_video/1139678486296031232/pu/vid/640x720/b0ZDq8zG_HppFWb6.mp4?tag=10'
        responce = self.db_cont.DBRetweetVideoURLSelect("'" + filename + "'")
        return responce[0][3]  # url

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
    c = RetweetCrawler()
    c.Crawl()
