import re
import urllib.parse
from dataclasses import dataclass

from media_gathering.link_search.nijie.workid import Workid
from media_gathering.link_search.url import URL


@dataclass
class NijieURL:
    """NijieURL

    NijieURL を表す文字列を受け取る
    引数が NIJIE_URL_PATTERN と一致する場合に NijieURL として受け入れる

    Raises:
        ValueError: 引数が NIJIE_URL_PATTERN と一致しない文字列の場合

    Returns:
        NijieURL: NijieURL を表す ValueObject
    """

    url: URL

    NIJIE_URL_PATTERN = r"^https?://nijie.info/view.php\?id=[0-9]+"
    NIJIE_URL_DETAIL_PATTERN = r"^https?://nijie.info/view_popup.php\?id=[0-9]+"

    def __post_init__(self) -> None:
        """初期化処理

        バリデーションのみ
        """
        original_url = self.url.original_url
        if not self.is_valid(original_url):
            raise ValueError("URL is not nijie URL.")

    @property
    def work_id(self) -> Workid:
        """作品IDを返す"""
        original_url = self.url.original_url
        qs = urllib.parse.urlparse(original_url).query
        qd = urllib.parse.parse_qs(qs)
        work_id_num = int(qd.get("id", [-1])[0])
        return Workid(work_id_num)

    @property
    def non_query_url(self) -> str:
        """クエリなしURLを返す"""
        return self.url.non_query_url

    @property
    def original_url(self) -> str:
        """元のURLを返す"""
        return self.url.original_url

    @classmethod
    def is_valid(cls, estimated_url: str) -> bool:
        """NijieURL のパターンかどうかを返す

        このメソッドがTrueならば NijieURL インスタンスが作成できる
        また、このメソッドがTrueならば引数の estimated_url が真に NijieURL の形式であることが判別できる
        (v.v.)

        Args:
            estimated_url (str): チェック対象の候補URLを表す文字列

        Returns:
            bool: 引数が NijieURL.NIJIE_URL_PATTERN パターンに則っているならばTrue,
                  そうでないならFalse
        """
        f1 = re.search(NijieURL.NIJIE_URL_PATTERN, estimated_url) is not None
        f2 = re.search(NijieURL.NIJIE_URL_DETAIL_PATTERN, estimated_url) is not None
        return f1 or f2

    @classmethod
    def create(cls, url: str | URL) -> "NijieURL":
        """NijieURL インスタンスを作成する

        URL インスタンスを作成して
        それをもとにして NijieURL インスタンス作成する

        Args:
            url (str | URL): 対象URLを表す文字列 or URL

        Returns:
            NijieURL: NijieURL インスタンス
        """
        return cls(URL(url))


if __name__ == "__main__":
    urls = [
        "https://nijie.info/view_popup.php?id=12345678",
        "https://nijie.info/view_popup.php?id=12345678?some_query=1",
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = NijieURL.create(url)
            print(u.original_url)
    except ValueError as e:
        print(e)
