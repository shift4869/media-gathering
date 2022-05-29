# coding: utf-8
import enum
from dataclasses import dataclass
from logging import INFO, getLogger
from typing import ClassVar

from bs4 import BeautifulSoup
from pixivpy3 import AppPixivAPI

from PictureGathering.LinkSearch.PixivNovel.PixivNovelSaveDirectoryPath import PixivNovelSaveDirectoryPath
from PictureGathering.LinkSearch.PixivNovel.PixivNovelURL import PixivNovelURL
from PictureGathering.LinkSearch.Pixiv.PixivSaveDirectoryPath import PixivSaveDirectoryPath

logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class DownloadResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()
    FAILED = enum.auto()


@dataclass(frozen=True)
class PixivNovelDownloader():
    aapi: AppPixivAPI
    novel_url: PixivNovelURL
    save_directory_path: PixivNovelSaveDirectoryPath
    result: ClassVar[DownloadResult]

    def __post_init__(self):
        self._is_valid()
        object.__setattr__(self, "result", self.download_illusts())

    def _is_valid(self):
        if not isinstance(self.aapi, AppPixivAPI):
            raise TypeError("aapi is not AppPixivAPI.")
        if not isinstance(self.novel_url, PixivNovelURL):
            raise TypeError("urls is not PixivNovelURL.")
        if not isinstance(self.save_directory_path, PixivNovelSaveDirectoryPath):
            raise TypeError("save_directory_path is not PixivNovelSaveDirectoryPath.")
        return True

    def download_illusts(self) -> DownloadResult:
        """pixiv作品ページURLからノベル作品をダウンロードする

        Notes:
            非公式pixivAPIを通して保存する
            save_directory_pathは
            {base_path}/{作者名}({作者pixivID})/{ノベルタイトル}({ノベルID})/の形を想定している
            save_directory_pathからノベルタイトルとノベルIDを取得し
            {base_path}/{作者名}({作者pixivID})/{ノベルタイトル}({ノベルID}).{拡張子}の形式で保存
            ノベルテキスト全文はurlからノベルIDを取得し、非公式pixivAPIを利用して取得する

        Args:
            url (str): pixiv作品ページURL
            save_directory_path (str): 保存先フルパス

        Returns:
            int: DL成功時0、スキップされた場合1、エラー時-1
        """
        # ノベルID取得
        url = self.novel_url.original_url
        novel_id = self.novel_url.novel_id

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
        name = "{}{}".format(sd_path.name, ext)

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
