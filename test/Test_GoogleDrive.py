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
    def setUp(self):
        # requestsのResourceWarning抑制
        warnings.simplefilter("ignore", ResourceWarning)
        self.drive = self.__MakeInitialDrive()

    def tearDown(self):
        pass

    def __MakeInitialDrive(self) -> List[dict]:
        """仮想のGoogleDriveの初期状態を設定する

        Returns:
            list[dict]: GoogleDriveの仮想rootフォルダと仮想Filesオブジェクトのリスト
        """
        res = []

        # 仮想のrootフォルダ
        mimeType = "application/vnd.google-apps.folder"
        r = self.__MakeFilesObject(SOURCE_FOLDER_NAME, mimeType, [])
        parents = r["id"]
        res.append(r)

        # 仮想のrootフォルダ内に仮想のサンプルファイルを追加
        mimeType = "application/x-zip-compressed"
        for i in range(0, 11):
            res.append(self.__MakeFilesObject("sample_{}.zip".format(i), mimeType, [parents]))
        return res

    def __MakeFilesObject(self, name: str, mimeType: str, parents: List[str]) -> dict:
        """仮想Filesオブジェクトを生成する

        Args:
            name (str): ファイル/フォルダ名
            mimeType (str): mimetype
            parents (str): 所属するフォルダのID

        Returns:
            dict: 仮想Filesオブジェクト
        """
        td_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        ct = (datetime.now() + timedelta(hours=-9)).strftime(td_format)
        parents_str = "_".join(parents)
        id_str = hashlib.md5(name.encode()).hexdigest() + hashlib.md5(parents_str.encode()).hexdigest()
        res = {
            "id": id_str,
            "name": name,
            "mimeType": mimeType,
            "trashed": False,
            "parents": parents,
            "createdTime": ct
        }
        return res

    def __MakeCredentialsMock(self, mock: MagicMock) -> MagicMock:
        """ "google.oauth2.service_account.Credentials.from_service_account_file" のモックを設定するヘルパ

        Notes:
            呼び出し例:creds = Credentials.from_service_account_file(str(cred_path))

        Args:
            mock (MagicMock): 設定対象のmock

        Returns:
            MagicMock: 設定後のmock
        """
        def creds_se(filename):
            self.assertTrue(Path(filename).is_file())
            return filename
        mock.side_effect = creds_se
        return mock

    def __MakeMediaUploadMock(self, mock: MagicMock) -> MagicMock:
        """ "apiclient.http.MediaFileUpload" のモックを設定するヘルパ

        Notes:
            呼び出し例:media = MediaFileUpload(file_path, mimetype="application/x-zip-compressed", resumable=True)

        Args:
            mock (MagicMock): 設定対象のmock

        Returns:
            MagicMock: 設定後のmock
        """
        def mediaupload_se(file_path, mimetype, resumable):
            self.assertTrue(Path(file_path).is_file())
            self.assertEqual(True, resumable)
            res = {
                "file_path": file_path,
                "mimetype": mimetype,
                "resumable": resumable
            }
            return res
        mock.side_effect = mediaupload_se
        return mock

    def __MakeBuildMock(self, mock: MagicMock) -> MagicMock:
        """ "PictureGathering.GoogleDrive.build" のモックを設定するヘルパ

        Notes:
            呼び出し例:
            service = build("drive", "v3", credentials=creds, cache_discovery=False)
            results = service.files().list(q="mimeType='application/vnd.google-apps.folder'").execute()
            results = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
            results = service.files().copy(body=file_metadata, fileId=item["id"]).execute()
            results = service.files().delete(fileId=item["id"]).execute()

        Args:
            mock (MagicMock): 設定対象のmock

        Returns:
            MagicMock: 設定後のmock
        """
        def ReturnBuild(serviceName, version, credentials, cache_discovery):
            self.assertEqual("drive", serviceName)
            self.assertEqual("v3", version)
            self.assertEqual(str(Path(CREDENTIALS_PATH)), credentials)
            self.assertTrue(Path(credentials).is_file())
            self.assertEqual(False, cache_discovery)

            def ReturnFiles():
                def ReturnList(q, fields=""):
                    def ReturnListExecute():
                        res = {}
                        records = []

                        rs = re.search("^mimeType='(.*)'$", q)
                        if rs and rs.groups():
                            mimeType = rs.groups()[0]
                            records = [r for r in self.drive if r["mimeType"] == mimeType]
                        rs = re.search("^mimeType!='(.*)'$", q)
                        if rs and rs.groups():
                            mimeType = rs.groups()[0]
                            records = [r for r in self.drive if r["mimeType"] != mimeType]
                        rs = re.search("^'(.*)' in parents$", q)
                        if rs and rs.groups():
                            parent = rs.groups()[0]
                            records = [r for r in self.drive if parent in r["parents"]]
                        rs = re.search("^mimeType='(.*)' and '(.*)' in parents$", q)
                        if rs and rs.groups():
                            mimeType = rs.groups()[0]
                            parent = rs.groups()[1]
                            records = [r for r in self.drive if r["mimeType"] == mimeType and parent in r["parents"]]
                        rs = re.search("^name='(.*)' and mimeType='(.*)' and '(.*)' in parents$", q)
                        if rs and rs.groups():
                            name = rs.groups()[0]
                            mimeType = rs.groups()[1]
                            parent = rs.groups()[2]
                            records = [r for r in self.drive if r["name"] == name and r["mimeType"] == mimeType and parent in r["parents"]]

                        res["files"] = records
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

                def ReturnCreate(body, fields="", media_body=""):
                    def ReturnCreateExecute():
                        self.assertTrue("name" in body)
                        self.assertTrue("mimeType" in body)
                        self.assertTrue("parents" in body)
                        name = body.get("name")
                        mimeType = body.get("mimeType")
                        parents = body.get("parents")

                        r = self.__MakeFilesObject(name, mimeType, parents)
                        self.drive.append(r)
                        return {"id": r["id"]}

                    r3 = MagicMock()
                    p_execute = PropertyMock()
                    p_execute.return_value = ReturnCreateExecute
                    type(r3).execute = p_execute
                    return r3

                p_create = PropertyMock()
                p_create.return_value = ReturnCreate
                type(r2).create = p_create
                
                def ReturnCopy(body, fileId):
                    def ReturnCopyExecute():
                        records = [r for r in self.drive if r["id"] == fileId]
                        self.assertEqual(1, len(records))
                        record = records[0]
                        self.assertTrue("name" in record)
                        self.assertTrue("mimeType" in record)

                        self.assertTrue("parents" in body)
                        parents = body.get("parents")

                        r = self.__MakeFilesObject(record["name"], record["mimeType"], parents)
                        self.drive.append(r)
                        return r["id"]

                    r3 = MagicMock()
                    p_execute = PropertyMock()
                    p_execute.return_value = ReturnCopyExecute
                    type(r3).execute = p_execute
                    return r3

                p_copy = PropertyMock()
                p_copy.return_value = ReturnCopy
                type(r2).copy = p_copy
                
                def ReturnDelete(fileId):
                    def ReturnDeleteExecute():
                        records = [r for r in self.drive if r["id"] == fileId]
                        self.assertEqual(1, len(records))
                        r = records[0]
                        self.drive.remove(r)
                        return r["id"]

                    r3 = MagicMock()
                    p_execute = PropertyMock()
                    p_execute.return_value = ReturnDeleteExecute
                    type(r3).execute = p_execute
                    return r3

                p_delete = PropertyMock()
                p_delete.return_value = ReturnDelete
                type(r2).delete = p_delete
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

            res = GoogleDrive.GoogleDriveDirectoryCopy(SOURCE_FOLDER_NAME, TEST_FOLDER_NAME)
            dest_folderid = GoogleDrive.GetFolderId(service, TEST_FOLDER_NAME)

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
        with ExitStack() as stack:
            mockgdcreds = stack.enter_context(patch("google.oauth2.service_account.Credentials.from_service_account_file"))
            mockgdbuild = stack.enter_context(patch("PictureGathering.GoogleDrive.build"))
            mockgdmediaupload = stack.enter_context(patch("PictureGathering.GoogleDrive.MediaFileUpload"))
            
            mockgdcreds = self.__MakeCredentialsMock(mockgdcreds)
            mockgdbuild = self.__MakeBuildMock(mockgdbuild)
            mockgdmediaupload = self.__MakeMediaUploadMock(mockgdmediaupload)

            service = GoogleDrive.GetAPIService(CREDENTIALS_PATH)

            # 仮想のテスト用フォルダにコピー
            dest_folderid = GoogleDrive.GoogleDriveDirectoryCopy(SOURCE_FOLDER_NAME, TEST_FOLDER_NAME)

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
        with ExitStack() as stack:
            mockgdcreds = stack.enter_context(patch("google.oauth2.service_account.Credentials.from_service_account_file"))
            mockgdbuild = stack.enter_context(patch("PictureGathering.GoogleDrive.build"))
            
            mockgdcreds = self.__MakeCredentialsMock(mockgdcreds)
            mockgdbuild = self.__MakeBuildMock(mockgdbuild)

            service = GoogleDrive.GetAPIService(CREDENTIALS_PATH)

            # 仮想のテスト用フォルダにコピー
            dest_folderid = GoogleDrive.GoogleDriveDirectoryCopy(SOURCE_FOLDER_NAME, TEST_FOLDER_NAME)

            GoogleDrive.GoogleDriveAllDelete(TEST_FOLDER_NAME)

            # 削除確認
            results = service.files().list(q="'{}' in parents".format(dest_folderid)).execute()
            items = results.get("files")

            self.assertEqual([], items)


if __name__ == "__main__":
    if sys.argv:
        del sys.argv[1:]
    unittest.main(warnings="ignore")
