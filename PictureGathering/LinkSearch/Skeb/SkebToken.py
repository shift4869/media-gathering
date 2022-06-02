# coding: utf-8
from dataclasses import dataclass


@dataclass(frozen=True)
class SkebToken():
    """SkebToken

    Returns:
        SkebToken: SkebTokenを表すValueObject
    """
    token: str

    def __post_init__(self) -> None:
        """初期化処理

        バリデーションのみ
        """
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self.token, str):
            raise TypeError("token is not string, invalid SkebToken.")
        if self.token == "":
            raise ValueError("empty string, invalid SkebToken")
        return True


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = SkebToken.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
