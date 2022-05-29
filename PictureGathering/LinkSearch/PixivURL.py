# coding: utf-8
import re
from pathlib import Path
from dataclasses import dataclass

from PictureGathering.LinkSearch.URL import URL


@dataclass
class PixivURL():
    """PixivURL

    PixivURL を表す文字列を受け取る
    引数がPIXIV_URL_PATTERN と一致する場合にPixivURL として受け入れる

    Raises:
        ValueError: 引数がPIXIV_URL_PATTERN と一致しない文字列の場合

    Returns:
        PixivURL: PixivURLを表すValueObject
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
    def illust_id(self) -> int:
        tail = Path(self.non_query_url).name
        illust_id = int(tail)
        return illust_id

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
        """PixivURLのパターンかどうかを返す

        このメソッドがTrueならばPixivURL インスタンスが作成できる
        また、このメソッドがTrueならば引数のestimated_url が真にPixivURL の形式であることが判別できる
        (v.v.)

        Args:
            estimated_url (str): チェック対象の候補URLを表す文字列

        Returns:
            bool: 引数がPixivURL.PIXIV_URL_PATTERN パターンに則っているならばTrue,
                  そうでないならFalse
        """
        return re.search(PixivURL.PIXIV_URL_PATTERN, estimated_url) is not None

    @classmethod
    def create(cls, url: str | URL) -> "PixivURL":
        """PixivURL インスタンスを作成する

        URL インスタンスを作成して
        それをもとにしてPixivURL インスタンス作成する

        Args:
            url (str | URL): 対象URLを表す文字列 or URL

        Returns:
            PixivURL: PixivURL インスタンス
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
            u = PixivURL.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
