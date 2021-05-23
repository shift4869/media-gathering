# coding: utf-8
"""アーカイバのテスト

Archiverの各種機能をテストする
"""

import re
import shutil
import sys
import time
import unittest
import zipfile
from contextlib import ExitStack
from datetime import datetime
from logging import WARNING, getLogger
from pathlib import Path

import freezegun
from mock import MagicMock, PropertyMock, patch

from PictureGathering import Archiver

logger = getLogger("root")
logger.setLevel(WARNING)


class TestArchiver(unittest.TestCase):
    """テストメインクラス
    """

    def setUp(self):
        pass

    def test_MakeZipFile(self):
        """アーカイブ作成機能のテスト
        """

        # アーカイブテスト対象のディレクトリをコピー
        ARCHIVE_TARGET = "test/operate_file_example"
        src_sd = Path(ARCHIVE_TARGET)
        expect_sd = src_sd.parent / "expect_archive"
        actual_sd = src_sd.parent / "actual_archive"
        if expect_sd.is_dir():
            shutil.rmtree(expect_sd)
        if actual_sd.is_dir():
            shutil.rmtree(actual_sd)
        shutil.copytree(src_sd, expect_sd)

        # ダミーzip生成
        (expect_sd.absolute() / "dummy.zip").touch()
        shutil.copytree(expect_sd, actual_sd)

        with freezegun.freeze_time("2021-01-29 11:52:24"):
            # アーカイブの名前予測
            expect_tsd = expect_sd.absolute()
            now_s = datetime.now()
            date_str_s = now_s.strftime("%Y%m%d_%H%M%S")
            type_str_s = "Fav"
            achive_name_s = "{}_{}.zip".format(type_str_s, date_str_s)
            expect_tpath = expect_tsd / achive_name_s

            # 既にあるzipファイルは削除する
            zipfile_list = [sp for sp in expect_tsd.glob("**/*") if re.search("^(.*zip).*$", str(sp))]
            for f in zipfile_list:
                f.unlink()

            # 対象ファイルリストを設定
            # zipファイル以外、かつ、ファイルサイズが0でないものを対象とする
            target_list = [p for p in expect_tsd.glob("**/*") if re.search("^(?!.*zip).*$", str(p)) and p.stat().st_size > 0]

            # zip圧縮する
            if target_list:
                with zipfile.ZipFile(expect_tpath, "w", compression=zipfile.ZIP_DEFLATED) as zfout:
                    for f in target_list:
                        zfout.write(f, f.name)
                        f.unlink()  # アーカイブしたファイルは削除する

            # 実行
            expect_path = expect_tpath
            actual_path = Path(Archiver.MakeZipFile(str(actual_sd), "Fav"))
            self.assertEqual(expect_path.name, actual_path.name)

            # 結果確認
            expect_files = [(sp.name, sp.stat().st_size) for sp in expect_path.parent.glob("**/*") if sp.is_file()]
            actual_files = [(sp.name, sp.stat().st_size) for sp in actual_path.parent.glob("**/*") if sp.is_file()]
            self.assertEqual(expect_files, actual_files)

            # 結果確認（zip展開後）
            with zipfile.ZipFile(expect_path) as existing_zip:
                existing_zip.extractall(expect_path.parent)
            with zipfile.ZipFile(actual_path) as existing_zip:
                existing_zip.extractall(actual_path.parent)
            expect_files = [(sp.name, sp.stat().st_size) for sp in expect_path.parent.glob("**/*") if sp.is_file()]
            actual_files = [(sp.name, sp.stat().st_size) for sp in actual_path.parent.glob("**/*") if sp.is_file()]
            self.assertEqual(expect_files, actual_files)

        # 後始末
        if expect_sd.is_dir():
            shutil.rmtree(expect_sd)
        if actual_sd.is_dir():
            shutil.rmtree(actual_sd)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
