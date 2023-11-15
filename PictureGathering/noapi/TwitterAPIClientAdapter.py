from logging import INFO, getLogger

from twitter.account import Account
from twitter.scraper import Scraper

from PictureGathering.noapi.Username import Username

logger = getLogger(__name__)
logger.setLevel(INFO)


class TwitterAPIClientAdapter():
    _ct0: str
    _auth_token: str
    _target_screen_name: Username
    _target_id: int

    def __init__(self, ct0: str, auth_token: str, target_screen_name: Username | str, target_id: int) -> None:
        if not isinstance(ct0, str):
            raise ValueError("ct0 must be str.")
        if not isinstance(auth_token, str):
            raise ValueError("auth_token must be str.")
        if not isinstance(target_screen_name, (Username, str)):
            raise ValueError("target_screen_name must be Username or str.")
        if not isinstance(target_id, int):
            raise ValueError("target_id must be int.")

        self._ct0 = ct0
        self._auth_token = auth_token
        if isinstance(target_screen_name, Username):
            target_screen_name = target_screen_name.name
        self._target_screen_name = Username(target_screen_name)
        self._target_id = int(target_id)

    @property
    def ct0(self) -> str:
        return self._ct0

    @property
    def auth_token(self) -> str:
        return self._auth_token

    @property
    def target_screen_name(self) -> Username:
        return self._target_screen_name

    @property
    def target_id(self) -> int:
        return self._target_id

    @property
    def scraper(self) -> Scraper:
        if hasattr(self, "_scraper"):
            return self._scraper
        self._scraper = Scraper(cookies={"ct0": self.ct0, "auth_token": self.auth_token}, pbar=False)
        return self._scraper

    @property
    def account(self) -> Account:
        if hasattr(self, "_account"):
            return self._account
        self._account = Account(cookies={"ct0": self.ct0, "auth_token": self.auth_token}, pbar=False)
        return self._account


if __name__ == "__main__":
    pass
