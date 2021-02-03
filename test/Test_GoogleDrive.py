# coding: utf-8
"""GoogleDrive APIのテスト

GoogleDrive APIの各種機能をテストする
設定ファイルとして ./config/credentials.json を使用する
各種機能、テストの中でもGoogleDrive APIを実際に呼び出してテストする
TODO::モック化
"""

import hashlib
import re
import random
import sys
import time
import unittest
import warnings
import zipfile
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from logging import WARNING, getLogger
from pathlib import Path
from typing import List

import requests
from mock import MagicMock, PropertyMock, patch

from PictureGathering import GoogleDrive

logger = getLogger("root")
logger.setLevel(WARNING)

CREDENTIALS_PATH = "./config/credentials.json"
SOURCE_FOLDER_NAME = "PictureGathering"
TEST_FOLDER_NAME = "test"


class TestGoogleDrive(unittest.TestCase):
    """テストメインクラス
    """
    @classmethod
    def setUpClass(cls):
        # テスト用フォルダに現在のアーカイブ先フォルダ内のファイルをコピー
        service = GoogleDrive.GetAPIService(CREDENTIALS_PATH)
        dest_folderid = GoogleDrive.GoogleDriveDirectoryCopy(SOURCE_FOLDER_NAME, TEST_FOLDER_NAME)

    @classmethod
    def tearDownClass(cls):
        service = GoogleDrive.GetAPIService(CREDENTIALS_PATH)
        dest_folderid = GoogleDrive.GetFolderId(service, TEST_FOLDER_NAME)
        # テスト用フォルダ削除
        # フォルダをdeleteするとフォルダ内のファイルも警告なしで全て削除される
        service.files().delete(fileId=dest_folderid).execute()

    def setUp(self):
        # requestsのResourceWarning抑制
        warnings.simplefilter("ignore", ResourceWarning)
        self.drive = self.__MakeInitialDrive()

    def tearDown(self):
        pass

    def __MakeInitialDrive(self):
        # 仮想のrootフォルダ
        mimeType = "application/vnd.google-apps.folder"
        res = []
        r = self.__MakeFilesObject(SOURCE_FOLDER_NAME, mimeType, [])
        parents = r["id"]
        res.append(r)

        # 仮想のテスト用フォルダ
        # r = self.__MakeFilesObject(TEST_FOLDER_NAME, mimeType, [parents])
        # parents = r["id"]
        # res.append(r)

        # 仮想のrootフォルダ内に仮想のサンプルファイルを追加
        mimeType = "application/x-zip-compressed"
        for i in range(0, 10):
            res.append(self.__MakeFilesObject("sample_{}.zip".format(i), mimeType, [parents]))
        return res

    def __MakeFilesObject(self, name, mimeType, parents):
        td_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        ct = datetime.now().strftime(td_format)
        res = {
            "id": hashlib.md5(name.encode()).hexdigest(),
            "name": name,
            "mimeType": mimeType,
            "trashed": False,
            "parents": parents,
            "createdTime": ct
        }
        return res

    def __MakeCredentialsMock(self, mock):
        # "google.oauth2.service_account.Credentials.from_service_account_file" のモックを設定するヘルパ
        # 呼び出し例：creds = Credentials.from_service_account_file(str(cred_path))
        def creds_se(filename):
            return filename
        mock.side_effect = creds_se
        return mock

    def __MakeBuildMock(self, mock):
        # "PictureGathering.GoogleDrive.build" のモックを設定するヘルパ
        # 呼び出し例：service = build("drive", "v3", credentials=creds, cache_discovery=False)
        def ReturnBuild(serviceName, version, credentials, cache_discovery):
            def ReturnFiles():
                buf_q = ""

                def ReturnList(q, fields=""):
                    buf_q = q

                    def ReturnListExecute():
                        res = {}
                        elements = []
                        if buf_q == "mimeType='application/vnd.google-apps.folder'":
                            mimeType = "application/vnd.google-apps.folder"
                            elements = [r for r in self.drive if r["mimeType"] == mimeType]
                        elif buf_q == "mimeType!='application/vnd.google-apps.folder'":
                            mimeType = "application/vnd.google-apps.folder"
                            elements = [r for r in self.drive if r["mimeType"] != mimeType]
  
                        res["files"] = elements
                        return res

                    r3 = MagicMock()
                    p_execute = PropertyMock()
                    p_execute.return_value = ReturnListExecute
                    type(r3).execute = p_execute
                    return r3

                r2 = MagicMock()
                p_list = PropertyMock()
                p_list.return_value = ReturnList
                type(r2).list = p_list
                return r2

            r1 = MagicMock()
            p_files = PropertyMock()
            p_files.return_value = ReturnFiles
            type(r1).files = p_files

            return r1
        mock.side_effect = ReturnBuild
        
        return mock

    def test_GetAPIService(self):
        """GoogleDriveのサービス取得機能をチェックする
        """

        with ExitStack() as stack:
            mockgdcreds = stack.enter_context(patch("google.oauth2.service_account.Credentials.from_service_account_file"))
            mockgdbuild = stack.enter_context(patch("PictureGathering.GoogleDrive.build"))

            mockgdcreds = self.__MakeCredentialsMock(mockgdcreds)
            mockgdbuild = self.__MakeBuildMock(mockgdbuild)

            actual_service = GoogleDrive.GetAPIService(CREDENTIALS_PATH)

            self.assertIsNotNone(actual_service)
            # expect_service = ("drive", "v3", str(Path(CREDENTIALS_PATH)), False)
            # self.assertEqual(expect_service, actual_service)

    def test_GetFolderId(self):
        """GoogleDrive内のフォルダID取得機能をチェックする
        """
        with ExitStack() as stack:
            mockgdcreds = stack.enter_context(patch("google.oauth2.service_account.Credentials.from_service_account_file"))
            mockgdbuild = stack.enter_context(patch("PictureGathering.GoogleDrive.build"))
            
            mockgdcreds = self.__MakeCredentialsMock(mockgdcreds)
            mockgdbuild = self.__MakeBuildMock(mockgdbuild)

            service = GoogleDrive.GetAPIService(CREDENTIALS_PATH)
            expect_id = ""
            folder_name_s = TEST_FOLDER_NAME
            results = service.files().list(q="mimeType='application/vnd.google-apps.folder'").execute()
            items = results.get("files")
            for item in items:
                if ("name" in item) and ("id" in item):
                    if item["name"] == folder_name_s:
                        expect_id = item["id"]
                        break
            actual_id = GoogleDrive.GetFolderId(service, folder_name_s)
            self.assertEqual(expect_id, actual_id)

    def test_GoogleDriveDirectoryCopy(self):
        """GoogleDriveのフォルダをコピーする機能をチェックする
        """
        with ExitStack() as stack:
            mockgdcreds = stack.enter_context(patch("google.oauth2.service_account.Credentials.from_service_account_file"))
            mockgdbuild = stack.enter_context(patch("PictureGathering.GoogleDrive.build"))
            
            mockgdcreds = self.__MakeCredentialsMock(mockgdcreds)
            mockgdbuild = self.__MakeBuildMock(mockgdbuild)
        
            service = GoogleDrive.GetAPIService(CREDENTIALS_PATH)
            src_folderid = GoogleDrive.GetFolderId(service, SOURCE_FOLDER_NAME)
            dest_folderid = GoogleDrive.GetFolderId(service, TEST_FOLDER_NAME)

            # res = GoogleDrive.GoogleDriveDirectoryCopy(SOURCE_FOLDER_NAME, TEST_FOLDER_NAME)

            # 全ファイルを取得
            results = service.files().list(q="mimeType!='application/vnd.google-apps.folder'",
                                           fields="files(id,name,mimeType,trashed,parents,createdTime)").execute()
            items = results.get("files", [])

            # コピー元とコピー先のファイルについて一致するか確認する
            src_items = [(item["name"], item["mimeType"], item["trashed"])
                         for item in items if src_folderid in item["parents"]]
            dest_items = [(item["name"], item["mimeType"], item["trashed"])
                          for item in items if dest_folderid in item["parents"]]
            src_items.sort()
            dest_items.sort()
            self.assertEqual(src_items, dest_items)

    def test_UploadToGoogleDrive(self):
        """GoogleDriveへのアップロード機能をチェックする
        """
        service = GoogleDrive.GetAPIService(CREDENTIALS_PATH)
        dest_folderid = GoogleDrive.GetFolderId(service, TEST_FOLDER_NAME)

        # アップロードテスト用zipを作成する
        ARCHIVE_TARGET = "test/operate_file_example"
        src_sd = Path(ARCHIVE_TARGET)
        dest_path = src_sd.parent / "operate_file_example.zip"
        target_list = [sp for sp in src_sd.glob("**/*") if re.search("^(?!.*zip).*$", str(sp))]
        if target_list:
            with zipfile.ZipFile(dest_path, "w", compression=zipfile.ZIP_DEFLATED) as zfout:
                for f in target_list:
                    zfout.write(f, f.name)

        # テスト用フォルダにアップロード
        uploaded_fileid1 = GoogleDrive.UploadToGoogleDrive(str(dest_path), CREDENTIALS_PATH, TEST_FOLDER_NAME)
        
        # アップロードが完了したか確認
        results1 = service.files().list(q="name='{}' and mimeType='application/x-zip-compressed' and '{}' in parents".format(dest_path.name, dest_folderid),
                                        fields="files(id,name,mimeType,trashed,parents,createdTime)").execute()

        # テスト用フォルダにアップロード（2回目）
        uploaded_fileid2 = GoogleDrive.UploadToGoogleDrive(str(dest_path), CREDENTIALS_PATH, TEST_FOLDER_NAME)
        
        # アップロードが完了したか確認（2回目）
        results2 = service.files().list(q="name='{}' and mimeType='application/x-zip-compressed' and '{}' in parents".format(dest_path.name, dest_folderid),
                                        fields="files(id,name,mimeType,trashed,parents,createdTime)").execute()

        # アップロードしたzipをGoogleDriveから削除（後始末を先にやる）
        # 2回目のアップロード時に1回目のファイルは削除されて作り直されているはずなので2回目のファイルのみ削除
        service.files().delete(fileId=uploaded_fileid2["id"]).execute()

        # アップロードテスト用zipを削除（後始末を先にやる）
        dest_path.unlink()

        # アップロード後の結果を確認する
        items1 = results1.get("files")
        self.assertEqual(1, len(items1))
        for item in items1:
            self.assertEqual([dest_folderid], item["parents"])
            self.assertEqual(dest_path.name, item["name"])

        items2 = results2.get("files")
        self.assertEqual(1, len(items2))
        for item in items2:
            self.assertEqual([dest_folderid], item["parents"])
            self.assertEqual(dest_path.name, item["name"])

        self.assertEqual(items1[0]["name"], items2[0]["name"])

    def test_GoogleDriveAllDelete(self):
        """GoogleDriveのフォルダ内全削除機能をチェックする
        """
        service = GoogleDrive.GetAPIService(CREDENTIALS_PATH)
        dest_folderid = GoogleDrive.GetFolderId(service, TEST_FOLDER_NAME)

        GoogleDrive.GoogleDriveAllDelete(TEST_FOLDER_NAME)

        # 削除確認
        results = service.files().list(q="'{}' in parents".format(dest_folderid)).execute()
        items = results.get("files")

        self.assertEqual([], items)

        # テスト開始時の状態に戻す
        dest_folderid = GoogleDrive.GoogleDriveDirectoryCopy(SOURCE_FOLDER_NAME, TEST_FOLDER_NAME)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
