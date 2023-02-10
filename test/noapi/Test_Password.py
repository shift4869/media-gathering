# coding: utf-8
"""Password のテスト

パスワードを表すクラスのテスト
"""
import sys
import unittest

from PictureGathering.noapi.Password import Password


class TestPassword(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_Password(self):
        # 正常系
        word = "パスワード1"
        password = Password(word)

        # 異常系
        # 空白
        with self.assertRaises(ValueError):
            password = Password("")

        # 文字列でない
        with self.assertRaises(TypeError):
            password = Password(-1)

    def test_word(self):
        word = "パスワード1"
        password = Password(word)
        self.assertEqual(word, password.password)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
