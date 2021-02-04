# coding: utf-8
import os
import time
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from apiclient.http import MediaFileUpload


def GetAPIService(credentials_path: str):
    """GoogleDriveのAPI操作サービスクライアントオブジェクト取得
    
    Args:
        credentials_path (str): credentials.jsonファイルへのパス

    Returns:
        service : GoogleDriveのAPI操作サービスクライアントオブジェクト
    """
    cred_path = Path(credentials_path)
    if not cred_path.is_file():
        return None
    creds = Credentials.from_service_account_file(str(cred_path))
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return service


def GetFolderId(service, folder_name: str) -> str:
    """フォルダID取得
    
    Args:
        service : GoogleDriveのAPI操作サービスクライアントオブジェクト
        folder_name (str): 取得フォルダ名

    Returns:
        str: 正常時folder_nameのフォルダID、存在しないまたはエラー時空文字列
    """
    folder_id = ""
    results = service.files().list(q="mimeType='application/vnd.google-apps.folder'").execute()
    items = results.get("files")
    for item in items:
        if ("name" in item) and ("id" in item):
            if item["name"] == folder_name:
                folder_id = item["id"]
                break
    return folder_id


def UploadToGoogleDrive(file_path: str, credentials_path: str, folder_name: str = "PictureGathering"):
    """GoogleDriveへファイルをアップロードする
    
    Args:
        file_path (str) : GoogleDriveへアップロードするファイルへのパス
        credentials_path (str): credentials.jsonファイルへのパス
        folder_name (str): アップロード先のGoogleDriveのフォルダ

    Returns:
        Files: アップロードしたファイルのファイルリソースオブジェクト
    """
    warnings.filterwarnings("ignore")
    service = GetAPIService(credentials_path)

    # フォルダID取得
    folder_id = GetFolderId(service, folder_name)

    # 指定ファイル数以上存在する場合、一番古いファイルを削除する（ローテート）
    MAX_FILE_NUM = 10
    results = service.files().list(q="mimeType='application/x-zip-compressed' and '{}' in parents".format(folder_id),
                                   fields="files(id,name,mimeType,trashed,parents,createdTime)").execute()
    items = results.get("files")
    if len(items) > MAX_FILE_NUM:
        # ローテート
        old_create_time = datetime.now()
        old_file_id = -1
        td_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        for item in items:
            created_datetime = datetime.strptime(item["createdTime"], td_format) + timedelta(hours=9)
            if old_create_time > created_datetime:
                old_create_time = created_datetime
                old_file_id = item["id"]

        if old_file_id != -1:
            results = service.files().delete(fileId=old_file_id).execute()
    
    # 同名ファイルがある場合は削除
    file_name = Path(file_path).name
    results = service.files().list(q="name='{}' and mimeType='application/x-zip-compressed' and '{}' in parents".format(file_name, folder_id),
                                   fields="files(id,name,mimeType,trashed,parents,createdTime)").execute()
    items = results.get("files")
    if items:
        for item in items:
            results = service.files().delete(fileId=item["id"]).execute()

    # ファイルアップロード
    file_metadata = {
        "name": file_name,
        "mimeType": "application/x-zip-compressed",
        "parents": [folder_id]
    }
    media = MediaFileUpload(file_path,
                            mimetype="application/x-zip-compressed",
                            resumable=True)
    results = service.files().create(body=file_metadata,
                                     media_body=media,
                                     fields="id").execute()

    # TODO::アップロード終了を検知する

    return results


def GoogleDriveAllDelete(folder_name: str = "PictureGathering"):
    """指定フォルダ内のファイルを全て削除する

    Args:
        folder_name (str): 対象フォルダ名

    Returns:
        int: 成功時0
    """
    # 全ファイル消す
    service = GetAPIService("./config/credentials.json")

    # フォルダID取得
    folder_id = GetFolderId(service, folder_name)

    # 取得
    results = service.files().list(q="'{}' in parents".format(folder_id)).execute()
    items = results.get("files")

    for item in items:
        # 削除（デリート）
        if item["id"] != folder_id:
            f = service.files().delete(fileId=item["id"]).execute()
    return 0


def GoogleDriveDirectoryCopy(src_foldername: str, dest_foldername: str) -> str:
    """GoogleDrive内のディレクトリをコピーする

    Notes:
        権限の都合上、{src_foldername}内に{dest_foldername}を作成する。
        {src_foldername}内のすべてのファイルを、./{src_foldername}/{dest_foldername}/ 配下にコピーする。

    Args:
        src_foldername (str): コピー元ファイルが存在するディレクトリ名
        dest_foldername (str): コピー先ディレクトリ名（存在しない場合作成される）

    Returns:
        str: 正常時{dest_foldername}のフォルダID、エラー時空文字列
    """
    service = GetAPIService("./config/credentials.json")
    if not service:
        return ""

    # src_foldernameのフォルダID取得
    src_folderid = GetFolderId(service, src_foldername)

    # dest_foldernameのフォルダID取得（存在しない場合は空文字列）
    dest_folderid = GetFolderId(service, dest_foldername)

    # dest_foldernameが存在していない場合作成
    if dest_folderid == "":
        file_metadata = {
            "name": dest_foldername,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [src_folderid]
        }
        service.files().create(body=file_metadata,
                               fields="id").execute()
        dest_folderid = GetFolderId(service, dest_foldername)
        if dest_folderid == "":
            return ""

    # src_foldername内のファイルを取得
    results = service.files().list(q="mimeType!='application/vnd.google-apps.folder'",
                                   fields="files(id,name,mimeType,trashed,parents,createdTime)").execute()
    items = results.get("files", [])

    for item in items:
        file_metadata = {
            "parents": [dest_folderid]
        }
        service.files().copy(body=file_metadata, fileId=item["id"]).execute()
    return dest_folderid


if __name__ == "__main__":
    # GoogleDriveAllDelete()
    # UploadToGoogleDrive("D:\\Users\\shift\\Documents\\git\\PictureGathering\\archive\\Fav_20200624_174315.zip", "./config/credentials.json")
    # GoogleDriveDirectoryCopy("PictureGathering", "test")
    pass
