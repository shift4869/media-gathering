import sys
import unittest
from pathlib import Path

import orjson

from PictureGathering.Util import Result, find_values


class TestUtil(unittest.TestCase):
    def test_Result(self):
        self.assertEqual(True, hasattr(Result, "success"))
        self.assertEqual(True, hasattr(Result, "failed"))

    def test_find_values(self):
        cache_filepath = Path("./test/cache/test_notes_with_reactions.json")
        sample_dict = orjson.loads(
            cache_filepath.read_bytes()
        ).get("result")

        # 辞書とキーのみ指定
        actual = find_values(sample_dict, "username")
        expect = [
            "user1_username",
            "user2_username",
            "user1_username",
            "user3_username",
            "user1_username",
            "user4_username",
        ]
        self.assertEqual(expect, actual)

        # ホワイトリスト指定
        actual = find_values(sample_dict, "username", False, ["user"])
        expect = [
            "user1_username",
            "user1_username",
            "user1_username",
        ]
        self.assertEqual(expect, actual)

        # ブラックリスト指定
        actual = find_values(sample_dict, "username", False, [], ["note"])
        expect = [
            "user1_username",
            "user1_username",
            "user1_username",
        ]
        self.assertEqual(expect, actual)

        # ホワイトリスト指定複数
        actual = find_values(sample_dict, "name", False, ["note", "files"])
        expect = [
            "1300000001.jpg.webp",
            "1300000002.jpg.webp",
            "1300000003.jpg.webp",
            "1300000004.jpg.webp",
            "2300000001.png",
        ]
        self.assertEqual(expect, actual)

        # ブラックリスト複数指定
        actual = find_values(sample_dict, "createdAt", False, [], ["user", "note"])
        expect = [
            "2023-09-10T03:55:55.054Z",
            "2023-09-10T03:55:57.643Z",
            "2023-09-10T03:56:04.691Z",
        ]
        self.assertEqual(expect, actual)

        # 一意に確定する想定
        actual = find_values(sample_dict[0], "username", True, ["user"])
        expect = "user1_username"
        self.assertEqual(expect, actual)

        # 直下を調べる
        actual = find_values(sample_dict[0], "id", True, [""])
        expect = sample_dict[0]["id"]
        self.assertEqual(expect, actual)

        # 存在しないキーを指定
        actual = find_values(sample_dict, "invalid_key")
        expect = []
        self.assertEqual(expect, actual)

        # 空辞書を探索
        actual = find_values({}, "username")
        expect = []
        self.assertEqual(expect, actual)

        # 空リストを探索
        actual = find_values([], "username")
        expect = []
        self.assertEqual(expect, actual)

        # 文字列を指定
        actual = find_values("invalid_object", "username")
        expect = []
        self.assertEqual(expect, actual)

        # 一意に確定する想定の指定だが、複数見つかった場合
        with self.assertRaises(ValueError):
            actual = find_values(sample_dict, "username", True)

        # 一意に確定する想定の指定だが、見つからなかった場合
        with self.assertRaises(ValueError):
            actual = find_values(sample_dict, "invalid_key", True)

if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
