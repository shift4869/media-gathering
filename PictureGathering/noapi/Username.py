# coding: utf-8
from dataclasses import dataclass


@dataclass(frozen=True)
class Username():
    _name: str

    def __post_init__(self) -> None:
        """初期化後処理
        """
        if not isinstance(self._name, str):
            raise TypeError("name is not string, invalid Username.")
        if self._name == "":
            raise ValueError("empty string, invalid Username.")

        # ツイッターのスクリーンネームを想定しているため
        # @で始まるならエラー
        if self._name.startswith("@"):
            raise ValueError("Username start with '@' string, shuoud exclude '@' Username.")

    @property
    def name(self) -> str:
        return self._name


if __name__ == "__main__":
    names = [
        "test_user",
        "@invalid_user",
        "",
        -1,
    ]

    for name in names:
        try:
            username = Username(name)
            print(username)
        except (ValueError, TypeError) as e:
            print(e.args[0])
