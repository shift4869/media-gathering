# coding: utf-8
"""Authorname のテスト

作者名を表すクラスをテストする
"""
import re
import sys
import unittest

import emoji

from PictureGathering.LinkSearch.Skeb.Authorname import Authorname


class TestAuthorname(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def _sanitize(self, _original_name: str) -> str:
        regex = re.compile(r'[\\/:*?"<>|]')
        trimed_name = regex.sub("", _original_name)
        non_emoji_name = emoji.replace_emoji(trimed_name, "")
        return non_emoji_name

    def test_Authorname(self):
        # 正常系
        # 通常
        name = "作成者1"
        author_name = Authorname(name)
        self.assertEqual(name, author_name.name)

        # 記号含み
        name = "作成者2?****//"
        author_name = Authorname(name)
        expect = self._sanitize(name)
        self.assertEqual(expect, author_name.name)

        # 絵文字含み
        name = "作成者3😀"
        author_name = Authorname(name)
        expect = self._sanitize(name)
        self.assertEqual(expect, author_name.name)

        # 異常系
        # 文字列でない
        with self.assertRaises(TypeError):
            author_name = Authorname(-1)

        # 空文字列
        with self.assertRaises(ValueError):
            author_name = Authorname("")

    def test_id(self):
        name = "作成者1"
        author_name = Authorname(name)
        self.assertEqual(name, author_name.name)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
