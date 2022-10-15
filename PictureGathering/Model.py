# coding: utf-8
from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import *

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

    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)
        self.is_exist_saved_file = True

    def __init__(self, is_exist_saved_file, img_filename, url, url_thumbnail, tweet_id, tweet_url, created_at, user_id, user_name, screan_name, tweet_text, tweet_via, saved_localpath, saved_created_at, media_size, media_blob):
        # self.id = id
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

    def __repr__(self):
        return "<Favorite(id='%s', img_filename='%s', url='%s')>" % (self.id, self.img_filename, self.url)

    def __eq__(self, other):
        return isinstance(other, Favorite) and other.img_filename == self.img_filename

    def toDict(self):
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
            "media_blob": None,
        }

    @classmethod
    def create(cls, arg_dict: dict) -> "Favorite":
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
                return cls(is_exist_saved_file,
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
                           media_blob)
            case _:
                raise ValueError(f"{type(cls)} create failed.")


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

    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)
        self.is_exist_saved_file = True

    def __init__(self, is_exist_saved_file, img_filename, url, url_thumbnail, tweet_id, tweet_url, created_at, user_id, user_name, screan_name, tweet_text, tweet_via, saved_localpath, saved_created_at, media_size, media_blob):
        # self.id = id
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

    def __repr__(self):
        return "<Retweet(id='%s', img_filename='%s', url='%s')>" % (self.id, self.img_filename, self.url)

    def __eq__(self, other):
        return isinstance(other, Retweet) and other.img_filename == self.img_filename

    def toDict(self):
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
            "media_blob": None,
        }

    @classmethod
    def create(cls, arg_dict: dict) -> "Retweet":
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
                return cls(is_exist_saved_file,
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
                           media_blob)
            case _:
                raise ValueError(f"{type(cls)} create failed.")


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

    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)

    def __init__(self, external_link_url, tweet_id, tweet_url, created_at, user_id, user_name, screan_name, tweet_text, tweet_via, saved_created_at, link_type):
        # self.id = id
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

    def __repr__(self):
        return "<ExternalLink(id='%s', external_link_url='%s', tweet_url='%s')>" % (self.id, self.external_link_url, self.tweet_url)

    def __eq__(self, other):
        return isinstance(other, ExternalLink) and other.external_link_url == self.external_link_url and other.tweet_url == self.tweet_url

    def toDict(self):
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
    def create(cls, arg_dict: dict) -> "ExternalLink":
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
                return cls(external_link_url,
                           tweet_id,
                           tweet_url,
                           created_at,
                           user_id,
                           user_name,
                           screan_name,
                           tweet_text,
                           tweet_via,
                           saved_created_at,
                           link_type)
            case _:
                raise ValueError(f"{type(cls)} create failed.")


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

    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)
        self.delete_done = False

    def __init__(self, tweet_id, delete_done, created_at, deleted_at, tweet_text, add_num, del_num):
        # self.id = id
        self.tweet_id = tweet_id
        self.delete_done = delete_done
        self.created_at = created_at
        self.deleted_at = deleted_at
        self.tweet_text = tweet_text
        self.add_num = add_num
        self.del_num = del_num

    def __repr__(self):
        return "<DeleteTarget(id='%s', tweet_id='%s', delete_done='%s')>" % (self.id, self.tweet_id, self.delete_done)

    def __eq__(self, other):
        return isinstance(other, DeleteTarget) and other.tweet_id == self.tweet_id

    def toDict(self):
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


if __name__ == "__main__":
    engine = create_engine("sqlite:///PG_DB.db", echo=True)
    Base.metadata.create_all(engine)

    session = Session(engine)

    result = session.query(Favorite).all()[:10]
    for f in result:
        print(f)

    session.close()
