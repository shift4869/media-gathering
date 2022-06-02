# coding: utf-8
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class IllustConvertor():
    _source: Path
    _extension: str = ".png"

    def convert(self) -> Path:
        src_path = self._source
        img = Image.open(src_path).convert("RGB")
        dst_path = src_path.with_suffix(self._extension)
        img.save(dst_path)

        src_path.unlink(missing_ok=True)
        if not dst_path.is_file():
            raise ValueError("IllustConvertor convert failed.")

        return dst_path


if __name__ == "__main__":
    names = [
        "作品名1",
        "作品名2?****//",
        "作品名3😀",
        "",
        -1,
    ]

    for name in names:
        try:
            username = SkebSourceURLList(name)
            print(username.name)
        except (ValueError, TypeError) as e:
            print(e.args[0])
