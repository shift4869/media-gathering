# coding: utf-8
from datetime import datetime, timedelta, timezone
import os
import time
import warnings

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from apiclient.http import MediaFileUpload


def UploadToGoogleDrive(file_path, credentials_path):
    warnings.filterwarnings("ignore")
    creds = Credentials.from_service_account_file(credentials_path)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    # フォルダID取得
    GOOGLEDRIVE_FOLDER_NAME = "PictureGathering"
    folder_id = ""
    results = service.files().list(q="mimeType='application/vnd.google-apps.folder'").execute()
    items = results.get("files")
    if not items:
        return None
    else:
        for item in items:
            if ("name" in item) and ("id" in item):
                if item["name"] == GOOGLEDRIVE_FOLDER_NAME:
                    folder_id = item["id"]
                    break
    if folder_id == "":
        return None

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
                old_file_id = item["id"]

        if old_file_id != -1:
            results = service.files().delete(fileId=old_file_id).execute()
    
    # 同名ファイルがある場合は削除
    file_name = os.path.basename(file_path)
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

    # アップロードしたファイルはローカルから削除する
    # TODO::アップロード終了を検知する
    # os.remove(file_path)

    return results


def GoogleDriveAllDelete():
    # 全ファイル消す
    creds = Credentials.from_service_account_file('./config/credentials.json')
    service = build('drive', 'v3', credentials=creds)

    # フォルダID取得
    GOOGLEDRIVE_FOLDER_NAME = "PictureGathering"
    folder_id = ""
    results = service.files().list(q="mimeType='application/vnd.google-apps.folder'").execute()
    items = results.get("files")
    if not items:
        return None
    else:
        for item in items:
            if ("name" in item) and ("id" in item):
                if item["name"] == GOOGLEDRIVE_FOLDER_NAME:
                    folder_id = item["id"]
                    break
    if folder_id == "":
        return None

    # 取得
    results = service.files().list().execute()
    items = results.get('files')

    for item in items:
        # 削除（デリート）
        if item["id"] != folder_id:
            f = service.files().delete(fileId=item['id']).execute()
    return 0


def GoogleDriveApiTest():
    creds = Credentials.from_service_account_file('./config/credentials.json')

    service = build('drive', 'v3', credentials=creds)

    # Call the Drive v3 API

    # 作成（アップロード）
    folder_id = ""
    file_metadata = {
        'name': "fw2g.jpg",
        'mimeType': "image/jpeg",
        'parents': [folder_id]
    }
    media = MediaFileUpload("fw2g.jpg",
                            mimetype='image/jpeg',
                            resumable=True)
    service.files().create(body=file_metadata,
                           media_body=media,
                           fields='id').execute()

    # 取得
    results = service.files().list().execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))
            # 削除（デリート）
            if item["id"] != folder_id:
                f = service.files().delete(fileId=item['id']).execute()


if __name__ == '__main__':
    # GoogleDriveAllDelete()
    # UploadToGoogleDrive("D:\\Users\\shift\\Documents\\git\\PictureGathering\\archive\\Fav_20200624_174315.zip", "./config/credentials.json")
    pass
