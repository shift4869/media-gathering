# coding: utf-8
import os.path
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from apiclient.http import MediaFileUpload


def GoogleDriveApiTest():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = Credentials.from_service_account_file('./config/credentials.json')

    service = build('drive', 'v3', credentials=creds)

    # Call the Drive v3 API

    # 作成（アップロード）
    folder_id = "1AnmJlnOw2tyO3NuGECUTyzzpY9-_56y3"
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
    main()
