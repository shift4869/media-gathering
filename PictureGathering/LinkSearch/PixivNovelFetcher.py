# coding: utf-8
from dataclasses import dataclass
from pathlib import Path

from logging import INFO, getLogger
from pixivpy3 import AppPixivAPI

from PictureGathering.LinkSearch.FetcherBase import FetcherBase
from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.PixivNovelDownloader import PixivNovelDownloader
from PictureGathering.LinkSearch.PixivNovelSaveDirectoryPath import PixivNovelSaveDirectoryPath
from PictureGathering.LinkSearch.PixivNovelURL import PixivNovelURL
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username

logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class PixivNovelFetcher(FetcherBase):
    aapi: AppPixivAPI
    base_path = Path

    def __init__(self, username: Username, password: Password, base_path: Path):
        super().__init__()

        if not isinstance(username, Username):
            raise TypeError("username is not Username.")
        if not isinstance(password, Password):
            raise TypeError("password is not Password.")
        if not isinstance(base_path, Path):
            raise TypeError("base_path is not Path.")

        object.__setattr__(self, "aapi", self.login(username, password))
        object.__setattr__(self, "base_path", base_path)

    def login(self, username: Username, password: Password) -> AppPixivAPI:
        aapi = AppPixivAPI()

        # 前回ログインからのrefresh_tokenが残っているか調べる
        REFRESH_TOKEN_PATH = "./config/refresh_token.ini"
        rt_path = Path(REFRESH_TOKEN_PATH)
        if rt_path.is_file():
            refresh_token = ""
            with rt_path.open(mode="r") as fin:
                refresh_token = str(fin.read())
            try:
                '''
                # 2021/10/14 python 3.10にてOpenSSL 1.1.1以降が必須になった影響？のためこの回避は使えなくなった
                # また、PixivPy側でデフォルトのユーザーエージェントが修正されたためreCAPTCHAも気にしなくて良くなった
                # 2021/06/15 reCAPTCHAを回避する
                # https://github.com/upbit/pixivpy/issues/171#issuecomment-860264788
                class CustomAdapter(requests.adapters.HTTPAdapter):
                    def init_poolmanager(self, *args, **kwargs):
                        # When urllib3 hand-rolls a SSLContext, it sets 'options |= OP_NO_TICKET'
                        # and CloudFlare really does not like this. We cannot control this behavior
                        # in urllib3, but we can just pass our own standard context instead.
                        import ssl
                        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                        ctx.load_default_certs()
                        ctx.set_alpn_protocols(["http/1.1"])
                        return super().init_poolmanager(*args, **kwargs, ssl_context=ctx)

                aapi.requests = requests.Session()
                aapi.requests.mount("https://", CustomAdapter())
                '''
                aapi.auth(refresh_token=refresh_token)

                if aapi.access_token is not None:
                    return aapi
            except Exception:
                pass

        # refresh_tokenが存在していない場合、または有効なトークンではなかった場合
        # api.login(username, password)
        # aapi.login(username, password)
        # auth_success = (api.access_token is not None) and (aapi.access_token is not None)
        # 2021/05/20 現在PixivPyで新規ログインができない
        # https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362
        # https://gist.github.com/upbit/6edda27cb1644e94183291109b8a5fde
        logger.info(f"not found {REFRESH_TOKEN_PATH}")
        logger.info("please access to make refresh_token.ini for below way:")
        logger.info("https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362")
        logger.info(" or ")
        logger.info("https://gist.github.com/upbit/6edda27cb1644e94183291109b8a5fde")
        logger.info("process abort")
        raise ValueError("pixiv auth failed.")

        # refresh_tokenを保存
        refresh_token = api.refresh_token
        with rt_path.open(mode="w") as fout:
            fout.write(refresh_token)

        raise ValueError("pixiv auth failed.")

    def is_target_url(self, url: URL) -> bool:
        return PixivNovelURL.is_valid(url.original_url)

    def run(self, url: URL) -> None:
        novel_url = PixivNovelURL.create(url)
        save_directory_path = PixivNovelSaveDirectoryPath.create(self.aapi, novel_url, self.base_path)

        result = PixivNovelDownloader(self.aapi, novel_url, save_directory_path).result


if __name__ == "__main__":
    import configparser
    import logging.config
    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    if config["pixiv"].getboolean("is_pixiv_trace"):
        pa_cont = PixivFetcher(Username(config["pixiv"]["username"]), Password(config["pixiv"]["password"]), base_path)
        work_url = "https://www.pixiv.net/artworks/86704541"
        pa_cont.run(work_url)
