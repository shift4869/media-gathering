# coding: utf-8
from dataclasses import dataclass


@dataclass(frozen=True)
class RetweetInfo():
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

    @classmethod
    def create(cls, dict: dict) -> "RetweetInfo":
        match dict:
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
                return cls(media_filename,
                           media_url,
                           media_thumbnail_url,
                           tweet_id,
                           tweet_url,
                           created_at,
                           user_id,
                           user_name,
                           screan_name,
                           tweet_text,
                           tweet_via)
            case _:
                raise ValueError("LikeTweet create failed.")

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


if __name__ == "__main__":
    pass
