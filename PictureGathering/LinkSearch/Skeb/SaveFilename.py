# coding: utf-8
import enum
from dataclasses import dataclass

from PictureGathering.LinkSearch.Skeb.Authorname import Authorname
from PictureGathering.LinkSearch.Skeb.Workid import Workid


@dataclass(frozen=True)
class Extension(enum.Enum):
    UNKNOWN: str = ".unknown"
    WEBP: str = ".webp"
    PNG: str = ".png"
    MP4: str = ".mp4"
    TXT: str = ".txt"


@dataclass(frozen=True)
class SaveFilename():
    _name: str

    # SINGLE_PATTERN = r"^(.+?)_([0-9]{3})\.(.+?)$"
    # SEVERAL_PATTERN = r"^(.+?)_([0-9]{3})_([0-9]{3})\.(.+?)$"

    def __post_init__(self) -> None:
        self._is_valid()

    def _is_valid(self) -> bool:
        if not isinstance(self._name, str):
            raise TypeError("name is not string, invalid SaveFilename.")

        # TODO::正規表現でファイル名として受け付けるパターンを記述しようとしたが想定どおりいかなかった
        # f1 = re.search(SaveFilename.SINGLE_PATTERN, self.name) is not None
        # f2 = re.search(SaveFilename.SEVERAL_PATTERN, self.name) is not None
        # if not (f1 or f2):
        #     raise ValueError("invalid SaveFilename.")
        return True

    # def _is_single(self):
    #     return re.search(SaveFilename.SINGLE_PATTERN, self.name) is not None

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def create(cls, author_name: Authorname, work_id: Workid, index: int = -1, extension: Extension = Extension.UNKNOWN) -> "SaveFilename":
        if not isinstance(author_name, Authorname):
            raise TypeError("author_name is not Authorname, invalid SaveFilename.")
        if not isinstance(work_id, Workid):
            raise TypeError("work_id is not Illustid, invalid SaveFilename.")
        if not isinstance(index, int):
            raise TypeError("index is not int, invalid SaveFilename.")
        if not isinstance(extension, Extension):
            raise TypeError("extension is not Extension, invalid SaveFilename.")

        filename = ""
        if index <= -1:
            # 連番なし
            filename = f"{author_name.name}_{work_id.id:03}{extension.value}"
        else:
            # 連番あり
            filename = f"{author_name.name}_{work_id.id:03}_{index:03}{extension.value}"
        return SaveFilename(filename)


if __name__ == "__main__":
    names = [
        "作成者1_001.png",
        "作成者1_001_000.png",
        "作成者2?****//_001.png",
        "作成者2?****//_001_000.png",
        "作成者3😀****//_001.png",
        "作成者3😀_001_000.png",
        "",
        -1,
    ]

    for name in names:
        try:
            save_filename = SaveFilename(name)
            print(save_filename.name)
        except (ValueError, TypeError) as e:
            print(e.args[0])
