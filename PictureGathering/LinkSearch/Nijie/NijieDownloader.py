# coding: utf-8
import enum
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path
from typing import ClassVar
from time import sleep

from bs4 import BeautifulSoup
import requests
from PictureGathering.LinkSearch.Nijie.NijieCookie import NijieCookie
from PictureGathering.LinkSearch.Nijie.NijiePageInfo import NijiePageInfo
from PictureGathering.LinkSearch.Nijie.NijieSaveDirectoryPath import NijieSaveDirectoryPath

from PictureGathering.LinkSearch.Nijie.NijieURL import NijieURL


logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class DownloadResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()
    FAILED = enum.auto()


@dataclass(frozen=True)
class NijieDownloader():
    nijie_url: NijieURL
    base_path: Path
    cookies: NijieCookie
    result: ClassVar[DownloadResult]

    def __post_init__(self):
        self._is_valid()
        object.__setattr__(self, "result", self.download_illusts())

    def _is_valid(self):
        if not isinstance(self.nijie_url, NijieURL):
            raise TypeError("nijie_url is not NijieURL.")
        if not isinstance(self.base_path, Path):
            raise TypeError("base_path is not Path.")
        if not isinstance(self.cookies, NijieCookie):
            raise TypeError("cookies is not NijieCookie.")
        return True

    def download_illusts(self) -> DownloadResult:
        illust_id = self.nijie_url.illust_id

        # 作品詳細ページをGET
        illust_url = f"http://nijie.info/view_popup.php?id={illust_id}"
        headers = self.cookies._headers
        cookies = self.cookies._cookies
        res = requests.get(illust_url, headers=headers, cookies=cookies)
        res.raise_for_status()

        # BeautifulSoupを用いてhtml解析を行う
        soup = BeautifulSoup(res.text, "html.parser")
        illust_info = NijiePageInfo.create(soup)

        # 保存先ディレクトリを取得
        save_directory_path = NijieSaveDirectoryPath.create(self.nijie_url, self.base_path, illust_info)
        sd_path = save_directory_path.path

        urls = illust_info.urls
        pages = len(urls)
        if pages > 1:  # 漫画形式、うごイラ複数
            dirname = sd_path.parent.name
            logger.info("Download nijie illust: [" + dirname + "] -> see below ...")

            # 既に存在しているなら再DLしないでスキップ
            if sd_path.is_dir():
                logger.info("\t\t: exist -> skip")
                return DownloadResult.PASSED

            # {作者名}/{作品名}ディレクトリ作成
            sd_path.mkdir(parents=True, exist_ok=True)

            # 画像をDLする
            # ファイル名は{イラストタイトル}({イラストID})_{3ケタの連番}.{拡張子}
            for i, url in enumerate(urls):
                res = requests.get(url.original_url, headers=headers, cookies=cookies)
                res.raise_for_status()

                ext = Path(url.original_url).suffix
                file_name = "{}_{:03}{}".format(sd_path.name, i, ext)
                with Path(sd_path / file_name).open(mode="wb") as fout:
                    fout.write(res.content)

                logger.info("\t\t: " + file_name + " -> done({}/{})".format(i + 1, pages))
                sleep(0.5)
        elif pages == 1:  # 一枚絵、うごイラ一枚
            # {作者名}ディレクトリ作成
            sd_path.parent.mkdir(parents=True, exist_ok=True)

            # ファイル名設定
            url = urls[0]
            ext = Path(url.original_url).suffix
            name = "{}{}".format(sd_path.name, ext)

            # 既に存在しているなら再DLしないでスキップ
            if (sd_path.parent / name).is_file():
                logger.info("Download nijie illust: " + name + " -> exist")
                return DownloadResult.PASSED

            # 画像をDLする
            res = requests.get(url.original_url, headers=headers, cookies=cookies)
            res.raise_for_status()

            # {作者名}ディレクトリ直下に保存
            with Path(sd_path.parent / name).open(mode="wb") as fout:
                fout.write(res.content)
            logger.info("Download nijie illust: " + name + " -> done")
        else:  # エラー
            raise ValueError("download nijie illust failed.")

        return DownloadResult.SUCCESS


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = NijieSaveDirectoryPath.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
