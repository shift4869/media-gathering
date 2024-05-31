import enum
import re
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path

from media_gathering.link_search.nico_seiga.illust_extension import IllustExtension
from media_gathering.link_search.nico_seiga.nico_seiga_info import NicoSeigaInfo
from media_gathering.link_search.nico_seiga.nico_seiga_save_directory_path import NicoSeigaSaveDirectoryPath
from media_gathering.link_search.nico_seiga.nico_seiga_session import NicoSeigaSession
from media_gathering.link_search.nico_seiga.nico_seiga_url import NicoSeigaURL

logger = getLogger(__name__)
logger.setLevel(INFO)


@dataclass(frozen=True)
class DownloadResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()


@dataclass(frozen=True)
class NicoSeigaDownloader():
    """ニコニコ静画作品をDLするクラス
    """
    nicoseiga_url: NicoSeigaURL  # ニコニコ静画作品ページURL
    base_path: Path              # 保存ディレクトリベースパス
    session: NicoSeigaSession    # 認証済セッション

    def __post_init__(self):
        self._is_valid()

    def _is_valid(self):
        if not isinstance(self.nicoseiga_url, NicoSeigaURL):
            raise TypeError("nicoseiga_url is not NicoSeigaURL.")
        if not isinstance(self.base_path, Path):
            raise TypeError("base_path is not Path.")
        if not isinstance(self.session, NicoSeigaSession):
            raise TypeError("session is not NicoSeigaSession.")
        return True

    def download(self) -> DownloadResult:
        """ニコニコ静画作品ページURLからダウンロードする
        """
        # イラスト情報取得
        illust_id = self.nicoseiga_url.illust_id
        author_id = self.session.get_author_id(illust_id)
        illust_title = self.session.get_illust_title(illust_id)
        author_name = self.session.get_author_name(author_id)

        # イラスト情報をまとめる
        illust_info = NicoSeigaInfo(illust_id, illust_title, author_id, author_name)

        # 画像保存先パスを取得
        save_directory_path = NicoSeigaSaveDirectoryPath.create(illust_info, self.base_path)
        sd_path = save_directory_path.path

        # {作者名}ディレクトリ作成
        sd_path.parent.mkdir(parents=True, exist_ok=True)

        # ファイルが既に存在しているか調べる
        # 拡張子は実際にDLするまで分からない
        # そのため、対象フォルダ内にillust_idを含むファイル名を持つファイルが存在するか調べることで代用する
        name = sd_path.name
        pattern = r"^.*\(" + str(illust_id.id) + r"\).*$"
        same_name_list = [f for f in sd_path.parent.glob("**/*") if re.search(pattern, str(f))]

        # 既に存在しているなら再DLしないでスキップ
        if same_name_list:
            name = same_name_list[0].name
            logger.info("Download nico_seiga illust: " + name + " -> exist")
            return DownloadResult.PASSED

        # 画像直リンクを取得
        source_url = self.session.get_source_url(illust_id)

        # 画像バイナリDL
        content = self.session.get_illust_binary(source_url)

        # 拡張子取得
        ext = IllustExtension.create(content).extension

        # ファイル名設定
        name = f"{sd_path.name}{ext}"

        # {作者名}ディレクトリ直下に保存
        with Path(sd_path.parent / name).open(mode="wb") as fout:
            fout.write(content)
        logger.info("Download seiga illust: " + name + " -> done")

        return DownloadResult.SUCCESS


if __name__ == "__main__":
    import configparser
    import logging.config

    from media_gathering.link_search.nico_seiga.nico_seiga_fetcher import NicoSeigaFetcher
    from media_gathering.link_search.password import Password
    from media_gathering.link_search.username import Username

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./media_gathering/link_search/")
    if config["nico_seiga"].getboolean("is_seiga_trace"):
        fetcher = NicoSeigaFetcher(Username(config["nico_seiga"]["email"]), Password(config["nico_seiga"]["password"]), base_path)
        illust_id = 11308865
        illust_url = f"https://seiga.nicovideo.jp/seiga/im{illust_id}?query=1"
        fetcher.fetch(illust_url)
