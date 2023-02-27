# coding: utf-8
"""NijiePageInfo のテスト
"""
import sys
import unittest

from bs4 import BeautifulSoup

from PictureGathering.LinkSearch.Nijie.Authorid import Authorid
from PictureGathering.LinkSearch.Nijie.Authorname import Authorname
from PictureGathering.LinkSearch.Nijie.NijiePageInfo import NijiePageInfo
from PictureGathering.LinkSearch.Nijie.NijieSourceList import NijieSourceList
from PictureGathering.LinkSearch.Nijie.Worktitle import Worktitle


class TestNijiePageInfo(unittest.TestCase):
    def _get_NijieSourceList(self) -> NijieSourceList:
        url_base = "https://nijie.info/view_popup.php?id={}"
        urls = [url_base.format(i) for i in range(10)]
        return NijieSourceList.create(urls)

    def test_NijiePageInfo(self):
        urls = self._get_NijieSourceList()
        author_name = Authorname("作成者1")
        author_id = Authorid(11111111)
        work_title = Worktitle("作品名1")

        actual = NijiePageInfo(urls, author_name, author_id, work_title)

        self.assertEqual(urls, actual.urls)
        self.assertEqual(author_name, actual.author_name)
        self.assertEqual(author_id, actual.author_id)
        self.assertEqual(work_title, actual.work_title)

    def test_is_valid(self):
        urls = self._get_NijieSourceList()
        author_name = Authorname("作成者1")
        author_id = Authorid(11111111)
        work_title = Worktitle("作品名1")

        actual = NijiePageInfo(urls, author_name, author_id, work_title)
        self.assertTrue(actual._is_valid())

        with self.assertRaises(TypeError):
            actual = NijiePageInfo("invalid_args", author_name, author_id, work_title)

        with self.assertRaises(TypeError):
            actual = NijiePageInfo(urls, "invalid_args", author_id, work_title)

        with self.assertRaises(TypeError):
            actual = NijiePageInfo(urls, author_name, "invalid_args", work_title)

        with self.assertRaises(TypeError):
            actual = NijiePageInfo(urls, author_name, author_id, "invalid_args")

    def test_create(self):
        html_img = """
            <title>作品名1 | 作者名1 | ニジエ</title>
            <div id="img_filter" data-index='0'>
            <a href="javascript:void(0);">
            <img src="//pic.nijie.net/04/nijie/23m02/24/11111111/illust/sample_01.jpg" border="0" />
            </a>
            </div>
        """
        soup = BeautifulSoup(html_img)
        actual = NijiePageInfo.create(soup)

        urls = ["http://pic.nijie.net/04/nijie/23m02/24/11111111/illust/sample_01.jpg"]
        source_list = NijieSourceList.create(urls)
        author_name = Authorname("作者名1")
        author_id = Authorid(11111111)
        illust_name = Worktitle("作品名1")
        expect = NijiePageInfo(source_list, author_name, author_id, illust_name)
        self.assertEqual(expect, actual)

        html_video = """
            <title>作品名1 | 作者名1 | ニジエ</title>
            <div id="img_filter" data-index='0'>
            <a href="javascript:void(0);">
            <video autoplay="autoplay" loop="loop" class="mozamoza ngtag" illust_id="542233" user_id="11111111" itemprop="image"
             src="//pic.nijie.net/02/nijie/23m02/12/11111111/illust/sample_01.mp4"
             alt="sample_01" style="display:none;"></video>
            </a>
            </div>
        """
        soup = BeautifulSoup(html_video)
        actual = NijiePageInfo.create(soup)

        urls = ["http://pic.nijie.net/02/nijie/23m02/12/11111111/illust/sample_01.mp4"]
        source_list = NijieSourceList.create(urls)
        author_name = Authorname("作者名1")
        author_id = Authorid(11111111)
        illust_name = Worktitle("作品名1")
        expect = NijiePageInfo(source_list, author_name, author_id, illust_name)
        self.assertEqual(expect, actual)

        with self.assertRaises(ValueError):
            soup = BeautifulSoup("")
            actual = NijiePageInfo.create(soup)

        with self.assertRaises(TypeError):
            actual = NijiePageInfo.create(-1)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
