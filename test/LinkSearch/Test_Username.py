"""Username のテスト

ユーザー名を表すクラスをテストする
"""
import sys
import unittest

from media_gathering.LinkSearch.Username import Username


class TestUsername(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_Username(self):
        # 正常系
        name = "ユーザー名1"
        username = Username(name)

        # 異常系
        # 空白
        with self.assertRaises(ValueError):
            username = Username("")

        # 文字列でない
        with self.assertRaises(TypeError):
            username = Username(-1)

    def test_name(self):
        name = "ユーザー名1"
        username = Username(name)
        self.assertEqual(name, username.name)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
