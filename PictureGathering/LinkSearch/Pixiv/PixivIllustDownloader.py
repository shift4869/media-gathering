# coding: utf-8
import enum
import re
from pathlib import Path
from dataclasses import dataclass
from logging import INFO, getLogger
from time import sleep
from typing import ClassVar

from pixivpy3 import AppPixivAPI

from PictureGathering.LinkSearch.Pixiv.PixivIllustURLList import PixivIllustURLList
from PictureGathering.LinkSearch.Pixiv.PixivSaveDirectoryPath import PixivSaveDirectoryPath
from PictureGathering.LinkSearch.Pixiv.PixivUgoiraDownloader import PixivUgoiraDownloader

logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class DownloadResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()
    FAILED = enum.auto()


@dataclass(frozen=True)
class PixivIllustDownloader():
    aapi: AppPixivAPI
    urls: PixivIllustURLList
    save_directory_path: PixivSaveDirectoryPath
    result: ClassVar[DownloadResult]

    def __post_init__(self):
        self._is_valid()
        object.__setattr__(self, "result", self.download_illusts())

    def _is_valid(self):
        if not isinstance(self.aapi, AppPixivAPI):
            raise TypeError("aapi is not AppPixivAPI.")
        if not isinstance(self.urls, PixivIllustURLList):
            raise TypeError("urls is not PixivIllustURLList.")
        if not isinstance(self.save_directory_path, PixivSaveDirectoryPath):
            raise TypeError("save_directory_path is not PixivSaveDirectoryPath.")
        return True

    def download_illusts(self) -> DownloadResult:
        """pixiv作品ページURLからダウンロードする

        リファラの関係？で直接requestできないためAPIを通して保存する
        save_directory_pathは
        {base_path}/{作者名}({作者pixivID})/{イラストタイトル}({イラストID})/の形を想定している
        漫画形式の場合：
            save_directory_pathを使用し
            /{作者名}({作者pixivID})/{イラストタイトル}({イラストID})/{イラストタイトル}({イラストID})_{3ケタの連番}.{拡張子}の形式で保存
        イラスト一枚絵の場合：
            save_directory_pathからイラストタイトルとイラストIDを取得し
            /{作者名}({作者pixivID})/{イラストタイトル}({イラストID}).{拡張子}の形式で保存
        うごイラの場合：
            save_directory_pathからイラストタイトルとイラストIDを取得し
            /{作者名}({作者pixivID})/{イラストタイトル}({イラストID}).{拡張子}の形式で扉絵（1枚目）を保存
            /{作者名}({作者pixivID})/{イラストタイトル}({イラストID})/{イラストID}_ugoira{*}.{拡張子}の形式で各フレームを保存
            /{作者名}({作者pixivID})/{イラストタイトル}({イラストID}).gifとしてアニメーションgifを保存

        """
        pages = len(self.urls)
        sd_path = self.save_directory_path.path
        if pages > 1:  # 漫画形式
            dirname = sd_path.parent.name
            logger.info("Download pixiv illust: [" + dirname + "] -> see below ...")

            # 既に存在しているなら再DLしないでスキップ
            if sd_path.is_dir():
                logger.info("\t\t: exist -> skip")
                return DownloadResult.PASSED

            sd_path.mkdir(parents=True, exist_ok=True)
            for i, url in enumerate(self.urls):
                ext = Path(url.non_query_url).suffix
                name = "{}_{:03}{}".format(sd_path.name, i + 1, ext)
                self.aapi.download(url.non_query_url, path=str(sd_path), name=name)
                logger.info("\t\t: " + name + " -> done({}/{})".format(i + 1, pages))
                sleep(0.5)
        elif pages == 1:  # 一枚絵
            sd_path.parent.mkdir(parents=True, exist_ok=True)

            url = self.urls[0].non_query_url
            ext = Path(url).suffix
            name = "{}{}".format(sd_path.name, ext)
            
            # 既に存在しているなら再DLしないでスキップ
            if (sd_path.parent / name).is_file():
                logger.info("Download pixiv illust: " + name + " -> exist")
                return DownloadResult.PASSED

            self.aapi.download(url, path=str(sd_path.parent), name=name)
            logger.info("Download pixiv illust: " + name + " -> done")

            # うごイラの場合は追加で保存する
            regex = re.compile(r'.*\(([0-9]*)\)$')
            result = regex.match(sd_path.name)
            if result:
                illust_id = int(result.group(1))
                res = PixivUgoiraDownloader(self.aapi, illust_id, sd_path.parent).result
        else:  # エラー
            raise ValueError("download pixiv illust failed.")
        return DownloadResult.SUCCESS


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = PixivSaveDirectoryPath.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
