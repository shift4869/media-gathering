# coding: utf-8
import pprint
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LocalStorage():
    """Twitterセッションで使うローカルストレージ
    """
    _local_storage: list[str]

    # ローカルストレージファイルパス
    TWITTER_LOCAL_STORAGE_PATH = "./config/twitter_localstorage.ini"

    def __post_init__(self) -> None:
        self._is_valid_local_storage()

    def _is_valid_local_storage(self) -> bool:
        # _local_storage = [] は許容する
        if (not self._local_storage) and (self._local_storage != []):
            raise ValueError("LocalStorage is None.")
        if not isinstance(self._local_storage, list):
            raise TypeError("local_storage is not list, invalid LocalStorage.")
        return True

    @property
    def local_storage(self) -> list[str]:
        return self._local_storage

    @classmethod
    def validate_line(cls, line) -> bool:
        pattern = "^(.*?) : (.*)$"
        if re.findall(pattern, line):
            return True
        return False

    @classmethod
    def load(cls) -> list[str]:
        # アクセスに使用するローカルストレージファイル置き場
        slsp = Path(LocalStorage.TWITTER_LOCAL_STORAGE_PATH)
        if not slsp.exists():
            # ローカルストレージファイルが存在しない = 初回起動
            raise FileNotFoundError

        # ローカルストレージを読み込む
        local_storage = []
        with slsp.open(mode="r") as fin:
            for line in fin:
                if not cls.validate_line(line):
                    break
                local_storage.append(line)
        return local_storage

    @classmethod
    def save(cls, local_storage: list[str]) -> list[str]:
        # if not local_storage:
        #     raise ValueError("local_storage is empty.")
        if not isinstance(local_storage, list):
            raise TypeError("local_storage is not list.")
        # if not isinstance(local_storage[0], str):
        #     raise TypeError("local_storage is not list[str].")

        # ローカルストレージ情報を保存
        slsp = Path(cls.TWITTER_LOCAL_STORAGE_PATH)
        with slsp.open("w") as fout:
            for line in local_storage:
                if cls.validate_line(line):
                    fout.write(line + "\n")
                else:
                    raise ValueError("local_storage format error.")

        return local_storage

    @classmethod
    def create(cls) -> "LocalStorage":
        return cls(cls.load())


if __name__ == "__main__":
    try:
        ls = LocalStorage.create()
        LocalStorage.save(ls.local_storage)
        pprint.pprint(ls.local_storage)
    except Exception as e:
        pprint.pprint(e)
