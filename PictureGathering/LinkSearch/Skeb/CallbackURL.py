# coding: utf-8
from dataclasses import dataclass

from PictureGathering.LinkSearch.Skeb.SkebToken import SkebToken
from PictureGathering.LinkSearch.URL import URL


@dataclass
class CallbackURL():
    """CallbackURL

    CallbackURL を表す文字列を生成する
    """
    url: URL

    @property
    def callback_url(self) -> str:
        return self.url.original_url

    @classmethod
    def create(cls, top_url: URL, path: str, token: SkebToken) -> "CallbackURL":
        """コールバックURLを生成する

        以下のURLを生成する
            callback_url = f"{top_url}callback?path=/{path}&token={token.token}"
        tokenの正当性はチェックしない

        Args:
            top_url (URL): skebトップページのURL
            path (str): 遷移先のURLパス文字列、先頭に"/"があった場合は"/"は無視される
            token (SkebToken): アクセス用トークン

        Returns:
            CallbackURL: コールバックURLインスタンス
        """
        # pathの先頭チェック
        # 先頭と末尾に"/"があった場合は"/"を無視する
        if path[0] == "/":
            path = path[1:]
        if len(path) > 1 and path[-1] == "/":
            path = path[:-1]

        callback_url = f"{top_url.non_query_url}callback?path=/{path}&token={token.token}"
        return cls(URL(callback_url))


if __name__ == "__main__":
    import configparser
    import logging.config
    from pathlib import Path
    from PictureGathering.LinkSearch.Password import Password
    from PictureGathering.LinkSearch.Skeb.SkebFetcher import SkebFetcher
    from PictureGathering.LinkSearch.Username import Username

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    if config["skeb"].getboolean("is_skeb_trace"):
        fetcher = SkebFetcher(Username(config["skeb"]["twitter_id"]), Password(config["skeb"]["twitter_password"]), base_path)

        # イラスト（複数）
        work_url = "https://skeb.jp/@matsukitchi12/works/25?query=1"
        # 動画（単体）
        # work_url = "https://skeb.jp/@wata_lemon03/works/7"
        # gif画像（複数）
        # work_url = "https://skeb.jp/@_sa_ya_/works/55"

        fetcher.fetch(work_url)
