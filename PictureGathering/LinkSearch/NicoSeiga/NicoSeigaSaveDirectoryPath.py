# coding: utf-8
import re
from dataclasses import dataclass
from pathlib import Path

from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaInfo import NicoSeigaInfo


@dataclass(frozen=True)
class NicoSeigaSaveDirectoryPath():
    path: Path

    def __post_init__(self):
        self._is_valid()

    def _is_valid(self):
        if not isinstance(self.path, Path):
            raise TypeError("path is not Path.")
        return True

    @classmethod
    def create(cls, illust_info: NicoSeigaInfo, base_path: Path) -> "NicoSeigaSaveDirectoryPath":
        illust_id = illust_info.illustid.id
        illust_name = illust_info.illustname.name
        author_id = illust_info.authorid.id
        author_name = illust_info.authorname.name

        # 既に{作者nijieID}が一致するディレクトリがあるか調べる
        IS_SEARCH_AUTHOR_ID = True
        sd_path = ""
        save_path = Path(base_path)
        if IS_SEARCH_AUTHOR_ID:
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
                        sd_path = f"./{dir_name}/{illust_name}({illust_id})/"
                        break

        if sd_path == "":
            sd_path = f"./{author_name}({author_id})/{illust_name}({illust_id})/"

        save_directory_path = save_path / sd_path
        return NicoSeigaSaveDirectoryPath(save_directory_path)


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
