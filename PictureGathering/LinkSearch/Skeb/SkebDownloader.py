# coding: utf-8
import enum
from dataclasses import dataclass
from logging import INFO, getLogger
from msilib.schema import Extension
from pathlib import Path
from time import sleep
from typing import ClassVar

import requests

from PictureGathering.LinkSearch.Skeb.SaveFilename import SaveFilename, Extension
from PictureGathering.LinkSearch.Skeb.SkebSaveDirectoryPath import SkebSaveDirectoryPath
from PictureGathering.LinkSearch.Skeb.SkebSourceList import SkebSourceList
from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL
from PictureGathering.LinkSearch.URL import URL


logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class DownloadResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()


@dataclass()
class SkebDownloader():
    """skeb作品をDLするクラス
    """
    skeb_url: SkebURL                           # skeb作品ページURL
    source_list: SkebSourceList                 # 直リンク情報リスト
    save_directory_path: SkebSaveDirectoryPath  # 保存先ディレクトリパス
    headers: dict                               # 接続時ヘッダー
    dl_file_pathlist: ClassVar[list[Path]]      # DL完了したファイルのパス

    def __post_init__(self) -> None:
        self._is_valid()
        self.dl_file_pathlist = []

    def _is_valid(self) -> bool:
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
        """skeb作品をダウンロードしてsave_directory_pathに保存する
        """
        # 結果のパスリストをクリア
        self.dl_file_pathlist.clear()

        author_name = self.skeb_url.author_name
        work_id = self.skeb_url.work_id
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
            for i, src in enumerate(source_list):
                url: URL = src.url
                src_ext: Extension = src.extension

                # ファイル名は{イラストタイトル}_{イラストID}_{3ケタの連番}.{拡張子}
                file_name = SaveFilename.create(author_name, work_id, i, src_ext).name

                res = requests.get(url.original_url, headers=self.headers)
                res.raise_for_status()

                with Path(sd_path / file_name).open(mode="wb") as fout:
                    fout.write(res.content)

                dst_path = sd_path / file_name
                self.dl_file_pathlist.append(dst_path)
                logger.info("\t\t: " + dst_path.name + " -> done({}/{})".format(i + 1, work_num))
                sleep(0.5)
        elif work_num == 1:  # 単一
            # {作者名}ディレクトリ作成
            sd_path.parent.mkdir(parents=True, exist_ok=True)

            # ファイル名設定
            url: URL = source_list[0].url
            src_ext: Extension = source_list[0].extension

            # ファイル名は{イラストタイトル}_{イラストID}.{拡張子}
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

            dst_path = sd_path.parent / file_name
            self.dl_file_pathlist.append(dst_path)
            logger.info("Download Skeb work: " + dst_path.name + " -> done")
        else:  # エラー
            raise ValueError("download skeb work failed.")

        return DownloadResult.SUCCESS


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
