# coding: utf-8
import configparser
import os
import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.ext.declarative import declarative_base


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
        [saved_localpath] TEXT,
        [saved_created_at] TEXT,
        PRIMARY KEY([id])
    """
    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)
        self.is_exist_saved_file = True

    def __init__(self, is_exist_saved_file, img_filename, url, url_thumbnail, tweet_id, tweet_url, created_at, user_id, user_name, screan_name, tweet_text, saved_localpath, saved_created_at):
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
        self.saved_localpath = saved_localpath
        self.saved_created_at = saved_created_at

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
    saved_localpath = Column(String(256))
    saved_created_at = Column(String(32))

    def __repr__(self):
        return "<Favorite(id='%s', img_filename='%s', url='%s')>" % (self.id, self.img_filename, self.url)


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
        [saved_localpath] TEXT,
        [saved_created_at] TEXT,
        PRIMARY KEY([id])
    """
    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)
        self.is_exist_saved_file = True

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
    saved_localpath = Column(String(256))
    saved_created_at = Column(String(32))

    def __repr__(self):
        return "<Retweet(id='%s', img_filename='%s', url='%s')>" % (self.id, self.img_filename, self.url)


class DeleteTarget(Base):
    """削除対象ツイート保持テーブルモデル

        CREATE TABLE [DeleteTarget] (
        [id] INTEGER,
        [tweet_id] TEXT NOT NULL UNIQUE,
        [delete_done] BOOLEAN DEFAULT '0',
        [created_at] DATETIME NOT NULL,
        [deleted_at] DATETIME,
        [tweet_text] TEXT NOT NULL,
        [add_num] INTEGER NOT NULL,
        [del_num] INTEGER NOT NULL,
        PRIMARY KEY(id)
        );
    """
    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)
        self.delete_done = False

    __tablename__ = "DeleteTarget"

    id = Column(Integer, primary_key=True)
    tweet_id = Column(String(256), nullable=False, unique=True)
    delete_done = Column(Boolean, server_default=text("False"))
    created_at = Column(String(32), nullable=False)
    deleted_at = Column(String(32))
    tweet_text = Column(String(512), nullable=False)
    add_num = Column(Integer, nullable=False)
    del_num = Column(Integer, nullable=False)

    def __repr__(self):
        return "<DeleteTarget(id='%s', tweet_id='%s', delete_done='%s')>" % (self.id, self.tweet_id, self.delete_done)


if __name__ == "__main__":
    engine = create_engine("sqlite:///PG_DB.db", echo=True)
    Base.metadata.create_all(engine)

    session = Session(engine)

    result = session.query(Favorite).all()[:10]
    for f in result:
        print(f)

    session.close()
