# coding: utf-8
import re
from dataclasses import dataclass

from PictureGathering.LinkSearch.Skeb.Authorname import Authorname
from PictureGathering.LinkSearch.Skeb.Workid import Workid
from PictureGathering.LinkSearch.URL import URL


@dataclass
class SkebURL():
    """SkebURL

    SkebURL を表す文字列を受け取る
    引数がSKEB_URL_PATTERN と一致する場合にSkebURL として受け入れる

    Raises:
        ValueError: 引数がSKEB_URL_PATTERN と一致しない文字列の場合

    Returns:
        SkebURL: SkebURLを表すValueObject
    """
    url: URL

    SKEB_URL_PATTERN = r"^https://skeb.jp/\@(.+?)/works/([0-9]+)"

    def __post_init__(self) -> None:
        """初期化処理

        バリデーションのみ
        """
        non_query_url = self.non_query_url
        if not self.is_valid(non_query_url):
            raise ValueError("URL is not Skeb URL.")

    @property
    def work_id(self) -> Workid:
        m = re.match(SkebURL.SKEB_URL_PATTERN, self.url.non_query_url)
        if m:
            return Workid(int(m.group(2)))
        raise ValueError("SkebURL work_id parse failed.")

    @property
    def author_name(self) -> Authorname:
        m = re.match(SkebURL.SKEB_URL_PATTERN, self.url.non_query_url)
        if m:
            return Authorname(m.group(1))
        raise ValueError("SkebURL author_name parse failed.")

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
        """SkebURLのパターンかどうかを返す

        このメソッドがTrueならばSkebURL インスタンスが作成できる
        また、このメソッドがTrueならば引数のestimated_url が真にSkebURL の形式であることが判別できる
        (v.v.)

        Args:
            estimated_url (str): チェック対象の候補URLを表す文字列

        Returns:
            bool: 引数がSkebURL.SKEB_URL_PATTERN パターンに則っているならばTrue,
                  そうでないならFalse
        """
        return re.search(SkebURL.SKEB_URL_PATTERN, estimated_url) is not None

    @classmethod
    def create(cls, url: str | URL) -> "SkebURL":
        """SkebURL インスタンスを作成する

        URL インスタンスを作成して
        それをもとにしてSkebURL インスタンス作成する

        Args:
            url (str | URL): 対象URLを表す文字列 or URL

        Returns:
            SkebURL: SkebURL インスタンス
        """
        return cls(URL(url))


if __name__ == "__main__":
    urls = [
        "https://skeb.jp/@matsukitchi12/works/25?query=1",  # イラスト（複数）
        "https://skeb.jp/@wata_lemon03/works/7",  # 動画（単体）
        "https://skeb.jp/@_sa_ya_/works/55",  # gif画像（複数）
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = SkebURL.create(url)
            print(u.original_url)
    except ValueError as e:
        print(e)
