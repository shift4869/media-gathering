# coding: utf-8
import re
import zipfile
from datetime import datetime
from pathlib import Path


def MakeZipFile(target_directory: str, type_str: str) -> str:
    """保存した画像をzipファイルに固める
    """

    # 対象フォルダ内のzip以外のファイルをzipに固める

    # アーカイブの名前を設定
    target_sd = Path(target_directory).absolute()
    now = datetime.now()
    date_str = now.strftime("%Y%m%d_%H%M%S")
    type_str = "Fav" if type_str == "Fav" else "RT"
    achive_name = "{}_{}.zip".format(type_str, date_str)
    target_path = target_sd / achive_name

    # 既にあるzipファイルは削除する
    zipfile_list = [p for p in target_sd.glob("**/*") if re.search("^(.*zip).*$", str(p))]
    for f in zipfile_list:
        f.unlink()

    # 対象ファイルリストを設定
    # zipファイル以外、かつ、ファイルサイズが0でないものを対象とする
    target_list = [p for p in target_sd.glob("**/*") if re.search("^(?!.*zip).*$", str(p)) and p.stat().st_size > 0]

    # zip圧縮する
    if target_list:
        with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as zfout:
            for f in target_list:
                zfout.write(f, f.name)
                f.unlink()  # アーカイブしたファイルは削除する

    return str(target_path)


if __name__ == "__main__":
    print(MakeZipFile("./archive", "Fav"))
