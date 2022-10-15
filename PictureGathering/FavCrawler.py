# coding: utf-8
import random
from datetime import datetime
from logging import INFO, getLogger
from pathlib import Path

from PictureGathering.Crawler import Crawler
from PictureGathering.FavDBController import FavDBController
from PictureGathering.LogMessage import MSG
from PictureGathering.v2.Like import Like
from PictureGathering.v2.TwitterAPI import TwitterAPIEndpoint

logger = getLogger("root")
logger.setLevel(INFO)


class FavCrawler(Crawler):
    def __init__(self):
        logger.info(MSG.FAVCRAWLER_INIT_START.value)
        super().__init__()
        try:
            config = self.config["db"]
            save_path = Path(config["save_path"])
            save_path.mkdir(parents=True, exist_ok=True)
            db_fullpath = save_path / config["save_file_name"]
            self.db_cont = FavDBController(db_fullpath, False)  # テーブルはFavoriteを使用
            if config.getboolean("save_permanent_image_flag"):
                Path(config["save_permanent_image_path"]).mkdir(parents=True, exist_ok=True)

            self.save_path = Path(self.config["save_directory"]["save_fav_path"])
            self.type = "Fav"
        except KeyError:
            logger.exception("invalid config file error.")
            exit(-1)
        logger.info(MSG.FAVCRAWLER_INIT_DONE.value)

    def FavTweetsGet(self, page):
        kind_of_api = self.config["tweet_timeline"]["kind_of_timeline"]
        if kind_of_api == "favorite":
            url = "https://api.twitter.com/1.1/favorites/list.json"
            params = {
                "screen_name": self.user_name,
                "page": page,
                "count": self.count,
                "include_entities": 1,  # ツイートのメタデータ取得。これしないと複数枚の画像に対応できない。
                "tweet_mode": "extended"
            }
        elif kind_of_api == "home":
            url = "https://api.twitter.com/1.1/statuses/home_timeline.json"
            params = {
                "count": self.count,
                "include_entities": 1,
                "tweet_mode": "extended"
            }
        else:
            logger.error("kind_of_api is invalid.")
            return None

        return self.TwitterAPIRequest(url, params)

    def MakeDoneMessage(self):
        now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        done_msg = "Fav PictureGathering run.\n"
        done_msg += now_str
        done_msg += " Process Done !!\n"
        done_msg += "add {0} new images. ".format(self.add_cnt)
        done_msg += "delete {0} old images.".format(self.del_cnt)
        done_msg += "\n"

        # 画像URLをランダムにピックアップする
        random_pickup = True
        if random_pickup:
            pickup_url_list = random.sample(self.add_url_list, min(4, len(self.add_url_list)))
            for pickup_url in pickup_url_list:
                pickup_url = str(pickup_url).replace(":orig", "")
                done_msg += pickup_url + "\n"

        return done_msg

    def Crawl(self):
        logger.info(MSG.FAVCRAWLER_CRAWL_START.value)
        # count * fav_get_max_loop だけツイートをさかのぼる。
        fav_get_max_loop = int(self.config["tweet_timeline"]["fav_get_max_loop"]) + 1
        # for i in range(1, fav_get_max_loop):
        #     tweets = self.FavTweetsGet(i)
        #     self.InterpretTweets(tweets)
        my_user_info = self.twitter.get(TwitterAPIEndpoint.USER_ME.value[0], {})
        my_id = my_user_info.get("data", {}).get("id", "")
        like = Like(userid=my_id, pages=fav_get_max_loop, max_results=100, twitter=self.twitter)
        fetched_tweets = like.fetch()
        tweet_info_list = like.to_convert_TweetInfo(fetched_tweets)
        self.interpret_tweets_v2(tweet_info_list)

        external_link_list = like.to_convert_ExternalLink(fetched_tweets, self.lsb)
        self.trace_external_link(external_link_list)

        self.ShrinkFolder(int(self.config["holding"]["holding_file_num"]))
        self.EndOfProcess()
        logger.info(MSG.FAVCRAWLER_CRAWL_DONE.value)
        return 0


if __name__ == "__main__":
    c = FavCrawler()

    # クロール前に保存場所から指定枚数削除しておく
    # c.ShrinkFolder(int(c.config["holding"]["holding_file_num"]) - 10)
    # c.del_cnt = 0
    # c.del_url_list = []

    c.Crawl()
