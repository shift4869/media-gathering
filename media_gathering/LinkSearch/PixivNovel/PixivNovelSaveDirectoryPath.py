import re
from dataclasses import dataclass
from pathlib import Path

from pixivpy3 import AppPixivAPI

from media_gathering.LinkSearch.PixivNovel.Authorid import Authorid
from media_gathering.LinkSearch.PixivNovel.Authorname import Authorname
from media_gathering.LinkSearch.PixivNovel.Noveltitle import Noveltitle
from media_gathering.LinkSearch.PixivNovel.PixivNovelURL import PixivNovelURL


@dataclass(frozen=True)
class PixivNovelSaveDirectoryPath():
    """pixivノベル作品の保存先ディレクトリパス
    """
    path: Path  # 保存先ディレクトリパス

    def __post_init__(self) -> None:
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self.path, Path):
            raise TypeError("path is not Path.")
        return True

    @classmethod
    def create(cls, aapi: AppPixivAPI, novel_url: PixivNovelURL, base_path: Path) -> "PixivNovelSaveDirectoryPath":
        """pixivノベル作品の保存先ディレクトリパスを生成する

        Args:
            aapi (AppPixivAPI): 非公式pixivAPI操作インスタンス
            novel_url (PixivNovelURL): ノベルURL
            base_path (Path): 保存ディレクトリベースパス

        Raises:
            ValueError: 非公式pixivAPI操作時エラー

        Returns:
            PixivNovelSaveDirectoryPath: 保存先ディレクトリパス
                {base_path}/{作者名}({作者pixivID})/{ノベルタイトル}({ノベルID})/の形を想定している
        """
        # ノベルID取得
        novel_id = novel_url.novel_id.id

        # ノベル詳細取得
        works = aapi.novel_detail(novel_id)
        if works.error or (works.novel is None):
            raise ValueError("PixivNovelSaveDirectoryPath create failed.")
        work = works.novel

        # ValueObject生成
        author_name = Authorname(work.user.name).name
        author_id = Authorid(int(work.user.id)).id
        novel_title = Noveltitle(work.title).title

        # 既に{作者pixivID}が一致するディレクトリがあるか調べる
        sd_path = ""
        save_path = Path(base_path)
        filelist = []
        filelist_tp = [(sp.stat().st_mtime, sp.name) for sp in save_path.glob("*") if sp.is_dir()]
        for mtime, path in sorted(filelist_tp, reverse=True):
            filelist.append(path)

        regex = re.compile(r'.*\(([0-9]*)\)$')
        for dir_name in filelist:
            result = regex.match(dir_name)
            if result:
                ai = result.group(1)
                if ai == str(author_id):
                    sd_path = f"./{dir_name}/{novel_title}({novel_id})/"
                    break

        if sd_path == "":
            sd_path = f"./{author_name}({author_id})/{novel_title}({novel_id})/"

        save_directory_path = save_path / sd_path
        return PixivNovelSaveDirectoryPath(save_directory_path)


if __name__ == "__main__":
    import configparser
    import logging.config
    from pathlib import Path

    from media_gathering.LinkSearch.Password import Password
    from media_gathering.LinkSearch.PixivNovel.PixivNovelFetcher import PixivNovelFetcher
    from media_gathering.LinkSearch.Username import Username

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/LinkSearch/")
    if config["pixiv"].getboolean("is_pixiv_trace"):
        fetcher = PixivNovelFetcher(Username(config["pixiv"]["username"]), Password(config["pixiv"]["password"]), base_path)
        work_url = "https://www.pixiv.net/novel/show.php?id=3195243"
        save_directory_path = PixivNovelSaveDirectoryPath.create(fetcher.aapi, PixivNovelURL.create(work_url), base_path)
        print(save_directory_path)
