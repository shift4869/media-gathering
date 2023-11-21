from dataclasses import dataclass

from PictureGathering.LinkSearch.NicoSeiga.Authorid import Authorid
from PictureGathering.LinkSearch.NicoSeiga.Authorname import Authorname
from PictureGathering.LinkSearch.NicoSeiga.Illustid import Illustid
from PictureGathering.LinkSearch.NicoSeiga.Illustname import Illustname


@dataclass(frozen=True)
class NicoSeigaInfo():
    """NicoSeigaInfo

    Returns:
        NicoSeigaInfo: NicoSeigaInfoを表すValueObject
    """
    illust_id: Illustid
    illust_name: Illustname
    author_id: Authorid
    author_name: Authorname

    def __post_init__(self) -> None:
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self.illust_id, Illustid):
            raise TypeError("illust_id must be Illustid.")
        if not isinstance(self.illust_name, Illustname):
            raise TypeError("illust_name must be Illustname.")
        if not isinstance(self.author_id, Authorid):
            raise TypeError("author_id must be Authorid.")
        if not isinstance(self.author_name, Authorname):
            raise TypeError("author_name must be Authorname.")
        return True


if __name__ == "__main__":
    illust_id = Illustid(1234567)
    illust_name = Illustname("作品名1")
    author_id = Authorid(12345678)
    author_name = Authorname("作者名1")
    illust_info = NicoSeigaInfo(illust_id, illust_name, author_id, author_name)
    print(illust_info)
