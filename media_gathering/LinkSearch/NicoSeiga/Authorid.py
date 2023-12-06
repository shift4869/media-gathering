from dataclasses import dataclass


@dataclass(frozen=True)
class Authorid():
    _id: int

    def __post_init__(self) -> None:
        """初期化後処理

        バリデーションのみ
        """
        if not isinstance(self._id, int):
            raise TypeError("id is not int, invalid Authorid.")
        if self._id <= 0:
            raise ValueError("invalid Authorid")

    @property
    def id(self) -> str:
        return self._id


if __name__ == "__main__":
    ids = [
        12345678,
        0,
        -1,
        "",
    ]

    for id_num in ids:
        try:
            authorid = Authorid(id_num)
            print(authorid)
        except (ValueError, TypeError) as e:
            print(e.args[0])
