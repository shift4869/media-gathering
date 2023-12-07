import sys
import unittest
from copy import deepcopy
from typing import Iterable

from mock import MagicMock
from pixivpy3 import AppPixivAPI

from media_gathering.link_search.pixiv.pixiv_source_list import PixivSourceList
from media_gathering.link_search.pixiv.pixiv_work_url import PixivWorkURL
from media_gathering.link_search.url import URL


class TestPixivSourceList(unittest.TestCase):
    def test_PixivSourceList(self):
        work_url = "https://www.pixiv.net/artworks/1111111{}"
        work_urls = [URL(work_url.format(i)) for i in range(10)]
        expect = deepcopy(work_urls)
        actual = PixivSourceList(work_urls)
        self.assertEqual(expect, actual._list)
        self.assertTrue(isinstance(actual, Iterable))

    def test_create(self):
        mock_aapi = MagicMock(spec=AppPixivAPI)

        # 一枚絵
        work_url = "https://www.pixiv.net/artworks/11111110"
        pixiv_url = PixivWorkURL.create(work_url)
        mock_works = MagicMock()
        mock_work = MagicMock()
        mock_work.page_count = 1
        mock_work.image_urls.large = work_url
        mock_works.error = False
        mock_works.illust = mock_work
        mock_aapi.illust_detail.side_effect = lambda work_id: mock_works
        actual = PixivSourceList.create(mock_aapi, pixiv_url)
        expect = PixivSourceList([URL(work_url)])
        self.assertEqual(expect, actual)

        # 漫画形式
        work_url = "https://www.pixiv.net/artworks/1111111{}"
        work_urls = [URL(work_url.format(i)) for i in range(10)]
        pixiv_url = PixivWorkURL.create(work_url.format(0))
        mock_works = MagicMock()
        mock_work = MagicMock()
        mock_work.page_count = len(work_urls)

        def make_property(image_url):
            r = MagicMock()
            r.image_urls.large = image_url
            return r
        mock_work.meta_pages = [make_property(url) for url in work_urls]
        mock_works.error = False
        mock_works.illust = mock_work
        mock_aapi.illust_detail.side_effect = lambda work_id: mock_works
        actual = PixivSourceList.create(mock_aapi, pixiv_url)
        expect = PixivSourceList(work_urls)
        self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            mock_works.error = True
            mock_aapi.illust_detail.side_effect = lambda work_id: mock_works
            actual = PixivSourceList.create(mock_aapi, pixiv_url)

        with self.assertRaises(TypeError):
            actual = PixivSourceList.create("invalid argument", pixiv_url)

        with self.assertRaises(TypeError):
            actual = PixivSourceList.create(mock_aapi, "invalid argument")


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
