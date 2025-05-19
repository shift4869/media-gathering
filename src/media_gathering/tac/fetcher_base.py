from abc import ABCMeta, abstractmethod
from pathlib import Path

from tweeterpy import TweeterPy

from media_gathering.tac.twitter_api_client_adapter import TwitterAPIClientAdapter
from media_gathering.tac.username import Username


class FetcherBase(metaclass=ABCMeta):
    twitter: TweeterPy
    CACHE_PATH = Path(__file__).parent / "cache/"

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

        self.twitter = TweeterPy(log_level="WARNING")
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.twitter.generate_session(auth_token=self.auth_token)
        self.twitter.save_session(path=Path(self.session_path).parent)

    @property
    def session_path(self) -> Path:
        """セッションファイルパス"""
        return Path(self.CACHE_PATH) / f"session/{self.target_screen_name}.pkl"

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
    pass
