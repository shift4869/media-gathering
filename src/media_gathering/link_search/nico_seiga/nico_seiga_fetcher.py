from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path

from media_gathering.link_search.fetcher_base import FetcherBase
from media_gathering.link_search.nico_seiga.nico_seiga_downloader import NicoSeigaDownloader
from media_gathering.link_search.nico_seiga.nico_seiga_session import NicoSeigaSession
from media_gathering.link_search.nico_seiga.nico_seiga_url import NicoSeigaURL
from media_gathering.link_search.password import Password
from media_gathering.link_search.url import URL
from media_gathering.link_search.username import Username

logger = getLogger(__name__)
logger.setLevel(INFO)


@dataclass(frozen=True)
class NicoSeigaFetcher(FetcherBase):
    """ニコニコ静画を取得するクラス"""

    session: NicoSeigaSession  # 取得に使う認証済セッション
    base_path: Path  # 保存ディレクトリベースパス

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
    import logging.config

    import orjson

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.json"
    config = orjson.loads(Path(CONFIG_FILE_NAME).read_bytes())

    base_path = Path("./media_gathering/link_search/")
    if config["nico_seiga"]["is_seiga_trace"]:
        fetcher = NicoSeigaFetcher(
            Username(config["nico_seiga"]["email"]), Password(config["nico_seiga"]["password"]), base_path
        )
        illust_id = 11308865
        illust_url = f"https://seiga.nicovideo.jp/seiga/im{illust_id}?query=1"
        fetcher.fetch(illust_url)
