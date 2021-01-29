# coding: utf-8
import glob
import os
import re
import zipfile
from datetime import datetime


def MakeZipFile(target_directory, type_str):
    """保存した画像をzipファイルに固める
    """

    # 対象フォルダ内のzip以外のファイルをzipに固める

    # アーカイブの名前を設定
    target_directory = os.path.abspath(target_directory)
    now = datetime.now()
    date_str = now.strftime("%Y%m%d_%H%M%S")
    type_str = "Fav" if type_str == "Fav" else "RT"
    achive_name = "{}_{}.zip".format(type_str, date_str)
    target_path = os.path.join(target_directory, achive_name)

    # 既にあるzipファイルは削除する
    zipfile_list = [p for p in glob.glob(os.path.join(target_directory, "*.*")) if re.search("^(.*zip).*$", p)]
    for f in zipfile_list:
        os.remove(f)

    # 対象ファイルリストを設定
    # zipファイル以外を対象とする
    target_list = [p for p in glob.glob(os.path.join(target_directory, "*.*")) if re.search("^(?!.*zip).*$", p)]

    # zip圧縮する
    if target_list:
        with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as zfout:
            for f in target_list:
                zfout.write(f, os.path.basename(f))
                os.remove(f)  # アーカイブしたファイルは削除する

    return target_path


if __name__ == "__main__":
    print(MakeZipFile("./archive", "Fav"))
