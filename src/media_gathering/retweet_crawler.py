import random
from datetime import datetime
from logging import INFO, getLogger
from pathlib import Path

from media_gathering.crawler import Crawler
from media_gathering.log_message import MSG
from media_gathering.retweet_db_controller import RetweetDBController
from media_gathering.tac.retweet_fetcher import RetweetFetcher
from media_gathering.tac.retweet_parser import RetweetParser
from media_gathering.util import Result

logger = getLogger(__name__)
logger.setLevel(INFO)


class RetweetCrawler(Crawler):
    def __init__(self) -> None:
        logger.info(MSG.RTCRAWLER_INIT_START.value)
        super().__init__()
        try:
            config = self.config["db"]
            save_path = Path(config["save_path"])
            save_path.mkdir(parents=True, exist_ok=True)
            db_fullpath = save_path / config["save_file_name"]
            self.db_cont = RetweetDBController(db_fullpath)  # テーブルはRetweetを使用

            config = self.config["save_permanent"]
            if config["save_permanent_media_flag"]:
                Path(config["save_permanent_media_path"]).mkdir(parents=True, exist_ok=True)

            self.save_path = Path(self.config["save_directory"]["save_retweet_path"])
            self.type = "RT"
        except KeyError as e:
            logger.exception(e)
            raise
        logger.info(MSG.RTCRAWLER_INIT_DONE.value)

    def is_post(self) -> bool:
        return self.config["notification"]["is_post_retweet_done_reply"]

    def make_done_message(self) -> str:
        now_str = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        done_msg = "Retweet MediaGathering run.\n"
        done_msg += now_str
        done_msg += " Process Done !!\n"
        done_msg += f"add {self.add_cnt} new images. "
        done_msg += f"delete {self.del_cnt} old images."
        done_msg += "\n"

        # メディアURLをランダムにピックアップする
        pickup_url_list = random.sample(self.add_url_list, min(4, len(self.add_url_list)))
        for pickup_url in pickup_url_list:
            pickup_url = str(pickup_url).replace(":orig", "")
            done_msg += pickup_url + "\n"

        return done_msg

    def crawl(self) -> Result:
        logger.info(MSG.RTCRAWLER_CRAWL_START.value)
        logger.info("TAC use mode...")

        config = self.config["twitter_api_client"]
        ct0 = config["ct0"]
        auth_token = config["auth_token"]
        target_screen_name = config["target_screen_name"]
        target_id = int(config["target_id"])
        retweet = RetweetFetcher(ct0, auth_token, target_screen_name, target_id)

        limit = int(self.config["tweet_timeline"]["retweet_get_max_count"])
        fetched_tweets = retweet.fetch(limit)

        parser = RetweetParser(fetched_tweets, self.lsb)

        # メディア取得
        logger.info(MSG.MEDIA_DOWNLOAD_START.value)
        tweet_info_list = parser.parse_to_TweetInfo()
        self.interpret_tweets(tweet_info_list)
        logger.info(MSG.MEDIA_DOWNLOAD_DONE.value)

        # 外部リンク収集
        logger.info(MSG.GETTING_EXTERNAL_LINK_START.value)
        external_link_list = parser.parse_to_ExternalLink()
        self.trace_external_link(external_link_list)
        logger.info(MSG.GETTING_EXTERNAL_LINK_DONE.value)

        # 後処理
        self.shrink_folder(int(self.config["holding"]["holding_file_num"]))
        self.end_of_process()
        logger.info(MSG.RTCRAWLER_CRAWL_DONE.value)

        return Result.success


if __name__ == "__main__":
    c = RetweetCrawler()
    c.crawl()
