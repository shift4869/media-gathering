import re
from dataclasses import dataclass
from pathlib import Path

from pixivpy3 import AppPixivAPI

from media_gathering.link_search.pixiv.Authorid import Authorid
from media_gathering.link_search.pixiv.Authorname import Authorname
from media_gathering.link_search.pixiv.PixivWorkURL import PixivWorkURL
from media_gathering.link_search.pixiv.Worktitle import Worktitle


@dataclass(frozen=True)
class PixivSaveDirectoryPath():
    """pixiv作品の保存先ディレクトリパス
    """
    path: Path  # 保存先ディレクトリパス

    def __post_init__(self):
        self._is_valid()

    def _is_valid(self):
        if not isinstance(self.path, Path):
            raise TypeError("path is not Path.")
        return True

    @classmethod
    def create(cls, aapi: AppPixivAPI, pixiv_url: PixivWorkURL, base_path: Path) -> "PixivSaveDirectoryPath":
        """pixiv作品の保存先ディレクトリパスを生成する

        Args:
            aapi (AppPixivAPI): 非公式pixivAPI操作インスタンス
            pixiv_url (PixivWorkURL): 作品URL
            base_path (Path): 保存ディレクトリベースパス

        Raises:
            ValueError: 非公式pixivAPI操作時エラー

        Returns:
            PixivNovelSaveDirectoryPath: 保存先ディレクトリパス
                {base_path}/{作者名}({作者pixivID})/{作品タイトル}({作品ID})/の形を想定している
        """
        # 作品ID取得
        work_id = pixiv_url.work_id.id

        # 作品詳細取得
        works = aapi.illust_detail(work_id)
        if works.error or (works.illust is None):
            raise ValueError("PixivSaveDirectoryPath create failed.")
        work = works.illust

        # ValueObject生成
        author_name = Authorname(work.user.name).name
        author_id = Authorid(int(work.user.id)).id
        work_title = Worktitle(work.title).title

        # 既に{作者pixivID}が一致するディレクトリがあるか調べる
        sd_path = ""
        save_path = base_path
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
                    sd_path = f"./{dir_name}/{work_title}({work_id})/"
                    break
        
        if sd_path == "":
            sd_path = f"./{author_name}({author_id})/{work_title}({work_id})/"

        save_directory_path = save_path / sd_path
        return PixivSaveDirectoryPath(save_directory_path)


if __name__ == "__main__":
    import configparser
    import logging.config
    from pathlib import Path

    from media_gathering.link_search.Password import Password
    from media_gathering.link_search.pixiv.PixivFetcher import PixivFetcher
    from media_gathering.link_search.Username import Username

    logging.config.fileConfig("./log/logging.ini", disable_existing_loggers=False)
    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    base_path = Path("./PictureGathering/link_search/")
    if config["pixiv"].getboolean("is_pixiv_trace"):
        fetcher = PixivFetcher(Username(config["pixiv"]["username"]), Password(config["pixiv"]["password"]), base_path)
        work_url = "https://www.pixiv.net/artworks/86704541"
        save_directory_path = PixivSaveDirectoryPath.create(fetcher.aapi, PixivWorkURL.create(work_url), base_path)
        print(save_directory_path)
