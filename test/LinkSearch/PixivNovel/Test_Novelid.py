"""Novelid のテスト

作者IDを表すクラスをテストする
"""
import sys
import unittest

from PictureGathering.LinkSearch.PixivNovel.Novelid import Novelid


class TestNovelid(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_Novelid(self):
        # 正常系
        id_num = 12345678
        novelid = Novelid(id_num)

        # 異常系
        # 0は不正なIDとする
        with self.assertRaises(ValueError):
            novelid = Novelid(0)

        # マイナスのID
        with self.assertRaises(ValueError):
            novelid = Novelid(-1)

        # 数値でない
        with self.assertRaises(TypeError):
            novelid = Novelid("invalid id")

        # 数値でない
        with self.assertRaises(TypeError):
            novelid = Novelid("")

    def test_id(self):
        id_num = 12345678
        novelid = Novelid(id_num)
        self.assertEqual(id_num, novelid.id)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
