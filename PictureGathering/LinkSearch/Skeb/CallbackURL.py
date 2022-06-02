# coding: utf-8
from dataclasses import dataclass

from PictureGathering.LinkSearch.Skeb.SkebToken import SkebToken
from PictureGathering.LinkSearch.URL import URL


@dataclass
class CallbackURL():
    """CallbackURL

    CallbackURL を表す文字列を生成する

    Returns:
        CallbackURL: CallbackURLを表すValueObject
    """
    url: URL

    @property
    def callback_url(self) -> str:
        return self.url.original_url

    @classmethod
    def create(cls, top_url: URL, path: str, token: SkebToken) -> "CallbackURL":
        """コールバックURLを生成する

        Notes:
            以下のURLを生成する
                callback_url = f"{self.top_url}callback?path=/{path}&token={token}"
            self.top_urlが不正（存在しないor空白）の場合は空文字列を返す
            tokenの正当性はチェックしない(self.IsValidTokenの役目)

        Args:
            path (str): 遷移先のURLパス、先頭に"/"があった場合は"/"は無視される
            token (str): アクセス用トークン

        Returns:
            str: 正常時callback_url、異常時 空文字列
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
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = CallbackURL.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
