from dataclasses import dataclass


@dataclass(frozen=True)
class Novelid():
    _id: int

    def __post_init__(self) -> None:
        """初期化後処理

        バリデーションのみ
        """
        if not isinstance(self._id, int):
            raise TypeError("id is not int, invalid Novelid.")
        if self._id <= 0:
            raise ValueError("invalid Novelid")

    @property
    def id(self) -> int:
        return self._id


if __name__ == "__main__":
    ids = [
        12345678,
        0,
        -1,
        "",
    ]

    for id in ids:
        try:
            novel_id = Novelid(id)
            print(novel_id)
        except (ValueError, TypeError) as e:
            print(e.args[0])
