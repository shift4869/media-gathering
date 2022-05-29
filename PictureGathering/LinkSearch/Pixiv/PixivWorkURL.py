# coding: utf-8
import re
from dataclasses import dataclass
from pathlib import Path

from PictureGathering.LinkSearch.Pixiv.Illustid import Illustid
from PictureGathering.LinkSearch.URL import URL


@dataclass
class PixivWorkURL():
    """PixivWorkURL

    PixivWorkURL を表す文字列を受け取る
    引数がPIXIV_URL_PATTERN と一致する場合にPixivWorkURL として受け入れる

    Raises:
        ValueError: 引数がPIXIV_URL_PATTERN と一致しない文字列の場合

    Returns:
        PixivWorkURL: PixivWorkURLを表すValueObject
    """
    url: URL

    PIXIV_URL_PATTERN = r"^https://www.pixiv.net/artworks/[0-9]+$"

    def __post_init__(self) -> None:
        """初期化処理

        バリデーションのみ
        """
        non_query_url = self.url.non_query_url
        if not self.is_valid(non_query_url):
            raise ValueError("URL is not Pixiv URL.")

    @property
    def illust_id(self) -> Illustid:
        tail = Path(self.non_query_url).name
        illust_id = int(tail)
        return Illustid(illust_id)

    @property
    def non_query_url(self) -> str:
        """クエリなしURLを返す
        """
        return self.url.non_query_url

    @property
    def original_url(self) -> str:
        """元のURLを返す
        """
        return self.url.original_url

    @classmethod
    def is_valid(cls, estimated_url: str) -> bool:
        """PixivWorkURLのパターンかどうかを返す

        このメソッドがTrueならばPixivWorkURL インスタンスが作成できる
        また、このメソッドがTrueならば引数のestimated_url が真にPixivWorkURL の形式であることが判別できる
        (v.v.)

        Args:
            estimated_url (str): チェック対象の候補URLを表す文字列

        Returns:
            bool: 引数がPixivWorkURL.PIXIV_URL_PATTERN パターンに則っているならばTrue,
                  そうでないならFalse
        """
        return re.search(PixivWorkURL.PIXIV_URL_PATTERN, estimated_url) is not None

    @classmethod
    def create(cls, url: str | URL) -> "PixivWorkURL":
        """PixivWorkURL インスタンスを作成する

        URL インスタンスを作成して
        それをもとにしてPixivWorkURL インスタンス作成する

        Args:
            url (str | URL): 対象URLを表す文字列 or URL

        Returns:
            PixivWorkURL: PixivWorkURL インスタンス
        """
        return cls(URL(url))


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = PixivWorkURL.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
