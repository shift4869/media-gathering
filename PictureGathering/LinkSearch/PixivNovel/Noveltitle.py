# coding: utf-8
from dataclasses import dataclass
import re
from typing import ClassVar

import emoji


@dataclass(frozen=True)
class Noveltitle():
    _original_title: str
    _title: ClassVar[str]

    def __post_init__(self) -> None:
        """初期化後処理

        サニタイズを行う
        TODO::サニタイズを厳密に行う
        """
        if not isinstance(self._original_title, str):
            raise TypeError("title is not string, invalid Noveltitle.")
        if self._original_title == "":
            raise ValueError("title is empty, invalid Noveltitle")

        regex = re.compile(r'[\\/:*?"<>|]')
        trimed_title = regex.sub("", self._original_title)
        non_emoji_title = emoji.get_emoji_regexp().sub("", trimed_title)
        object.__setattr__(self, "_title", non_emoji_title)

    @property
    def title(self) -> str:
        return self._title


if __name__ == "__main__":
    titles = [
        "作品名1",
        "作品名2?****//",
        "作品名3😀",
        "",
        -1,
    ]

    for title in titles:
        try:
            novel_title = Noveltitle(title)
            print(novel_title.title)
        except (ValueError, TypeError) as e:
            print(e.args[0])
