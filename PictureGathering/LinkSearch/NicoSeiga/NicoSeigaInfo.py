# coding: utf-8
from dataclasses import dataclass
from logging import INFO, getLogger

from PictureGathering.LinkSearch.NicoSeiga.Authorid import Authorid
from PictureGathering.LinkSearch.NicoSeiga.Authorname import Authorname
from PictureGathering.LinkSearch.NicoSeiga.Illustid import Illustid
from PictureGathering.LinkSearch.NicoSeiga.Illustname import Illustname


logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class NicoSeigaInfo():
    """NicoSeigaInfo

    Returns:
        NicoSeigaInfo: NicoSeigaInfoを表すValueObject
    """
    illustid: Illustid
    illustname: Illustname
    authorid: Authorid
    authorname: Authorname

    def __post_init__(self) -> None:
        """初期化処理

        バリデーションのみ
        """
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self.illustid, Illustid):
            raise TypeError("illustid must be Illustid.")
        if not isinstance(self.illustname, Illustname):
            raise TypeError("illustname must be Illustname.")
        if not isinstance(self.authorid, Authorid):
            raise TypeError("authorid must be Authorid.")
        if not isinstance(self.authorname, Authorname):
            raise TypeError("authorname must be Authorname.")
        return True


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = NicoSeigaInfo.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
