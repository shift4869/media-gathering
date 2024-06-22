import configparser
from logging import INFO, getLogger
from pathlib import Path
from typing import Self

from plyer import notification

from media_gathering.link_search.fetcher_base import FetcherBase
from media_gathering.link_search.nico_seiga.nico_seiga_fetcher import NicoSeigaFetcher
from media_gathering.link_search.nijie.nijie_fetcher import NijieFetcher
from media_gathering.link_search.password import Password
from media_gathering.link_search.pixiv.pixiv_fetcher import PixivFetcher
from media_gathering.link_search.pixiv_novel.pixiv_novel_fetcher import PixivNovelFetcher
from media_gathering.link_search.url import URL
from media_gathering.link_search.username import Username
from media_gathering.log_message import MSG

logger = getLogger(__name__)
logger.setLevel(INFO)


class LinkSearcher:
    def __init__(self):
        self.fetcher_list: list[FetcherBase] = []

    def register(self, fetcher) -> None:
        interface_check = hasattr(fetcher, "is_target_url") and hasattr(fetcher, "fetch")
        if not interface_check:
            raise TypeError("Invalid fetcher.")
        self.fetcher_list.append(fetcher)
        fetcher_class = fetcher.__class__.__name__
        logger.info(MSG.LINKSEARCHER_REGISTERED.value.format(fetcher_class))

    def fetch(self, url: str) -> None:
        # CoR
        for p in self.fetcher_list:
            if p.is_target_url(URL(url)):
                fetcher_class = p.__class__.__name__
                logger.info(MSG.LINKSEARCHER_FETCHER_FOUND.value.format(url, fetcher_class))
                p.fetch(url)
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
    def create(self, config_dict: dict) -> Self:
        logger.info(MSG.LINKSEARCHER_CREATE_START.value)
        ls = LinkSearcher()

        config = config_dict

        # 登録失敗時の通知用
        # 登録に失敗しても処理は続ける
        def notify(fetcher_kind: str):
            notification.notify(
                title="Media Gathering 実行エラー",
                message=f"LinkSearcher: {fetcher_kind} register failed.",
                app_name="Media Gathering",
                timeout=10,
            )

        # pixiv登録
        try:
            c = config["pixiv"]
            if c["is_pixiv_trace"]:
                fetcher = PixivFetcher(Username(c["username"]), Password(c["password"]), Path(c["save_base_path"]))
                ls.register(fetcher)
        except Exception:
            notify("pixiv")

        # pixivノベル登録
        try:
            c = config["pixiv"]
            if c["is_pixiv_trace"]:
                fetcher = PixivNovelFetcher(
                    Username(c["username"]), Password(c["password"]), Path(c["save_base_path"])
                )
                ls.register(fetcher)
        except Exception:
            notify("pixiv novel")

        # nijie登録
        try:
            c = config["nijie"]
            if c["is_nijie_trace"]:
                fetcher = NijieFetcher(Username(c["email"]), Password(c["password"]), Path(c["save_base_path"]))
                ls.register(fetcher)
        except Exception:
            notify("nijie")

        # ニコニコ静画登録
        try:
            c = config["nico_seiga"]
            if c["is_seiga_trace"]:
                fetcher = NicoSeigaFetcher(Username(c["email"]), Password(c["password"]), Path(c["save_base_path"]))
                ls.register(fetcher)
        except Exception:
            notify("niconico seiga")

        # # skeb登録
        # try:
        #     c = config["skeb"]
        #     if c["is_skeb_trace"]:
        #         fetcher = SkebFetcher(
        #             Username(c["twitter_id"]), Password(c["twitter_password"]), Path(c["save_base_path"])
        #         )
        #         ls.register(fetcher)
        # except Exception:
        #     notify("skeb")

        logger.info(MSG.LINKSEARCHER_CREATE_DONE.value)
        return ls


if __name__ == "__main__":
    import logging.config

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)

    # url = "https://www.pixiv.net/artworks/86704541"
    # url = "https://www.pixiv.net/novel/show.php?id=17668373"
    # url = "http://nijie.info/view_popup.php?id=251267"
    url = "https://seiga.nicovideo.jp/seiga/im11308865?query=1"
    # url = "https://skeb.jp/@matsukitchi12/works/25?query=1"
    # url = "https://www.anyurl/sample/index_{}.html"

    CONFIG_FILE_NAME = "./config/config.json"
    config = configparser.ConfigParser()
    if not config.read(CONFIG_FILE_NAME, encoding="utf8"):
        raise IOError

    lsc = LinkSearcher.create(config)
    print(lsc.can_fetch(url))
    print(lsc.fetch(url))
