# coding: utf-8
import enum
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path
from time import sleep
from typing import ClassVar

import requests

from PictureGathering.LinkSearch.Skeb.SaveFilename import SaveFilename
from PictureGathering.LinkSearch.Skeb.SkebSaveDirectoryPath import SkebSaveDirectoryPath
from PictureGathering.LinkSearch.Skeb.SkebSourceList import SkebSourceList
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL


logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class DownloadResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()
    FAILED = enum.auto()


@dataclass()
class SkebDownloader():
    skeb_url: SkebURL
    source_list: SkebSourceList
    save_directory_path: SkebSaveDirectoryPath
    headers: dict
    dl_file_pathlist: ClassVar[list[Path]]

    def __post_init__(self):
        self._is_valid()
        self.result = DownloadResult.FAILED
        self.dl_file_pathlist = []

    def _is_valid(self):
        if not isinstance(self.skeb_url, SkebURL):
            raise TypeError("skeb_url is not SkebURL.")
        if not isinstance(self.source_list, SkebSourceList):
            raise TypeError("source_list is not SkebSourceList.")
        if not isinstance(self.save_directory_path, SkebSaveDirectoryPath):
            raise TypeError("save_directory_path is not SkebSaveDirectoryPath.")
        if not isinstance(self.headers, dict):
            raise TypeError("headers is not dict.")
        return True

    def download(self) -> DownloadResult:
        self.dl_file_pathlist.clear()

        author_name = self.skeb_url.author_name
        work_id = self.skeb_url.illust_id
        source_list = self.source_list
        sd_path = Path(self.save_directory_path.path)

        work_num = len(source_list)
        if work_num > 1:  # 複数作品
            logger.info(f"Download Skeb work: [{author_name.name}_{work_id.id:03}] -> see below ...")

            # 既に存在しているなら再DLしないでスキップ
            if sd_path.is_dir():
                logger.info("\t\t: exist -> skip")
                return DownloadResult.PASSED

            # {作者名}/{作品名}ディレクトリ作成
            sd_path.mkdir(parents=True, exist_ok=True)

            # 作品をDLする
            # ファイル名は{イラストタイトル}({イラストID})_{3ケタの連番}.{拡張子}
            for i, src in enumerate(source_list):
                url = src.url
                src_ext = src.extension

                file_name = SaveFilename.create(author_name, work_id, i, src_ext).name

                res = requests.get(url.original_url, headers=self.headers)
                res.raise_for_status()

                with Path(sd_path / file_name).open(mode="wb") as fout:
                    fout.write(res.content)

                dst_path = sd_path / file_name
                self.dl_file_pathlist.append(dst_path)
                logger.info("\t\t: " + dst_path.name + " -> done({}/{})".format(i + 1, work_num))
                #     logger.info("\t\t: " + file_name + " -> done({}/{}) , but convert failed".format(i + 1, work_num))
                sleep(0.5)
        elif work_num == 1:  # 単一
            # {作者名}ディレクトリ作成
            sd_path.parent.mkdir(parents=True, exist_ok=True)

            # ファイル名設定
            url = source_list[0].url
            src_ext = source_list[0].extension

            file_name = SaveFilename.create(author_name, work_id, -1, src_ext).name

            # 既に存在しているなら再DLしないでスキップ
            if (sd_path.parent / file_name).is_file():
                logger.info("Download Skeb work: " + file_name + " -> exist")
                return DownloadResult.PASSED

            # DLする
            res = requests.get(url.original_url, headers=self.headers)
            res.raise_for_status()

            # {作者名}ディレクトリ直下に保存
            # file_name = f"{author_name.name}_{work_id.id:03}{src_ext}"
            with Path(sd_path.parent / file_name).open(mode="wb") as fout:
                fout.write(res.content)

            dst_path = sd_path / file_name
            self.dl_file_pathlist.append(dst_path)
            logger.info("Download Skeb work: " + dst_path.name + " -> done")
        else:  # エラー
            raise ValueError("download skeb work failed.")

        return DownloadResult.SUCCESS


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
