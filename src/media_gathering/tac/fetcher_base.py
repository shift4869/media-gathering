from abc import ABCMeta, abstractmethod
from pathlib import Path

from tweeterpy import TweeterPy

from media_gathering.tac.twitter_api_client_adapter import TwitterAPIClientAdapter
from media_gathering.tac.username import Username


class FetcherBase(metaclass=ABCMeta):
    ct0: str
    auth_token: str
    target_screen_name: str
    target_id: int
    tac_twitter: TwitterAPIClientAdapter
    twitter: TweeterPy
    cache_path: Path
    session_path: Path

    def __init__(self, ct0: str, auth_token: str, target_screen_name: Username | str, target_id: int) -> None:
        # ct0 と auth_token は同一のアカウントのクッキーから取得しなければならない
        # target_screen_name と target_id はそれぞれの対応が一致しなければならない
        # 　（機能上は target_id のみ参照する）
        # ct0 と auth_token が紐づくアカウントと、 target_id は一致しなくても良い
        # 　（前者のアカウントで後者の id のTL等を見に行く形になる）
        self.tac_twitter = TwitterAPIClientAdapter(ct0, auth_token, target_screen_name, target_id)

        self.ct0 = ct0
        self.auth_token = auth_token
        self.target_screen_name = target_screen_name
        self.target_id = target_id

        self.cache_path = Path("./data/") / str(target_id)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self.session_path.parent.mkdir(parents=True, exist_ok=True)

        self.twitter = TweeterPy()
        self.twitter.generate_session(auth_token=self.auth_token)
        # self.twitter.save_session(path=Path(self.session_path).parent)

    @property
    def session_path(self) -> Path:
        """セッションファイルパス"""
        return self.cache_path / f"session_{self.target_screen_name}.pkl"

    @abstractmethod
    def fetch(self, limit: int = 400) -> list[dict]:
        """TwitterページからJSONをfetchする

        Args:
            limit (int, optional): 取得上限

        Returns:
            list[dict]: fetchされたJSONを表す辞書のリスト
        """
        raise NotImplementedError


if __name__ == "__main__":
    import logging.config

    import orjson

    from media_gathering.tac.like_fetcher import LikeFetcher
    from media_gathering.tac.retweet_fetcher import RetweetFetcher

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
