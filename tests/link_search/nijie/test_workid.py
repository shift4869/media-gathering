"""Workid のテスト

作者IDを表すクラスをテストする
"""

import sys
import unittest

from media_gathering.link_search.nijie.workid import Workid


class TestWorkid(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_Workid(self):
        # 正常系
        id_num = 12345678
        workid = Workid(id_num)

        # 異常系
        # 0は不正なIDとする
        with self.assertRaises(ValueError):
            workid = Workid(0)

        # マイナスのID
        with self.assertRaises(ValueError):
            workid = Workid(-1)

        # 数値でない
        with self.assertRaises(TypeError):
            workid = Workid("invalid id")

        # 数値でない
        with self.assertRaises(TypeError):
            workid = Workid("")

    def test_id(self):
        id_num = 12345678
        workid = Workid(id_num)
        self.assertEqual(id_num, workid.id)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
