import re
from dataclasses import dataclass
from pathlib import Path

from media_gathering.link_search.nijie.nijie_page_info import NijiePageInfo
from media_gathering.link_search.nijie.nijie_url import NijieURL


@dataclass(frozen=True)
class NijieSaveDirectoryPath:
    """nijie作品の保存先ディレクトリパス"""

    path: Path  # 保存先ディレクトリパス

    def __post_init__(self):
        self._is_valid()

    def _is_valid(self):
        if not isinstance(self.path, Path):
            raise TypeError("path is not Path.")
        return True

    @classmethod
    def create(cls, nijie_url: NijieURL, page_info: NijiePageInfo, base_path: Path) -> "NijieSaveDirectoryPath":
        """nijie作品の保存先ディレクトリパスを生成する

        Args:
            nijie_url (NijieURL): nijie作品ページURL
            base_path (Path): 保存ディレクトリベースパス
            page_info (NijiePageInfo): nijie作品詳細ページ結果

        Returns:
            NijieSaveDirectoryPath: 保存先ディレクトリパス
                {base_path}/{作者名}({作者ID})/{作品タイトル}({作品ID})/の形を想定している
        """
        if not isinstance(nijie_url, NijieURL):
            raise TypeError("nijie_url must be NijieURL.")
        if not isinstance(page_info, NijiePageInfo):
            raise TypeError("page_info must be NijiePageInfo.")
        if not isinstance(base_path, Path):
            raise TypeError("base_path must be Path.")

        author_name = page_info.author_name.name
        author_id = page_info.author_id.id
        work_title = page_info.work_title.title
        work_id = nijie_url.work_id.id

        # 既に{作者nijieID}が一致するディレクトリがあるか調べる
        sd_path = ""
        save_path = Path(base_path)
        filelist = []
        filelist_tp = [(sp.stat().st_mtime, sp.name) for sp in save_path.glob("*") if sp.is_dir()]
        for mtime, path in sorted(filelist_tp, reverse=True):
            filelist.append(path)

        regex = re.compile(r".*\(([0-9]*)\)$")
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
        return NijieSaveDirectoryPath(save_directory_path)


if __name__ == "__main__":
    import orjson

    from media_gathering.link_search.nijie.nijie_fetcher import NijieFetcher
    from media_gathering.link_search.password import Password
    from media_gathering.link_search.username import Username

    CONFIG_FILE_NAME = "./config/config.json"
    config = orjson.loads(Path(CONFIG_FILE_NAME).read_bytes())

    base_path = Path("./media_gathering/link_search/")
    if config["nijie"]["is_nijie_trace"]:
        fetcher = NijieFetcher(Username(config["nijie"]["email"]), Password(config["nijie"]["password"]), base_path)

        illust_id = 251267  # 一枚絵
        # illust_id = 251197  # 漫画
        # illust_id = 414793  # うごイラ一枚
        # illust_id = 409587  # うごイラ複数

        illust_url = f"https://nijie.info/view_popup.php?id={illust_id}"
        fetcher.fetch(illust_url)
