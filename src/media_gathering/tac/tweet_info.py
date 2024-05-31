from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True)
class TweetInfo:
    media_filename: str
    media_url: str
    media_thumbnail_url: str
    tweet_id: str
    tweet_url: str
    created_at: str
    user_id: str
    user_name: str
    screan_name: str
    tweet_text: str
    tweet_via: str

    def __post_init__(self) -> None:
        if not isinstance(self.media_filename, str):
            raise TypeError("media_filename must be str.")
        if not isinstance(self.media_url, str):
            raise TypeError("media_url must be str.")
        if not isinstance(self.media_thumbnail_url, str):
            raise TypeError("media_thumbnail_url must be str.")
        if not isinstance(self.tweet_id, str):
            raise TypeError("tweet_id must be str.")
        if not isinstance(self.tweet_url, str):
            raise TypeError("tweet_url must be str.")
        if not isinstance(self.created_at, str):
            raise TypeError("created_at must be str.")
        if not isinstance(self.user_id, str):
            raise TypeError("user_id must be str.")
        if not isinstance(self.user_name, str):
            raise TypeError("user_name must be str.")
        if not isinstance(self.screan_name, str):
            raise TypeError("screan_name must be str.")
        if not isinstance(self.tweet_text, str):
            raise TypeError("tweet_text must be str.")
        if not isinstance(self.tweet_via, str):
            raise TypeError("tweet_via must be str.")

    def to_dict(self) -> dict:
        return {
            "media_filename": self.media_filename,
            "media_url": self.media_url,
            "media_thumbnail_url": self.media_thumbnail_url,
            "tweet_id": self.tweet_id,
            "tweet_url": self.tweet_url,
            "created_at": self.created_at,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "screan_name": self.screan_name,
            "tweet_text": self.tweet_text,
            "tweet_via": self.tweet_via,
        }

    @classmethod
    def create(cls, arg_dict: dict) -> Self:
        match arg_dict:
            case {
                "media_filename": media_filename,
                "media_url": media_url,
                "media_thumbnail_url": media_thumbnail_url,
                "tweet_id": tweet_id,
                "tweet_url": tweet_url,
                "created_at": created_at,
                "user_id": user_id,
                "user_name": user_name,
                "screan_name": screan_name,
                "tweet_text": tweet_text,
                "tweet_via": tweet_via,
            }:
                return cls(
                    media_filename,
                    media_url,
                    media_thumbnail_url,
                    tweet_id,
                    tweet_url,
                    created_at,
                    user_id,
                    user_name,
                    screan_name,
                    tweet_text,
                    tweet_via,
                )
            case _:
                raise ValueError("TweetInfo instance create failed.")


if __name__ == "__main__":
    params = {
        "media_filename": "",
        "media_url": "media_url",
        "media_thumbnail_url": "media_thumbnail_url",
        "tweet_id": "tweet_id",
        "tweet_url": "tweet_url",
        "created_at": "created_at",
        "user_id": "user_id",
        "user_name": "user_name",
        "screan_name": "screan_name",
        "tweet_text": "tweet_text",
        "tweet_via": "tweet_via",
    }
    tweet_info = TweetInfo.create(params)
    print(tweet_info)
