# coding: utf-8
import enum
from dataclasses import dataclass

from PictureGathering.LinkSearch.URL import URL


@dataclass(frozen=True)
class SourceType(enum.Enum):
    ILLUST = "Illust"
    VIDEO = "Video"


@dataclass(frozen=True)
class SkebSourceInfo():
    _url: URL
    _type: SourceType

    @property
    def url(self) -> URL:
        return self._url

    @property
    def type(self) -> SourceType:
        return self._type


if __name__ == "__main__":
    names = [
        "作品名1",
        "作品名2?****//",
        "作品名3😀",
        "",
        -1,
    ]

    for name in names:
        try:
            username = SkebSourceURLList(name)
            print(username.name)
        except (ValueError, TypeError) as e:
            print(e.args[0])
