# coding: utf-8
import re
from pathlib import Path
from dataclasses import dataclass

import emoji
from pixivpy3 import AppPixivAPI

from PictureGathering.LinkSearch.PixivNovel.PixivNovelURL import PixivNovelURL


@dataclass(frozen=True)
class PixivNovelSaveDirectoryPath():
    path: Path

    def __post_init__(self):
        self._is_valid()

    def _is_valid(self):
        if not isinstance(self.path, Path):
            raise TypeError("path is not Path.")
        return True

    @classmethod
    def create(cls, aapi: AppPixivAPI, novel_url: PixivNovelURL, base_path: Path) -> "PixivNovelSaveDirectoryPath":
        # ノベルID取得
        novel_id = novel_url.novel_id

        # ノベル詳細取得
        works = aapi.novel_detail(novel_id)
        if works.error or (works.novel is None):
            raise ValueError("PixivNovelSaveDirectoryPath create failed.")
        work = works.novel

        # パスに使えない文字をサニタイズする
        # TODO::サニタイズを厳密に行う
        regex = re.compile(r'[\\/:*?"<>|]')
        author_name = regex.sub("", work.user.name)
        author_name = emoji.get_emoji_regexp().sub("", author_name)
        author_id = int(work.user.id)
        novel_title = regex.sub("", work.title)
        novel_title = emoji.get_emoji_regexp().sub("", novel_title)

        # 既に{作者pixivID}が一致するディレクトリがあるか調べる
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
                        sd_path = f"./{dir_name}/{novel_title}({novel_id})/"
                        break
        
        if sd_path == "":
            sd_path = f"./{author_name}({author_id})/{novel_title}({novel_id})/"

        save_directory_path = save_path / sd_path
        return PixivNovelSaveDirectoryPath(save_directory_path)


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = PixivNovelSaveDirectoryPath.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
