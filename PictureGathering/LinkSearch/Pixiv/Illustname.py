# coding: utf-8
from dataclasses import dataclass
import re
from typing import ClassVar

import emoji


@dataclass(frozen=True)
class Illustname():
    _original_name: str
    _name: ClassVar[str]

    def __post_init__(self) -> None:
        """初期化後処理

        サニタイズを行う
        TODO::サニタイズを厳密に行う
        """
        if not isinstance(self._original_name, str):
            raise TypeError("name is not string, invalid Authorname.")
        if self._original_name == "":
            raise ValueError("empty string, invalid Authorname")

        regex = re.compile(r'[\\/:*?"<>|]')
        trimed_name = regex.sub("", self._original_name)
        non_emoji_name = emoji.get_emoji_regexp().sub("", trimed_name)
        object.__setattr__(self, "_name", non_emoji_name)

    @property
    def name(self) -> str:
        return self._name


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
            username = Illustname(name)
            print(username.name)
        except (ValueError, TypeError) as e:
            print(e.args[0])
