# coding: utf-8
"""IllustConvertor のテスト
"""
import shutil
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path

from mock import MagicMock, call, patch

from PictureGathering.LinkSearch.Skeb.IllustConvertor import IllustConvertor


class TestIllustConvertor(unittest.TestCase):
    def setUp(self) -> None:
        self.base_path = Path("./test/LinkSearch/Skeb/") / "作者名1"
        self.source = self.base_path / "123/作者名_123_001.webp"
        self.source.parent.mkdir(parents=True, exist_ok=True)
        self.source.touch(exist_ok=True)

    def tearDown(self) -> None:
        if self.base_path.exists():
            shutil.rmtree(self.base_path)

    def test_IllustConvertor(self):
        extension = ".png"
        converter = IllustConvertor(self.source, extension)

        self.assertEqual(self.source, converter._source)
        self.assertEqual(extension, converter._extension)
        self.assertEqual(".webp", converter.SOURCE_EXTENSION)

    def test_is_valid(self):
        extension = ".png"
        converter = IllustConvertor(self.source, extension)
        self.assertTrue(converter._is_valid())

        with self.assertRaises(TypeError):
            self.source.with_suffix(".invalid").touch(exist_ok=True)
            converter = IllustConvertor(self.source.with_suffix(".invalid"), extension)

        with self.assertRaises(FileNotFoundError):
            self.source.with_suffix(".invalid").unlink(missing_ok=True)
            converter = IllustConvertor(self.source.with_suffix(".invalid"), extension)

        with self.assertRaises(TypeError):
            converter = IllustConvertor(self.source, -1)

        with self.assertRaises(TypeError):
            converter = IllustConvertor("invalid_source", extension)

    def test_convert(self):
        with ExitStack() as stack:
            mock_image = stack.enter_context(patch("PictureGathering.LinkSearch.Skeb.IllustConvertor.Image"))

            def image(src_path: Path) -> MagicMock:
                r1 = MagicMock()
                r2 = MagicMock()
                r2.save.side_effect = lambda dst_path: dst_path.touch(exist_ok=True)
                r1.convert.side_effect = lambda mode: r2
                return r1
            mock_image.open.side_effect = image

            extension = ".png"
            converter = IllustConvertor(self.source, extension)
            dst_path = self.source.with_suffix(extension)
            actual = converter.convert()
            expect = dst_path
            self.assertEqual(expect, actual)
            self.assertFalse(self.source.exists())
            self.assertTrue(dst_path.exists())

            expect = [
                call.open(self.source)
            ]
            self.assertEqual(expect, mock_image.mock_calls)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
