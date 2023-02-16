# coding: utf-8
import enum
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from PictureGathering.LinkSearch.Skeb.IllustConvertor import IllustConvertor
from PictureGathering.LinkSearch.Skeb.SaveFilename import Extension


@dataclass(frozen=True)
class ConvertResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()


@dataclass()
class Converter():
    """DL後のファイルを変換するクラス
    """
    src_file_pathlist: list[Path]            # 変換対象ファイルのパスリスト
    dst_file_pathlist: ClassVar[list[Path]]  # 変換完了後ファイルのパスリスト

    # 拡張子ごとの変換マッピング
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
        """DL後のファイルを変換する
   
        src_file_pathlistに格納されているパスにあるファイルの拡張子を判別し
        変換対象ならば変換する

        Returns:
            ConvertResult: 変換結果
        """
        if len(self.src_file_pathlist) == 0:
            # 変換対象がなかった
            return ConvertResult.PASSED

        for src_path in self.src_file_pathlist:
            if not src_path.is_file():
                continue
            dst_path = None
            src_ext = src_path.suffix
            dst_ext = self.convert_map.get(src_ext, Extension.UNKNOWN.value)

            if src_ext == Extension.WEBP.value:
                # .webpを.pngに変換
                dst_path = IllustConvertor(src_path, dst_ext).convert()
            else:
                dst_path = src_path.with_suffix(dst_ext)

            self.dst_file_pathlist.append(dst_path)

        return ConvertResult.SUCCESS


if __name__ == "__main__":
    import configparser
    import logging.config
    from pathlib import Path

    from PictureGathering.LinkSearch.Password import Password
    from PictureGathering.LinkSearch.Skeb.SkebFetcher import SkebFetcher
    from PictureGathering.LinkSearch.Username import Username

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    if config["skeb"].getboolean("is_skeb_trace"):
        fetcher = SkebFetcher(Username(config["skeb"]["twitter_id"]), Password(config["skeb"]["twitter_password"]), base_path)

        # イラスト（複数）
        work_url = "https://skeb.jp/@matsukitchi12/works/25?query=1"
        # 動画（単体）
        # work_url = "https://skeb.jp/@wata_lemon03/works/7"
        # gif画像（複数）
        # work_url = "https://skeb.jp/@_sa_ya_/works/55"

        fetcher.fetch(work_url)
