import enum
import re
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path
from time import sleep

from pixivpy3 import AppPixivAPI

from media_gathering.link_search.pixiv.pixiv_save_directory_path import PixivSaveDirectoryPath
from media_gathering.link_search.pixiv.pixiv_source_list import PixivSourceList
from media_gathering.link_search.pixiv.pixiv_ugoira_downloader import PixivUgoiraDownloader
from media_gathering.link_search.pixiv.workid import Workid

logger = getLogger(__name__)
logger.setLevel(INFO)


@dataclass(frozen=True)
class DownloadResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()


@dataclass(frozen=True)
class PixivWorkDownloader():
    """pixiv作品をDLするクラス
    """
    aapi: AppPixivAPI                            # 非公式pixivAPI操作インスタンス
    source_list: PixivSourceList                 # 直リンクURLリスト
    save_directory_path: PixivSaveDirectoryPath  # 保存先ディレクトリパス

    def __post_init__(self) -> None:
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self.aapi, AppPixivAPI):
            raise TypeError("aapi is not AppPixivAPI.")
        if not isinstance(self.source_list, PixivSourceList):
            raise TypeError("source_list is not PixivSourceList.")
        if not isinstance(self.save_directory_path, PixivSaveDirectoryPath):
            raise TypeError("save_directory_path is not PixivSaveDirectoryPath.")
        return True

    def download(self) -> DownloadResult:
        """pixiv作品ページURLからダウンロードする

        リファラの関係で直接requestできないためAPIを通して保存する
        save_directory_pathは
        {base_path}/{作者名}({作者pixivID})/{作品タイトル}({作品ID})/の形を想定している
        漫画形式の場合：
            save_directory_pathを使用し
            /{作者名}({作者pixivID})/{作品タイトル}({作品ID})/{作品タイトル}({作品ID})_{3ケタの連番}.{拡張子}の形式で保存
        一枚絵の場合：
            save_directory_pathから作品タイトルと作品IDを取得し
            /{作者名}({作者pixivID})/{作品タイトル}({作品ID}).{拡張子}の形式で保存
        うごイラの場合：
            save_directory_pathから作品タイトルと作品IDを取得し
            /{作者名}({作者pixivID})/{作品タイトル}({作品ID}).{拡張子}の形式で扉絵（1枚目）を保存
            /{作者名}({作者pixivID})/{作品タイトル}({作品ID})/{作品ID}_ugoira{*}.{拡張子}の形式で各フレームを保存
            /{作者名}({作者pixivID})/{作品タイトル}({作品ID}).gifとしてアニメーションgifを保存
        """
        pages = len(self.source_list)
        sd_path = self.save_directory_path.path
        if pages > 1:  # 漫画形式
            author_name_id = sd_path.parent.name
            work_name_id = sd_path.name
            logger.info(f"Download pixiv works: [{author_name_id} / {work_name_id}] -> see below ...")

            # 既に存在しているなら再DLしないでスキップ
            if sd_path.is_dir():
                logger.info("\t\t: exist -> skip")
                return DownloadResult.PASSED

            sd_path.mkdir(parents=True, exist_ok=True)
            for i, url in enumerate(self.source_list):
                ext = Path(url.non_query_url).suffix
                name = "{}_{:03}{}".format(sd_path.name, i + 1, ext)
                self.aapi.download(url.non_query_url, path=str(sd_path), name=name)
                logger.info(f"\t\t: {name} -> done({i + 1}/{pages})")
                sleep(0.5)
        elif pages == 1:  # 一枚絵
            sd_path.parent.mkdir(parents=True, exist_ok=True)

            url = self.source_list[0].non_query_url
            ext = Path(url).suffix
            name = f"{sd_path.name}{ext}"
            author_name_id = sd_path.parent.name

            # 既に存在しているなら再DLしないでスキップ
            if (sd_path.parent / name).is_file():
                logger.info(f"Download pixiv work: {author_name_id} / {name} -> exist")
                return DownloadResult.PASSED

            self.aapi.download(url, path=str(sd_path.parent), name=name)
            logger.info(f"Download pixiv work: {author_name_id} / {name} -> done")

            # うごイラの場合は追加で保存する
            regex = re.compile(r'.*\(([0-9]*)\)$')
            result = regex.match(sd_path.name)
            if result:
                work_id = Workid(int(result.group(1)))
                PixivUgoiraDownloader(self.aapi, work_id, sd_path.parent).download()
        else:  # エラー
            raise ValueError("download pixiv work failed.")
        return DownloadResult.SUCCESS


if __name__ == "__main__":
    import configparser
    import logging.config

    from media_gathering.link_search.password import Password
    from media_gathering.link_search.pixiv.pixiv_fetcher import PixivFetcher
    from media_gathering.link_search.username import Username

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./media_gathering/link_search/")
    if config["pixiv"].getboolean("is_pixiv_trace"):
        fetcher = PixivFetcher(Username(config["pixiv"]["username"]), Password(config["pixiv"]["password"]), base_path)
        # 一枚絵（単一）
        # work_url = "https://www.pixiv.net/artworks/98804653"
        # 漫画（複数）
        # work_url = "https://www.pixiv.net/artworks/98789839"
        # うごイラ（単一）
        work_url = "https://www.pixiv.net/artworks/86704541"
        fetcher.fetch(work_url)
