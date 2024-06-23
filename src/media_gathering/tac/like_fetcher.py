import shutil
from logging import INFO, getLogger
from pathlib import Path

import orjson

from media_gathering.tac.fetcher_base import FetcherBase
from media_gathering.tac.username import Username

logger = getLogger(__name__)
logger.setLevel(INFO)


class LikeFetcher(FetcherBase):
    def __init__(self, ct0: str, auth_token: str, target_screen_name: Username | str, target_id: int) -> None:
        # ct0 と auth_token は同一のアカウントのクッキーから取得しなければならない
        # target_screen_name と target_id はそれぞれの対応が一致しなければならない
        # 機能上は target_id のみ参照する
        # ct0 と auth_token が紐づくアカウントと、 target_id は一致しなくても良い
        # 前者のアカウントで後者の id のTL等を見に行く形になる
        super().__init__(ct0, auth_token, target_screen_name, target_id)

    def get_like_jsons(self, limit: int = 400) -> list[dict]:
        logger.info("Fetched Tweet by TAC -> start")

        # キャッシュ保存場所の準備
        base_path = Path(self.CACHE_PATH)
        if base_path.is_dir():
            shutil.rmtree(base_path)
        base_path.mkdir(parents=True, exist_ok=True)

        # TAC で likes ページをスクレイピング
        scraper = self.twitter.scraper
        likes = scraper.likes([self.twitter.target_id], limit=limit)

        # キャッシュに保存
        for i, like in enumerate(likes):
            Path(base_path / f"likes_{i:02}.json").write_bytes(orjson.dumps(like, orjson.OPT_INDENT_2))

        # キャッシュから読み込み
        # 保存して読み込みをするのでほぼ同一の内容になる
        # 違いは result は json.dump→json.load したときに、エンコード等が吸収されていること
        result: list[dict] = []
        n = len(likes)
        for i in range(n):
            json_dict = orjson.loads(Path(base_path / f"likes_{i:02}.json").read_bytes())
            result.append(json_dict)

        logger.info("Fetched Tweet by TAC -> done")
        return result

    def fetch(self, limit: int = 400) -> list[dict]:
        """Likes ページをクロールして取得する

        Args:
            limit (int, optional): 取得上限

        Returns:
            list[dict]: ツイートオブジェクトを表すJSONリスト
        """
        result = self.get_like_jsons(limit)
        return result


if __name__ == "__main__":
    import configparser
    import logging.config

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.json"
    config_parser = configparser.ConfigParser()
    if not config_parser.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    config = config_parser["twitter_api_client"]
    ct0 = config["ct0"]
    auth_token = config["auth_token"]
    target_screen_name = config["target_screen_name"]
    target_id = int(config["target_id"])
    like = LikeFetcher(ct0, auth_token, target_screen_name, target_id)

    # like取得
    # fetched_tweets = like.fetch()

    # キャッシュから読み込み
    base_path = Path(like.CACHE_PATH)
    fetched_tweets = []
    for cache_path in base_path.glob("*likes*"):
        json_dict = orjson.loads(cache_path.read_bytes())
        fetched_tweets.append(json_dict)
    print(len(fetched_tweets))
