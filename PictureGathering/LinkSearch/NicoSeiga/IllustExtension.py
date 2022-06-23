# coding: utf-8
import enum
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Extension(enum.Enum):
    JPG = ".jpg"
    PNG = ".png"
    GIF = ".gif"


@dataclass(frozen=True)
class IllustExtension():
    """画像バイナリから拡張子を判別するクラス
    """
    _extension: Extension

    def __post_init__(self) -> None:
        """初期化後処理

        バリデーションのみ
        """
        if not isinstance(self._extension, Extension):
            raise TypeError("_extension is not Extension, invalid IllustExtension.")

    @property
    def extension(self) -> str:
        """拡張子を返す
        """
        return str(self._extension.value)

    @classmethod
    def create(self, data: bytes) -> "IllustExtension":
        """画像バイナリから拡張子を判別し、IllustExtensionインスタンスを生成する
        """
        ext = ""

        if not isinstance(data, bytes):
            raise TypeError("data is not bytes, invalid IllustExtension.")

        # プリフィックスを得るのに短すぎるbyte列の場合はエラー
        if len(data) < 8:
            raise ValueError("data is too short, invalid IllustExtension")

        # 拡張子判別
        if bool(re.search(b"^\xff\xd8", data[:2])):
            # jpgは FF D8 で始まる
            ext = Extension.JPG
        elif bool(re.search(b"^\x89\x50\x4e\x47\x0d\x0a\x1a\x0a", data[:8])):
            # pngは 89 50 4E 47 0D 0A 1A 0A で始まる
            ext = Extension.PNG
        elif bool(re.search(b"^\x47\x49\x46\x38", data[:4])):
            # gifは 47 49 46 38 で始まる
            ext = Extension.GIF
        return IllustExtension(ext)


if __name__ == "__main__":
    datas = [
        b"\xff\xd8\xff\xff\xff\xff\xff\xff",
        b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a",
        b"\x47\x49\x46\x38\xff\xff\xff\xff",
        b"\xff\xff\xff\xff\xff\xff\xff\xff",
        b"\xff\xff\xff\xff",
        -1,
    ]

    for data in datas:
        try:
            ext = IllustExtension.create(data)
            print(ext.extension)
        except (ValueError, TypeError) as e:
            print(e.args[0])
