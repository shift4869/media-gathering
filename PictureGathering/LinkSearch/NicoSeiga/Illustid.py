from dataclasses import dataclass


@dataclass(frozen=True)
class Illustid():
    _id: int

    def __post_init__(self) -> None:
        """初期化後処理

        バリデーションのみ
        """
        if not isinstance(self._id, int):
            raise TypeError("id is not int, invalid Illustid.")
        if self._id <= 0:
            raise ValueError("invalid Illustid")

    @property
    def id(self) -> int:
        return self._id


if __name__ == "__main__":
    ids = [
        "作成者1",
        "",
        -1,
    ]

    for id in ids:
        try:
            userid = Illustid(id)
            print(userid)
        except (ValueError, TypeError) as e:
            print(e.args[0])
