# coding: utf-8
"""Worktitle のテスト

作者名を表すクラスをテストする
"""
import re
import sys
import unittest

import emoji

from PictureGathering.LinkSearch.Nijie.Worktitle import Worktitle


class TestWorktitle(unittest.TestCase):
    def _sanitize(self, _original_title: str) -> str:
        regex = re.compile(r'[\\/:*?"<>|]')
        trimed_title = regex.sub("", _original_title)
        non_emoji_title = emoji.replace_emoji(trimed_title, "")
        return non_emoji_title

    def test_Worktitle(self):
        # 正常系
        # 通常
        title = "作成者1"
        illust_title = Worktitle(title)
        self.assertEqual(title, illust_title.title)

        # 記号含み
        title = "作成者2?****//"
        illust_title = Worktitle(title)
        expect = self._sanitize(title)
        self.assertEqual(expect, illust_title.title)

        # 絵文字含み
        title = "作成者3😀"
        illust_title = Worktitle(title)
        expect = self._sanitize(title)
        self.assertEqual(expect, illust_title.title)

        # 異常系
        # 文字列でない
        with self.assertRaises(TypeError):
            illust_title = Worktitle(-1)

        # 空文字列
        with self.assertRaises(ValueError):
            illust_title = Worktitle("")

    def test_id(self):
        title = "作成者1"
        illust_title = Worktitle(title)
        self.assertEqual(title, illust_title.title)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
