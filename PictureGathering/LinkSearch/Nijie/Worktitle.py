# coding: utf-8
from dataclasses import dataclass


@dataclass(frozen=True)
class Worktitle():
    _title: str

    def __post_init__(self) -> None:
        """初期化後処理

        バリデーションのみ
        """
        if not isinstance(self._title, str):
            raise TypeError("name is not string, invalid Worktitle.")
        if self._title == "":
            raise ValueError("empty string, invalid Worktitle")

    @property
    def title(self) -> str:
        return self._title


if __name__ == "__main__":
    titles = [
        "作成者1",
        "",
        -1,
    ]

    for title in titles:
        try:
            work_title = Worktitle(title)
            print(work_title)
        except (ValueError, TypeError) as e:
            print(e.args[0])
