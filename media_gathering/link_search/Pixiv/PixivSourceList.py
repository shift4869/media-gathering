import pprint
from dataclasses import dataclass
from typing import Iterable

from pixivpy3 import AppPixivAPI

from media_gathering.link_search.Pixiv.PixivWorkURL import PixivWorkURL
from media_gathering.link_search.URL import URL


@dataclass(frozen=True)
class PixivSourceList(Iterable):
    """pixiv作品の直リンクURLリスト
    """
    _list: list[URL]  # URLリスト

    def __post_init__(self) -> None:
        """初期化後処理

        バリデーションのみ
        """
        if not isinstance(self._list, list):
            raise TypeError("list is not list[], invalid PixivSourceList.")
        if self._list:
            if not all([isinstance(r, URL) for r in self._list]):
                raise ValueError("include not URL element, invalid PixivSourceList")

    def __iter__(self):
        return self._list.__iter__()

    def __len__(self):
        return self._list.__len__()

    def __getitem__(self, i):
        return self._list.__getitem__(i)

    @classmethod
    def create(cls, aapi: AppPixivAPI, pixiv_url: PixivWorkURL) -> "PixivSourceList":
        """pixiv作品の直リンクを取得する

        Args:
            aapi (AppPixivAPI): 非公式pixivAPI操作インスタンス
            pixiv_url (PixivWorkURL): 作品URL

        Raises:
            ValueError: 非公式pixivAPI操作時エラー

        Returns:
            PixivSourceList: pixiv作品の直リンクURLリスト
        """
        if not isinstance(aapi, AppPixivAPI):
            raise TypeError("aapi must be AppPixivAPI instance.")
        if not isinstance(pixiv_url, PixivWorkURL):
            raise TypeError("pixiv_url must be PixivWorkURL.")

        work_id = pixiv_url.work_id.id

        # イラスト情報取得
        works = aapi.illust_detail(work_id)
        if works.error or (works.illust is None):
            raise ValueError("PixivSourceList create failed.")
        work = works.illust

        source_list = []
        if work.page_count > 1:  # 漫画形式
            # https://i.pximg.net/c/600x1200_90/img-master/img/2022/06/03/05/01/37/98789839_p{i}_master1200.jpg
            for page_info in work.meta_pages:
                image_url = URL(page_info.image_urls.large)
                source_list.append(image_url)
        else:  # 一枚絵
            # https://i.pximg.net/c/600x1200_90/img-master/img/2022/06/03/22/46/49/98804653_p0_master1200.jpg
            image_url = URL(work.image_urls.large)
            source_list.append(image_url)

        return PixivSourceList(source_list)


if __name__ == "__main__":
    work_url = "https://www.pixiv.net/artworks/1111111{}"
    work_urls = [URL(work_url.format(i)) for i in range(10)]
    source_list = PixivSourceList(work_urls)
    pprint.pprint(source_list)
