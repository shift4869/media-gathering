# coding: utf-8
import re
from pathlib import Path
from dataclasses import dataclass

import emoji

from PictureGathering.LinkSearch.Nijie.NijiePageInfo import NijiePageInfo
from PictureGathering.LinkSearch.Nijie.NijieURL import NijieURL


@dataclass(frozen=True)
class NijieSaveDirectoryPath():
    path: Path

    def __post_init__(self):
        self._is_valid()

    def _is_valid(self):
        if not isinstance(self.path, Path):
            raise TypeError("path is not Path.")
        return True

    @classmethod
    def create(cls, nijie_url: NijieURL, base_path: Path, illust_info: NijiePageInfo) -> "NijieSaveDirectoryPath":
        author_name = illust_info.authorname.name
        author_id = illust_info.authorid.id
        illust_name = illust_info.illustname.name
        illust_id = nijie_url.illust_id.id

        # パスに使えない文字をサニタイズする
        # TODO::サニタイズを厳密に行う
        regex = re.compile(r'[\\/:*?"<>|]')
        author_name = regex.sub("", author_name)
        author_name = emoji.get_emoji_regexp().sub("", author_name)
        author_id = int(author_id)
        illust_title = regex.sub("", illust_name)
        illust_title = emoji.get_emoji_regexp().sub("", illust_title)

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
                        sd_path = f"./{dir_name}/{illust_title}({illust_id})/"
                        break

        if sd_path == "":
            sd_path = f"./{author_name}({author_id})/{illust_title}({illust_id})/"

        save_directory_path = save_path / sd_path
        return NijieSaveDirectoryPath(save_directory_path)


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = NijieSaveDirectoryPath.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
