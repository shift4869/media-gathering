# coding: utf-8
import configparser
from pathlib import Path
import re
from PictureGathering.LinkSearch.Password import Password

from PictureGathering.LinkSearch.PixivFetcher import PixivFetcher
from PictureGathering.LinkSearch.FetcherBase import FetcherBase
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.PixivURL import PixivURL
from PictureGathering.LinkSearch.Username import Username


class LinkSearcher():
    def __init__(self):
        self.fetcher_list: list[FetcherBase] = []

    def register(self, fetcher) -> None:
        interface_check = hasattr(fetcher, "is_target_url") and hasattr(fetcher, "run")
        if not interface_check:
            raise TypeError("Invalid fetcher.")
        self.fetcher_list.append(fetcher)

    def fetch(self, url: str) -> None:
        # CoR
        for p in self.fetcher_list:
            if p.is_target_url(URL(url)):
                p.run(url)
                break
        else:
            raise ValueError("Fetcher not found.")

    def can_fetch(self, url: str) -> bool:
        # CoR
        for p in self.fetcher_list:
            if p.is_target_url(URL(url)):
                return True
        return False

    @classmethod
    def create(self, config: configparser.ConfigParser) -> "LinkSearcher":
        ls = LinkSearcher()

        # pixiv登録
        c = config["pixiv"]
        lsp = PixivFetcher(Username(c["username"]), Password(c["password"]), Path(c["save_base_path"]))
        ls.register(lsp)

        return ls


if __name__ == "__main__":
    import logging.config
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"

    url = "https://www.pixiv.net/artworks/86704541"
    # url = "http://nijie.info/view_popup.php?id=409587"
    # url = "https://www.anyurl/sample/index_{}.html"

    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    if not config.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    lsc = LinkSearcher.create(config)
    print(lsc.can_fetch(url))
    print(lsc.fetch(url))
