import logging
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

import freezegun
import orjson

from media_gathering.util import Result, find_values, log_suppress, manage_cache_file


class TestUtil(unittest.TestCase):
    def test_Result(self):
        self.assertEqual(True, hasattr(Result, "success"))
        self.assertEqual(True, hasattr(Result, "failed"))

    def test_log_suppress(self):
        logger = logging.getLogger("external_test_logger")
        logger.disabled = False

        log_suppress()

        self.assertTrue(logger.disabled)

    def test_find_values(self):
        cache_filepath = Path("./tests/cache/test_notes_with_reactions.json")
        sample_dict = orjson.loads(cache_filepath.read_bytes()).get("result")

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

    def test_manage_cache_file(self):
        # 異常系チェック
        self.enterContext(freezegun.freeze_time("2026/08/05 12:34:56"))
        result = manage_cache_file(Path("./not_exist_path"))
        self.assertEqual(
            result,
            Result.failed,
        )

        # 一時ディレクトリ内で確認
        with tempfile.TemporaryDirectory() as tmp:
            base_path = Path(tmp)
            test_file = base_path / "test.txt"
            test_file.write_text("dummy")

            # 昨日の日付に変更
            yesterday = datetime.now() - timedelta(days=1)
            timestamp = yesterday.timestamp()
            test_file.touch()
            os.utime(test_file, (timestamp, timestamp))

            result = manage_cache_file(base_path)
            self.assertEqual(
                result,
                Result.success,
            )

            zip_file = base_path / yesterday.strftime("%Y%m%d.zip")
            self.assertTrue(zip_file.exists())
            self.assertFalse(test_file.exists())
            with ZipFile(zip_file) as zf:
                self.assertIn(
                    "test.txt",
                    zf.namelist(),
                )

        # 今日日付zip化テスト
        with tempfile.TemporaryDirectory() as tmp:
            base_path = Path(tmp)
            test_file = base_path / "today.txt"
            test_file.write_text("dummy")

            result = manage_cache_file(base_path)
            self.assertEqual(
                result,
                Result.success,
            )

            zip_files = list(base_path.glob("*.zip"))
            self.assertEqual(
                zip_files,
                [],
            )
            self.assertTrue(test_file.exists())

        # 月単位zip化テスト
        with tempfile.TemporaryDirectory() as tmp:
            base_path = Path(tmp)

            # 月末日zipを作成
            month_end_zip = base_path / "20260131.zip"
            with ZipFile(month_end_zip, "w") as zf:
                zf.writestr("dummy1.txt", "dummy")

            # 同月の日次zipを作成
            daily_zip = base_path / "20260101.zip"
            with ZipFile(daily_zip, "w") as zf:
                zf.writestr("dummy2.txt", "dummy")

            result = manage_cache_file(base_path)
            self.assertEqual(
                result,
                Result.success,
            )

            month_zip = base_path / "202601.zip"
            self.assertTrue(month_zip.exists())
            self.assertFalse(daily_zip.exists())
            self.assertFalse(month_end_zip.exists())

            with ZipFile(month_zip) as zf:
                self.assertIn(
                    "20260101.zip",
                    zf.namelist(),
                )
                self.assertIn(
                    "20260131.zip",
                    zf.namelist(),
                )

        # 年単位zip化テスト
        with tempfile.TemporaryDirectory() as tmp:
            base_path = Path(tmp)
            old_month = datetime.now() - timedelta(days=400)
            old_month_name = old_month.strftime("%Y%m")
            month_zip = base_path / f"{old_month_name}.zip"

            with ZipFile(month_zip, "w") as zf:
                zf.writestr(
                    "dummy.txt",
                    "dummy",
                )

            result = manage_cache_file(base_path)
            self.assertEqual(
                result,
                Result.success,
            )

            year_zip = base_path / f"{old_month.strftime('%Y')}.zip"
            self.assertTrue(year_zip.exists())
            self.assertFalse(month_zip.exists())

            with ZipFile(year_zip) as zf:
                self.assertIn(
                    f"{old_month_name}.zip",
                    zf.namelist(),
                )


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
