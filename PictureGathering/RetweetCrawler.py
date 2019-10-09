# coding: utf-8
from datetime import datetime
from logging import getLogger, DEBUG, INFO
import os
import random
import sys

from PictureGathering.Crawler import Crawler


logger = getLogger("root")
logger.setLevel(INFO)


class RetweetCrawler(Crawler):
    def __init__(self):
        super().__init__()
        try:
            self.retweet_get_max_loop = int(self.config["tweet_timeline"]["retweet_get_max_loop"])
            self.save_path = os.path.abspath(self.config["save_directory"]["save_retweet_path"])
        except KeyError:
            logger.exception("invalid config file eeror.")
            exit(-1)
        self.max_id = None
        self.type = "RT"

    def RetweetsGet(self):
        url = "https://api.twitter.com/1.1/statuses/user_timeline.json"
        rt_tweets = []
        holding_num = int(self.config["holding"]["holding_file_num"])

        # 存在マーキングをクリアする
        self.db_cont.DBRetweetFlagClear()

        # 既存ファイル一覧を取得する
        exist_filepaths = self.GetExistFilelist()
        exist_filenames = []
        for exist_filepath in exist_filepaths:
            exist_filenames.append(os.path.basename(exist_filepath))
        exist_oldest_filename = exist_filenames[-1]

        # 存在マーキングを更新する
        self.db_cont.DBRetweetFlagUpdate(exist_filenames, 1)

        get_cnt = 0
        end_flag = False
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
                        entities = t['retweeted_status']["extended_entities"]
                        include_new_flag = False
                        # 一つでも保存していない画像を含んでいるか判定
                        for entity in entities["media"]:
                            media_url = self.GetMediaUrl(entity)
                            filename = os.path.basename(media_url)

                            # 既存ファイルの最後のファイル名と一致したら探索を途中で打ち切る
                            if filename == exist_oldest_filename:
                                end_flag = True

                            # 存在しないならそのツイートを収集対象とする
                            if filename not in exist_filenames:
                                include_new_flag = True
                                break

                        # 一つでも保存していない画像を含んでいたらツイートを収集する
                        if include_new_flag:
                            rt_tweets.append(t['retweeted_status'])
                            get_cnt = get_cnt + 1

                        # 探索を途中で打ち切る
                        if end_flag:
                            break

            # 次のRTから取得する
            self.max_id = timeline_tweeets[-1]['id'] - 1

            # 収集したツイートが保持数を超えたor既存ファイルの最後まで探索した場合break
            if get_cnt > holding_num or end_flag:
                break

        # 古い順にする
        rt_tweets = reversed(rt_tweets)

        return rt_tweets

    def UpdateDBExistMark(self, add_img_filename):
        # 存在マーキングを更新する
        self.db_cont.DBRetweetFlagClear()
        self.db_cont.DBRetweetFlagUpdate(add_img_filename, 1)

    def GetVideoURL(self, filename):
        # 'https://video.twimg.com/ext_tw_video/1139678486296031232/pu/vid/640x720/b0ZDq8zG_HppFWb6.mp4?tag=10'
        responce = self.db_cont.DBRetweetVideoURLSelect("'" + filename + "'")
        url = responce[0]["url"] if len(responce) == 1 else ""
        return url

    def MakeDoneMessage(self):
        now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        done_msg = "Retweet PictureGathering run.\n"
        done_msg += now_str
        done_msg += " Process Done !!\n"
        done_msg += "add {0} new images. ".format(self.add_cnt)
        done_msg += "delete {0} old images.".format(self.del_cnt)
        done_msg += "\n"

        # 画像URLをランダムにピックアップする
        random_pickup = True
        if random_pickup:
            pickup_url_list = random.sample(self.add_url_list, 4)
            for pickup_url in pickup_url_list:
                done_msg += pickup_url + "\n"

        return done_msg

    def Crawl(self):
        tweets = self.RetweetsGet()
        self.ImageSaver(tweets)
        self.ShrinkFolder(int(self.config["holding"]["holding_file_num"]))
        self.EndOfProcess()


if __name__ == "__main__":
    logger.info("Retweet Crawler run.")
    c = RetweetCrawler()
    c.Crawl()
