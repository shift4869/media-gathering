# coding: utf-8
"""NicoSeigaInfo のテスト

ニコニコ静画の情報をまとめるクラスをテストする
"""
import sys
import unittest

from PictureGathering.LinkSearch.NicoSeiga.Authorid import Authorid
from PictureGathering.LinkSearch.NicoSeiga.Authorname import Authorname
from PictureGathering.LinkSearch.NicoSeiga.Illustid import Illustid
from PictureGathering.LinkSearch.NicoSeiga.Illustname import Illustname
from PictureGathering.LinkSearch.NicoSeiga.NicoSeigaInfo import NicoSeigaInfo


class TestNicoSeigaInfo(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_NicoSeigaInfo(self):
        # 正常系
        author_id = Authorid(12345678)
        illust_id = Illustid(11111111)
        illust_name = Illustname("作品名1")
        author_name = Authorname("作成者1")
        illust_info = NicoSeigaInfo(illust_id, illust_name, author_id, author_name)

        self.assertEqual(illust_id, illust_info.illust_id)
        self.assertEqual(illust_name, illust_info.illust_name)
        self.assertEqual(author_id, illust_info.author_id)
        self.assertEqual(author_name, illust_info.author_name)

        # 異常系
        with self.assertRaises(TypeError):
            illust_info = NicoSeigaInfo("invalid illust_id", illust_name, author_id, author_name)

    def test_is_valid(self):
        author_id = Authorid(12345678)
        illust_id = Illustid(11111111)
        illust_name = Illustname("作品名1")
        author_name = Authorname("作成者1")
        illust_info = NicoSeigaInfo(illust_id, illust_name, author_id, author_name)

        self.assertEqual(True, illust_info._is_valid())


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
