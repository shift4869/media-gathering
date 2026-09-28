import math
import random
import shutil
import time
from copy import deepcopy
from logging import INFO, getLogger
from pathlib import Path

import orjson
from tweeterpy.core.resources import XOperations

from media_gathering.tac.fetcher_base import FetcherBase
from media_gathering.tac.username import Username
from media_gathering.util import find_values

logger = getLogger(__name__)
logger.setLevel(INFO)


class RetweetFetcher(FetcherBase):
    def __init__(self, ct0: str, auth_token: str, target_screen_name: Username | str, target_id: int) -> None:
        # ct0 と auth_token は同一のアカウントのクッキーから取得しなければならない
        # target_screen_name と target_id はそれぞれの対応が一致しなければならない
        # 機能上は target_id のみ参照する
        # ct0 と auth_token が紐づくアカウントと、 target_id は一致しなくても良い
        # 前者のアカウントで後者の id のTL等を見に行く形になる
        super().__init__(ct0, auth_token, target_screen_name, target_id)

    def get_retweet_jsons(self, limit: int = 400) -> list[dict]:
        logger.info("Fetched Tweet by TP -> start")

        # キャッシュ保存場所の準備
        base_path = Path(self.cache_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # TP で TL をスクレイピング
        result = []
        timeline_tweets = []

        # ページング処理
        next_cursor = ""
        current_cursor = ""
        max_page = range(math.ceil(limit / 20))
        for _ in max_page:
            variables_dict = {
                "userId": str(self.target_id),
                "count": 20,
                "includePromotedContent": True,
                "withQuickPromoteEligibilityTweetFields": True,
                "withVoice": True,
                "withV2Timeline": True,
            }

            if next_cursor != "":
                variables_dict["cursor"] = next_cursor
                current_cursor = next_cursor

            timeline_tweet_partial = self.twitter.execute(
                operation=XOperations.UserTweets,
                variables=variables_dict,
            )
            timeline_tweets.append(timeline_tweet_partial["data"])

            content_list = find_values(timeline_tweet_partial, "content")
            for content in content_list:
                if "__typename" in content and content["__typename"] == "TimelineTimelineCursor":
                    if "cursorType" in content and content["cursorType"] == "Bottom":
                        next_cursor = content["value"]
                        break
            if not next_cursor:
                break
            if current_cursor == next_cursor:
                break

            time.sleep(random.uniform(0.1, 0.5))

        if not timeline_tweets:
            raise ValueError("Failed getting XOperations.UserTweets -> abort")

        # キャッシュに保存
        filename = f"{time.time_ns()}_tp_timeline_tweets.json"
        Path(base_path / filename).write_bytes(orjson.dumps(timeline_tweets, option=orjson.OPT_INDENT_2))
        logger.info(f"Cached to {filename}.")

        # キャッシュから読み込み
        # 保存して読み込みをするのでほぼ同一の内容になる
        # 違いは result は json.dump→json.load したときに、エンコード等が吸収されていること
        result: list[dict] = orjson.loads(Path(base_path / filename).read_bytes())

        logger.info("Fetched Tweet by TP -> done")
        return result

    def fetch(self, limit: int = 400) -> list[dict]:
        """TL ページをクロールして取得する

        Args:
            limit (int, optional): 取得上限

        Returns:
            list[dict]: ツイートオブジェクトを表すJSONリスト
        """
        result = self.get_retweet_jsons(limit)
        return result


if __name__ == "__main__":
    import logging.config

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.json"
    config = orjson.loads(Path(CONFIG_FILE_NAME).read_bytes())
    if not config:
        raise IOError

    ct0 = config["twitter_api_client"]["ct0"]
    auth_token = config["twitter_api_client"]["auth_token"]
    target_screen_name = config["twitter_api_client"]["target_screen_name"]
    target_id = int(config["twitter_api_client"]["target_id"])
    retweet = RetweetFetcher(ct0, auth_token, target_screen_name, target_id)

    # retweet取得
    fetched_tweets = retweet.fetch()

    # キャッシュから読み込み
    base_path = Path(retweet.cache_path)
    fetched_tweets = []
    for cache_path in base_path.glob("*timeline_tweets*"):
        json_dict = orjson.loads(cache_path.read_bytes())
        fetched_tweets.append(json_dict)
    print(len(fetched_tweets))
