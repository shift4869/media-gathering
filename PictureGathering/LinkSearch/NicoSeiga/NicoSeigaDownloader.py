# coding: utf-8
import enum
import re
from dataclasses import dataclass
from logging import INFO, getLogger
from pathlib import Path
from typing import ClassVar

from PictureGathering.LinkSearch.NicoSeiga.IllustExtension import IllustExtension
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaInfo import NicoSeigaInfo
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSaveDirectoryPath import NicoSeigaSaveDirectoryPath
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaSession import NicoSeigaSession
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaURL import NicoSeigaURL


logger = getLogger("root")
logger.setLevel(INFO)


@dataclass(frozen=True)
class DownloadResult(enum.Enum):
    SUCCESS = enum.auto()
    PASSED = enum.auto()
    FAILED = enum.auto()


@dataclass(frozen=True)
class NicoSeigaDownloader():
    nicoseiga_url: NicoSeigaURL
    base_path: Path
    session: NicoSeigaSession
    result: ClassVar[DownloadResult]

    def __post_init__(self):
        self._is_valid()
        object.__setattr__(self, "result", self.download_illusts())

    def _is_valid(self):
        if not isinstance(self.nicoseiga_url, NicoSeigaURL):
            raise TypeError("nicoseiga_url is not NicoSeigaURL.")
        if not isinstance(self.base_path, Path):
            raise TypeError("base_path is not Path.")
        if not isinstance(self.session, NicoSeigaSession):
            raise TypeError("session is not NicoSeigaSession.")
        return True

    def download_illusts(self) -> DownloadResult:
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
        pattern = "^.*\(" + str(illust_id.id) + "\).*$"
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
        name = "{}{}".format(sd_path.name, ext)

        # {作者名}ディレクトリ直下に保存
        with Path(sd_path.parent / name).open(mode="wb") as fout:
            fout.write(content)
        logger.info("Download seiga illust: " + name + " -> done")

        return DownloadResult.SUCCESS


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = NicoSeigaSaveDirectoryPath.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
