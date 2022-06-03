# coding: utf-8
import enum
from dataclasses import dataclass
from logging import INFO, getLogger

from bs4 import BeautifulSoup
from pixivpy3 import AppPixivAPI

from PictureGathering.LinkSearch.PixivNovel.PixivNovelSaveDirectoryPath import PixivNovelSaveDirectoryPath
from PictureGathering.LinkSearch.PixivNovel.PixivNovelURL import PixivNovelURL

logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class DownloadResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()


@dataclass(frozen=True)
class PixivNovelDownloader():
    """pixiv小説作品をDLするクラス
    """
    aapi: AppPixivAPI                                 # 非公式pixivAPI操作インスタンス
    novel_url: PixivNovelURL                          # ノベルURL
    save_directory_path: PixivNovelSaveDirectoryPath  # 保存ディレクトリベースパス

    def __post_init__(self) -> None:
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self.aapi, AppPixivAPI):
            raise TypeError("aapi is not AppPixivAPI.")
        if not isinstance(self.novel_url, PixivNovelURL):
            raise TypeError("urls is not PixivNovelURL.")
        if not isinstance(self.save_directory_path, PixivNovelSaveDirectoryPath):
            raise TypeError("save_directory_path is not PixivNovelSaveDirectoryPath.")
        return True

    def download(self) -> DownloadResult:
        """ノベルURLから作品をダウンロードする

        非公式pixivAPIを通して保存する
        save_directory_pathは
        {base_path}/{作者名}({作者pixivID})/{ノベルタイトル}({ノベルID})/の形を想定している
        作品は
        {base_path}/{作者名}({作者pixivID})/{ノベルタイトル}({ノベルID}).{拡張子}の形式で保存

        Args:
            url (str): pixiv作品ページURL
            save_directory_path (str): 保存先フルパス

        Returns:
            DownloadResult: DL成功時SUCCESS, スキップされた場合PASSED
        """
        # ノベルID取得
        url = self.novel_url.original_url
        novel_id = self.novel_url.novel_id.id

        # ノベル詳細取得
        works = self.aapi.novel_detail(novel_id)
        if works.error or (works.novel is None):
            raise ValueError("Download pixiv novel: " + url + " -> failed")
        work = works.novel

        # ノベルテキスト取得
        work_text = self.aapi.novel_text(novel_id)
        if work_text.error or (work_text.novel_text is None):
            raise ValueError("Download pixiv novel: " + url + " -> failed")

        # 保存場所親ディレクトリ作成
        sd_path = self.save_directory_path.path
        sd_path.parent.mkdir(parents=True, exist_ok=True)

        # ファイル名取得
        ext = ".txt"
        name = f"{sd_path.name}{ext}"

        # 既に存在しているなら再DLしないでスキップ
        if (sd_path.parent / name).is_file():
            logger.info("Download pixiv novel: " + name + " -> exist")
            return DownloadResult.PASSED

        # ノベル詳細から作者・キャプション等付与情報を取得する
        info_tag = f"[info]\n" \
                   f"author:{work.user.name}({work.user.id})\n" \
                   f"id:{work.id}\n" \
                   f"title:{work.title}\n" \
                   f"create_date:{work.create_date}\n" \
                   f"page_count:{work.page_count}\n" \
                   f"text_length:{work.text_length}\n"
        soup = BeautifulSoup(work.caption, "html.parser")
        caption = f"[caption]\n" \
                  f"{soup.prettify()}\n"

        # ノベルテキストの全文を保存する
        # 改ページは"[newpage]"の内部タグで表現される
        # self.aapi.download(url, path=str(sd_path.parent), name=name)
        with (sd_path.parent / name).open("w", encoding="utf-8") as fout:
            fout.write(info_tag + "\n")
            fout.write(caption + "\n")
            fout.write("[text]\n" + work_text.novel_text + "\n")

        logger.info("Download pixiv novel: " + name + " -> done")
        return DownloadResult.SUCCESS


if __name__ == "__main__":
    import configparser
    import logging.config
    from pathlib import Path
    from PictureGathering.LinkSearch.PixivNovel.PixivNovelFetcher import PixivNovelFetcher
    from PictureGathering.LinkSearch.Username import Username
    from PictureGathering.LinkSearch.Password import Password

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    if config["pixiv"].getboolean("is_pixiv_trace"):
        fetcher = PixivNovelFetcher(Username(config["pixiv"]["username"]), Password(config["pixiv"]["password"]), base_path)
        work_url = "https://www.pixiv.net/novel/show.php?id=3195243&query=1"
        fetcher.fetch(work_url)
