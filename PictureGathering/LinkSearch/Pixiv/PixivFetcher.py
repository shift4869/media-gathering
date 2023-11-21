from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path

from pixivpy3 import AppPixivAPI

from PictureGathering.LinkSearch.FetcherBase import FetcherBase
from PictureGathering.LinkSearch.Password import Password
from PictureGathering.LinkSearch.Pixiv.PixivSaveDirectoryPath import PixivSaveDirectoryPath
from PictureGathering.LinkSearch.Pixiv.PixivSourceList import PixivSourceList
from PictureGathering.LinkSearch.Pixiv.PixivWorkDownloader import PixivWorkDownloader
from PictureGathering.LinkSearch.Pixiv.PixivWorkURL import PixivWorkURL
from PictureGathering.LinkSearch.URL import URL
from PictureGathering.LinkSearch.Username import Username

logger = getLogger(__name__)
logger.setLevel(INFO)


@dataclass(frozen=True)
class PixivFetcher(FetcherBase):
    """pixiv作品を取得するクラス
    """
    aapi: AppPixivAPI  # 非公式pixivAPI操作インスタンス
    base_path: Path    # 保存ディレクトリベースパス

    # refresh_tokenファイルパス
    REFRESH_TOKEN_PATH = "./config/refresh_token.ini"

    def __init__(self, username: Username, password: Password, base_path: Path) -> None:
        """初期化処理

        バリデーションと非公式pixivAPIインスタンス取得

        Args:
            username (Username): pixivログイン用ユーザーID
            password (Password):  pixivログイン用パスワード
            base_path (Path): 保存ディレクトリベースパス
        """
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
        """pixivログインして非公式pixivAPIインスタンスを取得する

        Args:
            username (Username): pixivログイン用ユーザーID
            password (Password):  pixivログイン用パスワード

        Returns:
            aapi: AppPixivAPI非公式pixivAPI操作インスタンス
        """
        aapi = AppPixivAPI()

        # 前回ログインからのrefresh_tokenが残っているか調べる
        rt_path = Path(self.REFRESH_TOKEN_PATH)
        if rt_path.is_file():
            refresh_token = ""
            with rt_path.open(mode="r") as fin:
                refresh_token = str(fin.read())
            try:
                # 非公式pixivAPI認証
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
        logger.error(f"not found {self.REFRESH_TOKEN_PATH}")
        logger.error("please access to make refresh_token.ini for below way:")
        logger.error("https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362")
        logger.error(" or ")
        logger.error("https://gist.github.com/upbit/6edda27cb1644e94183291109b8a5fde")
        logger.error("process abort")
        raise ValueError("pixiv auth failed.")

    def is_target_url(self, url: URL) -> bool:
        """担当URLかどうか判定する

        FetcherBaseオーバーライド

        Args:
            url (URL): 処理対象url

        Returns:
            bool: 担当urlだった場合True, そうでない場合False
        """
        return PixivWorkURL.is_valid(url.non_query_url)

    def fetch(self, url: URL) -> None:
        """担当処理：pixiv作品を取得する

        FetcherBaseオーバーライド

        Args:
            url (URL): 処理対象url
        """
        pixiv_url = PixivWorkURL.create(url)
        source_list = PixivSourceList.create(self.aapi, pixiv_url)
        save_directory_path = PixivSaveDirectoryPath.create(self.aapi, pixiv_url, self.base_path)
        PixivWorkDownloader(self.aapi, source_list, save_directory_path).download()


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
        pa_cont.fetch(work_url)
