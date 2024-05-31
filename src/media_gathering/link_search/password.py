from dataclasses import dataclass


@dataclass(frozen=True)
class Password():
    _password: str

    def __post_init__(self) -> None:
        """初期化後処理

        バリデーションのみ
        """
        if not isinstance(self._password, str):
            raise TypeError("password is not string, invalid password.")
        if self._password == "":
            raise ValueError("empty string, invalid password")

    @property
    def password(self) -> str:
        return self._password


if __name__ == "__main__":
    passwords = [
        "パスワード1",
        "",
        -1,
    ]

    for password in passwords:
        try:
            password = Password(password)
            print(password)
        except (ValueError, TypeError) as e:
            print(e.args[0])
