# coding: utf-8
import re
from pathlib import Path
from dataclasses import dataclass

import emoji
from pixivpy3 import AppPixivAPI

from PictureGathering.LinkSearch.Pixiv.PixivWorkURL import PixivWorkURL


@dataclass(frozen=True)
class PixivSaveDirectoryPath():
    path: Path

    def __post_init__(self):
        self._is_valid()

    def _is_valid(self):
        if not isinstance(self.path, Path):
            raise TypeError("path is not Path.")
        return True

    @classmethod
    def create(cls, aapi: AppPixivAPI, pixiv_url: PixivWorkURL, base_path: Path) -> "PixivSaveDirectoryPath":
        illust_id = pixiv_url.illust_id

        works = aapi.illust_detail(illust_id)
        if works.error or (works.illust is None):
            raise ValueError("PixivSaveDirectoryPath create failed.")
        work = works.illust

        # パスに使えない文字をサニタイズする
        # TODO::サニタイズを厳密に行う
        regex = re.compile(r'[\\/:*?"<>|]')
        author_name = regex.sub("", work.user.name)
        author_name = emoji.get_emoji_regexp().sub("", author_name)
        author_id = int(work.user.id)
        illust_title = regex.sub("", work.title)
        illust_title = emoji.get_emoji_regexp().sub("", illust_title)

        # 既に{作者pixivID}が一致するディレクトリがあるか調べる
        IS_SEARCH_AUTHOR_ID = True
        sd_path = ""
        save_path = base_path
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
        return PixivSaveDirectoryPath(save_directory_path)


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = PixivSaveDirectoryPath.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
