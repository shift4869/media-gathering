# coding: utf-8
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from PictureGathering.LinkSearch.FetcherBase import FetcherBase
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaDownloader import NicoSeigaDownloader
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSession import NicoSeigaSession
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaURL import NicoSeigaURL
from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username

logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class NicoSeigaFetcher(FetcherBase):
    session: NicoSeigaSession
    base_path: Path

    HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36"}

    LOGIN_ENDPOINT = "https://account.nicovideo.jp/api/v1/login?show_button_twitter=1&site=niconico&show_button_facebook=1&next_url=&mail_or_tel=1"

    def __init__(self, username: Username, password: Password, base_path: Path):
        super().__init__()

        if not isinstance(username, Username):
            raise TypeError("username is not Username.")
        if not isinstance(password, Password):
            raise TypeError("password is not Password.")
        if not isinstance(base_path, Path):
            raise TypeError("base_path is not Path.")

        object.__setattr__(self, "session", self.login(username, password))
        object.__setattr__(self, "base_path", base_path)

    def login(self, username: Username, password: Password) -> NicoSeigaSession:
        """セッションを開始し、ログインする

        Args:
            email (str): ニコニコユーザーIDとして登録したemailアドレス
            password (str): ニコニコユーザーIDのパスワード

        Returns:
            session, auth_success (requests.Session, boolean): 認証済みセッションと認証結果の組
        """
        # セッション開始
        session = requests.session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))

        # ログイン
        params = {
            "mail_tel": username.name,
            "password": password.password,
        }
        response = session.post(self.LOGIN_ENDPOINT, data=params, headers=self.HEADERS)
        response.raise_for_status()

        return NicoSeigaSession(session, self.HEADERS)

    def is_target_url(self, url: URL) -> bool:
        return NicoSeigaURL.is_valid(url.original_url)

    def run(self, url: URL) -> None:
        nicoseiga_url = NicoSeigaURL.create(url)
        result = NicoSeigaDownloader(nicoseiga_url, self.base_path, self.session).result


if __name__ == "__main__":
    import configparser
    import logging.config
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    if config["nico_seiga"].getboolean("is_seiga_trace"):
        fetcher = NicoSeigaFetcher(Username(config["nico_seiga"]["email"]), Password(config["nico_seiga"]["password"]), base_path)
        illust_id = 5360137
        illust_url = f"https://seiga.nicovideo.jp/seiga/im{illust_id}"
        fetcher.run(illust_url)
