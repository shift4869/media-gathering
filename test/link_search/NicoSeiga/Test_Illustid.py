"""Illustid のテスト

作者IDを表すクラスをテストする
"""
import sys
import unittest

from media_gathering.link_search.NicoSeiga.Illustid import Illustid


class TestIllustid(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_Illustid(self):
        # 正常系
        id_num = 12345678
        illustid = Illustid(id_num)

        # 異常系
        # 0は不正なIDとする
        with self.assertRaises(ValueError):
            illustid = Illustid(0)

        # マイナスのID
        with self.assertRaises(ValueError):
            illustid = Illustid(-1)

        # 数値でない
        with self.assertRaises(TypeError):
            illustid = Illustid("invalid id")

        # 数値でない
        with self.assertRaises(TypeError):
            illustid = Illustid("")

    def test_id(self):
        id_num = 12345678
        illustid = Illustid(id_num)
        self.assertEqual(id_num, illustid.id)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
