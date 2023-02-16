# coding: utf-8
"""IllustExtension のテスト

イラスト拡張子を表すクラスをテストする
"""
import sys
import unittest

from PictureGathering.LinkSearch.NicoSeiga.IllustExtension import Extension, IllustExtension


class TestIllustExtension(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_Extension(self):
        expect = [".jpg", ".png", ".gif"]
        actual = [ext.value for ext in Extension]
        self.assertEqual(expect, actual)

    def test_IllustExtension(self):
        # 正常系
        illust_extension = IllustExtension(Extension.JPG)
        self.assertEqual(Extension.JPG.value, illust_extension.extension)

        # 異常系
        # 文字列指定
        with self.assertRaises(TypeError):
            illust_extension = IllustExtension(".jpg")

    def test_create(self):
        # 正常系
        # .jpg
        data = b"\xff\xd8\xff\xff\xff\xff\xff\xff"
        illust_extension = IllustExtension.create(data)
        self.assertEqual(Extension.JPG.value, illust_extension.extension)

        # .png
        data = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"
        illust_extension = IllustExtension.create(data)
        self.assertEqual(Extension.PNG.value, illust_extension.extension)

        # .gif
        data = b"\x47\x49\x46\x38\xff\xff\xff\xff"
        illust_extension = IllustExtension.create(data)
        self.assertEqual(Extension.GIF.value, illust_extension.extension)

        # 異常系
        # 想定されるデータ形式でない
        with self.assertRaises(TypeError):
            data = b"\xff\xff\xff\xff\xff\xff\xff\xff"
            illust_extension = IllustExtension.create(data)

        # データが短い
        with self.assertRaises(ValueError):
            data = b"\xff\xff\xff\xff"
            illust_extension = IllustExtension.create(data)

        # データがbytes型でない
        with self.assertRaises(TypeError):
            data = -1
            illust_extension = IllustExtension.create(data)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
