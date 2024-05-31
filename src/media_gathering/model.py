from typing import Self

from sqlalchemy import BLOB, INTEGER, Boolean, Column, Integer, String, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, deferred

Base = declarative_base()


class Favorite(Base):
    """お気に入りツイートモデル

    [id] INTEGER,
    [is_exist_saved_file] BOOLEAN DEFAULT 'True',
    [img_filename] TEXT NOT NULL UNIQUE,
    [url] TEXT NOT NULL UNIQUE,
    [url_thumbnail] TEXT NOT NULL UNIQUE,
    [tweet_id] TEXT NOT NULL,
    [tweet_url] TEXT NOT NULL,
    [created_at] TEXT,
    [user_id] TEXT NOT NULL,
    [user_name] TEXT NOT NULL,
    [screan_name] TEXT NOT NULL,
    [tweet_text] TEXT,
    [tweet_via] TEXT,
    [saved_localpath] TEXT,
    [saved_created_at] TEXT,
    [media_size] INTEGER,
    [media_blob] BLOB,
    PRIMARY KEY([id])
    """

    __tablename__ = "Favorite"

    id = Column(Integer, primary_key=True, autoincrement=True)
    is_exist_saved_file = Column(Boolean, server_default=text("True"))
    img_filename = Column(String(256), nullable=False, unique=True)
    url = Column(String(512), nullable=False, unique=True)
    url_thumbnail = Column(String(512), nullable=False, unique=True)
    tweet_id = Column(String(256), nullable=False)
    tweet_url = Column(String(512), nullable=False)
    created_at = Column(String(32))
    user_id = Column(String(256), nullable=False)
    user_name = Column(String(256), nullable=False)
    screan_name = Column(String(256), nullable=False)
    tweet_text = Column(String(512))
    tweet_via = Column(String(512))
    saved_localpath = Column(String(256))
    saved_created_at = Column(String(32))
    media_size = Column(INTEGER())
    media_blob = deferred(Column(BLOB()))

    def __init__(
        self,
        is_exist_saved_file: bool,
        img_filename: str,
        url: str,
        url_thumbnail: str,
        tweet_id: str,
        tweet_url: str,
        created_at: str,
        user_id: str,
        user_name: str,
        screan_name: str,
        tweet_text: str,
        tweet_via: str,
        saved_localpath: str,
        saved_created_at: str,
        media_size: int,
        media_blob: bytes | None,
    ) -> None:
        if not isinstance(is_exist_saved_file, bool):
            raise TypeError("is_exist_saved_file must be bool.")
        if not isinstance(img_filename, str):
            raise TypeError("img_filename must be str.")
        if not isinstance(url, str):
            raise TypeError("url must be str.")
        if not isinstance(url_thumbnail, str):
            raise TypeError("url_thumbnail must be str.")
        if not isinstance(tweet_id, str):
            raise TypeError("tweet_id must be str.")
        if not isinstance(tweet_url, str):
            raise TypeError("tweet_url must be str.")
        if not isinstance(created_at, str):
            raise TypeError("created_at must be str.")
        if not isinstance(user_id, str):
            raise TypeError("user_id must be str.")
        if not isinstance(user_name, str):
            raise TypeError("user_name must be str.")
        if not isinstance(screan_name, str):
            raise TypeError("screan_name must be str.")
        if not isinstance(tweet_text, str):
            raise TypeError("tweet_text must be str.")
        if not isinstance(tweet_via, str):
            raise TypeError("tweet_via must be str.")
        if not isinstance(saved_localpath, str):
            raise TypeError("saved_localpath must be str.")
        if not isinstance(saved_created_at, str):
            raise TypeError("saved_created_at must be str.")
        if not isinstance(media_size, int):
            raise TypeError("media_size must be int.")
        if media_blob and not isinstance(media_blob, bytes):
            raise TypeError("media_blob must be none or bytes.")

        if media_size <= 0:
            raise ValueError("media_size must be 0 < media_size.")

        self.is_exist_saved_file = is_exist_saved_file
        self.img_filename = img_filename
        self.url = url
        self.url_thumbnail = url_thumbnail
        self.tweet_id = tweet_id
        self.tweet_url = tweet_url
        self.created_at = created_at
        self.user_id = user_id
        self.user_name = user_name
        self.screan_name = screan_name
        self.tweet_text = tweet_text
        self.tweet_via = tweet_via
        self.saved_localpath = saved_localpath
        self.saved_created_at = saved_created_at
        self.media_size = media_size
        self.media_blob = media_blob

    def __repr__(self) -> str:
        columns = ", ".join([f"{k}={v}" for k, v in self.__dict__.items() if k[0] != "_"])
        return f"<{self.__class__.__name__}({columns})>"

    def __eq__(self, other: Self) -> bool:
        return isinstance(other, Favorite) and other.img_filename == self.img_filename

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "is_exist_saved_file": self.is_exist_saved_file,
            "img_filename": self.img_filename,
            "url": self.url,
            "url_thumbnail": self.url_thumbnail,
            "tweet_id": self.tweet_id,
            "tweet_url": self.tweet_url,
            "created_at": self.created_at,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "screan_name": self.screan_name,
            "tweet_text": self.tweet_text,
            "tweet_via": self.tweet_via,
            "saved_localpath": self.saved_localpath,
            "saved_created_at": self.saved_created_at,
            "media_size": self.media_size,
            "media_blob": self.media_blob,
        }

    @classmethod
    def create(cls, arg_dict: dict) -> Self:
        match arg_dict:
            case {
                "is_exist_saved_file": is_exist_saved_file,
                "img_filename": img_filename,
                "url": url,
                "url_thumbnail": url_thumbnail,
                "tweet_id": tweet_id,
                "tweet_url": tweet_url,
                "created_at": created_at,
                "user_id": user_id,
                "user_name": user_name,
                "screan_name": screan_name,
                "tweet_text": tweet_text,
                "tweet_via": tweet_via,
                "saved_localpath": saved_localpath,
                "saved_created_at": saved_created_at,
                "media_size": media_size,
                "media_blob": media_blob,
            }:
                return cls(
                    is_exist_saved_file,
                    img_filename,
                    url,
                    url_thumbnail,
                    tweet_id,
                    tweet_url,
                    created_at,
                    user_id,
                    user_name,
                    screan_name,
                    tweet_text,
                    tweet_via,
                    saved_localpath,
                    saved_created_at,
                    media_size,
                    media_blob,
                )
            case _:
                raise ValueError("Favorite create failed.")


class Retweet(Base):
    """リツイートツイートモデル

    [id] INTEGER,
    [is_exist_saved_file] BOOLEAN DEFAULT 'True',
    [img_filename] TEXT NOT NULL UNIQUE,
    [url] TEXT NOT NULL UNIQUE,
    [url_thumbnail] TEXT NOT NULL UNIQUE,
    [tweet_id] TEXT NOT NULL,
    [tweet_url] TEXT NOT NULL,
    [created_at] TEXT,
    [user_id] TEXT NOT NULL,
    [user_name] TEXT NOT NULL,
    [screan_name] TEXT NOT NULL,
    [tweet_text] TEXT,
    [tweet_via] TEXT,
    [saved_localpath] TEXT,
    [saved_created_at] TEXT,
    PRIMARY KEY([id])
    """

    __tablename__ = "Retweet"

    id = Column(Integer, primary_key=True)
    is_exist_saved_file = Column(Boolean, server_default=text("True"))
    img_filename = Column(String(256), nullable=False, unique=True)
    url = Column(String(512), nullable=False, unique=True)
    url_thumbnail = Column(String(512), nullable=False, unique=True)
    tweet_id = Column(String(256), nullable=False)
    tweet_url = Column(String(512), nullable=False)
    created_at = Column(String(32))
    user_id = Column(String(256), nullable=False)
    user_name = Column(String(256), nullable=False)
    screan_name = Column(String(256), nullable=False)
    tweet_text = Column(String(512))
    tweet_via = Column(String(512))
    saved_localpath = Column(String(256))
    saved_created_at = Column(String(32))
    media_size = Column(INTEGER())
    media_blob = deferred(Column(BLOB()))

    def __init__(
        self,
        is_exist_saved_file: bool,
        img_filename: str,
        url: str,
        url_thumbnail: str,
        tweet_id: str,
        tweet_url: str,
        created_at: str,
        user_id: str,
        user_name: str,
        screan_name: str,
        tweet_text: str,
        tweet_via: str,
        saved_localpath: str,
        saved_created_at: str,
        media_size: int,
        media_blob: bytes | None,
    ) -> None:
        if not isinstance(is_exist_saved_file, bool):
            raise TypeError("is_exist_saved_file must be bool.")
        if not isinstance(img_filename, str):
            raise TypeError("img_filename must be str.")
        if not isinstance(url, str):
            raise TypeError("url must be str.")
        if not isinstance(url_thumbnail, str):
            raise TypeError("url_thumbnail must be str.")
        if not isinstance(tweet_id, str):
            raise TypeError("tweet_id must be str.")
        if not isinstance(tweet_url, str):
            raise TypeError("tweet_url must be str.")
        if not isinstance(created_at, str):
            raise TypeError("created_at must be str.")
        if not isinstance(user_id, str):
            raise TypeError("user_id must be str.")
        if not isinstance(user_name, str):
            raise TypeError("user_name must be str.")
        if not isinstance(screan_name, str):
            raise TypeError("screan_name must be str.")
        if not isinstance(tweet_text, str):
            raise TypeError("tweet_text must be str.")
        if not isinstance(tweet_via, str):
            raise TypeError("tweet_via must be str.")
        if not isinstance(saved_localpath, str):
            raise TypeError("saved_localpath must be str.")
        if not isinstance(saved_created_at, str):
            raise TypeError("saved_created_at must be str.")
        if not isinstance(media_size, int):
            raise TypeError("media_size must be int.")
        if media_blob and not isinstance(media_blob, bytes):
            raise TypeError("media_blob must be none or bytes.")

        if media_size <= 0:
            raise ValueError("media_size must be 0 < media_size.")

        self.is_exist_saved_file = is_exist_saved_file
        self.img_filename = img_filename
        self.url = url
        self.url_thumbnail = url_thumbnail
        self.tweet_id = tweet_id
        self.tweet_url = tweet_url
        self.created_at = created_at
        self.user_id = user_id
        self.user_name = user_name
        self.screan_name = screan_name
        self.tweet_text = tweet_text
        self.tweet_via = tweet_via
        self.saved_localpath = saved_localpath
        self.saved_created_at = saved_created_at
        self.media_size = media_size
        self.media_blob = media_blob

    def __repr__(self) -> str:
        columns = ", ".join([f"{k}={v}" for k, v in self.__dict__.items() if k[0] != "_"])
        return f"<{self.__class__.__name__}({columns})>"

    def __eq__(self, other: Self) -> bool:
        return isinstance(other, Retweet) and other.img_filename == self.img_filename

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "is_exist_saved_file": self.is_exist_saved_file,
            "img_filename": self.img_filename,
            "url": self.url,
            "url_thumbnail": self.url_thumbnail,
            "tweet_id": self.tweet_id,
            "tweet_url": self.tweet_url,
            "created_at": self.created_at,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "screan_name": self.screan_name,
            "tweet_text": self.tweet_text,
            "tweet_via": self.tweet_via,
            "saved_localpath": self.saved_localpath,
            "saved_created_at": self.saved_created_at,
            "media_size": self.media_size,
            "media_blob": self.media_blob,
        }

    @classmethod
    def create(cls, arg_dict: dict) -> Self:
        match arg_dict:
            case {
                "is_exist_saved_file": is_exist_saved_file,
                "img_filename": img_filename,
                "url": url,
                "url_thumbnail": url_thumbnail,
                "tweet_id": tweet_id,
                "tweet_url": tweet_url,
                "created_at": created_at,
                "user_id": user_id,
                "user_name": user_name,
                "screan_name": screan_name,
                "tweet_text": tweet_text,
                "tweet_via": tweet_via,
                "saved_localpath": saved_localpath,
                "saved_created_at": saved_created_at,
                "media_size": media_size,
                "media_blob": media_blob,
            }:
                return cls(
                    is_exist_saved_file,
                    img_filename,
                    url,
                    url_thumbnail,
                    tweet_id,
                    tweet_url,
                    created_at,
                    user_id,
                    user_name,
                    screan_name,
                    tweet_text,
                    tweet_via,
                    saved_localpath,
                    saved_created_at,
                    media_size,
                    media_blob,
                )
            case _:
                raise ValueError("Retweet create failed.")


class ExternalLink(Base):
    """外部リンクモデル

    [id] INTEGER,
    [external_link_url] TEXT NOT NULL,
    [tweet_id] TEXT NOT NULL,
    [tweet_url] TEXT NOT NULL,
    [created_at] TEXT,
    [user_id] TEXT NOT NULL,
    [user_name] TEXT NOT NULL,
    [screan_name] TEXT NOT NULL,
    [tweet_text] TEXT,
    [tweet_via] TEXT,
    [saved_created_at] TEXT,
    [link_type] TEXT,
    PRIMARY KEY([id])
    """

    __tablename__ = "ExternalLink"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_link_url = Column(String(512), nullable=False)
    tweet_id = Column(String(256), nullable=False)
    tweet_url = Column(String(512), nullable=False)
    created_at = Column(String(32))
    user_id = Column(String(256), nullable=False)
    user_name = Column(String(256), nullable=False)
    screan_name = Column(String(256), nullable=False)
    tweet_text = Column(String(512))
    tweet_via = Column(String(512))
    saved_created_at = Column(String(32))
    link_type = Column(String(256))

    def __init__(
        self,
        external_link_url: str,
        tweet_id: str,
        tweet_url: str,
        created_at: str,
        user_id: str,
        user_name: str,
        screan_name: str,
        tweet_text: str,
        tweet_via: str,
        saved_created_at: str,
        link_type: str,
    ):
        if not isinstance(external_link_url, str):
            raise TypeError("external_link_url must be str.")
        if not isinstance(tweet_id, str):
            raise TypeError("tweet_id must be str.")
        if not isinstance(tweet_url, str):
            raise TypeError("tweet_url must be str.")
        if not isinstance(created_at, str):
            raise TypeError("created_at must be str.")
        if not isinstance(user_id, str):
            raise TypeError("user_id must be str.")
        if not isinstance(user_name, str):
            raise TypeError("user_name must be str.")
        if not isinstance(screan_name, str):
            raise TypeError("screan_name must be str.")
        if not isinstance(tweet_text, str):
            raise TypeError("tweet_text must be str.")
        if not isinstance(tweet_via, str):
            raise TypeError("tweet_via must be str.")
        if not isinstance(saved_created_at, str):
            raise TypeError("saved_created_at must be str.")
        if not isinstance(link_type, str):
            raise TypeError("link_type must be str.")

        self.external_link_url = external_link_url
        self.tweet_id = tweet_id
        self.tweet_url = tweet_url
        self.created_at = created_at
        self.user_id = user_id
        self.user_name = user_name
        self.screan_name = screan_name
        self.tweet_text = tweet_text
        self.tweet_via = tweet_via
        self.saved_created_at = saved_created_at
        self.link_type = link_type

    def __repr__(self) -> str:
        columns = ", ".join([f"{k}={v}" for k, v in self.__dict__.items() if k[0] != "_"])
        return f"<{self.__class__.__name__}({columns})>"

    def __eq__(self, other: Self) -> bool:
        return (
            isinstance(other, ExternalLink)
            and other.external_link_url == self.external_link_url
            and other.tweet_url == self.tweet_url
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "external_link_url": self.external_link_url,
            "tweet_id": self.tweet_id,
            "tweet_url": self.tweet_url,
            "created_at": self.created_at,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "screan_name": self.screan_name,
            "tweet_text": self.tweet_text,
            "tweet_via": self.tweet_via,
            "saved_created_at": self.saved_created_at,
            "link_type": self.link_type,
        }

    @classmethod
    def create(cls, arg_dict: dict) -> Self:
        match arg_dict:
            case {
                "external_link_url": external_link_url,
                "tweet_id": tweet_id,
                "tweet_url": tweet_url,
                "created_at": created_at,
                "user_id": user_id,
                "user_name": user_name,
                "screan_name": screan_name,
                "tweet_text": tweet_text,
                "tweet_via": tweet_via,
                "saved_created_at": saved_created_at,
                "link_type": link_type,
            }:
                return cls(
                    external_link_url,
                    tweet_id,
                    tweet_url,
                    created_at,
                    user_id,
                    user_name,
                    screan_name,
                    tweet_text,
                    tweet_via,
                    saved_created_at,
                    link_type,
                )
            case _:
                raise ValueError("ExternalLink create failed.")


class DeleteTarget(Base):
    """削除対象ツイート保持テーブルモデル

    [id] INTEGER,
    [tweet_id] TEXT NOT NULL UNIQUE,
    [delete_done] BOOLEAN DEFAULT '0',
    [created_at] DATETIME NOT NULL,
    [deleted_at] DATETIME,
    [tweet_text] TEXT NOT NULL,
    [add_num] INTEGER NOT NULL,
    [del_num] INTEGER NOT NULL,
    PRIMARY KEY(id)
    """

    __tablename__ = "DeleteTarget"

    id = Column(Integer, primary_key=True)
    tweet_id = Column(String(256), nullable=False, unique=True)
    delete_done = Column(Boolean, server_default=text("False"))
    created_at = Column(String(32), nullable=False)
    deleted_at = Column(String(32))
    tweet_text = Column(String(512), nullable=False)
    add_num = Column(Integer, nullable=False)
    del_num = Column(Integer, nullable=False)

    def __init__(self, tweet_id, delete_done, created_at, deleted_at, tweet_text, add_num, del_num):
        if not isinstance(tweet_id, str):
            raise TypeError("tweet_id must be str.")
        if not isinstance(delete_done, bool):
            raise TypeError("delete_done must be bool.")
        if not isinstance(created_at, str):
            raise TypeError("created_at must be str.")
        if deleted_at and not isinstance(deleted_at, str):
            raise TypeError("deleted_at must be str.")
        if not isinstance(tweet_text, str):
            raise TypeError("tweet_text must be str.")
        if not isinstance(add_num, int):
            raise TypeError("add_num must be int.")
        if not isinstance(del_num, int):
            raise TypeError("del_num must be int.")

        if add_num < 0:
            raise ValueError("add_num must be 0 <= add_num.")
        if del_num < 0:
            raise ValueError("del_num must be 0 <= del_num.")

        self.tweet_id = tweet_id
        self.delete_done = delete_done
        self.created_at = created_at
        self.deleted_at = deleted_at
        self.tweet_text = tweet_text
        self.add_num = add_num
        self.del_num = del_num

    def __repr__(self) -> str:
        columns = ", ".join([f"{k}={v}" for k, v in self.__dict__.items() if k[0] != "_"])
        return f"<{self.__class__.__name__}({columns})>"

    def __eq__(self, other: Self) -> bool:
        return isinstance(other, DeleteTarget) and other.tweet_id == self.tweet_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tweet_id": self.tweet_id,
            "delete_done": self.delete_done,
            "created_at": self.created_at,
            "deleted_at": self.deleted_at,
            "tweet_text": self.tweet_text,
            "add_num": self.add_num,
            "del_num": self.del_num,
        }

    @classmethod
    def create(cls, arg_dict: dict) -> Self:
        match arg_dict:
            case {
                "tweet_id": tweet_id,
                "delete_done": delete_done,
                "created_at": created_at,
                "deleted_at": deleted_at,
                "tweet_text": tweet_text,
                "add_num": add_num,
                "del_num": del_num,
            }:
                return cls(tweet_id, delete_done, created_at, deleted_at, tweet_text, add_num, del_num)
            case _:
                raise ValueError("DeleteTarget create failed.")


if __name__ == "__main__":
    engine = create_engine("sqlite:///PG_DB.db", echo=True)
    Base.metadata.create_all(engine)

    session = Session(engine)

    result = session.query(Favorite).all()[:10]
    for f in result:
        print(f)

    session.close()
