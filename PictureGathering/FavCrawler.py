# coding: utf-8
import random
from datetime import datetime
from logging import INFO, getLogger
from pathlib import Path

from PictureGathering.Crawler import Crawler
from PictureGathering.FavDBController import FavDBController
from PictureGathering.LogMessage import MSG
from PictureGathering.noapi.NoAPILikeFetcher import NoAPILikeFetcher

logger = getLogger(__name__)
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
            self.db_cont = FavDBController(db_fullpath)  # テーブルはFavoriteを使用
            if config.getboolean("save_permanent_image_flag"):
                Path(config["save_permanent_image_path"]).mkdir(parents=True, exist_ok=True)

            self.save_path = Path(self.config["save_directory"]["save_fav_path"])
            self.type = "Fav"
        except KeyError:
            logger.exception("invalid config file error.")
            exit(-1)
        logger.info(MSG.FAVCRAWLER_INIT_DONE.value)

    def make_done_message(self):
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

    def crawl(self):
        logger.info(MSG.FAVCRAWLER_CRAWL_START.value)
        logger.info("No API use mode...")

        config = self.config["twitter_api_client"]
        ct0 = config["ct0"]
        auth_token = config["auth_token"]
        target_screen_name = config["target_screen_name"]
        target_id = config["target_id"]
        like = NoAPILikeFetcher(ct0, auth_token, target_screen_name, target_id)
        fetched_tweets = like.fetch()

        # メディア取得
        tweet_info_list = like.to_convert_TweetInfo(fetched_tweets)
        self.interpret_tweets_v2(tweet_info_list)

        # 外部リンク収集
        external_link_list = like.to_convert_ExternalLink(fetched_tweets, self.lsb)
        self.trace_external_link(external_link_list)

        # 後処理
        self.shrink_folder(int(self.config["holding"]["holding_file_num"]))
        self.end_of_process()
        logger.info(MSG.FAVCRAWLER_CRAWL_DONE.value)

        return 0


if __name__ == "__main__":
    c = FavCrawler()

    # クロール前に保存場所から指定枚数削除しておく
    # c.shrink_folder(int(c.config["holding"]["holding_file_num"]) - 10)
    # c.del_cnt = 0
    # c.del_url_list = []

    c.crawl()
