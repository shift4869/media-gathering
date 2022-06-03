# coding: utf-8
from dataclasses import dataclass

from PictureGathering.LinkSearch.Skeb.SaveFilename import Extension
from PictureGathering.LinkSearch.URL import URL


@dataclass(frozen=True)
class SkebSourceInfo():
    _url: URL
    _extension: Extension

    @property
    def url(self) -> URL:
        return self._url

    @property
    def extension(self) -> Extension:
        return self._extension


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
            username = SkebSourceInfo(name)
            print(username.name)
        except (ValueError, TypeError) as e:
            print(e.args[0])
