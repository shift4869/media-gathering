# coding: utf-8
import re
import urllib.parse
from dataclasses import dataclass

from PictureGathering.LinkSearch.PixivNovel.Novelid import Novelid
from PictureGathering.LinkSearch.URL import URL


@dataclass
class PixivNovelURL():
    """PixivNovelURL

    PixivNovelURL を表す文字列を受け取る
    引数がPIXIV_NOVEL_URL_PATTERN と一致する場合にPixivNovelURL として受け入れる

    Raises:
        ValueError: 引数がPIXIV_NOVEL_URL_PATTERN と一致しない文字列の場合

    Returns:
        PixivNovelURL: PixivNovelURLを表すValueObject
    """
    url: URL

    PIXIV_NOVEL_URL_PATTERN = r"^https://www.pixiv.net/novel/show.php\?id=[0-9]+"

    def __post_init__(self) -> None:
        """初期化処理

        バリデーションのみ
        """
        original_url = self.url.original_url
        if not self.is_valid(original_url):
            raise ValueError("URL is not pixiv novel URL.")

    @property
    def novel_id(self) -> Novelid:
        """ノベルIDを返す
        """
        original_url = self.url.original_url
        q = urllib.parse.urlparse(original_url).query
        qs = urllib.parse.parse_qs(q)
        novel_id_num = int(qs.get("id", [-1])[0])
        return Novelid(novel_id_num)

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
        """PixivNovelURLのパターンかどうかを返す

        このメソッドがTrueならばPixivNovelURL インスタンスが作成できる
        また、このメソッドがTrueならば引数のestimated_url が真にPixivNovelURL の形式であることが判別できる
        (v.v.)

        Args:
            estimated_url (str): チェック対象の候補URLを表す文字列

        Returns:
            bool: 引数がPixivNovelURL.PIXIV_NOVEL_URL_PATTERN パターンに則っているならばTrue,
                  そうでないならFalse
        """
        return re.search(PixivNovelURL.PIXIV_NOVEL_URL_PATTERN, estimated_url) is not None

    @classmethod
    def create(cls, url: str | URL) -> "PixivNovelURL":
        """PixivNovelURL インスタンスを作成する

        URL インスタンスを作成して
        それをもとにしてPixivNovelURL インスタンス作成する

        Args:
            url (str | URL): 対象URLを表す文字列 or URL

        Returns:
            PixivNovelURL: PixivNovelURL インスタンス
        """
        return cls(URL(url))


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/novel/show.php?id=3195243",  # 作品URL
        "https://www.pixiv.net/novel/show.php?id=3195243&query=1",  # 作品URL（余分なクエリつき）
        "https://www.pixiv.net/novel/show.php?id=",  # idが空白
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    for url in urls:
        try:
            u = PixivNovelURL.create(url)
            print(u.original_url)
        except ValueError as e:
            print(e)
