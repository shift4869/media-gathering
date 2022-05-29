# coding: utf-8
from dataclasses import dataclass
from typing import Iterable

from pixivpy3 import PixivAPI

from PictureGathering.LinkSearch.PixivURL import PixivURL
from PictureGathering.LinkSearch.URL import URL


@dataclass(frozen=True)
class PixivIllustURLList(Iterable):
    _list: list[URL]

    def __post_init__(self) -> None:
        """初期化後処理

        バリデーションのみ
        """
        if not isinstance(self._list, list):
            raise TypeError("list is not list[], invalid PixivIllustURLList.")
        if self._list:
            if not all([isinstance(r, URL) for r in self._list]):
                raise ValueError(f"include not URL element, invalid PixivIllustURLList")

    def __iter__(self):
        return self._list.__iter__()

    def __len__(self):
        return self._list.__len__()

    def __getitem__(self, i):
        return self._list.__getitem__(i)

    @classmethod
    def create(cls, aapi: PixivAPI, pixiv_url: PixivURL) -> "PixivIllustURLList":
        illust_id = pixiv_url.illust_id
        if illust_id == -1:
            return []

        # イラスト情報取得
        works = aapi.illust_detail(illust_id)
        if works.error or (works.illust is None):
            return []
        work = works.illust

        illust_url_list = []
        if work.page_count > 1:  # 漫画形式
            for page_info in work.meta_pages:
                image_url = URL(page_info.image_urls.large)
                illust_url_list.append(image_url)
        else:  # 一枚絵
            image_url = URL(work.image_urls.large)
            illust_url_list.append(image_url)

        return PixivIllustURLList(illust_url_list)


if __name__ == "__main__":
    pass
