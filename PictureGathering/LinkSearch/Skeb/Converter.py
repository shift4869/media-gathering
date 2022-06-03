# coding: utf-8
import enum
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar


from PictureGathering.LinkSearch.Skeb.IllustConvertor import IllustConvertor
from PictureGathering.LinkSearch.Skeb.SaveFilename import Extension
from PictureGathering.LinkSearch.Skeb.SkebSaveDirectoryPath import SkebSaveDirectoryPath


@dataclass(frozen=True)
class ConvertResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()


@dataclass()
class Converter():
    src_file_pathlist: list[Path]
    dst_file_pathlist: ClassVar[list[Path]]

    # 変換マッピング
    convert_map = {
        Extension.WEBP.value: Extension.PNG.value,
        Extension.MP4.value: Extension.MP4.value,
    }

    def __post_init__(self):
        self._is_valid()
        self.dst_file_pathlist = []

    def _is_valid(self):
        if not isinstance(self.src_file_pathlist, list):
            raise TypeError("src_file_pathlist is not list[], invalid Converter.")
        if self.src_file_pathlist:
            if not all([isinstance(r, Path) for r in self.src_file_pathlist]):
                raise ValueError("include not Path element, invalid Converter")
        return True

    def convert(self) -> ConvertResult:
        if len(self.src_file_pathlist) == 0:
            # 変換対象がなかった
            return ConvertResult.PASSED

        for src_path in self.src_file_pathlist:
            dst_path = None
            src_ext = src_path.suffix
            dst_ext = self.convert_map.get(src_ext, Extension.UNKNOWN.value)

            if src_ext == Extension.WEBP.value:
                dst_path = IllustConvertor(src_path, dst_ext).convert()
            else:
                dst_path = src_path.with_suffix(dst_ext)

            self.dst_file_pathlist.append(dst_path)

        return ConvertResult.SUCCESS


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = SkebSaveDirectoryPath.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
