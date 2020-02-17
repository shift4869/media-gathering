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


engine = create_engine("sqlite:///PG_DB.db", echo=True)
Base = declarative_base()


class Favorite(Base):
    """ふぁぼツイートモデル
    """
    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)
        self.is_exist_saved_file = True

    __tablename__ = "Favorite"

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

    '''
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
    '''

    def __repr__(self):
        return "<Favorite(id='%s', img_filename='%s', url='%s')>" % (self.id, self.img_filename, self.url)


if __name__ == "__main__":
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    result = session.query(Favorite).all()[:10]
    for f in result:
        print(f)

    session.close()
