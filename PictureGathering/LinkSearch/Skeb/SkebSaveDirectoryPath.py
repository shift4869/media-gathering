# coding: utf-8
from dataclasses import dataclass
from pathlib import Path

from PictureGathering.LinkSearch.Skeb.SkebURL import SkebURL


@dataclass(frozen=True)
class SkebSaveDirectoryPath():
    path: Path

    def __post_init__(self):
        self._is_valid()

    def _is_valid(self):
        if not isinstance(self.path, Path):
            raise TypeError("path is not Path.")
        return True

    @classmethod
    def create(cls, skeb_url: SkebURL, base_path: Path) -> "SkebSaveDirectoryPath":
        # urlチェック
        author_name = skeb_url.author_name
        work_id = skeb_url.illust_id

        # パス生成
        save_path = base_path
        sd_path = f"./{author_name.name}/{work_id.id:03}/"
        save_directory_path = save_path / sd_path
        return SkebSaveDirectoryPath(save_directory_path)


if __name__ == "__main__":
    urls = [
        "https://www.pixiv.net/artworks/86704541",  # 投稿動画
        "https://www.pixiv.net/artworks/86704541?some_query=1",  # 投稿動画(クエリつき)
        "https://不正なURLアドレス/artworks/86704541",  # 不正なURLアドレス
    ]

    try:
        for url in urls:
            u = SkebSaveDirectoryPath.create(url)
            print(u.non_query_url)
            print(u.original_url)
    except ValueError as e:
        print(e)
