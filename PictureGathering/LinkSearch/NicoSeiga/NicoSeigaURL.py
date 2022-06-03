# coding: utf-8
from pathlib import Path
import re
from dataclasses import dataclass

from PictureGathering.LinkSearch.NicoSeiga.Illustid import Illustid
from PictureGathering.LinkSearch.URL import URL


@dataclass
class NicoSeigaURL():
    """NicoSeigaURL

    NicoSeigaURL を表す文字列を受け取る
    引数がNICOSEIGA_URL_PATTERN と一致する場合にNicoSeigaURL として受け入れる

    Raises:
        ValueError: 引数がNICOSEIGA_URL_PATTERN と一致しない文字列の場合

    Returns:
        NicoSeigaURL: NicoSeigaURLを表すValueObject
    """
    url: URL

    NICOSEIGA_URL_PATTERN_1 = r"^https://seiga.nicovideo.jp/seiga/(im)[0-9]+"
    NICOSEIGA_URL_PATTERN_2 = r"^http://nico.ms/(im)[0-9]+"

    def __post_init__(self) -> None:
        """初期化処理

        バリデーションのみ
        """
        non_query_url = self.non_query_url
        if not self.is_valid(non_query_url):
            raise ValueError("URL is not NicoSeiga URL.")

    @property
    def illust_id(self) -> Illustid:
        """イラストIDを返す
        """
        non_query_url = self.non_query_url
        tail = Path(non_query_url).name
        if tail[:2] != "im":
            raise ValueError("URL is not NicoSeiga URL.")

        illust_id = int(tail[2:])
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
        """NicoSeigaURLのパターンかどうかを返す

        このメソッドがTrueならばNicoSeigaURL インスタンスが作成できる
        また、このメソッドがTrueならば引数のestimated_url が真にNicoSeigaURL の形式であることが判別できる
        (v.v.)

        Args:
            estimated_url (str): チェック対象の候補URLを表す文字列

        Returns:
            bool: 引数がNicoSeigaURL.NICOSEIGA_URL_PATTERN パターンに則っているならばTrue,
                  そうでないならFalse
        """
        f1 = re.search(NicoSeigaURL.NICOSEIGA_URL_PATTERN_1, estimated_url) is not None
        f2 = re.search(NicoSeigaURL.NICOSEIGA_URL_PATTERN_2, estimated_url) is not None
        return f1 or f2

    @classmethod
    def create(cls, url: str | URL) -> "NicoSeigaURL":
        """NicoSeigaURL インスタンスを作成する

        URL インスタンスを作成して
        それをもとにしてNicoSeigaURL インスタンス作成する

        Args:
            url (str | URL): 対象URLを表す文字列 or URL

        Returns:
            NicoSeigaURL: NicoSeigaURL インスタンス
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
            u = NicoSeigaURL.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
