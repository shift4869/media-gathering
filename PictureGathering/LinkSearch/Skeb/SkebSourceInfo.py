# coding: utf-8
from dataclasses import dataclass

from PictureGathering.LinkSearch.Skeb.SaveFilename import Extension
from PictureGathering.LinkSearch.URL import URL


@dataclass(frozen=True)
class SkebSourceInfo():
    """Skeb直リンク情報
    """
    _url: URL              # 直リンク
    _extension: Extension  # 拡張子

    def __post_init__(self) -> None:
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self._url, URL):
            raise TypeError("_url is not URL.")
        if not isinstance(self._extension, Extension):
            raise TypeError("_extension is not Extension.")
        return True

    @property
    def url(self) -> URL:
        return self._url

    @property
    def extension(self) -> Extension:
        return self._extension


if __name__ == "__main__":
    url = URL("https://skeb.jp/source_link/dummy01?query=1")
    ext = Extension.WEBP
    source_info = SkebSourceInfo(url, ext)
    print(source_info.url.original_url)
    print(source_info.extension.value)
