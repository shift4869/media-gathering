# coding: utf-8
from dataclasses import dataclass


@dataclass(frozen=True)
class Illustname():
    _name: str

    def __post_init__(self) -> None:
        """初期化後処理

        バリデーションのみ
        """
        if not isinstance(self._name, str):
            raise TypeError("name is not string, invalid Illustname.")
        if self._name == "":
            raise ValueError("empty string, invalid Illustname")

    @property
    def name(self) -> str:
        return self._name


if __name__ == "__main__":
    names = [
        "作成者1",
        "",
        -1,
    ]

    for name in names:
        try:
            username = Illustname(name)
            print(username)
        except (ValueError, TypeError) as e:
            print(e.args[0])
