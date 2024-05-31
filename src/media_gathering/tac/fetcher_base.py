from abc import ABCMeta, abstractmethod
from pathlib import Path

from media_gathering.tac.twitter_api_client_adapter import TwitterAPIClientAdapter
from media_gathering.tac.username import Username


class FetcherBase(metaclass=ABCMeta):
    twitter: TwitterAPIClientAdapter
    CACHE_PATH = Path(__file__).parent / "cache/"

    def __init__(self, ct0: str, auth_token: str, target_screen_name: Username | str, target_id: int) -> None:
        # ct0 と auth_token は同一のアカウントのクッキーから取得しなければならない
        # target_screen_name と target_id はそれぞれの対応が一致しなければならない
        # 　（機能上は target_id のみ参照する）
        # ct0 と auth_token が紐づくアカウントと、 target_id は一致しなくても良い
        # 　（前者のアカウントで後者の id のTL等を見に行く形になる）
        self.twitter = TwitterAPIClientAdapter(ct0, auth_token, target_screen_name, target_id)

    @abstractmethod
    def fetch(self) -> list[dict]:
        """TwitterページからJSONをfetchする

        Returns:
            list[dict]: fetchされたJSONを表す辞書のリスト
        """
        raise NotImplementedError


if __name__ == "__main__":
    pass
