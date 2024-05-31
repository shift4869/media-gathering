"""Illustname のテスト

作者名を表すクラスをテストする
"""

import re
import sys
import unittest

import emoji

from media_gathering.link_search.nico_seiga.illustname import Illustname


class TestIllustname(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def _sanitize(self, _original_name: str) -> str:
        regex = re.compile(r'[\\/:*?"<>|]')
        trimed_name = regex.sub("", _original_name)
        non_emoji_name = emoji.replace_emoji(trimed_name, "")
        return non_emoji_name

    def test_Illustname(self):
        # 正常系
        # 通常
        name = "作成者1"
        illust_name = Illustname(name)
        self.assertEqual(name, illust_name.name)

        # 記号含み
        name = "作成者2?****//"
        illust_name = Illustname(name)
        expect = self._sanitize(name)
        self.assertEqual(expect, illust_name.name)

        # 絵文字含み
        name = "作成者3😀"
        illust_name = Illustname(name)
        expect = self._sanitize(name)
        self.assertEqual(expect, illust_name.name)

        # 異常系
        # 文字列でない
        with self.assertRaises(TypeError):
            illust_name = Illustname(-1)

        # 空文字列
        with self.assertRaises(ValueError):
            illust_name = Illustname("")

    def test_id(self):
        name = "作成者1"
        illust_name = Illustname(name)
        self.assertEqual(name, illust_name.name)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
