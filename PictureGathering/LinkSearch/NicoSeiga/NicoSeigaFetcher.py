# coding: utf-8
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path

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
    """ニコニコ静画を取得するクラス
    """
    session: NicoSeigaSession  # 取得に使う認証済セッション
    base_path: Path            # 保存ディレクトリベースパス

    def __init__(self, username: Username, password: Password, base_path: Path):
        """初期化処理

        バリデーションとクッキー取得

        Args:
            username (Username): ニコニコログイン用ユーザーID
            password (Password):  ニコニコログイン用パスワード
            base_path (Path): 保存ディレクトリベースパス
        """
        super().__init__()

        if not isinstance(username, Username):
            raise TypeError("username is not Username.")
        if not isinstance(password, Password):
            raise TypeError("password is not Password.")
        if not isinstance(base_path, Path):
            raise TypeError("base_path is not Path.")

        object.__setattr__(self, "session", NicoSeigaSession(username, password))
        object.__setattr__(self, "base_path", base_path)

    def is_target_url(self, url: URL) -> bool:
        """担当URLかどうか判定する

        FetcherBaseオーバーライド

        Args:
            url (URL): 処理対象url

        Returns:
            bool: 担当urlだった場合True, そうでない場合False
        """
        return NicoSeigaURL.is_valid(url.original_url)

    def fetch(self, url: URL) -> None:
        """担当処理：ニコニコ静画作品を取得する

        FetcherBaseオーバーライド

        Args:
            url (URL): 処理対象url
        """
        nicoseiga_url = NicoSeigaURL.create(url)
        NicoSeigaDownloader(nicoseiga_url, self.base_path, self.session).download()


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
        illust_url = f"https://seiga.nicovideo.jp/seiga/im{illust_id}?query=1"
        fetcher.fetch(illust_url)
