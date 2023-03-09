# coding: utf-8
"""Converter のテスト
"""
import shutil
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

from mock import MagicMock, call, patch

from PictureGathering.LinkSearch.Skeb.Converter import Converter, ConvertResult
from PictureGathering.LinkSearch.Skeb.SaveFilename import Extension


class TestConverter(unittest.TestCase):
    def test_ConvertResult(self):
        expect = ["SUCCESS", "PASSED"]
        actual = [r.name for r in ConvertResult]
        self.assertEqual(expect, actual)

    def test_Converter(self):
        src_file_path = Path("./test/LinkSearch/Skeb/作者名1/123/作者名_123_001.webp")
        converter = Converter([src_file_path])

        expect = [src_file_path]
        self.assertEqual(expect, converter.src_file_pathlist)
        expect = []
        self.assertEqual(expect, converter.dst_file_pathlist)
        expect = {
            Extension.WEBP.value: Extension.PNG.value,
            Extension.MP4.value: Extension.MP4.value,
        }
        self.assertEqual(expect, converter.convert_map)

    def test_is_valid(self):
        src_file_path = Path("./test/LinkSearch/Skeb/作者名1/123/作者名_123_001.webp")
        converter = Converter([src_file_path])
        self.assertTrue(converter._is_valid())

        converter = Converter([])
        self.assertTrue(converter._is_valid())

        with self.assertRaises(ValueError):
            converter = Converter(["invalid_Path"])

        with self.assertRaises(TypeError):
            converter = Converter("invalid_args_type")

    def test_convert(self):
        with ExitStack() as stack:
            mock_illust_convertor = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.Converter.IllustConvertor"))

            def illust_convertor(src_path: Path, dst_ext: str) -> MagicMock:
                r = MagicMock()
                r.convert.side_effect = lambda: src_path.with_suffix(dst_ext)
                return r
            mock_illust_convertor.side_effect = illust_convertor

            # .webp -> .png
            FILE_NUM = 15
            base_path = Path("./test/LinkSearch/Skeb/") / "作者名1"
            src_file_template = str(base_path / "123/作者名_123_{:03}.webp")
            src_file_pathlist = [Path(src_file_template.format(i)) for i in range(FILE_NUM)]
            src_file_pathlist[0].parent.mkdir(parents=True, exist_ok=True)
            list(map(lambda p: p.touch(exist_ok=True), src_file_pathlist))
            converter = Converter(src_file_pathlist)

            actual = converter.convert()
            expect = ConvertResult.SUCCESS
            self.assertIs(expect, actual)
            expect = []
            expect_calls = []
            for src_path in src_file_pathlist:
                src_ext = src_path.suffix
                dst_ext = converter.convert_map.get(src_ext, Extension.UNKNOWN.value)
                expect.append(src_path.with_suffix(dst_ext))
                expect_calls.append(call(src_path, dst_ext))
            self.assertEqual(expect, converter.dst_file_pathlist)
            self.assertEqual(expect_calls, mock_illust_convertor.mock_calls)
            mock_illust_convertor.reset_mock()

            if base_path.exists():
                shutil.rmtree(base_path)

            # .mp4 -> .mp4
            src_file_template = str(base_path / "123/作者名_123_{:03}.mp4")
            src_file_pathlist = [Path(src_file_template.format(i)) for i in range(FILE_NUM)]
            src_file_pathlist[0].parent.mkdir(parents=True, exist_ok=True)
            list(map(lambda p: p.touch(exist_ok=True), src_file_pathlist))
            converter = Converter(src_file_pathlist)

            actual = converter.convert()
            expect = ConvertResult.SUCCESS
            self.assertIs(expect, actual)
            expect = []
            for src_path in src_file_pathlist:
                src_ext = src_path.suffix
                dst_ext = converter.convert_map.get(src_ext, Extension.UNKNOWN.value)
                expect.append(src_path.with_suffix(dst_ext))
            self.assertEqual(expect, converter.dst_file_pathlist)
            mock_illust_convertor.assert_not_called()
            mock_illust_convertor.reset_mock()

            if base_path.exists():
                shutil.rmtree(base_path)

            # 実体が存在しないファイルパスを指定
            src_file_template = str(base_path / "/123/作者名_123_{:03}.webp")
            src_file_pathlist = [Path(src_file_template.format(i)) for i in range(FILE_NUM)]
            converter = Converter(src_file_pathlist)

            actual = converter.convert()
            expect = ConvertResult.SUCCESS
            self.assertIs(expect, actual)
            expect = []
            self.assertEqual(expect, converter.dst_file_pathlist)
            mock_illust_convertor.assert_not_called()
            mock_illust_convertor.reset_mock()

            # 変換対象なし
            converter = Converter([])
            actual = converter.convert()
            expect = ConvertResult.PASSED
            self.assertIs(expect, actual)

            # 後始末
            if base_path.exists():
                shutil.rmtree(base_path)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
