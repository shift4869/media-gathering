# coding: utf-8
import enum
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path
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


@dataclass(frozen=True)
class NijieDownloader():
    """nijie作品をDLするクラス
    """
    nijie_url: NijieURL   # nijie作品ページURL
    base_path: Path       # 保存ディレクトリベースパス
    cookies: NijieCookie  # nijieのクッキー

    def __post_init__(self):
        self._is_valid()

    def _is_valid(self):
        if not isinstance(self.nijie_url, NijieURL):
            raise TypeError("nijie_url is not NijieURL.")
        if not isinstance(self.base_path, Path):
            raise TypeError("base_path is not Path.")
        if not isinstance(self.cookies, NijieCookie):
            raise TypeError("cookies is not NijieCookie.")
        return True

    def download(self) -> DownloadResult:
        """nijie作品ページURLから作品をダウンロードしてbase_path以下に保存する
        """
        illust_id = self.nijie_url.work_id.id

        # 作品詳細ページをGET
        illust_url = f"http://nijie.info/view_popup.php?id={illust_id}"
        headers = self.cookies._headers
        cookies = self.cookies._cookies
        res = requests.get(illust_url, headers=headers, cookies=cookies)
        res.raise_for_status()

        # BeautifulSoupを用いてhtml解析を行う
        soup = BeautifulSoup(res.text, "html.parser")
        page_info = NijiePageInfo.create(soup)

        # 保存先ディレクトリを取得
        save_directory_path = NijieSaveDirectoryPath.create(self.nijie_url, page_info, self.base_path)
        sd_path = save_directory_path.path

        urls = page_info.urls
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
                file_name = f"{sd_path.name}_{i:03}{ext}"
                with Path(sd_path / file_name).open(mode="wb") as fout:
                    fout.write(res.content)

                logger.info(f"\t\t: {file_name} -> done({i + 1}/{pages})")
                sleep(0.5)
        elif pages == 1:  # 一枚絵、うごイラ一枚
            # {作者名}ディレクトリ作成
            sd_path.parent.mkdir(parents=True, exist_ok=True)

            # ファイル名設定
            url = urls[0]
            ext = Path(url.original_url).suffix
            name = f"{sd_path.name}{ext}"

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
    import configparser
    from PictureGathering.LinkSearch.Password import Password
    from PictureGathering.LinkSearch.Nijie.NijieFetcher import NijieFetcher
    from PictureGathering.LinkSearch.Username import Username

    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    if config["nijie"].getboolean("is_nijie_trace"):
        fetcher = NijieFetcher(Username(config["nijie"]["email"]), Password(config["nijie"]["password"]), base_path)

        illust_id = 251267  # 一枚絵
        # illust_id = 251197  # 漫画
        # illust_id = 414793  # うごイラ一枚
        # illust_id = 409587  # うごイラ複数

        illust_url = f"https://nijie.info/view_popup.php?id={illust_id}"
        fetcher.fetch(illust_url)
